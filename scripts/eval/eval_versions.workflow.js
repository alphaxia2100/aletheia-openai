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
//   trials:    1,                     // exact A/B+B/A PAIRS per topic (both orders are mandatory)
//   out:       "runs/eval/<ts>"       // where briefs + results.json + anchor.jsonl land
// }
// It generates a brief per (version,topic), computes objective sub-metrics (report.py score), then a
// blind exact-order-paired judge. Return value MUST be passed to persist_judges.py; it writes one
// immutable artifact per judge call plus separate public anchors and private mapping keys.
export const meta = {
  name: 'eval-aletheia-versions',
  description: 'Automated pairwise version eval: generate briefs, neutralize paths, score, and run exact-order-paired judging',
  phases: [
    { title: 'Generate', detail: 'run each version (from its tag) on each held-out topic -> brief + objective score' },
    { title: 'Judge', detail: 'blind, neutral-path, exact A/B+B/A pairwise judge (different model)' },
  ],
}

const A = args
const tier = A.tier || 'deep'
const trials = A.trials || 1
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
    A.topics.map((t) => {
      const blindSlot = v.name === A.baseline.name ? 'input-1' : 'input-2'
      const blindPath = `${out}/blind-inputs/${t.id}/${blindSlot}.md`
      return () => agent(
      `Run the aletheia-research skill (scripts at ${v.scripts_dir}/.cursor/skills/aletheia-research/scripts, ` +
      `SKILL at ${v.scripts_dir}/.cursor/skills/aletheia-research/SKILL.md) at thoroughness ${tier}, verbosity user, ` +
      `--base ${out}/gen on the topic: "${t.topic}". Execute the full loop (doctor, frame, decompose, investigate, ` +
      `synthesize+independence, adversary, verify to completion, write brief.md). Then score the run with the SHARED ` +
      `scorer (one instrument for BOTH versions): python3 ${A.scorer} score --run <run_dir>. ` +
      `Create a byte-for-byte copy of brief.md at the neutral path ${blindPath}; create its parent directory first. ` +
      `Return ONLY JSON: {"version":"${v.name}","topic_id":"${t.id}","run_dir":"<the run dir>","brief_path":"<run>/brief.md",` +
      `"blind_path":"${blindPath}",` +
      `"objective":<the shared-scorer JSON>}. Do NOT summarize the brief.`,
      { label: `gen:${v.name}:${t.id}`, phase: 'Generate',
        schema: { type: 'object', additionalProperties: true,
                  required: ['version', 'topic_id', 'brief_path', 'blind_path'],
                  properties: { version: {}, topic_id: {}, run_dir: {}, brief_path: {},
                                blind_path: {}, objective: {} } } }
      )
    })
  )
).then((r) => r.filter(Boolean))

const briefOf = (ver, tid) => gen.find((g) => g.version === ver && g.topic_id === tid)

// Phase 2: per topic, N exact A/B+B/A pairs. A semantic win survives only if BOTH orders agree.
const pairwise = await parallel(
  A.topics.flatMap((t) => {
    const b = briefOf(A.baseline.name, t.id), c = briefOf(A.candidate.name, t.id)
    if (!b || !c) return []
    return Array.from({ length: trials }, (_, i) =>
      [true, false].map((candIsA) => () => {
        const A_path = candIsA ? c.blind_path : b.blind_path
        const B_path = candIsA ? b.blind_path : c.blind_path
        const order = candIsA ? { A: 'candidate', B: 'baseline' } : { A: 'baseline', B: 'candidate' }
        const prompt =
          `You are a blind, impartial judge of two research briefs answering the SAME question: "${t.topic}". ` +
          `Read brief A (${A_path}) and brief B (${B_path}) in full. Judge which is the better research product on: ` +
          `completeness, groundedness to DISTINCT PRIMARY sources, uncertainty expression, and honest gaps. ` +
          `Do not reward repetition or length by itself. You do not know which system produced which. ` +
          `Output {"better":"A"|"B"|"tie","why":"..."}.`
        return agent(prompt,
          { label: `judge:${t.id}:${i}:${candIsA ? 'order-1' : 'order-2'}`, phase: 'Judge',
            schema: VERDICT, model: A.judge_model || 'sonnet' }
        ).then((v) => {
          const winner = v.better === 'tie' ? 'tie' : order[v.better]
          return { schema_version: 2, topic: t.id, pair_id: `pair-${i}`, judge_id:
                   `judge:${t.id}:${i}:${candIsA ? 'order-1' : 'order-2'}`,
                   judge_model: A.judge_model || 'sonnet', order, winner_shown: v.better,
                   winner, why: v.why, A_path, B_path, prompt }
        })
      })
    ).flat()
  })
).then((r) => r.filter(Boolean))

const objective = { candidate: {}, baseline: {} }
for (const g of gen) {
  const side = g.version === A.candidate.name ? 'candidate' : g.version === A.baseline.name ? 'baseline' : null
  if (side && g.objective) objective[side][g.topic_id] = g.objective
}

// Human-visible anchors contain NO generator mapping. Keep the key in a separate private artifact.
const anchorPublic = A.topics.map((t) => {
  const b = briefOf(A.baseline.name, t.id), c = briefOf(A.candidate.name, t.id)
  const candIsA = t.id.charCodeAt(0) % 2 === 0
  return b && c ? { topic: t.id, question: t.topic,
                    A: candIsA ? c.blind_path : b.blind_path,
                    B: candIsA ? b.blind_path : c.blind_path } : null
}).filter(Boolean)
const anchorKey = A.topics.map((t) => {
  const b = briefOf(A.baseline.name, t.id), c = briefOf(A.candidate.name, t.id)
  const candIsA = t.id.charCodeAt(0) % 2 === 0
  return b && c ? { topic: t.id, candidate_is: candIsA ? 'A' : 'B' } : null
}).filter(Boolean)

return { out, objective, pairwise, judge_artifacts: pairwise, anchor_public: anchorPublic, anchor_key: anchorKey,
         note: 'Persist this whole object with scripts/eval/persist_judges.py before scoring. Label only ' +
               'anchor-public.jsonl; keep anchor-key.jsonl private. Then add human generator-space labels and run ' +
               'judge_score.py. A win is valid only when both shown orders agree.' }
