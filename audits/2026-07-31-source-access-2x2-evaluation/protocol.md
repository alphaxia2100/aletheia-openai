# Preregistered source-access 2×2 pilot

**Status:** protocol frozen before this audit's first live retrieval.
**Question:** Does Aletheia's specialist source surface retrieve designated,
decision-relevant landmarks that a healthy two-index generic-web lane does not,
and does its current candidate-processing path preserve those landmarks?

## Why this is the right next test

The prior controlled comparison held the source packet fixed. It could test
workflow overhead after access was equal, but could not test the user's central
claim: more and different source endpoints may make Aletheia substantially more
useful. This pilot isolates that claim at the retrieval/candidate layer before
pretending to know whether the extra sources improve a final answer.

It is deliberately **not** a general benchmark and cannot establish that
Aletheia is better than a capable direct agent. A direct agent given identical
channel credentials can use those channels too. The actual differentiator under
test is the supplied source-access policy and its retention through the current
pipeline—not an intrinsic property of a role prompt.

## Factors and four cells

The test crosses a source-access factor with a post-retrieval process factor.
All four cells see the same predeclared query, live snapshot window, per-channel
limit, timeout, no-browser rule, and no-model/no-reading policy.

| Process factor | Generic-web access | Specialist access |
|---|---|---|
| **Direct/raw** | DuckDuckGo + Marginalia records as returned by their adapters | Two topic-specific Aletheia adapters as returned by their adapters |
| **Aletheia candidate replay** | The same generic records passed through v0.5 work-level dedupe and rank | The same specialist records passed through v0.5 work-level dedupe and rank |

The process factor is an offline replay, not a second network call. That is
intentional: it prevents the structured condition from buying a different web
snapshot or extra connector requests. It tests whether the current candidate
transform keeps a source that direct access surfaced. It does **not** test
planning, agent source choice, full-text extraction, verification, or final
prose.

## Fixed network contract

`tasks.json` is the machine-readable contract. Every task gets exactly two
requests in each access lane, at most eight records per channel, with a 20-second
per-request timeout. The pilot makes no browser calls, model calls, retries
beyond connector-internal behavior, full-document reads, or human source
selection. Network effects are public metadata retrieval only.

The generic lane uses two healthy, independent no-key web indexes:

- DuckDuckGo (`bing` index group), and
- Marginalia (independent small-web index).

The specialist lane uses two enabled, topic-specific channels. This is not a
claim that two source types have equal quality or that the lanes have equal
expected recall. It is an intentionally small **access frontier** comparison:
the total number of requests is held fixed while the index families differ.

Brave is excluded because it is unavailable without a key. Its absence is a
coverage limitation, not a win for either lane. Channels that return empty,
error, or rate-limited results remain in the denominator and are reported.

## Landmarks and primary endpoint

Each task contains one predeclared landmark matching rule based on a stable
identifier or canonical repository URL already named in repository material.
The main endpoint is a binary **candidate hit**:

```text
hit = any returned URL contains one of the task's predeclared landmark strings
```

The report also records the best raw per-channel rank, the candidate-replay rank
after Aletheia work-level deduplication/ranking, returned count, errors,
latency, and effective query. It must distinguish:

- **access hit:** a lane returned the landmark;
- **retention hit:** the candidate replay retains it in the top-eight ranked
  candidates; and
- **answer-level value:** *not measured here*.

The primary descriptive comparison is the paired difference in landmark hits
between specialist and generic access. With three tasks it has no meaningful
statistical power; it is a regression fixture with a transparent outcome, not a
significance test. A result of 3/3 versus 0/3 would be a reason to build a
larger benchmark, not evidence of a general win rate.

## Predeclared interpretation

| Observation | Allowed interpretation | Forbidden interpretation |
|---|---|---|
| Specialist lane retrieves a landmark generic misses | For this frozen task/window, specialist access supplied a candidate absent from the defined generic lane. | Aletheia gives better final answers in general. |
| Both lanes retrieve it | The landmark was not exclusive under this generic-web setup. | Specialist channels add no value on other tasks. |
| Specialist fails or rates limits | That channel/task/run did not demonstrate access value; failure remains an operational cost. | The source does not exist or generic search is superior generally. |
| Replay drops/downranks an access hit | Current v0.5 candidate handling can lose available access; inspect the exact mechanism. | The underlying channel lacks value. |
| Replay preserves it | This narrow post-retrieval transform did not lose that landmark. | The workflow verified or used it correctly. |

## Threats deliberately not hidden

1. **Task selection is small and favorable to named specialist channels.** It
   is a predeclared regression fixture, not a representative draw. The next
   study must use sealed, stratified tasks and multiple landmarks per task.
2. **The generic baseline is a defined lane, not Google, Brave, a managed deep
   research system, or a strong agent with the same tool grant.** Those deserve
   separate cells in the larger study.
3. **Live indexes drift.** The run records date, runtime commit, channel health,
   request limit, and errors. It does not claim timeless recall.
4. **URL matching is not evidence identity or semantic relevance.** It only
   proves candidate discovery; the v2 identity/claim gate remains required.
5. **No model is asked to select/read/synthesize.** This cannot adjudicate
   Aletheia's agentic workflow, answer quality, cost, or latency end to end.
6. **The frozen runtime is checked out separately.** Uncommitted working-tree
   changes are excluded from the executable result.

## What follows if the pilot is positive

The next phase is a sealed, answer-level 2×2:

1. source access: generic lane versus broad specialist lane;
2. workflow: competent direct single lead versus v2/Aletheia policy;
3. same model/harness, source window, total model/tool/read/time envelope, and
   output cap;
4. independent claim/source annotation and blinded human-calibrated evaluation;
5. a 2×2 interaction analysis: access effect, workflow effect, and whether the
   workflow makes extra access usable rather than merely available.

That future study must include community, current/policy, repository, academic,
and biomedical strata; direct-agent-with-identical-tools is the serious control.
