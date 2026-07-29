# Independent deep audit — Aletheia OpenAI runtime

- **Audited runtime candidate:** `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`
- **Audit branch:** `codex/independent-audit-2026-07-28` at `cbed478`
- **Candidate state:** unpromoted; repository documentation separately labels `prod` stable.

## Opinion

**Aletheia is a thoughtful research protocol wrapped around a partially enforced filesystem workflow. It is not yet a trustworthy high-stakes research runtime, and default `unlimited` is the wrong product default.**

The project has unusually good instincts for an agent workflow: preserve artifacts, separate retrieval from source selection, seek adversarial evidence, track origin/echo signals, and make a fresh pass over a final answer. Its standard-library implementation, runtime fingerprinting, portable closure work, and 186 passing hermetic regression tests are real strengths.

The critical problem is enforcement. Its most consequential guarantees remain prompt obligations or mutable-file conventions. At the audited candidate, a long wrong document can become a successful read; a bogus answer can clear the clarification gate; replay can mix stale branches into synthesis; and concurrent workers can exceed the configured node cap or duplicate the global source index. The public default also has no enforceable run-level budget for host-model tokens, dollars, wall time, external requests, manual reads, or human review.

**Recommendation:** use a bounded, single-lead research workflow as the default. Offer the full Aletheia investigation workflow only as an explicit, budgeted, human-reviewed escalation.

## Gradecard

These are audit judgments, not benchmark scores.

| Dimension | Grade | Assessment |
|---|---:|---|
| Research-process ideas | **B** | Adversary framing, artifacts, and fresh review target genuine model failures. |
| Local implementation discipline | **C+** | Compact code, tests, fingerprints, and privacy/capability work are meaningful; critical integrity paths still fail. |
| Evidence/read identity | **D** | Sufficient text length is treated as a usable read without binding returned text to the requested work. |
| Parallel/resume control plane | **D** | No transactional, leased, or idempotent state protocol; races and replay defects reproduce. |
| Resource and cost governance | **F** | `unlimited` has finite tree backstops but no resource envelope the runtime can enforce or price. |
| Observability/forensics | **B-** | Artifacts, telemetry, and hashes are useful after the fact, not a complete execution or semantic ledger. |
| Portable/capability boundary | **C-** | Serious defensive work, but callable adapter, browser provenance, marker, and readiness gaps remain. |
| High-stakes default readiness | **F** | Identity, state-integrity, resource, and evaluation gates are not met. |
| Ordinary research workflow fit | **D** | The expected multi-agent/multi-artifact process is too costly and brittle for most normal questions. |
| Proven outcome superiority | **D** | Existing evidence is small-N and not cost matched; this audit adds one narrow controlled comparison. |

## What this design is

This is not an autonomous research service that owns planning, cost metering, tool authorization, and an evidence database. It is a **skill-level protocol plus a filesystem blackboard**.

1. `SKILL.md` asks a host agent to frame questions, fan out workers, select sources, write findings, synthesize, and fact-check.
2. `treestate.py` makes directories plus JSON/Markdown files into shared state.
3. `investigate.py` retrieves, ranks, reads, and records artifacts, while the host agent still decides epistemic appropriateness, saturation, and claims.
4. `report.py`, `verify.py`, and `synthesize.py` check selected file shape, hash relationships, and lexical conditions. They do not prove entailment, independent review, appropriate stopping, or host-model spend.

Externalizing state is a sensible answer to a context-window problem. It becomes fragile when the same agents it is meant to constrain can write the ordinary files that represent successful state. A host can bypass a gate by editing artifacts directly, and the runtime cannot observe host-model calls or authority decisions.

The literal source inventory is [line-review/README.md](line-review/README.md): 38 executable files / 7,358 executable lines, plus 120 behavior-changing container/config lines. Every executable line was reviewed against the frozen candidate. The engine, control-plane, and boundary reports contain exact contiguous coverage manifests.

## Release blockers reproduced in this audit

### Read identity is not established

`investigate.py` accepts a body of at least 1,500 characters as `_read_ok`, stores it under a hash of the requested URL, and does no expected-versus-observed title/DOI/identifier comparison. A hermetic unrelated 2,200-character body was recorded as a successful evidence read. `verify.py` later finds a note solely by a 40-bit URL-derived filename and does not inspect the note's embedded source header. A mismatched body can therefore look lexically relevant for the cited URL.

The historical observation record documents two wrong GRADE documents and an anti-bot body accepted in an earlier run. It does **not** establish a current failure rate. It demonstrates why a length predicate cannot justify saying a primary was read. An opt-in browser reader has an additional stale-session risk: it ignores the navigation result and can extract prior page content from a shared browser session under a new requested URL.

**Required gate:** record requested/final URL, expected/observed identity, content state, content hash, and failed attempts in a typed source ledger. Only identity-compatible usable content may carry evidence weight. The repository's separate identity-gate mechanism remains experimental and unpromoted.

See [engine E-01](line-review/engine.md#e-01--p0-read-success-is-body-length-success-not-document-identity-success), [control-plane CP-02](line-review/control-plane.md#cp-02--p1--verification-does-not-prove-that-stored-text-came-from-the-cited-url), and [boundary H2/H3](line-review/boundary.md#bnd-h2--browser-reads-can-return-stalewrong-content-under-the-requested-url).

### Parallel/resume gates are not transactional

The clarification gate treats any nonblank answer record as resolution; a typoed QID with an empty body cleared a real unanswered question. Replaying `split_node` leaves old child directories on disk while synthesis enumerates every directory rather than the declared child list. Barrier probes also reproduced duplicate QIDs, duplicate global-index rows, and seven nodes after concurrent splits each observed only two free slots in a `max_nodes=5` run.

These failures require retry, duplicate scheduling, restart, or another writer; they are not claims that every ordinary sequential run corrupts itself. They are still incompatible with an assertion that the prescribed parallel workflow is enforced, fully resumable, or audit-safe.

**Required gate:** use transactional/leased state, immutable IDs, atomic transitions, idempotency keys, and a tree manifest that synthesis consumes instead of arbitrary directories. Add crash/retry and multi-worker tests.

See [control-plane CP-01, CP-03, and CP-04](line-review/control-plane.md#confirmed-defects), [severity validation](findings-validation.md), and the [50-trial source-index race](probes/source_index_race-result.json).

### `unlimited` is not a resource contract

The code gives `unlimited` finite structural settings: a 1,000,000 logical budget, depth 99, six children, and 512 nodes; `max` has a higher tree backstop. It is therefore not literally structurally infinite. It remains unbounded in the resources a user actually pays for: unlimited/max leaves have no round cap, and no component sets a run-wide limit for host-model tokens, dollars, agent wall time, external requests, manual/linked-primary reads, browser work, or human review.

Telemetry totals retrieval/read activity and reader seconds after the fact. The Python runtime does not make or meter the host-model calls that dominate the workflow. Retry layers, serial selected reads, and multi-worker orchestration make a logical tree “budget” especially misleading as a spend promise.

**Required gate:** make bounded operation the default. Require a visible cross-worker envelope for requests, bytes, reads, wall time, concurrency, and host tokens/spend where available. Stop with a durable incomplete/abstain state when exhausted.

See [control-plane D-03/D-04](line-review/control-plane.md#design-limitations-and-documentation-mismatches), [engine E-04/D-01/D-02](line-review/engine.md#confirmed-performance-design-limits-not-bugs-by-themselves), and [boundary M1/M2](line-review/boundary.md#medium-findings).

## Routing and source selection are more brittle than the protocol suggests

The retrieval engine has good raw ingredients: domain-specific channel maps, concurrent retrieval,
work-level deduplication, a relevance gate, and an agent-triage path that deliberately leaves
epistemic source selection to a human-like host agent. Those are real improvements over a generic
"search ten links and summarize" loop. They do not constitute reliable source coverage.

Three implementation behaviors matter most:

1. **Mixed-domain routing can remove the specialist sources for both domains.** The router unions
   each classified domain's exclusions before it filters all choices. A medical-machine-learning
   probe selected generic web/OpenAlex/community channels while excluding arXiv, Europe PMC, GitHub,
   and Stack Exchange. Generic OpenAlex remains, so this is coverage degradation rather than a total
   outage; it is still exactly the sort of question for which specialist routing is needed.
2. **Network timing can decide which alias is ranked.** Retrieval records are appended in completion
   order, then deduplicated before ranking. In a controlled delay swap, whichever of an arXiv record
   and a mirror returned first survived. Determinism after that point does not restore the discarded
   representation or guarantee that a primary has won.
3. **The deterministic path does not enforce a primary-source quota.** "Primary" adds only a 1.05
   score multiplier. A reproducible counterexample selected three higher-scoring non-primary records
   despite an eligible primary. The agent-triage path can do better, but only if the host recognizes
   the issue and makes a good choice.

There are smaller but operationally meaningful cost/quality leaks: duplicate explicit channels issue
duplicate calls; a CLI read count is not propagated through the triage suggestion path; a fully failed
or empty bounded round can become "investigated" and spend that round; and relevance is normalized to
the best returned hit, so a weak result set can make its best weak hit eligible. The point is not that
every query is bad. It is that the code cannot honestly promise its intended "wide, primary-first,
domain-appropriate" survey without a competent operator supervising the exceptions.

See [engine E-02 through E-08](line-review/engine.md#confirmed-defects-and-contract-failures) and the calibrated
[validation record](findings-validation.md#confirmed-behavior-with-scope-or-severity-qualification).

## Capability and portability work is useful, but not a proof boundary

The copied portable closure, user-scoped configuration, channel allow-listing, private artifact
defaults, environment scrubbing, and runtime fingerprinting are thoughtful engineering. They are
better than treating arbitrary browser or connector access as an invisible implementation detail.

They should not be marketed as a security or provenance guarantee:

- The engine checks that its own routed channels are enabled, but a caller importing a connector can
  invoke its generic search function without the command-line enable gate. This is an API-contract
  leak, not evidence that arbitrary local code has escaped an OS sandbox.
- The browser reader can treat contents remaining in its shared browser session as the result of a
  failed navigation. That is an opt-in path rather than the default engine read path, but it is a
  severe provenance problem when used.
- A changed portable-install marker can cause preflight to skip the manifest verification it would
  otherwise apply. A writer who can alter the installed runtime is already trusted, so this is a
  tamper-evidence gap rather than an elevation-of-privilege finding.
- Health reporting and the DuckDuckGo path do not share all of the normal guardrails, so a green-ish
  readiness signal is not a comprehensive live-channel reliability statement.

The audit therefore gives the boundary a C- rather than an F: it contains useful defense-in-depth and
clear documentation, but it does not make an untrusted execution environment safe or bind retrieved
text to the claimed source.

See the [boundary high findings](line-review/boundary.md#high-findings), especially BND-H1 through BND-H4, and the
[severity qualification](findings-validation.md#confirmed-behavior-with-scope-or-severity-qualification).

## Is it too slow, costly, or complex?

### The honest speed answer: unmeasured end to end, structurally high-overhead

I cannot responsibly label the current candidate "X minutes" or "slower than product Y". The Python
runtime neither invokes the host model nor records host wall-clock time. Live channel availability is
also configuration- and date-dependent; during this audit Brave was degraded without a key and Reddit
returned HTTP 502. There is no credible latency distribution for equivalent real questions.

What the code and records do establish is the latency shape:

| Stage | Behavior in the candidate | Practical consequence |
|---|---|---|
| Candidate retrieval | Concurrent across selected channels | Good latency behavior when providers respond and a leaf has several channels. |
| Reading selected sources in one leaf | Serial loop | Four controlled 50 ms reads took about 0.219 s; several slow full-text reads add rather than overlap within that leaf. |
| Cross-leaf work | The skill asks the host to fan out workers | It may reduce elapsed time only if the host actually schedules them safely; it also increases coordination. |
| Synthesis / verification | Central, sequential artifact work plus a fresh review | Useful for coherence but adds at least another full pass over material. |
| Unlimited/max stopping | Agent-declared saturation | No predictable upper bound on rounds, retries, or human intervention. |

The project does have a useful historical scale signal, not a benchmark: a July 27 first-party run
reported 37 rounds, 48 candidate gathers, 1,137 retrieved results, 72 selected reads, 65 successful
engine reads, 131 persisted read artifacts, and 347.4 reader-seconds. It did **not** report comparable
model time, tokens, dollars, or total elapsed time. That is entirely reasonable for an exploratory
dossier; it is not an ordinary answer workflow.

### The honest cost answer: not priced, but plainly expensive to orchestrate

No dollar claim belongs in this audit. Paid connectors, model pricing, cache state, and operator
behavior are outside the runtime ledger. The relevant product failure is not a proven price tag; it is
that a default called `unlimited` offers the user no hard economic contract.

The controlled comparison below shows the shape of the premium even without token telemetry: the
structured condition assigned the same eight documents 28 times across four leaf workers, a
synthesizer, and a reviewer. The direct condition assigned them eight times to one author/self-check.
Duplicated reading is sometimes the point of adversarial review; it is still a real cost. Aletheia
should make that premium opt-in and estimate it before launch.

There is also an unadvertised duplication mechanism in the runtime itself. A hermetic two-leaf probe
read the same primary URL twice and created one note in each leaf while the global source index showed
only one URL. The global index deduplicates bookkeeping; it is not a run-wide verified-content cache
or a re-read policy. Independent rereads can be a valid epistemic choice, but they should be explicit,
metered, and justified rather than silently multiplying context, latency, and source-reading work.
See [AD-01](runtime-adversarial-addendum.md#ad-01--p2-the-global-index-does-not-prevent-cross-leaf-re-reads).

There is a counterweight worth retaining: `unlimited` and `max` are finite in topology. Before races,
their caps permit at most 426 and 1,792 leaves respectively. With the default first-round unit, that
can still imply up to 1,704 or 7,168 selected full reads before later rounds or manual work. These are
upper-bound scenarios, not expected runs; they explain why a node cap is not a user-facing spend or
deadline promise. The full derivation and parallelism caveat are in the
[adversarial addendum](runtime-adversarial-addendum.md).

### The honest complexity answer: valuable safeguards bundled into a fragile ritual

The portable runtime contains 7,358 executable source lines plus 120 behavior-changing policy/config
lines, and its public skill asks the host to carry a long sequence of framing, routing, splitting,
triage, reading, synthesis, verification, and attestations. None of those components is frivolous.
Portfolio framing, source-origin analysis, an adversary, and a fresh reviewer target real failure
modes of language models.

The problem is mandatory composition. The normal path needs a model to honor subtle instructions,
several workers to communicate through mutable files, and a human/operator to distinguish output
signals from genuine epistemic assurance. Each layer creates a new failure surface. Its complexity is
justifiable only when the value of a traceable investigation exceeds the cost of a potentially slower, more brittle
operation.

## Controlled same-question comparison

I ran a deliberately limited internal comparison: the same consequential-default question, the same
eight frozen local source documents, no external retrieval, a predeclared 20-item rubric, shuffled
anonymous outputs, and a fresh judge who could declare a tie. The full protocol, source hashes,
outputs, rubric, blind record, and its independent correction are retained in [comparison/](comparison/).

| Result | Direct bounded baseline | Aletheia protocol condition |
|---|---:|---:|
| **Corrected factual-rubric coverage** | **11/20** | **11/20** |
| Original blind record (superseded factual score) | 11/20 | 12/20 |
| Original judge's qualitative preference | — | 0.62, not independently auditable as blind |
| Unique source documents | 8 | 8 |
| Declared document-read assignments | 8 | **28** |
| Roles | 1 author/self-check | 4 leaves + synthesizer + fresh reviewer |
| Final prose words, excluding source table | 1,182 | 1,297 |

The original judge thought the Aletheia output won on two useful qualifications: historical wrong-body
incidents are not a current failure-rate estimate, and telemetry is not a spending/stop controller.
The direct baseline was better on bounded-tier arithmetic. But the judge also incorrectly awarded
Aletheia a rubric point for naming two favorable capped-triage topics; it named only one. Under the
predeclared all-or-nothing rubric, the score is a tie. Neither answer covered every required
implementation distinction. See the preserved [blind judgment](comparison/blind-judgment.md),
the corrected [result](comparison/results.md), and the [independent method audit](comparison/independent-method-audit.md).

This is evidence **only for a retestable hypothesis**: source-separated framing plus fresh review may
buy a modest calibration gain on a difficult audit-style synthesis. It is not cost-matched, not a live
retrieval test, not an end-to-end Aletheia run, not a latency measurement, and not a general win-rate
estimate. The tree/gate was initialized and passed, but source records were not injected, so it also
does not demonstrate the read/verification engine under realistic conditions.

The result is still informative despite being small: a direct workflow reached the same decision and
tied the factual rubric while requiring far less visible orchestration. The Aletheia arm also received
a documented fresh reviewer while the direct arm's self-check was only asserted. These asymmetric
staffing and audit trails mean the test cannot isolate an Aletheia-runtime effect. They support a
two-tier product and a proper matched-budget evaluation, not the entire ceremony as a default.

## How it stacks up

This is a product and workflow comparison, not a cross-vendor benchmark. No controlled test here
measures Aletheia against managed research products or other open-source systems. The comparison is
therefore deliberately qualitative; the prior independent audit's source-linked external survey is
available at [../2026-07-28-independent-project-audit/comparisons/alternatives.md](../2026-07-28-independent-project-audit/comparisons/alternatives.md).

| Alternative / pattern | Better choice today when | Aletheia's plausible edge | My verdict |
|---|---|---|---|
| **Bounded single lead agent** | Ordinary lookup, product research, coding reconnaissance, a fast decision, or any work with a strict budget. | Broad, contested questions where preserved disagreement, source origins, and a dossier can materially affect a decision. | This should be the default baseline and default product path. The controlled test says it is already close. |
| **Managed Deep Research** | A capable cited report is wanted with low setup, integrated browsing, and provider-managed execution controls. | Custom epistemic policy, local artifacts, source-origin auditing, and a bespoke review process matter more than convenience. | Usually the practical choice for normal broad reports; Aletheia has no measured superiority on matched tasks. |
| **Open research-agent stacks** | A team wants a deployable application, UI/API/MCP integration, model choice, or published operational configurations. | Aletheia's explicit concern with fake source diversity, adversarial framing, and claim scope is more philosophically developed. | Treat them as serious baselines, not straw men. Aletheia lacks their comparable end-to-end cost/latency/quality disclosure. |
| **Karpathy-style autoresearch** | The job is a closed, deterministic optimization problem with an immutable score. | It is not an open-web research substitute. | Borrow its evaluation discipline, not its literal agent loop. |

The Karpathy comparison is especially useful if made precisely. His autoresearch-style loop can keep
one mutable target, run a fixed-duration experiment, compare a stable scalar metric, retain/revert
with Git, and do it again. Open-world research has no equivalent trustworthy scalar: citation count,
LLM-judge score, link diversity, and prose length can all be gamed without becoming truer. So the
lesson is not "make Aletheia tiny" or "let it endlessly self-improve." The lesson is to require a
frozen task/source policy, equal budgets, an unweakened simple baseline, independent evaluation, and
a predeclared keep/revert rule for every change.

## What I would ship, and what I would block

I would **not** ship the current candidate as a default high-stakes or default-unlimited research
agent. I would preserve the ideas and ship two explicit service levels after the following gates.

### Blockers before a strong reliability claim

1. Bind every usable read to requested/final URL, expected/observed title or identifier, content hash,
   content type/error state, and provenance; reject or quarantine mismatches.
2. Replace shared JSON/Markdown mutation with transaction/lease/idempotency semantics, immutable IDs,
   and a declared tree manifest that controls synthesis membership.
3. Make a bounded mode the default. Enforce a cross-worker envelope for requests, reads, bytes,
   elapsed time, concurrency, model tokens/dollars where the host exposes them, and human-review
   obligations. Persist a truthful stopped/incomplete result on exhaustion.
4. Fix routing/selection determinism: preserve and rank aliases before choosing a representation,
   avoid cross-domain specialist cancellation, deduplicate explicit channels, and require an
   appropriate primary/decisive-source policy where the domain calls for it.
5. Add hostile retrieval, retry/replay, concurrent-writer, source-identity, and stale-browser cases to
   continuous regression tests. The 186 current tests are a good base, not this proof.

### Evidence needed before a performance claim

Run a preregistered multi-topic evaluation with a direct bounded baseline, bounded Aletheia, audited
Aletheia, and optionally a managed/open comparator where source conditions allow it. Freeze or record
source access; equalize model family and time/token/tool/read/dollar envelopes; blind expert/human
evaluation; report quality, harmful omissions, uncertainty calibration, source identity failures,
latency distribution, token/dollar ledger, and all failed runs. Ablate worker fan-out, adversary,
origin analysis, full reads, and fresh verification so the project learns which safeguards actually
earn their cost.

### Product direction

- **Default — bounded research:** one lead, small domain-appropriate source set, strict resource
  envelope, compact claim/source ledger, and one independent check for consequential claims.
- **Opt-in — audited investigation:** portfolio/framing, source-origin analysis, adversary,
  source-separated workers, and a dossier, but only with visible limits, the identity/state gates
  above, and human review for material conclusions.

Keep final decisions and writing single-threaded. Parallelize only genuinely independent evidence
gathering and advisory review. That retains Aletheia's best idea while avoiding a parallel-writer
filesystem swarm.

## Audit limits and evidence index

This is a literal source and controlled-output audit, not a proof that all live deployments fail or
that a competitor is universally better.

- All 7,358 executable runtime source lines and 120 behavior-changing policy/config lines were
  accounted for in contiguous coverage manifests; see [line-review/README.md](line-review/README.md).
- The audited portable source is byte-identical between frozen candidate
  `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5` and audit base `cbed478` for the scoped runtime.
- Hermetic probes reproduce the named state/source problems without network calls; the source-index
  race data and driver are in [probes/](probes/).
- The standard test suite passed 186/186. It does not exercise host-model compliance, live retrieval
  variance, exact source identity, or concurrent artifacts.
- The output comparison is one source-controlled task with one fresh judge. Its initial 12–11 blind
  score was corrected to an 11–11 tie under its own rubric. It has no credible token, dollar, latency,
  retrieval-quality, or population-level quality conclusion.
- The detailed controlled-tree state is ignored raw-run data; a compact committed record preserves its
  relevant status and hashes in [tree-execution-summary.json](comparison/tree-execution-summary.json).
  The missing immutable execution log is itself a limitation, not evidence of hidden execution.
- Live channel coverage was incomplete during audit: Brave was degraded and Reddit was down. This is
  recorded rather than hidden in [channel-health-2026-07-28.json](comparison/channel-health-2026-07-28.json).

## Bottom line

**Aletheia is better as an experimental, auditable investigation workbench than as a default research
agent.** Its intellectual design is stronger than most generic "agent swarm" recipes, but the runtime
does not yet enforce the things that make that design trustworthy. It may be worth its overhead for a
high-value, contested investigation with a human owner. For ordinary work, use a bounded single agent
or managed research tool; for high-stakes work, do not permit current `unlimited` without explicit
limits and human review. The project should earn every additional layer of complexity with a
cost-matched benchmark, not assume that more agents and artifacts mean better research.
