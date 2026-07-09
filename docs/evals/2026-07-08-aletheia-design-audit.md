# Aletheia Research — full design self-audit

**Date:** 2026-07-08 · **Method:** `aletheia-research` at `exhaustive` — 8 parallel read-only workers,
one per design cluster, each 3–7 investigate rounds. **Corpus:** 472 sources indexed, **114 read in
full**, echo_ratio 0.34 (healthy), 94 domains, 457 evidence-class. Run:
`runs/aletheia-research/2026-07-08-2045-self-design-audit/`.

## Bottom line
Most of the design is **sound and evidence-backed** — the multi-agent-only-for-read-only-breadth
topology, filesystem coordination, evidence-driven decomposition, authority ranking, read-in-full,
two-layer verification shape, chase-the-primary, and skills-only architecture all trace to strong
primaries. But the audit found **one confirmed flaw, one category error with no basis, and ~10
improvables** — and, notably, the run **caught real bugs in the tool while using it**. The single
highest-value fix is the **budget model's uniform split**; the most important epistemic fix is that
**`voice_key` under-detects the very "1 origin echoed 40×" failure it exists to catch.**

## Verdict table (≈30 decisions)
| # | Decision | Verdict |
|---|---|---|
| **Topology** | multi-agent tree of **read-only** workers | **sound** (safe *because* read-only/no-chaining — the form even Cognition/MAST exempt) |
| | parallel breadth only at high thoroughness | sound |
| | **"equal time per level"** | **improvable — no external basis** (conflicts with value-proportional allocation) |
| | bounded caps (max depth/children/nodes) | sound (matches Anthropic's 50-subagent failure + fix) |
| **Coordination** | filesystem-as-blackboard | **sound** (Google: blackboard +13–57% vs message-passing) — but "blackboard" *over-claims*; it's a shared-artifact store |
| | lightweight refs up (anti-telephone) | contested→sound-for-read-only (conditional on parents actually pulling artifacts; sibling-blindness) |
| | resumability via `frontier` | **improvable — concrete bug** (crash leaves `state=active`; `frontier` defaults to `pending` → silently skipped) |
| **Budget** | conserved split / **uniform "equal scrutiny per leaf"** | **PARTIALLY FLAWED** (uniform confirmed suboptimal; conservation-cap + unit-floor are sound) |
| | thoroughness dial | sound (caveat: `unit` constant → higher tiers buy more leaves, not deeper scrutiny) |
| | scale-effort-to-complexity | sound/strongly-backed — **but contradicts the uniform split** (top fix) |
| **Decomposition** | 4–6 competing-framings portfolio | sound (STORM; payoff is *source breadth*, not outline quality) |
| | evidence-driven vs a-priori split | **strongly supported** (WebWeaver + AgentCPM converge) |
| | same-model framings | **fake-diversity risk CONFIRMED REAL** (mode collapse; "be diverse" prompts fail) |
| | the specific 5-viewpoint taxonomy | **no basis** as a named set (STORM *derives* perspectives from data) |
| **Retrieval** | channel classes evidence/lead_gen/color | sound |
| | scope-aware **keyword** router | improvable (learned routers win; no confidence/abstain path) |
| | keywordize | sound |
| | "convergence stop **(dzhng-style)**" | **improvable — mislabeled** (no convergence implemented; dzhng uses a fixed depth countdown) |
| | authority ranking + class-budgeted reads | sound (weakness: AUTH/FARM lists small, CS-biased — no Lancet/BMJ/JAMA) |
| | read-in-full | sound (caveat: **40k-char cap, silent truncation**) |
| | decisive-source hunt + chase-primary | **sound — highest-leverage discipline** |
| | no-key channel diet | contested/improvable (keyword-web + keywordize + keyword-router *compound* into a recall gap; add neural Exa as first paid upgrade) |
| **Epistemics** | independence via **`voice_key`/echo_ratio** | **partially valid — under-detects** (counts source *identity*, so 40 domains echoing one origin score echo≈0) |
| | adversary pass | sound, conditional (it's a *fresh-retrieval* branch = the exempted case; risk: nothing enforces source disjointness) |
| | never-cite-color | sound core — but SKILL prose **contradicts** channels.json (Reddit = lead_gen there, "color" in SKILL §7) |
| **Verification** | two-layer gate (lexical→LLM entailment) | sound (matches "Cited but Not Verified") — but **layer-2 is honor-system, not gated code** |
| | LLM entailment judge | **defensible but UNCALIBRATED** (self-preference/position/verbosity bias; same model writes+judges) |
| | `citation_accuracy` headline | **weak/gameable** (precision-only; pair with recall/coverage + denominator) |
| | enforced ask/answer gate | partially justified (120-char proxy; "answer" adds no new retrieval → ritual) |
| **Meta** | skills-only, no framework | **sound** (Anthropic "Building Effective Agents"; Willison; Agent Skills now an industry standard) |
| | **DOK split** (AI 1–2 / human 3–4) | **contested — NO EMPIRICAL BASIS** (category error: DOK measures task demand, not performer capability; 2↔3 line least reliable; Webb disowned the "DOK wheel") |
| | Consilient Atlas memory | sound but improvable (flat markdown = naive end; add structure/consolidation/provenance; poisoning risk) |
| | blind LLM-judge vs numeric | sound with caveats (blind+absolute-numeric is the weak form; prefer pairwise + reference/rubric + human calibration) |

## What actually needs changing (ranked)
1. **Budget — kill the uniform split.** Keep conservation (cap) + scrutiny-unit (floor); reallocate the
   *remainder* by contestedness/uncertainty from post-round-1 reflection (UAB arXiv 2605.26849; Snell
   2408.03314; Anthropic "scale effort to complexity"). Resolves the design's own D1↔D3 contradiction.
2. **Independence — fix `voice_key`.** It counts source identity, so many domains echoing one origin
   look independent — it misses the exact failure it's named for. Add shared-origin/co-citation
   structure (bibliometric independence) and never let low echo_ratio license "Agreement."
3. **Verification — make it real.** Gate the layer-2 entailment in *code* (not an honor-system SKILL
   line); use a **different** judge model than the writer; calibrate κ against a small human-labeled
   set; demote `citation_accuracy` to paired precision+recall with a stated denominator (FactScore/SAFE/VeriScore).
4. **Diversity — force it structurally.** Ground each framing in *retrieved contrarian sources* /
   different channels, not one aligned model's imagination (mode-collapse: Persona-Generators 2602.03545,
   Verbalized-Sampling 2510.01171). The portfolio's whole value is contingent on this.
5. **Retrieval robustness (tool bugs the run itself exposed):** (a) `investigate.py._anchor()` pollutes
   queries with the root topic — it injected self-referential "Aletheia" papers when the topic is a
   proper noun; (b) **semanticscholar 429-throttled on nearly every run** (no backoff) and openalex/HN
   returned 0 on long compound queries — the keyword-recall gap, live; (c) `read` caps at 40k chars with
   no `truncated` flag; (d) AUTH list is CS-biased — add biomed/news venues.
6. **Resumability:** `frontier` should also re-pick `active`/`needs_answer` nodes (a mid-round crash is
   currently skipped).
7. **Labels/docs (no-basis claims to drop or soften):** "equal time per level", "convergence stop
   (dzhng-style)", DOK-as-capability-ceiling; fix the Reddit color/lead_gen contradiction; call it a
   "shared-artifact store," not a "blackboard."

## What's validated (keep, with confidence)
Read-only multi-agent breadth (safe side of the single-vs-multi debate); filesystem coordination;
bounded caps; evidence-driven decomposition; the competing-framings portfolio (for breadth); channel
classes; keywordize; authority/class-budgeted ranking; read-in-full; **decisive-source hunt +
chase-the-primary (highest-leverage)**; the two-layer verification *shape*; skills-only architecture;
LLM-judge-over-numeric for eval.

## Cross-cutting: the audit caught its own tool's failures
This run dogfooded Aletheia on itself and surfaced, live: the `_anchor` query pollution, the
semanticscholar rate-limit fragility + keyword-recall gap (decisive sources often came via direct
WebFetch, not the pipeline), the subagent `findings.md` write-block (workers used `treestate.py
findings` or inline return), and the Reddit class contradiction. These are the strongest signals
because they're observed, not argued.

## Gaps / honesty
- **Domain transfer:** the budget verdict rests on LLM-reasoning test-time-compute papers (tokens/
  samples), not a direct study of research-budget-over-a-question-tree — strong analogy, not identity.
- **No controlled head-to-heads** exist for skills-vs-framework, DOK-partition, or equal-vs-weighted
  time-per-level — those verdicts rest on authority + practitioner consensus, not RCTs.
- **Channel degradation during the audit** (semanticscholar 429, openalex/HN 0 on long queries) means
  the CS-citation-graph and practitioner-forum voices are under-sampled; several decisive primaries were
  reached via WebFetch. So the audit *itself* was run on a partially degraded toolkit — fittingly, the
  thing recommendation #5 is about.
