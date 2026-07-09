# Changelog

Current skill:
- **aletheia-research 0.3** — deep, multi-perspective research surveyor (filesystem tree; parallel
  read-only investigations; wide source variety; decisive-source hunt; completed verification). This is
  the one to use. (Renamed from `aletheia` so its purpose — the research tool to invoke — is explicit.)

## channel-retrieval — reliability fixes (2026-07-08)
- **Query formulation:** keyword channels (HN/Stack Exchange/GitHub/Marginalia) returned 0 on long
  natural-language queries; added a shared `_http.keywordize()` (short queries pass through) so they
  match. Fixes the silent variety loss seen in real runs.
- **Marginalia:** pointed at the dead `old-search.marginalia.nu`; switched to the live
  `marginalia-search.com` (results parse again).
- **Enabled DuckDuckGo** as a second reliable keyless independent web index alongside Brave.
- **doctor.py is now FUNCTIONAL:** it runs a real query per channel and flags "live but 0 results" as
  `warn` (a false `ok` had hidden Marginalia). aletheia-research surfaces `warn`/`down` channels to the
  user and lists them in the brief's Gaps. See `docs/channel-proposals.md` for sources worth adding.


Kept runnable ONLY as eval baselines (`scripts/eval/eval_compare.py`):
- **deep-aletheia 0.2** — the direct **ancestor** of aletheia 0.3 (frozen).
- **surveyor 0.1** — single-agent-first surveyor; superseded 2026-07-08.
- **aletheia v1.0** — the original single-agent judgment loop (the `aletheia` name was rebased onto the
  deep-tree line at 0.3).

Versioning is [SemVer](https://semver.org/); each notable change bumps minor/patch and is tagged `<skill>-vX.Y.Z`.

---

## aletheia 0.3.0 — unreleased

Built **off deep-aletheia 0.2**, which won a blind LLM-judge (5 judges, order-randomized) over the
single-agent `surveyor` on **completeness, source variety, and groundedness to distinct primaries** —
see `docs/evals/2026-07-08-creatine-cognition-bakeoff.md`. 0.3 keeps 0.2's engine and good parts and
adds four things. Design + evidence: `docs/aletheia-0.3-design.md`.

- **Kept from 0.2 (the good parts):** the multi-perspective portfolio tree (→ variety of distinct
  sources), real multi-round surveying, evidence-driven decomposition, bottom-up synthesis with an
  enforced ask/answer gate, adversary, independence/echo judgment, honest gaps, and a verification
  gate that runs to completion. Engine reused verbatim (`treestate/investigate/synthesize/verify/
  rank/router`), copied into `aletheia/scripts/` so deep-aletheia 0.2 stays frozen as a baseline.
- **New #1 — hunt the DECISIVE source.** Actively find the authoritative/settling source (regulator
  opinion, landmark SR/MA, largest RCT), not just pool many primaries — the one place the single-agent
  design beat 0.2 (it found the EFSA verdict that 0.2 missed).
- **New #2 — chase the primary, never cite the secondary** (find the primary behind any blog/summary,
  or mark Unverified).
- **New #3 — wider source variety by design** (multiple index-groups per framing).
- **New #4 — thoroughness dial** (`quick|standard|deep|exhaustive` + `auto`) on `treestate.py init`,
  making it callable/scaled from any session (scales the tree's budget/caps to the question).

---

## surveyor 0.1.0 — unreleased

Fresh skill rebuilt from the deep-aletheia self-audit (X/Reddit/HN/papers), which retired both prior
skills. Design + evidence: `docs/surveyor-design.md`.

- **Single-agent-first.** The audit's strongest finding: frontier deep-research is single-loop
  (OpenAI Deep Research, HF smolagents 55%↔67% GAIA, Step-DeepResearch, Tran & Kiela SAS≈MAS at equal
  tokens); multi-agent only earns its cost for *independent breadth* (Anthropic +90.2%). So surveyor's
  core is a single-agent loop; it fans out to one read-only worker per angle ONLY at `deep`/`exhaustive`
  — no recursive tree.
- **Thoroughness dial replaces the flawed uniform budget.** `quick | standard | deep | exhaustive`
  plus `auto` (scope → scale to breadth×contestedness). Effort scales to complexity (Anthropic), not
  the retired conserved-B/K "equal scrutiny per leaf" currency (graded FLAWED: ~12.8% worse, and it
  made deep leaves single-pass).
- **Verification that completes.** Two layers — deterministic relevance (never certifies support) then
  an LLM entailment Fact-Check on every claim → supported/contradicted/unsupported. Reports a real
  `citation_accuracy` (the 0.2 flagship verifier never completed; `null` on its runs).
- **Flat run dir** by default (`sources.jsonl`, `notes/`, `deepen.json`, `verify.jsonl`, `brief.md`);
  `angles/<a>/` only at `deep`. Reuses the sound utilities (channel clients, read, rerank, dedupe,
  independence) — none of the retired tree/budget/gate machinery.
- **One driver, `surveyor.py`** (`plan|gather|deepen|independence|verify|score`) + a short callable
  `SKILL.md`. Callable from any session: `use the surveyor skill to survey <topic> (thoroughness: auto)`.
- **Eval harness** (`scripts/eval/eval_compare.py` + `topics.jsonl`): scores surveyor vs the retired
  baselines on a shared rubric so improvement is measured, not asserted. First run (IF topic):
  surveyor-standard had the **highest source-quality (0.567) and independence (0.567)** and a completed
  `citation_accuracy` of 0.5, vs deep-aletheia-0.2 (`None` — gate never ran) and 0.1 (0.5).
- Tests: `tests/test_surveyor.py` (tiers, channel roles, dedup, deepen convergence, independence,
  verify relevance-only, score). 39/39 pass.

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
