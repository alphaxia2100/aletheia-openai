---
name: channel-retrieval
description: Retrieves from a single research channel (web, academic, community, video, books) and returns compressed findings plus normalized source records tagged with index_of_origin and an evidence/lead-gen/color class. Use inside an Aletheia survey when a scoped subagent needs to pull from one channel, or whenever you need source records that feed the provenance audit.
disable-model-invocation: true
---

# channel-retrieval

One subagent, one channel, one tightly-scoped direction. Retrieve, **compress**, and emit normalized records. Do not dump raw text back to the orchestrator (that causes context explosion and the game-of-telephone) — return key findings + structured records.

## The normalized source record

Every source you surface becomes one JSON object appended to `runs/<run>/sources.jsonl` (one per line). This is the shared schema the whole pipeline speaks:

```json
{
  "id": "stable-short-id",
  "url": "https://...",
  "index_of_origin": "brave|openalex|arxiv|semantic_scholar|hackernews|stackexchange|reddit|google_books|gutenberg|youtube|podcast|github|...",
  "title": "...",
  "authors": [{"name": "...", "id": "", "affiliation": "", "country": ""}],
  "published": "ISO-8601 or year",
  "doi": "if a paper",
  "refs": ["doi/id of works this source cites, if known"],
  "derives_from": ["source id(s) this is an echo/summary of, if known"],
  "primary": true,
  "cited_by_count": 0,
  "snippet": "the load-bearing quote or finding, compressed",
  "channel_class": "evidence|lead_gen|color",
  "retrieved_at": "ISO-8601"
}
```

- `index_of_origin` and `channel_class` come from `channels.json`. **Tag by the index, not the vendor** (e.g. a Serper result is `index_of_origin: google_serper`, `index_group: google`).
- `primary`: is this the origin of the claim, or a summary of someone else's? Set `derives_from` when it is an echo. These two fields are what let `provenance-audit` collapse "1 paper echoed by 39 blogs."
- `snippet`: compress to the finding, not the whole page.

## Discipline (non-negotiable)

0. **Use only ENABLED (core) channels.** The active set is the user-scoped `channels.json` overlay on bundled metadata. The safe no-key core is web x2 (Marginalia + DuckDuckGo; Brave/Exa are optional upgrades), OpenAlex + arXiv + Europe PMC (primary), Reddit archive + Hacker News (un-laundered), GitHub/Stack Exchange, and `read.py` (depth). YouTube and X are disabled by default because they can require third-party tools or browser/session access. Every other channel is disabled and hidden — do NOT use it unless the user enables it (`python3 "$AL/channel-retrieval/scripts/channels.py" enable <name>`), e.g. YouTube/X after explicit consent, or Google Books/Gutenberg for history. The overlay can change only enabled names; an unsafe or malformed overlay fails closed to zero enabled channels, never back to network access.

**Browser sessions are a two-part capability.** Plain `read.py` and `reddit.py` never open or use
an authenticated browser. `--browser` requests it, but the host must also grant a matching
`ALETHEIA_BROWSER_CAPABILITY` domain (for example `reddit.com`). A Jina stub, paywall, or failed
archive lookup is not authorization; an environment gate is defense-in-depth, not an OS sandbox.
1. **Tag every record** with `index_of_origin` + `channel_class`. Untagged records break the provenance audit.
2. **Respect the class.** `evidence` is citable; `lead_gen` (HN, Reddit, Perplexity) is for *finding* primary sources — cite the linked primary, not the aggregator; `color` (X, YouTube, podcasts) is never cited as fact.
3. **Independence guard.** Do not fill a survey with channels that share an `index_group` — that is fake diversity. Use at most ONE Google-index channel (Serper), and keep it precisely to *see* the SEO/mainstream bias.
4. **Compress.** Findings + records, never raw dumps.
5. **Re-fetch for reading.** Discovery snippets are filtered by the search vendor. When a source matters, re-fetch the actual page (via the `fetch` MCP server or the extraction layer) so your reading isn't a vendor summary of a summary.

## Depth: read the full thing (don't stop at search)

Search finds pointers; research reads the sources. Emulate the depth a careful human goes to — after reranking, **read the top sources in full** before they inform synthesis, and cite the primary you actually read, not the snippet:

- **Any URL or PDF: `scripts/read.py`** — Jina Reader renders pages/PDFs to markdown (no key). A stub (JS-gated / login / soft-paywall) is flagged honestly; it does **not** open Chrome. Only an explicit `--browser` plus a matching host capability uses opencli's authenticated Browser Bridge. Output shows the method used. `python3 "$AL/channel-retrieval/scripts/read.py" --from-sources sources.jsonl --top-k 8`.
- **Papers**: `read.py` on the PDF/abs URL; or Europe PMC `fullTextXML` / Unpaywall -> OA PDF.
- **YouTube: `scripts/youtube.py`** — captions via `youtube-transcript-api`, `yt-dlp + faster-whisper` fallback; writes the FULL transcript to a file. Class = color.
- **Reddit threads (OP + comments): `python3 "$AL/channel-retrieval/scripts/reddit.py" --thread <url|id>`** — reads the archive path by default. Add `--browser` only with a caller authorization and `ALETHEIA_BROWSER_CAPABILITY=reddit.com`; it then falls back to PullPush. This is the un-laundered layer read in full — don't stop at titles. Plain `read.py` treats Reddit as an ordinary Jina read unless it too receives `--browser`.

Depth beats breadth: a handful of sources read in full and reasoned through beats a hundred skimmed snippets (form over weight). This is the DOK-1-2 gathering done thoroughly so the user can do DOK 3-4.

## Channels

Full per-channel playbooks (endpoints, auth, rate limits, optional-MCP-or-raw-API, class) are in [reference.md](reference.md). Channel metadata is in [channels.json](channels.json). The portable runtime ships no third-party MCP configuration; add reviewed harness-owned MCPs separately. Below is the default web channel.

### Web — Brave (independent index)

Brave is the one at-scale independent Western web index with a public API — the baseline "real web, not just Google" channel.

- **Bundled client**: `scripts/brave.py`; needs `BRAVE_API_KEY` from the user-scoped configuration.
- **Optional MCP**: configure a reviewed `brave-search` equivalent in the harness; repository MCP files are intentionally outside the portable closure.
- **Raw endpoint** (through a reviewed harness HTTP client if needed): `GET https://api.search.brave.com/res/v1/web/search?q=<q>&count=10` with header `X-Subscription-Token: <BRAVE_API_KEY>`.
- Tag results `index_of_origin: brave`, `channel_class: evidence` (a search hit is a pointer — set `primary:false` and re-fetch the target before citing).
- Prefer primary targets (official docs, standards bodies, papers, gov/edu). Down-weight affiliate/listicle/"best X 2026" domains — that pattern is the SEO layer you are trying to de-emphasize.

If `BRAVE_API_KEY` is absent, fall back to the `fetch` server against primary sites you already know, plus the no-key channels in `reference.md` (arXiv, OpenAlex, HN, Stack Exchange, Gutendex, Google Books).
