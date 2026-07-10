# Frozen release-evaluation protocol

Status: evaluator v2 is a validated fail-closed **harness**, not yet a calibrated release judge.

## Measurement contract

Report these independently; never collapse them into one “accuracy” number:

| Dimension | Minimum evidence | Fail-closed behavior |
|---|---|---|
| Citation entailment | atomic claim, actual cited span, polarity/scope/magnitude check | `null` without final scope audit |
| Factual truth | independent truth/decisive-primary adjudication | `null` without labels |
| Answer recall | frozen topic-specific required-information rubric | `null` without rubric |
| Source quality | topic-relative role and decisive-primary rubric | `null`; no domain-authority proxy |
| Temporal correctness | dated claim, source/event/version dates, supersession cases | `null` without temporal labels |
| Contradiction recall | frozen known disputes plus internal-consistency scan | `null` without dispute rubric |
| Calibration | outcome/probability pairs, Brier/log loss/reliability | not trusted below 30 labels |
| Holistic utility | blind paired A/B and B/A judgments | inconsistent order becomes tie |

## Evaluator meta-gate

Before it scores an architecture, the evaluator must:

1. Detect every frozen catastrophic defect and retain every correct control.
2. Persist each judgment, shown order, rationale, judge/model identity, prompt hash, output hash, run
   hashes, evaluator commit, and timestamp before aggregation.
3. Require at least 30 human anchors, including at least five baseline and five candidate wins; require
   κ≥0.60, balanced accuracy≥0.70, macro-F1≥0.70, and Wilson agreement lower bound≥0.55.
4. Keep identical reports tied in both orders and repetitive padding from becoming a win.
5. Reject any output lacking a valid final-brief claim-scope attestation.

The 24 known-defect judgments produced during evaluator development are explicitly self-authored
design-target labels. Their 24/24 score versus the legacy evaluator's 8/24 proves the scoring harness
can represent the intended distinctions; it does not calibrate an independent judge.

## Architecture A/B

- Pin baseline/candidate commits and runtime hashes.
- Use identical topic prompts, candidate pools where causal isolation requires them, maximum reads,
  model/writer/verifier, answer-length band, and wall clock.
- Persist actual search passes, attempted/successful/manual reads, source artifacts, origin clusters,
  claim/span state transitions, and termination reason.
- Run both presentation orders. Judge factual dimensions before holistic utility.
- Report per-topic outcomes and regressions; no average may hide a material domain loss.
- Separate matched-read architectural effects from read-scaling curves.

## Held-out integrity

The original 12-topic SHA `c865e76…` is contaminated and forbidden. Its plaintext rows were printed
during evaluator development. Replacement topics and rubrics must be created **after** evaluator and
candidate commits freeze, retained outside all developer contexts, and exposed to generation only as
opaque jobs. Unseal exactly once after outputs, verification artifacts, and judge prompts are frozen.

## Promotion

Promotion requires objective claim/source/temporal improvement or a trusted blind judge win whose 95%
confidence interval clears 0.5, no material tested-domain regression, complete independent final-
answer verification, intended-mechanism telemetry, and valid cap accounting. Otherwise the result is
provisional or no-go. The installed checkpoint remains unchanged.

