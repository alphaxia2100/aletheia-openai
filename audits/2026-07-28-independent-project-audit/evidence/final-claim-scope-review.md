# Final claim-scope review

**Independent verifier:** fresh-context semantic pass, 2026-07-28. This review covers only the
final cited-source set below; it does not treat uncited repository material or prior audit prose as
evidence.

## Locked artifact set

| Artifact | SHA-256 |
|---|---|
| `research-runs/2026-07-28-184302-independent-project-audit/brief.md` | `ebf3ce5e9fb8410f9eeaecc01a46b63aebe39678442f22e87ec38ffc38eb1f90` |
| `research-runs/2026-07-28-184302-independent-project-audit/claims.jsonl` | `d8cccbeff3c0a86c64ef6f3aca7272942d6e8f3ead6054e13f9ec5897a3c8ef2` |
| `research-runs/2026-07-28-184302-independent-project-audit/verify.jsonl` | `2564202594109942285420c3db1785c47af044bb06a87559bac2a7c86fca3726` |

## Semantic verification

| # | Ledger claim | Verdict | Cited-source basis | Wording fix, if needed |
|---|---|---|---|---|
| 1 | Unlimited has the stated 1,000,000 synthetic budget, depth 99, 512-node backstop; max has 2,048 nodes; neither has a per-leaf round cap. | **supported** | `treestate.py` defines the two tier dictionaries; `investigate.py::_round_cap()` returns `None` for `unlimited` and `max`. | None. |
| 2 | The current read path treats 1,500 non-whitespace characters as success rather than proving requested-document identity. | **supported** | `investigate.py::_read_source()` and `_execute_reads()` apply the length predicate and record `_read_ok`; there is no expected-versus-observed title/identifier comparison. | None; retain the current *read path* scope, rather than claiming every resolver behavior is identical. |
| 3 | Historical wrong-document, anti-bot, and arXiv error-shell false successes occurred. | **supported** | `internal-observations.md` documents two identifier mismatches, the 1,952-character anti-bot success, and the post-survey replay's rejected arXiv “No HTML” success row. | None. Keep “historical”; it is not a prevalence estimate. |
| 4 | Runtime reporting aggregates retrieval/read counts, read seconds, and artifacts rather than token, price, whole-agent-wall-time, or human-review cost. | **supported** | `report.py::_runtime_telemetry()` returns only the listed retrieval, read, timing, and artifact fields; it has no model-token, price, total-agent-wall-time, or human-review field. | None. Do not extend this to possible external host logs. |
| 5 | The forward test says two topics are not a general win-rate estimate and records 97 candidate versus 41 baseline artifacts despite equal configured rounds. | **supported** | `openai-v0.5-forward-test.md` states the two-topic limitation and gives the 97/41 cost-audit result. | None. |
| 6 | The July 27 score records 37 rounds, 1,137 retrieved, 72 selected, 97 direct/manual artifacts, and 347.4 reader seconds. | **supported** | The cited `score.json` reports each exact value under `runtime`. | None. |
| 7 | Anthropic reports a production multi-agent system with a 90.2% internal-evaluation gain and about 15× chat-token use. | **supported** | Anthropic's engineering report describes Research's prototype-to-production path, reports the 90.2% internal result, and says multi-agent systems use about 15× chat tokens. | None. Retain “Anthropic reports” and “internal”; this is not independent replication or Aletheia evidence. |
| 8 | Tran and Kiela report single-agent systems matching or outperforming their multi-agent configurations under matched **requested** thinking-token-budget caps, except when single-agent context is sufficiently degraded. | **supported** | The paper's abstract/results/conclusion support the direction and the context-degradation boundary. Its token-accounting appendix says actual token use is opaque and its primary comparison is matched *requested* budget `B`; the revised claim now preserves that qualification. | None. Do not revert to “equal thinking-token budgets.” |
| 9 | The project records lack a general win-rate estimate and a cost-matched, human-calibrated, multi-topic A/B against a bounded single-agent baseline. | **supported** | The forward-test record denies a general win-rate estimate and a human-calibrated multi-topic benchmark; `adversary.md` says no existing Aletheia experiment meets the frozen matched test and no direct cost-matched A/B exists. | None. Scope remains the project/audited records, not unpublished or external work. |
| 10 | With neither a tier nor an explicit budget, the runtime selects unlimited by default. | **supported** | `treestate.py::init_run()` selects `unlimited` when `budget is None` and no named tier is supplied. | None. |
| 11 | Unlimited's synthetic budget, depth, and node backstop are structural settings, not executable quotas for tokens, dollars, elapsed time, or total requests in the audited runtime artifacts. | **supported** | `treestate.py` defines only tree-budget/depth/node settings; the cited `report.py` aggregate contains no resource or cost ledger for the listed quantities. | None. The existing “audited runtime artifacts” qualification is required. |

## Coverage result

The two new rows cover the two factual, load-bearing parts of observation 1 that the earlier
nine-row ledger did not separately state: the no-argument default and the distinction between tree
settings and real resource quotas. The remaining uncited prose in the brief is evaluative or
prescriptive (for example, the recommended default workflow and benchmark), or an inference drawn
from the supported observations; it does not add a separate atomic factual assertion requiring a
claim row.

All 11 ledger claims are semantically supported by their cited sources, and the corresponding
`verify.jsonl` rows were promoted from lexical `relevant` to final `supported` verdicts without
changing their claim text or resolved allowed URL. `report.py audit-claims` then produced a valid,
hash-bound attestation for this exact artifact set (`auditor: fresh-context verifier`,
`claim_count: 11`, `added_claims: 2`); `report.py score` reports `citation_complete: true` and
`citation_accuracy: 1.0`.

added_claims: 2
