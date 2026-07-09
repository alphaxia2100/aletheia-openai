# Head-to-head review — Surveyor vs. the retired skills

**Question surveyed:** *Does creatine monohydrate supplementation improve cognition in healthy adults?*
**Date:** 2026-07-08

---

## 1. What was run

Three skills, each executed **fresh in its own isolated agent** following **only its own `SKILL.md`**, on
the same question, with live retrieval/reading. No skill saw another's work; none reused my earlier
hand-written briefs.

| # | Skill | How it ran | Reads / sources | Verification |
|---|---|---|---|---|
| 1 | **surveyor 0.1** (current) | single-agent, `standard` tier, 3 gather rounds | 17 reads / 96 indexed | citation_accuracy **1.0** (14/14) |
| 2 | **deep-aletheia 0.2** (retired) | single-operator tree, 3 framings × 2 rounds | 20 reads / 76 indexed | citation_accuracy **1.0** (13/13) |
| 3 | **aletheia v1** (retired) | single-agent 8-step loop | 8 reads / 73 indexed | (v1 has no verify gate) |

Then a **blind, order-randomized, 5-judge LLM-as-judge** on the de-identified briefs (skill names and
process tells stripped), scoring accuracy / completeness / calibration / groundedness / usefulness.

**Caveats (read these before trusting the result):** N=1 topic, one run per skill; much of the gap is
*which sources each run happened to find* (retrieval luck), not architecture; I did the
de-identification (small bias risk); and the judges are LLMs.

---

## 2. Result of the blind judge

| skill | 1st-place votes | Borda | overall mean | acc | complete | calib | ground | useful |
|---|---|---|---|---|---|---|---|---|
| **deep-aletheia 0.2** | **3** | 6 | **4.52** | 4.4 | 4.6 | 4.2 | 4.8 | 4.6 |
| **surveyor 0.1** | 2 | 5 | 4.00 | 4.0 | 3.4 | 4.4 | 3.6 | 4.6 |
| **aletheia v1** | 0 | 4 | 4.16 | 4.2 | 4.0 | 4.8 | 3.8 | 4.0 |

Per-judge rankings: `DA>SV>A1` · `DA>A1>SV` · `SV>A1>DA` · `DA>A1>SV` · `SV>A1>DA`

**Winner: deep-aletheia 0.2 (the one I retired), but narrowly and polarizing** — it took 3 firsts *and*
2 lasts. Scores are close (Borda 6/5/4). This is best read as **"no clear quality winner; roughly
comparable,"** not a decisive verdict.

---

## 3. Honest conclusion

- **My earlier claim that surveyor is "better" does not hold up.** A blind judge of *fresh* runs put the
  retired deep-aletheia slightly ahead; surveyor did not win. My original numeric eval
  (source-quality / independence proxies) pointed the wrong way.
- **The three are close and the result is noisy.** All three reached the correct bottom line
  (*no reliable general cognitive benefit in healthy rested adults; small memory-only effect in
  older / stressed / low-baseline people; the "brain booster" claim is not supported*). They separated
  mostly on **which distinct sources each happened to surface**:
  - **surveyor** uniquely found the **EFSA 2024 regulator verdict** + the Xu-2024 statistical critique
    (the most *decision-relevant* facts) → judges rewarded its **calibration + usefulness**.
  - **deep-aletheia** uniquely found **Sandkühler 2023** (largest RCT), the mechanistic bottleneck, and
    side-effect cost → judges rewarded its **completeness + groundedness** (its tree bought breadth).
  - **aletheia v1** had the cleanest independence critique but **missed both** decisive 2024–26 developments.
- **What the redesign actually earns:** *process* wins — simpler, single-agent, and its verification
  **completes** (real citation_accuracy, vs deep-aletheia 0.2's earlier `null`). It does **not** yet earn
  a *quality* win. I should not describe surveyor as "better."
- **To answer "which is better" for real** would need the blind judge across the **full topic set (several
  topics × a couple runs each)** to average out retrieval luck. N=1 proves nothing.

---

## 4. The three outputs (full briefs, as produced)

### Output 1 — surveyor 0.1 (`standard`)
*Run dir: `runs/survey/2026-07-08-1842-does-creatine-monohydrate-supplementatio/`*

**Bottom line:** Not established. For healthy rested adults there is no reliable evidence of a general
cognitive benefit. In Nov 2024 EFSA formally concluded no cause-and-effect relationship is established
in any domain. The one recent positive meta-analysis (Xu 2024) is a single contested source, attacked
for the same statistical error by a 2026 Commentary *and* EFSA. What survives is narrower — signals in
stressed states (acute high-dose during sleep deprivation), older adults, and low-baseline
(vegetarians); reviews find no change in the young. Safe/cheap, but "buy it to get smarter" is not
supported for a healthy adult.

**Agreement:** young healthy no clear benefit (Avgerinos 2018, PMC6093191); even the pro meta-analysis
finds null overall cognition & executive function (Xu 2024, 16 RCTs); regulator negative — EFSA Nov
2024, acute working-memory effect only at 20 g/day for 5–7 d, gone at lower doses, mechanism weak
(PubMed 39564533); evidence thin/heterogeneous (no MA feasible 2018).

**Disagreement:** Positive side = Xu 2024 (single origin), memory SMD 0.31 moderate certainty — but its
own corrigendum shows attention/processing *scores* not significant. Rebuttal: 2026 Commentary
(unit-of-analysis / double-counting error; correct re-analysis makes memory effect disappear except in
older adults) + EFSA same criticism ("no conclusions can be drawn"). Independence crux: apparent
convergence is largely Xu mirrored across /full, /pdf, PMC, corrigendum; the *independent* voices
(EFSA, Commentary, Avgerinos) lean negative. Who benefits: Xu says diseased more; EFSA reviewed
diseased and found no support (direct contradiction). Older adults suggestive but weak (5/6 positive,
only 2 double-blind).

**Unverified:** acute sleep-deprivation result reached only via a secondary summary (+ a retrieval
fault) — lead not proof; critical-perspective review login-gated; community anecdote = color.

**Gaps:** single contested pillar; dose gap (positives at 20 g/day vs typical 3–5); sleep-dep primary
+ J Nutr perspective not reached; no 2025–26 large RCT in healthy rested adults surfaced.

---

### Output 2 — deep-aletheia 0.2 (retired)
*Run dir: `runs/deep/2026-07-08-1842-creatine-cognition/`*

**Bottom line:** Mostly no for the typical case, with one narrow, well-supported exception. Ordinary
healthy young rested omnivorous adults: creatine, even at high doses for weeks, does not reliably
improve cognition. What survives is a small **memory** improvement (SMD ≈ 0.31, moderate GRADE),
concentrated where brain creatine is likely low/depleted — vegetarians, older adults, the acutely
sleep-deprived. Overall cognition & executive function: no significant effect even in the most
favorable meta-analysis. The general "brain booster" claim is not supported and is actively
contradicted by null trials.

**Agreement:** memory improves a little (16-RCT MA, SMD 0.31, memory the only moderate-GRADE domain,
PMC11275561); but overall cognition & executive do NOT (same MA, both n.s.); in ordinary young adults
null (dose-response RCT n=30, 10/20 g/day 6 wk, MDPI 13/9/1276; SR "unchanged in young"); benefit
clusters where brain creatine is low/stressed (vegetarians not meat-eaters n=128; single 0.35 g/kg
during sleep deprivation raised phosphocreatine/ATP, n=15); mechanistic bottleneck (~5% of body
creatine in brain; supplementation raises brain creatine only ~3–10%).

**Disagreement:** Does diet moderate? YES (Benton 2011: vegetarians gained, omnivores didn't) vs NO —
the **largest study to date, Sandkühler 2023 (n=123)**: "vegetarians did not benefit more." Is even the
memory effect real? pro MA reports significant memory with no publication bias, yet the largest single
RCT **missed significance on both primaries** (working memory p=0.064, reasoning p=0.327), and a
critical perspective argues "enthusiasm and commercial promotion have far exceeded the evidence."
Older-adult quality poor (5/6 positive but only 2 RCTs). Cost: more side effects than placebo (RR 4.25).

**Unverified:** a 2024 "fails to support" review was paywalled — grounded only via the critical
perspective + a Reddit paraphrase; subgroup claims rest on one MA; practitioner dosing = color.

**Independence & adversary:** key claims rest on distinct research groups (Xu, Marshall, Gordji-Nejad,
Benton, Sandkühler, Avgerinos, the dose-response RCT, a critical perspective). Leading "creatine helps"
framing attacked and **downgraded**.

**Gaps:** broad-but-shallow run; one skeptical primary paywalled; the pro MA mixes 13 healthy + 3 diseased.

---

### Output 3 — aletheia v1 (retired)
*Run dir: `runs/2026-07-08-1841-creatine-cognition/`*

**Bottom line:** Mostly no, with narrow exceptions. For a young, well-rested, omnivorous healthy adult,
best evidence does not support a reliable improvement in general cognition. Genuine positives are
domain/population-specific — memory (possibly processing speed), mainly in older adults, under acute
stress, and possibly in low-baseline people (vegetarians). These rest on a small pool of little trials
re-pooled repeatedly, several high risk-of-bias, with one key meta-analysis formally challenged for a
statistical error. Promising in niches; not established as a general enhancer.

**Agreement:** young healthy rested adults ~no benefit (Avgerinos 2018 "unchanged in young";
Prokopidis 2023 null in young SMD 0.03 vs older 0.88); if anything helps it's memory not "cognition"
broadly (Xu 2024 memory SMD 0.31, no effect on overall/executive); creatine raises brain creatine only
modestly; literature small/heterogeneous/partly high-risk-of-bias.

**Disagreement:** Does stress unlock benefit? Both ways (Prokopidis: memory improved *non*-stressed not
stressed — opposite the popular story; vs an acute megadose during sleep deprivation). Is the headline
memory benefit even real? Prokopidis's pooled result was challenged by a Letter ("double-counting →
false-positive findings"); authors replied. Vegetarians mixed. Older-adult case: 5/6 positive but only
2 double-blind RCTs, quality fair/poor.

**Unverified/color:** Independence is weak — the four reviews re-pool the **same ~10–16 small RCTs**,
not independent replication. Processing-speed/attention low-certainty. r/Nootropics splits (color).

**Gaps:** two primary RCTs read only secondhand via reviews; strongest skeptic paper paywalled
(abstract only). *Did not surface the EFSA verdict or the largest RCT (Sandkühler).*

---

## 5. Judge notes (condensed, per judge)

1. **→ deep-aletheia.** "Ties claims to the most distinct, verifiable primaries (Sandkühler, dose-response, Gordji-Nejad); strongest, best-grounded independence analysis." (surveyor 2nd; v1 3rd)
2. **→ deep-aletheia.** "Widest genuinely-independent evidence base; best mechanism + subgroup contest + cost." (v1 2nd; surveyor last — "leans on EFSA, reads positives secondhand")
3. **→ surveyor.** "Its load-bearing claims (EFSA rejection, Xu unit-of-analysis error, the dose gap) all check out; most decision-ready." (v1 2nd; deep-aletheia last)
4. **→ deep-aletheia.** "Most complete, best-grounded, most decision-ready; reaches past the meta-analytic echo to distinct primaries." (v1 2nd; surveyor last)
5. **→ surveyor.** "Centers the authoritative independent verdict (EFSA) and the same statistical error two sources flag; best calibration." (v1 2nd; deep-aletheia last)

---

## 6. Files
- surveyor run: `runs/survey/2026-07-08-1842-does-creatine-monohydrate-supplementatio/` (brief.md, verify.jsonl, notes/)
- deep-aletheia run: `runs/deep/2026-07-08-1842-creatine-cognition/`
- aletheia v1 run: `runs/2026-07-08-1841-creatine-cognition/`
- atlas entry: `atlas/surveys/2026-07-08-creatine-cognition-healthy-adults.md`
- (all `runs/` are gitignored working artifacts)
