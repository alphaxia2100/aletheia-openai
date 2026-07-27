# Semantic read-identity gate v0.6 — results

Status: **mechanism passed the exact-defect diagnostic; remains experimental and is not promoted**  
Base: `prod` at `060387b` (production runtime checkpoint `addfaf6`)  
Branch: `codex/exp-read-identity-gate-v06`

## Outcome

The candidate closes the observed false-success path. A long fetched body no longer becomes evidence
solely because it exceeds 1,500 characters. The runtime now records expected and observed identifiers,
title evidence, identity state, content state, content hash, resolver method, resolved URL, and the
persisted attempt path. Mismatches and unverified identities remain on disk but `_read_ok=false`.

The mechanism is deliberately conservative: the system distinguishes “this is the wrong document”
from “the body may be useful, but identity is not established.” Both are excluded from automatic
synthesis; the latter is recoverable through another resolver or explicit inspection.

## Portable mechanism A/B

The same 11 cases were evaluated under production's effective length predicate and the candidate
gate ([machine-readable result](fixture-ab.json)).

| Measure | Production predicate | Candidate |
|---|---:|---:|
| Correct case outcomes | 7/11 | **11/11** |
| False accepts | 4 | **0** |
| False rejects among five usable controls | 0 | **0** |
| Mismatch classification | not represented | **3/3** |

The four production false accepts were the two exact observed wrong bodies, a readable body with no
identity evidence, and a single conflicting strong identifier. Candidate controls covered a matching
DOI, title-only page, abbreviated manifest title, matching title with multiple cited DOIs, direct
YouTube-caption object, blocked interstitial, and image-only artifact. An expected DOI appearing only
in a wrong document's reference list also failed closed.

This is a mechanism diagnostic, not a claim that all open-web pages are represented by 11 fixtures.

## Same-run replay

The gate was replayed offline over all 34 rows that production had marked `_read_ok=true` in the
completed Aletheia self-survey
([machine-readable audit](same-run-audit.json)). It retained 30 and rejected four:

| Candidate classification | Count | Direct interpretation |
|---|---:|---|
| `verified_identifier` | 15 | expected strong ID found in trusted front matter/direct adapter |
| `verified_title` | 16 | normalized high-confidence title match |
| `mismatch` | **2** | the two ACM candidates whose bodies were unrelated GRADE articles |
| `unverified_identity` | **1** | an anti-bot human-verification interstitial |
| content `shell` | **1** | an arXiv “No HTML available” 404 shell that production had counted as a full read |

The two identity mismatches are the exact motivating defects. The replay also found two independent
content-integrity false successes that the initial diagnosis had not counted: a blocked interstitial
and an arXiv error shell. Fifteen of the retained reads were truncated, which remains visible as a
separate state and still requires an uncapped reread when a claim depends on the tail.

## Executable checks

- 164/164 repository tests pass; production had 156/156.
- Eight new regression methods cover portable cases, reference-list identifier laundering,
  identity/content orthogonality, retry eligibility, persistence, telemetry aggregation, and
  per-attempt provenance.
- Every read attempt emits a machine-readable event before the round summary. A crash after a fetch
  therefore cannot erase which body was accepted or rejected.
- A retry with different content is stored as `*.attempt-N.md`; it does not overwrite the first wrong
  body.

## What this does not solve

- It detects a failed resolver but does not yet execute a DOI/repository/HTML/PDF/OCR recovery ladder.
- Title parsing and thresholds need calibration on broader multilingual, legal, standards, books,
  code, forums, and publisher corpora.
- A matching title or identifier does not prove that a body is complete, current, unretracted, or the
  cited version.
- A content hash is tamper-evident only relative to the recorded event; it is not an externally signed
  archive timestamp.
- Excluding `unverified_identity` can reduce recall. Promotion needs paired real runs measuring both
  false acceptance and resolver-recovery yield, not just this clean regression result.

## Decision

Keep the branch experimental. It is a credible invariant candidate because it caught every observed
false success without rejecting the portable positive controls, but production should not inherit it
until a resolver-recovery branch proves that conservative identity gating does not strand important
evidence across diverse domains.

The next isolated mechanism should be a resolver ladder driven by typed failure state:

1. canonical identifier metadata (Crossref/OpenAlex/PubMed/arXiv/registry);
2. publisher HTML and PDF;
3. repository/author manuscript and archival snapshot;
4. browser render;
5. OCR for image-only documents;
6. explicit unresolved state with attempted routes and hashes.

Other ideas worth preserving: quarantine conflicting bodies into a run-wide identity-conflict index;
learn publisher-specific title/identifier adapters from observed failures; attach version/retraction
state to identity; and use the content hash to deduplicate alternate resolvers while retaining the
full attempt chronology.
