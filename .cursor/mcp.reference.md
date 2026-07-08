# MCP connector catalog

The live `.cursor/mcp.json` intentionally ships only three servers that are reliable to load:

- **`fetch`** (`uvx mcp-server-fetch`) — the official reference fetch server. This is the workhorse: with it, the agent can hit **every raw REST API** documented in `skills/channel-retrieval/reference.md` (OpenAlex, Semantic Scholar, HN Algolia, Stack Exchange, Europe PMC, Crossref, Gutendex, Google Books, ...). Most channels therefore need **no dedicated MCP at all**.
- **`brave-search`** — the one at-scale independent Western web index with a public API. Needs `BRAVE_API_KEY`.
- **`arxiv`** — preprint search + PDF retrieval, no key.

Everything below is **opt-in**. Copy the block into `mcp.json`'s `mcpServers`, add the key to `.env`, and restart. They are separated out because community MCP package names/entrypoints drift; if one is wrong it should fail in isolation, not break your setup. Each is marked with a verification status.

Env interpolation uses `${env:VAR}`. If your Cursor build does not interpolate, paste the literal key instead (never commit it).

---

## Design principle: MCP-optional

Every channel in `skills/channel-retrieval/reference.md` lists its raw endpoint, auth, and rate limits. A dedicated MCP is a convenience over the `fetch` server, not a requirement. Prefer the raw API via `fetch` (or the bundled stdlib clients in `skills/channel-retrieval/scripts/`) when a dedicated MCP is unverified.

---

## Academic

### Multi-source paper search (OpenAlex + Semantic Scholar + arXiv + Crossref + PubMed)
Status: community, verify entrypoint before relying.
```json
"paper-search": {
  "command": "uvx",
  "args": ["paper-search-mcp"],
  "env": {
    "OPENALEX_API_KEY": "${env:OPENALEX_API_KEY}",
    "SEMANTIC_SCHOLAR_API_KEY": "${env:SEMANTIC_SCHOLAR_API_KEY}"
  }
}
```
Alternatives seen in the wild: `research-master-mcp` (Rust, 28 sources), `Lyra-s-Expanded-Research-MCP`. Prefer the bundled `scripts/openalex.py` + `scripts/arxiv.py` (no install) if unsure.

### scite (support / contrast / mention citation classification)
Status: official, paid subscription.
```json
"scite": { "url": "https://api.scite.ai/mcp", "env": { "SCITE_API_TOKEN": "${env:SCITE_API_TOKEN}" } }
```

### Consensus (claim-level agreement)
Status: official, OAuth.
```json
"consensus": { "url": "https://mcp.consensus.app/mcp" }
```

---

## Community / social

### Hacker News (Algolia search + Firebase items)
Status: community, thin wrapper over official free APIs.
```json
"hackernews": { "command": "npx", "args": ["-y", "@isteam/hackernews-mcp"] }
```
Or just use `scripts/hn.py` (no install, no key).

### Stack Overflow (official)
Status: official, beta rate-limited (~100 req/day). Falls back to raw Stack Exchange API.
```json
"stackoverflow": { "command": "npx", "args": ["-y", "@stackexchange/stack-mcp"] }
```

### Reddit (PRAW-based, compliant — uses YOUR OAuth app)
Status: community, compliant path (not a scraper).
```json
"reddit": {
  "command": "uvx",
  "args": ["reddit-mcp"],
  "env": {
    "REDDIT_CLIENT_ID": "${env:REDDIT_CLIENT_ID}",
    "REDDIT_CLIENT_SECRET": "${env:REDDIT_CLIENT_SECRET}",
    "REDDIT_USER_AGENT": "${env:REDDIT_USER_AGENT}"
  }
}
```
Historical / cross-sub keyword search (no key): Arctic Shift / PullPush REST via the `fetch` server (see reference.md). Aletheia already ships a no-key Reddit client at `skills/channel-retrieval/scripts/reddit.py` (PullPush -> Arctic Shift failover) — no install needed for search/history.

### agent-reach (RECOMMENDED no-key access layer for walled gardens)
Status: third-party, MIT ([Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)). This is the right division of labor for a personal project: **agent-reach = the free "eyes"** (zero-API-fee read/search of X, Reddit, YouTube, Bilibili, XiaoHongShu, GitHub via the best free CLI/browser-session backend per platform); **Aletheia = the "judgment"** (framing portfolio, provenance/independence, adversary, defensibility) plus the channels agent-reach doesn't cover (academic, books).
```bash
pip install "https://github.com/Panniantong/agent-reach/archive/main.zip"
agent-reach install --env=auto && agent-reach doctor
# then call upstream tools directly, e.g. twitter search "q" -n 20 ; opencli reddit search "q" -f yaml
```
Use agent-reach for **X and any other walled garden** instead of paying for an API. Feed what it returns into Aletheia's pipeline and tag by class (social/video = color; cite the linked primary). Aletheia also ships its own no-key `reddit.py`/`youtube.py`/`read.py` so it works even without agent-reach; agent-reach widens reach (X timelines, XHS, Bilibili) for free.

### X / Twitter (CORE, color-only) — INSTALLED via agent-reach
Installed on this machine: agent-reach in `~/.aletheia-agentreach` (Python 3.12 via uv), `twitter` CLI at `~/.local/bin/twitter`. Aletheia bridges it via `channel-retrieval/scripts/x.py` (emits normalized records, class=color). No paid API. One-time interactive login:
```bash
# 1) log into x.com in Chrome, then:
agent-reach configure --from-browser chrome     # imports your session cookies (also YouTube/XHS)
twitter status                                   # -> ok: true
# then Aletheia can read X:
python3 .cursor/skills/channel-retrieval/scripts/x.py "topic" --limit 15 [--top] [--from user] [--since 2026-01-01]
```
(Alternative auth: export TWITTER_AUTH_TOKEN + TWITTER_CT0.) Paid alternatives (no login): **GetXAPI** (~$0.05/1k) via `getxapi-mcp` (`GETXAPI_KEY`), or `twitterapi-io-mcp-server` (`TWITTERAPI_IO_KEY`). X is **color-only** — surface what people react to; never cite as evidence.

agent-reach also unlocks Reddit/Bilibili/XHS/Instagram/etc. the same way: `agent-reach install --channels=<name>` then browser login. Live no-login channels already active: GitHub (`gh`), web (Jina), RSS, V2EX, Bilibili search.

---

## Web search + extraction (paid, toggle for index diversity)

```json
"exa":        { "url": "https://mcp.exa.ai/mcp",       "env": { "EXA_API_KEY": "${env:EXA_API_KEY}" } },
"perplexity": { "command": "npx", "args": ["-y", "@perplexity-ai/mcp-server"], "env": { "PERPLEXITY_API_KEY": "${env:PERPLEXITY_API_KEY}" } },
"linkup":     { "command": "npx", "args": ["-y", "linkup-mcp-server"],         "env": { "LINKUP_API_KEY": "${env:LINKUP_API_KEY}" } },
"firecrawl":  { "url": "https://mcp.firecrawl.dev",    "env": { "FIRECRAWL_API_KEY": "${env:FIRECRAWL_API_KEY}" } },
"serper":     { "command": "npx", "args": ["-y", "serper-search-mcp"],         "env": { "SERPER_API_KEY": "${env:SERPER_API_KEY}" } }
```
Independence guard: enable **at most one** of `serper` / serpapi / google_pse — they are the same Google index.

---

## Video / audio / books

```json
"supadata": { "url": "https://supadata.ai/mcp", "env": { "SUPADATA_API_KEY": "${env:SUPADATA_API_KEY}" } },
"books":    { "command": "npx", "args": ["-y", "alexandria-mcp"], "env": { "GOOGLE_BOOKS_API_KEY": "${env:GOOGLE_BOOKS_API_KEY}" } }
```
`alexandria-mcp` bundles Gutenberg (full text), Open Library, Internet Archive, Standard Ebooks, Google Books (snippets). Or use `scripts/gutendex.py` + `scripts/googlebooks.py` (no install).

---

## Not included, on purpose

- **Bing Search API** — retired Aug 2025 (HTTP 410). Do not wire.
- **LinkedIn** — no compliant content API; low signal. Skip.
- **Anna's Archive / LibGen / Z-Library** — active 2026 legal judgments. Never wired. See `skills/channel-retrieval/reference.md` for the legally-defensible books stack.
- **Internet Archive borrowing/CDL** — not legal to automate (*Hachette v. Internet Archive*, 2d Cir. 2024). Metadata + full-text search + public-domain downloads only.
