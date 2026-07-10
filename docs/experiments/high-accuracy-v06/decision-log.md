# Decision log

Append entries; do not rewrite history. A reversal adds a new entry that names the superseded one.

## D001 — preserve the validated release

- Decision: tag `addfaf6` as `openai-aletheia-v0.5.0-openai.1-checkpoint` and branch experiments into
  a separate worktree.
- Why: installation and prior forward tests remain reproducible while aggressive changes proceed.
- Alternative rejected: experiment directly on the installed branch; it would destroy the rollback.

## D002 — operationalize the user's ceilings conservatively

- Decision: enforce 3,600 seconds, 40 reads per round, and 640 run-wide read attempts/artifacts.
- Assumption: “current cap” refers to the code-enforced four reads per round and the exhaustive tier's
  64-read theoretical maximum; both interpretations are enforced at 10×.
- Why: a wall-clock promise without runtime enforcement and a read promise without manual-artifact
  counting are not real caps.
- Revisit when: cap instrumentation or the user's intended denominator proves different.

## D003 — audit the evaluator before optimizing against it

- Decision: delegate an independent evaluator-validity audit and require known-defect meta-evaluation.
- Why: pairwise preference can reward length and polish while missing unsupported, stale, or omitted
  claims. Optimizing against a weak evaluator would select reward hacking.
- Alternative rejected: immediately restore the dynamic outline because two judges preferred it.

## D004 — keep mechanisms separable

- Decision: treat hard-cap enforcement, claim/evidence state, adaptive control, source acquisition,
  synthesis, and evaluation as independently testable changes.
- Why: a monolithic “high accuracy” prompt cannot identify causality or support rollback.

## D005 — start with a four-framing evidence portfolio

- Decision: investigate adaptive claim planning, retrieval/source quality, verification/evaluation,
  and working-system/adversarial evidence from distinct source bases.
- Leading hypothesis: a claim-and-uncertainty ledger with evidence-directed actions will outperform a
  prose outline alone.
- Adversary: extra planning/reads may amplify noise, context loss, echo, and evaluator gaming.

