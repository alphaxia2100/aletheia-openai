// Blind re-judge of ALREADY-GENERATED briefs, from SANITIZED copies (version/identity stripped).
// Use when the first judge pass was un-blinded by provenance strings inside the briefs (e.g. a brief
// self-labeling "v0.4.3" / "0.5.0-dev3" or "this baseline"). Generation is NOT redone — only the judge.
//   Workflow({ scriptPath: "scripts/eval/rejudge_sanitized.workflow.js", args: {
//     pairs: [{topic, question, cand, base}],   // cand/base = sanitized brief.md paths (blind to judge)
//     trials: 3, judge_model: "opus" } })
// Returns {pairwise:[{topic,trial,winner,why}]} de-randomized to generator-space; feed with the
// (unaffected) objective metrics into scripts/eval/judge_score.py.
export const meta = {
  name: 'rejudge-sanitized',
  description: 'Blind re-judge of sanitized briefs (fix a provenance-leak in the first judge pass)',
  phases: [{ title: 'Judge', detail: 'blind, position-randomized, multi-trial pairwise judge on sanitized copies' }],
}

const A = args
const trials = A.trials || 3
const VERDICT = {
  type: 'object', additionalProperties: false, required: ['better', 'why'],
  properties: {
    better: { type: 'string', description: 'exactly "A" or "B" or "tie"' },
    why: { type: 'string', description: 'one line: which was more complete + better grounded to distinct primaries' },
  },
}

const pairwise = await parallel(
  A.pairs.flatMap((p) =>
    Array.from({ length: trials }, (_, i) => () => {
      const candIsA = (p.topic.charCodeAt(0) + i) % 2 === 0   // deterministic pseudo-random position
      const A_path = candIsA ? p.cand : p.base
      const B_path = candIsA ? p.base : p.cand
      return agent(
        `You are a blind, impartial judge of two research briefs answering the SAME question: "${p.topic}". ` +
        `Read brief A (${A_path}) and brief B (${B_path}) in full. Judge which is the better research product on: ` +
        `completeness, groundedness to DISTINCT PRIMARY sources, calibration/honesty of uncertainty, and honest gaps. ` +
        `You do not know which system produced which; the briefs carry no version or identity markers. ` +
        `Output {"better":"A"|"B"|"tie","why":"..."}.`,
        { label: `rejudge:${p.topic}:${i}`, phase: 'Judge', schema: VERDICT, model: A.judge_model || 'opus' }
      ).then((v) => ({
        topic: p.topic, trial: i,
        winner: v.better === 'tie' ? 'tie' : (v.better === 'A') === candIsA ? 'candidate' : 'baseline',
        why: v.why,
      }))
    })
  )
).then((r) => r.filter(Boolean))

return { pairwise, note: 'sanitized blind re-judge; combine with the unchanged objective metrics in judge_score.py' }
