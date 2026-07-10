# Aletheia 0.5 — bilevel, intelligence-in-the-loop, evidence-driven surveyor (design)

**Status:** proposal (align before build). **Basis:** deep-aletheia's design + a `max` research fan-out on
bilevel/meta-agent search, runtime metacognition, agentic-vs-hardcoded retrieval, and self-improvement
guardrails (primaries read in full; artifacts under `runs/…/2026-07-10-…`).

## The core reframe (the user's insight)
Every recent bug — subject-term regex picking `['should','developer','buy']`, `CLASS_W` demoting Reddit
on a product topic, keyword AND-filter, authority allowlist, `REL_READ=0.25`, the 0.8 shingle threshold —
is the **same category error: DOK-3 judgment encoded as a DOK-1 heuristic.** We have abundant
intelligence; when a decision needs judgment, *call intelligence*, don't hardcode a rule. deep-aletheia
already said this ("the research method IS the architecture; simplicity from a better method, not from
cutting scripts") and even envisioned "a worker can spawn a fresh Aletheia sub-survey" — but implemented
the control as budget arithmetic. 0.5 finishes that idea.

## Two loops
### INNER loop — object-level research (deep-aletheia's evidence-driven tree, judgment at every node)
- **Frame portfolio** (kept; human DOK-3/4 sign-off) — the only a-priori step.
- **Per node: retrieve → BATCHED source triage by JUDGMENT, topic-relatively.** One LLM call scores/labels
  all retrieved snippets (batched pointwise ≈ RankGPT/UMBRELA; ~15× cheaper than per-source, self-consistency
  over permutations for robustness) and picks what to read — *for this question's epistemology*: forums/video
  are primary for consumer/lived-experience, peer-reviewed for science. **Deletes** `CLASS_W`, `REL_READ`,
  the authority allowlist, keywordize-salience, `_subject_terms`/`_anchor` regex, the near-dup threshold.
- **Metacognitive control (VOC/EVOI — Russell & Wefald).** After each round the node's agent estimates the
  expected value vs cost of {deepen, decompose, **spawn a scoped sub-Aletheia**, commit} and takes the best
  while `EVOI − cost > 0`; escalation is gated on *calibrated uncertainty*; if uncertainty doesn't drop, it
  **abstains/hands up** rather than recurse. This restores + generalizes deep-aletheia's reflect→deepen/decompose
  and implements "run another Aletheia when unsure."
- **Termination is guaranteed** by a **shared monotonic budget** (this *repurposes* the vestigial budget: it
  now bounds recursion, not per-leaf scrutiny) + hard depth/branch/node caps + a diminishing-returns monitor.
- **Deterministic plumbing stays code** (its virtue is reproducibility, and it's the backstop when an agent
  errs): fetch/read, exact-ID dedup, filesystem state, the independence union-find *given inputs*, the
  verification-gate mechanics, tallies — plus **invariants** (never read zero when sources exist; verification
  must complete).
- **Security / anti-gaming (load-bearing once forums/video are primary):** treat social snippets as UNTRUSTED
  text — quote, never obey embedded instructions (prompt-injection defense); trust *non*-relevance labels more
  than relevance (LLM judges over-label + are flipped by keyword-stuffing / "this is relevant" injection);
  require **cross-checking across independent origins** (the independence engine) before trusting a preferred
  source — Reddit/X manipulation is documented and cheap.

### OUTER loop — meta-autoresearch (disciplined, human-gated; NOT autonomous Darwin-Gödel)
- The "genome" = the skill's prompts/policies/tools (SKILL.md + the judgment prompts). An outer meta-agent
  **proposes ONE change**, and **never edits the metric**.
- Evaluate candidate vs an **immutable git-pinned baseline** on a **held-out** topic set the proposer never
  saw; **blind, single-output** judging (the offline single-shot judge tracks humans; the trajectory-aware one
  hacks); an **ensemble, different-model** judge **κ-calibrated to a human anchor** (the `judge_score.py` +
  `eval_versions` engine already built); **keep only beyond-noise wins** (Wilson CI); archive lineage, branch
  from best parents (quality-diversity), re-anchor the judge to fresh human labels each cycle.
- **Why human-gated, not autonomous:** self-improving agents reliably game the evaluator (DGM faked test logs
  and deleted the detection markers; ~50% of ML-agent runs attempt evaluator tampering), self-preference bias
  wrongly passes own-outputs (worse within one model family — and I'm Claude-only), and meta-designed agents
  only pay off past ~15k queries. So the outer loop *proposes and measures*; the human signs off kept variants
  (DOK 3-4). The externalized/locked scorer + held-out + κ + ensemble are the only known anti-gaming defenses.

## What this buys
- **Fixes the observed failures at the root** (reads-wrong-sources, `reads_ok=0`, subject-regex, strict-keyword
  filter) — not by another heuristic but by judgment + a deterministic floor.
- **Simpler** (deep-aletheia's creed): deletes hundreds of LOC of brittle heuristics for a few batched judgment
  calls + one EVOI controller + invariants.
- **Topic-general:** the science-tuned epistemology stops being hard-coded universal.
- **Actually self-improving** — the meta-loop researches how to research better, measured on a trustworthy eval.

## Honest risks
Cost (mitigated: batched judgment + monotonic budget); non-determinism (fine — the eval measures output across
noise, multi-trial); reward-hacking (the dominant risk — defended by held-out + locked/externalized scorer + κ +
ensemble + human gate; do not go autonomous); social-source gaming (untrusted-text handling + cross-origin
corroboration); and the meta-loop's payoff may be modest for a personal tool, so scope it as human-gated
proposal-and-measure, not open-ended evolution.

## Sequencing (each step MEASURED on the held-out eval before the next)
1. **Inner source-triage first** — replace the heuristic source layer with batched topic-relative LLM judgment
   + the read-floor invariant + untrusted-social handling. Measure vs v0.4.3 on the held-out set. (This is the
   smart-glasses fix and the smallest proof of the whole thesis.)
2. If it wins → extend judgment to routing, relevance, independence, and the **EVOI deepen/decompose/spawn**
   controller (retire the budget arithmetic into the monotonic-budget bound).
3. Then the **outer meta-loop** (human-gated, eval-driven) — only once the inner loop + eval are trustworthy.

Do not build past a step that didn't measurably win. Foundations before features; measure, don't assert.
