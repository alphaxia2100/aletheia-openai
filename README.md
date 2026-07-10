# Aletheia

*alḗtheia* — "unconcealment, disclosure." A research **surveyor**: it gives you an accurate, bird's-eye picture of a field or task, and it is built to resist the three failure modes that wreck ordinary research agents:

1. **Anchoring / consensus-lock** — forming one hypothesis (usually the consensus one) and conditioning every downstream query, source-selection, and synthesis on it.
2. **A narrow source diet** — living on one web index whose SEO/editorial bias dominates ranking.
3. **Bias sources** — treating "40 blogs echoing 1 paper" as 40 independent confirmations.

Aletheia is delivered as a **portable Skill + MCP suite** — no standalone app. It runs in Cursor, Claude Code, Codex, and any harness that reads `SKILL.md` + MCP configs.

> What makes this better than a bare LLM: it **refuses to anchor** (holds 4-6 competing framings and commits to none), pulls **current, diverse, real sources** the model can't reach, **reads them in full**, **judges whether support is independent or just one origin echoed** (by reading what's cited — a judgment, not a graph), **attacks its own leading conclusion** before believing it, and answers with **every claim tied to a source**, disagreement kept visible.

## The one architectural rule

The pro-swarm (Anthropic, +90.2% on breadth-first) vs. anti-swarm (Cognition, "Don't Build Multi-Agents") debate is not a contradiction — it's a **decomposition rule**, and the Berkeley MAST failure taxonomy (37% inter-agent misalignment, 21% verification failures) says where the danger is:

- **Parallelize the independent parts** — heterogeneous channels x competing framings (fan-out subagents, each a *different, tightly-scoped direction*).
- **Single-thread the interdependent parts** — hypothesis arbitration, provenance reconciliation, synthesis (one writer, continuous context).
- **The adversary is read-only and procedural** — an "intelligence contributor," not a parallel writer.

```mermaid
flowchart TD
    scope["survey-scope: 4-6 competing framings (no single hypothesis)"] --> fanout
    subgraph fanout [Parallel scoped subagents - different directions]
        web["web: Brave/Exa"]
        acad["academic: OpenAlex/arXiv/S2"]
        comm["community: HN/StackEx/Reddit"]
        media["video/books: Supadata/GoogleBooks"]
    end
    fanout --> compress["compress to findings + source records"]
    compress --> prov["provenance-audit: claims<->sources graph, independence scoring"]
    prov --> adv["adversary: hunt disconfirmation, count sources not citations"]
    adv --> synth["synthesis: single-threaded writer, preserve disagreement"]
    synth --> judge["defensibility-judge: 4-part rubric"]
    judge --> atlas["Consilient Atlas: accrete markdown so surveys compound"]
```

## Skills

> **Current skill: `aletheia-research` 0.4.3.** The flagship is the deep, multi-perspective tree
> surveyor — built off **deep-aletheia 0.2** (which won a blind LLM-judge on completeness, source
> variety, and grounding), keeping its good parts and adding a decisive-source hunt, chase-the-primary
> discipline, wider source variety, and a thoroughness dial. See `docs/aletheia-0.3-design.md` and the
> bake-off in `docs/evals/`. Invoke: *"use the aletheia-research skill to survey \<topic\> (thoroughness: auto)."*

| Skill | Role |
|-------|------|
| **`aletheia-research` 0.4.3** | **Current** deep surveyor (multi-perspective tree). Defaults to unbounded convergence; `quick\|standard\|deep\|exhaustive` bound it and `max` expands it. |
| `deep-aletheia` 0.2 | *Frozen — direct ancestor of aletheia-research 0.3; eval baseline.* |
| `surveyor` 0.1 | *Retired 2026-07-08 — eval baseline (single-agent).* |
| `aletheia` v1.0 | *Retired — original single-agent loop; superseded by `aletheia-research`.* |
| `survey-scope` | Turns a topic into a **portfolio of competing framings** + scoped subagent specs. Resolves entities *before* searching. |
| `channel-retrieval` | Per-channel playbooks. Every result is tagged with `index_of_origin` + an **evidence / lead-gen / color** class. |
| `iterative-deepening` | Breadth x depth search loop with reflection (search -> learn -> recurse into gaps). Turns flat fan-out into real research. |
| `provenance-audit` | Judge (by reading) whether support is independent or one origin echoed — not a graph. |
| `adversary` | Attack your own leading conclusion: hunt disconfirmation before believing it. |
| `synthesis` | Single-threaded writer; preserves disagreement instead of laundering it. |
| `defensibility-judge` | 4-part rubric: is a belief actually defensible? |
| `depth-channels` | YouTube + podcast transcripts (paid/toggle) as corroborate-before-citing color. |
| `consilient-atlas` | Accretes each survey into a growing knowledge base so surveys compound. |

Suite utilities live in `channel-retrieval/scripts/` (global after install): `doctor.py` (channel health-probe + ordered failover), `channels.py` (enable/disable the core), the no-install channel clients, `rerank.py`, and `read.py`.

## Core connectors (enabled) vs. the rest (hidden)

This is a personal research project, so **the core runs with ZERO API keys.** Only a tight core is enabled and visible to the agent; every other channel is disabled and hidden but one command away. For X and other walled gardens, use **agent-reach** (free, browser-session access) rather than a paid API — Aletheia adds the epistemic layer on top.

| Role | Channel(s) | Key |
|------|-----------|-----|
| Web search x2 (independent) | **Marginalia** (independent) + **DuckDuckGo** | none — add free **Brave** key or paid **Exa** to upgrade |
| Latest video | **YouTube** — `youtube.py --latest` (yt-dlp `ytsearchdate` discovery) + `youtube-transcript-api` | none (pip install) |
| Social pulse (color) | **X** via **agent-reach** (browser session) | none (paid GetXAPI/twitterapi optional) |
| Primary / independence backbone | **OpenAlex** + **arXiv** + **Europe PMC** | none — add free OpenAlex key for volume |
| History / books | **Wikipedia** + **Open Library** | none — enable Google Books when its keyless quota is healthy |
| Un-laundered layer | **Reddit** (PullPush) + **Hacker News** | none |
| Depth | **read.py** (Jina: pages + PDFs) | none |

Manage the core:
```bash
AL=~/.cursor/skills                                          # Aletheia's global home
python3 "$AL/channel-retrieval/scripts/channels.py" list        # the enabled core
python3 "$AL/channel-retrieval/scripts/channels.py" list --all  # every channel, [on]/[off]
python3 "$AL/channel-retrieval/scripts/channels.py" enable stackexchange       # for software
python3 "$AL/channel-retrieval/scripts/channels.py" enable google_books gutenberg  # for history
python3 "$AL/channel-retrieval/scripts/channels.py" reset       # back to the core
```
The agent uses only enabled channels (`channel-retrieval` enforces this). Hidden channels stay ready — pick per topic rather than firing all of them (more channels != more rigor).

## Install

**Cursor** (this repo): skills live in `.cursor/skills/` and load automatically. MCP servers load from `.cursor/mcp.json`.

**Use it in ANY chat (global install).** Make the skills personal so Cursor, Claude Code, and Codex can invoke them outside this repo:
```bash
bash scripts/install.sh          # full suite to Cursor/Claude; validated flagship to Codex
# bash scripts/install.sh --copy # copy Cursor/Claude skills; Codex stays symlinked for sibling runtime
# bash scripts/install.sh --codex-only # update Codex while preserving a separate Cursor/Claude version
```
Then invoke *"use the aletheia-research skill to survey \<topic\>."* In Codex, `$aletheia-research` is also available after starting a new session. The scripts self-locate this repo via realpath, so `.env`, channel settings, and the atlas work from anywhere. Codex resolves through `${CODEX_HOME:-$HOME/.codex}`; utilities also run by absolute path, e.g. `python3 ~/.cursor/skills/channel-retrieval/scripts/doctor.py`. (One source of truth: edits here show up in every client.)

**Keys**: `cp .env.example .env` and fill in only what you need. The free core needs almost nothing (the `fetch` MCP server + no-key REST APIs cover it). See `.cursor/mcp.reference.md` for the full connector catalog and which are free vs. paid. Run `python3 ~/.cursor/skills/channel-retrieval/scripts/doctor.py` any time to see which channels are live (~15 work with no API key, including Reddit, two no-key web-search indexes, Wikipedia/Open Library, no-key full-page/PDF reading via `read.py`, and YouTube transcripts via `youtube.py` after `pip install --user -r requirements-optional.txt`).

## Run a survey

Invoke the orchestrator skill (by name) with a topic, e.g. *"survey the state of X."* It will:
1. propose a portfolio of framings and confirm scope with you,
2. fan out scoped retrieval across independent channels,
3. audit provenance/independence, run the adversary,
4. synthesize (disagreement preserved), score defensibility, and offer to append to the Atlas.

## The discipline is core; these scripts are just conveniences

The **hypothesis portfolio** (anti-anchoring), **judging source independence by reading**, and the **adversary** pass are core steps — they live as agent discipline in the `aletheia` loop, not as machinery. The scripts below are optional add-ons:
- `provenance-audit/scripts/provenance_graph.py` — *computes* independence when a source set is too big to judge by hand (normally you judge it while reading — see the `provenance-audit` skill).
- `defensibility-judge/scripts/rubric.py` — a 4-point check before committing to a spiky claim.

All scripts are pure Python 3.9+ stdlib — no install required, covered by `tests/`.

## Naming

This is a Skill/MCP **bundle**, not an npm/PyPI package. If you ever publish connectors, avoid the name `aletheia-mcp` — an unrelated OpenAlex citation-graph MCP already uses it.

## Ethics & legality

The books channel is restricted to legally-defensible sources (Google Books snippets, Open Library / Internet Archive metadata + public-domain full text, Project Gutenberg, Standard Ebooks). Aletheia does **not** wire shadow libraries (Anna's Archive / LibGen / Z-Library) and does **not** automate Internet Archive borrowing. See `.cursor/skills/channel-retrieval/reference.md`.

## Status

Built in milestones (see `.cursor/plans/` for the source plan). Each skill is independently usable.
