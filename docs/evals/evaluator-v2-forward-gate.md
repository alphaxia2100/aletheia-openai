# Evaluator v2: validity, results, and forward gate

Date: 2026-07-10

Branch: `codex/exp-accuracy-eval-v2`

Base: `52aaca93d48a4645ec9da73ba55219268f8af902`

## Bottom line

Evaluator v2 is a useful **fail-closed citation-integrity scorer and evaluation harness**. It is not
yet a release-grade factual-accuracy evaluator and must not select the high-accuracy architecture.

The current 24/24 known-defect result is target conformance by a self-authored judgment file. The
file describes the behavior the eventual evaluator should have; it was not emitted by evaluator code
and was not independently labeled. The result therefore records
`implementation_validated: false` and `meta_eval_passed: false`.

The prior 12-topic sealed set (SHA-256 `c865e76aa07668669c6d26e798676028ea4af374ab4328d11bc08891ec2d4758`)
was exposed in plaintext to the evaluator-development context while tracing fixture references. It is
compromised for this experiment. Do not use it for promotion; create a new externally held set after
the evaluator and candidates are frozen.

## What v2 actually guarantees

1. One canonical scorer. Repository tools delegate citation scoring to the scorer shipped with the
   current skill. The call runs in an isolated subprocess so generic module names from retained
   Aletheia generations cannot contaminate one another.
2. A headline requires a hash-consistent final-answer claim-scope artifact, including on legacy runs.
   Row-level entailment remains visible as a diagnostic, but a missing artifact makes
   `citation_accuracy` null. This is an integrity check, not proof of independent coverage: the
   current auditor identity is an unauthenticated string and omitted claims can still be self-attested
   away. It is therefore not a release gate.
3. Metric names state their semantics. `citation_entailment_precision` is support against submitted
   citation rows. It is not real-world factual accuracy or answer recall.
4. Unmeasured properties stay null: factual accuracy, answer recall, topic-relative source quality,
   probabilistic calibration, temporal correctness, and contradiction recall.
5. Pairwise judging requires exactly one A/B and one B/A call per pair. Missing or duplicate orders
   invalidate the protocol; position-inconsistent results become ties.
6. Judge-visible paths are neutral, raw calls and input hashes are persisted, human anchors are copied
   to neutral A/B files, and the mapping key is written separately with mode `0600`.
7. Judge trust requires at least 30 human anchors, candidate/baseline label diversity, kappa,
   balanced accuracy, macro-F1, per-class metrics, and a Wilson lower bound on agreement.
8. Calibration utilities compute Brier score, log loss, reliability error, AUROC, and selective risk.
   Release probability claims require at least 30 two-class outcomes, provenance attestation, Brier
   <= 0.20, exact-bin ECE <= 0.10, and AUROC >= 0.70. Equal-confidence selective-risk rows are retained
   as atomic groups. Attestation remains caller-controlled, so passing metrics alone do not authenticate
   labels or make this a standalone release gate.

## Evidence and provenance

### Controlled known defects

- Fixture: `docs/evals/fixtures/evaluator-known-defects.jsonl`
- SHA-256: `2ac645d111a7e3ae8c8bcef78cb536833d3321b9eaf64ae6dffb3ecb2e449202`
- Cases: 24 across nine dimensions; several dimensions have only two cases.
- Old judgment artifact: self-authored capability audit, 8/24 correct (0.333).
- V2 judgment artifact: self-authored design target, 24/24 relations match the fixture.
- Implementation/release result: **fail**. Reasons: judgments are not independently adjudicated
  implementation output; fewer than 30 cases; at least one dimension has fewer than three cases.

This 24/24 number must never be presented as measured evaluator efficacy.

### Calibration fixtures

- Fixture: `docs/evals/fixtures/calibration-batches.jsonl`
- SHA-256: `22f3999298ca1346aff9ab4ecf9896e7d1ab10f4346b97b2c9507bfcb93342a8`
- Three synthetic batches contain 16, 10, and 8 outcomes.
- The scorer correctly prefers the intended calibrated/honest predictions and produces the expected
  selective-risk curve.
- All three are explicitly insufficient for a release calibration claim.

### Prior-run rescoring

Strict v2 rescored six existing baseline/candidate runs. Five lose the headline because their final
brief scope audit is absent or invalid. Only the capped-magnesium candidate retains
`citation_accuracy = 1.0`. All six still show row-level entailment precision of 1.0. This demonstrates
the scope gate and also why entailment alone cannot choose an architecture.

### Regression evidence

The untouched base passed 156 tests. The first v2 integration passed its 17 focused tests but failed
three full-suite tests because importing the canonical scorer eagerly mixed current `router` and
`investigate` modules with frozen deep-Aletheia modules. The canonical scorer now executes across a
process boundary. The complete suite then passed 169 tests under Python 3.9.6.

### Freeze-time adversarial findings

An independent read-only review reproduced release-blocking failures against the frozen code:

- A two-claim brief with only one extracted and verified claim can receive `citation_accuracy = 1.0`
  after a self-authored scope attestation. A directly written hash-consistent audit with an arbitrary
  auditor string can also pass. Scoring does not establish independent rendered-answer coverage.
- A caller can set calibration `release_attested` true; sample size and class presence can then mark a
  catastrophically wrong 30-case predictor release-valid because no Brier/ECE/AUROC thresholds exist.
  Equal-confidence selective-risk results are also input-order dependent.
- Pairwise inference excludes ties. A probe with 25 wins, 5 losses, and 100 ties among 130 trusted
  anchors still declared the candidate better; the 77% tie rate did not temper the interval.
- The workflow uses deterministic input mappings, delegates blind copying to the generator, filters
  missing generation results, and does not require the complete expected topic set. Persisted neutral
  paths therefore do not by themselves prove blinding or completeness.
- Prior rescoring references mutable absolute temporary paths, and no immutable complete run plus raw
  judge bundle exists in the committed result set.

These are additional reasons for the NO-GO. They were recorded rather than patched after the one-hour
freeze because safe fixes require authenticated audit provenance, evaluator-owned claim extraction,
tie-aware inference, and orchestrator-owned copy/topic-set enforcement.

## Decisions and rejected alternatives

- **Delegate, do not reimplement, canonical citation scoring.** Three divergent formulas had already
  produced incompatible conclusions. A subprocess boundary costs a small amount of latency but
  preserves cross-generation compatibility.
- **Fail closed on scope.** Legacy compatibility remains an explicit diagnostic mode; it cannot emit a
  release headline.
- **Do not synthesize a universal score from missing dimensions.** Null is more informative than a
  formatting, domain-authority, or confidence-prose proxy.
- **Pre-register calibration quality before another forward set.** Brier <= 0.20 demands material
  improvement over a maximum-entropy 0.25 forecast, ECE <= 0.10 caps mean reliability error at ten
  percentage points, and AUROC >= 0.70 requires useful discrimination. These are minimum gates, not a
  claim of optimal calibration; changing them requires a new evaluator version and forward set.
- **Treat confidence ties as indivisible.** Selective retention happens at observable thresholds, so a
  tied group enters the risk-coverage curve together. Its group-size-weighted right-endpoint risk makes
  discrete AURC invariant to row order without inventing a favorable ordering inside a tie.
- **Do not count self-authored target labels as validation.** Target conformance remains useful for
  specifying behavior, but the CLI exits nonzero for release use.
- **Do not alter router behavior to make integration tests pass.** The failure was namespace
  contamination, not a routing regression.
- **Do not run the exposed sealed set.** A replacement must be generated outside the development
  context after code freeze.

## Gate before any architecture promotion

1. Implement or connect evaluator-owned atomic claim extraction and reconcile it against the rendered
   answer, with source spans and snapshot hashes.
2. Build frozen, topic-specific must-cover and must-not-assert rubrics before generation; score weighted
   information recall and false positives separately from citation precision.
3. Add claim-relative source-role/method/currency judgments, temporal supersession checks, and internal
   plus evidence-conflict contradiction checks.
4. Expand the known-defect set to at least 30 cases with at least three per declared dimension.
5. Run the actual evaluator implementation on those cases, persist its outputs, and obtain independent
   blind human/model adjudication. The provenance-aware defect gate must pass.
6. Calibrate the exact-order pairwise judge on at least 30 diverse human anchors and pass identical,
   padding, concise-rewrite, and content-swap controls.
7. Freeze evaluator and candidate commits. Only then commission a new externally held, domain-balanced
   topic set and run matched budgets/read ceilings. Broad preference remains secondary; promotion
   requires precision and recall gains with no catastrophic temporal or contradiction regression.

## Reproduction

```bash
python3 -m unittest discover -s tests

python3 scripts/eval/defect_meta_eval.py \
  --fixture docs/evals/fixtures/evaluator-known-defects.jsonl \
  --old docs/evals/results/evaluator-v2-old-judgments.jsonl \
  --new docs/evals/results/evaluator-v2-self-authored-design-target-judgments.jsonl \
  --old-provenance self-authored-capability-audit \
  --new-provenance self-authored-design-target
# Expected exit: 1 (target conformance succeeds; implementation/release validation fails closed).

python3 scripts/eval/calibration_score.py \
  docs/evals/fixtures/calibration-batches.jsonl \
  --expect-sha256 22f3999298ca1346aff9ab4ecf9896e7d1ab10f4346b97b2c9507bfcb93342a8
```

## Research basis

The design separates factual precision, citation support, and information recall following
[FActScore](https://arxiv.org/abs/2305.14251),
[ALCE](https://arxiv.org/abs/2305.14627), and
[FactLens](https://arxiv.org/abs/2411.05980); uses controlled errors in the spirit of
[GO FIGURE](https://arxiv.org/abs/2010.12834); treats currentness explicitly following
[FreshQA](https://aclanthology.org/2024.findings-acl.813/); and addresses judge order/verbosity bias
identified by [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685). Proper scoring and selective
risk follow [Language Models (Mostly) Know What They Know](https://arxiv.org/abs/2207.05221).
The need for expert-derived atomic recall rubrics is also reflected in
[DeepResearch Bench II](https://arxiv.org/abs/2601.08536).
