# Roadmap & durability

> Historical architecture note. The current evidence-backed experiment sequence and its qualifications
> are in the [2026-07-27 agent-output quality survey](research/2026-07-27-agent-output-quality/README.md).
> `prod` remains skills-first; claim/evidence hardening, retrieval/reranking, revision-capable question
> graphs, and stop cards are isolated experiments rather than established upgrades.

Aletheia is intentionally **skills-only** today: portable `SKILL.md` bundles + MCP configs, orchestrated by the harness (Cursor / Claude Code) running "tools in a loop." That is the right first architecture — the independent-practitioner and academic consensus (Willison's "tools in a loop," Ronacher on avoiding heavy agent-SDK abstractions, the Agentless result) says: write the loop, add a framework only when a failure mode demands it.

## When to graduate to LangGraph / a standalone app

Add durable infrastructure only when this specific pain appears:

- **Long runs that must survive a crash.** When a full survey fans out over dozens of sources for 10+ minutes and a failure at step 9 of 12 forces a full restart, you need **checkpointing / durable resume**. That is LangGraph's real justification (its checkpointer snapshots state per super-step; a failed node resumes from the last checkpoint) — the thing Anthropic reported hand-building.
- **Human-in-the-loop steering mid-run.** Pausing for the user to approve a framing or redirect retrieval, then resuming, is LangGraph `interrupt()` + `Command`.
- **Cross-session memory beyond the Atlas.** A queryable store of claims/provenance across many surveys.

Until then, LangGraph is complexity you'd pay for without earning. A single-shot survey does not need it.

## Migration path (when the time comes)

The epistemic core is already framework-agnostic Python (`provenance_graph.py`, `dedupe.py`, `rubric.py`, `entity_resolve.py`, the channel clients) and the channels are MCP servers. To graduate:
1. Wrap the pipeline stages (scope → fan-out → provenance → adversary → synthesis → judge) as LangGraph nodes; the scripts stay as-is (call them from nodes).
2. Add a `PostgresSaver` checkpointer; keep subagent context isolation (retrieval parallel, synthesis single-threaded — unchanged).
3. Keep the skills as the portable, in-harness interface; the standalone runtime becomes an *additional* entry point, not a replacement.

Nothing in the current design has to be thrown away to make that jump — that is the reason to stay skills-first now.

## Connector maturity

- **Free core, wired via the `fetch` server + no-install clients:** Brave, arXiv, OpenAlex, Semantic Scholar, HN, Stack Exchange, Europe PMC, Crossref, Gutendex, Google Books, GitHub.
- **Toggle-on with keys (documented in `.cursor/mcp.reference.md`):** Exa, Firecrawl, Perplexity, Linkup, Serper (one Google window), Supadata, Taddy, scite, Apify.
- **Deliberately excluded:** Bing (retired), LinkedIn (no compliant API), shadow libraries (legal), Internet Archive borrowing (legal).

## Heterogeneous models

The single highest-leverage upgrade that needs no new infra: run **synthesis and the adversary on different base models** (dispatch the adversary as a subagent on another model), and have `defensibility-judge` compare them as an audit, not a vote. Correlated errors are the enemy; heterogeneity is the cure.
