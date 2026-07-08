# Surveyor — design (rebuilt from the self-audit)

**Status:** built (surveyor 0.1.0). Supersedes and retires `aletheia` (v1) and `deep-aletheia` (v0.2).

## Why a fresh skill
A full self-audit of `deep-aletheia` 0.2 — grounded in expert/practitioner sources (X, Reddit, HN)
and papers, not just the papers it was built on — found real flaws that warranted a clean rebuild:
- **"Simpler AND deeper" was overclaimed:** 0.2 was a net-larger strict superset, "deeper" rested on
  one hand-driven run, and its flagship verifier **never completed** (`citation_accuracy: null`).
- **The budget model was FLAWED:** conserved-B/K "equal scrutiny per leaf" is uniform allocation,
  which the adaptive-compute literature shows wastes compute (~12.8% worse at matched budget) and
  contradicts Anthropic's "scale effort to complexity"; worse, it made deep leaves single-pass —
  reproducing the exact shallow-leaf flaw it claimed to fix.
- **Multi-agent tree unproven:** the strongest current evidence leans single-agent for the core loop
  (OpenAI Deep Research = one RL-tuned agent; HF smolagents replica 55% vs 67% GAIA with one agent;
  Step-DeepResearch: single beats orchestration; Tran & Kiela: SAS ≈/≥ MAS at equal tokens, incl.
  subtask-parallel; MAST: 41–87% MAS failure). Multi-agent earns its cost only for **independent
  breadth** (Anthropic +90.2% breadth-first).
- The **filesystem blackboard** and **anti-anchoring** graded SOUND and are kept (reimplemented light).

## Principles
1. **Single-agent by default.** Fan out to read-only workers ONLY at `deep`/`exhaustive`, one per
   angle, for independent breadth — never a recursive tree.
2. **Scale effort to complexity** via a thoroughness dial, not a uniform per-item budget.
3. **Verification must complete** and report a real number.
4. **Read in full, cite primaries, judge independence, attack the leading conclusion.** The human owns
   the final call.

## Shape
One skill: `.cursor/skills/surveyor/` = a short callable `SKILL.md` (the 7-step loop + tier table +
invocation) and one driver `surveyor.py` (`plan|gather|deepen|independence|verify|score`) that owns
deterministic state in a **flat** run dir; the calling agent supplies judgment. Reuses only the
low-level utilities (channel clients, `read.py`, `rerank.py`, `dedupe.py`, independence) — not the
retired orchestration.

**Thoroughness tiers** (effort scales to the question; `auto` scopes then picks):

| tier | angles | channels | reads/round | deepen rounds | fan-out | verify | adversary |
|---|---|---|---|---|---|---|---|
| quick | 1–2 | 2 | 5 | 0 | no | light | no |
| standard | 2–3 | 3 | 6 | 1–2 | no | full | yes |
| deep | 3–4 | 3–4 | 6/angle | 2 | yes (1 worker/angle) | full + subagent | yes |
| exhaustive | 4–6 | 4+ | 8/angle | 3 | yes | multi-vote | yes |

**Loop:** SCOPE (angles incl. one disconfirming; auto picks a tier) → GATHER (retrieve → authority-rank
→ read in full; class-budgeted) → DEEPEN (reflect → drill gaps; stop on convergence) → INDEPENDENCE
(echo/one-origin check) → ADVERSARY (attack the leading angle) → VERIFY (relevance layer + LLM
entailment on every claim) → ANSWER (Agreement/Disagreement/Unverified, every claim → primary).

## Improve over time
`scripts/eval/eval_compare.py` scores any run (surveyor flat OR the retired tree layout) on a shared
rubric (citation accuracy, source quality, independence, sources/reads, brief completeness) so gains
and regressions are measured against the retired baselines, not asserted. `topics.jsonl` is a fixed,
contamination-aware set for repeatable comparison as the skill iterates.

## What we deliberately did NOT carry over
Recursive `treestate` tree; conserved-budget "equal scrutiny per leaf" currency; the 120-char `--gate`;
a mandatory rigid 4–6 portfolio on every topic; and any "better" claim without the eval to back it.
