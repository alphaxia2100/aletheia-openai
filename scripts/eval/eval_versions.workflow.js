// Aletheia automated version eval — run with:
//   Workflow({ scriptPath: "scripts/eval/eval_versions.workflow.js", args: {...} })
// args = {
//   baseline:  {name, scripts_dir},   // scripts_dir = a worktree checked out at the baseline's git TAG
//   candidate: {name, scripts_dir},   // (baseline integrity: never point at edited working files)
//   topics:    [{id, topic}],         // held-out subset from scripts/eval/topics.jsonl
//   tier:      "deep",                // fixed across versions (fair, affordable); NOT max
//   judge_model: "opus",              // use the STRONGEST judge (judging quality is HARDER than
//                                     // generating it). Do NOT weaken the judge for "disjointness":
//                                     // here both briefs are the SAME generator model (only the skill
//                                     // version differs), so there is no self-preference axis; bias is
//                                     // handled by blinding + position-randomization + human kappa, not
//                                     // by downgrading the judge. (Optionally ensemble the top models.)
//   trials:    3,                     // pairwise judge trials, position-randomized
//   out:       "runs/eval/<ts>"       // where briefs + results.json + anchor.jsonl land
// }
// It generates a brief per (version,topic), computes objective sub-metrics (report.py score), then a
// blind position-randomized multi-trial pairwise judge; de-randomizes; writes results.json (feed to
// scripts/eval/judge_score.py) + anchor.jsonl (blind pairs for the human to label -> judge calibration).
export const meta = {
  name: 'eval-aletheia-versions',
  description: 'Automated pairwise version eval: generate briefs per version/topic, objective metrics, blind multi-trial LLM judge',
  phases: [
    { title: 'Generate', detail: 'run each version (from its tag) on each held-out topic -> brief + objective score' },
    { title: 'Judge', detail: 'blind, position-randomized, multi-trial pairwise judge (different model)' },
  ],
}

const A = args
const tier = A.tier || 'deep'
const trials = A.trials || 3
const out = A.out || 'runs/eval/latest'

const VERDICT = {
  type: 'object', additionalProperties: false,
  required: ['better', 'why'],
  properties: {
    better: { type: 'string', description: 'exactly "A" or "B" or "tie"' },
    why: { type: 'string', description: 'one line: which was more complete + better grounded to distinct primaries' },
  },
}

// Phase 1: generate a brief per (version, topic), and objective sub-metrics for each.
const gen = await parallel(
  [A.baseline, A.candidate].flatMap((v) =>
    A.topics.map((t) => () => agent(
      `Run the aletheia-research skill (scripts at ${v.scripts_dir}/.cursor/skills/aletheia-research/scripts, ` +
      `SKILL at ${v.scripts_dir}/.cursor/skills/aletheia-research/SKILL.md) at thoroughness ${tier}, verbosity user, ` +
      `--base ${out}/gen on the topic: "${t.topic}". Execute the full loop (doctor, frame, decompose, investigate, ` +
      `synthesize+independence, adversary, verify to completion, write brief.md). Then score the run with the SHARED ` +
      `scorer (one instrument for BOTH versions): python3 ${A.scorer} score --run <run_dir>. ` +
      `Return ONLY JSON: {"version":"${v.name}","topic_id":"${t.id}","run_dir":"<the run dir>","brief_path":"<run>/brief.md",` +
      `"objective":<the shared-scorer JSON>}. Do NOT summarize the brief.`,
      { label: `gen:${v.name}:${t.id}`, phase: 'Generate',
        schema: { type: 'object', additionalProperties: true, required: ['version', 'topic_id', 'brief_path'],
                  properties: { version: {}, topic_id: {}, run_dir: {}, brief_path: {}, objective: {} } } }
    ))
  )
).then((r) => r.filter(Boolean))

const briefOf = (ver, tid) => gen.find((g) => g.version === ver && g.topic_id === tid)

// Phase 2: per topic, N blind position-randomized trials of a DIFFERENT-model judge.
const pairwise = await parallel(
  A.topics.flatMap((t) => {
    const b = briefOf(A.baseline.name, t.id), c = briefOf(A.candidate.name, t.id)
    if (!b || !c) return []
    return Array.from({ length: trials }, (_, i) => () => {
      const candIsA = (t.id.charCodeAt(0) + i) % 2 === 0   // deterministic pseudo-random position (no Math.random in scripts)
      const A_path = candIsA ? c.brief_path : b.brief_path
      const B_path = candIsA ? b.brief_path : c.brief_path
      return agent(
        `You are a blind, impartial judge of two research briefs answering the SAME question: "${t.topic}". ` +
        `Read brief A (${A_path}) and brief B (${B_path}) in full. Judge which is the better research product on: ` +
        `completeness, groundedness to DISTINCT PRIMARY sources, calibration/honesty of uncertainty, and honest gaps. ` +
        `You do not know which system produced which. Output {"better":"A"|"B"|"tie","why":"..."}.`,
        { label: `judge:${t.id}:${i}`, phase: 'Judge', schema: VERDICT, model: A.judge_model || 'sonnet' }
      ).then((v) => {
        const winner = v.better === 'tie' ? 'tie'
          : (v.better === 'A') === candIsA ? 'candidate' : 'baseline'   // de-randomize to generator-space
        return { topic: t.id, trial: i, winner, why: v.why }
      })
    })
  })
).then((r) => r.filter(Boolean))

const objective = { candidate: {}, baseline: {} }
for (const g of gen) {
  const side = g.version === A.candidate.name ? 'candidate' : g.version === A.baseline.name ? 'baseline' : null
  if (side && g.objective) objective[side][g.topic_id] = g.objective
}

// anchor.jsonl: the same pairs, blind, for the HUMAN to label -> feeds judge calibration (kappa).
const anchor = A.topics.map((t) => {
  const b = briefOf(A.baseline.name, t.id), c = briefOf(A.candidate.name, t.id)
  const candIsA = t.id.charCodeAt(0) % 2 === 0
  return b && c ? { topic: t.id, question: t.topic,
                    A: candIsA ? c.brief_path : b.brief_path, B: candIsA ? b.brief_path : c.brief_path,
                    _cand_is: candIsA ? 'A' : 'B' } : null
}).filter(Boolean)

return { out, objective, pairwise, anchor,
         note: 'write {pairwise,objective,human:[{topic,winner}]} to results.json and run scripts/eval/judge_score.py; ' +
               'label anchor.jsonl yourself (which of A/B is better) to calibrate the judge (kappa).' }
