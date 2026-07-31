# Adversarial review: the “exclusive source access” thesis

**Question reviewed.** If Aletheia can access sources that ordinary search cannot,
should it be *much* better than a direct research agent?

**Independent verdict (2026-07-31).** This is a credible product hypothesis, not a
demonstrated property of the current system.  The active Aletheia bundle gives a
lead agent convenient access to several public, differently indexed source
surfaces.  That can be extremely valuable on a task whose decisive material is
poorly ranked by one general web index.  It does **not** yet establish that the
underlying sources are exclusive to Aletheia, that the router reliably finds the
right specialist surface, that a source body is the requested source, or that the
extra discoveries improve a user's decision after their cost and delay are paid.

The right claim today is: **“Aletheia may improve discovery on source-index
blind-spot tasks; test it as a source-access bundle.”**  The claims “Aletheia has
exclusive sources” and “therefore it is much better in general” are unsupported.
The latter should not be used in product positioning until the experiment below
passes.

| Proposition | Audit grade | Why |
|---|---:|---|
| Multiple independent indexes can surface a useful source a single generic index misses. | **B (plausible)** | This follows from differing coverage/ranking and is a useful reason to test the bundle. |
| Current Aletheia has access to sources a capable direct agent cannot lawfully access. | **D (unproven)** | The enabled inventory is principally public/no-key or ordinary credentialed APIs; no comparison establishes an otherwise inaccessible corpus. |
| Current routing and reading reliably convert extra indexes into usable evidence. | **D** | The deep audit reproduced routing and read-identity failures; the live routing probes below expose important coverage holes. |
| Aletheia is already “much much better” because of access. | **F (no outcome evidence)** | The only controlled head-to-head froze the source packet and tied after correction; no live-retrieval, resource-matched, multi-topic access test exists. |

This review deliberately attacks the appealing interpretation, not the idea of
specialist retrieval itself.  A narrow, repeatable access win would be a very good
reason to invest in v2.  It is not a reason to assume that more channels, agents,
or artifacts are the cause of a better answer.

## 1. What the present evidence actually says

### 1.1 The active bundle is broad, but breadth is not exclusivity

The local channel registry currently lists twelve configured channels: general
web/index discovery (Brave, DuckDuckGo, Marginalia), academic indexes (OpenAlex,
arXiv, Europe PMC), community/code sources (Reddit, Hacker News, GitHub, Stack
Exchange), and Wikipedia/Open Library.  The registry itself classifies several of
these as `lead_gen`, meaning they should lead to a primary rather than be cited as
evidence.  It also shows that most are public, free, optional-token, or
free-key surfaces—not a proprietary corpus that a direct agent could never reach.
See the [channel registry](../../../.cursor/skills/channel-retrieval/channels.json)
and its [active configuration tool](../../../.cursor/skills/channel-retrieval/scripts/channels.py).

That is still useful product work.  A user who ordinarily performs one generic
search may not know to query Europe PMC, arXiv, GitHub, a forum, or a citation
index.  Packaging those routes, source-role rules, and resolvers can produce an
*access-bundle advantage*.  But that is different from either of these stronger
claims:

1. **Architecture advantage:** a direct agent given the same public channel
   adapters cannot do as well.
2. **Entitlement advantage:** Aletheia has lawful rights to data a comparator
   cannot access.

The former requires a same-access ablation.  The latter requires a separate
licensing/privacy comparison; it is not evidence that the research protocol is
better.  A user-connected private corpus may be decisive, but its value belongs to
the authorization and data integration, and must not be marketed as general web
superiority.

There is a live availability qualification.  On 2026-07-31, Aletheia's own
`doctor.py` found **12/13 core health checks live** but marked Brave `warn` because
`BRAVE_API_KEY` was absent.  GitHub was live but rate-limited for unauthenticated
use.  A health probe means a single request worked; it does not prove load,
coverage, result quality, or reproducibility under a parallel run.  Any evaluation
must record this exact configuration and cannot silently describe all configured
channels as available.

### 1.2 The current router weakens the blanket access story

The current route policy is a keyword taxonomy, not a general source-access
oracle.  Its own comments identify missing specialist adapters: legal routing
mentions a future CourtListener client; finance routing mentions a future SEC
EDGAR client.  In live probes on the current checkout:

| Probe question | Channels returned | Adversarial implication |
|---|---|---|
| “current legal status of software copyright litigation” | DuckDuckGo, Marginalia, OpenAlex, Reddit | No legal-primary connector was selected.  A generic direct agent that reaches an official court/regulator site may be better positioned. |
| “assess a startup's latest 10-K and valuation” | DuckDuckGo, Marginalia, OpenAlex, Reddit, Hacker News | No EDGAR/filing connector was selected; academic/community routes are a weak substitute for the authoritative record. |
| clinical ML risk prediction | DuckDuckGo, Marginalia, Europe PMC, OpenAlex, Reddit | Relevant biomedical coverage is possible, but arXiv/GitHub/Stack Exchange were excluded by the topic classifier. |

The source code confirms both the route choices and the proposed-but-absent legal
and finance adapters in [router.py](../../../.cursor/skills/aletheia-research/scripts/router.py).
These probes do **not** prove that a direct baseline wins.  They do show that the
system cannot infer a broad “Aletheia reaches the otherwise unreachable” conclusion
from the number of registered connectors.  It must prove channel/task coverage
case by case.

### 1.3 Existing head-to-head evidence intentionally cannot test access

The July 28 controlled comparison gave both conditions the same eight frozen
documents.  After an independent correction, the direct bounded condition and the
Aletheia protocol condition each covered **11/20** factual-rubric items, while the
Aletheia condition declared 28 document-read assignments to the direct condition's
eight.  That is evidence about source **use**, synthesis, and workflow overhead
after access is equal; it says nothing about who would discover a decisive source
on the live web.  It neither refutes nor validates the access hypothesis.

It does matter because it rules out an invalid syllogism: “more source access
exists; therefore the current workflow automatically exploits it better.”  The
prior audit also records a one-topic experiment whose authors explicitly attribute
much of the difference to *retrieval luck*, not architecture.  See the [deep
runtime audit](../../2026-07-28-deep-runtime-and-head-to-head/report.md), its
[independent method correction](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md),
and the project's [evaluation review](../../../docs/research/2026-07-27-agent-output-quality/branches/evaluation.md).

### 1.4 A hit is not source access, and source access is not answer quality

For this claim, a URL in a result list is not a unit of success.  The minimum
causal chain is:

```text
index result
  → source-family discovery
  → lawful fetch and identity-compatible body
  → complete enough text/span
  → appropriate selection
  → support or contradiction of a specific claim
  → a changed, independently judged decision or answer
```

The deep audit reproduced a long wrong body being recorded as a successful read,
and identified routing, ordering, duplicate-read, and capability problems.  Until
the proposed v2 identity receipt exists, a claimed “unique source” can be a
redirect, mirror, anti-bot page, stale browser content, or irrelevant body stored
under a desired URL.  That invalidates the numerator of an access benchmark, not
just a polish metric.  The exact failure evidence and required identity gate are
in the [audit report](../../2026-07-28-deep-runtime-and-head-to-head/report.md).

For evaluation, define four distinct quantities instead of collapsing them into
“sources found”:

| Quantity | Counts only when | What it can establish |
|---|---|---|
| **Discovery** | A canonical source family appears in a persisted candidate manifest. | Index/ranking reach. |
| **Verified usable access** | Requested/final URL, expected/observed identity, body hash, completeness state, and authorization result pass a gate. | The system actually obtained the claimed document. |
| **Incremental evidence** | An exact span is attached to a claim/counterclaim and the family was absent from all matched baseline attempts. | The extra access produced usable information, not a duplicate URL. |
| **Decisive incremental evidence** | Independent adjudicators judge that the source materially changes a pre-specified must-cover fact, recommendation, or uncertainty. | The only source-level result that begins to justify a “much better” product claim. |

Source families must be clustered by origin, version, DOI/arXiv/PMID/official
identifier, and mirror relation.  Counting a publisher page, repository copy,
abstract record, and copied press coverage as four exclusive discoveries would
manufacture an advantage.

## 2. Confounds that can create a fake access win

| Confound | How it falsely favors or harms Aletheia | Required control |
|---|---|---|
| **Straw-man “traditional search.”** | Giving the baseline one weak search box while Aletheia gets twelve public APIs measures tool deprivation, not protocol quality. | Name the baseline precisely; run both a consumer/general-web baseline and a capable direct lead with the same expanded channel adapters. |
| **More economic work.** | More channel calls, workers, tokens, reranking, and full reads buy more chances to find a source. | Match total token, request, byte/read, dollar, concurrency, and deadline envelopes; also publish quality/cost frontiers. |
| **Different source entitlements.** | Paid, authenticated, private, or browser-session data can be decisive independent of orchestration. | Freeze credentials, domains, terms, and session policy.  Report entitlement benefit separately from workflow benefit. |
| **Time drift and index volatility.** | A source appears, disappears, is re-ranked, or rate-limited between arms. | Run matched arms interleaved/concurrently with isolated caches; preserve result manifests and source snapshots/hashes where lawful. |
| **Prompt/model/operator differences.** | Better query wording, a stronger model, or human rescue looks like source access. | Same model/version, prompt skeleton, human-intervention rule, tool wrapper, and randomized seed policy; log every intervention. |
| **Aletheia-to-baseline leakage.** | A baseline sees a source title, query, draft, or reviewer memo produced by the treatment. | Isolate workspaces and randomization map; no cross-arm artifacts until all final outputs are sealed. |
| **URL/mirror inflation.** | The treatment reports many URLs from the same underlying source. | Evaluate distinct origin/version families, not URL count or channel count. |
| **Retrieval without reading.** | Snippets, landing pages, blocked pages, and wrong bodies are called evidence. | Require typed identity/completeness receipts and exact evidence spans before scoring. |
| **Curated win-only tasks.** | A benchmark selected because a specialty index happens to contain the answer overstates general performance. | Pre-register a source-access stress stratum *and* a representative task stratum; report them separately. |
| **Post-hoc gold set.** | Evaluators see the winning answer then decide its sources were “decisive.” | Independent curators freeze must-cover claims/source families and harm cases before runs; use a second blinded panel for unexpected evidence. |
| **Citation-count or prose bias.** | More citations/longer essays look more researched even when no decision changes. | Atomic, blinded claim/decision grading; separately score harmful omissions, calibration, and source identity. |
| **Failure censoring.** | Rate limits, empty channels, and stuck workers disappear from successful-run averages. | Intention-to-treat reporting: every scheduled run, failure, retry, timeout, and degraded channel stays in the denominator. |
| **Benchmark contamination.** | Models may have memorized prominent questions/sources, masking retrieval. | Prefer recent, versioned, or locally sourced tasks; annotate likely memorization and include source-discovery traces. |

## 3. The experiment that answers the question: a true 2×2

Use a factorial design, not a one-arm bakeoff.  Let the first factor be the
**source contract**, and the second be the **research workflow**.

| | **S0: conventional/general-web source contract** | **S1: expanded Aletheia source contract** |
|---|---|---|
| **W0: direct bounded lead** | `D0` — serious direct baseline: one accountable agent, finite plan, normal web/direct-URL capability, source/claim table, one check. | `D1` — same direct lead, same budget, but granted the identical enabled specialist adapters and resolver policy as Aletheia. |
| **W1: Aletheia workflow** | `A0` — Aletheia's planning/verification process constrained to S0. | `A1` — full bounded Aletheia configuration under S1. |

This produces three interpretable effects:

```text
Pure access effect       = D1 - D0
Workflow effect at S0    = A0 - D0
Access × workflow effect = (A1 - A0) - (D1 - D0)
```

`D1 - D0` is the load-bearing comparison for the user's premise.  It asks whether
the *bundle of additional sources* helps a competent, simple agent.  `A1 - D1`
asks whether Aletheia's orchestration makes better use of the same access.  A
headline based only on `A1 - D0` cannot distinguish either from “Aletheia was
given more tools.”

The source contract needs an executable manifest, not prose:

```text
run_id, task_id, arm, model/version, prompt hash, seed policy
allowed channels + versions + credentials class + query limits
resolver/read policy + browser/session/cache policy
max input/output/reasoning tokens, tool calls, reads, bytes, dollars,
wall time, concurrency, retries, and human interventions
source snapshots/result manifests and clock window
```

The exact live configuration matters.  For example, the July 31 run must not
claim Brave in S1 if it is keyless/degraded.  Either exclude it from both source
contracts, supply equivalent authorized credentials to the specified arm, or mark
the run invalid for that access comparison.

### A strong baseline is two baselines, not one

`D0` tests real bundle value against the ordinary user experience.  `D1` prevents
the team from attributing public-index access to Aletheia's agent architecture.
Both are necessary.  A managed-research provider can be added as an external
comparison, but it should be reported under its own source/terms contract rather
than smuggled into this causal 2×2.

For a private or paid corpus, run a separate **entitlement** study: direct and
Aletheia conditions either both receive the lawful corpus or neither does.  If
only one can receive it, the honest result is “this integration has data access
value,” not “Aletheia's research workflow is superior.”

### Test corpus and execution protocol

1. **Freeze two held-out strata before implementation changes.**
   - *Source-access stress tasks:* independent curators document a genuinely
     relevant primary, counterexample, or versioned artifact that is plausibly
     missed by one generic index.  This tests the hypothesis at its strongest.
   - *Representative tasks:* recent, ordinary technical/product/policy/science
     questions sampled to reflect intended use.  These prevent an access
     diagnostic from becoming a general product claim.
   Include negative controls where generic web is sufficient and cases where a
   specialist source contradicts the popular web narrative.
2. **Build the hidden rubric before runs.**  Curators create atomic must-cover,
   harmful-omission, uncertainty, and source-family criteria without seeing arm
   outputs.  Keep the core sources secret from the generators.  A separate
   blinded panel handles legitimate unexpected discoveries so the rubric does not
   punish novelty.
3. **Run at least three independent, interleaved trials per task/arm.**  Use a
   task-time block and a common seed schedule where the provider permits it.
   More repetitions are needed if model variance dominates.  A first pilot can
   diagnose telemetry; it cannot support the product claim.
4. **Seal final outputs and traces.**  Strip arm identity for outcome judges;
   randomize A/B order; retain raw traces for a different provenance auditor.
   Treat timeout, identity mismatch, channel failure, and an honest abstention as
   outcomes—not discarded noise.
5. **Analyze paired effects and uncertainty.**  Use task-stratified paired
   intervals/mixed effects or an equivalent preregistered estimator.  Report all
   four cells, the access main effect, workflow main effect, interaction, and
   per-stratum results; do not replace them with a single LLM preference score.

A reproducible frozen-source subtest should accompany the live test.  It holds
the evidence packet constant and compares `D1` to `A1` on source use.  The prior
11–11 tie is an early version of that diagnostic.  It is useful precisely because
it cannot be misrepresented as evidence for retrieval reach.

## 4. Outcomes that would make access matter

### 4.1 Primary outcomes

Score at the task/trial level first; aggregate only afterward.

| Layer | Metric | Why it is needed |
|---|---|---|
| **Reach** | Recall of pre-adjudicated decisive source *families* in candidates; verified-usable source recall; time/cost to first decisive source. | Separates an index advantage from writing skill. |
| **Use** | Recall of decisive/counterevidence families actually attached to claims; exact-span and source-identity validity. | A source that is retrieved but ignored has no user value. |
| **Decision quality** | Blinded correct-and-complete decision/answer rate, weighted must-cover coverage, harmful omissions, and appropriate abstention. | The user cares whether the answer changed for the right reason. |
| **Calibration and safety** | Unsupported/contradicted claim rate, overconfidence, citation identity failures, and failure-to-disclose gaps. | Extra sources can create false confidence or citation laundering. |
| **Economics/reliability** | End-to-end P50/P95 latency, dollars, tokens, requests, reads/bytes, retries, failure rate, and human effort. | “Better” must survive the cost and latency that produced it. |

Useful derived measures are:

- **Decisive-evidence recovery (DER):** fraction of tasks where the arm
  identity-verifiably acquired at least one independently adjudicated decisive
  source family within its envelope.
- **Incremental decisive-evidence yield (IDEY):** DER sources found by the
  treatment that no matched baseline trial found, after origin/mirror collapse.
- **Decision-complete correctness (DCC):** a blinded binary or calibrated score
  that requires correct conclusion, material must-cover facts, no harmful
  omission, and honest uncertainty where the evidence is unresolved.
- **Cost per additional decision-complete answer:** total observed spend divided
  by the DCC improvement, reported with uncertainty rather than hidden behind
  average “rounds.”

### 4.2 Proposed promotion thresholds

These are deliberately **project policy thresholds, not universal scientific
constants**.  They should be frozen before data collection and tuned to the
decision class.  A health/legal use case may choose a lower benefit threshold but
a stricter safety margin; a casual research mode should demand efficiency.

| Decision | Minimum proposed evidence |
|---|---|
| Say **“the expanded source bundle has an access advantage”** | In the held-out source-access stratum, `D1 - D0` improves DER by **at least 15 percentage points** with a paired 95% lower bound above **5 points**, and does not worsen DCC or critical-error rate under the same hard envelope. |
| Say **“much better on source-dependent tasks”** | Replicate on two independently frozen cohorts; improve DER by **≥20 points** (lower bound ≥10) *and* DCC by **≥15 points** (lower bound ≥5), with no material safety degradation.  Report this only for that stratum unless the representative cohort also passes. |
| Make it a **default** rather than an escalation | On the representative cohort, show a positive DCC effect whose lower bound exceeds a predeclared smallest worthwhile effect (provisionally **5 points**) at equal budget, or demonstrate a better quality/cost frontier.  It must not materially worsen P95 latency, cost per DCC answer, or critical-error rate. |
| Keep an individual connector/complex safeguard | Its feature-off ablation must pass identity/reliability gates and produce a replicated outcome or value gain above its predeclared smallest worthwhile effect.  More hits, citations, or prose are insufficient. |
| Offer an expensive high-stakes mode | The lower credible bound of its segment-specific incremental decision value must exceed incremental run and delay cost, and the user must approve the envelope up front. |

The numerical margins prevent a tiny, noisy gain from becoming a “much better”
story.  They also make a negative result meaningful: if a sufficiently powered
study's confidence interval lies wholly below the 5-point DCC or 10-point DER
smallest worthwhile margins, the strong access claim is falsified for that
population—not merely “not statistically significant.”

## 5. What would validate, narrow, or falsify the premise

| Observed 2×2 pattern | Honest conclusion | Product action |
|---|---|---|
| `D1 > D0`; `A1 ≈ D1` | Expanded sources help, but the direct lead captures the gain. | Keep a small source-adapter layer; do not claim workflow/multi-agent superiority. |
| `A0 > D0`; `A1 ≈ A0` | The process helps independent of extra sources. | Evaluate the specific workflow control; do not market exclusive access. |
| `A1 > D1` and positive interaction, replicated | Aletheia may exploit expanded access better than a direct lead. | Keep only the activated controls; test cost frontier and scope claim to passing strata. |
| DER rises but DCC does not | The system finds more material but does not convert it to a better answer. | Fix selection/synthesis or remove the expensive route; no quality claim. |
| `D1 ≈ D0` and `A1 ≈ A0`, with powered equivalence | The access thesis is falsified for this task mix/envelope. | Revert the broad claim; retain connectors only for documented niche uses. |
| `A1 > D0` only when it receives more calls/tokens, private data, human rescue, or a better model | The result is confounded. | Label it an entitlement/effort advantage; rerun fair comparison. |
| Gains occur only on curator-seeded specialist tasks | Evidence of a valuable niche, not general superiority. | Offer an explicit specialist/high-stakes mode and publish the scope boundary. |
| Any scored decisive source fails identity/completeness/provenance checks | The access numerator is untrustworthy. | Invalidate the affected run; fix the receipt layer before interpreting quality. |

This table also explains why a one-off “Aletheia found a paper Google missed” is
not enough.  It can be a compelling case study and a test seed.  It is not a
causal estimate, and it says nothing about whether another direct query, source
API, or a different day would recover the same work.

## 6. Minimum credible next experiment

Do not begin by adding more channels.  Begin with a small vertical slice that
can answer the central question without reproducing v0.5's unverifiable
orchestration:

1. Implement/enable a **source receipt gate**: requested and final URL,
   expected/observed identity, content state/completeness, content hash, origin
   family, discovered-via channel/query, and an immutable failed-attempt record.
2. Freeze `S0` and the actually healthy `S1` channel manifests, credentials
   classes, models, prompts, and a resource-credit system.  `unlimited` cannot
   appear in this evaluation.
3. Run a **24-task pilot** (12 source-access stress, 12 representative; three
   trials per cell) to validate logging, identity, judge calibration, variance,
   and resource accounting.  Treat its effect estimates as planning data only.
4. Power a larger two-cohort evaluation from the pilot variance and the
   predeclared 5/10/15-point smallest-effect margins.  Do not choose sample size
   after looking at a favorable point estimate.
5. Retain the full manifest, raw result cards, source-family mapping, blinded
   rubric, output hashes, failed runs, and analysis code.  Release both positive
   and negative channel ablations.

The v2 direction is therefore not “more sources make us automatically better.”
It is **a source-policy and evidence-receipt layer that can prove when a source
index changed an answer**.  If that layer finds a large, replicated access effect,
Aletheia has a defensible differentiator.  If it does not, the honest result is
still useful: a strong direct agent plus a small number of carefully chosen public
adapters is likely the better default.

## Evidence and scope notes

- This review inspected the current local registry, live doctor output, router
  behavior, the July 28 deep audit, its corrected controlled comparison, and the
  project's existing evaluation-design record.  It did **not** run a live
  quality benchmark, so it makes no new empirical performance claim.
- Channel health is point-in-time.  Brave was degraded in this environment on
  2026-07-31; health of a channel is not evidence of recall, source quality, or
  an entitlement advantage.  The local `doctor.py` also had an unrelated dirty
  Reddit-probe change at observation time, so the 12/13 result is a live
  environment observation—not a release-pinned health claim—and must be rerun
  from the frozen evaluator runtime.
- The prior v2 dossier independently reaches compatible conclusions about a
  bounded direct baseline, evidence identity, and fixed-contract evaluation; see
  [workflows and alternatives](../../2026-07-29-v2-ground-up-design/research/workflows-and-alternatives.md)
  and [adversarial evaluation](../../2026-07-29-v2-ground-up-design/research/adversary-and-evaluation.md).
  Those are project-authored design evidence, not an external validation of the
  access thesis.
