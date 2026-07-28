# No-install channel clients

Pure-stdlib clients that turn a query into **normalized source records** (JSONL) — the schema in `../SKILL.md`. No dependencies; run with system `python3`. They make the free channels usable immediately, without any MCP server.

```bash
AL="${CODEX_HOME:-$HOME/.codex}/skills/.aletheia-runtime/skills"
cd "$AL/channel-retrieval/scripts"              # copied runtime location (also holds doctor.py + channels.py)
python3 arxiv.py "your query" --limit 8            > /tmp/a.jsonl
python3 openalex.py "your query" --limit 8         >> /tmp/a.jsonl   # OPENALEX_API_KEY recommended (2026)
python3 hn.py "your query"                          >> /tmp/a.jsonl
python3 stackexchange.py "your query"              >> /tmp/a.jsonl   # SE_SITE env to change site
python3 openlibrary.py "your query"                >> /tmp/a.jsonl
python3 gutendex.py "your query"                   >> /tmp/a.jsonl
python3 googlebooks.py "your query"                >> /tmp/a.jsonl   # GOOGLE_BOOKS_API_KEY recommended

# then feed straight into the provenance audit:
python3 ../../provenance-audit/scripts/provenance_graph.py audit --sources /tmp/a.jsonl --claims claims.json
```

Each record is tagged with `index_of_origin` and an auto-filled `channel_class`
(evidence / lead_gen / color, from `../channels.json`). Every client is
best-effort: on network/quota errors it prints a message to stderr and exits
non-zero without emitting partial garbage.

| Client | index_of_origin | class | key |
|--------|-----------------|-------|-----|
| `brave.py` | brave | evidence | BRAVE_API_KEY (free, loaded only from user config `.env`) |
| `x.py` | x | color | opt-in agent-reach browser session + `ALETHEIA_BROWSER_CAPABILITY=x.com` |
| `arxiv.py` | arxiv | evidence | none |
| `openalex.py` | openalex | evidence | OPENALEX_API_KEY (free, 2026) |
| `semanticscholar.py` | semantic_scholar | evidence | none (429-prone; SEMANTIC_SCHOLAR_API_KEY optional) |
| `europepmc.py` | europepmc | evidence | none |
| `crossref.py` | crossref | evidence | none (OPENALEX_MAILTO optional) |
| `hn.py` | hackernews | lead_gen | none |
| `stackexchange.py` | stackexchange | evidence | STACKEXCHANGE_KEY (optional) |
| `reddit.py` | reddit | lead_gen | none (search: `site:reddit.com` via Brave/DDG -> PullPush -> Arctic; browser only with explicit grant) |
| `github.py` | github | evidence | none (GITHUB_TOKEN optional) |
| `wikipedia.py` | wikipedia | lead_gen | none |
| `openlibrary.py` | openlibrary | lead_gen | none |
| `youtube.py` | youtube | color | opt-in; install reviewed dependencies in an isolated venv |
| `web_ddg.py` | duckduckgo | lead_gen | none (Bing-derived, brittle HTML scrape) |
| `web_marginalia.py` | marginalia | lead_gen | none (independent index, brittle HTML scrape) |
| `gutendex.py` | gutenberg | evidence | none |
| `googlebooks.py` | google_books | evidence | GOOGLE_BOOKS_API_KEY (optional) |

`rerank.py` and `read.py` are not clients — they post-process records:

```bash
# rank by relevance, prune noise, then READ the top sources in full (no key):
python3 rerank.py "your query" --sources /tmp/a.jsonl --top-k 20 > /tmp/ranked.jsonl
python3 read.py --from-sources /tmp/ranked.jsonl --top-k 8 --outdir runs/reads
```

`read.py` uses Jina Reader (r.jina.ai) to turn any URL or PDF (incl. arXiv) into
full markdown with no key — the depth step. `youtube.py` needs optional packages but no API key on a
residential machine; it is disabled until explicitly enabled and runs yt-dlp with an isolated child
environment rather than inherited connector keys/cookies.

`_agentreach.py` is the **adapter** module (not a client): it wraps agent-reach's
CLIs (`twitter`, `opencli`/`rdt`, ...) as swappable backends. `x.py` routes through
it; `reddit.py` uses it only for explicit authorized browser reads while search stays relevance-first
via a web index (`site:reddit.com`). When a walled-garden backend breaks, swap
the command/parser there — see "Adapters" in `../reference.md`.

For channels without a bundled client (Discourse forums, podcasts), use the raw
endpoints in `../reference.md` or configure a separately reviewed, harness-owned MCP.
The portable runtime deliberately includes no third-party MCP configuration.
