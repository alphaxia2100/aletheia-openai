---
name: defensibility-judge
description: Scores whether a belief is actually defensible using a 4-part rubric (falsifier stated, falsifier searched, traces to independent primary evidence, opposing view steelmanned), and coordinates a heterogeneous-model audit. Use to judge each spiky POV or load-bearing conclusion at the end of an Aletheia survey, or as a "both-sides" check on any belief.
disable-model-invocation: true
---

# defensibility-judge

A belief is a claim plus the best counter-argument it survived. This stage decides whether the survey's conclusions have earned that status — and it doubles as the "both-sides" judge for checking whether an agentically-generated view is biased.

## The 4-part rubric

A belief is defensible only when:
1. **It states its own falsifier** — what specific evidence would sink it.
2. **You went looking for that falsifier** and can report what you found (even "nothing after a real search").
3. **It traces to independent primary evidence** — not circular citation; the `provenance-audit` "N independent, not M echoed" test.
4. **You can steelman the strongest opposing view** and say specifically why you still hold the belief.

## Run

```bash
# score a belief; auto-fill criterion 3 straight from the provenance audit:
python3 ~/.cursor/skills/defensibility-judge/scripts/rubric.py belief.json \
    --from-provenance runs/<run>/provenance.json --claim-id <claim>
```

`belief.json` mirrors `samples/demo_belief.json`. The script exits non-zero when a belief is not yet defensible, so it can gate the pipeline. Wiring `--from-provenance` is the point: a belief that reads well but rests on a single echoed origin will drop to PARTIAL on criterion 3 automatically.

## Both-sides loop

Judge **every** spiky POV and load-bearing conclusion. If one fails:
- criterion 1/4 fail → the writer must state the falsifier / steelman before shipping;
- criterion 2 fails → send the `adversary` back out on the un-laundered channels;
- criterion 3 fails → send `channel-retrieval` back for an *independent* corroborating source (different `index_group`), then re-audit.
Do not ship a failed belief as established fact — demote it to "lead" or "unresolved disagreement" in `synthesis`.

## Heterogeneous-model audit

Correlated errors are the enemy. Where the harness allows, run **synthesis and the adversary on different base models** so their mistakes are uncorrelated:
- In Cursor/Claude Code, dispatch the adversary (and optionally a second synthesis) as a subagent on a *different* model than the one that wrote the survey, then have this judge compare them.
- Structure the comparison as an **audit, not a vote**: surface agreement / disagreement / unique claims across models. Divergence is a finding, not noise to average away.
- Diversity must be real: different base models and different channels. A "skeptic" persona on the *same* model is weak diversity (and persuasive personas can eclipse accuracy) — never weight whose answer to believe by persona.

## When is it enough? (the transfer test)

Enough brainlifting is when **you can defend the view unaided** — without the model in the room. That is the whole point (you don't lift to move the one rock; you lift to become strong). Corollaries:
- **Form over weight** — ten sources reasoned-through beats a hundred skimmed.
- **Progressive overload** — each survey, harder topics and stronger adversaries.
- **Overtraining is real** — once new sources stop moving the view, more "research" is procrastination wearing the costume of rigor. Stop and commit to the belief.

## Output

Write `runs/<run>/defensibility.md` with each belief's verdict, per-criterion scores, and the gaps to close. Defensible beliefs are eligible for the `consilient-atlas`; failed ones are demoted, not shipped.
