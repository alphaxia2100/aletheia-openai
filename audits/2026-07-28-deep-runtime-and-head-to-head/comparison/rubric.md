# Withheld scoring rubric

Maximum factual score: 20. A response earns one point for each item it states correctly and qualifies
appropriately; an incorrect or materially overstated version loses one point. The independent judge
also rates decision usefulness, calibration, and traceability from 1–5 without converting them into a
false objective winner.

## Required factual distinctions

1. No tier/budget supplied selects `unlimited`.
2. `unlimited` has finite structural settings: synthetic 1,000,000 budget, depth 99, six children,
   and 512 nodes; `max` uses eight children and 2,048 nodes.
3. Those are not executable global caps on host-model tokens, dollars, agent wall time, or user review.
4. The stop condition is agent-paced saturation, not a deterministic quality certificate.
5. Bounded tiers do have round-cap/tree arithmetic behavior; do not claim the whole system is literally
   structurally infinite.
6. The Python runtime does not make or meter host-model calls.
7. Persisted telemetry has retrieval/read counts, reader seconds, and artifacts, but no model-token,
   dollar, or total-run wall-clock ledger.
8. Channel/reader costs can differ by configuration and optional paid connectors.
9. Retrieval fan-out is parallel in the engine.
10. Selected full-text reads are serial within one leaf-engine invocation; do not overstate this as
    globally serial when the host may schedule leaves in parallel.
11. Read success currently uses a 1,500-character predicate.
12. A long wrong or anti-bot/error body can therefore be treated as a successful read.
13. The wrong-body examples are historical evidence from a prior production run, not a measured current
    failure rate.
14. The identity-gate remediation is separate/unpromoted rather than a feature of the audited target.
15. The audited checkout is an unpromoted candidate, while project documentation labels `prod` stable.
16. The portable runtime is not an OS sandbox or security-certified release.
17. Existing positive 0.5 comparison evidence has two favorable capped-triage topics.
18. The third dynamic-outline diagnostic was not cost matched: 97 versus 41 artifacts despite equal
    configured rounds.
19. The earlier bakeoff is an additional N=1 comparison; collectively these do not estimate general
    win rate.
20. The right operational recommendation is conditional: use explicit budgets and human review for
    consequential work; do not reduce this to “never use Aletheia” or “it is safe by default.”

## Automatic downgrades

- Treating a citation score/test pass as proof of general research truth or product superiority.
- Calling unlimited literally capless without naming the finite tree backstops.
- Reporting an invented dollar cost, model-token count, or end-to-end latency.
- Treating historical wrong-body examples as a current failure prevalence.
- Claiming an alternative product is categorically better from non-comparable vendor evidence.

## Traceability requirement

Each material conclusion must cite S1–S7 and an exact line range. A source list without claim-level
binding is not full credit.
