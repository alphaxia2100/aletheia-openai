# Mechanism hypotheses and experiment matrix

| ID | Mechanism | Accuracy rationale | Main falsifier | Required telemetry | Status |
|---|---|---|---|---|---|
| H1 | Enforced wall/read budget ledger | Prevents hidden cost and incomplete termination | Counters disagree with persisted artifacts or timeout is advisory | monotonic elapsed time; engine/manual reads; cap reason | proposed |
| H2 | Atomic claim-and-evidence ledger | Directs work to important unsupported/conflicted claims and exposes omissions | Same or worse claim recall/precision than prose workflow | claim state transitions; source spans; uncertainty; action reason | researching |
| H3 | Adaptive expand/contract/revise controller | Evidence can reveal missing or redundant branches | Quality gain disappears at matched reads or controller only expands | proposals, accepted/rejected actions, budget transfer, contractions | researching |
| H4 | Query portfolio plus citation-chain chasing | Raises decisive-primary recall and source independence | More retrieval without more useful/independent claim evidence | query intent; parent lead; resolved primary; origin graph | researching |
| H5 | Structured contradiction and temporal checks | Prevents polarity, scope, version, and stale-status errors | Defect suite is not detected or false positives damage correct claims | check type; quoted spans; as-of date; verdict | researching |
| H6 | Evidence-table-first synthesis | Reduces prose claims not grounded in the gathered record | Final claim-scope additions and unsupported rate do not fall | evidence row→draft claim mapping; omitted-claim audit | proposed |
| H7 | Improved evaluator with defect calibration | Selects accuracy rather than verbosity/style | Cannot outperform old evaluator on known seeded defects | defect detection by type; order reversal; calibration agreement | delegated audit |
| H8 | More reads alone | May improve breadth when cost is permissive | Marginal sources add no supported decision-relevant claims or reduce accuracy | marginal claim yield and origin novelty per read tranche | adversarial control |

No row is promoted from paper plausibility, unit tests, or a single favorable topic.
