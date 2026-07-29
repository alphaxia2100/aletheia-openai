# Aletheia v2: workflows, alternatives, and product boundaries

**Status:** design research, not a benchmark result
**Reviewed:** 2026-07-29
**Question:** where should a ground-up Aletheia v2 sit relative to a bounded
single agent, managed Deep Research APIs, open research-agent stacks, and the
experimental discipline exemplified by Karpathy's `autoresearch`?

## Decision in one paragraph

V2 should **not** launch as another default-unlimited research swarm or try to
out-execute every managed research provider. Its product should be a small,
portable **evidence, policy, and evaluation layer** with an excellent bounded
single-lead mode as the default. Managed and open agents should be interchangeable
*executors* behind that layer, not the definition of Aletheia. A more expensive
source-separated investigation mode is defensible only when the task has high
decision value, independent subproblems, and an explicit human-approved resource
envelope. That position is an engineering recommendation, not a claim that v2
will be more accurate than OpenAI, Gemini, Anthropic, LangChain, or any other
system; the present evidence cannot support that claim.

The distinction matters. Managed products can already own much of the difficult
long-running-agent machinery: provider-operated browser/search execution,
background jobs, and in some cases tool-call or per-run cost controls.
Open stacks already offer deployment surfaces, model choice, search/MCP
integration, and published operating configurations. The differentiated job for
Aletheia is to make the *research contract* explicit and independently
inspectable: what was authorized, what was spent, what exact source body was
used, which claim it supports or contradicts, what remains unknown, and why an
added research mechanism was kept rather than reverted.

## What the evidence does and does not establish

The local deep audit gives unusually concrete reasons to rebuild the control
plane, but it does **not** give a ranking of research systems. It reviewed the
complete portable runtime closure and reproduced source-identity and concurrent
state defects. Its controlled head-to-head is more modest: a source-frozen,
hand-executed synthesis exercise tied **11/20 to 11/20** after correction, while
the Aletheia condition had 28 declared document-read assignments and six roles
versus eight assignments and one author/self-check for the direct condition.
There is no common live-retrieval, token, dollar, latency, or multi-topic
comparison. [A1][A2]

Therefore, the following are deliberately separated:

| Statement | Status |
|---|---|
| The v0.5 filesystem control plane fails important integrity and resource-contract requirements. | Reproduced in the local audit. [A1] |
| Aletheia's adversarial/source-origin ideas may improve calibration on some difficult investigations. | Plausible hypothesis; one corrected tied exercise does not prove it. [A2] |
| Multi-agent research can help broad, independent search tasks. | A credible but provider-first-party finding; it must be retested for Aletheia's tasks and budgets. [M3] |
| Aletheia is presently better or worse than a named managed/open alternative. | Unknown; no fair common-task evaluation exists. |
| A v2 bounded single-lead mode should be the default. | Product and risk recommendation, supported by the audit and alternatives' operating properties—not a measured win-rate claim. |

This report uses direct product documentation and pinned upstream repositories for
descriptive facts. Vendor claims and self-reported benchmark/cost figures remain
vendor claims. The local channel doctor found 12 of 13 core channels live but
Brave degraded because no key was configured; this investigation therefore relied
on direct official pages for load-bearing external statements rather than claiming
complete independent-web coverage. [A3]

## First, separate four jobs that are usually conflated

"Research agent" is an overloaded label. V2 should make four jobs separately
replaceable, measurable, and failure-contained.

| Job | Question it answers | Appropriate owner | Why it should not be silently fused |
|---|---|---|---|
| **Execution** | Which searches, reads, tools, and reasoning steps will produce a draft? | A direct lead agent, a managed Deep Research API, or a self-hosted open agent. | Providers and frameworks differ sharply in tool access, latency, data residency, and model behavior. |
| **Evidence assurance** | Did the claimed URL/document actually yield the stored text, and which claim is it evidence for? | Aletheia's deterministic evidence gateway and verifier. | A citation, a URL, or a long body is not by itself an identity or entailment guarantee. |
| **Run governance** | What may this run spend, access, retry, and publish? | V2 policy/controller, with the user or organization owning the envelope. | An executor can make sensible local choices while still exceeding a user-level cost, time, or data policy. |
| **Product evaluation** | Did a workflow change earn its cost across held-out work? | Aletheia's evaluation harness plus independent human/domain review where needed. | A polished one-off report, citation count, or an LLM judge's preference can be gamed or be unrepresentative. |

V0.5 bundles portions of all four into prompts, mutable directories, and a
particular tool suite. The audit's core finding is that a protocol written in
instructions is not an enforceable run contract. [A1] V2 should instead make the
contract the durable artifact and let several execution strategies compete behind
it.

## The recommended product modes

The best product is not a single universal loop. It is an escalation ladder with
visible costs and stable meanings. A mode must say what it will do *before* it
does it, preserve a truthful partial result if it runs out of allowance, and
never turn a simple request into an unbounded tree merely because a model finds
another interesting lead.

| Mode | Default executor shape | Required controls | Best fit | Not appropriate for |
|---|---|---|---|---|
| **0. Answer / lookup** | One model/tool interaction; no research promise. | Small response and tool cap; citations only if actually used. | Familiar facts, local code lookup, low-consequence questions. | A question that needs broad coverage or a defensible evidence record. |
| **1. Bounded research — default** | **One accountable lead** with a small source set and one bounded verification pass. | Immutable run plan; total time, tool, read, byte, token/spend, and concurrency limits; typed source/claim ledger; explicit stop status. | Most product, technical, market, and factual research. | Questions where one context/provenance lane cannot adequately cover independent disputes. |
| **2. Managed research, audited wrapper** | A managed Deep Research API performs the exploratory work; v2 normalizes its trace/citations and verifies consequential final claims. | Provider/model/version/job ID recorded; allowed tools/data domains; provider usage/limits captured where available; local evidence identity re-read or abstention policy. | Broad reports where managed browsing and operations are acceptable and turnaround matters. | Strict data-residency/ZDR constraints, unavailable trace/body access, or a requirement to independently preserve every source body. |
| **3. Audited investigation — opt in** | One lead plus a small number of source-separated, read-only workers and an independent reviewer. | Everything in mode 1, plus a predeclared decomposition, per-branch allocations, no parallel writers, identity-verified evidence, conflict/coverage review, human decision owner. | Consequential, contested, or provenance-sensitive decisions with truly independent lines of inquiry. | Ordinary lookup; a task whose subtasks strongly depend on one shared evolving context; any run without an approved envelope. |
| **4. Evaluation lab — internal** | Frozen direct, managed, and/or open executors run under matched contracts. | Precommitted task set, snapshots/fixtures when lawful, telemetry, blinded outcome assessment, promotion/revert rules. | Choosing which controls deserve modes 1–3. | End-user research delivery. |

Mode 1 is the product's center of gravity. It should be good enough that a user
does not need to understand multi-agent theory to get a careful answer. Mode 3 is
not a higher numerical "thoroughness" setting. It is a different service level:
the user is purchasing an explicit investigation plan, a documented evidence
record, and a review process. Calling it `unlimited` hides the most important
choice—the maximum effort and cost the user is willing to authorize.

### Escalation should be policy-driven, not a model's whim

V2 may recommend an escalation, but it should not self-escalate across a
user-level envelope. A transparent rule can assess:

1. **Decision consequence:** Is a material decision, external action, health,
   legal, financial, or policy issue at stake?
2. **Independent breadth:** Can the question be decomposed into at least two
   genuinely different source bases—not merely several prompts likely to search
   the same web results?
3. **Expected value of disconfirmation:** Would a missed contrary source plausibly
   change the decision or its uncertainty?
4. **Evidence constraints:** Are primary documents, exact versions, data
   residency, reproducibility, or audit artifacts required?
5. **Budget authority:** Has someone approved the maximum spend, time, data/tool
   access, worker count, and review obligation?

If the answer to (5) is no, v2 should either run mode 1 or ask for a service
level. A high-confidence-looking output is not authority to consume more money,
time, or private data.

## Alternatives, honestly compared

### 1. The bounded single lead is the baseline—not a straw man

A strong direct research workflow is a capable model with only the tools it
needs, a well-scoped prompt, a finite resource contract, selected primary or
decisive sources, a compact claim/source table, and a final independent check
for consequential claims. It retains one working context, has one accountable
author, and does not pay the handoff/duplication cost of a tree unless the
question earns it.

Its weaknesses are equally real: one agent can anchor on an early framing,
mistake echoed sources for corroboration, omit a contrary perspective, or fail to
preserve enough for later audit. Those are reasons to add *specific* controls;
they are not evidence that every ordinary question needs a worker hierarchy.

The local comparison makes the baseline requirement concrete. A direct
source-frozen answer reached the same corrected factual-rubric score as the
more elaborate condition, while the latter had much greater declared reading and
role overhead. This is not a conclusion that the direct system "won"—the task
was too small and asymmetric—but it does establish why v2 must retain a strong
direct baseline throughout development. [A2]

**V2 implication:** the default executor must be a first-class product, using
the same ledger, budget accountant, evidence gateway, and final-report schema as
every other mode. Do not make the simple baseline a weak prompt while reserving
all quality controls for the elaborate path; that makes later comparisons
meaningless.

### 2. Managed Deep Research APIs are executors, not competitors to emulate wholesale

OpenAI documents Deep Research as a Responses API model using at least one data
source such as web search, remote MCP, or file search, with optional code
interpreter. The response can contain web-search/MCP/file/code call records and
inline-citation annotations. It recommends background execution for long tasks
and exposes `max_tool_calls` as its primary tool-call control for cost and
latency. It also documents a real data-handling boundary: background responses
are retained for roughly ten minutes for polling and are incompatible with Zero
Data Retention requirements. [M1]

Google's Gemini Deep Research documentation presents a parallel managed design:
asynchronous background execution, collaborative plan review before execution,
supported search/URL/code/MCP/file tools, streamed progress, and a documented
maximum research time of 60 minutes. Its July 2026 preview documentation even
publishes *estimated* common-run usage and price bands. It also warns that web
content can be malicious and recommends review of supplied citations. [M2]

Those capabilities demonstrate that v2 need not own all long-running execution
to deliver user value. A managed executor can be the right choice when:

- access to the provider's browser/index/tooling is a feature rather than a
  compliance concern;
- a user values a fast, polished broad report more than a custom local
  investigative procedure;
- the provider exposes sufficient job/usage/citation information to make the
  run understandable; and
- the organization accepts the provider's data, versioning, availability, and
  pricing terms for that run.

They do **not** remove the reason for an Aletheia layer. A tool-call trace tells
us that a provider called a search/open tool; it is not, by itself, a v2 proof
that the locally cited claim is supported by the exact source body, has the
right identity, represents an independent origin, or covers the decision's
important countercase. Nor should v2 assume a provider citation is durable or
semantically sufficient just because it is clickable. It must either ingest an
identity-compatible source artifact and verify the claim, or label the claim
provider-supplied/unverified and decline a strong assurance label.

**V2 implication:** implement provider adapters, not provider-specific state
machines. An adapter should turn a provider response into a canonical event
record while preserving the original response/job ID and raw citation/tool
metadata:

```text
Run contract → managed executor adapter → provider job/response
     ↓                                       ↓
budget/allow-list enforcement          trace, citations, usage, errors
     ↓                                       ↓
canonical source/claim ledger ← identity-aware evidence gateway ← final report
```

The adapter must report its limits. If a provider does not expose tool
arguments, usage, or source content necessary for a requested assurance level,
the run remains useful as a report but cannot be certified as a fully auditable
investigation. This is a graceful product boundary, not a reason to fabricate
local certainty.

### 3. Open research-agent projects are serious deployment/evaluation baselines

Open systems should be used as actual competitors in v2's evaluation lab rather
than presented as generic "agent swarms." Two useful reference points illustrate
what v2 must either reuse or clearly differentiate from:

- **LangChain Open Deep Research** documents a configurable research,
  summarization, compression, and final-report pipeline; model-provider and
  search/MCP selection; local/server/hosted deployment paths; and a 100-task
  Deep Research Bench integration. Its pinned README publishes historical total
  token and cost figures for named configurations, including a default 100-task
  run. Those figures are self-reported and version/model dependent, but the
  disclosure itself is an operational standard Aletheia lacks today. [O1]
- **GPT Researcher** documents a planner/executor/publisher architecture,
  local and web inputs, server/UI/MCP integration, a recursive tree option, and
  tracing. Its pinned README advertises an approximate five-minute/$0.40 deep
  run for one named configuration. That is not a universal price or an
  independently validated quality result. Its own "more scraped sites means
  less chance of incorrect data" rationale also exposes precisely why v2 should
  retain source-origin analysis: many domains can repeat one upstream claim
  without becoming independent evidence. [O2]

The self-hosted/open path is appropriate where teams need model choice, custom
connectors, deployment control, local datasets, private network access, or
long-lived workflow integration. It also shifts obligations to the operator:
credentials, tool policy, data isolation, connector availability, error/retry
semantics, content capture, lifecycle/versioning, and monitoring. V0.5 tried to
own part of that surface with a filesystem protocol; the audit shows why v2 must
not repeat that without transactional state and deterministic enforcement. [A1]

**V2 implication:** do not rebuild a broad UI, generic crawler ecosystem, or
model abstraction layer merely to match an open project's feature checklist.
Provide a narrow self-hosted executor interface and a well-specified evidence
gateway. Let an organization plug in an existing open agent only if it can
produce the contract's required event/usage/source records. If it cannot, it
may still produce a report, but should not inherit an "audited" label.

### 4. Multi-agent is a conditional capacity multiplier, not the default architecture

Anthropic's account of its production Research system is valuable because it is
both enthusiastic and specific about the cost. It reports strong internal
results for breadth-first tasks, but also says multi-agent systems used about
15× chat tokens in its data. Its reported successful shape is a lead that plans
and delegates independent searches, then synthesizes; it describes early
failures such as excessive subagents and endless searching, and recommends
effort rules based on query complexity. It also calls out durable checkpoints,
tracing, retry logic, and the added consistency/error-propagation problems of
asynchronous work. These are first-party findings, not a general Aletheia
performance guarantee. [M3]

That evidence agrees with the audit's practical lesson: parallelism is earned
only when it attacks a real structural bottleneck. Use it for a question like
"compare separate regulatory regimes, technical mechanisms, and field reports"
where different source bases can be gathered independently. Do not use it for a
question whose answer turns on a single primary source, a small internal corpus,
or a shared sequential decision chain.

**V2 implication:** maintain one lead as the only authority permitted to change
the run plan, resolve conflicts, choose final claims, and publish. Workers get
immutable task IDs, read-only access to inputs, a fixed allocation, and a
structured evidence return. A worker may propose a follow-up or a source, but
not mutate a global tree, clear another worker's question, or quietly make a
new budget. This keeps the useful "parallel independent evidence, centralized
decision" pattern without recreating v0.5's shared-blackboard races.

### 5. Karpathy's loop is an evaluation lesson, not a web-research executor

`autoresearch` is unusually clear because it confines the experiment to one
mutable file (`train.py`), fixes the evaluation/data harness, fixes a five-minute
single-GPU run, records an immutable numerical metric (`val_bpb`), and uses Git
to keep an improved commit or reset a non-improvement. It also records crashes
and applies a stated simplicity criterion. [K1]

It would be a category mistake to call that a replacement for open-world
research. Web research does not have one scalar equivalent to `val_bpb`:
citation count, output length, source count, link diversity, or a friendly LLM
judge can all improve while factual completeness or decision quality worsens.
The lesson for v2 is more demanding than "make it small":

1. freeze the task and source-access policy before comparing designs;
2. give every contender the same actual resource envelope, including tokens,
   tool calls, reads, wall time, and dollars where observable;
3. preserve an unweakened direct baseline;
4. score a compact, predeclared suite of outcomes rather than asking whether one
   output feels impressive;
5. independently judge consequential output quality and calibrate automatic
   graders with humans; and
6. retain a feature only if it clears a predeclared benefit threshold; otherwise
   disable or revert it.

This is consistent with OpenAI's own evaluation guidance: use task-specific
evals, log behavior, combine metrics with human judgment, evaluate early and
continuously, and favor comparisons/classification against explicit criteria
over unconstrained open-ended judging. [E1]

## Managed versus self-hosted: the real boundary

The choice is not simply "easy managed" versus "serious self-hosted." It is
which party can credibly own each failure mode.

| Concern | Managed executor is usually strongest when… | Self-hosted executor is required/preferred when… | V2's non-negotiable role in either case |
|---|---|---|---|
| Long-running job lifecycle | Provider background jobs, retries, service monitoring, and scale are acceptable. | Jobs need to run in a private network, under a local scheduler, or with bespoke recovery semantics. | Record a durable run state, provider/local job reference, cancellation, timeout, and terminal reason. |
| Search/browser/tool access | The provider's web/index/connectors meet the source policy. | Required sources are private, licensed, local, allow-listed, or need custom retrieval/crawling. | Enforce an explicit capability and data policy; record which source/tool route was actually used. |
| Data governance | Provider retention/residency/contract terms fit the question. | ZDR, regulated data, air-gapped data, or content-retention policy bars the managed route. | Do not silently route private material to a provider; record the selected data classification and assurance limitation. |
| Cost and latency | Provider exposes usable job/usage controls and the task fits its price/latency profile. | The organization needs its own model/search economics or hard local quotas. | Own a cross-executor envelope and final ledger; provider request caps alone are not a user-level proof of total spend. |
| Reproducibility | A provider job ID, response, versions, and citations are sufficient for the intended report. | Exact inputs, retrieval code, snapshots, model versions, or content bodies must be held locally. | Declare reproducibility tier and capture hashes/versions; never label a merely replayable-looking response fully reproducible. |
| Evidence assurance | A report with visible citations and human spot checks is sufficient. | Exact source-body identity, a custom provenance policy, or a long-lived case file is required. | Bind source references to observed content/identity and claim verdicts, or explicitly report the gap. |

Two concrete implications follow.

**First, v2 must not infer a stronger assurance level from a provider choice.** A
managed citation is useful data. It is not automatically a verified primary
source, a stable source body, or independent corroboration. Likewise, a local
crawler does not automatically make a source more trustworthy. Assurance is
earned by the recorded evidence relationship, not by brand or deployment model.

**Second, v2 should be portable at the contract level, not by copying a whole
agent runtime into every harness.** The portable object is a versioned run
schema, event and evidence formats, deterministic validators, test fixtures, and
adapter conformance tests. A Codex skill, a service, a CLI, or a managed-provider
client can implement it. This avoids coupling the research product's truth claims
to one host agent's file-writing behavior.

## A concrete v2 composition

This is a product-facing architecture, not a prescription for a particular
database or framework. It states the ownership boundaries that must hold whether
the implementation is a small local CLI or a service.

```text
                         immutable run contract
                                    │
                         policy / budget controller
                                    │
       ┌────────────────────────────┼───────────────────────────┐
       │                            │                           │
direct bounded lead          managed-executor adapter    self-hosted adapter
       │                            │                           │
       └─────────── normalized action / result events ──────────┘
                                    │
                         evidence identity gateway
                                    │
                    typed source ↔ claim ↔ verdict ledger
                                    │
            single lead synthesis + independent verification gate
                                    │
                      report, stop reason, and audit bundle

      separate: evaluation harness → keep / disable / revert decisions
```

### The immutable run contract

Before the first tool call, persist an immutable, versioned contract containing:

- task, decision context, output type, and time sensitivity;
- chosen mode and executor adapter/version/model configuration;
- allowed tools, domains, data classifications, and credential/capability policy;
- hard maxima for wall time, queued/executing workers, model tokens and spend
  where the host/provider exposes them, tool calls, external requests, bytes,
  source reads, and human-review time/obligation;
- source/claim assurance level requested and permitted fallbacks;
- the declared decomposition, if any, including worker allocations and the lead
  who can authorize a change; and
- identifiers for the evaluation/baseline policy if this is an experimental run.

Changing scope needs a new contract revision with a named authority and an audit
event—not an agent silently changing a JSON file. The audit's wrong-answer,
stale-child, and concurrency probes explain why this is not ceremony. [A1]

### The evidence gateway

Treat every external document as an untrusted proposed source until the gateway
records a normalized evidence item. For an assurance-capable source, capture at
minimum:

- requested and final URL; retrieval route/tool/provider; status/content type;
- expected and observed title/identifier/DOI or a documented identity exception;
- retrieval time, content hash, canonical source/origin relations, and immutable
  stored body or a clear retention limitation;
- a readable passage/span reference used by a claim; and
- the source's role (primary, official record, secondary analysis, lead,
  first-hand case, or color), plus why it was selected.

The direct reason is the audited v0.5 behavior: a body-length predicate could
make unrelated text look like a successful read under the requested URL. A
provider trace or a local note filename cannot repair that after the fact. [A1]

Workers and providers may suggest claims; only an evidence-bound claim ledger
can classify each final claim as supported, contradicted, insufficient,
provider-cited-only, or intentionally not checked. The final report should make
the assurance boundary legible rather than pretend every citation means the same
thing.

### Single-writer state and advisory parallelism

The controller is the sole writer of run transitions, allocations, and final
ledger verdicts. Workers submit append-only proposals with idempotency keys. A
lease/transaction layer commits them in a declared order; retrying a completed
proposal cannot create a second source index row or resurrect stale tree
children. Synthesis reads the contract's manifest rather than enumerating a
directory. This is a functional requirement derived from the v0.5 race/replay
findings, not a preference for any particular workflow engine. [A1]

Parallel workers remain useful as *advisory evidence producers* where they can
be allocated independent source bases. They should not share a mutable planning
file, make global membership decisions, or write the final report. This creates
a clear place to attribute added cost and a clear failure mode: a failed worker
is an incomplete branch, not an invisible reason that the whole investigation
looks complete.

### Honest stopping and abstention

Every mode ends in one of several durable outcomes: `complete`,
`complete_with_gaps`, `budget_exhausted`, `source_identity_unresolved`,
`review_required`, `cancelled`, or `failed`. These are product output states,
not errors to conceal. A budget exhausted run may return a useful partial report,
but it must contain the known gaps and must not inherit a high-assurance label.

There is no v2 equivalent of `unlimited` without a maximum. An organization can
offer a high ceiling or a human-approved continuation policy, but the current run
still needs an envelope and a stop rule. The background-job limits and estimated
cost disclosure in managed APIs show that long-running research can be honest
about its operational boundary; v2 should be stricter, not looser. [M1][M2]

## What to measure before claiming v2 earns its complexity

The local audit's key quality conclusion is not that multi-agent research is
bad. It is that Aletheia has no credible evidence that its full ceremony wins at
equal resources. V2's first major deliverable should therefore be the evaluation
lab, alongside—not after—the bounded product path.

### Contenders and parity

For each held-out task, compare at least:

1. **Direct bounded baseline:** one lead with the shared evidence/budget core.
2. **Direct plus critic:** the same direct baseline plus one independent bounded
   reviewer, to separate the value of fresh review from the value of a tree.
3. **V2 audited investigation:** source-separated workers plus lead and review.
4. **Optional external executor:** a managed API and/or an open agent when the
   source, data, and terms permit a meaningful same-policy comparison.

Hold fixed or fully record model family/version, prompts/instructions, date and
source access, allowed tools, data classifications, dollars/tokens/tool calls,
wall-clock deadline, browser/search cache policy, and human intervention. It is
not enough to give each system a similar number of "rounds." The v0.5 audit
shows why rounds were a poor proxy for both model spend and read activity. [A1]

### Outcome scorecard

No single metric can act as `val_bpb` for open-web truth seeking. Use a compact
scorecard with separately reported dimensions:

| Dimension | Example measure | Why it matters |
|---|---|---|
| Decision correctness/usefulness | Blinded domain/human rubric, with a prespecified decision scenario. | A report may be well cited yet not answer the decision. |
| Claim support and citation identity | Claim-level supported/contradicted/insufficient verdict; exact-body/identifier match rate. | Prevents fluent citations from masking a wrong or unrelated body. |
| Coverage and counterevidence | Recall of decisive sources/counterexamples on frozen tasks; known-unknowns stated. | A supported narrow story can still omit the fact that changes the answer. |
| Calibration | Appropriate uncertainty, abstentions, and disagreement reporting. | High-stakes value is often knowing when not to conclude. |
| Source quality/origin diversity | Primary/official source mix and independent-origin analysis, reviewed by task type. | Many URLs do not automatically mean independent corroboration. |
| Operational efficiency | End-to-end latency distribution; dollars/tokens/tool calls/reads/bytes; failure and retry rate. | Measures whether a safeguard earns its cost rather than merely adding ceremony. |
| Reliability and safety | Budget/allow-list violations, source-identity failures, duplicate/replay defects, prompt-injection resilience. | A good final answer does not excuse an unsafe or unauditable run. |

Automated graders are useful for scoped, evidence-backed comparisons, but must
be calibrated against blinded human/domain judgments. OpenAI's evaluation
guidance explicitly warns against generic or vibe-based metrics and recommends
task-specific evals plus human calibration. [E1] Keep the raw source packet,
trace, random assignment, output hashes, and grading rationale so a future
auditor can challenge the apparent win—the earlier 12–11 claim became an 11–11
tie only because the rubric and outputs were retained. [A2]

### Feature-level keep/revert rules

Each proposed safeguard gets its own hypothesis, not a spot in the permanent
ritual. Examples:

| Feature | Keep only if it repeatedly… | Revert/disable if it… |
|---|---|---|
| Portfolio/adversary branch | Improves counterevidence recall or calibrated uncertainty under a capped overhead. | Merely produces more prose/links or harms ordinary-task utility. |
| Source-origin graph | Finds material echo/attribution errors that human review validates. | Adds an untrusted score with no decision-changing discoveries. |
| Full-body identity gateway | Prevents measurable wrong-document/citation failures at acceptable retrieval cost. | Is bypassed, weakly matches identity, or imposes an unjustified default retention risk. |
| Additional worker | Improves held-out coverage or latency enough to pay for its token and coordination budget. | Duplicates the lead's work, worsens failures, or only wins under unmatched resources. |
| Fresh verifier | Catches meaningful final-claim errors beyond a similarly budgeted direct critic. | Rubber-stamps the author or duplicates a check without detectable benefit. |

Promotion should require a preregistered threshold and confidence/replication
rule appropriate to sample size. A feature that is inconclusive remains behind
an experimental flag; it does not become the default because it has a persuasive
story.

## Product positioning after the rebuild

If v2 follows this design, its honest positioning is not "the most intelligent
researcher" and not "more agents equals more truth." It is:

> A bounded research-control system that can use a direct agent, a managed
> researcher, or a self-hosted executor, while preserving a verifiable evidence
> record, a declared resource contract, and an evaluation trail for the
> safeguards it asks users to pay for.

That is useful even if a managed API generates the best ordinary report today.
It also avoids locking v2 into a false choice between a minimal single agent and
a maximal worker tree. The simple mode is a durable product; the audited mode is
a deliberately expensive escalation; and the evaluation lab decides where the
line should move.

## Sources and evidence limits

The sources below support descriptive capability and process statements, not a
cross-vendor quality ranking. Accessed 2026-07-29 unless otherwise noted.

| ID | Source | What it supports | Limitation |
|---|---|---|---|
| A1 | [Local independent deep runtime audit](../../2026-07-28-deep-runtime-and-head-to-head/report.md) | Reproduced v0.5 identity, state, and resource-governance defects; 7,358-line review; limits of current evidence. | Project-local audit of one frozen candidate, not a vendor bake-off or prevalence study. |
| A2 | [Corrected controlled comparison](../../2026-07-28-deep-runtime-and-head-to-head/comparison/results.md) and [independent method audit](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md) | Corrected 11–11 result and 28-versus-8 declared read-assignment asymmetry. | One frozen-packet task; no live retrieval, tokens, dollars, latency, or general quality conclusion. |
| A3 | [Channel-health snapshot](channel-health-2026-07-29.md) | 12/13 core channels live; Brave degraded without an API key. | Point-in-time health, not a load test or independent-web coverage guarantee. |
| M1 | [OpenAI Deep Research API guide](https://developers.openai.com/api/docs/guides/deep-research) | Managed tools, output call/citation structure, background mode, `max_tool_calls`, and ZDR/background caveat. | Official documentation; no independent quality/cost comparison. |
| M2 | [Google Gemini Deep Research Agent guide](https://ai.google.dev/gemini-api/docs/deep-research) | Managed background execution, plan review, tools, estimates, safety warning, and 60-minute maximum. | Official preview documentation; capabilities, prices, and limits may change. |
| M3 | [Anthropic: multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Orchestrator/worker shape, conditional parallelism, reported token premium, production reliability lessons. | First-party internal evaluation/results; not a universal performance result. |
| O1 | [LangChain Open Deep Research README, pinned](https://github.com/langchain-ai/open_deep_research/blob/d337ae32ed4ff8f4c6fbe192ba3bf1b2d6610799/README.md) | Open configurable pipeline, provider/search/MCP options, deployment, benchmark/cost disclosure. | Self-reported README figures from a pinned historical revision. |
| O2 | [GPT Researcher README, pinned](https://github.com/assafelovic/gpt-researcher/blob/5d84d2f5553e70a2765a8ff3a0d2672d60437ce8/README.md) | Planner/executor/publisher design, tree option, tracing, and advertised operating figure. | Self-reported claims; the frequency-of-sites rationale is not proof of independent evidence. |
| K1 | [Karpathy `autoresearch` program, pinned](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md) | Fixed five-minute budget, immutable evaluator, one mutable target, Git keep/revert loop. | A closed ML-optimization program, not an open-web research system. |
| E1 | [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Task-specific, continuous, human-calibrated evaluation and comparison-friendly grading guidance. | Official methodological guidance, not a validation of this proposed v2 scorecard. |
