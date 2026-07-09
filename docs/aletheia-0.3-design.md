# Aletheia 0.3 — design

**Status:** built (aletheia 0.3.0). Built **off deep-aletheia 0.2** (its direct ancestor).
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
- Filesystem-as-blackboard; resumable; auditable. Engine reused verbatim, copied into
  `.cursor/skills/aletheia/scripts/` (deep-aletheia 0.2 left frozen as an eval baseline).

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
