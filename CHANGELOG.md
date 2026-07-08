# Changelog

Two products, versioned independently:
- **aletheia** — v1 judgment-driven surveyor (stable; quick single-agent surveys).
- **deep-aletheia** — recursive, filesystem-coordinated orchestrator-worker research tree
  (in development; deep, high-scrutiny surveys).

Versioning is [SemVer](https://semver.org/). `deep-aletheia` is expected to iterate quickly;
each notable change bumps the minor/patch and is tagged `deep-aletheia-vX.Y.Z`.

---

## deep-aletheia 0.1.0 — unreleased

First cut of the recursive architecture (see `docs/deep-aletheia-design.md`).

- **Filesystem-as-blackboard** (`treestate.py`): every agent node is a directory holding its
  spec, decision log, sources, notes, findings, and a parent↔child Q&A channel. State lives on
  disk, not in context — fixes context overflow, the "telephone" problem, resumability, audit.
- **Budget model** (conserved split + scrutiny-unit floor): equal scrutiny per leaf and equal
  effort per tree level, with hard caps (max depth / children / nodes) to bound fan-out.
- **Topic-aware routing** (`router.py`): executes `channels.json` selection guidance instead of
  leaving it as a comment (fixes off-topic channel firing).
- **Authority/class-aware ranking** (`rank.py`): class-budgeted reads; primaries over content
  farms (fixes lexical-rerank misranking blogs above papers).
- **Leaf investigation pipeline** (`investigate.py`): route → retrieve → dedupe → rank → read →
  extract cited claims, writing artifacts to the node dir.
- **Verification gate** (`verify.py`): per-claim Link-Works / Relevant / Fact-Check.
- **Orchestrator skill** (`deep-aletheia/SKILL.md`): recursive decomposition, parallel read-only
  Task subagents, bottom-up synthesis with top-down clarification.

## aletheia 1.0.0 — 2026-07-08

- Initial: anti-anchoring judgment-driven surveyor + heterogeneous no-key channels
  (Brave, OpenAlex, arXiv, Reddit, Hacker News, YouTube, Stack Exchange, GitHub, books,
  real-browser reads), independence judgment, adversary, defensibility, Consilient Atlas.
- Reddit discovery relevance-fix (`site:reddit.com` via Brave/DDG; opencli for thread reads).
- Fix silent YouTube discovery failure; add `scripts/eval/run_metrics.py`.
