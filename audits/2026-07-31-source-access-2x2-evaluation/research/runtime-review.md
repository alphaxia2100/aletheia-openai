# Retrieval runtime review and reproducible source-access probe

## Bottom line

Aletheia has a credible *hypothesis* of a source-access advantage: it can call source-native public
APIs and community archives rather than rely only on web-index ranking. That can matter a great deal
when a decisive source is poorly web-indexed. It is not a demonstrated general advantage today.

The current code gives neither a clean proof nor a clean measurement of that hypothesis. A channel
being called "evidence" does not make its results unique, primary, readable, correctly identified, or
more useful than generic web results. In small bounded live checks on 2026-07-31, generic DuckDuckGo
found exact arXiv, GitHub, and Stack Overflow targets at rank one; OpenAlex missed the exact arXiv
target and the current GitHub adapter missed the exact repository. Reddit's default discovery path
first uses generic web search when Brave is absent, but records the result only as "reddit".

The correct v2 evidence plan is therefore:

1. Run a target-labelled, model-free source-access probe with generic web versus the appropriate
   source-native lane.
2. Seal the resulting source packets.
3. Run a frozen-packet 2x2 that varies source policy and workflow separately.
4. Keep an added channel, router policy, worker, or verification step only if its preregistered
   benefit exceeds its observed reliability, latency, and cost burden.

This note does not make production changes. It records current behavior and the smallest executable
evaluation contract needed to answer the source-access question honestly.

## Snapshot and channel health

The review inspected the live worktree on 2026-07-31:

| Item | Observation |
|---|---|
| Branch / committed base | codex/independent-audit-2026-07-28 at 5bea63a |
| Worktree | Dirty. Active changes include investigate.py, doctor.py, read.py, reddit.py, skill instructions, and tests. These observations describe the current tree, not a sealed release. |
| Health result | 12/13 enabled core channels live in a real probe. Brave was degraded because BRAVE_API_KEY was absent. |
| Healthy generic control now | DuckDuckGo and Marginalia. DuckDuckGo is Bing-derived; Marginalia is an independent small-web index. This is a useful no-key generic-web control, not a proxy for every commercial web product. |
| Enabled specialist clients now | arXiv, OpenAlex, Europe PMC, GitHub, Stack Exchange, and Reddit. GitHub was unauthenticated and documented as 60 requests/hour. |

The health command was:

~~~sh
python3 .cursor/skills/channel-retrieval/scripts/doctor.py
~~~

It is real network activity, not a static configuration check. Its output is a point-in-time
availability signal. It is not a load test, does not get stored in an Aletheia run, and may consume
a provider request/rate-limit budget.

## What the current adapters actually do

| Adapter | Current mechanism | Potential increment over generic web | Important boundary |
|---|---|---|---|
| DuckDuckGo | HTML scrape of DuckDuckGo's HTML endpoint; lead-generation class | Broad web ranking and common canonical pages | Bing-derived, brittle scrape, no provider-rank/raw-response receipt |
| Marginalia | HTML scrape of the Marginalia search page | Independent small-web discovery | Sparse snippets, brittle scrape, noisy on mainstream topics |
| arXiv | arXiv export API | Preprint identifiers, metadata, direct abstract/PDF route | Public URLs may already be found through web search; shared-IP 429/cooldown risk |
| OpenAlex | Works search API | Structured work IDs, DOI, authors, affiliations, citations | Current adapter performs broad search, not direct ID resolution; target can rank poorly or be absent |
| Europe PMC | Europe PMC search API | Biomedical corpus metadata and DOI/PMC paths | A DOI result is not proof of readable full text; output does not retain PMID/PMCID as a first-class identity |
| GitHub | Repository search API | Repository metadata and direct repository URLs | Searches repositories only, not code/issues/releases/commits; current code asks GitHub to sort by stars rather than relevance |
| Stack Exchange | Search API, default site Stack Overflow | Question IDs, score, answer count, accepted state | Other Stack Exchange sites require a task-specific SE_SITE; answer content still needs a reader |
| Reddit | Web search scoped to reddit.com, then PullPush, then Arctic Shift; browser by explicit capability | Community posts/archives can sometimes add public material generic web misses | With no Brave key it normally starts with DuckDuckGo. Output lacks a machine-readable backend identity. |

Relevant current code is in:

- .cursor/skills/channel-retrieval/scripts/web_ddg.py
- .cursor/skills/channel-retrieval/scripts/web_marginalia.py
- .cursor/skills/channel-retrieval/scripts/arxiv.py
- .cursor/skills/channel-retrieval/scripts/openalex.py
- .cursor/skills/channel-retrieval/scripts/europepmc.py
- .cursor/skills/channel-retrieval/scripts/github.py
- .cursor/skills/channel-retrieval/scripts/stackexchange.py
- .cursor/skills/channel-retrieval/scripts/reddit.py
- .cursor/skills/aletheia-research/scripts/router.py
- .cursor/skills/aletheia-research/scripts/investigate.py

### The runtime is not yet an access ledger

The leaf engine is useful operationally: it routes, fans out retrieval concurrently, may retry a
zero-result query with shorter keywords, deduplicates, ranks, and emits a candidate manifest for
agent choice. It is not the correct primary collector for a source-access experiment:

1. Provider results are appended in completion order. Deduplication happens after that, so timing can
   decide which alias representation survives.
2. One logical retrieval can make up to three physical requests because zero results trigger shorter
   query recovery. The normal aggregate does not attribute a hit to an attempt.
3. Providers transform queries differently. GitHub keeps four keywords and sorts stars; Stack
   Exchange keeps five keywords; Marginalia keywordizes; OpenAlex shortens long queries. The
   effective provider query is not preserved as a durable receipt.
4. The heuristic router is itself a treatment variable. A mixed clinical-ML query currently selected
   DuckDuckGo, Marginalia, OpenAlex, Reddit, and Hacker News while excluding arXiv, Europe PMC,
   GitHub, and Stack Exchange. A source-access test must declare the channels rather than let this
   policy silently choose them.
5. Discovery and full-text access are distinct. The reader normally uses Jina. A returned URL is not
   a readable body, not evidence of correct document identity, and not proof of a supported claim.

For access measurement, call fixed adapters directly, preserve every provider's ordered raw output,
then canonicalize in a separate deterministic pass. Test the router in a different evaluation about
policy coverage and misrouting.

## Bounded live adapter diagnostics

The following were intentionally small public checks: top five results, one adapter request per
command, ten-second timeout, no browser, no paid connector. They ran between 15:10 and 15:12 UTC on
2026-07-31. They are sanity checks, not a benchmark. The query/target examples are now exposed and
must not enter a held-out fixture unchanged.

| Query and intended target | Generic-web observation | Native-adapter observation | Honest interpretation |
|---|---|---|---|
| Exact title of arXiv 2604.02460, Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets | DuckDuckGo returned the canonical arXiv abstract first. Marginalia did not return it in its first five. | arXiv returned it first with author/date/abstract metadata. OpenAlex did not return it in its first five. | arXiv added structured metadata but generic web already discovered the decisive URL. A scholarly channel is not automatically higher recall. |
| openai codex github repository; target openai/codex | DuckDuckGo returned github.com/openai/codex first and its README second. | GitHub's first five did not include openai/codex; they were broad high-star agent/Codex matches. | Direct API access exists, but sorting repository search by stars currently defeats exact repository discovery. |
| python asyncio task exception was never retrieved; target Stack Overflow question 65147823 | DuckDuckGo returned the exact question first. | Stack Exchange returned the same question first, with score 16, one answer, and accepted=true. | The native API adds useful selection metadata, but not unique discovery for this crawled target. |
| intermittent fasting metabolic health randomized controlled trial | DuckDuckGo returned substantive Nature, Science, Springer, Lancet, and MDPI pages. | Europe PMC returned five biomedical records with DOI, author, year, and citation metadata. | No gold target was preregistered, so there is no honest winner. Count or class label cannot replace target-labelled recall. |
| python asyncio task exception was never retrieved through reddit.py | Not separately scored. | Returned snippets explicitly said web-relevance. With Brave absent, reddit.py's first discovery backend is DuckDuckGo. | This is generic-web-assisted Reddit discovery, not evidence of a distinct native Reddit advantage. |

Representative current commands:

~~~sh
python3 .cursor/skills/channel-retrieval/scripts/web_ddg.py \
  "Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets" \
  --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/arxiv.py \
  "Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets" \
  --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/openalex.py \
  "Single-Agent LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal Thinking Token Budgets" \
  --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/web_ddg.py \
  "openai codex github repository" --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/github.py \
  "openai codex" --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/stackexchange.py \
  "python asyncio task exception was never retrieved" --limit 5 --timeout 10

python3 .cursor/skills/channel-retrieval/scripts/reddit.py \
  "python asyncio task exception was never retrieved" --limit 3 --timeout 10
~~~

The GitHub result is especially important. A benchmark that selects only cases where a specialist
endpoint wins would manufacture its conclusion. Aletheia's source advantage must be measured against
strong generic web and against the actual adapter implementation, including failures.

## Current telemetry, cost, and reproducibility limits

| Present behavior | Why it is insufficient | Required receipt |
|---|---|---|
| Normalized records carry URL, source index, title, basic metadata, and second-resolution retrieval time | No provider rank, original/effective query, request ordinal, status, retry, response digest, cache state, or backend | Immutable receipt for every physical request and result |
| investigate.retrieve exposes per-channel count, latency, error, and sometimes shortened query only in transient context/evidence prose | Aggregate telemetry cannot say why a source appeared or failed | Persist logical and physical attempts with effective query and retry/fallback reason |
| telemetry.jsonl totals retrieved/unique/selected/reads and summed read seconds | These are not request costs, response bytes, wall time, model tokens, dollars, or recall | Run-level resource ledger; unknown cost/token values must be null, not zero |
| report.py reconstructs note-file counts | It sees some manual reads but not lane/provider provenance or shared content identities | Content-addressed reads linked to retrieval receipts and source identity |
| Reddit records say index_of_origin=reddit | A claimed community access win may be DDG, Brave, PullPush, Arctic Shift, or browser | Separate adapter, backend, and discovered_via fields |
| Async gather then dedupe | Network timing can decide retained duplicate representation | Store raw provider outputs in stable provider/rank order; dedupe only in a projection |
| Router has keyword classification and combined excludes | Phrasing changes treatment membership; specialist sources can disappear | Fixture declares channels. Router gets a separate coverage test. |
| Reader success reflects body length/readability in this runtime | A readable wrong document could count as access | Expected/observed identity, resolver chain, content hash, completeness state |
| Doctor is not attached to each run | Later analysis cannot know capability/health conditions | Health/configuration snapshot and adapter code hashes in the manifest |

The evaluator must distinguish four propositions:

1. The provider returned a candidate.
2. The candidate is the predeclared source/work.
3. Its content can be read and identity-verified.
4. It changes a supported final claim.

Only the first is an access result. The current artifact model does not make the latter three
mechanically attributable.

## Recommended two-stage evaluation

### Claim hierarchy

Do not ask one trial to prove "Aletheia is better." Pre-register progressively stronger claims:

1. Access: an appropriate native lane improves target-source recall over healthy generic web with
   the same query/result budget.
2. Usable evidence: the extra target resolves, matches its identity, and is readable within the
   same source-read/resource envelope.
3. Outcome: the extra usable evidence improves correctness, coverage, calibration, or decision
   quality in a fixed workflow comparison.

A positive result at claim 1 is useful, but it does not prove claim 3. If a direct single lead gets
the same benefit from the extra packet as Aletheia does, credit source policy rather than orchestration.

### Stage A: target-labelled access probe

This stage makes no model calls and performs no full reads. It measures discovery mechanically.

For each fixed task/query:

1. Query generic web: DuckDuckGo plus Marginalia, retaining top K=10 from each provider.
2. Query exactly the applicable native specialist adapter, also top K=10. Do not fan out to every
   specialist service just to make the treatment larger.
3. Construct generic-plus-specialist offline from the sealed generic and specialist receipts. Do not
   repeat generic retrieval for the union condition.
4. Canonicalize identities after raw outputs are sealed. Score against targets chosen before any
   evaluated run.
5. Capture capability health, configuration, code fingerprints, rate-limit state, and every failure.

No browser, private corpus, paid connector, or hidden optional provider belongs in the first
comparison. Source access must be a publicly reproducible capability first.

#### Fixture strata

The fixture is the integrity boundary. Questions must be realistic user questions that do not leak a
source URL or identifier. Targets must be selected/reviewed without seeing results from the evaluated
lanes.

| Stratum | Pilot tasks | Native adapter | Match identity |
|---|---:|---|---|
| CS/ML preprints | 6 | arXiv | arXiv ID without version |
| Published scholarly works | 6 | OpenAlex | DOI or OpenAlex work ID |
| Biomedical/clinical works | 6 | Europe PMC | DOI plus PMID/PMCID when available |
| Software implementation/release facts | 6 | GitHub | owner/repository plus immutable release tag or commit |
| Technical Q&A | 6 | Stack Exchange | site plus question ID |
| Public lived-experience/community leads | 6 | Reddit | submission ID, timestamp, archived/snapshot body hash |
| Generic/official-web controls | 6 | none expected | canonical issuer URL |

A 42-task pilot only validates instrumentation, fixtures, and provider error behavior. It cannot
justify a performance claim. After the pilot, preregister a held-out balanced set of at least 120
tasks or an independently justified sample size. Reddit should remain exploratory until native
backend attribution and archive/snapshot behavior are explicit.

An illustrative fixture object, which is a proposed schema rather than a file that exists today:

~~~json
{
  "schema_version": 1,
  "task_id": "gh-007",
  "stratum": "github_repository",
  "question": "Which maintained project provides the requested capability and what release documents it?",
  "queries": [
    {"query_id": "natural", "text": "natural language user query", "purpose": "realistic discovery"},
    {"query_id": "authority", "text": "capability plus maintainer/release wording", "purpose": "authority seeking"}
  ],
  "generic_lane": ["duckduckgo", "marginalia"],
  "specialist_lane": ["github"],
  "target_sets": [{
    "role": "must_find",
    "accepted_ids": ["github:owner/repository@tag-or-commit"],
    "canonical_url": "https://github.com/owner/repository",
    "why_decisive": "independent curator rationale written before execution"
  }],
  "target_frozen_at": "2026-07-31T00:00:00Z",
  "fixture_source_provenance": "reviewed blind to evaluated run outputs",
  "sensitivity": "public"
}
~~~

Use canonical identity sets rather than exact URL matching. An arXiv abstract, HTML page, and PDF
can be the same work; DOI resolver variants can be the same paper; a mutable default-branch GitHub
URL is not a release fact. Include generic-web control tasks deliberately. Otherwise a benchmark
selects specialist wins by construction.

### Stage B: frozen-packet 2x2

After Stage A, give systems sealed source packets and prohibit unlogged additional retrieval:

| | Generic-web packet | Generic plus appropriate specialist packet |
|---|---|---|
| Strong direct baseline | One accountable lead, same model and fixed source/read/token/time/dollar envelope | Same lead and envelope |
| Bounded Aletheia workflow | Same generic packet, fixed bounded workflow | Same augmented packet, fixed bounded workflow |

This separates:

- direct-agent access lift;
- workflow lift when access is equal;
- the interaction between Aletheia's process and additional sources;
- practical outcome lift per request/read/token/dollar/second.

The direct baseline must not be a deliberately weak one-result search. It should be one competent lead
with the same model and envelope, a short verification pass, and the same sealed source material.
The Aletheia condition must not have unlimited expansion, invisible manual primary chasing, browser
access, or post-hoc task-specific prompt changes.

## Metrics and bounded operating contract

Primary Stage A metric:

~~~text
must_find_recall_at_10(lane)
  = evaluable tasks where an accepted must-find identity appears at provider rank <= 10
    / evaluable tasks

paired_access_lift
  = recall_at_10(generic_plus_specialist) - recall_at_10(generic)
~~~

Report per stratum and overall:

- generic-only, specialist-only, both, and neither target hits;
- paired target-recall lift and a stratified task-level bootstrap interval;
- reciprocal rank of the first accepted target;
- native unique-target yield, meaning specialist hit while generic top K misses;
- later readable-and-identity-verified target yield;
- provider success/error/rate-limit/fallback rates;
- p50/p95 provider and run wall time;
- logical and physical request counts, response/retained bytes, read count/bytes;
- model input/output/cache tokens, reported dollars, and explicit unknowns;
- degraded channels, fixture exclusions, and every failed run.

Never convert a missing capability into a silent zero. The current no-key generic condition lacks
Brave, which is a distinct condition from a configured generic-web lane with Brave. Keep conditions
immutable and report configuration as part of every result.

Pilot resource ceiling:

| Resource | Ceiling |
|---|---:|
| Tasks | 42 |
| Query variants/task | 2 |
| Providers/query | 2 generic + 1 appropriate specialist |
| Results/provider | 10 |
| Logical calls before retry accounting | 252 |
| Full reads / browser / paid calls | 0 / 0 / 0 |
| Global concurrency | 2, and one in-flight request/provider |
| Timeout | 15 seconds |
| Retry policy | At most one explicitly logged transient retry |
| Run wall-time | 30 minutes, then terminal incomplete with reason |

Run in provider-aware waves. arXiv has shared-IP throttle/cooldown behavior, GitHub's unauthenticated
budget is 60/hour, and Stack Exchange documents a keyless daily quota. Do not clear an arXiv cooldown
to make a run look healthy. Repeat later on separate dates/times with generic and specialist order
randomized within each task; web volatility is a result to measure, not a reason to rerun until one
lane wins.

## Proposed executable harness

No checked-in source-access probe exists at this review's end. Build the small evaluation harness
before expanding orchestration. Its proposed interface is:

~~~sh
python3 scripts/eval/source_access_probe.py validate-fixtures \
  --fixtures fixtures/source-access-v1.jsonl

python3 scripts/eval/source_access_probe.py run \
  --fixtures fixtures/source-access-v1.jsonl \
  --run-dir audits/2026-07-31-source-access-2x2-evaluation/runs/<run-id> \
  --generic-lane duckduckgo,marginalia \
  --k 10 \
  --timeout-s 15 \
  --max-physical-attempts 2 \
  --max-logical-requests 252 \
  --max-wall-s 1800 \
  --global-concurrency 2 \
  --per-provider-concurrency 1 \
  --seed 20260731 \
  --no-browser \
  --no-paid-connectors

python3 scripts/eval/source_access_probe.py score \
  --run-dir audits/2026-07-31-source-access-2x2-evaluation/runs/<run-id> \
  --fixtures fixtures/source-access-v1.jsonl \
  --out audits/2026-07-31-source-access-2x2-evaluation/runs/<run-id>/score.json

python3 scripts/eval/source_access_probe.py replay \
  --run-dir audits/2026-07-31-source-access-2x2-evaluation/runs/<run-id> \
  --fixtures fixtures/source-access-v1.jsonl
~~~

The expected layout is:

~~~text
<run-dir>/
  manifest.json
  channel-health.json
  requests.jsonl
  candidates.jsonl
  canonicalization.jsonl
  budget.jsonl
  score.json
  raw/
~~~

Replay must make no network request. It must recompute canonicalization and scores exactly from sealed
receipts and fixtures. This makes metric calculation reproducible even though the live web is not.

Every physical request should have a receipt equivalent to:

~~~json
{
  "schema_version": 1,
  "run_id": "uuid",
  "task_id": "gh-007",
  "query_id": "natural",
  "lane": "specialist",
  "adapter": "github",
  "backend": "github_repository_search",
  "adapter_sha256": "code fingerprint",
  "provider_config_fingerprint": "non-secret fingerprint",
  "query_original": "fixture query",
  "query_effective": "exact provider query",
  "logical_request_id": "uuid",
  "physical_attempt": 1,
  "started_monotonic_ns": 0,
  "ended_monotonic_ns": 0,
  "status": "ok",
  "http_status": 200,
  "retry_reason": null,
  "cache_state": "cold",
  "response_bytes": 0,
  "raw_response_sha256": "digest-or-null",
  "credential_mode": "none",
  "price_usd": null
}
~~~

Candidates must link to a request receipt and include provider_rank, returned/canonical URL,
observed canonical identifiers, adapter, backend, and a response-record digest. Do not store keys,
headers, or sensitive raw text in committed audit data.

## Implementation implications and decision rule

The probe will likely force the following fixes or explicit limitations:

1. Do not let router heuristics allocate an access-test treatment.
2. Make fallback/backend provenance first-class, especially for Reddit and readers.
3. Retain ordered provider output before deduplication.
4. Record original/effective query, attempt count, timing, bytes, and response state.
5. Fix or separately stratify GitHub's star-ranked repository search; evaluate exact ID resolution
   separately from popularity discovery.
6. Treat Stack Exchange site as a task field.
7. Add source identity/resolution states before scoring usable evidence.
8. Keep discovery source, document type, epistemic role, and claim support distinct.
9. Pin commit, dirty state, adapter hashes, configuration fingerprint, dependency/runtime version,
   and secret presence only.
10. Freeze packets for the full workflow comparison.

An added access capability earns complexity only when a held-out, capability-matched trial shows a
predeclared practical lift in target recall or usable verified evidence without unacceptable
reliability, latency, or request burden. If generic web finds the same decisive target at comparable
rank, retain the simpler lane for that stratum. If a native source finds extra leads that cannot be
resolved or do not improve outcome metrics, keep it as an optional lead generator rather than market
it as an accuracy guarantee.

This is the evidence path that can validate the user's intuition. Aletheia might win sharply on
source-native corpora. Current code and these bounded diagnostics show that the win is neither
universal nor reliably attributed yet.
