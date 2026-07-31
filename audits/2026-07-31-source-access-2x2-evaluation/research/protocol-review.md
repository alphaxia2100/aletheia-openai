# Protocol review: testing whether Aletheia's source access is the real advantage

**Status:** proposed, bounded evaluation protocol — not an executed benchmark.
**Date:** 2026-07-31
**Scope:** isolate source-access value from orchestration value without weakening the direct-agent baseline.

## Executive assessment

The proposition is plausible and important: a research system can be materially better if it reaches a decisive regulator decision, primary paper, versioned release, docket, registry, code issue, or first-hand corpus that a normal broad-web workflow does not surface within a reasonable budget. A beautiful synthesis cannot compensate for evidence it never encounters.

That proposition is **not yet demonstrated for Aletheia**. The strongest local head-to-head deliberately gave both arms the same frozen source packet, so it measured a subset of synthesis/review behavior and cannot answer the access question. After correction, it was an 11–11 factual tie while the structured arm had 28 declared document-read assignments against eight for the direct arm. See [the independent method audit](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md). It is evidence that the direct baseline must remain strong; it is not evidence against an access advantage.

The appropriate claim is therefore not “Aletheia can access sources traditional search cannot.” That wording is usually unprovable: a source may be public on the web yet practically absent from a broad index’s top results, or discoverable only through a different query, date, region, or API. The testable claim is:

> Under a frozen, stated generic-web contract and the same finite resource envelope, does Aletheia’s specialist-access portfolio discover, validate, and materially use more decision-relevant source landmarks than generic web alone—and does that improvement survive into better, safer research outputs?

The answer requires **two linked experiments**, not one attractive report:

1. a fixed-query source-access map, which attributes discovery differences to access rather than agent prompting; and
2. a live, adaptive 2×2 factorial run, which determines whether access and/or structured orchestration improve the actual answer under the same total budget.

The first is a component test. The second is the product test. A source-retrieval win without material use is a lead-generation observation; a polished output win without a source-access trace cannot support the claimed mechanism.

## What the repository establishes—and what it does not

| Local evidence | What it establishes | Boundary for this protocol |
|---|---|---|
| [Controlled frozen-packet comparison](../../2026-07-28-deep-runtime-and-head-to-head/comparison/protocol.md) and its [independent audit](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md) | The previous comparison was deliberately retrieval-controlled. It cannot measure live discovery, live source identity, price, latency, or a source-access advantage. Its corrected factual result is 11–11, not a general workflow win. | Do not reuse its score as an access result. Preserve its direct, bounded baseline as a reference design. |
| [0.5 forward test](../../../docs/evals/openai-v0.5-forward-test.md) | Two topic-level diagnostics suggest that capped source triage can find useful material. The dynamic-outline candidate also persisted 97 read artifacts versus 41 for baseline (2.37×), despite equal configured rounds. | Treat this as a hypothesis and a warning: configured rounds are not resource parity. Count every actual read, retry, manual chase, and model turn. |
| [`scripts/eval/run_metrics.py`](../../../scripts/eval/run_metrics.py) | A usable one-query retrieval smoke tool: per-channel count, latency/error, duplication, rough relevance, and optional read probes. | It is **not** an end-to-end evaluator. It has no model-token/dollar ledger, no hidden task set, no source-to-claim trace, no isolation, and its `DISPATCH` omits `europepmc`, even though the main retrieval skill supports it. It cannot certify the specialist portfolio. |
| [`investigate.py`](../../../.cursor/skills/aletheia-research/scripts/investigate.py), [`report.py`](../../../.cursor/skills/aletheia-research/scripts/report.py), and [`treestate.py`](../../../.cursor/skills/aletheia-research/scripts/treestate.py) | Current scripts can route channels, retrieve candidates, record some telemetry, select reads, and report post-hoc artifacts. `investigate.py` does dispatch `europepmc`. | They remain a mutable filesystem workflow, not an authoritative experiment controller. The deep audit found wrong-body acceptance, race/replay/cap problems, and incomplete resource control. They may drive a diagnostic only behind an external recorder; they must not be the sole source of truth for a promotion result. |
| [`scripts/eval/topics.jsonl`](../../../scripts/eval/topics.jsonl) | A visible development topic list exists. | It is not held out: candidate authors can see it and tune against it. Do not use it as the headline suite. It is useful only for harness calibration. |
| Current channel doctor, run 2026-07-31 | ArXiv, DuckDuckGo, Europe PMC, GitHub, HN, Marginalia, OpenAlex, Open Library, reader, Reddit, Stack Exchange, and Wikipedia returned healthy probes. Brave returned `warn`: no `BRAVE_API_KEY`; the fallback was fetch/Jina, not an independent Brave index. | A “generic web = Brave” comparison cannot run credibly on this machine today. Either supply a dedicated, recorded Brave key to both access cells or preregister a distinct `DDG+Marginalia` generic contract. Do not silently substitute one for the other after results appear. |

The v2 documents already point in the right direction: a bounded direct lead should be the default, and a source/claim/resource controller must own the facts that the final report relies on. See the [v2 acceptance contract](../../2026-07-29-v2-ground-up-design/acceptance-contract.md) and [adversarial evaluation review](../../2026-07-29-v2-ground-up-design/research/adversary-and-evaluation.md). This protocol turns that principle into a falsifiable access claim.

## The causal question

There are two independently manipulable factors.

| Factor | Level 0 | Level 1 | What it is intended to test |
|---|---|---|---|
| **A — access portfolio** | `G`: generic web only | `S`: generic web plus a topic-appropriate specialist portfolio | Whether access to structured/domain/community/code indices increases useful source reach under the same finite budget. |
| **W — workflow** | `D`: one accountable direct lead | `O`: bounded, centrally controlled structured investigation | Whether deliberate delegation, source-separated work, and fresh verification add value after access is held fixed. |

This yields four arms, all using the same generator model snapshot, system prompt core, output contract, public-data policy, and global envelope:

| Arm | Access | Workflow | Permitted shape |
|---|---|---|---|
| `G-D` | Generic web | Direct lead | One lead plans, searches, reads, writes, and performs a prescribed self-audit. No workers, shared state, or hidden critic. |
| `G-O` | Generic web | Structured | Controller may assign up to two source-separated research tasks and one fresh verifier; all use the generic endpoint only. |
| `S-D` | Specialist portfolio | Direct lead | The same one-lead workflow as `G-D`, with the specialist menu available. |
| `S-O` | Specialist portfolio | Structured | The intended bounded Aletheia investigation: controller, at most two research tasks, central synthesis, one fresh verifier, same total cap. |

The four-way layout matters. Comparing only `G-D` to `S-O` confounds access, role count, prompting, review, and possibly cost. It can produce an impressive product demo, but not a causal explanation.

For topic `i`, after aggregating repeated trials within each cell, report these *predeclared* factorial contrasts rather than only a winner table:

```text
access effect A_i      = ((S-D_i - G-D_i) + (S-O_i - G-O_i)) / 2
workflow effect W_i    = ((G-O_i - G-D_i) + (S-O_i - S-D_i)) / 2
interaction I_i        = (S-O_i - G-O_i) - (S-D_i - G-D_i)
```

`I` answers a particularly useful product question: does orchestration make specialist access more usable, or does a capable single lead capture nearly all of it? A strong `S-D` result with a near-zero `I` argues for a simpler default. A positive `S-O` only at a higher observed spend is useful information, but must be reported as **quality at higher cost**, not a matched-budget win.

## Define access without a strawman

### Generic-web contract (`G`)

`G` means a normal, competent broad-web research workflow, not “one query typed into a weak search box.” It receives:

- one pinned broad web-search provider with an API/search-version identifier captured in the manifest;
- public, unauthenticated URL fetching for pages returned by that provider or followed from those pages;
- the same content extractor, source-identity resolver, canonicalizer, and citation/claim checker as `S`;
- the same model, prompt, output limit, tool-call credits, full-text read budget, and deadline as `S`.

It may formulate alternative queries, inspect result pages, follow citations, and use direct URLs it has legitimately discovered. It may **not** call an academic index, bibliographic/citation API, code-host search API, forum/community search API, registry, specialist database, browser session, private corpus, or a managed research product on the side.

The preferred `G` provider is a paid, pinned broad-search API such as Brave, because that makes the contract explicit and reproducible. Current channel health makes that unavailable here. If a project chooses DuckDuckGo plus Marginalia instead, name the arm `G-DDG-M` and treat it as a different study—not as an invisible fallback for `G-Brave`.

### Specialist-access contract (`S`)

`S` contains every `G` capability **plus only a preregistered, topic-specific set of specialist endpoints**. Do not give it “all channels.” More endpoints create noise, duplication, expense, and untestable latitude.

| Topic family | Allowed specialist endpoints | Evidence rule |
|---|---|---|
| Biomedical/scientific | Europe PMC, OpenAlex, ArXiv where appropriate | Index records are leads/identity aids; a claim still needs a resolved paper, regulator, registry, or data source. |
| Software/technical | GitHub search/releases/issues, Stack Exchange, OpenAlex/ArXiv if research is material | Version, commit, release, issue, or official documentation identity is mandatory for version-sensitive claims. |
| Product/reliability/lived experience | Relevant public manuals/parts/official support discovered through the web; Reddit/HN/community search only as explicitly labeled first-hand/lead-generating channels | Community reports can establish a labeled case experience, not prevalence or causal fact. Chase the underlying manual, recall, repair record, or primary documentation for general claims. |
| Policy/legal/current public record | Official repositories/dockets/registries only if an adapter is actually available and lawful; otherwise no fictional “specialist” advantage | A specialist menu cannot be claimed merely because a worker knows how to search harder. Capture the concrete endpoint and its policy. |
| Humanities/history | Open Library/Internet Archive/other lawful catalogues only where enabled and where the question actually needs them | Catalogue hits are discovery aids; cite the primary edition/archive record actually read. |

The endpoint menu, version, health, credentials class, response limit, and source-role policy are part of the pre-run manifest. `S` should be *strictly more capable* than `G`; it must not secretly have a different reader, a longer deadline, or an authenticated browser session.

### What counts as a source-access result

A source is **operationally reached** only when all of the following are recorded:

1. the condition generated a discovery action within its tool credits;
2. the returned candidate has a canonical work/source identity (for example DOI, PMID, arXiv ID/version, docket, official publication ID, repository + commit/tag, or normalized official URL);
3. the source body was fetched or an explicit, truthful failure was logged;
4. expected and observed identity match sufficiently for the source type; and
5. the earliest qualifying discovery event is attributed to its endpoint.

A source appearing in both conditions is attributed to the first qualifying event within that trial. A retrieved URL that resolves to the wrong document, a snippet-only hit, an unread PDF, or a duplicate mirror is **not** a successful landmark read. This is intentionally stricter than the current mutable tree artifacts: the prior audit found that wrong bodies and nontransactional source state can make a superficially successful read unreliable.

The study may say “specialist access reached this source more often under the stated contract.” It may not say “ordinary search cannot access it” unless a separately defined accessibility study supports that stronger absolute statement.

## Two linked experiments

### Experiment A0: fixed-query source-access map

**Purpose:** identify access reach independently of adaptive prompt quality, delegation, or prose quality.

For every hidden topic, an evaluator—not the candidate author—prepares a sealed set of six to eight semantic query intents. An intent is a research need, such as “current regulator decision for [intervention/population]” or “official release/issue that changes [version-sensitive fact],” not a source title and not an answer hint. A query-rendering template for each endpoint is frozen before any arm runs.

Each access condition receives the same number of remote discovery-action credits (`Q=24` in the recommended S1 envelope below), the same maximum `K=10` candidates per action, and the same response-timeout/retry policy:

- `G` spends all 24 credits on the pinned generic provider: eight initial intent queries plus sixteen frozen, topic-appropriate generic reformulations.
- `S` spends 24 credits: the same eight initial generic intent queries plus sixteen preallocated specialist calls across the topic’s frozen endpoint menu. The number of returned candidates is capped identically.

This is not designed to make the two result lists look alike. It measures whether an equivalent number of retrieval actions, allocated to different available indices, changes landmark reach. It prevents the trivial but misleading result “the system that made more queries found more sources.”

No generative model makes adaptive decisions in A0. The harness records the rendered query, provider response, candidate rank, timestamp, raw-response digest, canonicalization result, and normalized destination identity. A0’s primary outcomes are weighted landmark reach, time-to-first-landmark, identity-resolution rate, and candidate precision; it has no answer-quality claim.

Run A0 first on calibration topics and then on the sealed headline topics. If it cannot show that the declared `S` endpoints actually produce distinctive, valid candidates, an expensive `S-O` workflow experiment is premature.

### Experiment A1: adaptive 2×2 product evaluation

**Purpose:** estimate the access, workflow, and interaction effects in the complete research process.

Each arm gets the same topic, decision context, output contract, initial six query intents, and hard global envelope. It may use the remaining adaptive discovery credits as it chooses, subject to its access policy. This allows a strong direct lead to exploit `S`; the test must not assume that only a hierarchy can operate specialist tools well.

`D` is deliberately strong:

- one persistent lead gets the entire global model/tool budget and all source-access capabilities for its cell;
- it may plan, revise queries, follow valid leads, maintain a compact claim/source table, and self-audit against a fixed checklist;
- it has no delegated workers, no separate critic context, no shared artifact tree, and no free second pass.

`O` is deliberately narrow, not v0.5’s unrestricted tree:

- a controller freezes the plan, capabilities, reservations, and task leases;
- at most two read-only source workers receive non-overlapping research questions/source bases where that separation is justified;
- workers return immutable source/claim proposals, not free-form authority to mutate global state or spend more budget;
- the controller alone accepts sources, resolves identity, owns the final answer, and publishes;
- one fresh verifier may inspect the final claim set and source bodies inside the same global envelope.

The structured arm does not receive an extra model budget merely because it has more roles. Any coordination, handoff, synthesis, verification, retry, and prompt token is charged to its one run ledger. The direct arm may use the same budget in fewer, longer turns. This is the comparison the prior frozen-packet test did not make.

## Recommended S1 resource envelope

These are **recommended pilot values**, not retroactive facts about Aletheia. Freeze them after a four-topic non-headline calibration run; never adjust them after examining headline quality results. A lower-tier quick benchmark may use smaller values, but must be reported as such.

| Resource | Hard cap per arm/trial | Enforcement and reporting rule |
|---|---:|---|
| End-to-end elapsed time | 75 minutes | Starts at executor launch and includes queueing, worker startup, retries, source extraction, verification, and final rendering. Report active tool time separately; do not substitute it for latency. |
| Model usage | 250,000 total provider-metered tokens, including input, output, and reasoning where exposed | Freeze model snapshot, reasoning setting, cache policy, and price card. If the provider exposes only opaque usage, reserve conservatively and label the comparison `metering-incomplete`; it cannot make a cost-matched promotion claim. |
| Direct model/provider spend | US$25 total | Includes model, search, reader, OCR/PDF, and any paid endpoint charge. The run stops at the first hard cap. A provider credit that is not priced is still logged as an invocation and cannot be treated as free. |
| Discovery actions | 24 remote search/index calls | All endpoints count one action per request, including re-queries and manual/direct lookup calls. Each action returns at most 10 retained candidates. Cache hits must be logged and charged consistently in both cells. |
| Full-text read attempts | 12 attempts; at most 10 successfully accepted unique source bodies | A retry is another attempt. Reads of different URL variants of the same canonical work do not create another unique-source credit but do consume time/attempt and bytes. |
| Evidence volume | 1.2 MiB normalized unique accepted body text; 120 KiB per body by default | Raw bytes and extraction hashes remain available for audit. Full rereads beyond a truncation boundary are charged. If a source needs more text, an explicit `large-source` reservation displaces another read rather than making it free. |
| Retries | one retry per remote operation, two only for a documented transient-provider failure | A retry never silently creates a new source/read budget. Exhaustion records a failure and the system routes or abstains. |
| Concurrency | `D`: one model worker. `O`: controller + at most two research workers; verifier runs after workers finish | Concurrency may improve elapsed time but cannot increase any global cap. Queue/worker timing is retained. |
| Final output | 1,200–1,400 prose words plus source/uncertainty table | Output length is a reporting constraint, not a quality metric. Full run artifacts are retained separately. |
| Data/capability boundary | public, unauthenticated sources only; zero browser-session pages; zero private corpora | Any browser session, paid proprietary corpus, private file, or user data creates a different access treatment and must be separately evaluated. |

Two comparisons should be reported from this same machinery:

1. **Strict parity (headline causal result):** all caps above are enforced globally. A cap breach is a failed/mismatched trial, not a quality win.
2. **Service-realistic profile (secondary):** allow the production configuration’s normal parallel endpoint fan-out while holding the same user-facing deadline and recording all additional cost/action/read use. This may answer “is the product better for a user?” but must be labeled **quality at observed cost**, not “the specialist logic is better at equal cost.”

The numerical values are intentionally finite. An `unlimited` mode cannot answer a cost/latency comparison because there is no stable treatment to compare.

## Landmarks, rubrics, and source identity

### Hidden-topic construction

Use a sealed 24-topic headline suite, plus four non-headline calibration topics. The existing `scripts/eval/topics.jsonl` remains a development suite only. The headline suite should include six source ecosystems with four topics each:

- biomedical/scientific;
- software/technical;
- policy/public-record;
- consumer/product reliability;
- academic/technical research;
- history/humanities or another domain where specialist catalogues are actually available.

Within each ecosystem, preregister two **specialist-sensitive** tasks and two **generic-web-friendly/neutral controls**. The control strata are essential. A suite selected only because its decisive documents sit in specialist databases answers “can we construct a win?” rather than “when does specialist access pay?”

Topics need a bounded date/jurisdiction/population/version and a real decision or factual dispute. They should include cases where the right result is uncertainty, contradiction, or abstention. Do not select only questions whose answer matches an Aletheia design thesis. Do not publish source titles, answer keys, or landmark identities in the candidate repository before runs.

### Landmark registry

For each topic, two source curators work independently before the arms run. A third domain adjudicator reconciles the result into a **sealed landmark registry**. The registry does not prescribe one ideal essay. It records several possible evidentiary paths and lets an arm earn answer credit with a valid alternative source.

Each landmark has:

```json
{
  "landmark_id": "opaque-id",
  "canonical_identity": {"kind": "doi|pmid|arxiv|official_url|repo_tag|docket", "value": "..."},
  "role": "decision_setter|primary_evidence|counterevidence|current_policy|version_anchor|first_hand_case",
  "weight": 1,
  "source_class": "evidence|lead_only|case_only",
  "why_material": "short criterion-specific rationale",
  "coverage_criterion_ids": ["C03", "C09"],
  "valid_time_window": {"from": "...", "to": "..."},
  "acceptable_alternatives": ["opaque group id"],
  "identity_resolution_rule": "..."
}
```

Use weights only for pre-agreed decision importance: for example 3 for a decisive/current official or primary source, 2 for a material counter-source, and 1 for context. Do not inflate a conclusion by giving it many friendly landmarks. Every leading conclusion must have an adversarial/counterevidence landmark or an explicit finding that one was not available.

Curators also write 12–20 atomic answer criteria: must-cover facts, disagreement/mechanism, provenance/support, calibrated uncertainty, and negative criteria for a harmful omission or unsupported leap. A criterion is scored with an output quote and source span. A missing but valid alternative source can be adjudicated into an `acceptable_alternatives` group **before unblinding arm labels**; it must not be silently ignored because it was absent from the key.

Seal `topics`, `landmarks`, `criteria`, endpoint menus, price card, judge prompts, and score code in a separate evaluator repository/bucket. Commit their hashes and a timestamp before any run. Candidate authors see only public calibration topics and schema, never headline item content.

### Identity and provenance gate

The test must avoid crediting a search hit that resolves to a different body. Before a source can count as read, cited, or landmark-recovered, record:

- discovery action ID, endpoint, query intent, rendered query, rank, and response-body digest;
- requested URL and all redirects;
- expected identity from the candidate and observed identity from body metadata/text;
- resolver path (DOI/PMID/arXiv/repository tag/official page); match, mismatch, ambiguous, or unreadable state;
- extracted-body SHA-256, normalized length, truncation flag, reader/OCR version, timestamp, and source role;
- canonical work/origin IDs for deduplication; and
- every later claim and final-verdict relation to that immutable body.

Only `matched` or adjudicated `acceptable-alternative` identities receive landmark credit. `ambiguous`, `mismatched`, `truncated-unresolved`, and `snippet-only` records remain useful failure data but cannot inflate access or citation metrics. A worker may propose a source; only the controller/gateway may accept it after identity validation.

## Outcomes

Do not collapse all results into citation count, source count, an LLM preference, or a single opaque score. Report the following vector per topic, trial, and arm.

### Access outcomes

Let `L_i` be the sealed landmark set for topic `i`, `w_l` a preregistered weight, and `reached(l)` a valid candidate identity discovered within the envelope.

```text
Weighted Landmark Reach (WLR)
  = sum_l w_l * 1[reached(l)] / sum_l w_l

Validated Landmark Use (VLU)
  = sum_l w_l * 1[matched body was read and correctly linked to a final claim]
    / sum_l w_l

Material Landmark Activation (MLA)
  = sum_l w_l * 1[VLU and a blinded adjudicator finds that it changes/satisfies
                    a material answer criterion or prevents a material error]
    / sum_l w_l
```

`WLR` says whether the endpoint portfolio sees more relevant sources. `VLU` says whether the agent makes evidence of them. `MLA` is the critical bridge to product value. A system that retrieves 30 interesting papers but does not use one correctly has not proved an advantage.

Also report:

- time and action count to first landmark and first decision-setter landmark;
- candidate precision at `K` (valid/relevant candidates divided by retained candidates), broken down by endpoint;
- unique canonical work and independent-origin yield, with duplicate/mirror rate kept separate;
- source-identity mismatch and failed-read rate;
- `specialist-exclusive` landmark recovery under the explicit `G` contract; and
- blinded, adjudicated novel-source yield. Novel sources are secondary so the frozen key cannot punish a genuinely better route, but they cannot be promoted without review.

### Answer and downstream outcomes

For final reports, grade atomic criteria first. Use a criterion matrix, not a reference-essay similarity score:

- mandatory-criterion recall;
- material negative-criterion incidence (harmful omission, unsupported causal leap, invalid generalization);
- claim support precision and coverage after source-span checking;
- calibrated abstention/uncertainty where the evidence does not settle the question;
- disagreement/mechanism mapping;
- decision usefulness under the stated context; and
- a fresh consumer-agent test: answer hidden factual/decision questions and locate the exact source body/path/span under a separate token/tool cap.

The consumer test matters because a research artifact can be useful even when its prose is not prettier: it asks whether the evidence can be found and reused. The downstream question writer must not be the same person who wrote the final report.

Every consequential claim is fact-checked against the archived source body by a fresh context/model or human adjudicator. The verifier may add missing claims; the claim list is then rechecked and hashed. Citation precision with incomplete claim coverage is not an accuracy result.

### Resource and reliability outcomes

For every trial, publish raw and normalized measurements:

- provider/model identity, reasoning setting, cache policy, input/output/reasoning tokens, and cost receipts;
- tool calls by endpoint, query/retry count, provider charge, response failures, and rate-limit waits;
- source attempts, successful unique bodies, unique body bytes, repeated reads, manual reads, identity failures, and truncations;
- end-to-end elapsed time, p50/p95 across trials, worker/queue time, and controller overhead;
- final output/artifact bytes and source/claim graph size; and
- terminal status: complete, bounded partial, abstained, failed, or envelope breach.

This answers whether `S` is slower or more expensive as an empirical matter rather than assuming that many channels or many workers are either free or automatically costly.

## Randomization, isolation, and judging

### Execution design

- Run all four cells for a topic/trial in a randomized Latin-square order, interleaved in the same short live-web block. Record start/end time and channel health immediately before each block.
- Use three independent trials per arm/topic for the headline run. Trial is the unit of model stochasticity; **topic**, not trial, is the independent unit for the final population estimate.
- Launch each trial from an immutable baseline/candidate worktree/container and empty run directory. Block shared filesystem state, browser state, caches, Atlas/memory, source indexes, and Git-history access. A source response cache may be shared only if the identical cache key/body is visible to every matched cell and the cache hit is recorded/charged consistently.
- Use separate credentials/capability grants for the generic and specialist adapters. Do not let a generic arm invoke a hidden specialist endpoint through a URL resolver.
- Capture public response bodies or cryptographic digests plus lawful archival metadata. If rights prevent body retention, record that the relevant claim cannot receive high-assurance source-span credit.

### Blind grading

Keep raw traces available to an audit team, but give output judges only de-identified reports, source tables, and the rubric. Strip system names, arm labels, worker prose, token/cost details, and process tells. Randomize output order and run exact `AB` and `BA` pairwise comparisons as a **secondary** preference measure; an order-flipping pair is a tie.

Use at least two judge families disjoint from the generator when practical, plus a human/domain calibration set before the headline run. The local evaluation design already identifies position, verbosity, and self-preference as risks; see [the evaluation branch](../../../docs/research/2026-07-27-agent-output-quality/branches/evaluation.md). Atomic criteria and source-span adjudication are primary; pairwise LLM preference is a diagnostic, never a truth oracle.

## Analysis plan and decision rules

### Estimation

1. Aggregate the three trials inside each topic/cell using the preregistered median for continuous outcomes and a conservative all-trials-success indicator for critical gates.
2. Compute `A_i`, `W_i`, and `I_i` for each topic as shown above.
3. Use a topic-clustered paired bootstrap (10,000 resamples) to report point estimates and 95% intervals. Do not treat 72 trials as 72 independent research questions.
4. Report results overall and by preregistered ecosystem/specialist-sensitive versus neutral strata. Do not reclassify a topic after knowing which arm won.
5. Preserve per-topic outcomes, failures, missing data, and raw ledgers. Averages may not erase a critical wrong-body acceptance, harmful unsupported recommendation, envelope breach, or unavailable endpoint.

### Promotion language

Use deliberately narrow claims:

| Result | Permitted conclusion |
|---|---|
| `S` increases WLR but not VLU/MLA or answer quality | Specialist endpoints improve discovery under this contract; no demonstrated research-outcome advantage yet. |
| `S` increases VLU/MLA and answer outcomes under strict parity, with no critical gate failure | Specialist access is a measured contributor on this suite. |
| `S-D` captures the gain and `I` is near zero | Make specialist access available to the bounded direct lead; do not default to orchestration. |
| `S-O` has a positive interaction under the same cap and passes gates | Structured investigation earns opt-in use for tasks with demonstrated independent source bases. |
| Quality improves only after a cost/time/read breach | Keep as a premium/experimental profile; do not call it a matched-budget win. |
| Effects vary materially by source ecosystem | Publish the eligibility rule and route only eligible tasks; do not advertise a universal advantage. |
| CIs span both useful gain and harm/no gain | Inconclusive. Add independent held-out topics or improve instrumentation; do not loosen gates. |

For the stronger phrase **“much better because of access,”** require all of the following on the sealed headline suite:

1. the lower 95% bound for the access effect on WLR is at least +10 percentage points and on MLA is positive;
2. the lower 95% bound for a predeclared material answer-quality vector is non-negative, with a positive decision-relevant component;
3. no increase in critical unsupported/high-stakes recommendation, wrong-body acceptance, or incomplete final claim coverage;
4. strict-parity cost/time/tool/read caps pass in every included trial; and
5. a disaggregated result shows the benefit is not a single lucky topic, one duplicated source, or an endpoint outage in the baseline.

Calling the result merely “better source reach” requires less: WLR/VLU evidence and an honest contract label. It should never be inflated into a general quality or safety claim.

### Keep/revert discipline

The evaluation itself needs the same discipline proposed for v2:

- Baseline, evaluator, tool adapters, channel configuration, price card, prompts, rubric, and hidden-suite hashes are immutable for a run series.
- A candidate branch changes one named access or workflow mechanism. A matching feature-off ablation is created before seeing hidden results when a causal mechanism is claimed.
- No candidate edits, prompt changes, source-menu additions, or rubric weight changes after a hidden result. A failed candidate is archived with its trace and reverted/disabled; it is not quietly retested until a fresh evaluator version and topic set are declared.
- A useful but more expensive result is retained as a separate service tier, not smuggled into the default baseline.
- Every kept feature must beat the direct baseline on its mechanism-specific outcome and not degrade non-compensable gates. “More citations,” “more sources,” or “more agent activity” is not sufficient.

This is the transferable part of a fixed-budget, keep/revert experimental loop. Web research has no single scalar equivalent to a validation loss, so the answer is a frozen multidimensional contract, not a theatrically precise one-number score.

## Threats to validity and controls

| Threat | How it can produce a false win/loss | Required control |
|---|---|---|
| Strawman generic baseline | A restricted or broken web search makes any specialist menu look superior. | Use a pinned competent broad provider; health-check it; give `G` full URL following and the same reader. If the provider/key is unavailable, do not run the named study. |
| More work masquerading as access | `S-O` fans out more queries, sources, and tokens. | Global model/tool/read/time/dollar caps; log every manual and retry operation; strict-parity result excludes breaches. |
| Live-web drift and rate limits | Later arms see changed pages or a degraded index. | Interleave randomized arms in short blocks, capture health/response digests, repeat blocks when a predeclared outage rule fires, and report time-bounded results. |
| Landmark/key leakage | Candidate is optimized against visible topics or source titles. | Keep headline tasks/landmarks outside the candidate repo; hash-seal before runs; use fresh held-out suite after two feature decisions. |
| Reference-answer overfitting | A novel valid source/argument is marked wrong because it is not in the key. | Landmark groups plus blind alternative-source adjudication before label reveal; raw atomic criteria are more important than essay similarity. |
| Source echo / mirrors | Ten URLs repeat one upstream paper and inflate coverage. | Canonical work/origin IDs, DOI/repository/version dedupe, and separate independent-origin reporting. |
| Wrong-body / identity fault | A title/snippet points to a different document but receives credit. | Expected/observed identity gate, archived body hash, source-type resolver ladder, and zero landmark credit on mismatch. |
| Workflow confounded with model quality | Workers use a different model or a larger hidden context. | Pin identical model snapshot/reasoning policy and total metered envelope. The only difference is permitted role topology. |
| Judge position/verbosity/self-preference | A long familiar report wins a holistic LLM preference. | Atomic quote-backed rubric first; AB/BA order mirroring; judge calibration with human anchors; report length/useful-criterion density. |
| Trial contamination | Later agents read earlier files, caches, or Git history. | Per-cell isolated worktrees/containers, no shared run directory or agent memory, access logs, and a nonce contamination probe. |
| Topic-selection bias | Only specialist-friendly topics appear in the suite. | Balanced specialist-sensitive and generic-neutral strata, declared before runs, ecosystem-level results. |
| Endpoint availability is conflated with Aletheia | A paid key, browser session, or proprietary corpus—not the system—causes the gain. | Public-only headline study; provider/configuration is disclosed. Evaluate premium/private capabilities as separate access treatments. |
| Too few topics / noisy models | One favorable run looks like a product conclusion. | Three trials per cell, topic-clustered analysis, hidden 24-topic screen, explicit inconclusive outcome. |

## What can be executed now

The following are legitimate **diagnostics** with the present repository. They do not justify a product-performance claim.

1. **Channel-health and endpoint inventory.** `doctor.py --json` already shows the present capability boundary: the core public channels are mostly live; Brave is degraded because no key is configured. Archive the JSON with any diagnostic run.
2. **A0-style retrieval smoke tests on public development topics.** `investigate.py candidates` with explicit `--channels` can produce candidate manifests for `G`-like and `S`-like channel sets, and can exercise Europe PMC. Preserve raw requests/responses externally rather than treating the mutable run tree as a durable ledger.
3. **Per-channel yield/latency probes.** `scripts/eval/run_metrics.py` can measure a single query for its supported dispatch list. Use it to find endpoint failures, duplicate rates, and read success—not to rank access portfolios. Its lack of `europepmc` dispatch must be fixed or worked around before a biomedical A0 result.
4. **Identity-gate fixtures.** The experimental identity-gate branch and current tests are useful for deterministic wrong-document, redirect, title/DOI, retry, truncation, and duplicate-work probes. These should be an admission gate for the evaluator, not a claim that live research is already controlled.
5. **A four-topic calibration dry run.** Use only visible development topics to validate manifests, health logs, cost receipts, action counting, isolated execution, output blinding, and judge calibration. Throw away its quality results for promotion purposes.

## What must remain future work before a credible 2×2 claim

The current toolkit is not enough to execute A1 as specified. Build or independently supply the following minimum evaluator kernel first:

1. **Authoritative run ledger and capability gateway.** It must reserve and settle model/tool/read spend before calls, reject expired/over-cap actions, produce idempotent receipts, and prevent workers from writing final state directly. A directory plus JSONL files is not sufficient.
2. **Cross-provider metering collector.** Capture tokens, reasoning tokens where available, unit price/version, search/PDF/OCR charges, cache behavior, and wall-clock spans. Without it, a result can be informative but cannot be called cost-matched.
3. **Query/tool interceptor.** Every search, direct URL read, redirect, resolver call, retry, and manual read needs an action ID and policy decision. This is how the generic arm is kept from reaching a specialist source through an unlogged path.
4. **Immutable source/artifact store plus identity resolver.** Store raw response/body hashes and typed expected/observed identities. The prior audit’s wrong-body and cross-leaf state findings make this a precondition, not polish.
5. **Isolated four-cell runner.** Immutable worktrees/containers, fresh agent state, capability-scoped credentials, randomized schedule, source-cache rules, cancellation/timeout behavior, and full timing trace are required.
6. **Sealed evaluator package.** Hidden topics, landmark registry, atomic rubric, alternative-source adjudication procedure, judge prompts, random assignment, and result analysis code must live outside candidate worktrees with pre-run hashes.
7. **Generic-web baseline decision.** Obtain a dedicated pinned broad-search provider/key or explicitly scope the study to a healthy `DDG+Marginalia` baseline. The existing Brave warning is a stop condition for a Brave-named trial.
8. **A real `S` adapter matrix.** The main `investigate.py` and the metrics harness currently disagree on endpoint coverage. Resolve this, add adapter conformance/health tests, and record which exact endpoints participate in each ecosystem.
9. **Human/SME adjudication capacity.** At minimum, source-landmark reconciliation and a sampled claim/source-span review must be independently checked. An uncalibrated LLM judge alone cannot establish a high-stakes access advantage.

Do not “solve” these gaps by letting an agent manually keep a spreadsheet. That would reproduce the auditability asymmetry in the earlier comparison: one arm can appear more carefully documented than the other while neither has a complete accounting boundary.

## Minimal implementation sequence

The smallest useful next step is not a full v2 orchestration engine. It is an **evaluation harness vertical slice**:

```text
sealed topic + source-landmark registry
             │
             ▼
immutable trial manifest ──► policy/query gateway ──► G or S adapters
             │                         │                     │
             │                         ▼                     ▼
             └────────────────── append-only receipts ──► immutable source bodies
                                                               │
                                                               ▼
direct lead or bounded O controller ──► claim/source proposals ──► fresh verification
                                                               │
                                                               ▼
                                                       blinded score/export
```

Suggested order:

1. Build a hermetic A0 recorder for two endpoints plus a source identity fixture suite.
2. Add an external, append-only resource ledger and one generic + one biomedical specialist adapter.
3. Run four visible calibration topics, intentionally including a generic-neutral control and a degraded-channel case.
4. Freeze the S1 envelope only after the recorder passes failure injection: retry, duplicate, wrong body, provider 429, truncated PDF, worker crash, and cap refusal.
5. Add the direct lead and one-controller/two-worker A1 executor behind the same gateway.
6. Recruit/prepare the sealed 24-topic evaluator and run the headline matrix without changing the candidate.

If the direct `S-D` arm wins, that is success: ship the specialist source policy to the bounded single lead. It would be a mistake to force a multi-agent tree merely because Aletheia’s historical identity is multi-agent. If only `S-O` wins under parity, make it an explicitly selected, bounded investigation service—not the automatic default.

## Sources and provenance notes

This protocol rests chiefly on direct local evidence because it is a design for this repository’s concrete capabilities and audit failures. External material informs evaluation hygiene, not a claim that it proves Aletheia’s performance:

- [Independent method audit of the local frozen-packet comparison](../../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md) — primary local audit evidence for the 11–11 correction, unmeasured retrieval, and 28-versus-8 read-assignment asymmetry.
- [OpenAI 0.5 forward test](../../../docs/evals/openai-v0.5-forward-test.md) — primary local record of the two positive diagnostics and the 2.37× observed read-artifact amplification.
- [Current channel configuration](../../../.cursor/skills/channel-retrieval/channels.json) and [current retrieval metrics harness](../../../scripts/eval/run_metrics.py) — primary local implementation evidence for endpoint capabilities and gaps.
- [V2 acceptance contract](../../2026-07-29-v2-ground-up-design/acceptance-contract.md) and [adversarial evaluation review](../../2026-07-29-v2-ground-up-design/research/adversary-and-evaluation.md) — project-authored design evidence; useful constraints, not independent proof of outcome quality.
- [Anthropic, “Demystifying evals for AI agents” (2026)](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — first-party practitioner guidance for distinguishing tasks, trials, graders, and multistep agent evaluation. It supports repeated/isolated trials as a design practice; it is not evidence that this specific protocol will work.
- [Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena”](https://arxiv.org/abs/2306.05685) and [Wang et al., “Large Language Models are not Fair Evaluators”](https://arxiv.org/abs/2305.17926) — empirical reasons to treat order-sensitive holistic LLM judging as secondary and to use order mirroring/atomic criteria.

### Explicit gaps

- No controlled local experiment has yet measured Aletheia specialist-access recall against a strong generic-web baseline.
- Current channel health is a point-in-time observation, not a guarantee of availability or coverage.
- “Landmark” construction itself can bias a benchmark. The dual-curator, sealed-key, alternative-source procedure reduces but cannot eliminate that risk.
- A 24-topic, three-trial screen can detect a large, decision-relevant effect and expose regressions; it cannot estimate a timeless universal win rate.
- Access gains may be domain-specific, key-dependent, and transient as broad search engines change their indexes. The result must be time-stamped and endpoint-specific.
