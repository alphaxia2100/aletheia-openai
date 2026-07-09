# Aletheia 0.3 — design

**Status:** built (aletheia-research 0.3.1). Built **off deep-aletheia 0.2** (its direct ancestor).
Supersedes `surveyor`; the `aletheia` name is rebased from the retired v1 onto the deep-tree line.

## Why 0.3 is built on deep-aletheia 0.2
A blind, order-randomized, 5-judge LLM-as-judge over **fresh** runs (creatine → cognition;
`docs/evals/2026-07-08-creatine-cognition-bakeoff.md`) found deep-aletheia 0.2 beat the single-agent
`surveyor` on **completeness, source variety, and groundedness to distinct primaries** — because its
competing framings each retrieved independently and surfaced more distinct primary sources, with real
multi-round surveying and honest gaps. That is the behavior worth keeping, so 0.3 is its successor,
not a rewrite.

## What 0.3 keeps from 0.2 (the good parts)
- **Multi-perspective portfolio tree** (anti-anchoring) → a *variety* of distinct sources.
- **Real multi-round surveying** (investigate accumulates across rounds; deepen into gaps).
- **Evidence-driven decomposition** (split when a scout round shows sub-questions).
- **Bottom-up synthesis with an enforced ask/answer gate** (parents ask thin children).
- **Adversary** (attack the leading framing) + **independence/echo** judgment.
- **Honest gaps** (paywalled primaries, empty channels, missing large RCTs stated).
- **Verification that runs to completion** (lexical relevance → LLM entailment → real citation_accuracy).
- Filesystem shared-artifact store (each node is a directory); resumable; auditable. Engine reused
  verbatim, copied into `.cursor/skills/aletheia/scripts/` (deep-aletheia 0.2 left frozen as a baseline).

## Anchoring (both skills were run on the design question)
Decisions were anchored by running **both** skills on "how to architect a survey agent for
complete/grounded/varied briefs": a `surveyor` pass (86 sources) and — richer — a **deep-aletheia 0.2**
pass (122 distinct works, echo_ratio 0.238, verification 0.917; it caught an overclaim, flipping
"LangChain ships multi-agent" to *unsupported* because that version is deprecated to `legacy/`). The
deep-0.2 anchor **confirmed** this design: its "single-agent-invisible" recommendations (verification
gate, independence/echo checking, adversary pass) are exactly what 0.3 keeps from 0.2, and its other
recs map onto 0.3's four additions. It reframed the real lever as **diverse perspectives + shared
context/tokens, not agent count** (token usage ≈ 80% of BrowseComp variance) and added two sharpenings
now folded into the SKILL: **filter for relevance before spending the read budget**, and
**health-check + broaden channels** (that run lost GitHub/HN/StackExchange/Marginalia to 0 results).
Run: `runs/deep/2026-07-08-1922-survey-agent-arch/`.

## What 0.3 adds (anchored by the judge + the self-audit + surveys run with BOTH skills)
1. **Hunt the decisive source.** The single-agent design's *only* win was finding the authoritative,
   question-settling source (the EFSA regulator opinion) that 0.2 missed. 0.3 makes "find the
   regulator opinion / landmark SR-MA / largest RCT" an explicit step, not an accident of retrieval.
2. **Chase the primary, never cite the secondary.** Both prior designs occasionally cited a
   blog/summary (Examine/Healthline) for a load-bearing claim. 0.3 requires finding the primary or
   marking the claim Unverified.
3. **Wider source variety by design.** Cover multiple index-groups per framing (independent web ·
   academic · community · code/QA where relevant), so distinct origins surface rather than one echoed.
4. **Thoroughness dial** (`treestate.py init --thoroughness quick|standard|deep|exhaustive`, plus
   `auto`), which sets the tree's budget/caps — making it callable and scaled from any session, and
   scaling effort to the question rather than a fixed budget.

## Shape (unchanged spine + the dial)
`.cursor/skills/aletheia/` = `SKILL.md` (the 7-step loop) + `scripts/` (`treestate`, `investigate`,
`router`, `rank`, `synthesize`, `verify`). Loop: frame portfolio → decompose tree → investigate
leaves (multi-round, wide, primary-first, decisive-source hunt) → synthesize bottom-up with ask/answer
gate → independence + adversary → verify to completion → grounded brief with gaps → Atlas. At
`deep`/`exhaustive`, leaves are investigated by parallel read-only worker subagents (breadth).

## Honestly unresolved / next
- **"Better" is judged on N=1 topic.** The promotion rests on one blind bake-off; the honest next step
  is the judge across the full `scripts/eval/topics.jsonl` set (several topics × runs) to confirm 0.3
  ≥ 0.2 and that the four additions actually raise the decisive-source / primary-grounding scores.
- **Budget model.** 0.3 keeps 0.2's conserved-budget split (the self-audit flagged uniform allocation
  as suboptimal); the thoroughness dial scales the *total*, but per-branch allocation is still even.
  A contestedness-weighted split is a candidate 0.3.x improvement — deferred, not done.
  → **Done in 0.3.1** (see below).

## 0.3.1 — design self-audit fixes (2026-07-08)
An exhaustive `aletheia-research` self-audit on its own design (`docs/evals/2026-07-08-aletheia-design-
audit.md`, 472 sources; one confirmed flaw, one under-detection, tool bugs caught while dogfooding)
drove these, each traceable to a numbered recommendation:
- **Budget (audit #1): contestedness-weighted split.** `split_node --weights` distributes the
  *remainder* by contestedness after flooring each child at the scrutiny unit — budget still conserved.
  Resolves the design's own D1↔D3 contradiction (scale-effort-to-complexity vs uniform scrutiny). This
  is the deferred item above, now implemented. Grounding: Snell 2408.03314, UAB 2605.26849, Anthropic
  "scale effort to complexity."
- **Independence (audit #2): structural shared-origin.** `voice_key` counts source *identity*, so many
  domains echoing one origin looked independent. `synthesize.independence` (and `score_run`) now also
  report `independent_origins` / `origin_echo_ratio` via `provenance_graph.build_clusters`
  (canonical-url + voice + `derives_from` + near-duplicate shingles). Low identity-echo no longer
  licenses "Agreement."
- **Verification (audit #3): real & code-gated.** `citation_accuracy` = precision, reported only once
  `citation_complete` (coverage = 1.0), with a stated denominator; a different judge model than the
  writer is mandated (self-preference bias). Not an honor-system SKILL line — the score is null until
  the pass finishes.
- **Diversity (audit #4): structural, not asserted.** Each framing must be grounded in a distinct
  source base / channels; framings that retrieve the same sources are merged (mode collapse:
  Persona-Generators 2602.03545, Verbalized-Sampling 2510.01171).
- **Retrieval robustness (audit #5):** `_anchor` no longer pollutes on proper-noun/coined topics or
  over-anchors self-contained questions; reads flag truncation at the 40k cap; `semanticscholar` gets
  exponential backoff; `AUTH_HIGH` gains biomed/regulatory venues + wire services (the CS-bias fix).
- **Resumability (audit #6):** `frontier --resumable` re-picks crashed-mid-round `active` nodes.
- **Labels (audit #7):** dropped "equal time per level" (breadth-first is a scheduling order, not an
  equal-time promise); "blackboard" → "shared-artifact store"; fixed the Reddit color/lead_gen
  contradiction.

## Honestly unresolved after 0.3.1
- The budget verdict rests on LLM-reasoning test-time-compute papers (tokens/samples), not a direct
  study of research-budget-over-a-question-tree — a strong analogy, not identity. The weights are
  agent-judged from the scout round, not learned.
- No controlled head-to-head yet confirms weighted > uniform *for this task*; the eval across the full
  topic set (the N=1 caveat above) is still the honest next step.
- The LLM judge is now cross-model but still **uncalibrated** against a human-labeled set (audit noted
  κ calibration as the remaining verification gap).
