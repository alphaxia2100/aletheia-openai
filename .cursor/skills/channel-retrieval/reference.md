# Channel reference (2026)

Per-channel playbooks: raw endpoint, auth, rate limit, epistemic class, and how to reach it (bundled no-install client / separately reviewed MCP). Channel metadata lives in `channels.json`. Repository MCP examples are not part of the portable runtime and must not be assumed installed.

**Reading the class column:** `evidence` = citable · `lead_gen` = use to find the primary, cite the primary · `color` = never cite as fact.

**Global rule — decouple searcher from index:** never count two channels sharing an `index_group` as independent corroboration (see the fake-diversity note under Web). Re-fetch a source's real page before citing; discovery snippets are vendor-filtered.

---

## Web search + extraction

### Brave — `index_of_origin: brave` · class evidence · own independent index
- Raw: `GET https://api.search.brave.com/res/v1/web/search?q=<q>&count=10`, header `X-Subscription-Token: $BRAVE_API_KEY`.
- Optional MCP: configure a reviewed `brave-search` equivalent in the host if needed. Auth: free tier ~$5 credit/mo. The bundled `brave.py` client is the portable path.

### Exa — `index_of_origin: exa` · class evidence · neural/embedding index (different paradigm)
- MCP: `https://mcp.exa.ai/mcp` (`EXA_API_KEY`). Paid (~$7/1k). Strongest anti-monoculture pick alongside Brave: surfaces documents keyword engines miss.

### Perplexity Sonar — `index_of_origin: perplexity` · class lead_gen · own hybrid index
- Returns cited answers, not raw links → good for a second opinion + disagreement signal; follow the citations to primaries. MCP: `@perplexity-ai/mcp-server` (`PERPLEXITY_API_KEY`, paid).

### Linkup — `index_of_origin: linkup` · class evidence · licensed-publisher index
- Different provenance (pays publishers; EU path); leans primary/premium. MCP `linkup-mcp-server` (`LINKUP_API_KEY`, paid).

### Serper (the ONE Google window) — `index_of_origin: google_serper` · index_group `google` · class lead_gen
- Raw: `POST https://google.serper.dev/search` body `{"q":"..."}`, header `X-API-KEY: $SERPER_API_KEY`. Free 2,500 queries.
- Keep exactly one Google-index channel, precisely to *see* the SEO/mainstream bias. **Do NOT also enable SerpAPI or Google PSE — same index = fake diversity.**

### DuckDuckGo (no-key fallback) — `index_of_origin: duckduckgo` · index_group `bing` · class lead_gen
- Client: `scripts/web_ddg.py` (HTML scrape, no key). A no-key general web search for when `BRAVE_API_KEY` is absent. **Bing-derived → NOT independent** (same `index_group` as Bing/DuckDuckGo-style resellers); provenance collapses it accordingly. Brittle; may rate-limit.

### Marginalia (no-key, INDEPENDENT) — `index_of_origin: marginalia` · class lead_gen
- Client: `scripts/web_marginalia.py` (HTML scrape of `old-search.marginalia.nu`, no key). A genuinely independent "small-web" index — the best no-key way to add real index diversity next to Brave, and it surfaces primary/personal sources big engines bury. Its JSON API needs a free key; the HTML path is brittle.

### Extraction (decouple fetch from search)
- **Firecrawl** — `https://mcp.firecrawl.dev` (`FIRECRAWL_API_KEY`); robust crawl/scrape/extract to clean markdown/JSON.
- **Jina Reader** — `GET https://r.jina.ai/<url>` -> markdown (keyless at low rate; `JINA_API_KEY` for volume). Cheapest bulk URL->markdown.
- **fetch MCP server** — the default; fetches any URL/REST endpoint. Operationalizes every raw endpoint on this page.

### Retired / skip
- **Bing Search API** — retired Aug 11 2025 (HTTP 410). Do not wire.

---

## Academic (the independence backbone)

### OpenAlex — `index_of_origin: openalex` · class evidence · full citation graph + author/institution/country
- Client: `scripts/openalex.py`. Raw: `GET https://api.openalex.org/works?search=<q>&per_page=25&api_key=$OPENALEX_API_KEY`.
- **2026: a free API key is now required** (old `mailto` polite pool deprecated); $1/day free tier. This is the backbone for independence scoring — `referenced_works`, `cited_by_count`, and authorships with author/institution/country IDs let you compute "N independent vs. 1 echoed."
- Scale: download the free CC0 snapshot for heavy graph traversal instead of the metered API.

### Semantic Scholar (S2AG) — `index_of_origin: semantic_scholar` · class evidence · citation *contexts* + influential-citation flag
- Raw: `GET https://api.semanticscholar.org/graph/v1/paper/search?query=<q>&fields=title,authors,externalIds,citationCount,influentialCitationCount,references,citations`. Optional `x-api-key: $SEMANTIC_SCHOLAR_API_KEY`.
- Best complement to OpenAlex: `isInfluential` + citation `contexts` separate load-bearing citations from perfunctory ones.

### arXiv — `index_of_origin: arxiv` · class evidence · preprints (not peer-reviewed)
- Client: `scripts/arxiv.py`. Raw: `https://export.arxiv.org/api/query?search_query=all:<q>` (Atom XML). No key; <=1 req/3s. Freshest CS/ML; no citation graph (judge independence elsewhere).

### Europe PMC — `index_of_origin: europepmc` · class evidence · free biomedical citation graph + OA full text
- Raw: search `https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=<q>&format=json`; citations `/{source}/{id}/citations`; refs `/references`; full text `/{PMCID}/fullTextXML`. No key.

### Crossref — `index_of_origin: crossref` · class evidence · DOI/identity + funder/license
- Raw: `https://api.crossref.org/works?query=<q>&mailto=$OPENALEX_MAILTO`. Use to de-dup and resolve identity across channels; incoming citations not in the free API.

### PubMed / E-utilities — `index_of_origin: pubmed` · class evidence · biomedical + MeSH
- `esearch`/`efetch` over `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`. 3 req/s (10 with `NCBI_API_KEY`). Defer citations to Europe PMC/OpenAlex.

### Unpaywall — `index_of_origin: unpaywall` · class evidence · OA full-text resolver
- `https://api.unpaywall.org/v2/{DOI}?email=$OPENALEX_MAILTO`. DOI -> legal OA PDF. The "can I read the primary?" step behind any DOI.

### scite — `index_of_origin: scite` · class evidence · support / contrast / mention
- MCP `https://api.scite.ai/mcp` (`SCITE_API_TOKEN`, paid). The only source that classifies each citation as supporting/contrasting/mentioning — the literal echo-vs-independent-support discriminator + disagreement surfacer.

### Dead
- **Papers With Code** — shut down by Meta (Jul 2025); API gone. Archival dump only.

---

## Community / social

### Hacker News — `index_of_origin: hackernews` · class lead_gen
- Client: `scripts/hn.py`. Raw: search `https://hn.algolia.com/api/v1/search?query=<q>&tags=story` (no key, ~1000 req/min); items `https://hacker-news.firebaseio.com/v0/item/<id>.json`. Comments link to primaries and name real practitioners — cite the linked primary; use HN for expert contrarian color.

### Stack Exchange / Stack Overflow — `index_of_origin: stackexchange` · class evidence
- Client: `scripts/stackexchange.py`. Raw: `https://api.stackexchange.com/2.3/search/advanced?q=<q>&site=stackoverflow&order=desc&sort=relevance` (gzip'd; keyless 300/day, `STACKEXCHANGE_KEY` -> 10000/day). Structured, voted, accepted answers → consensus AND disagreement visible.

### Discourse official project forums — `index_of_origin: discourse` · class evidence (near-primary)
- Per instance: `GET https://<forum>/search.json?q=<q>` (operators: `#category @user before: after: tags: status:solved`), threads `/t/{id}.json`. Anonymous read often works; heavier reads use per-forum `Api-Key`+`Api-Username`. Maintainers/core users speaking on their own project's forum ≈ primary. Curate an allowlist per field.

### Reddit — `index_of_origin: reddit` · class lead_gen
- **Bundled client: `scripts/reddit.py`** — **search is relevance-first**: web index scoped to reddit.com (`site:reddit.com` via Brave/DDG) -> **PullPush** -> **Arctic Shift**. Reddit's *own* search ranks by recency/engagement (viral noise); a web index ranks by relevance, so discovery stays on-topic. Winning backend is relevance-filtered. Search: `reddit.py "q" [--subreddit s]`. **Full thread (OP + comments): `reddit.py --thread <url|id>`** uses PullPush by default. Add `--browser` only after explicit authorization to use agent-reach/opencli's authenticated reader (then PullPush remains the fallback).
- Live (compliant, higher fidelity): official Data API via PRAW, OAuth app (`REDDIT_CLIENT_ID/SECRET/USER_AGENT`), free non-commercial, 100 QPM. MCP: `reddit` (PRAW-based). Use when you need current vote counts / live threads.
- Great for lived experience and finding leads; noisy/astroturf-prone. Cite specific technical threads only; never aggregate sentiment as fact.

### X / Twitter — `index_of_origin: x` · class color ONLY · OPT-IN
- **Bundled client: `scripts/x.py`** — wraps agent-reach's `twitter` CLI (browser-session auth, no paid API) into normalized records. One-time login: log into x.com in Chrome, then `agent-reach configure --from-browser chrome`, verify `twitter status`. Enable `x` first, and require a host-scoped grant for every run: `ALETHEIA_BROWSER_CAPABILITY=x.com python3 "$AL/channel-retrieval/scripts/x.py" "topic" --limit 15 [--top] [--from user] [--since YYYY-MM-DD]`.
- Paid alternatives (no login): GetXAPI ~$0.05/1k, twitterapi.io ~$0.15/1k, but no paid X adapter is bundled in this portable runtime. Configure a reviewed external adapter separately. ToS-gray. **Color only**: what people react to, never cite as evidence.

### LinkedIn — SKIP
- No compliant content API for this; low signal. Excluded on purpose.

### GitHub — `index_of_origin: github` · class evidence (code/primary)
- `https://api.github.com/search/repositories?q=<q>&sort=stars` (60 req/hr unauth; `GITHUB_TOKEN` -> 5000). Used in entity resolution; also a real primary channel for tooling claims.

---

## Video / audio (see Milestone 5 for the transcript fallback chain)

### YouTube — `index_of_origin: youtube` · class color
- **Bundled no-key client: `scripts/youtube.py`** (residential machine): captions via `youtube-transcript-api` (sidesteps the 2026 yt-dlp PO-token gate), `yt-dlp` search + audio, `faster-whisper` fallback (`--whisper`). Writes the full transcript to a file.
- **YouTube Data API v3 cannot return transcripts** for videos you don't own; use it for metadata/search only (`YOUTUBE_API_KEY`). On cloud/datacenter IPs, prefer **Supadata** (managed, official MCP, whisper built in) since datacenter IPs are blocked. Treat transcript content as color; cite claims only after verifying the underlying source.

### Podcasts — `index_of_origin: podcast` · class color
- **Taddy** GraphQL `api.taddy.org` (`TADDY_USER_ID`/`TADDY_API_KEY`, free 500 req/mo) — generates transcripts when absent. Fallback: RSS `<enclosure>` audio -> whisper (podcast audio is openly downloadable → low legal risk).

---

## Books (legally-defensible only)

### Google Books — `index_of_origin: google_books` · class evidence
- Client: `scripts/googlebooks.py`. Raw: `https://www.googleapis.com/books/v1/volumes?q=<q>&key=$GOOGLE_BOOKS_API_KEY`. Court-blessed snippet search across a huge corpus; metadata noisy (verify). Do not charge fees for a Books-API app (ToS).

### Open Library / Internet Archive — `index_of_origin: openlibrary` / `internet_archive` · class lead_gen/evidence
- Open Library: `https://openlibrary.org/search.json?q=<q>`; Search-Inside for scanned-book snippets. Internet Archive: advanced search + `https://archive.org/metadata/{id}`; **scholar.archive.org** for 25M+ OA papers. Metadata + full-text *search* + public-domain downloads only.
- **Do NOT automate borrowing / Controlled Digital Lending** (*Hachette v. Internet Archive*, 2d Cir. 2024 — not fair use).

### Project Gutenberg (Gutendex) — `index_of_origin: gutenberg` · class evidence
- Client: `scripts/gutendex.py`. `https://gutendex.com/books?search=<q>`. Public-domain FULL TEXT, cleanest legal posture. US-PD scope caveat.

### Standard Ebooks — `index_of_origin: standard_ebooks` · class evidence
- OPDS feed `https://standardebooks.org/feeds/opds`. Curated PD + CC0, best formatting. Small catalog → complement to Gutenberg.

### Do NOT wire
- **Anna's Archive / LibGen / Z-Library** — shadow libraries; active 2026 judgments (LibGen $30M default judgment; Anna's Archive Jan-2026 default judgment; Z-Library DOJ criminal case). Statutory damages up to $150k/work + contributory-infringement exposure. Excluded on purpose.

---

## Adapters — swappable backends (via agent-reach)

Some channels can route through **agent-reach** (browser-session access to walled gardens) only as
an explicitly authorized capability; safe default paths remain no-session native clients. This is the
plugin/adapter design: **when a backend breaks, swap it in one place** and the client keeps working.

- **Adapter module:** `scripts/_agentreach.py` — locates agent-reach's upstream CLIs (`twitter`, `opencli`/`rdt`, ...) and maps their output into Aletheia's record schema. All agent-reach-backed parsing lives here; fix a broken CLI/parser once, here.
- **The master key — a real logged-in browser.** How agent-reach gets past walls: opencli drives your authenticated Chrome (daemon + extension = "Browser Bridge"), so it executes JS and carries your cookies. That defeats the three things a plain HTTP fetch (Jina) can't: anonymous 403 anti-bot, login/soft-paywalls, and JS-rendered pages. It is explicit and never an automatic fallback:
  - `browser_extract(url)` → render any page in real Chrome → markdown, only through `read.py --browser` **and** a matching `ALETHEIA_BROWSER_CAPABILITY` host grant.
  - `reddit_read(id)` → full thread (OP + comments), only through `reddit.py --thread … --browser` or `read.py --browser` on a Reddit URL, again with `reddit.com` granted.
  - opencli also ships 163 per-site adapters (amazon, bloomberg, google-scholar, arxiv, ...) and a generic `opencli browser` surface — reachable the same way if you add more channels.
  - **Honest limits:** the browser is slow (~15-35s/page) and needs the opencli daemon + Chrome running; hard captcha/interactive-Cloudflare and true no-login paywalls still lose; and this is ToS-gray (fine for a personal project, don't ship it commercially). The scrubbed child environment reduces accidental secret inheritance but does not sandbox an untrusted third-party CLI running as the same user.
- **X** (`x.py`) → agent-reach `twitter` CLI (live when `twitter status` = `ok: true`). Optional paid fallback: GetXAPI / twitterapi.io.
- **Reddit** (`reddit.py`) → **search** order: web-relevance (`site:reddit.com` via Brave/DDG) → **PullPush** → **Arctic Shift**. Add `--browser` to make agent-reach `opencli` an explicit final fallback. **Reading** (`--thread`) uses PullPush by default; `--browser` opts into opencli's authenticated reader first. Web-relevance beats Reddit's native search, so discovery stays on-topic with or without opencli.
- Native channels (`youtube.py`, `github.py`, `read.py`) already cover what agent-reach's YouTube/GitHub/web backends do; agent-reach is an alternate, not a requirement.

**Availability is machine-specific.** Treat agent-reach/browser adapters as absent until the current
host's explicit capability grant and `doctor.py` check show otherwise; do not copy browser profiles,
cookies, or adapter state between machines.

**To swap a broken backend:** edit the command/parser in `_agentreach.py`, or reorder the backend list in the client's `search()`. Ordered fallback means a dead backend simply drops to the next — nothing else changes. This is deliberately how you keep the walled-garden channels alive as tools come and go.

## Independence groups (fake-diversity guard)

Counting two of these as independent = the fake-diversity trap; `provenance_graph.py` collapses them by `index_group`:
- `google` = Serper + SerpAPI + Google PSE (one index).
- `internet_archive` = Open Library + Internet Archive.
Genuinely independent web indexes: `brave`, `exa_neural`, `perplexity`, `linkup`. Genuinely independent academic sources: `openalex`, `semantic_scholar`, `arxiv`, `europepmc`, `crossref` (identity), `scite` (intent).
