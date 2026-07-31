# Result-integrity review — source-access 2×2 pilot

**Reviewer:** independent result-integrity pass
**Review date:** 2026-07-31
**Scope:** `protocol.md`, `tasks.json`, `run_access_probe.py`, the local
`raw/observed-1.json`, and the clean runtime recorded by that observation. I
made no change to preregistered inputs, raw observations, production code, or
other reviewers' files. The few runtime checks below were read-only and did not
re-run the pilot.

## Auditor verdict

This is a useful **operational retrieval incident report**, with a sound
in-memory raw-versus-rerank comparison for the one GitHub discovery it contains.
It is **not yet a valid result from which to infer whether specialist source
access helps or hurts Aletheia**.

| Dimension | Verdict | Reason |
|---|---|---|
| File self-consistency | Pass | The recorded task and result hashes recompute exactly. |
| Frozen executable runtime | Pass, with limits | `runtime_commit` resolves to clean commit `5bea63a`; runtime code was isolated from the dirty checkout. |
| Preregistration proof | Not independently established | Protocol, tasks, and runner were untracked, so the present hashes prove only that today's files match the observation, not that they were fixed before it. |
| Literal preregistered URL score | Mechanically reproducible from the recorded score fields | It is the score the script was programmed to calculate. |
| Semantic landmark / source-identity score | Fail for the biomedical landmark; weak elsewhere | The primary matcher is URL-substring-only, while adapters discard key stable identifiers and aliases. |
| Specialist-access comparison | Inconclusive | Two OpenAlex calls failed because the implementation sends a terminal `?` as an OpenAlex wildcard; the GitHub query compiler over-constrains a named-repository lookup; arXiv returns irrelevant rows. These are implementation/query-policy failures, not evidence that the sources lack the landmarks. |
| Candidate-replay result | Narrowly valid, not a workflow result | It reuses the same in-memory records and performs only dedupe/ranking. It does not exercise normal retrieval, routing, source selection, reading, or answering. |
| Candidate-replay reproducibility from the saved raw artifact | Fail | The saved projection omits fields used by the ranker; reconstructing it changes both nonempty specialist top-eight orders. |
| Cost, latency, answer quality, or multi-agent value | Not measured | The protocol correctly excludes model calls and reading; its timing fields are per adapter invocation, not end-to-end latency or cost. |

The appropriate headline is therefore: **the current path demonstrably has
source-access operational failures and identity-observability gaps; this pilot
does not demonstrate that specialist sources fail to add value.**

## What is verified

### Artifact and runtime checks

The following checks passed without modifying an artifact.

| Check | Observed value | Assessment |
|---|---|---|
| `tasks_sha256` | `sha256:4d20bebac1bb2324c71b83ae518a68fe1318d50c2c0a42e467edc7308bd53a16` | Equals canonical JSON of the current `tasks.json`. |
| `result_sha256` | `sha256:8157f3e636e5400af80edcde9addf2a245fd4621805a6cc9190c3b3c49804db8` | Equals canonical JSON of `observed-1.json` with `result_sha256` excluded. |
| Runtime pin | `5bea63a9ffb13e9de0e94f8ba38c426a301faaf8` | Resolves to the recorded clean detached runtime, whose commit message is `docs: add Aletheia v2 design audit`. |
| Channel config | bundled configuration, hash `f98d438f…dda769` | The output identifies enabled channel names and the bundled config hash. |
| Run interval | 12.585476 seconds | Consistent with `started_at_utc` and `finished_at_utc`; this is observational, not a latency benchmark. |

The clean runtime pin is a real strength. It prevents the current dirty working
tree from silently changing the connector or ranker used by the run. It does
**not** pin the pilot runner, its task file, its execution command, credentials,
cache state, HTTP attempt trace, or remote index snapshots.

### Literal primary outcome, frozen as recorded

Do not change this table retrospectively. Under the exact rule in
`tasks.json`—`any returned URL contains a declared string`—the observation is
self-consistent:

| Task | Generic raw URL hit | Specialist raw URL hit | Candidate replay result | Literal reading only |
|---|---:|---:|---|---|
| `creatine-cognition` | No | No | No | Neither returned URL contained `39564533`. |
| `multiagent-research` | No | No | No | Neither returned URL contained `2604.02460`. |
| `autoresearch-program` | Yes, DuckDuckGo raw rank 7 | No | Generic retained at pooled rank 4 | The generic lane returned the canonical GitHub URL. |

This gives a **literal descriptive count** of generic 1/3 and specialist 0/3
for this one observation. It is not a semantic conclusion or an estimate of a
win rate. Calling it simply “the landmark result” would overstate what it
means; the next section explains why.

## Literal score versus landmark identity

### The required distinction

There are three different statements which must not be collapsed:

1. **Literal rule result:** a URL in the saved records contained the exact
   substring configured in `tasks.json`. This is what the frozen script
   reports, and its false values must remain intact.
2. **Operational result:** the current adapter/query policy returned records,
   zero records, or an error at that time. An error is a genuine user-facing
   availability failure and belongs in an operational denominator.
3. **Semantic landmark discovery:** the source index surfaced the designated
   work or repository, including any canonical aliases. The current artifact
   does not reliably establish this for the biomedical task and cannot use a
   connector failure to establish source absence.

The first two are observations. The third is the construct the protocol says it
wants to measure. The third is not licensed by the current matcher.

### Biomedical identity mismatch — material defect

The creatine landmark is a **PubMed identifier**, `39564533`. The Europe PMC
adapter in the frozen runtime chooses a PMC URL whenever a PMCID is available:

```text
https://europepmc.org/article/PMC/<pmcid>
```

It then discards the API's source/id/PMID fields. The OpenAlex adapter similarly
uses a DOI or OpenAlex work URL and drops the `ids.pmid` alias. Finally,
`run_access_probe.py` persists only a limited public record projection, which
also has no typed source IDs. A record for PubMed `39564533` can therefore be
returned yet fail the URL-substring matcher.

Consequently:

- The recorded `false` is a valid result of the **literal URL test**.
- It is **not an interpretable semantic miss of PubMed record 39564533**.
- The returned Europe PMC titles do not visibly identify the target, so this
  observation is not evidence that the target was actually present and
  mis-scored. Rather, the endpoint definition is incapable of proving the
  intended construct if it is present. The semantic score is therefore
  *not evaluable as designed*, rather than a source-access loss.

This is not a reason to edit the frozen result. It is a reason to label the
creatine source-access inference `NE` (not evaluable) in the report while
retaining its literal `false` in the immutable primary table.

### Other matcher limits

- The arXiv URL happens to carry `2604.02460`, but the matcher does not parse a
  versionless arXiv ID. It will be brittle across canonical URLs, PDF/HTML URLs,
  or alternate hosts.
- The GitHub rule worked for this exact canonical URL but is still a plain
  substring test, not a normalized owner/repository identity. It can miss
  `www`/trailing-slash/redirect variants and can accept a non-repository URL
  containing the string.
- URL containment supplies neither relevance nor evidence identity. It is
  appropriate only as a temporary discovery fixture, not as an answer-quality
  proxy.

### Exact correction for future runs

Use a predeclared identity registry, not a URL token list. Each landmark should
have typed aliases, for example:

```json
{
  "landmark_id": "creatine-efsa-2024",
  "identifiers": {
    "pmid": ["39564533"],
    "pmcid": ["PMC11574456"]
  },
  "canonical_urls": ["https://pubmed.ncbi.nlm.nih.gov/39564533/"]
}
```

Adapters must preserve `source`, `source_id`, `pmid`, `pmcid`, DOI, arXiv
ID, and canonical GitHub slug in normalized records. The persisted candidate
ledger must retain them. The matcher should compare typed, normalized identities;
canonical URL comparison is a secondary fallback with false-positive tests.

For this run, keep `tasks.json` unchanged. An exact-ID retrieval check belongs
in a separately named **post-hoc adapter/identifier diagnostic**, with its own
hash and explicit statement that it cannot repair the primary result.

## Why the specialist misses cannot be read as source absence

### OpenAlex's 400 is a reproducible query-sanitization bug

Both OpenAlex calls in the observation failed with HTTP 400. The frozen
`openalex.py` sends the natural-language question unchanged when it is fewer
than 100 characters. Both questions end in `?`. A read-only request using the
same URL shape received OpenAlex's explicit error:

```text
Wildcards (* or ?) require exact (no-stem) search.
```

Thus the specialist cells contain a real **current implementation failure**, not
a test of whether OpenAlex indexes the target. Preserve the error in the
operational denominator, but do not translate it into “OpenAlex has no useful
record” or “specialist access lost.”

Required repair before a new run:

1. sanitize/escape terminal `?` and `*` for OpenAlex's stemmed search, or use a
   deliberate exact-search mode only when that is the intended query;
2. add adapter tests for ordinary question punctuation and inspect the emitted
   request URL, status, and response error body;
3. record those request facts in the run trace, not only the truncated Python
   exception string; and
4. make the repaired rerun a new, post-hoc run ID rather than a replacement for
   `observed-1.json`.

### Channel-specific query compilation is hidden and materially changes treatment

The protocol says all lanes receive the same predeclared query. That is true of
the Python argument, but not necessarily of the endpoint query:

| Adapter | Effective behavior relevant here | Integrity consequence |
|---|---|---|
| GitHub | Compacts the repository question to `karpathy autoresearch constrain agents` before an AND-like repository search. | A named-repository discovery query is over-constrained; zero rows do not show that GitHub lacks the repository. |
| Stack Exchange | Compacts to five terms and searches the default Stack Overflow site. | It is not a second source-code repository index for this task. |
| Marginalia | Compacts long questions to six terms. | The generic lane also receives a transformed query, not the literal question. |
| OpenAlex | Sent the punctuation-bearing question and failed. | The task is confounded by a known client bug. |
| arXiv | Sent the natural-language question through the export API and returned eight clearly unrelated physics rows. | The connector is reachable, but this query policy did not retrieve the target. |

`observed-1.json` records only the original task query. It does not record the
effective per-adapter query, retry/relaxation path, URL, response status, or
attempt count. The claimed fixed network contract is therefore only partially
auditable.

Fix this by having each adapter return a structured trace such as
`input_query`, `effective_query`, `endpoint`, `attempts`, `retries`,
`response_statuses`, `response_hash`, and `credential_mode` (never a
secret). For named entities, benchmark a predeclared channel-specific query
compiler or a separately labeled exact-identifier lookup. Do not allow a generic
natural-language question to silently become different, unrecorded retrieval
treatments across endpoints.

## The four cells are a paired transformation, not a full factorial experiment

The protocol is admirably explicit that candidate replay uses the same network
records. That is the correct way to hold the snapshot fixed for a narrow
retention check. It also means the rows are not four independent executions:

```text
one live access-lane retrieval  →  raw union of records
                                   └→ deterministic dedupe/rank replay
```

The runner invokes `DISPATCH` directly and then calls only
`_dedupe_records()` and `rank.rank()`. It bypasses the normal
`investigate.retrieve()` path, including its concurrent requests and
zero-result query relaxation. The protocol's phrase “v0.5 work-level dedupe and
rank” is accurate; any report must not call this “the Aletheia workflow” or
estimate a workflow-by-access interaction from it.

### Retention denominator is mostly vacuous

The replay top-k is eight **pooled** candidates, while raw access can contain up
to 16 (two channels × eight). The raw sizes in this run are:

| Task / access | Raw candidates | Candidate top-k | Can top-8 replay drop a raw item? |
|---|---:|---:|---|
| Creatine / generic | 16 | 8 | Yes |
| Creatine / specialist | 8 | 8 | No — every raw item fits. |
| Multi-agent / generic | 16 | 8 | Yes |
| Multi-agent / specialist | 8 | 8 | No — every raw item fits. |
| Autoresearch / generic | 11 | 8 | Yes |
| Autoresearch / specialist | 0 | 8 | No candidates. |

Only the generic autoresearch cell contains both a landmark access hit and a
nontrivial compression: the target moved from DuckDuckGo's within-channel raw
rank 7 to pooled candidate rank 4 and remained in the top eight. That is a
valid, narrow preservation observation. It is not evidence that reranking
generally improves discovery.

The distinction between `candidate_replay.landmark.hit` and
`candidate_replay.landmark.retained_top_k` must also remain explicit. The
former may be true outside the displayed top eight; only the latter answers the
predeclared retention question.

`best_raw_rank` is a channel-local ordinal, not a global rank across the raw
union. It should be displayed as channel plus rank rather than compared
numerically to a pooled candidate rank without that caveat.

## Persisted raw data cannot reproduce the recorded replay

This is a concrete reproducibility failure, not merely a documentation wish.

`public_records()` in `run_access_probe.py` persists only channel, raw rank,
class, index group, URL, title, DOI, date, and snippet. It drops `authors`,
`primary`, `cited_by_count`, source IDs, and other normalized fields. The
frozen ranker uses authors in TF–IDF relevance and uses both citation count and
`primary` in its score.

I replayed the frozen `pipeline_replay()` against the saved projected records,
without network access or edits. Saved versus regenerated top-eight order was:

| Cell | Replay from saved records |
|---|---|
| Creatine / generic | Matches |
| Creatine / specialist | **Does not match** |
| Multi-agent / generic | Matches |
| Multi-agent / specialist | **Does not match** |
| Autoresearch / generic | Matches |
| Autoresearch / specialist | Matches (empty) |

The two specialist order mismatches are exactly what the omitted rank inputs
permit. Therefore the raw result hash proves that a JSON file has not changed;
it does **not** provide an independently replayable derivation of the candidate
ranking. Because `raw/` is ignored by Git, a future auditor may not even have
this incomplete local projection.

Required repair:

1. persist a normalized, schema-versioned candidate ledger containing every
   field consumed by dedupe, ranking, and matching, plus a redaction policy;
2. hash each input ledger and emit a derived-result manifest that includes
   runner/protocol/task hashes, command line, Python version, and runtime tree
   hash;
3. retain public metadata either in the audit repository or in a durable
   content-addressed archive with a committed manifest pointer; and
4. make the validator re-run dedupe/rank from that ledger and assert exact
   candidate order, scores, and landmark fields.

## Reproducibility and protocol deficiencies

### No independently auditable pre-run freeze

At review time, `protocol.md`, `tasks.json`, and `run_access_probe.py` are
untracked files. Their hash in the output ties the observation to their present
contents, but no Git commit, signed tag, external timestamp, or recorded tree
hash proves they existed unchanged before the first live request. The claim of
predeclaration may be true; it is simply not independently verifiable from the
artifact.

For subsequent runs, commit a baseline containing the protocol, tasks,
identifier registry, runner, and validation script **before** retrieval. Record
the baseline commit/tree hash, clean/dirty assertion, and hashes of every
executed file in the output. A signed tag or external timestamp strengthens the
claim. Execute from that detached baseline, not merely from a directory whose
runtime happens to be clean.

### Network contract is looser than its wording

`direct_lane()` makes one *adapter invocation* per channel, but the adapters
may make multiple HTTP requests. `_http.get_bytes()` retries several transient
errors; arXiv has additional retry/cooldown behavior. The 20-second value is a
per-attempt timeout, not a hard adapter or task deadline. The script also runs
the two channels sequentially, whereas normal `investigate.retrieve()` runs
them concurrently.

This does not invalidate the raw observation. It means the phrase “exactly two
requests” should be corrected to “two adapter invocations, with
connector-internal attempts recorded,” and the current latency figures must not
be treated as comparable end-to-end lane latency. No model/API bill, retry
count, byte count, credential mode, or wall-clock lane total is captured.

### Environment and mutable external state are under-recorded

The channel configuration hash is useful but incomplete. Results may vary with
GitHub/OpenAlex credentials, API rate limits, locale/IP, server ranking, and the
isolated cache (notably arXiv's cooldown file). None of the following is in the
artifact: command invocation, environment presence flags for credentials, cache
initial-state digest, Python version, OS/platform, HTTP response headers, or
endpoint result hashes. Record nonsecret boolean/mode fields and request metadata
next time; do not store credentials themselves.

## Claims the completed report may and may not make

### Supported, if worded narrowly

- On 2026-07-31, with the recorded frozen runtime and network conditions,
  DuckDuckGo returned `github.com/karpathy/autoresearch` at its raw rank 7; the
  frozen pooled replay placed it at rank 4.
- OpenAlex produced HTTP 400 in both affected specialist calls; GitHub and Stack
  Exchange returned zero for the repository question under their current query
  compilers.
- The pilot found concrete reliability problems worth fixing: typed identity
  loss, OpenAlex punctuation handling, opaque query rewriting, and incomplete
  replay provenance.

### Unsupported

- “Specialist sources do not add access value,” “generic web is better,” or any
  general 1/3-versus-0/3 performance claim.
- “Aletheia's workflow was tested” or an estimate of workflow/access
  interaction. Only a deterministic candidate transformation was tested.
- Any claim about answer accuracy, source verification, user value, total cost,
  end-to-end speed, or multi-agent orchestration.
- A claim that the sources lack the known landmarks. The observed errors and
  query failures instead diagnose the current access path.

## Keep/revert discipline for this result

1. **Keep** `tasks.json`, `protocol.md`, `run_access_probe.py`, and
   `observed-1.json` intact as the record of run 1. Do not silently “fix” the
   original primary score or swap in a successful exact-ID lookup.
2. **Label** the report's original result as `literal URL-score / operational
   pilot`, with the biomedical semantic conclusion marked `NE` and the
   specialist failures described as implementation confounds.
3. **Repair separately**: typed IDs, OpenAlex punctuation behavior,
   channel-specific query tracing, and replayable ledger serialization should be
   implemented and unit-tested outside this frozen observation.
4. **Replicate separately** from a committed baseline with fresh, recorded cache
   state and a new run ID. Index drift is expected; a later success or failure is
   a replication outcome, not a revision of run 1.
5. **Promote only after a sealed benchmark**: use enough stratified tasks and
   multiple typed landmarks, a direct agent with the same source grants, fixed
   total budgets, and blinded answer-level evaluation. Until then, this pilot
   should guide engineering fixes, not product-performance claims.
