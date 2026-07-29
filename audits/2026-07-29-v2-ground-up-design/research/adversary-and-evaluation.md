# Adversarial design, evaluation, and migration review — Aletheia v2

**Status:** design-review input; not an implementation plan or performance claim
**Author role:** adversarial reviewer
**Date:** 2026-07-29
**Question:** What must v2 prove before it replaces a bounded direct research workflow?

## Executive judgment

**Do not begin by rebuilding the current multi-agent tree.** Build a small bounded evidence-run kernel and a pre-registered evaluation harness in parallel. The first usable product should be a single accountable lead agent that cannot spend beyond an explicit envelope, cannot turn an unbound response body into evidence, and cannot advance state by editing ordinary files. It must be able to end honestly as "budget exhausted", "identity unresolved", or "insufficient evidence".

This is deliberately less dramatic than a recursive research swarm. It is the only sequence that can show whether extra machinery earns its cost. The present evidence does not establish a general quality benefit for decomposition, adversarial branches, or a fresh verifier at matched resources. The only controlled source-packet comparison corrected to an **11/20 versus 11/20 tie**, while the structured condition used 28 declared document assignments versus 8 for the direct condition. Those mechanisms are hypotheses to test, not defaults.

Recommended order:

1. Build the authority boundary, typed evidence/claim ledger, resource broker, crash-safe workflow, bounded single-lead path, and fixture/evaluation harness.
2. Shadow-test the v2 core against an immutable bounded direct baseline under identical source and resource conditions.
3. Add independent verification, adversarial retrieval, and decomposition one at a time only after predeclared cost-matched ablations show a durable benefit.
4. Defer default fan-out, autonomous saturation, authenticated browser research, generic plug-ins, cross-run memory that influences answers, distributed orchestration, and self-modifying policies.

The point is not to prove multi-agent research impossible. It is to make a complex workflow falsifiable rather than preserving it because the trace looks rigorous.

## Method and confidence labels

This review inspected the frozen runtime candidate bd5e1a50a491ee7c5ebe1382ace35c21f7909de5, the line-level audit committed at c66c182, the current portable source closure, and the historical evaluation code and records.

- **[Observed]** means reproduced in the audit or directly visible in source.
- **[Derived]** follows mechanically from observed behavior or from a specified experiment.
- **[Recommendation]** is engineering/product judgment, not a claimed benchmark result.
- **[Policy placeholder]** is an explicit starting threshold that must be locked before a run; it is not a scientific constant.

Channel health for this investigation: 11/13 core channels were live. Brave was degraded without a key and Reddit was live-but-empty/degraded. This memo therefore relies mainly on reproducible local audit/source evidence; it does not turn a date-specific web search into a quality result.

## What the audit actually establishes

| Observation | Evidence | Proper inference |
|---|---|---|
| A long wrong body can count as a successful read. | Hermetic wrong-body probe; the reader persists a note and marks it usable from body length. | **[Observed]** provenance failure; not a prevalence estimate for live providers. |
| Parallel/resume tree state is not transactional. | Reproduced stale split, bogus-answer gate, global-index, duplicate-QID, and node-cap race probes. | **[Observed]** integrity risk under retry/concurrency; not proof every sequential run corrupts. |
| "Unlimited" is not a resource contract. | No run-wide cap for host tokens/dollars, total time, requests, reads, browser use, or human review. | **[Observed]** no enforceable economic/deadline guarantee; not a measured dollar cost. |
| Cross-leaf rereads are implicit. | Two leaves read the same source twice while the global index had one URL. | **[Observed]** amplification mechanism; deliberate independent rereads can be legitimate if explicit and charged. |
| Current output superiority is unproved. | Corrected controlled result is 11/20 vs 11/20; conditions were not resource matched and bypassed live retrieval. | **[Observed]** no general win has been shown; not proof that decomposition can never help. |
| Regression tests are meaningful but bounded. | 186 hermetic tests passed in the prior audit. | **[Observed]** deterministic behavior is tested; host-model quality, live-web reliability, and spend remain unproved. |

The full evidence is in the [deep runtime audit](../../2026-07-28-deep-runtime-and-head-to-head/report.md), its [skeptical validation](../../2026-07-28-deep-runtime-and-head-to-head/findings-validation.md), the [runtime adversarial addendum](../../2026-07-28-deep-runtime-and-head-to-head/runtime-adversarial-addendum.md), and the [corrected comparison](../../2026-07-28-deep-runtime-and-head-to-head/comparison/results.md).

### The core architectural implication

V1's problem is not merely that it has many files. It is that the same worker expected to obey a gate can write many artifacts that represent gate success. A mutable directory, status file, Markdown findings, and append-looking JSONL are not an authority boundary if the model can edit them.

The audit's examples are structural:

- tree caps use check-then-create behavior without a transaction or lease;
- global source uniqueness is read then later appended, allowing a race;
- synthesis enumerates on-disk children rather than one declared immutable plan revision;
- text is stored under a requested-URL-derived filename and treated as usable based on length;
- later verification can locate that note by the same short URL hash rather than proving that its embedded body belongs to the claimed work.

V2 should not add more prompts around these conventions. It should move state, budget, identity, and capability decisions to a controller that ordinary workers cannot mark successful by writing a file.

## V2 design premise: separate authority from reasoning

A credible v2 separates three planes.

| Plane | Question | Worker may do | Controller/ledger must do |
|---|---|---|---|
| Execution/control | What work is permitted, leased, complete, failed, or canceled? | Propose a transition. | Validate and atomically apply it. |
| Evidence/provenance | What bytes were fetched for what intended source, through which method and at what time? | Request a fetch and inspect returned evidence. | Bind request, receipt, content hash, identity state, and use policy. |
| Reasoning/content | What does evidence mean and what claim should appear? | Draft claims, uncertainty, and questions. | Record a stable claim denominator and verification status. |

This is the minimum useful meaning of "auditable." It does not make a model truthful. It makes false provenance, hidden spending, state skips, and missing verification visible and more difficult to launder into a green result.

### Threat model that must be stated

V2 can defend against ordinary retries, connector failures, stale/redirected bodies, duplicate deliveries, accidental overspend, and a model trying to satisfy a workflow by manipulating its own artifacts. It cannot defend against a user/administrator who controls the controller database, code, and model host. If workers have raw filesystem/database/tool credentials, the ledger is a convention, not an integrity boundary.

**[Recommendation]** Make the controller a narrow API/service even if it runs locally. Workers receive scoped capability tokens; raw content is append-only/content-addressed; fetches go through a broker. Do not call this a sandbox or cryptographic guarantee unless deployment really provides those boundaries and keys.

## The smallest useful v2: a bounded evidence run

The first release need not have a tree. It needs one lead, a finite plan, optional metered verification, and a clear audit card.

~~~mermaid
flowchart LR
  U["User request + chosen envelope"] --> C["Run controller / immutable manifest"]
  C --> P["Lead proposes typed work"]
  P --> C
  C --> B["Capability + budget broker"]
  B --> F["Fetch adapter"]
  F --> L["Content store / source receipt / identity result"]
  L --> C
  C --> W["Lead drafts atomic claims"]
  W --> V["Independent verifier (optional, metered)"]
  V --> C
  C --> O["Brief + audit card: complete / abstain / exhausted"]
~~~

The directions matter. A lead can request a source; it cannot simply declare that it read the desired primary. A verifier can assess a claim; it cannot silently alter the authoritative claim set. The controller persists terminal outcomes through a crash.

### Minimal typed contracts

These are deliberately small contracts, not an invitation to build a general knowledge graph.

| Object | Minimum immutable fields | Why |
|---|---|---|
| RunManifest | run ID, code/config hashes, model/harness IDs, user authorization, envelope, policy version, creation time | Pins what was allowed before results are known. |
| BudgetEnvelope | deadline; reported model tokens/cost if host supports them; request/read/byte caps; active-worker and browser limits | Turns a tier into an enforceable contract or explicitly says what cannot be metered. |
| WorkItem | immutable ID, parent/plan revision, purpose, allowed capabilities, reserved budget, lease owner/expiry, idempotency key | Replaces mutable directory state and duplicate scheduling. |
| FetchIntent | target URL/entity, expected identity fields, redirect policy, reason, requesting work item | Separates what was meant from what returned. |
| FetchReceipt | intent ID, final URL/redirect chain, method, status/content type, timestamps, byte/content hashes, extraction version, failure state | Creates an auditable record for every attempt, including failure. |
| IdentityAssessment | expected and observed DOI/PMID/arXiv/Git revision/title/authors, match class, explanation, policy version | Prevents body length from masquerading as document identity. |
| EvidenceObject | immutable content hash, receipt ID, truncation, eligibility, sensitivity/retention policy | Enables reuse without pretending duplicate bodies are independent evidence. |
| Claim | atomic scoped text, time qualifier, cited evidence IDs, risk class, revision | Gives verification a fixed denominator. |
| Verification | claim revision, evidence/passage IDs, verdict, rationale, verifier/model lineage, conflict state | Separates semantic support from lexical overlap. |
| RunEvent | monotonic sequence, causal parent, actor/capability, event type, payload hash, controller timestamp | Supports recovery and postmortem reconstruction. |

Human-readable Markdown remains an export. It is not authoritative for state, resource consumption, identity, or a claim verdict.

### Source identity: four independent facts

Replace the overloaded v1 "read OK" boolean with four separate states:

1. **Transport/extraction:** Was content received? Was it blocked, rendered, truncated, or browser-derived?
2. **Identity:** Does it match the intended work/entity? Immutable typed IDs are stronger than title similarity.
3. **Eligibility:** May it support this category of claim? A firsthand post can support a labeled case but not a prevalence estimate.
4. **Entailment:** Does a cited passage support the scoped claim? This is a semantic evaluation, not identity.

Only "matched" identity, or a documented human override, may become normal evidence. "Unknown" can be a lead or a human-review item; "mismatch" is quarantined. A final URL equal to the requested URL is not enough, because stale browser extraction and wrong upstream bodies are exactly the failures already reproduced.

For changing web material, retain content hash and sufficient receipt metadata subject to legal/privacy retention policy. Do not convert a private browser-session body into ordinary reusable corpus data by default.

### State and concurrency: boring transactional mechanics first

**[Recommendation]** Start with one controller process and SQLite in WAL mode, or an equivalently transactional embedded store. Keep large raw bodies in a content-addressed store and hashes/metadata in transactions. This is safer and more inspectable than starting with a queue, graph framework, distributed event bus, plug-in registry, and worker fleet.

Required semantics:

- apply transitions only if run/work/plan revision matches the expected value in one transaction;
- lease work with owner, expiry, attempt number, and idempotency key;
- reuse the idempotency key on retry rather than create a second logical fetch or charge;
- reserve budget before a model/tool action; reconcile afterward; no action spends against a negative balance;
- make synthesis query active work IDs from the declared plan revision, never arbitrary child directories;
- persist crash states as leased/expired/failed and make resume a visible charged policy decision;
- keep an application-level append-only audit log, while honestly acknowledging that local administrators can still alter storage.

### End-to-end resource control

A real envelope separately caps:

- total deadline and per-operation timeouts;
- model calls and input/output/reasoning tokens or money only where host/API telemetry exists;
- connector requests, fetch attempts, selected reads, browser actions, and response/evidence bytes;
- active worker count and queue depth;
- retry attempts and intentionally independent rereads;
- maximum evidence bytes allowed into a later model context.

If the host cannot report tokens/cost, v2 says so: "token/dollar cap unavailable in this host; bounded by time, requests, reads, and bytes." It cannot advertise a cost promise it cannot enforce. There should be a planned/reserved ledger and an actual/reconciled ledger. A logical round count is neither.

No "unlimited" label should survive. A user can choose a large finite envelope with a visible maximum; the system must still finish in a terminal state.

### Default user path

The ordinary path is:

1. Scope request and display finite envelope.
2. Gather a small candidate set through permitted connectors.
3. Fetch a limited number of identity-eligible sources and store receipts.
4. Draft atomic claims, gaps, and uncertainty.
5. Run one scoped verification pass only if policy says it pays for itself.
6. Return an audit card: used/remaining budget, identity states, claim verdict counts, degraded channels, and reviewer provenance.

This can be useful without a recursive research tree. High-stakes investigation is an explicit bigger-envelope mode, not a surprise default.

## Build now, defer, and refuse

| Capability | Decision | Rationale and promotion condition |
|---|---|---|
| Immutable manifest, finite envelope, terminal stop states | **Build now** | Direct remedy for the resource-contract failure. |
| Controller-mediated transitions, leases, idempotency, declared plan revision | **Build now** | Direct remedy for replay/race/QID failures; must pass fault injection before parallelism. |
| Typed fetch receipt, identity assessment, content-addressed cache | **Build now** | Direct remedy for wrong-body/stale-body and hidden rereads. |
| One lead and one bounded evidence pass | **Build now** | Establishes a useful default and the necessary practical baseline. |
| Claim ledger and audit-card export | **Build now** | Makes coverage/verification measurable; does not claim truth. |
| Fixture/replay/evaluation harness | **Build now, in parallel** | Prevents v2 being justified by anecdotes/self-judging prose. |
| Independent verifier | **Feature flag** | Compare against giving the lead exactly the same resource budget for self-check. |
| Adversarial/counterevidence pass | **Feature flag** | Keep only if it improves decisive contradiction handling at fixed budget. |
| Origin clustering | **Diagnostic only** | It can flag echo but cannot prove independent truth; test false merges/splits. |
| Parallel fetches with per-connector limits | **Later** | Only after receipts, global caps, cancellation, and rate limiting are solid. |
| Multi-agent decomposition/tree | **Defer** | Present evidence is tied/unmatched; direct port would inherit v1's most serious state risk. |
| Dynamic splitting/adaptive effort controller | **Defer** | Must beat a simple fixed plan at equal resource before becoming a foundation. |
| Authenticated browser/session reading | **Defer and isolate** | Audit reproduced stale-session provenance risk; requires separate consent/retention review. |
| Cross-run memory that affects answers | **Defer** | Creates poisoning, staleness, provenance, and deletion problems. |
| Generic connector/plugin execution | **Defer** | Each connector is part of evidence/security boundary, not a harmless extension. |
| Autonomous self-modification/prompt promotion | **Do not build in v2** | It invites metric gaming before the evaluator is trustworthy. |
| Distributed workflow platform/framework migration | **Do not build initially** | A single transactional controller is enough until measured recovery/throughput need exists. |

## Pre-registered evaluation harness

### Immutable baseline and protocol

The baseline is not a weak old prompt. It is a pinned runnable condition with exact code/prompt/config/model/harness manifest, fixed default and escalation envelopes, source-access condition, resource receipts, and output hashes. It must be competent. Do not weaken it to make v2 seem necessary.

The audit comparison illustrates why: one direct author/self-check was contrasted with four leaf workers, a synthesizer, and a fresh reviewer. Corrected factual coverage tied. A valid causal test separately compares:

- one bounded direct lead;
- v2 bounded single lead;
- bounded lead plus verifier;
- bounded lead plus adversary;
- multi-leaf variant;

with equal global resource envelopes and the same source condition.

### Three evaluation tracks

| Track | Input | Question | Passing result | Does not establish |
|---|---|---|---|---|
| A. Deterministic integrity | synthetic pages, controlled adapters, injected crashes/races | Does the runtime enforce contracts? | Exact invariant holds across fixture matrix. | General answer quality/live-web reliability. |
| B. Frozen research packets | versioned corpus, reference/claim annotations, frozen retrieval results | Does a workflow improve calibrated/correct output at equal budget? | Reproducible paired quality/cost result for these strata. | Fresh-web discovery/provider uptime. |
| C. Live shadow | time-stamped real requests, same time window, health receipts | Does it behave operationally with current connectors? | Evidence for a deployment cohort. | Timeless general performance ranking. |

Keep A in CI. Run B for material policy/controller/prompt changes. Run C on a scheduled, approval-gated basis and publish channel health rather than treating web drift as noise.

### Task strata that attack the design

The current topic inventory is only a seed. Held-out tasks must be tagged by expected source types, answer risk, temporal sensitivity, and failure mode.

| Stratum | Required cases | Main measures |
|---|---|---|
| Narrow factual lookup | exact official primary plus deceptive near-match | entity/identity precision, answer accuracy, cost floor |
| Technical implementation | docs, releases, repository revisions, version ambiguity | version identity, actionable correctness, passage support |
| Contested evidence synthesis | real disagreement and misleading secondary summaries | counterevidence recall, calibration, harmful overclaim rate |
| Consumer/lived experience | firsthand evidence relevant but not prevalence evidence | evidence-type labeling, no invalid generalization |
| Policy/current affairs | changing sources, dates, official/commentary conflict | temporal qualification, timestamp identity, correct abstention |
| Mixed domain | two valid specialist source families | specialist coverage, no cancellation of both domains |
| Insufficient evidence | no honest answer within envelope | appropriate abstain/escalate versus fabricated closure |
| Adversarial provenance | wrong body, redirect, stale browser body, duplicate aliases, injection | mismatch containment and trace completeness |
| Recovery/load | crash reserve/fetch/commit, duplicate delivery, lease expiry, throttling | exactly-once logical outcome and no double charge |

Seal tasks, source packets, rubric, model config, randomization, baseline, and evaluator before candidate outputs are visible. Split by task **and source packet**, not merely prompt wording. A packet used for iterative prompt tuning is not held out.

### Resource matching is a vector

Record both hard cap and actual use:

- model input/output/reasoning tokens and provider cost where available;
- model/tool calls, worker count, cache hits, retry count;
- retrieval/full-read attempts, bytes, browser actions, connector units;
- start/end/queue time, p50/p95 latency, deadline exits;
- unique content objects, intentional rereads, and context bytes sent to each role;
- human-review minutes where protocol invokes people.

Run two different regimes rather than conflating them:

1. **Fixed-budget effectiveness:** same hard envelope; asks whether a mechanism allocates scarce resources better.
2. **Quality-at-cost frontier:** sweep declared envelopes; asks whether extra quality is worth extra resource.

Never claim a quality win from unmatched resources. The historical dynamic-outline test had equal configured rounds yet 2.37x observed read artifacts. Rounds and source count are not a cost metric.

### Metrics that resist easy gaming

| Dimension | Measurement | Anti-gaming rule |
|---|---|---|
| Atomic correctness | human/expert/reference adjudication: correct, incorrect, unverifiable, omitted | Citation presence earns no automatic credit. |
| Citation entailment | blinded review of scoped claim against cited passage | Keep source identity separate from semantic support. |
| Claim coverage | required/decisive claim inventory versus output | Precision cannot be inflated by saying almost nothing. |
| Calibration/abstention | confidence/uncertainty and correct exhaustion decisions | Penalize unjustified certainty and needless abstention separately. |
| Counterevidence | recall of preannotated decisive contradictions | "Some disagree" without substance is not a pass. |
| Provenance | identity precision/recall, mismatch containment, receipt completeness | Wrong-body acceptance is an integrity failure even if prose is accidentally right. |
| Independence | known-origin fixture false merge/split; concentration display | Diversity is a diagnostic, not a truth score. |
| Operations | completion, duplicate work/charge, recovery, timeout behavior | Fault injection counts, not only happy-path telemetry. |
| User utility | blinded decision usefulness/clarity under output cap | Do not reward verbosity by default. |
| Resource | actual/cap-relative vector | A cap breach fails even if output looks strong. |

Model judges can scale annotation, but are not ground truth. Use them as secondary raters after calibration against a fixed human/expert anchor set. Preserve prompts, versions, order randomization, rationales, and disagreements. The existing judge code has good instincts (blind pairwise comparison, ties, Wilson intervals, human-calibration gate), but its raw win rate excludes ties. V2 should report the complete three-way outcome and a predeclared utility analysis; many ties must not turn into a misleading high decisive-win rate.

### Statistical contract

Before execution, lock:

- task strata and hidden test partition;
- paired unit and stochastic replicate plan;
- error taxonomy and adjudicator protocol;
- primary endpoint and noninferiority/superiority margins;
- timeout, abstention, missing-run, and cap-breach scoring;
- interval/test and multiplicity method;
- exact keep/revise/revert rule.

Report paired differences and uncertainty, not only judge preference. Report every stratum. A system that improves verbose technical synthesis while degrading identity on ordinary lookups has not won a general research benchmark.

Do a pilot to estimate variance, then size the held-out study for the stated minimum useful effect. For rare integrity defects, zero clean events are weak evidence: zero failures in n independent trials yields only an approximate 3/n 95% upper bound on failure probability. Thirty clean live runs therefore do not substantiate five-nines. Deterministic safety needs exhaustive/property/fault testing; operational reliability needs extensive exposure and a defined threat model.

## Fixed-budget ablation ladder

Every row fixes model, source-access condition, deadline, token/tool/read envelope, and output limit unless the row explicitly studies a frontier.

| Step | Addition | Matched control | Hypothesis | Keep only if | Kill/defer if |
|---|---|---|---|---|---|
| 0 | Bounded v2 single lead | bounded direct baseline | safer kernel is not worse by itself | integrity gates pass and primary quality is noninferior inside cap | safety plumbing causes unacceptable regressions; simplify before adding agents |
| 1 | identity receipts/eligibility | same lead, fixture adapters | wrong/stale bodies cannot become evidence without blocking known-good sources | mismatch fixture containment is perfect and known-good recall acceptable | policy becomes a brittle title matcher or length fallback |
| 2 | global cache plus explicit reread policy | local rereads | removes accidental duplicate work | lower resource use without evidence regression; duplicates always have reason/charge | reuse contaminates roles or hides a requested independent review |
| 3 | independent verifier | lead receives verifier's exact budget for self-check | separate review reduces material error | preregistered error rate falls at equal resource and judge is human-calibrated | it rubber-stamps, merely lengthens prose, or uses uncounted context |
| 4 | adversarial retrieval | extra lead retrieval under same budget | finds decisive contradictions | counterevidence recall rises or harmful overclaim falls | irrelevant contrarian noise or duplicate sources dominate |
| 5 | origin clustering | raw source list | flags echo correctly | known-origin fixtures show acceptable false merge/split and reviewers improve | used as a fake numeric truth proof |
| 6 | two/three scoped workers | single lead with same total allocation | decomposition improves a specified stratum | preregistered quality win within same global cap | tie/loss, hidden extra resources, or coordination failures |
| 7 | adaptive planning/splitting | fixed work plan | adapts finite budget better | improves fixed-budget frontier across held-out strata | self-reported uncertainty selects more work without benefit |

### Suggested promotion gates

These are **[Policy placeholders]**, deliberately visible rather than hidden after-the-fact rationales.

1. **Integrity:** zero violations of identity eligibility, budget reservation, or state-transition invariants in deterministic adversarial fixtures. Quality cannot waive this.
2. **Default path:** lower confidence bound for material-claim correctness is no worse than a small locked noninferiority margin (for example 2 percentage points), while staying inside baseline cap. This example margin must be justified per domain.
3. **Expensive optional feature:** lower confidence bound exceeds a locked meaningful benefit in material-error reduction or decisive-counterevidence recall, and it remains inside advertised cap. A one-topic qualitative preference is not enough.
4. **Operational:** no duplicate logical fetch/charge, stale plan work in synthesis, or successful final brief after a critical unresolved identity/verification state.
5. **Evaluation integrity:** tasks, baseline, rubric, evaluator, and random mapping are sealed before outputs; an independent reviewer can reconstruct blinding and resource receipts after unblinding.

Initial fixtures must include: long wrong body; redirect/entity mismatch; title/DOI conflict; stale browser extraction; prompt injection in source text; aliases/mirrors; duplicate idempotency key; crash after reserve/before commit; racing plan updates; cap hit during retry/verification/export; delayed/missing model telemetry; explicit reread charged once; and a legitimately short official source so v2 does not reinvent a hidden length rule.

## Release rings and keep/revert discipline

### Ring 0 — contracts and replay

No open web. CI runs deterministic, property, fuzz, crash/restart, and event-replay tests. Exercise valid and invalid transitions. Replaying events into an empty store must produce the same materialized state and content hashes. No user-facing high-stakes claim.

### Ring 1 — offline blinded comparison

Use frozen source packets and a pinned model/harness. Compare bounded v2 core versus immutable direct baseline at equal envelope. Independent adjudicators inspect atomic claims/citations. Model judges are calibrated, not trusted by assertion. Publish failures and actual resources; do not rerun timeouts until a favorable result appears.

### Ring 2 — live shadow

Run matched conditions on time-stamped requests without making v2 sole advice. Capture/cache responses under retention policy. Report health, provider change, queue time, retries, identity mismatch, and telemetry availability. Compare only same-window/source-access conditions.

### Ring 3 — bounded opt-in beta

Default tier remains finite and displays envelope. Final audit card distinguishes complete, complete-with-gaps, budget-exhausted, identity-unresolved, and abstained. Kill switch routes to pinned bounded direct mode or human review if controller/receipt/budget services degrade. No automatic browser access, invisible memory, or autonomous escalation.

### Ring 4 — explicit investigation mode

Only after individual ablations pass can v2 expose an adversary, extra verification, or parallel specialists. The UI says maximum envelope and the measured assurance benefit. High-stakes use also needs domain policy, human-review path, privacy/retention controls, and a domain-specific error study. More agents are not a high-stakes control.

Every feature gets an experiment card before implementation:

~~~
Hypothesis:        [mechanism] improves [metric] in [stratum].
Baseline:          immutable manifest/hash.
Budget:            exact resource envelope(s).
Endpoint:          metric, denominator, pass margin.
Safety invariants: gates that cannot be traded away.
Decision rule:     keep / revise / revert.
Owner + expiry:    reviewer and flag-removal date if inconclusive.
~~~

Failed or inconclusive features are disabled and preserved as negative results. Do not retain them because a trace was impressive or one judge liked an anecdote.

## Migration: do not convert v1's mutable state into v2 authority

### Phase A — freeze v1

Pin its executable closure, channel config, known limitations, audit artifacts, and evaluation code by hash. Keep runs readable/exportable but label their provenance as v1 semantics. In particular, a v1 read-success marker is not retrospective v2 source identity. Keep a separate bounded direct baseline because v2 must beat a practical alternative, not only an old Aletheia revision.

### Phase B — one-way legacy importer

Import old artifacts only as legacy observations:

- preserve original path, hash, runtime/config fingerprint, import time;
- mark source identity legacy-unverified unless a new v2 receipt/assessment is created;
- hash notes before creating content objects;
- retain old claim/verdict rows as historical assertions, not v2 verification;
- prohibit import from creating a completed v2 run or free budget.

Do **not** translate an in-flight v1 directory tree into leases/work items. Stale children, duplicate QIDs, and concurrent index writes make its exact state potentially ambiguous. Close/archive the v1 run and start v2 with a new explicit plan.

### Phase C — shadow and compare

For a representative cohort, run v1/direct/v2 under a sealed protocol. If equal source access is intended, use the same captured evidence object and charge context/tool resource according to the protocol. Do not allow any condition to see another condition's draft, reviewer memo, or randomization map.

### Phase D — limited cutover

Move the ordinary default only after offline and live-shadow gates pass. Keep v1 for reproducibility, not as an unbounded silent fallback. If v2 controller/identity services fail, fail closed to a clearly labeled bounded direct mode or stop; never fall back invisibly to v1 unlimited behavior.

Version every object/event schema; reject unknown critical fields instead of silently dropping them. Test forward migrations and backup database plus content store together. Separate implementation version from policy version. Retain provenance receipts when raw bodies must expire for privacy/copyright/deletion reasons; "auditable forever" is not automatically compatible with retention law or user consent.

## Ways v2 could become worse

| Failure mode | Bad v2 response | Required containment |
|---|---|---|
| Ledger theater | One green provenance badge hides weak identity/entailment. | Separate transport, identity, eligibility, and entailment statuses. |
| Metadata spoofing | Plausible title/DOI metadata is treated as proof of right version/body. | Typed IDs, hashes, redirect chain, ambiguity state, human override. |
| Controller bypass | Worker retains raw DB/filesystem/tool credentials. | Scoped capability broker; bypass tests; honest admin threat model. |
| Budget laundering | Side calls, late telemetry, cached context, or manual reads escape accounting. | Reserve first; instrument host; expose unknowns; hard request/read/time caps. |
| Verifier laundering | "Independent" verifier shares model/context or rubber-stamps. | Log lineage; blind scoped review; equal-budget self-check control; human calibration. |
| Metric gaming | Prompts optimize visible rubric/judge wording. | Hidden sealed tasks, immutable evaluator, independent review, retained failures. |
| Multi-agent cost explosion | Parallel fan-out hides aggregate work. | Global envelope, reread policy, connector concurrency limits, frontier reporting. |
| False independence | Origin score is read as truth. | Validate clustering on fixtures; show as warning only. |
| Prompt injection | Source text issues instructions to planner/tools. | Delimit data, controller-only tool authority, adversarial injection fixtures. |
| Browser/session leakage | Private/stale browser body becomes citable. | Separate opt-in capability, scoped receipts, redaction/retention control. |
| Framework gravity | Graphs, queues, plug-ins, dashboards, memory consume effort before proof. | Single-controller MVP; each subsystem requires measured need and deletion plan. |
| Premature high-stakes claim | A few attractive demos become reliability marketing. | Domain-specific error studies, human review, conservative UI language. |

The likely overengineering failure is building an "agent operating system" before proving a bounded lead is inadequate. The likely underengineering failure is retaining skills/files as the authority plane and calling it v2. Avoid both.

## Mandatory review questions

Before a v2 feature/PR is approved:

1. What observed user/v1 failure does it address?
2. What controller-owned invariant prevents it instead of a prompt request?
3. What resource does it reserve, meter, and cap globally?
4. What happens after crash, duplicate delivery, timeout, and stale retry?
5. Can a worker mark it complete by editing an ordinary artifact? If yes, why is that safe?
6. What frozen-baseline ablation isolates incremental benefit?
7. What denominator/error classes are reported, and how can the feature game them?
8. What is the keep/revert rule and flag expiry?
9. Does it expand browser/network/retention authority? What consent and threat model changes?
10. If the answer is "agent judgment", why is it not a measurable, bounded policy decision?

## Bottom line

The durable v2 idea is not "a more intelligent recursive Aletheia." It is **a workflow whose claims about evidence, resource use, and completion are mechanically narrower but actually true**.

Build the boring kernel and rigorous evaluator first. Make a bounded single lead the default. Treat adversarial review, source-separated workers, and dynamic planning as opt-in experiments that must independently beat the baseline under a fixed global envelope. If they win, v2 will have earned complexity. If they do not, the project still delivers a much safer and more transparent research workflow than v1.

## Evidence index

- [Independent deep runtime audit](../../2026-07-28-deep-runtime-and-head-to-head/report.md) — line-level conclusions, cost/latency limits, release recommendations.
- [Skeptical validation](../../2026-07-28-deep-runtime-and-head-to-head/findings-validation.md) — reproduced wrong-body, replay/race, capability, routing, and selection findings.
- [Runtime adversarial addendum](../../2026-07-28-deep-runtime-and-head-to-head/runtime-adversarial-addendum.md) — reread probe, tail-latency reasoning, finite-topology qualification, comparison limits.
- [Corrected controlled comparison](../../2026-07-28-deep-runtime-and-head-to-head/comparison/results.md) and [independent method audit](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md) — tied score and resource/blinding limitations.
- [Historical v0.5 forward-test record](../../../docs/evals/openai-v0.5-forward-test.md) — small-N evidence and the 2.37x dynamic-outline read-artifact result; not a general benchmark.
- [Existing deterministic judge core](../../../scripts/eval/judge_score.py) — useful blind/tie/calibration structure to extend, not sufficient proof.
- Frozen code reviewed: [treestate.py](../../../.cursor/skills/aletheia-research/scripts/treestate.py), [investigate.py](../../../.cursor/skills/aletheia-research/scripts/investigate.py), and [verify.py](../../../.cursor/skills/aletheia-research/scripts/verify.py).
