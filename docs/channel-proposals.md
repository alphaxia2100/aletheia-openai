# Channel proposals — sources worth adding to Aletheia

Researched via the toolkit itself (see `runs/` bake-off). The **core** now runs 12 live channels
(brave, duckduckgo, marginalia, openalex, arxiv, reddit, hackernews, stackexchange, github, youtube,
x, + read/jina). Below is a menu to widen coverage **per use-case** — enable per topic; more channels
≠ more rigor, so route to the 3 roles (independent-web · primary · un-laundered) plus any domain source.

`enable`: run `python3 ~/.cursor/skills/channel-retrieval/scripts/channels.py enable <name>` (already
implemented in the catalog). `add`: needs a small new client (`channel-retrieval/scripts/<name>.py`).

## Quick wins — already in the catalog, just enable (no code)
| channel | access | class | unlocks |
|---|---|---|---|
| **wikipedia** | no-key | lead_gen | fast orientation + citation-mining to primaries |
| **europepmc** / **pubmed** | no-key | evidence | biomedical/clinical literature (the arXiv-sized gap) — Europe PMC searches OA **full text**, not just abstracts |
| **semantic_scholar** | free-key | evidence | CS/ML citation graph + influential-citation signal |
| **crossref** | no-key | evidence | DOI metadata / reference lists for any paper |
| **unpaywall** | free-key | lead_gen | resolve any DOI → a legal free PDF (serves "read the primary in full") |
| **google_books / gutenberg / openlibrary / standard_ebooks** | no-key | evidence/color | history, humanities, long-form books |
| **discourse** | no-key | evidence | official project forums (Rust/Swift/PyTorch/…): near-primary maintainer answers off Reddit |

## New channels worth adding (by use-case)
**Academic / open-access / citations**
- **CORE** (free-key, evidence) — 40M+ full-text from institutional repositories: theses, working papers, grey literature DOI-centric channels miss.
- **bioRxiv / medRxiv** (no-key, lead_gen) — freshest bio/med preprints + preprint→published linkage (a peer-review maturity signal).
- **OpenCitations** (no-key, evidence) — a 3rd independent CC0 citation graph to triangulate against OpenAlex/S2 (directly serves the "40 sources or 1 echoed?" test + self-citation flags).
- **DOAJ** (no-key, lead_gen) — vetted open-access journal whitelist: a guardrail flag against predatory venues.

**Domain-authoritative primaries** (each fills a domain with *no* current coverage)
- **ClinicalTrials.gov v2** (no-key, evidence) — the trial registry incl. terminated/null/unpublished trials → the best lever against publication/spin bias on any clinical claim.
- **SEC EDGAR** (no-key, evidence) — US company primary filings (10-K/8-K/proxies/insider forms); the citable primary that finance news paraphrases.
- **CourtListener v4** (free-key, evidence) — US case law full text + citation graph (absorbs Harvard CAP); cite the actual holding, not a summary.
- **USPTO PatentSearch** (free-key, evidence) — granted patents / applications by assignee/CPC/date.
- **World Bank Indicators** (no-key, evidence) — ~16k cross-country socioeconomic time series for quantitative/policy claims.

**Web-index diversity** (fight single-index bias — currently Brave is the main independent crawl)
- **Mojeek** (free-key) + **Stract** (no-key) — additional *wholly independent* general crawls (not Google/Bing-derived).
- **SearXNG** (no-key) — metasearch fan-out across many engines from one endpoint.
- **Wikidata** (no-key, evidence) — entity grounding/disambiguation + external-ID bridges to authoritative registries.
- **Common Crawl CDX** (no-key) — open-web URL discovery + historical snapshots (provenance / change-over-time).

**Un-laundered community / practitioner / media**
- **Stack Exchange network sites** (no-key, evidence) — *enable non-SO sites*: Skeptics.SE (sourced debunking), Cross Validated (stats/ML), Health/Physics/History.SE — huge for non-software topics.
- **Lobsters** (no-key, lead_gen) — high-signal senior commentary on PL/systems/security/infra.
- **Substack + generic RSS/Atom** (no-key, lead_gen) — named independent experts writing outside journals/forums.
- **Podcast Index** (free-key, color) — long-form spoken founder/researcher interviews (never text).
- **Steam / App Store review RSS** (no-key, color) — real-user lived experience + failure modes for products/apps.

## Recommended default posture
Keep the 12-channel core; **enable per topic**: biomed → +europepmc/pubmed/clinicaltrials; CS/ML →
+semantic_scholar; history/humanities → +google_books/gutenberg; finance → +sec_edgar; legal →
+courtlistener; contested "is X true" → +skeptics.SE +opencitations. Add a 2nd–3rd independent web
crawl (Mojeek/Stract) whenever web-index bias is a risk. All are no-key or free-key first.
