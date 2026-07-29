# Blind judgment

## Decision

**Output B wins narrowly (about 0.62 confidence).** Its factual score is 12/20
versus 11/20 for Output A. The difference is not a general-quality or
product-performance finding: it is a small advantage on this frozen packet,
principally because B explicitly qualifies the wrong-body evidence as
historical/non-prevalence evidence and accurately describes the telemetry
boundary. Output A's material advantage is its explicit account of the
bounded-tier round arithmetic.

I treated a rubric item as all-or-nothing: “Missing” includes a partially
correct statement that omits a required part of that distinction. No item was
scored “Wrong”; the shortfalls are omissions or insufficient qualification.
The eight frozen blob hashes matched the supplied fingerprint manifest.

## Factual scorecard

| # | Required distinction | Output A | Output B |
|---:|---|---|---|
| 1 | No tier or budget defaults to unlimited. | **Correct** — states this directly. S2:222–233. | **Correct** — states this directly. S2:222–233. |
| 2 | Unlimited has finite 1,000,000/99/6/512 settings; max has 8/2,048. | **Missing (partial)** — gives all unlimited values but omits max's 8 children and 2,048 nodes. S2:199–207. | **Missing (partial)** — likewise gives only unlimited's values. S2:199–207. |
| 3 | Those settings are not executable global caps on tokens, dollars, agent time, or review. | **Correct** — distinguishes tree controls from money/time/token/decision controls. S2:246–252; S4:229–287. | **Correct** — calls them tree guardrails rather than resource reservations. S2:246–252; S4:229–287. |
| 4 | Saturation is agent-paced, not a deterministic quality certificate. | **Correct** — identifies agent-paced convergence and rejects it as an operator-owned sufficiency test. S1:70–78. | **Correct** — identifies agent-paced convergence and notes no code-enforced saturation stop. S1:70–78; S2:272–289. |
| 5 | Bounded tiers have round/tree arithmetic; the system is not literally structurally infinite. | **Correct** — gives the bounded floor calculation and contrasts it with the unlimited/max round behavior. S1:76–78; S3:495–517. | **Missing (partial)** — says the code does not run forever and describes finite tree caps, but never states bounded-tier round-cap arithmetic. S2:199–207; S3:495–517. |
| 6 | The Python runtime neither makes nor meters host-model calls. | **Missing** — does not state this implementation boundary. The shown runtime paths cover tree state, retrieval, and reporting, not host-model metering. S2:210–252; S3:320–359; S4:229–287. | **Missing** — does not state this boundary. Same source basis. |
| 7 | Telemetry has retrieval/read counts, reader seconds, and artifacts, but no token/dollar/total-run-clock ledger. | **Missing (partial)** — notes artifacts and lack of a single enforcement point, but does not state the telemetry's measured scope and missing token/dollar/total-clock ledger. S4:229–287. | **Correct** — names retrieval/read/read-seconds/artifact totals and correctly frames them as post-run observability rather than a spend/request/deadline control. S4:229–287; S4:462–504. |
| 8 | Channel/reader cost can vary with configuration and optional paid connectors. | **Missing** — no configuration/optional-connector cost qualification. S1:41–50; S6/PORTABILITY:99–118. | **Missing** — no configuration/optional-connector cost qualification. Same sources. |
| 9 | Retrieval fan-out is parallel in the engine. | **Missing** — no parallel-retrieval statement. S3:320–359. | **Missing** — no parallel-retrieval statement. S3:320–359. |
| 10 | Full-text reads are serial within one leaf invocation, not necessarily globally serial. | **Missing** — no serial-per-leaf/global-scheduling distinction. S3:578–612. | **Missing** — no serial-per-leaf/global-scheduling distinction. Same source. |
| 11 | Read success uses a 1,500-character predicate. | **Correct** — states the threshold and its use for _read_ok. S3:376–410; S3:598–609. | **Correct** — states the threshold and its use for _read_ok. Same source. |
| 12 | A long wrong or anti-bot/error body can be counted as successful. | **Correct** — identifies wrong GRADE bodies and an anti-bot page accepted as success. S3:598–609; S5:83–101. | **Correct** — explains why a readable substitute body can pass the length gate; its historical paragraph documents accepted wrong bodies. S3:598–609; S5:37–101. |
| 13 | Wrong-body examples are historical, not a current failure-rate measurement. | **Missing** — calls them operational observations but does not disclose the prior production commit or the explicit non-prevalence limitation. S5:5–7; S5:83–101. | **Correct** — explicitly calls out the 2026-07-27, different-commit record and says it is not a prevalence estimate or replay of the frozen candidate. S5:5–7; S5:37–101. |
| 14 | The identity-gate remediation is separate and unpromoted. | **Correct** — calls the later identity experiment isolated and unpromoted. S5:156–174; S6/BRANCHES:14–19, 121–126. | **Correct** — labels the identity mechanism experimental/unpromoted rather than an audited feature. Same sources. |
| 15 | The audited checkout is an unpromoted candidate while prod is stable. | **Missing (partial)** — calls the target a candidate but never supplies the contrast that prod is stable. S6/BRANCHES:3–19; S6/PORTABILITY:3–7. | **Missing (partial)** — likewise calls it a candidate without stating the stable-prod contrast. Same sources. |
| 16 | The portable runtime is not an OS sandbox or security-certified release. | **Correct** — states this disclaimer. S6/PORTABILITY:3–7, 151–164. | **Correct** — states this disclaimer and its host-boundary consequence. Same source. |
| 17 | Existing positive 0.5 evidence is two favorable capped-triage topics. | **Correct** — accurately limits the forward record to two mechanism-level topics, not a general result. S7:18–42. | **Correct** — accurately describes the consumer and biomedical capped evidence as favorable but limited. S7:18–42. |
| 18 | The dynamic-outline diagnostic was not cost matched: 97 versus 41 artifacts despite equal configured rounds. | **Correct** — gives 97/41, 2.37×, and the equal-round qualification. S7:46–65. | **Correct** — gives the same cost-parity failure accurately. Same source. |
| 19 | The earlier bakeoff is another N=1; collectively the records do not estimate general win rate. | **Missing** — says the current two-topic record is not a general win rate, but omits the earlier one-topic bakeoff and collective denominator. S5:122–134; S7:41–42. | **Missing** — likewise omits the earlier bakeoff, despite correctly noting small-N/model-judged limits. Same sources. |
| 20 | Recommendation is conditional: explicit budgets plus human review; neither blanket rejection nor safe-by-default. | **Correct** — rejects unenveloped high-stakes use while preserving bounded/verified uses and human review. S1:70–78; S7:62–72. | **Correct** — gives the same conditional deployment boundary and explicit human envelope. Same sources. |

**Factual total:** Output A **11/20**; Output B **12/20**.

## Qualitative ratings

For calibration, decision usefulness, and source traceability, 5 is best. For
needless complexity, 1 is least needless.

| Dimension | Output A | Output B | Reasoning |
|---|---:|---:|---|
| Calibration | 4 | 5 | Both reject a blanket conclusion and distinguish structural caps from resource governance. B is stronger because it explicitly bounds the historical wrong-body evidence to what it can show; A leaves that important qualification implicit. |
| Decision usefulness | 4 | 5 | Both reach a clear answer and provide actionable gates. B more compactly separates the strongest favorable case from the remaining deployment boundary, making the residual decision easier to audit. |
| Source traceability | 4 | 5 | Both use claim-level S1–S7 citations with line ranges. B more consistently gives the exact source path alongside the line range and makes the current-code/historical-record distinction visible in the cited prose. |
| Needless complexity | 3 | 2 | A's long gate lists and self-check add some repetition. B is mechanically longer (1,410 file words versus A's 1,228, counting headings and tables), but its added countercase is decision-relevant rather than decorative. This is an overhead observation, not a word-limit compliance finding because the protocol separately permits a source table. |

## Unsupported or overstated-claim notes

- **Output A:** The wrong-body examples are used appropriately as a risk
  mechanism, but their historical status and non-prevalence limit are not
  stated in the answer. A reader could wrongly treat them as measured current
  failure evidence. S5:5–7, 83–101.
- **Output A:** Its detailed envelope and release-gate lists are sensible
  recommendations, not capabilities or requirements demonstrated as already
  enforced by the frozen runtime. They should be read as the answer's policy
  judgment, not as an established implementation fact. S2:246–252;
  S4:229–287; S7:62–65.
- **Output B:** Its envelope and release-gate list is explicitly normative
  (“appropriate” / “I would require”), which is appropriately calibrated. It
  should still not be read as proof that those gates are presently implemented.
  S6/BRANCHES:38–44; S7:62–65.
- **Neither output** invents a dollar amount, model-token count, end-to-end
  latency, general win rate, or a current failure prevalence. That restraint is
  important given S4's telemetry scope and the historical limits in S5/S7.

## Why B wins, and uncertainty

The result is a **narrow B decision**, not a decisive superiority claim. B
adds two decision-relevant qualifications that A omits: the exact
telemetry-versus-enforcement boundary (item 7) and the fact that the
wrong-body evidence is historical rather than a current-rate measurement
(item 13). A, in turn, covers bounded-tier arithmetic that B leaves out
(item 5). The one-point score difference and the qualitative ratings therefore
support only a modest preference for Output B.

## Limitations

- This is a blind comparison of Output A and Output B against the specified
  frozen packet only. It does not identify their underlying conditions,
  authors, workflows, or any wider product property.
- No live retrieval, host-model call accounting, provider billing, scheduling,
  or real deployment behavior was examined; the protocol itself excludes
  those questions.
- S5 and S7 are first-party historical records. They can support documented
  observations and stated limitations, not current prevalence or a general
  effectiveness estimate.
- The code establishes a frozen implementation snapshot and some absence
  claims by inspection; it cannot establish what a host or operator will do in
  an actual consequential investigation.
- The all-or-nothing rubric makes partial coverage score as missing, and the
  1–5 ratings necessarily involve judgment. A different weighting of items 5,
  7, and 13 could reasonably produce a tie rather than this narrow preference.
