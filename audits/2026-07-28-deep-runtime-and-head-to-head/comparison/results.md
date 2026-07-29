# Controlled output comparison — revealed result and post-audit correction

## Corrected conclusion (authoritative)

The original blind judgment recorded a narrow preference for Output B, 12/20 versus 11/20. An
independent method audit found that rubric row 17 incorrectly credited Output B with naming two
favorable capped-triage topics: it names only the biomedical test. Applying the rubric's stated
all-or-nothing rule changes the factual score to **11/20 versus 11/20**.

The defensible result is therefore a **tied, one-judge frozen-source exercise with a recorded
qualitative preference**, not a demonstrated Aletheia win. The original
[blind judgment](blind-judgment.md) is intentionally preserved as the historical pre-correction
record. See the exact evidence, score correction, and design limits in the
[independent method audit](independent-method-audit.md) and the compact
[corrected-result.json](corrected-result.json).

The blind judgment was completed before this mapping was revealed. The local random assignment was:

| Blind label | Actual condition |
|---|---|
| Output A | Direct bounded baseline |
| Output B | Aletheia protocol condition |

The original blind record preferred **Output B narrowly**, at 0.62 confidence, with a recorded 12/20
factual score versus 11/20 for Output A. The corrected score above supersedes that factual result;
the recorded preference remains only a qualitative observation from one judge.

## Why the original judge preferred Output B

The original qualitative preference was not based on breadth, citation count, or a claimed truth score.
The judge credited Output B for two useful qualifications:

1. it explicitly treated the wrong-body incidents as historical, different-commit evidence rather than
   a current failure-rate estimate; and
2. it separated post-hoc telemetry from a runtime spending/stop boundary.

Output A was better on bounded-tier round arithmetic. Neither answer covered every rubric distinction;
both omitted the host-model implementation boundary, paid-connector variation, parallel retrieval,
serial per-leaf reads, max-tier settings, and the earlier one-topic bakeoff. The original scorecard's
row-17 credit was wrong, so these qualitative observations do not break the corrected factual tie.

## Process and visible overhead

| Measure | Direct bounded baseline | Aletheia protocol condition |
|---|---:|---:|
| Authoring roles | 1 author with 1 self-check | 4 leaf workers + 1 synthesizer + 1 fresh reviewer |
| Unique frozen packet documents | 8 | 8 |
| Declared document-read assignments | 8 source documents | 12 leaf assignments + 8 synthesis reads + 8 reviewer reads = 28 |
| Final prose words (excluding source table) | 1,182 | 1,297 |
| Rendered file words / bytes | 1,228 / 9,180 | 1,410 / 11,133 |
| External retrieval | none | none |

The assignment count is an auditable process-overhead measure, not a model-token or dollar-cost
measurement. The host exposes neither tokens, cache state, model price, nor comparable wall-clock
timing. It would be false to call this cost matched. The structured condition spent substantially more
orchestration and repeated source reading without a demonstrated factual-score advantage.

## Interpretation

This is the most charitable credible reading for Aletheia: its adversarial decomposition and fresh
review may improve calibration on a difficult audit-style synthesis. It is not evidence that the
workflow is generally better, faster, cheaper, or worth its overhead for ordinary research. A strong
bounded single agent reached the same decision and tied 11/20 factual coverage after correction.

The result therefore supports only a retestable hypothesis, not the present default. The multi-agent
protocol may be justified when its safeguards are independently shown to add material calibration, but
this test did not establish that they do. It has not earned default `unlimited` use, a general
output-quality claim, or a quality-per-dollar claim.

## Controls and limits

- Both answers used the same eight local documents at frozen commit
  `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`; all eight blob hashes matched
  [source-fingerprints.json](source-fingerprints.json).
- The Aletheia condition used a real initialized/split tree and four source-separated worker findings,
  but retrieval was deliberately bypassed to isolate orchestration and synthesis. Its runtime gate
  passed with four non-thin children; no source records were injected, so this is not an end-to-end
  retrieval or `report.py score` test.
- The direct condition had one author and one self-check. The Aletheia condition had a fresh reviewer.
  That is intentional protocol overhead, not equal-resource parity.
- This is one task, one source packet, one model family/environment, and one blind judge. The judge was
  allowed a tie; a different weighting of its all-or-nothing rubric could reasonably have tied the
  outputs.
- No pre-execution commitment, isolated workspace, judge transcript, model telemetry, or end-to-end
  retrieval/verification record was retained. The saved artifacts support a hand-executed
  source-packet synthesis exercise, not independent blinding or actual runtime performance.
- No claim follows about live retrieval quality, latency, dollar cost, host scheduling, human-review
  quality, or a general Aletheia win rate.
