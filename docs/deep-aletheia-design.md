# Deep Aletheia — architecture design

**Status:** proposal (for review before build)
**Author:** dogfooded Aletheia run + code/metrics audit, 2026-07-08
**Baseline:** Aletheia v1 @ commit `b310cf0` (+ YouTube fix `5348928`)

> Goal (user): a *deeper* research surveyor with a **revised, improved architecture — not
> just a longer runtime**. Grounded in metrics from real Aletheia runs and in how frontier
> deep-research systems are actually built. Tokens/time are not a constraint; output quality is.

---

## 1. What Aletheia v1 actually is

v1 is a **judgment-driven skill**, not an engine. The "orchestration" is the agent reading
`aletheia/SKILL.md` and hand-executing 8 steps (frame → pick channels → retrieve → read →
judge independence → iterate → attack → answer). The machinery underneath is a set of
**stateless helper scripts**: channel clients (`brave/openalex/arxiv/reddit/hn/...`), plus
`rerank`, `dedupe`, `read`, `deepen`, `provenance_graph`, `doctor`.

That design is honest and portable, but it means the "depth" is entirely dependent on the
agent remembering to do each step well, in one context window, by hand. There is **no
orchestration, no parallelism, no automated routing, no verification, no memory, no eval.**
Those absences are where "deep" has to come from.

---

## 2. Measured baseline (from `scripts/eval/run_metrics.py`, built for this)

I instrumented real retrieval passes. Numbers, not vibes:

| Topic | Channels that fired | total→unique | domains / index-groups | echo | relevance median | read ok |
|---|---|---|---|---|---|---|
| "multi-agent LLM systems for deep research" | openalex, brave, reddit, github, arxiv, hn (6/9) | 55 | 12 / 6 | 20% | **0.131** | 5/5 |
| "best budget mirrorless camera 2026" | arxiv, reddit, brave (3/9) | 30 | 11 / 3 | 33% | **0.122** | 4/5 |

### Measured weaknesses (each drove a design decision)

1. **W1 — YouTube silently dead.** `yt_search` ran `python -m yt_dlp` (module absent; binary
   present) → returned `[]` with no error. The flagship transcript channel was invisible.
   *(Fixed in `5348928`; kept here because "fails silently" is the class of bug to design out.)*
2. **W2 — No topic-aware routing.** Firing the enabled set put **10 irrelevant arXiv papers on
   a camera topic**. `channels.json` has `selection_guidance`, but nothing *executes* it — it's
   a comment the agent may or may not honor.
3. **W3 — Lexical rerank misranks.** TF-IDF put a Temporal workflow **doc** as #1 for the
   architecture question, and spent the entire read budget on **Medium/blog listicles + GitHub
   over the arXiv/OpenAlex papers**. Reading budget → secondary content.
4. **W4 — Low raw relevance / noise.** Median relevance ~0.12–0.13; single-pass retrieval is
   noisy. Depth needs iterative deepening + query refinement, not one shot.
5. **W5 — Echo present even at N=10** (20–33% voice collapse). Grows with scale; independence
   must be enforced, not hoped for.
6. **W6 — Silent zeros / fragility.** Marginalia works alone but returns 0 under the parallel
   burst (rate-limited); channels fail quietly with no surfaced diagnostics.
7. **W7 — Community spam leaks.** Even relevance-first Reddit surfaced `r/Seotrendingblogs`.
8. **W8 — No verification.** Nothing checks a cited source actually supports the claim.
9. **W9 — No memory/eval.** Runs don't compound; there was no way to score a run until I built one.

---

## 3. External evidence (dogfooded through Aletheia itself)

Read in full via Aletheia's own channels. Independence noted (the whole point).

- **Anthropic, "How we built our multi-agent research system"** (eng blog, 2025-06)
  <https://www.anthropic.com/engineering/multi-agent-research-system>
  - Orchestrator-worker: lead plans, spawns **parallel subagents with separate context
    windows**, each explores one aspect and **compresses** findings back. **+90.2%** over
    single-agent on their internal research eval (breadth-first).
  - **Token usage alone explains ~80% of performance variance** on BrowseComp (tool-calls +
    model = 95%). "Multi-agent works mainly because it spends enough tokens." Multi-agent
    ≈ 15× chat tokens → only worth it for high-value tasks. **→ validates "ignore tokens".**
  - Measured failure: agents **"consistently chose SEO-optimized content farms over
    authoritative but less highly-ranked sources like academic PDFs."** ← *independent
    corroboration of my W3.*
  - Prescriptions: detailed delegation (objective/format/tools/boundaries); scale effort to
    complexity; "start wide then narrow"; **write subagent output to filesystem to avoid the
    "game of telephone"**; dedicated **CitationAgent**; **LLM-as-judge** rubric (factual
    accuracy, citation accuracy, completeness, source quality, tool efficiency); checkpoints +
    resume; observability.

- **Cognition, "Don't Build Multi-Agents"** (eng blog, 2025-06) — *opposing thesis, independent*
  <https://cognition.ai/blog/dont-build-multi-agents>
  - **Context engineering** is the #1 job. Principle 1: **share context AND full agent traces**,
    not one-liners. Principle 2: **actions carry implicit decisions**; conflicting decisions →
    bad results. Parallel subagents that make **interdependent** decisions are fragile
    (their combine step is a telephone game). Default to **single-threaded**; for overflow,
    add a **compression model** that distills history into key decisions.

- **"Cited but Not Verified"** (arXiv 2605.06635, 2026-05) — independent academic
  <https://arxiv.org/abs/2605.06635> — (1) surface citation quality **masks** factual failures;
  (2) more citations trade **against** accuracy; (3) **more search degrades factual accuracy**.
  Verify via Link-Works / Relevant-Content / Fact-Check.

- **"Less Context, Better Agents"** (arXiv 2606.10209, 2026-06) — independent academic
  <https://arxiv.org/abs/2606.10209> — full context helps but is costly; **pruning +
  summarization improve performance *and* cut tokens**.

- **"Search-Time Contamination in Deep Research Agents"** (arXiv 2606.05241, 2026-06)
  <https://arxiv.org/abs/2606.05241> — web-searching agents can retrieve benchmark answers →
  inflated scores. Eval must be **contamination-aware + trajectory-transparent**.

- Practitioner color (Reddit, cited as color not proof): the single-vs-multi debate is live
  ("The real problem with multi-agent systems isn't the models, it's the handoffs";
  "Single agents win"). Echoes Cognition's handoff thesis.

### The reconciliation (this is the load-bearing insight)

Anthropic says *more tokens → better*; the papers say *more search → worse* and *less context
→ better*. Not a contradiction:

> **Spend tokens on parallel breadth, each worker in a clean, focused context — not on bloating
> one context or on unverified search sprawl.** Depth = (many independent, well-scoped, read-only
> explorations) + (aggressive compression) + (a verification gate), NOT a longer single loop.

And Anthropic vs Cognition reconcile on domain: parallel subagents are **safe + beneficial for
read-only, decomposable, breadth-first research** (workers gather/compress independent slices;
one writer synthesizes) and **dangerous for interdependent build tasks** (code). Research
surveying is the safe case. That is exactly Aletheia's domain.

---

## 4. Deep Aletheia — the architecture

An **orchestrator-worker research system** that keeps v1's epistemics (anti-anchoring,
class discipline, independence, adversary) and adds the six things v1 structurally lacks:
**routing, parallel read-only workers, authority-aware ranking, verification, memory, eval.**

```
                          ┌─────────────────────────────────────────────┐
  user topic ──▶ ORCHESTRATOR (lead, single-threaded)                    │
                │  1. Frame hypothesis portfolio (v1, kept)              │
                │  2. Decompose → detailed worker specs (Anthropic P2)  │
                │  3. Scale #workers to complexity                      │
                └───────────────┬───────────────────────────────────────┘
             spawns N parallel, READ-ONLY workers (separate contexts)
        ┌───────────────┬───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
   WORKER(framing A) WORKER(B)     WORKER(C)     WORKER(disconfirm-leading)
   • router picks channels (W2 fix)                 ← at least one worker
   • iterative-deepen: broad→narrow (W4)              hunts DISconfirming
   • authority-aware rank (W3 fix)                    evidence (adversary
   • read primaries IN FULL, class-budgeted            baked in, not bolted)
   • write ARTIFACTS to run/ (sources.jsonl, notes.md) — no telephone
   • return LIGHT summary + artifact paths ─────────────┐
        └────────────────────────────────────────────────┤
                                                          ▼
                          ┌───────────────────────────────────────────────┐
                          │  ORCHESTRATOR (synthesis, single-threaded)     │
                          │  4. Merge artifacts; dedupe + independence     │
                          │     (echo_ratio, provenance) — W5              │
                          │  5. Draft: Agreement / Disagreement / Unverified│
                          └───────────────┬───────────────────────────────┘
                                          ▼
                          ┌───────────────────────────────────────────────┐
                          │  VERIFIER (dedicated pass) — "Cited not Verified"│
                          │  every claim: Link-Works? Relevant? Fact-Check │
                          │  unsupported → downgrade/flag. (W8)            │
                          └───────────────┬───────────────────────────────┘
                                          ▼
                     decision-ready brief + run/ artifacts + Atlas entry (memory)
```

### Components (new unless noted)

- **C1 Orchestrator** — single-threaded lead. Frames the portfolio (keep v1 step 1, it's the
  best part), decomposes into **explicit worker specs** (objective, output schema, channel
  hints, boundaries — Anthropic P2), scales worker count to complexity, and is the **only**
  writer at synthesis (Cognition: one context sees all). Does no retrieval itself.

- **C2 Workers (parallel, read-only)** — the "spend tokens" engine. Each gets the **full shared
  framing/plan** (Cognition P1: share context, not one-liners), owns **one** framing/dimension,
  runs router→deepen→rank→read, and **writes artifacts to `run/<ts>/worker-<k>/`** returning
  only a light summary + paths (Anthropic anti-telephone). Read-only ⇒ Cognition-safe (no
  interdependent decisions to conflict). **≥1 worker is the adversary** — its job is to find the
  strongest *disconfirming* evidence for the current leading framing.

- **C3 Channel router** (`router.py`, new) — turns `channels.json:selection_guidance` from a
  comment into a function: `topic + framing → channel set` covering the 3 roles
  (independent-web / primary / un-laundered), excluding off-topic indexes. **Fixes W2.**

- **C4 Authority-aware ranker** (upgrade `rerank.py`) — beyond TF-IDF: **class-aware read budget**
  (guarantee K primaries + K community reads; never blow the budget on listicles), prefer
  `evidence` over `lead_gen`/aggregators, use signals already in records (`cited_by_count`,
  domain authority, primary flag). Optional embedding rerank with a no-key fallback.
  **Fixes W3** (and Anthropic's SEO-farm finding).

- **C5 Verifier** (`verify.py` + verifier subagent, new) — the CitationAgent + fact-check gate.
  For each drafted claim: does the cited URL resolve to a real source (Link-Works), does its
  content actually address the claim (Relevant), does it support it (Fact-Check)? Unsupported →
  downgrade to *Unverified* or cut. **Fixes W8**; directly implements the arXiv finding.

- **C6 Memory / run-state** (new) — every run persists to `run/<ts>/` (plan, per-worker
  artifacts, merged sources, draft, verified brief) → **resumable + checkpointed** (Anthropic
  reliability). Completed phases are **summarized/compacted** (Less-Context paper). Final brief
  accretes into the **Consilient Atlas** so runs compound (v1 skill, now actually wired in).

- **C7 Eval harness** (extend `scripts/eval/`) — LLM-as-judge on Anthropic's rubric (factual
  accuracy, citation accuracy, completeness, source quality, tool efficiency) **plus** Aletheia
  metrics (independence/echo, framing coverage, disconfirmation effort). ~20 fixed test topics;
  **contamination-aware** (don't let workers fetch the eval's own answers). Lets us prove Deep
  Aletheia > v1 > bare-LLM, and prevents regressions. **Fixes W9.**

- **C8 Robustness** (cross-cutting) — no silent zeros: every channel reports fired/empty/error;
  rate-limit-aware scheduling + retries (W6); community spam/authority filter (W7).

### DOK split (as you framed it)

- **Workers = DOK 1–2** (broad recall, retrieval, extraction, compression).
- **Orchestrator + Verifier = DOK 2–3** (independence, synthesis, attack, attribution).
- **You = DOK 3–4**: the brief is *decision-ready* with disagreements surfaced, not smoothed —
  human stays in the loop at framing sign-off and final judgment.

### What we deliberately DON'T do (anti-patterns, evidence-backed)

- No parallel workers making **interdependent** decisions (Cognition) — workers are read-only.
- No "just run longer / search more" as the depth mechanism (Cited-but-Not-Verified: more
  search can *lower* accuracy). Depth = parallel breadth + verification, not a longer loop.
- No dumping everything into one growing context (Less-Context) — compress per phase.
- No novel independence "graph" as the core (kept optional, as in v1) — judgment first.

---

## 5. Implementation in this environment

Cursor/Claude gives real orchestration primitives, so this is buildable natively:

- **Orchestrator** = a new **`deep-aletheia/SKILL.md`** the lead agent runs.
- **Workers** = **Task subagents** (`subagent_type: explore`/`generalPurpose`, run in parallel)
  — real separate context windows, exactly the Anthropic model. Each worker runs the **existing
  v1 channel scripts** (they work) for its framing and writes artifacts.
- **New code** is small and additive: `router.py`, ranker upgrade, `verify.py`, run-state
  helpers, eval extensions. **All v1 channels/skills are reused**, so this is an evolution, not
  a rewrite. v1 stays intact (`aletheia` skill) for quick surveys; `deep-aletheia` is the heavy one.

## 6. Build plan (phased, each independently useful)

- **P1 — Router + authority-aware reading** (fixes W2/W3): biggest quality/token win, no new agents.
- **P2 — Orchestrator-worker skill** (C1/C2) using Task subagents + artifacts.
- **P3 — Verifier** (C5) claim→source gate.
- **P4 — Eval harness** (C7) to prove the gains on ~20 topics.
- **P5 — Memory/Atlas + robustness** (C6/C8) for compounding + no-silent-fail.

## 7. Success criteria (must beat v1 on the eval, not just run longer)

Deep Aletheia is "better" iff, on the eval set: higher citation-accuracy (verified claims),
higher source-quality (primaries over farms), higher framing coverage + disconfirmation effort,
lower echo, **with** transparent trajectories — even though it spends far more tokens.

---

## 8. v2 addendum — recursive tree, budgets, bidirectional flow, blackboard

The single-level orchestrator→workers of §4 is too shallow ("surface-level"). v0.1 makes the
architecture a **recursive agent tree coordinated entirely through the filesystem**.

### 8.1 Recursive decomposition (depth, not one layer)
A node whose question is too broad **splits into child sub-questions** instead of investigating
directly; children may split again. A worker can spawn a fresh Aletheia sub-survey for its slice.
Recursion stops when a node's budget hits the **scrutiny unit** (an atomic question gets the full
route→read→verify treatment) or a hard cap trips.

### 8.2 Budget model = "equal time per level" + "equal scrutiny per leaf"
- A node holds a **budget** `B` (abstract effort units ≈ reads/tool-calls). Splitting into `K`
  children gives each `B/K` — **budget is conserved across a split**.
- Recurse while `B/K ≥ U` (the scrutiny unit); otherwise the node is a **leaf** and spends `B`
  on investigation (deeper reading if it can't usefully split — budget is never wasted).
- Consequence: for a balanced tree, **every level sums to ≈ `B_root`** (equal effort per level,
  your constraint) and **every leaf gets ≈ `U`** (equal scrutiny). Decomposition is chosen to
  keep the tree balanced.
- **Hard caps** (anti-explosion, per Anthropic's 50-subagent failure): `MAX_DEPTH`,
  `MAX_CHILDREN`, `MAX_NODES`, `MIN_LEAF_BUDGET = U`.

### 8.3 Bidirectional flow (no more "assuming")
Information flows **up** (children compress findings into `findings.md`) **and down**: a parent
that needs specifics writes to a child's `questions.jsonl`; the child re-activates and answers
from its **already-gathered sources** (cheap, no re-retrieval) into `answers.jsonl`. Flow is
strictly **parent↔child** (hierarchical), never peer↔peer — that's the fragile case Cognition
documented. The lead routes each higher agent's question to the target child.

### 8.4 Filesystem as the blackboard (storage is free; use it)
Every node is a directory; **all coordination is files**, so nothing depends on a single context
window:

```
runs/deep/<ts>-<slug>/
  run.json            topic, version, budgets, caps, status
  portfolio.md        hypothesis framings (anti-anchoring)
  tree/<node-path>/
    spec.md           question, role, budget, depth, parent
    status.json       state: pending|active|split|investigated|synthesized|answered
    decisions.jsonl   {t, actor, decision, why}         ← per-agent reasoning log
    questions.jsonl   parent → this (clarifications)
    answers.jsonl     this → parent
    sources.jsonl     retrieved/kept records (this node)
    notes/            full reads (one file per source)
    findings.md       compressed result that bubbles up
    children/<q>/     recursive
  index/
    sources.jsonl     global dedup + independence across the whole tree
  brief.md            final grounded answer
  verify.jsonl        per-claim Link-Works/Relevant/Fact-Check
```

Benefits: context never overflows (state on disk), no telephone (artifacts not messages),
resumable/checkpointed, and fully auditable (decision logs + trajectories).

### 8.5 Versioning
`aletheia` (v1) stays as the quick surveyor. `deep-aletheia` is versioned separately (`VERSION`,
`CHANGELOG.md`, git tags `deep-aletheia-vX.Y.Z`) since it will iterate.

---

## 9. v0.2 addendum — from a static tree to a dynamic, question-driven surveyor

**Status:** built. **Basis:** the first live 0.1 runs were *surface-level* and the machinery was
complex; the developer asked for depth from **both** leaf-deepening and larger-scope decomposition,
enforced back-and-forth, and — crucially — **simplicity that comes from a better research design, not
from cutting scripts.** So the fix is to make deep-aletheia work the way rigorous researchers and the
strongest systems actually do.

### 9.1 What 0.1 got wrong (measured)
Every leaf did **one** retrieval round (`n_read` 3–4; ~15 reads per survey) — v1's single pass,
parallelized. The parent↔child ask/answer channel was **never used** (`Qs=0/As=0`). Decomposition was
**guessed a-priori** before any evidence (off-target branches; the router even misfiled a nutrition
topic as consumer-trends). Budget conservation made deeper trees *shallower* leaves — depth traded
against scrutiny.

### 9.2 The reframe (evidence, read in full — independent origins)
- **STORM** (Stanford OVAL, NAACL 2024, arXiv 2402.14207): survey quality is set in *pre-writing* —
  discover diverse **perspectives**, ask **multi-perspective questions** to retrieval-grounded
  experts, curate an **outline**. Names failure modes: **source-bias transfer**, **over-association**.
- **WebWeaver** (SOTA OEDR, 2025, arXiv 2509.13312): names 0.1's exact flaw — *"static research
  pipelines that decouple planning from evidence acquisition."* Fix: a **dynamic cycle interleaving
  evidence acquisition with outline optimization**, a filesystem **memory bank**, **section-by-section
  grounded writing**. *"Emulates the human research process."*
- **AgentCPM-Report** (2026, arXiv 2602.06540): *plan-then-write depends on an initial outline you
  can't get right up front* → **revise the outline during research** (alternate draft ↔ deepen).
- **Static-DRA** (arXiv 2512.03887): a tree DRA with tunable **Depth/Breadth**; higher → measurably
  better — and flags "static" as the limitation.

Convergent lesson: **never fix the decomposition before the evidence.** Interleave planning and
evidence; the outline (tree) grows from what's found.

### 9.3 The 0.2 model — the research method *is* the architecture
One metaphor, processed **level by level** (equal time per level), each step mapping to an existing
piece (reuse-first, nothing deleted):

1. **FRAME** — perspectives → questions (STORM + the hypothesis portfolio). The competing framings are
   the *only* a-priori decomposition; the human signs off (DOK-3/4 entry).
2. **GROW THE OUTLINE FROM EVIDENCE** — a node investigates a round → **reflects** → **deepens**
   (drill the same question, via the now-wired `deepen.py`) or **decomposes** (`treestate propose` →
   orchestrator `materialize`). Depth = both axes. Replaces the a-priori split.
3. **BACK-AND-FORTH** — `synthesize.py --gate` blocks authoring while a child is thin and unanswered,
   forcing the parent to **ask** and the child to **answer from its already-gathered sources**.
4. **JUDGE INDEPENDENCE + ADVERSARY** — unchanged from v1 (the differentiator).
5. **WRITE GROUNDED + VERIFY** — section-by-section from the memory bank; two-layer citation gate
   (lexical relevance → LLM entailment). The human makes the final DOK 3–4 judgment.

**Why this is simpler:** it is one coherent human-research method, not a split-machine + a separate
deepen-loop + a budget-currency subsystem. The hardest, most error-prone step — guessing a correct
tree before any evidence — is *removed*. Depth and simplicity both come from the better method.

### 9.4 What changed in code (small, additive)
`investigate.py` accumulates across rounds (+ node-source dedup bug fix); `deepen.py` wired in as the
per-node round controller; `treestate.py` gains `propose`/`materialize` + `frontier --depth`;
`synthesize.py` gains `--gate`; `router.py` biomed fix; `score_run.py` depth metrics; `SKILL.md`
rewritten around the five steps. The epistemic core (portfolio, independence, adversary, verify,
read-in-full, DOK split) is unchanged.
