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

## aletheia-research 0.4.0 — 2026-07-09 (unlimited by default + verbosity dial)

Depth and audience are now first-class. Motivation: bounded tiers produced surface-level briefs that
didn't beat a few minutes of Google — the target is a brief worth a full DAY of manual searching (a
WEEK at `max`).

- **`unlimited` is the new DEFAULT** (`treestate.py init` with no tier/budget). Budget and depth are
  effectively unbounded (budget 1e6, max_depth 99); the stop is no longer budget-exhaustion but
  **agent-paced convergence** — keep splitting/deepening until a branch is saturated (no new distinct
  origins/claims). A high `max_nodes` (512; 2048 at `max`) remains only as a runaway backstop. The
  bounded tiers (`quick`/`standard`/`deep`/`exhaustive`) stay for when speed matters; `max` is the
  "proper flag" — same unbounded caps, run maximally (~a week). An explicit `--budget` still means a
  bounded CUSTOM run (nothing silently overrides it).
- **Verbosity dial** (`init --verbosity user|agent`, stored in run.json):
  - `agent` → the skill returns the **FULL artifact bundle**, not a summary: new `report.py bundle
    --run RUN --reads` concatenates every node's findings + evidence + sources + the primaries read in
    full. A calling agent loses no nuance to compression.
  - `user` (default) → a **multi-page nuanced summary** (a few pages minimum): mechanisms,
    disagreements and why, decisive sources, caveats, gaps — the distilled equivalent of a day's work.
- **New `report.py`** — output assembler: `bundle` (agent full-files) and `outline` (artifact
  inventory, so the user summary covers every branch and drops nothing).
- SKILL rewritten for the new default + verbosity; tests 74 → 77.

Still open (design-level): neural retriever (Exa) for the recall ceiling; the equal-token-budget
single-agent-vs-tree head-to-head; adaptive budget; threshold calibration.

## aletheia-research 0.3.3 — 2026-07-09 (keyword-recall — the audit's #1 systemic weakness)

Closes the recall gap the deep audit ranked as the dominant systemic weakness — the free indexes AND
their terms, so a long compound query returns NOTHING (it degraded both self-audits live). Designed,
then adversarially reviewed by a workflow that RAN the code; the review caught a real regression in the
first keywordize attempt and it was corrected before shipping. Tests 65 → 74.

- **0-result relaxation (`investigate.retrieve`):** the core fix — when a channel returns [] on a
  >3-word query, retry with progressively fewer keywords (keywordize → 3 → 2), first non-empty wins;
  capped at 2 retries, never broadens a query that already returned results, applies to ALL channels
  (incl. openalex/arxiv), and records `relaxed_to` in the per-channel report. Off-topic broadening is
  bounded by `rank`'s multiplicative relevance gate against the ORIGINAL query.
- **Salience-aware `keywordize` (`_http`):** keeps the n keywords that matter — quoted phrases, then
  ENTITY terms (acronyms / proper nouns / identifiers, distinctive regardless of position — the
  audit's actual complaint was dropping late proper nouns like Exa/Tavily), then the rest in discovery
  order (natural queries front-load the topic); total capped at n. *Review-caught & fixed:* the first
  attempt ranked by word length, which regressed common front-loaded queries (dropped "acid rain" for
  "significantly", "Claude" for "released") and let quoted phrases overflow n — length was replaced by
  the entity+position scheme, a strict improvement over the old first-n.
- **`doctor`:** probe query made realistic (`climate change effects`) and an honest caveat added —
  sequential single-request probes confirm a channel is REACHABLE, not concurrency-proof; parallel
  fan-out can still 429 the keyless academic pools (the real reason doctor false-greened under the
  audit's 12-worker fan-out).

Still open (design-level, not this release): keyword recall is fundamentally capped without a neural
retriever (add Exa as the first paid upgrade); the equal-token-budget single-agent-vs-tree head-to-head
that would settle the N=1 promotion — now runnable on a non-degraded toolkit.

## aletheia-research 0.3.2 — 2026-07-09 (deep-audit bug fixes)

Fixes the 6 code bugs the deeper per-component/per-step self-audit
(`runs/aletheia-research/2026-07-08-2139-self-audit-031-deep/brief.md`) reproduced deterministically.
Each fix was designed and then adversarially reviewed by a workflow that RAN the code; the review
caught and corrected two would-be regressions before they shipped (noted below). Tests 61 → 65.

- **B1 (budget):** `treestate.split_node` now warns (stderr) when a weighted split has no headroom
  (`B = K·U`, so weights can't apply above the scrutiny-unit floor), and folds the rounding residual
  into the most-scrutinized child so children sum **exactly** to the parent (fixes Σ=32.001 drift).
- **B2 (independence):** `provenance_graph.build_clusters` no longer false-merges distinct primaries —
  a near-duplicate text merge is vetoed when a **canonicalized** strong id (DOI / arXiv / PMID) proves
  the works are distinct. *Review-caught:* the first attempt (a `snippet≥5` guard) re-introduced an
  over-count by missing title-only wire-echoes, and `_norm_doi` missed `www.doi.org`/trailing-slash/
  `?query` notations — both fixed (veto-only + full DOI canonicalization; a matching id now dominates).
- **B3 (independence):** `dedupe.voice_key` keys author-less records on their canonical URL (not the
  bare domain), so distinct anonymous pages on one domain stay distinct voices; dead `PLATFORM_DOMAINS`
  removed.
- **B4 (verification):** `verify.py` (both copies, kept byte-identical) adds a light stemmer
  (`caloric`~`calorie`, `fasting`~`fast`; excludes collision-prone `al`/`ational`) and a `borderline`
  verdict so a readable low-overlap paraphrase is routed to the LLM instead of being silently dropped.
  `score_run.py` now counts readable `off_topic` in the precision **denominator** (a dropped citation
  can no longer vanish and inflate precision). Both SKILLs: Fact-Check every `relevant` **and**
  `borderline` claim.
- **B5 (router):** keyword matching is now on **word boundaries** (`kw in tokens`), killing the
  `"gene"`-in-`"general"` mis-scope. *Review-caught:* the added `<2` abstain wrongly stripped the
  domain primary from narrow single-signal queries (`insulin resistance`→general) — removed; the
  word-boundary fix alone resolves B5 with no collateral loss.
- **B6 (retrieval):** `investigate._anchor` drops generic research-meta words (`_META`) and keeps the
  first ≤3 surviving subject terms **in topic order** (not by length), so a coined/meta topic yields
  no fragment-noise prefix and a short distinctive token (`keto`/`json`) is no longer dropped for a
  longer generic word.

## aletheia-research 0.3.1 — 2026-07-08 (audit fixes)

Fixes grounded in the exhaustive design self-audit (`docs/evals/2026-07-08-aletheia-design-audit.md`,
472 sources), which found one confirmed flaw, one under-detection, and a set of tool bugs caught while
dogfooding. Every change below traces to a numbered audit recommendation.

- **Budget — killed the uniform split (audit #1).** `treestate.split_node` now takes optional
  `--weights`: budget is still conserved and every child floored at the scrutiny unit, but the
  *remainder* is distributed by contestedness/uncertainty (scale-effort-to-complexity; Snell
  2408.03314, UAB 2605.26849). Uniform stays the default when no weights are given.
- **Independence — fixed `voice_key` under-detection (audit #2).** `synthesize.independence` now also
  reports structural `independent_origins` / `origin_echo_ratio` via `provenance_graph.build_clusters`
  (canonical-url + voice + `derives_from` + near-duplicate shingles), so "40 domains echoing one origin"
  no longer scores as independent. The synthesis warning and `score_run` now key off the structural
  signal; low identity-echo no longer licenses "Agreement."
- **Verification — made it real & code-gated (audit #3).** `score_run` demotes `citation_accuracy` to
  **precision** (`supported / finally-judged`) reported **only when `citation_complete`** (every
  on-topic claim has a verdict, `citation_coverage` = 1.0), with a stated `citation_denominator`. SKILL
  now mandates a **different judge model** than the writer (self-preference bias).
- **Diversity — forced structurally (audit #4).** SKILL requires each framing to be grounded in a
  distinct source base / channels (mode collapse: Persona-Generators 2602.03545, Verbalized-Sampling
  2510.01171); framings that retrieve the same sources are merged.
- **Retrieval bugs the run itself exposed (audit #5).** `investigate._anchor` no longer pollutes queries
  with proper-noun/coined topics or over-anchors self-contained questions (the self-referential
  "Aletheia papers" bug); reads flag `_truncated` at the 40k cap (no silent cut-off); `semanticscholar`
  gets exponential backoff with jitter (was 429-throttled nearly every run); `rank.AUTH_HIGH` adds
  biomed/regulatory venues (Lancet/BMJ/JAMA/NEJM/Cochrane/EFSA/EMA/WHO/NICE) + wire services — the
  CS-bias fix.
- **Resumability (audit #6).** `frontier --resumable` re-picks pending **plus** crashed-mid-round
  `active`, unanswered `needs_answer`, and un-materialized `proposes_split` nodes — a mid-round crash is
  no longer silently skipped.
- **Labels/docs (audit #7).** Dropped the unsupported "equal time per level" claim (breadth-first is a
  scheduling order, not an equal-time promise); "blackboard" → "shared-artifact store"; fixed the
  Reddit `color`/`lead_gen` contradiction (X/YouTube = color; Reddit/HN = lead_gen → cite the primary).
- Tests: 44 → 52 (weighted split conservation/floor, resumable frontier, structural independence both
  directions, `_anchor` de-pollution, biomed authority, code-gated citation coverage).

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
