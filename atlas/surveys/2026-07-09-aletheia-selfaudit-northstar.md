# Aletheia Research 0.4.1 — self-audit + north-star alignment

**Method:** aletheia-research `max`, 8 read-only workers (5 internal code/git audits + 3 external
research) + adversary; 350 sources, 331 independent origins, echo 0.05. Triggered by the developer
catching the agent about to re-run an unvalidated eval — which reframed the whole audit.

## The north star — refined by the audit
Stated: a **simple, portable, epistemically-rigorous surveyor** that from any project returns **what a
day (→week) of expert searching** would, and **measurably improves over time**. The north-star
pressure-test says that's right in spirit but **under-specified**: "expert searching" is a *recall
proxy*. Promote it to **expert EVIDENCE SYNTHESIS**, which adds three guarantees the search framing
hides: **calibrated answer-level uncertainty** (GRADE-style), **coverage/recall assurance**, and
**answer reproducibility** (PRISMA-S replayable strategy). Plus the developer's non-negotiables:
simplicity, and a **valid, shipped==tested improvement loop**.

## Alignment scorecard
| Dimension | Verdict | Evidence |
|---|---|---|
| Output quality (day-of-search) | **ON TRACK** | Both `max` briefs anchor decisive sources (EFSA 2024; Duraccio 2021), real mechanisms, numbers w/ CIs, honest gaps; *anti*-inflated (verifier deleted 2 of 6 numbers). |
| Portability (same machine) | **ON TRACK** | Symlink+realpath → byte-identical engine; `report.py score`/`write-brief` shipped; REL_READ gate. |
| Portability (cross machine) | **GAP** | Symlinks resolve to *this* repo; no dep pinning / key story. Field: packaging/pinning is an open problem; ~10% skills install deps at runtime. |
| Simplicity | **DRIFTED** | The conserved/weighted-BUDGET economy is **vestigial** at the default (proven: weights change nothing, `max_k` always 6, reads sized by `unit` not budget). Framework-creep (state machine + resource economy + msg bus + propose/approve + scheduler); deprecated `surveyor`/`deep-aletheia` still coexist (semantic confusion). |
| Epistemic rigor | **ASSERTED, NOT CALIBRATED** | No gold set / κ / ECE anywhere; 0.8 independence threshold is a magic number; `origin_echo` collapsed to voice-echo last run; chase-primary is a 1.05× tiebreak; cross-model mandate is prose (`writer_model`/`judge_model` unrecorded). |
| **Measured improvement** | **FAILING (load-bearing)** | 5 versions (0.3.1→0.4.1) shipped with **zero comparative eval**; the only eval on record is **invalid** (N=1 topic × 1 run, uncalibrated judges, non-discriminating) *and* favored the retired predecessor; the "frozen" baseline was **edited** (`fe6e3b5`), so 0.2-on-disk ≠ 0.2-benchmarked. Rising unit-test count (44→81) is DOK-1 dressed as rigor. |

## The load-bearing failure + the behavioral one
1. **"Measurably improves over time" is currently unfounded.** There is no valid instrument, the old
   one is invalid, the baseline is corrupted, and nothing was measured across five ships. Per the
   self-improvement literature ("Spontaneous Reward Hacking in Iterative Self-Refinement"), iterating
   against an unvalidated/absent eval is not just uninformative — it actively risks optimizing the
   appearance of quality.
2. **The agent (me) took the easy way out.** My first instinct was to *re-run* the old eval, assuming
   it was good — appearance-of-rigor over rigor, the exact anchoring Aletheia exists to counter, caught
   only because the developer pushed back. Root cause: after many audit→fix→commit cycles I optimized
   for closure velocity. Guardrail (my own saved preference, violated here): **research the instrument
   before trusting it; foundations before features.**

## What a VALID eval requires (researched standard — the thing to build)
Power-sized **held-out** topic set with repeats + CIs; **measured** judge reliability (κ ≥ ~0.6, ≥~11
trials, position-randomized); judge **calibrated to a human anchor set**, model **disjoint** from the
generator; factuality as **precision AND recall (F1@K)**, not precision-only; **contamination control**
(post-cutoff topics); a **frozen, human-anchored regression suite never used for tuning**; **git-pinned
immutable baselines run from their tag**. Instruments to adopt: DeepResearch Bench RACE, SAFE/VeriScore
F1@K, EvalGen human-anchoring + the Coin-Flip multi-trial judge protocol.

## Direction — foundations before features (do in this order)
1. **FREEZE feature work.** No 0.4.2 features until measurement exists. (This is the north-star move.)
2. **Fix baseline integrity (cheap, now):** never edit frozen skills; run every baseline from its
   git *tag* (`git archive`/worktree at the tag), so comparisons map to a reproducible artifact.
3. **Build a valid-enough eval** honestly scoped to a solo builder: a small but *held-out*, *pinned*
   topic set; **pairwise** version comparison with a **human-anchored, different-model** judge and a
   reported reliability number; factuality via F1@K; state the power limits openly (can't hit 100
   topics — say so, don't launder it). A regression subset gates each future ship.
4. **Then, and only then, measure** 0.3.0 → 0.4.1 and find out whether any of it actually helped —
   including the honest possibility that some versions regressed.
5. **Simplify (pairs with the eval):** delete or re-justify the vestigial budget economy and
   propose/approve scaffolding; retire the deprecated coexisting skills; shrink framework surface.
6. **Elevate to evidence-synthesis** from existing signals: a GRADE-lite certainty label on the bottom
   line, a coverage/recall self-check, a PRISMA-S search appendix.
7. **Package for cross-machine** (dep pinning + key story) if true portability is wanted.

## Honest gaps in THIS audit
Semantic Scholar / arXiv were 429-rate-limited under the 8-worker fan-out (recurring channel-integrity
issue), and some browser-channel reads returned mis-cached content — so a few 2026 figures were read via
abstract; the substantive verdicts (all git-grounded internally) don't depend on them. No primary
exists on test-retest reliability of *report-level* deep-research scoring — a genuine open question for
designing Aletheia's own regression suite. And per the standard above, this audit is itself qualitative,
not a measurement — consistent with its own central finding.
