# Results: source access is available in theory, unreliable in the current path

**Status:** completed operational retrieval pilot; **not** an answer-quality,
cost, or general-recall benchmark.

The narrow question was whether the frozen v0.5 runtime's supplied specialist
adapters could surface three designated landmarks beyond a defined
DuckDuckGo+Marginalia lane, and whether its offline candidate transform retained
them. The preserved first observation has a literal URL-substring score of
generic web **1/3** and specialist **0/3**. That is not evidence that generic
web is superior: the fixture is tiny, live indexes drifted within minutes, and
independent review exposed endpoint/query and identity defects. It is an
operational-failure finding, not a valid broad source-access comparison.

The machine-readable derivation, raw-file hashes, and result hashes are in
[results.json](results.json). Volatile public response metadata is intentionally
kept out of Git under `raw/`.

## Integrity status

The harness ran against a clean detached runtime at commit
`5bea63a9ffb13e9de0e94f8ba38c426a301faaf8`, not this dirty working tree. Its
recorded task and result hashes verify. However, the protocol, task file, and
runner were untracked at review time. Their present hashes bind them to the
observation but do **not** independently prove they were committed/frozen before
the live request. The claimed preregistration is consequently an audit
limitation, not a fact this report can certify.

For **each task × access lane**, the live harness invoked two channel adapters
(six invocations per aggregate lane; 12 across the three-task primary run),
requesting at most eight records per invocation with a 20-second per-attempt
timeout. It made no browser, model, document-read, or human-selection call.
Connector-internal HTTP attempts/retries are not fully logged, so this is not a
physical-request count. Within an access lane, raw and replay use identical
retrieved records; generic and specialist calls were sequential within the
recorded 12.6-second observation window. The post-retrieval process cell is
only v0.5 work-level deduplication/ranking replay; it is not the full Aletheia
workflow.

This corrects the frozen protocol's shorthand “two requests” and “same live
snapshot window.” The protocol itself remains unchanged as the historical input:
it should have said two adapter invocations **per task/lane**, and it did not
obtain a common simultaneous generic/specialist snapshot.

Primary observation window: 2026-07-31 15:12:50–15:13:02 UTC. Recorded raw
observation hash:
`sha256:8157f3e636e5400af80edcde9addf2a245fd4621805a6cc9190c3b3c49804db8`.

## Frozen literal primary observation

| Designated task | Generic raw URL score | Generic replay | Specialist raw URL score | Specialist replay | Operational fact |
|---|---:|---:|---:|---:|---|
| Creatine cognition | literal miss | literal miss | literal miss / semantic **NE** | literal miss | Europe PMC returned 8 records; OpenAlex returned HTTP 400. |
| Equal-budget multi-agent research | literal miss | literal miss | literal miss | literal miss | arXiv returned 8 records but none matched the URL rule; OpenAlex returned HTTP 400. |
| Karpathy autoresearch repository | hit, DuckDuckGo rank 7 | retained, pooled rank 4 | literal miss | literal miss | GitHub and Stack Exchange returned zero records. |
| **Total (literal URL endpoint only)** | **1/3** | **1/3** | **0/3** | **0/3** | Specialist lane had 2 channel errors in 6 scheduled adapter calls. |

`NE` means *not evaluable as a semantic landmark result*. The biomedical
landmark is PubMed `39564533`, while Europe PMC normalizes a record with a PMCID
to a URL such as `.../PMC/PMC11574456` and does not retain PMID as a typed
field. The frozen URL rule therefore cannot establish whether Europe PMC
surfaced the intended work under an alias. The literal `false` is preserved; it
must not be reclassified after the run.

The generic autoresearch hit was retained in-memory and placed at pooled replay
rank 4 after appearing at DuckDuckGo's channel-local rank 7. These are different
candidate lists, so the ordinals are not a measured rank improvement. This is
one narrow preservation observation, not evidence that reranking generally
improves discovery: it is the only nonempty landmark-retention denominator, and
the saved public-record projection drops ranker inputs (including authors,
primary flag, and citation count). Independent replay from the saved projection
changes the two nonempty specialist top-eight orders.

## Post-hoc replication — deliberately not pooled with the primary

A second run used the identical recorded frozen runtime and task file about four
and a half minutes later. It was reported as using a fresh isolated
configuration/cache, but the saved receipt does not independently attest the
initial configuration/cache state. It was run after the first result and is a
replication diagnostic, not a replacement or second primary trial. Its result hash is
`sha256:d4be64530e5c62057cd94ec5d83f3496c65539bd096fd4059466ef53342fcd78`.

| Lane | First observation | Post-hoc replication | What changed |
|---|---:|---:|---|
| Generic direct raw | 1/3 | 0/3 | The DuckDuckGo autoresearch candidate was no longer in the returned top eight. |
| Generic replay top 8 | 1/3 | 0/3 | Follows the changed raw candidate set. |
| Specialist direct raw | 0/3 literal | 0/3 literal | No literal landmark; OpenAlex again failed on two tasks. |
| Specialist replay top 8 | 0/3 literal | 0/3 literal | No available literal specialist landmark to retain. |

This is far too few runs to estimate reliability. It does demonstrate why a
one-shot live scrape cannot support a timeless performance claim and why a
future study needs interleaving, immutable result receipts, and repeated trials.

## Post-hoc adapter and identity diagnostic

The following diagnostic was explicitly separated from the primary endpoint. It
asks whether a miss means “the source is unavailable” or instead reflects a
query/normalization failure. It used the same frozen commit, public metadata
only, and no model or full-document reads. Result hash:
`sha256:162b245bde8d38b9cb5245a2b892f8e9fd2ed1c64779401c5104250df043beb1`.
The executable is [posthoc_adapter_diagnostics.py](posthoc_adapter_diagnostics.py).

| Diagnostic | Observation | What it establishes — and does not establish |
|---|---|---|
| Europe PMC, `creatine cognition EFSA` | The target title appeared at rank 2, but the URL did not contain PubMed `39564533`. | The URL-only rule has a cross-adapter false-negative path. It does **not** turn the original natural-query observation into a specialist win. |
| Europe PMC, exact `39564533` | The target title appeared at rank 1; the URL still did not contain the PMID. | The endpoint can resolve a known identifier, but the adapter loses that typed identity. Known-ID lookup is not ordinary discovery. |
| arXiv, exact `2604.02460` | The paper appeared at rank 1. | The native endpoint can retrieve a known arXiv ID, not that the current natural-language query discovers it. |
| GitHub, natural question | The adapter compacted the question to `karpathy autoresearch constrain agents` and returned zero repositories. | Current query translation can make public native access unusable. |
| GitHub, exact `karpathy/autoresearch` | The repository appeared at rank 1. | An exact slug works after the decisive identifier is already known. |
| OpenAlex, natural question ending in `?` | The endpoint returned HTTP 400; its error explains that `?` is a wildcard in stemmed search. | Two primary specialist failures are reproducible query-sanitization failures, not evidence that OpenAlex lacks relevant literature. |
| OpenAlex, `creatine cognition` | The endpoint returned eight records. | The endpoint itself was reachable with a punctuation-free compact query; this is not a landmark-recall result. |

The diagnostic changes the interpretation, not the frozen score: **the current
path has not converted public specialist access into reliable discovery.** It
would be dishonest to count a known-ID lookup as a successful natural-language
run.

## What the pilot can and cannot conclude

It supports these limited conclusions:

- In the post-hoc diagnostic, Europe PMC, arXiv, and GitHub resolved known
  identifiers or a repository slug to the expected record; Europe PMC's
  normalized result did not retain the PMID.
- The current query and identity path did not reliably exploit that capability
  in this fixture.
- No observed result supports “Aletheia is already much better because of
  specialist access.”
- The only observed raw generic hit survived the narrow in-memory replay.

It does **not** establish that generic web is better, that specialist sources
have no value, that Aletheia gives a better final answer, that it is faster or
cheaper, or that a public source is exclusive to Aletheia. The generic contract
was specifically DuckDuckGo plus Marginalia—not Google, Brave, a managed deep
research product, or a direct lead with the same specialist tools. Brave was
degraded without an API key. The three visible known-source tasks are a
regression fixture, not a representative or held-out sample.

The correct next product evaluation is the sealed, resource-matched factorial
design in [research/protocol-review.md](research/protocol-review.md), not a
larger extrapolation from these three outcomes.
