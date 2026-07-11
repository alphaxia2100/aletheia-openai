# High-accuracy v0.6 experiment results

Updated: 2026-07-10  
Promotion status: **NO-GO pending independent evaluation**

## Frozen artifacts

| Artifact | Branch / commit | Evidence | Status |
|---|---|---|---|
| Stable Codex release | `codex/openai-aletheia-v05` / `addfaf6` | tagged, installed, clean | retained |
| Evaluator v2.1 | `codex/exp-accuracy-eval-v2` / `a80a387` | 183 tests; 14 new P0 regressions | harness only |
| Runtime ledger | `codex/exp-runtime-ledger-v06` / `087a228` | 160 tests | plumbing candidate |
| Claim/evidence ledger | `codex/exp-claim-evidence-ledger-v06` / `35fb82a` | 164 tests | architecture candidate |
| High-accuracy integration/docs | `codex/high-accuracy-aletheia-v06` | architecture/research/eval logs | not installed |

## Aletheia research run

Run: `/tmp/aletheia-high-accuracy-design/2026-07-10-174547-high-accuracy-research-architecture`

- Runtime pinned to checkpoint `addfaf6` with hashes in `run.json`.
- 4 evidence framings, 6 completed agent rounds, 7 retrieval passes.
- 222 retrieved records, 214 unique candidates, 20 engine read attempts, 19 successes.
- 69 persisted read artifacts; 62 were direct/manual primary chases.
- 168 retrieved sources reduce to 167 structural origins (`origin_echo_ratio=0.006`).
- Brave was degraded; other web, academic, repository, and direct-primary paths were used.
- Full brief completed. The writer initially extracted 16 claims; a fresh-context verifier found 17
  additional load-bearing claims, producing 33/33 supported claims after correcting one monotonicity
  overstatement and one percentage-point ambiguity. Final citation coverage/precision are 1.0/1.0;
  the content-hashed claim audit is valid. The 4.96 MB full bundle is persisted as `bundle.md`.

## Evaluator finding

Legacy evaluation is not safe for optimization: it misses claim extraction, answer recall, source
role/origin, order, verbosity, contradiction, and scope-audit defects. Evaluator v2 fixes metric
semantics, mandatory scope audit, paired order handling, anchor sample/diversity requirements,
calibration scoring, and artifact persistence. It deliberately reports truth/recall/source/time/
contradiction dimensions as `null` without external labels.

The known-defect improvement is **not** an efficacy estimate: v2's target judgments were authored by
its developer against the fixture. A base-regression audit also caught and fixed evaluator-induced
Python import contamination; untouched base had 156/156 tests passing and the corrected evaluator
worktree has 169/169 on Python 3.9 and 3.12.

An independent freeze review found additional P0s: scope coverage remains self-attested and forgeable;
calibration attestation is caller-controlled and lacks quality thresholds; tied-confidence AURC is
order-dependent; tie-heavy results can discard most topics yet claim a win; the workflow still permits
agent-owned blind copies and silent topic omission; and complete run/judge bundles are not immutable.
These are documented on the evaluator branch in `docs/evals/evaluator-v2-forward-gate.md`.

Continuation hardening fixed the five executable reproductions: scope/cardinality and exact
claim+URL reconciliation; SHA-pinned canonical brief/topic matrices; release-default persistence;
calibration quality thresholds; grouped equal-confidence AURC; and a 50% decisive-topic floor. All
183 tests and 14 P0 tests pass. Release remains NO-GO because pins/labels are unsigned, semantic claim
completeness and auditor independence remain procedural, calibration gates lack external validation,
and remote judge execution is unauthenticated.

## Candidate findings

The runtime branch removes two confirmed defects: agent `--reads` is honored and browser
`--max-chars 0` stays unlimited. It atomically reserves engine-managed searches/reads before I/O and
decouples source reads from the tree scrutiny unit. It does not claim higher answer quality.

The claim-ledger branch makes support fail closed unless an exact quote is present in a SHA-bound read
artifact and an independent verdict completes required polarity/scope/numeric/temporal checks.
Claim-specific origin requirements, disputed state, priority ordering, immutable history, and fresh
challenge/confirmation stops pass targeted tests. It still relies on independent judgment for claim
atomicity, complete claim extraction, correct origin keys, and cherry-pick resistance.

## Selection decision

Neither candidate is promoted. The original forward set is contaminated, the evaluator lacks
independent labels, and no matched-read end-to-end comparison exists. The next valid action is to
freeze evaluator/candidate commits, commission an externally held replacement set and rubrics, then
test the claim ledger first. Passage reranking, citation chasing, and outline patching remain later
orthogonal ablations.

## Runnable user-test candidate

`codex/high-accuracy-candidate-v06` now composes the runtime and claim/evidence mechanisms as the
separate `aletheia-research-accuracy 0.6.0-accuracy.1` skill. It passes 172 tests, defaults to the
3,600-second/40-per-round/640-total envelope, fails closed on an empty ledger, and ships a structural
run grader. It is installed beside the stable skill for a user-supplied forward test; it remains an
experimental candidate until semantic grading is complete.
