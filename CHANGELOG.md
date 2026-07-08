# Changelog

Two products, versioned independently:
- **aletheia** — v1 judgment-driven surveyor (stable; quick single-agent surveys).
- **deep-aletheia** — recursive, filesystem-coordinated orchestrator-worker research tree
  (in development; deep, high-scrutiny surveys).

Versioning is [SemVer](https://semver.org/). `deep-aletheia` is expected to iterate quickly;
each notable change bumps the minor/patch and is tagged `deep-aletheia-vX.Y.Z`.

---

## deep-aletheia 0.2.0 — unreleased

Reframed from a **static** recursive tree into a **dynamic, question-driven surveyor** — the way
expert survey-methodologists and SOTA deep-research systems actually work. Grounded in fresh,
independent research read in full: **STORM** (Stanford OVAL — multi-perspective question-asking →
outline), **WebWeaver** (SOTA 2025 — dynamic cycle interleaving evidence acquisition with outline
optimization; the failure mode it names, *"static pipelines that decouple planning from evidence,"*
was exactly 0.1), **AgentCPM-Report** (2026 — revise the outline *during* research), and Static-DRA
(tree + depth/breadth knobs). See `docs/deep-aletheia-design.md` §9.

- **The tree is now a living outline grown from evidence, not guessed up front.** A node investigates
  a round, **reflects**, then **deepens** (drills the same question) or **decomposes** (proposes
  sub-questions) based on what it found — removing 0.1's most error-prone step (a-priori
  decomposition, the source of off-target branches). `treestate.py`: `propose`/`materialize` +
  `frontier --depth` for level-by-level processing (equal time per level).
- **Real depth at the leaf** (fixes "surface level"): `investigate.py` is now one *round* that
  **accumulates** across calls (append per-round `evidence.md`, accumulate `n_read`, add a `rounds`
  counter); the worker sequences rounds via the now-wired `deepen.py` (reflect → drill the gap).
  Reads/round ≈ one scrutiny unit, so raising `--budget` buys leaf depth, not just branching. Also
  fixes a real bug: node `sources.jsonl` was appended unconditionally every call (only the global
  index deduped), which duplicated sources and corrupted independence math under multi-round.
- **Back-and-forth is enforced** (parents ask thin children instead of assuming): `synthesize.py
  --gate` exits nonzero and writes a BLOCKED block while any child is thin and unanswered.
- **Router fix**: nutrition/clinical topics were misfiled as consumer-trends (firing off-domain
  channels); `classify()` now routes ≥2 biomed signals to science/medicine.
- **Depth metrics** in `scripts/eval/score_run.py` (rounds/leaf, evidence-driven vs a-priori
  children, clarification coverage, reads-by-depth, per-leaf CV) to prove 0.2 is deeper than 0.1.
- Kept the epistemic core unchanged: hypothesis portfolio (anti-anchoring), source-independence
  judgment, adversary, two-layer verification, read-in-full, and the human-owned DOK 3–4 judgment.

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
- **Verification gate** (`verify.py`), two layers: a deterministic pass certifies **relevance
  only** (`broken`/`off_topic`/`relevant`) and **never** `supported` — lexical overlap can't see
  polarity/negation or magnitude ("IF is superior" vs "IF is *not* superior" share nearly all
  words). Entailment (`supported`/`contradicted`/`unsupported`) is the **LLM verifier subagent's**
  call on every `relevant` claim. Caught while dogfooding: the old lexical pass had scored a
  deliberately-false "doubles fat loss" claim as `supported`. Also fixed a latent bug where a
  readable-but-zero-overlap source was misreported as `broken` instead of `off_topic`.
- **Run scorer** (`scripts/eval/score_run.py`): the deterministic half of the Anthropic-style
  rubric plus Aletheia epistemics — citation accuracy (from the LLM verdicts), source quality,
  independence/echo, framing coverage, disconfirmation, tree shape.
- **Orchestrator skill** (`deep-aletheia/SKILL.md`): recursive decomposition, parallel read-only
  Task subagents, bottom-up synthesis with top-down clarification.

## aletheia 1.0.0 — 2026-07-08

- Initial: anti-anchoring judgment-driven surveyor + heterogeneous no-key channels
  (Brave, OpenAlex, arXiv, Reddit, Hacker News, YouTube, Stack Exchange, GitHub, books,
  real-browser reads), independence judgment, adversary, defensibility, Consilient Atlas.
- Reddit discovery relevance-fix (`site:reddit.com` via Brave/DDG; opencli for thread reads).
- Fix silent YouTube discovery failure; add `scripts/eval/run_metrics.py`.
