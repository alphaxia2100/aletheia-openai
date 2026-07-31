# Independent analysis: why source access is not yet Aletheia's advantage

## Verdict

**Aletheia should not currently be described as much better because it accesses
sources that traditional search cannot.** The stronger statement is not merely
unproven; this audit's live work shows that the present implementation often
fails before access becomes a usable, identity-compatible candidate. It has a
credible *product hypothesis*: differently indexed public surfaces can surface a
decisive source that a narrow generic-web contract misses. It does not have a
demonstrated current performance advantage over a competent direct lead.

```text
public endpoint exists
  ≠ Aletheia can formulate a working request
  ≠ it receives the intended record under a stable identity
  ≠ it can read and verify the intended document
  ≠ it changes a correct final answer
  ≠ a capable direct agent could not do the same
```

The first live pilot has a literal URL score of generic 1/3 and specialist 0/3;
the generic hit disappeared in a post-hoc replication. Separately, known
identifier/slug diagnostics can resolve expected records, but that is not a
natural-language discovery win. The product claim “Aletheia is already much
better because of unique source access” fails this audit. Operational specialist
discovery is unproven and currently unreliable. A carefully designed multi-index
source bundle remains a plausible but untested product hypothesis, especially on
specific index blind spots.

These caveats do not imply that generic web is better. The biomedical semantic
endpoint is not evaluable under the frozen URL-only matcher; two specialist calls
were broken by a query-sanitization error; and the three tasks are not
representative. See [results.md](results.md) and the independent
[result-integrity review](research/result-integrity-review.md).

## Why the intuition is partly right

A conventional one-search-box workflow can miss sources in a disciplinary
index, repository, issue tracker, registry, docket, catalogue, or community
archive. Europe PMC can expose biomedical metadata; arXiv can expose preprint
identifiers and versions; GitHub can expose repository state; Stack Exchange can
expose accepted-answer metadata. A source-native API can beat generic ranking
when the decisive artifact is buried, recent, versioned, or poorly crawled.

That is an **access-bundle** advantage against a restricted web-only workflow,
not an architectural entitlement. The channels inspected here are principally
public APIs or public pages. A strong direct agent with the same lawful tool
grant can call them too. If an integration has paid, private, authenticated, or
browser-session data, it may be very valuable, but the benefit belongs to the
entitlement and must be reported separately from research orchestration.

The earlier frozen-packet comparison makes the counterfactual clear. It held
source access constant, so it could not measure discovery. After independent
correction, its factual rubric was an **11–11 tie** while the structured arm
declared 28 document-read assignments to the direct arm's eight. See the
[independent method audit](../2026-07-28-deep-runtime-and-head-to-head/comparison/independent-method-audit.md).
That does not refute an access advantage. It does block the invalid inference
that more endpoints automatically make the current workflow better at using
them.

## Why the present runtime loses the opportunity

### Query translation is part of access

The OpenAlex adapter sends ordinary natural-language questions—including a
terminal `?`—to OpenAlex's stemmed `search` parameter. OpenAlex treats `?` as a
wildcard and returns HTTP 400. That occurred in two specialist calls in the
first run and again in the replication. A punctuation-free compact query
returned records immediately. An enabled connector is therefore not the same as
available research capability.

The GitHub adapter compacts the autoresearch question to four terms,
`karpathy autoresearch constrain agents`, and repository search returns zero
rows. Its exact-slug query succeeds at rank 1. The adapter also requests GitHub
repository search ordered by stars; the independent runtime review shows that
this can bury an exact known repository behind broad high-star matches. The
native access is defeated by query policy before an agent can inspect it.

The arXiv adapter can fetch the known preprint ID, yet the natural-language
primary request returned unrelated material. The exact-ID result is an endpoint
health check, not a discovery success. A v2 system needs endpoint-aware query
rendering, native syntax tests, and a fallback for empty or off-topic results;
it does not need a larger swarm around a malformed request.

### URL equality is not source identity

The creatine target is PubMed `39564533`. Europe PMC can return the same work
under a PMC URL but the normalized record does not retain PMID as a first-class
identity. The URL-substring matcher consequently gives a false-negative path
even for an exact PMID lookup. This is more than a scoring issue: a workflow
cannot deduplicate, verify, or credit sources reliably if URL spelling is work
identity.

A source receipt needs the requested and resolved URL; provider candidate ID;
canonical work/origin ID (DOI, PMID/PMCID, arXiv version, repository/tag/commit,
or official publication ID); observed body identity; content hash;
truncation/completeness; and the discovery receipt that found it. Until those
are explicit, neither “unique source” nor “verified read” is trustworthy enough
for a headline benchmark.

### The present evaluation can manufacture or hide a win

- The task/protocol/runner were untracked when independently reviewed. Current
  hashes prove present-file consistency, not a pre-run freeze.
- Result lists changed within minutes, including the only generic hit. A one-shot
  live scrape is not a stable recall score.
- Raw and replay share records only within their own access lane; generic and
  specialist calls were sequential, not a common simultaneous network snapshot.
- Brave was degraded without a key, so the generic lane is DuckDuckGo+Marginalia,
  not a silent proxy for a stronger commercial generic-search product.
- The fixture has three visible known-source tasks. It is neither sealed nor
  representative, so it can diagnose adapters but cannot support marketing.
- The process comparison is an in-memory dedupe/rank projection, not routing,
  reading, verification, or answer generation. Saved records omit ranker inputs,
  so two specialist replay orders cannot be regenerated from the persisted
  projection.
- No controller-owned ledger records physical requests, effective queries,
  retries, provider ranks, response hashes, bytes, model tokens, dollars, or
  human intervention. More work can look better without a fair cost comparison.

The [runtime review](research/runtime-review.md) independently finds examples
where generic DuckDuckGo discovered exact arXiv, GitHub, and Stack Overflow
targets at rank one while a native adapter did not. That is not proof that
generic web wins; it is a guard against cherry-picking only specialist-friendly
examples.

## How Aletheia stacks up today

| Comparator / question | Honest current position |
|---|---|
| One ordinary generic-web search | Aletheia has more *potential* routes and source-role guidance. It may win on a true index blind spot, but the current runtime has not shown reliable conversion of that potential into discovery. |
| Strong direct agent with identical specialist tools | No demonstrated Aletheia advantage. A direct lead can call the same public APIs; the fixed-source result gives no workflow win, and this live pilot does not show a specialist lift to exploit. |
| Karpathy-style minimal fixed-loop workflow | Aletheia is more complex without matched evidence of a quality/cost benefit. The useful lesson is to freeze the editable surface, measure one change under a fixed envelope, and keep/revert mechanically. |
| Managed deep-research product | Not evaluated. Such products can have different models, retrieval indices, licensed data, browser/session privileges, and price/latency envelopes; a connector inventory is not a cross-product comparison. |
| Aletheia v2 opportunity | Real if v2 turns selected source-native access into typed, evidence-verified, budgeted retrieval and proves a gain against an equal-tool direct lead. It must not be assumed from v0.5 connector count. |

## What to build—and what not to build

The right v2 default remains a bounded single lead with a small explicit
source-access policy. Use source-separated multi-agent work only when a task has
a predeclared reason and a global ledger can charge every request, read, token,
retry, and verifier turn. See the full design in
[v2-design.md](../2026-07-29-v2-ground-up-design/v2-design.md).

1. **Repair query and identity contracts before adding channels.** Render
   endpoint-native queries; strip/escape unsafe OpenAlex punctuation; record
   input and effective query; preserve PMID, PMCID, DOI, arXiv ID/version, and
   repository identity. Add target-labelled adapter regression tests.
2. **Make provider receipts immutable.** Persist request ordinal, endpoint,
   query, rank, status/retry/fallback, response digest, candidate identity, and
   canonicalization decision before any dedupe/ranking projection.
3. **Run a source-access map first.** Use sealed balanced tasks across
   biomedical, preprint, repository, Q&A, community, policy, and generic-web
   control strata. Hold request count, result cap, timeouts, keys, browser,
   retries, and baseline model/tool grant constant. Score canonical identities,
   not URLs.
4. **Only then run the actual 2×2.** Compare generic versus expanded source
   contracts and a strong direct lead versus bounded Aletheia workflow under the
   same model, global token/read/action/time/dollar envelope and blinded
   claim-level grading. The specification is in
   [research/protocol-review.md](research/protocol-review.md).

Do not retain an endpoint, planner branch, worker, or verifier because it sounds
research-like. Keep it only if a preregistered sealed evaluation shows valid
source-family reach or material claim coverage against a strong direct baseline,
identity/read reliability, a measured resource fit, and an independently judged
outcome benefit. Otherwise disable/revert it by default and preserve its failure
receipt. That is the path from “many sources exist” to “the system is materially
better for a user.”
