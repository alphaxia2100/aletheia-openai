# Independent audit of Aletheia OpenAI

**Audit date:** 2026-07-28
**Audited implementation:** bd5e1a50a491ee7c5ebe1382ace35c21f7909de5 (the unpromoted portable-runtime candidate)
**Stable runtime reference:** aletheia-prod-v0.5.0-openai.1^{} → addfaf648ca5577e00e393b2cb1c692a6302eac2
**Scope record:** [baseline.json](evidence/baseline.json)

## Verdict

**Aletheia is a promising high-scrutiny research protocol, not yet a proven better research product.**

Its best ideas are real: it makes an agent spell out competing framings, preserves a durable research
tree, distinguishes retrieval from full reads, looks for source-origin echo, calls for an adversary,
and requires a final claim-scope check. Those are unusually good epistemic instincts. The deterministic
control plane is small, portable, and substantially better tested than most agent prototypes.

But the project currently spends a great deal of complexity without evidence that the resulting answer
is better per unit of time, money, or operator attention than a strong bounded single-agent workflow.
The default is agent-paced unlimited: it has finite structural backstops, but no run-level resource or
cost governor and no runtime ledger for model tokens, dollar spend, elapsed time, or human-review time.
A separate correctness gap means a long but wrong, blocked, or error-page body can currently be marked
as a successful source read.

My honest recommendation is:

> **Make bounded single-agent research the normal path. Keep Aletheia's full protocol as an explicit,
> bounded audited/high-stakes escalation. Do not claim a general quality advantage until it wins a
> frozen, cost-matched, human-calibrated comparison.**

This is not a dismissal. It is the shortest route from an interesting research-engineering system to a
credible product: preserve the genuinely valuable safeguards, measure their marginal benefit, and stop
making every ordinary question pay for all of them.

## Executive scorecard

| Dimension | Independent assessment | Why |
|---|---|---|
| Deterministic engineering | **Strong for a research project** | 186/186 hermetic tests passed; preflight, portable install, manifest verification, and a smoke run passed. The runtime preserves run state, provenance, and telemetry. |
| Research methodology | **Thoughtful, differentiated** | Primary pursuit, origin/echo analysis, adversarial search, and claim-scope attestation address real failure modes that ordinary cited-report pipelines often ignore. |
| Research outcome proof | **Insufficient** | The record has two favorable capped-triage forward-test topics, one dynamic-outline diagnostic rejected on cost parity, and an older N=1 bakeoff—not a repeated, cost-matched, human-calibrated estimate of usefulness or truth. |
| Default economics and latency | **Poorly controlled** | The default is unlimited; logical tree budget is not a token/time/dollar quota, and the runtime cannot price or stop a costly run. |
| High-stakes correctness | **Not ready** | Current successful-read classification can accept the wrong long body. This invalidates a strong primary-read guarantee until an identity gate is promoted and validated. |
| Ordinary-user product fit | **Weak today** | Too much procedure, setup, and host-model compliance for common questions. A simpler bounded workflow is likely better on speed, price, and debuggability. |
| Potential in the narrow niche | **Real** | For valuable, contested, provenance-sensitive work where a human will inspect a dossier, the extra rigor could be worth it—but this remains a hypothesis to test. |

## What exists today

Aletheia is best understood as a **skill bundle and research protocol**, not a standalone research
service. Its Python tools create a directory-backed tree, route and retrieve sources, store reads and
source rows, calculate provenance/independence signals, and gate a final report/score. The host model
is expected to do the central intellectual work: frame the problem, choose sources, delegate read-only
workers, decide whether a branch is saturated, synthesize, and perform a semantically independent
fact-check.

The architecture is coherent:

    host model + research instructions
      → tree state / decision / artifact store
      → routed, parallel retrieval → agent source selection → serial full reads
      → leaf findings → central synthesis + adversary
      → lexical citation gate → fresh semantic review → claim-scope attestation

That division is a feature and a limitation. Filesystem artifacts, executable fingerprints, and
deterministic gates make a research run much more inspectable than a chat transcript. They cannot
guarantee that an underlying model followed the protocol well, chose a good counter-hypothesis,
recognized a bad source, or performed a genuinely independent semantic review.

The implementation is also in a nuanced release state. This audit examines the unpromoted
codex/exp-portable-sandbox-v06 candidate; the stable runtime tag remains the separate production
reference recorded above. The candidate shows good portability/security hygiene, but its own
documentation correctly says it is not an OS sandbox or an independently attested release. That is a
reasonable boundary for a personal skill bundle, not a high-assurance isolation claim.

## What is genuinely good

### 1. It treats research as evidence management, not report generation

The strongest design choice is its insistence that source count is not corroboration. The protocol
tries to distinguish independent origins from echoes, preserve the decision trail, chase primary
sources, and make an adversarial branch a first-class part of the workflow. It also separates a
mechanical lexical check from the semantic claim judgment instead of pretending keyword overlap proves
a claim.

That is a better intellectual model than many generic search, summarize, cite agent designs. It is
particularly relevant where a polished report can hide a shared-origin error, an omitted contrary
result, or a citation that merely looks relevant.

### 2. The boring engineering is unusually responsible

The audit reproduced a passing preflight, portable-copy install, manifest check, and tree-state smoke
run. The full hermetic suite passed **186/186** tests. The suite covers state caps, routing, source
selection traces, claim-score bookkeeping, portable installs, disabled connectors, browser boundaries,
and several regressions. The portable runtime is only about 47 files / 468 KB, so its problem is not
binary bloat.

The code also has useful observability: runtime and channel-configuration fingerprints, per-node
decisions, reads, source rows, retrieval/read telemetry, and a post-draft claim-scope hash attestation.
Those properties matter when a run must be inspected, reproduced as far as web/model variance allows,
or diagnosed after a failure.

See the detailed [architecture audit](notes/architecture-audit.md) and
[runtime/test audit](benchmarks/runtime-and-cost.md).

### 3. The project's self-criticism is an asset

The repository preserves failed experiments and documents defects such as wrong-body reads, routing
mistakes, cost-parity failures, convergence ambiguity, and oversize handoffs. This does not prove the
current system is correct; it is nevertheless a healthy engineering signal. The project is more
credible for admitting how it can fail than it would be if it simply reported a good-looking final
brief.

## The material problems

### P0 for high-stakes claims: source-read identity is not verified

The audited read path considers a source successful largely because the returned body has at least
1,500 characters. It does not establish that the body is the requested document. The project has
already reproduced wrong GRADE documents, an anti-bot interstitial, and an arXiv error shell being
accepted under that rule. A more conservative identity-gate experiment exists on a different,
unpromoted branch, but is not part of the audited target.

This is not an abstract corner case. If a system says it read the primary in full, users can reasonably
treat that as an evidentiary guarantee. A length threshold does not earn it. Until a title/URL/content
identity gate is shipped and tested against adversarial fixtures, Aletheia should describe these
artifacts as **fetched text associated with a URL**, not verified primary reads.

Evidence: [architecture finding A-01](notes/architecture-audit.md#material-findings-and-risks) and
[investigate.py](../../.cursor/skills/aletheia-research/scripts/investigate.py#L590-L609).

### P1: the default is unbounded in the resources users actually care about

Unlimited is the documented default. In code it has a synthetic 1,000,000 tree budget, depth 99, and a
512-node backstop; it has no per-leaf round cap. Max raises the node backstop to 2,048. Neither mode has
a global cap on model tokens, paid connector calls, elapsed time, direct/manual reads, or dollars. The
stop condition is an agent's subjective judgment of saturation.

That is a legitimate research posture when a user explicitly authorizes a day-long investigation. It is
a bad default product contract. A person asking a normal question cannot predict whether they are
initiating a short evidence pass or a multi-agent open-ended campaign.

The term budget is potentially misleading here: it governs tree arithmetic and bounded-tier rounds, not
spend. The current Python runtime does not make model API calls and does not record model name, tokens,
cache hits, dollar cost, total agent runtime, or human review time. It cannot truthfully tell the user
what a run cost or stop a run at a chosen dollar limit.

Evidence: [runtime/cost analysis](benchmarks/runtime-and-cost.md#the-actual-runtime-and-cost-model),
[treestate.py](../../.cursor/skills/aletheia-research/scripts/treestate.py#L190-L258), and
[report.py](../../.cursor/skills/aletheia-research/scripts/report.py#L229-L287).

### P1: the latency structure is expensive even though Python is fast

The local control plane is not the bottleneck: this audit's synthetic scheduler test found three
100-ms retrievals completed in about 103 ms, confirming parallel fan-out. Four 50-ms selected full
reads took about 218 ms, confirming that reads are serial **within one leaf-engine invocation**. Real
sources are much slower and can retry; then the host must inspect findings, synthesize, and conduct an
additional fact-check. The host may run separate leaf workers concurrently, but that scheduling is
outside this Python engine.

For the documented normal engine path, one leaf round can structurally reach about **36 retrieval
requests** (six channels × up to three zero-result retries × two agent-triage manifests) plus four
serial full reads before any manual primary chasing or model verification. This is an upper-envelope
shape—not a claim that every healthy round makes 36 calls—but it explains why round count is not a
credible cost or latency budget.

The project's own July 27 self-study offers a scale signal: 37 rounds, 1,137 retrieved records, 72
engine-selected reads, 97 direct/manual read artifacts, and 347.4 seconds of reader time, before model
time and human review. That is the right scale for a serious investigation; it is not normal question
answering.

Evidence: [microbenchmark and operating model](benchmarks/runtime-and-cost.md#offline-scheduler-microbenchmark)
and [the project's recorded self-study](../../docs/research/2026-07-27-agent-output-quality/score.json).

### P1: the protocol's most important properties are instructions, not constraints

The system does constrain some artifacts and scoring states, but it cannot mechanically ensure that the
host uses genuinely distinct framings, spawns the intended workers, reads the decisive source,
disconfirms its leading theory, uses a different semantic reviewer, or stops only after convergence.
Those are long natural-language obligations in SKILL.md.

This creates an uncomfortable gap: a model can complete a polished-looking directory tree while
executing only part of the intended procedure. Unit tests of deterministic code are valuable, but do
not establish protocol compliance or research quality. The more the product asks users to trust the
full process, the more it needs executable stop controls, trace validation, and end-to-end evaluations.

### P1: outcome evidence is too small to justify superiority claims

The strongest internal comparative evidence is useful diagnostic work, not a general performance
study: two favorable capped-triage forward-test topics; one additional dynamic-outline topic that was
rejected for cost mismatch (97 observed read artifacts versus 41); and an older one-topic bakeoff. The
repository itself says the favorable tests do not estimate a general win rate, and its adversary review
says no existing evaluation is cost-matched, multi-topic, and human-calibrated.

There is a more subtle issue: a claim-scope/citation score can demonstrate that cited claims have been
reviewed under a process. It cannot demonstrate that the answer covered the decisive evidence, chose
the right questions, avoided shared-origin bias, or helped the user make a better decision. The
project's own earlier review found omitted load-bearing claims and unsupported rows; that is evidence
the check is valuable, not evidence that it solves answer correctness.

The defensible current claim is **better research hygiene and observability**, not **proven better
answers**.

Evidence: [architecture finding A-06](notes/architecture-audit.md#material-findings-and-risks),
[forward-test record](../../docs/evals/openai-v0.5-forward-test.md), and
[bakeoff record](../../docs/evals/2026-07-08-creatine-cognition-bakeoff.md).

### P1/P2: routing, source coverage, handoffs, and release topology add operator cost

- The router is a hand-written keyword taxonomy. It has known domain gaps and has previously misrouted
  a meta-research question. Agent overrides help, but move correctness back into prompt compliance.
- A dated, deliberately keyless health probe found 11/13 core endpoints live; Brave was degraded
  without a key and Reddit returned HTTP 502. This is not a packaging flaw, but it means source variety
  is conditional on configuration and the current web.
- Full bundles can be very large yet omit some tree-state artifacts, which makes agent-to-agent handoff
  costly while still not literally complete.
- The repository's many experiment branches are an admirable lab notebook but a difficult release
  story. A user can easily confuse a documented experimental safeguard with production behavior.

These are normal problems for an ambitious research system. They become material because the protocol
already has high operational and cognitive load.

## Is it too slow, too expensive, too complex, or simply not very good?

### Slow and expensive?

**For ordinary work: yes in design, and inadequately measured in dollars.** The default intentionally
multiplies reasoning turns, source retrieval, serial reading, artifact work, adversarial review, and
independent verification. That is slower than a bounded agent deliberately because it does more.

It would be wrong to put a universal dollar figure on it: the code has no model ledger, no paid API was
used in this audit, and model/harness/source conditions dominate the cost. The accurate criticism is
not that it costs exactly too much; it is **the product provides no reliable economic envelope despite
choosing an unbounded default**.

**For high-value investigations: not necessarily.** If the alternative is a human spending a day
manually reconstructing evidence and provenance, a local dossier with good auditability can be cheap.
That value proposition must be made explicit and tested, not inferred from methodology alone.

### Too complex?

**The components are mostly justified; their mandatory combination is not yet justified as a default.**
Tree state, source-origin analysis, adversarial inquiry, a fresh reviewer, and artifact persistence
each address a real failure mode. The failure is product architecture: the routine path makes a model
carry a long, fragile procedure across all of them, without a budget controller or measured marginal
return.

The practical solution is not to delete safeguards. It is to make them conditional. Most queries need
a bounded source/claim pass; only some deserve portfolio construction, workers, origin analysis,
adversarial deepening, and a full dossier.

### Not great compared with other people's workflows?

**It is better than many generic agent workflows at reasoning about provenance and auditability. It is
not currently better proven at delivering useful answers.**

A strong single agent with a short source/claim ledger, an explicit time/read/tool cap, and a fresh
final reviewer is a credible practical baseline: it is likely to have less coordination loss, fewer
context transfers, a simpler failure surface, and clearer resource control. That is an architectural
recommendation, not a measured cross-product result—and it is the baseline Aletheia must beat.

Managed Deep Research products offer a different practical trade-off for ordinary reports: less local
setup, integrated browsing/tooling, and documented controls such as OpenAI's max_tool_calls. Open
systems such as LangChain Open Deep Research and GPT Researcher have broader deployable application
surfaces and publish recognizable benchmark/cost machinery, although their reported quality and price
are self-reported and configuration-dependent. Aletheia's possible edge is explicit epistemic policy,
not established outcome superiority.

The full comparison, sources, and limitations are in
[comparisons/alternatives.md](comparisons/alternatives.md).

## The Karpathy comparison: take the lesson, not the literal architecture

Karpathy's autoresearch is not a substitute for open-web research. It works because an ML-training
experiment can have one immutable evaluation harness, one mutable target, a fixed five-minute run, and
a comparable numerical outcome. Factual research has no trustworthy equivalent scalar metric: an agent
can optimize citation count, verbosity, an LLM judge, or even apparent source diversity while becoming
less accurate.

The transferable lesson is much more valuable than a superficial make-Aletheia-tiny comparison:

1. Freeze the task set, source-access policy, and evaluation before changing the workflow.
2. Give every contender the same model family and explicit token/time/read/tool budget.
3. Retain a simple baseline that cannot be quietly weakened.
4. Use blinded human/domain evaluation for decision usefulness and harmful omissions.
5. Log every run, including failures.
6. Promote or revert a change based on a predeclared result, not a compelling anecdote.

Aletheia already has the beginnings of the artifacts and Git discipline needed for this. It needs a
small, stable public evaluation contract more than it needs another layer of autonomous self-improvement.

## How it stacks up to alternatives

| Choice | Better than Aletheia today when… | Aletheia may be better when… | Honest recommendation |
|---|---|---|---|
| **Bounded single agent** | The question is ordinary, time-sensitive, narrow, or needs a concise answer. It wins on simplicity, cost control, and debuggability. | The topic is genuinely broad/contested and the user needs provenance, disagreement, and an inspectable dossier. | Make this the default baseline and default product path. |
| **OpenAI / Claude managed research** | A user wants a capable report with little local setup and managed browsing/tool execution. | Custom source-origin policy and durable local forensic artifacts matter more than convenience. | Usually choose managed research first for normal broad reports; spot-check consequential claims. |
| **LangChain Open Deep Research / GPT Researcher** | A team needs a deployable general-purpose application, integration surface, or published operating configurations. | The central concern is source provenance, echo, adversarial framing, and strict claim-scope audit. | Use as serious open baselines, not as straw men; compare on identical tasks and budgets. |
| **Anthropic-style orchestrator/workers** | The question has independent, parallelizable subproblems and the work is valuable enough to absorb a large token premium. | Same situation; this is architectural validation of Aletheia's narrow niche, not a general default. | Parallelize evidence gathering, centralize final judgment/writing. |
| **Karpathy-style experiment loop** | The work is a deterministic optimization problem with an immutable measurable objective. | It does not apply directly to open-web truth seeking. | Borrow its evaluation discipline, not its literal five-minute/autonomous loop. |

External evidence points both ways. Anthropic reports an internal breadth-first benefit from a
multi-agent research system but also about 15× chat-token use; that supports the costly niche, not
the universal case. Conversely, Tran and Kiela found the single-agent approaches they evaluated
matched or outperformed multi-agent variants under matched requested thinking-token-budget caps,
except when single-agent context use became sufficiently degraded. Neither directly evaluates Aletheia,
so neither settles its outcome; together they make a cost-matched Aletheia test non-negotiable.

## What to do next

### Immediate release blockers

1. **Promote an identity gate for full reads.** Test requested URL, canonical URL, title/content
   agreement, anti-bot/error signatures, and adversarial wrong-document fixtures. Do not use
   successful read to mean merely long text.
2. **Change the public default to a finite mode.** Add a clearly named scout/standard path with hard
   maximums for tool calls, selected reads, agent turns, elapsed time, and—where the host exposes
   it—tokens/dollars. Require explicit opt-in for unlimited/max.
3. **Add a run-level resource ledger.** Persist model/cost/time data from the host when available;
   otherwise state unmetered prominently rather than displaying an abstract logical budget as if it
   were spend.

### Next product/evaluation milestone

Run a pre-registered benchmark before adding more channels or meta-agent machinery:

| Element | Minimum credible design |
|---|---|
| Tasks | A diverse frozen set, including ordinary lookup, current/product research, technical research, and truly contested/high-stakes questions. |
| Contenders | Direct bounded single-agent baseline; Aletheia bounded; Aletheia audited; optionally a managed/open competitor under allowed identical source policy. |
| Parity | Same model family where possible, same time/token/tool/read/dollar envelope, pinned source snapshots or recorded access conditions. |
| Evaluation | Blinded domain/human rubric for factual correctness, decisive-source recall, counterexample/harmful-omission recall, calibrated uncertainty, and decision usefulness. |
| Reporting | Full latency distribution, token/dollar ledger, retrieval/read failures, source origin/authority measures, claim-scope coverage, artifact size, and all non-wins. |
| Promotion rule | Declare minimum practical improvement and maximum cost/latency regression before the run; retain the baseline if the result is inconclusive. |

Then ablate one safeguard at a time: portfolio, adversary, origin audit, full reading, fresh verifier,
and worker fan-out. Some will likely be highly valuable only for medical/legal/policy or other
consequential domains. That is a success: it turns a universal ritual into a service level justified
by evidence.

### Product direction I would choose

Build two explicit modes rather than one grand default:

- **Bounded research (default):** one lead, a small domain-appropriate source set, source/claim table,
  strict resource envelope, and one fresh verification pass for consequential claims.
- **Audited investigation (opt-in):** the current portfolio/origin/adversary/worker/dossier machinery,
  but with user-visible caps, an identity gate, a stop card, and mandatory human review for material
  conclusions.

Keep final decisions and writing single-threaded. Parallel evidence gathering is often sensible;
parallel writers and unstructured swarms are usually not. This retains Aletheia's most defensible
architectural choice while removing the false choice between a shallow answer and an unbounded
research campaign.

## Audit method, reproducibility, and limits

This audit did not rely solely on prose review. It inspected the code and release topology, ran the
hermetic test suite and portability/preflight path, measured the scheduler with controlled synthetic
I/O, performed a deliberately keyless live connector-health snapshot, examined the project's own
evaluations and self-audits, and compared primary documentation/research for relevant alternatives.
The audit used an independent adversarial branch and a fresh-context claim reviewer before finalizing
the report; see the [verifier's claim ledger](evidence/fresh-context-verification.md).

Important boundaries:

- No model or paid connector API calls were made, so this audit cannot state a real end-to-end dollar
  price or live answer-quality score.
- The scheduler benchmark tests structure (parallel retrieval and serial reads), not internet latency.
- The health snapshot is dated and keyless; 11/13 live probes does not estimate production reliability.
- Vendor/product comparisons are mainly first-party documentation. They establish available controls
  and published claims, not an independent quality ranking.
- The audited commit is a candidate, while the stable runtime is separately tagged. Conclusions about
  that candidate should not be silently attributed to all historical releases.

## Evidence index

- [Baseline / release record](evidence/baseline.json)
- [Detailed code and release audit](notes/architecture-audit.md)
- [Reproducible architecture-command log](evidence/architecture-commands.md)
- [Fresh-context verification memo](evidence/fresh-context-verification.md)
- [Final claim-scope review](evidence/final-claim-scope-review.md) and
  [compact attestation summary](evidence/claim-attestation-summary.json)
- [Runtime, cost, and scheduler benchmark](benchmarks/runtime-and-cost.md)
- [Machine-readable microbenchmark result](benchmarks/runtime_microbenchmark-result.json)
- [Keyless channel-health snapshot](benchmarks/keyless-channel-health-2026-07-28.json)
- [Alternatives and Karpathy comparison](comparisons/alternatives.md)
- Ignored raw research-run state in research-runs/2026-07-28-184302-independent-project-audit/; it is
  retained locally for replay but excluded because it contains fetched third-party content.

## Bottom line, without hedging

**Aletheia is not bad; it is ambitious in the right intellectual directions. But it is currently too
uncontrolled, slow, and complex to be the default way to answer ordinary research questions, and it
has not yet earned a claim that the extra machinery produces better answers than simpler workflows.**

Its near-term opportunity is not more agents. It is to make the basic bounded workflow excellent, fix
source-read identity, measure real cost and latency, and force every expensive safeguard to earn its
place against a frozen baseline. If it does that, it could become a genuinely distinctive tool for
research where provenance and disconfirmation matter. Until then, present it candidly as an
experimental high-rigor workbench—not a proven universal research winner.
