# Aletheia Research 0.3.1 — deep per-component / per-step self-audit

**Date:** 2026-07-08 · **Method:** aletheia-research 0.3.1 at `exhaustive` — 12 parallel READ-ONLY
worker subagents, one per component/step + a dedicated adversary; each grounded its verdict in BOTH
the live source code AND external literature via the channels. Root subtree: **336 sources, 175
independent origins, origin_echo 0.479, 94 domains, 7 index-groups, 297 evidence-class.** Run:
`runs/aletheia-research/2026-07-08-2139-self-audit-031-deep/`.

## Bottom line
The **architecture is sound and survived the adversary** — read-only breadth is the case both the
leading proponent (Anthropic) and the leading critic (Cognition; MAST) explicitly endorse/exempt, and
the topology, filesystem coordination, decisive-source discipline, and two-layer verification *shape*
all hold. **But every one of the 0.3.1 fixes is now graded `improvable`, not `sound`** — the audit,
verifying against the actual code, found each fix is directionally right yet either has a residual bug,
is unvalidated, or introduced a new failure mode. **9 of 12 units = improvable, 0 sound-as-is, 0
proven-bad; 1 sub-claim (the 0.8 shingle threshold) = no-basis.** The single most important truth: the
whole promotion of this design still rests on an **N=1 blind bake-off**, and no fix has been validated
head-to-head. **6 concrete code bugs were reproduced deterministically** (below) — those are the
highest-confidence, immediately-actionable output.

## Verified code bugs (reproduced by the orchestrator, independent of the workers) — 6/6 CONFIRMED
| # | Bug | Repro | Bites which 0.3.1 fix |
|---|---|---|---|
| B1 | **Weighted split silently vanishes at tight budget:** when `B = K·U` the remainder is 0, so every child gets exactly `U` regardless of weight — still logged "weighted". Weightable fraction `1−U·K/B` shrinks with depth (least effect at the finest splits). +rounding drift (Σ=32.001). | `B=8,U=4,w=[3,1] → [4.0,4.0]` | #1 budget |
| B2 | **build_clusters false-merges distinct primaries:** the near-dup shingle rule (rule 4) merges two papers with **different DOIs** if title+snippet shingles overlap ≥0.8 — it *overrides* voice_key's DOI-distinctness. Violates the "keeps distinct primaries" guarantee. | identical title, empty snippet, DOIs `10.1/a`≠`10.1/b` → **1 origin** | #2 independence |
| B3 | **voice_key over-merges author-less works:** the `"dom::"+domain` fallback collapses distinct anonymous same-domain pages into one voice; the `PLATFORM_DOMAINS` guard meant to prevent this is **dead code**. Under-counts origins for web scrapes (this run's Brave records had no authors). | two distinct `site.example` pages → same voice key | #2 independence |
| B4 | **Lexical verify prefilter drops true support:** a genuinely-supported *paraphrase* (synonyms, no stemming: `caloric`≠`calorie`) scores 0 overlap → `off_topic` → dropped before the LLM ever sees it. And `score_run` files `off_topic` in `bad`, excluded from the denominator → the dropped-true claim **vanishes, biasing precision optimistically.** Threshold 0.30 uncalibrated. | paraphrased true-support → `off_topic` | #3 verification |
| B5 | **Router substring mis-scope:** `kw in text` matches inside words — "general strategy" → biomed (via "gene"), "start a startup" → humanities (via "art") — firing wrong primaries, dropping arxiv/github; no confidence/abstain path. | `classify("general strategy…") → biomed` | (router, unchanged) |
| B6 | **_anchor trades proper-noun pollution for fragment noise:** the coined-topic fix works (drops "Aletheia") but short sub-questions get a `"deep component step"` prefix (hyphen-split `per-component`/`per-step`); the ≥5-term "self-contained" bypass passes long multi-topic queries through **uncleaned** → live, 3 of 4 in-full reads were off-topic. | `_anchor("adherence over time", topic) → "deep component step adherence over time"` | #5 retrieval |

## Per-unit verdict
| Unit (component/step) | Verdict | 0.3.1 fix status |
|---|---|---|
| **Budget model** (weighted split) | improvable | weighting swapped uniform-*static* for weighted-*static*; literature (fixed-budget best-arm-ID) says static is optimal only when evidence can't redirect effort — research is the adaptive regime. Basis is analogy-only (Snell); contestedness is the wrong weight (EVOI/difficulty is). **+bug B1.** |
| **Tree topology + resumable frontier** | improvable | topology **well-founded** (Anthropic + Cognition read-only exemption; avoids MAST inter-agent-misalignment). `--resumable` genuinely fixes the leaf-phase crash-skip with **no double-count on resume** — but I *overstated* it: a leaf crashing after gather but before authoring `findings.md` stays `investigated` (indistinguishable from success) and is NOT re-picked; split-synthesis crashes likewise. max_children 3–5 corroborated; max_depth/nodes = cost guards, no external basis. |
| **Router** | improvable | unchanged; prior "no abstain/confidence path" still open + **bug B5**; `exclude=` taxonomy is effectively dead (never filters channels). Evidence: trained TF-IDF/uncertainty-driven routers win; hand-rules worst. |
| **Investigate engine** | improvable | `_anchor` bug fixed but **bug B6** residual; truncation now flagged but 40k cap has no CLI override; reads top-K in full *before* any relevance gate, so a bad query burns read slots; append-only memory (no pruning/folding vs WebWeaver/ReSP). `_work_key` dedup **sound**. |
| **Authority ranking** | improvable | domain-as-credibility is the right unit, but a ~60-domain hand list is structurally coverage-limited; the biomed patch fixed one adjacent field, not the CS-bias generally (law/econ/humanities + all non-US/UK academia still 0.5). `europa.eu` credits the whole EU domain; no `tldextract` → `gc.ca` mis-parses; `student.stanford.edu`→1.0 via `.edu`. Field says augment curated core with link-based signals. |
| **Structural independence** (build_clusters) | improvable; **0.8 threshold = no-basis** | fixes verbatim syndication but defeated by ordinary headline/lede rewriting (title+snippet only, never body) → net **under-detection = false confidence**; **bug B2** false-merge; 0.8 is an uncalibrated magic number (Broder: "half science, half black magic — calibrate"); shingling is lexical, degenerate on ~20-word snippets. **On THIS run it added only ~2 merges over 336 sources — near-zero effect on a distinct-paper corpus.** origin_echo is the right *headline concept* (bibliometrics), weakest possible *signal*. |
| **Dedupe + synthesis ask/answer gate** | improvable | gate still partly **ritual**: `_answered()` clears on any one-char answer, the "answer" re-uses already-gathered sources (no new retrieval), 120-char proxy arbitrary. The ASK is grounded (MAST FM-2.2/2.4); the ANSWER should DEEPEN with new retrieval (AgentCPM WARP). **+bug B3.** bottom-up merge sound. |
| **Two-layer verify** | improvable | two-layer *shape* matches NLI/FactScore/SAFE, but the lexical layer as a **hard gate** is unsound (**bug B4**); its own cited source ("Cited but Not Verified") computes Link/Relevant/FactCheck in *parallel* — relevance never gates FactCheck. |
| **score_run + cross-model judge** | improvable | genuine improvement (precision+coverage+denominator, null-until-complete) but **precision has no recall/omission penalty** and the denominator is **writer-extracted from its own draft** → a hedged brief scores 1.0/complete while dropping disconfirming evidence; **cross-model judge is unenforced** (no `writer_model`/`judge_model` recorded in code — it's prose); still **uncalibrated** (no κ vs a human set). |
| **Channels + doctor** | improvable | **recall cliff reproduced live**: free APIs boolean-AND terms, so 5-term queries → 0 results; `keywordize` drops salient rare terms; no 0-result relaxation. `doctor` **false-greens** (2-word probes never trip the AND-cliff; single-request probes miss rate-limit collapse under fan-out). DDG shares Bing with Brave (fake diversity). Coverage holes: patents, legal, gov-data, news-archive, non-English, preprints beyond arXiv. BEIR: "just add neural" is not a clean win — fix keywordize first. |
| **7-step loop** | improvable | ingredients grounded, but the **rigid linear sequence is contra-SOTA** — WebWeaver/AgentCPM/ScaffoldAgent all *interleave* structure/synthesis/grounding with retrieval; the weakest step is decompose-before-evidence (the SKILL front-loads framings, though `propose_split`/`materialize` do allow a scout-driven split — the tension is real). Add a light in-loop grounding signal; keep the terminal completion-gate. |
| **Adversary** | F1 DOWNGRADED | "0.3.1 closed the gaps; design sound" → **"read-only breadth is defensible, but the fixes are unvalidated ceremony and the promotion is N=1."** Strong on validation, weak on topology: Tran & Kiela's own boundary condition (MAS wins in degraded/noisy-context — the survey regime) + MAST/Cognition read-only exemption mean the topology survives; the strongest surviving attack is that **Aletheia has never run itself vs a single-agent RAG loop at equal token budget** — the one test that would earn "sound". |

## Did the 0.3.1 fixes hold?
- **#1 weighted split** — partial. Correct direction, but weighted-static (not adaptive), analogy-only basis, +bug B1.
- **#2 structural independence** — weakest. Right concept, but +bug B2 (false-merge distinct DOIs) & B3 (author-less over-merge), no-basis threshold, near-zero effect on this corpus, still blind to paraphrase echo.
- **#3 verification hardening** — partial. Real improvement, but +bug B4 (silent true-support drop biases precision up), no recall, writer-chosen denominator, cross-model unenforced, uncalibrated.
- **#5 retrieval bugs** — partial. `_anchor` proper-noun bug fixed but B6 residual; S2 backoff present but **S2/arXiv still 429'd under this run's 12-way fan-out** (doctor showed 12/12 live); biomed authority added but structurally still a static list.
- **#6 resumable frontier** — mostly. Fixes the leaf-phase crash-skip with no double-count; overstated for findings-authoring / split-synthesis crashes.
- **#7 labels** — held (no regressions found in the label/diversity/Reddit-class changes).

## Cross-cutting themes (the real leverage)
1. **Keyword-recall is the dominant systemic weakness** (router B5 + channels AND-cliff + keywordize dropping rare terms + investigate B6 + no 0-result fallback all compound). This, not the tree, is what most limits source variety — and it degraded THIS audit.
2. **Uncalibrated magic numbers everywhere** (0.30 verify, 0.8 shingle, 60/25 read quotas, 120-char gate) — none tuned on labelled data.
3. **Static where the literature says adaptive/learned** (budget allocation, authority list, router rules).
4. **Silent drops bias metrics optimistically** (verify off_topic → score_run denominator; writer-chosen claim set).
5. **The architecture is fine; the instrumentation around it is unvalidated.**

## Recommendations (ranked)
1. **Fix the 6 code bugs** (all cheap): B2 guard — never let the shingle rule merge distinct DOIs; B3 — wire up or delete `PLATFORM_DOMAINS`; B4 — route load-bearing low-overlap claims to the LLM anyway (don't let `off_topic` be terminal) + count them in the denominator; B1 — warn/redistribute when `rem≈0`, fix rounding; B5 — word-boundary matching + widen-to-general abstain; B6 — clean the anchor tokens + don't equate length with on-topic.
2. **Run the one experiment that would settle "sound":** Aletheia (deep) vs a single-agent RAG loop at **equal token budget** on the eval topic set; report completeness/groundedness/independence. Until then, stop calling the fixes validated.
3. **Calibrate the thresholds** (0.30, 0.8, quotas) against a small human/LLM-labelled set; compute judge κ. Feed independence a body/abstract or sentence-embedding signal, not 20-word shingles.
4. **Attack keyword-recall before paying for neural:** salience-aware keywordize + 0-result relaxation; route CS to OpenAlex/S2 over rate-limited arXiv; add free GDELT/PatentsView/CourtListener/WorldBank/bioRxiv; make `doctor` probe realistically (multi-term + under concurrency).
5. **One adaptive budget upgrade** reusing the existing scout round (successive-halving: reallocate from settled to still-contested children post-scout); reframe weight as EVOI.
6. **Record `writer_model`/`judge_model`** in run.json so the cross-model mandate is code-gated, not prose.

## Gaps / honesty
- **The audit degraded itself.** The 12-way concurrent fan-out rate-limited the free academic channels (arXiv/Semantic Scholar 429, OpenAlex 400) even though `doctor` showed 12/12 live — so scholarly variety was under-sampled and several primaries were reached via direct WebFetch, not the pipeline. This is bug-class B5/channels, observed live for the second audit running.
- **Literature claims not independently re-verified.** The 6 CODE bugs are reproduced deterministically (high confidence). The external-literature verdicts rest on the workers' reads; several cited arXiv IDs are 2026-era (beyond the orchestrator's knowledge and unre-fetchable under the rate-limiting) — treat specific IDs as worker-reported, not orchestrator-verified. One anchor the design itself cites (UAB 2605.26849) a worker could not confirm.
- **Still N=1.** No controlled head-to-head exists for weighted-vs-adaptive budget, tree-vs-single-agent, or the threshold settings; all rest on analogy + practitioner consensus.
- **origin_echo ≈ voice echo on this corpus** (175 vs 177 of 336) — the flagship independence fix had near-zero effect here because the corpus is distinct papers, not syndicated news; its value is real but topic-dependent.
