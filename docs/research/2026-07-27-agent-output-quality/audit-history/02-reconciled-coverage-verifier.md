# Final independent coverage verification

Verifier: fresh-context Codex subagent (`/root/final_coverage_verifier`)  
Run: `2026-07-27-101249-aletheia-output-quality-20260727`  
Date: 2026-07-27

## Result

I independently read the complete current 426-line `brief.md`, all 81 current `claims.jsonl`
rows, all 81 current lexical `verify.jsonl` rows, the internal operational record, and the
current cited primary/full/decisive captures used by the ledger. All lexical rows are `relevant`;
that only located evidence and was not treated as proof.

The 81 existing rows yield **79 supported, 0 contradicted, and 2 unsupported** verdicts. The
unsupported rows are the universal normative tool-failure rule (claim 60) and the compound
cost-matching/order-balancing row (claim 73), for which no single declared URL supports both
clauses. `final-verifier-verdicts-proposal.jsonl` has exactly one row for every current ledger
claim, retains the exact claim text, and selects one declared URL per row.

I found **12 omitted load-bearing claims**. Of those additions, **4 are supported and 8 are
unsupported as currently framed**. The main omissions are the exact 950,921/28,782-byte table
comparison, the 164/164 identity-branch test result, opening priority/causal judgments, several
unvalidated architecture and policy requirements, the overbroad HiAgent inference, the final
cross-study disagreement synthesis, branch-table status assertions, and the final shipping rule.

| Scope | Supported | Contradicted | Unsupported | Total |
|---|---:|---:|---:|---:|
| Existing current claims | 79 | 0 | 2 | 81 |
| Omitted proposed additions | 4 | 0 | 8 | 12 |
| Reconciled proposal | 83 | 0 | 10 | 93 |

## Required edits before attestation

1. Split current claim 73 into a project-record cost-parity claim and a judge-order-bias claim;
   cite the latter to MT-Bench or the position-bias study.
2. Label the `must` rule about tool failure/empty indexes as an explicit project policy, or add
   a source that establishes the normative rule.
3. Add ledger coverage for the 950,921-byte versus 28,782-byte table row and the 164/164 test
   result.
4. Keep the opening seven-plane ranking and final branch-shipping requirements explicitly marked
   as risk-based project policy. The evidence identifies real defects but does not compare their
   expected value or establish that hierarchy is not the main bottleneck.
5. Downgrade or test the unvalidated claim/evidence-graph rules, question-graph action/ledger
   design, structural-origin-versus-domain superiority, and broad disagreement synthesis. The
   current labels are adequate where present but several adjacent sentences state them as
   requirements or conclusions.
6. Replace “direct evidence that summary-only memory is insufficient” with the bounded HiAgent
   ablation result. Add direct evidence records for the branch-table statuses not covered by the
   internal operational note.

No `brief.md`, `claims.jsonl`, or `verify.jsonl` file was edited, and no audit command was run.
The proposed artifacts are intentionally not an attestation; required edits and a subsequent
fresh coverage pass remain necessary before `audit-claims`.
