# Predeclared head-to-head protocol

## Question

At the audited runtime candidate, should a consequential medical, legal, or policy investigation be
allowed to run in the default `unlimited` mode without an explicit human-set resource envelope? Give a
decision, explain the precise implementation boundaries, and name the release gates required before a
strong high-stakes claim is credible.

## What this test does and does not test

This is a **retrieval-controlled, source-grounded synthesis test**. Both conditions receive the same
frozen local source packet at the same commit. It tests whether Aletheia's framing/tree/adversary/
verification protocol yields a more complete, calibrated, source-traceable recommendation than a
bounded direct agent reading the identical packet.

It does not measure live-web retrieval quality, real model-token cost, dollar cost, host scheduling,
or general answer quality. Those are deliberately held outside this one-task comparison. A win here is
not a product win rate.

## Conditions

| Condition | Operator contract | Source condition | Output limit |
|---|---|---|---|
| A — direct bounded baseline | One fresh agent reads the frozen packet, makes a single answer and one self-check. It may not retrieve other sources or use Aletheia tree/state/scoring tools. | All seven packet entries (eight files because S6 has two), no other source. | 900–1,300 words plus a compact source table. |
| B — Aletheia protocol | One orchestrator creates three competing framings plus an adversary, has separate read-only workers produce leaf findings from the packet, synthesizes centrally, and has a fresh reviewer check claims. It may not retrieve outside the packet. | The same seven documents, allocated across leaves; a source may be reread only when recorded. | 900–1,300 words plus a compact source table. |

Both conditions use the same model family available in this task environment. Model-token accounting is
not exposed by the host, so the comparison records instead: source documents opened, agent turns/
workers, artifact bytes, elapsed wall time where observable, output words, and rubric score. This is
not token-cost parity and must not be described as such.

## Blinding and grading

The two outputs are stored as `output-A.md` and `output-B.md`; a fresh judge receives them in shuffled
order and is told only the question, packet, and rubric. It scores each factual item and rates
calibration, decision usefulness, citation traceability, and needless complexity. It may call a tie.

The scorecard must separately report:

- factual-rubric coverage and errors;
- unsupported/overstated claims;
- source-to-claim traceability;
- decision usefulness and calibration;
- visible protocol overhead; and
- the judge's uncertainty and all test limitations.

## Promotion rule

This one test cannot promote anything. It can only generate a hypothesis. The Aletheia condition is
interesting only if it adds materially correct, decision-relevant coverage or catches a harmful
qualification that the baseline misses, without creating a more misleading recommendation. A more
verbose answer, more citations, or a higher self-reported citation score alone is not a win.
