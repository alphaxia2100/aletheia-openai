# MCP connector catalog

## Safety default

The shipped `.cursor/mcp.json` intentionally enables **no** third-party MCP servers. An MCP command
can execute a package installation and inherit the host's permissions, so enable one only after
reviewing and pinning its exact version in your own harness configuration. Aletheia's standard-library
channel clients are sufficient for the safe core and do not require an MCP server.

The live `.cursor/mcp.json` intentionally ships no servers. The following are reference options,
not defaults:

- **`fetch`** (`uvx mcp-server-fetch`) — the official reference fetch server. This is the workhorse: with it, the agent can hit **every raw REST API** documented in `skills/channel-retrieval/reference.md` (OpenAlex, Semantic Scholar, HN Algolia, Stack Exchange, Europe PMC, Crossref, Gutendex, Google Books, ...). Most channels therefore need **no dedicated MCP at all**.
- **`brave-search`** — the one at-scale independent Western web index with a public API. Needs `BRAVE_API_KEY`.
- **`arxiv`** — preprint search + PDF retrieval, no key.

Everything below is **opt-in**. Copy the block into a reviewed harness-owned `mcpServers` configuration, add any key to the user-scoped Aletheia configuration, and restart. They are separated out because community MCP package names/entrypoints drift; if one is wrong it should fail in isolation, not break your setup. Each is marked with a verification status.

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

### agent-reach (optional browser/session capability)
Status: third-party, MIT ([Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)). It can reach walled gardens through a logged-in browser, which means it is **not** part of the safe default. Review and pin a specific upstream release in an isolated environment before installing it; do not install GitHub `main` from an agent command. Grant browser/session access only after the caller explicitly requests it for a named purpose. Aletheia's bundled Reddit, YouTube, and page readers work without agent-reach; this adapter widens reach when its extra authority is worth the privacy tradeoff.

Browser-session access is an explicit capability: Aletheia's normal `read.py` and Reddit paths never invoke opencli or use browser cookies automatically. Use their `--browser` flag only after the caller has authorized authenticated-browser access for that specific operation.

### X / Twitter (OPT-IN, color-only) — agent-reach or a reviewed paid API

X is disabled in the safe core. Enable it only after deciding that browser/session or a reviewed paid API is appropriate for the run. Aletheia bridges a configured `twitter` CLI via `channel-retrieval/scripts/x.py` (class=color, never factual evidence). A one-time interactive login normally looks like:
```bash
# 1) log into x.com in Chrome, then:
agent-reach configure --from-browser chrome     # imports your session cookies (also YouTube/XHS)
twitter status                                   # -> ok: true
# then explicitly enable the channel before Aletheia can use it:
python3 .cursor/skills/channel-retrieval/scripts/channels.py enable x
```
(Alternative auth: export TWITTER_AUTH_TOKEN + TWITTER_CT0.) Paid alternatives (no login): **GetXAPI** (~$0.05/1k) via `getxapi-mcp` (`GETXAPI_KEY`), or `twitterapi-io-mcp-server` (`TWITTERAPI_IO_KEY`). X is **color-only** — surface what people react to; never cite as evidence.

agent-reach can also unlock Reddit/Bilibili/XHS/Instagram/etc. the same way. Treat every such integration as an independently reviewed capability, not as a required Aletheia dependency.

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
