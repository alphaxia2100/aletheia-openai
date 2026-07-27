# Evaluation designs for agent-facing Aletheia output quality

**Node question:** How should A/B tests distinguish a more robust, nuanced, usable field survey from a longer or more expensive report, while controlling judge bias, stochasticity, topic leakage, and whether the changed mechanism actually ran?

**Bottom line:** Keep the existing blind/version-pinned A/B scaffold, but do not use its holistic brief preference as the promotion endpoint. The next evaluator should test the **agent-facing artifact as a field model**: hidden atomic must-cover and harmful-omission criteria, claim support, disagreement/gap recovery, and fixed downstream question-answering/decision/evidence-location tasks. Run each generator three times on isolated held-out topics under the same hard resource envelope; grade atomically; use exact AB/BA mirrored holistic judging only as a secondary diagnostic; and require human-calibrated judges, mechanism activation, and feature-off ablations. This directly tests whether a tree/bundle helps an agent understand and use the field rather than whether a judge likes a longer report.

## Claim 1 — The repository's current A/B evidence is useful mechanism evidence, but not promotion-grade evidence

The existing evaluator already gets several important things right: immutable tag/worktree intent, a shared scorer, blinding, randomized presentation, human-anchor output, Wilson intervals, and a kappa trust gate. But its empirical record demonstrates why one generated brief per topic plus a holistic judge cannot establish superiority.

- In the creatine bakeoff, the authors explicitly report: **“N=1 topic, one run per skill; much of the gap is which sources each run happened to find (retrieval luck), not architecture.”** They also conclude that the earlier numeric source-quality/independence proxy **“pointed the wrong way.”** ([project experiment record, local primary](https://github.com/alphaxia2100/aletheia-openai/blob/addfaf648ca5577e00e393b2cb1c692a6302eac2/docs/evals/2026-07-08-creatine-cognition-bakeoff.md))
- In the 0.5 forward test, both reversed-order judges preferred the dynamic outline, yet the baseline had 41 persisted read artifacts and the candidate 97: **2.37× observed read amplification**. The record correctly calls this an invalid cost-matched promotion. It also records that a scope verifier expanded 17 writer-selected claims to 32, proving that an apparently perfect claim score can omit nearly half the load-bearing scope. ([project experiment record, local primary](https://github.com/alphaxia2100/aletheia-openai/blob/addfaf648ca5577e00e393b2cb1c692a6302eac2/docs/evals/openai-v0.5-forward-test.md))
- The current workflow performs only one generation per version/topic, runs `verbosity user`, presents one broad holistic rubric, and does not enforce resource parity or test the full agent bundle. ([project evaluator implementation, local primary](https://github.com/alphaxia2100/aletheia-openai/blob/addfaf648ca5577e00e393b2cb1c692a6302eac2/scripts/eval/eval_versions.workflow.js))

**Corroboration:** Strong within the project: two independent internal comparisons expose different failure modes (retrieval lottery; hidden cost and omitted claims). **Disconfirming evidence:** The two capped 0.5 source-triage tests did win reversed-order judgments and the biomedical run recovered better primaries, so the existing evaluator is not useless; it is a good *mechanism diagnostic*. It is simply underpowered and incomplete as a release gate.

**Frozen consequence:** Never promote from a single run/topic or from configured “rounds.” Use repeated generator runs, observed resources, and topic-level outcome scores. Preserve the existing tag-pinned baseline, shared scorer, Wilson interval, and “inconclusive” outcome.

## Claim 2 — The primary quality endpoint should be hidden, atomic field-model coverage with explicit harmful omissions, not holistic preference, source count, or reference overlap

ResearchRubrics is the closest decisive external instrument for long-form deep-research output. It uses 2,593 expert-written criteria across 101 open-ended tasks, separates mandatory from optional criteria, and includes negative weights for factual error, irrelevance, and verbosity. It reports that current systems remain below 68% average compliance and that implicit reasoning plus synthesis account for roughly 45–50% of failures. Its rubric taxonomy maps well to Aletheia's objective: explicit requirements, **implicit requirements**, synthesis, references, communication, and instruction following. ([primary benchmark study](https://arxiv.org/html/2511.07685))

Useful primary quotations:

- **“Implicit Requirements [cover] points that a well-informed person would expect, even if not directly asked.”**
- Mandatory criteria are **“core elements that must be satisfied”**; negative criteria identify failures that may make an answer **“actively harmful”** or invalidate its reasoning.
- The authors found binary human–judge Macro-F1 of about 0.72–0.76, while ternary grading was only about 0.53–0.57; LLM-expanded rubrics degraded alignment by 15–20%, whereas concise expert criteria with concrete examples worked better.

ReportBench independently supports separating retrieval coverage from statement support: it evaluates citation precision/recall, cited-claim entailment, and uncited-statement factuality rather than treating citation volume as quality. ([primary benchmark study](https://arxiv.org/html/2508.15804)) DeepResearch Bench likewise separates report quality (RACE) from effective/accurate citations (FACT) and reports distinct leaders on citation abundance versus accuracy. ([primary benchmark/project record](https://deepresearch-bench.github.io/))

**Corroboration:** Three independent benchmark groups converge on multidimensional, claim/criterion-level evaluation. **Disconfirming evidence:** Fixed gold reports and reference overlap can punish valid divergent synthesis and leak the intended answer. ReportBench itself observed agents retrieving the original survey despite instructions, and ResearchRubrics criticizes reference-derived/circular evaluators. Therefore Aletheia should freeze **criteria and decisive-source/camp sets, not a single ideal essay**, and should retain room for valid novel evidence.

**Frozen metric:** Each hidden topic gets 12–20 binary criteria written before either arm runs:

- 4–8 mandatory must-cover criteria;
- 3–6 nuance criteria (mechanism, boundary conditions, disagreement, evidence asymmetry);
- 2–4 provenance/support criteria;
- 1–3 negative criteria for a harmful omission, unsupported causal leap, laundered consensus, or irrelevant padding.

Grade each criterion independently with a quote/span justification. Report mandatory recall, optional recall, negative-criterion incidence, and supported-claim precision/coverage separately. Never allow a high average to cancel a critical harmful omission.

## Claim 3 — Because Aletheia is primarily an agent tool, the decisive test is downstream task performance and evidence navigation

Anthropic's first-party agent-evaluation guidance distinguishes the transcript from the outcome and says research-agent evaluation should combine groundedness, key-fact coverage, source quality, and open-ended synthesis. It also recommends multiple grader types and human calibration. ([first-party practitioner primary](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)) Aletheia's proposed evidence tree is only valuable if a fresh agent can use it to answer, decide, and locate support more accurately or cheaply than it can use the current flat/full bundle.

**Concrete A/B:** Give a fixed, fresh-context consumer agent one generated artifact directory, read-only file/search tools, no web, the same model, and the same token/tool/time limit. Keep the downstream questions hidden from the research generator. Per topic, require:

1. five supported factual questions, including one where the correct answer is “not established”;
2. two mechanism/disagreement questions that require naming both camps and why they differ;
3. one constrained decision/recommendation with an explicit uncertainty threshold;
4. one counterfactual update (“if this assumption/source changes, what changes?”);
5. two evidence-location tasks requiring the exact artifact path, source URL, and supporting quote.

Measure downstream answer F1, decision-rubric score, calibrated abstention, unsupported-answer rate, success within the tool/token cap, tool calls, consumer tokens, and **time-to-first-correct-evidence span**. For a tree-output experiment, the primary feature-specific endpoint is the evidence-location/time score, not judge preference.

**Corroboration:** Outcome-over-transcript evaluation is established practitioner guidance, and hidden atomic coverage is supported by ResearchRubrics. **Disconfirming evidence / gap:** Two focused Aletheia retrieval manifests found no primary controlled study comparing hierarchical versus flat research artifacts on downstream agent QA, decisions, or time-to-evidence. Therefore the tree's navigation benefit is a plausible but **unverified hypothesis**; this A/B is the experiment that should establish it, not a literature-derived assumption.

## Claim 4 — LLM judging is usable only with exact order mirroring, atomic rubrics, human calibration, and explicit verbosity/self-preference probes

The most decisive positional-bias experiment found that merely swapping two answers produced conflict rates as high as 46.3% for GPT-4 and 82.5% for ChatGPT in one comparison; balanced-position calibration improved human alignment. The authors' recommended procedure evaluates every pair in both orders. ([primary controlled experiment](https://ar5iv.labs.arxiv.org/html/2305.17926)) MT-Bench independently found position, verbosity, and possible self-enhancement effects; its conservative rule declares a win only when the same answer wins in both AB and BA order, otherwise a tie. It also constructed a “repetitive list” attack in which the longer answer added no information, yet some judges preferred it. ([primary empirical benchmark study](https://ar5iv.labs.arxiv.org/html/2306.05685))

Self-Preference Bias in LLM-as-a-Judge provides a separate origin: on human-labeled Chatbot Arena pairs, GPT-4's favorable-versus-unfavorable recall gap for its own outputs was reported as 0.520, and models generally overpreferred lower-perplexity/familiar text. ([primary empirical study](https://arxiv.org/html/2410.21819v1))

**Corroboration:** Three independent experimental groups identify order/familiarity/style failure modes. ResearchRubrics further shows that longer outputs can genuinely satisfy more criteria (reported length–compliance correlations around 0.24–0.28), so simply length-normalizing or penalizing words would also be wrong. **Disconfirming evidence:** After controls, strong LLM judges can exceed 80% agreement with human preferences in MT-Bench, and DeepResearch Bench reports automated RACE alignment near or above its human inter-agreement baseline. LLM judges are therefore useful, not disqualified—provided they are treated as calibrated instruments rather than truth.

**Frozen judge protocol:** 

- Atomic rubric grading is the primary automated score; grade one criterion at a time, binary, with evidence.
- Holistic A/B is secondary. Run exact AB and BA for every pair with the same prompt/model; a win requires the same winner in both positions, else tie. Do this with two judge families disjoint from the generator when available.
- Calibrate each judge against at least 12 adjudicated human/SME anchor pairs. Require Macro-F1 ≥0.75 **and** Cohen's κ ≥0.60 with bootstrap intervals reported; otherwise automated preference is untrusted.
- Include blinded judge-control items: identical outputs, a pure order swap, and a repetitive-padding variant. A judge that prefers padding or flips excessively is removed for that evaluation.
- Strip version names, runtime prose, and process tells, but do not truncate substantive content. Report score versus output length and useful-criterion density so real coverage is distinguishable from padding.

## Claim 5 — Generator stochasticity and full observed resource use must be first-class, because configured effort is not actual effort

Anthropic defines each attempt as a trial and explicitly recommends multiple trials because agent outputs vary. It distinguishes `pass@k` (at least one success) from `pass^k` (all trials succeed); Aletheia is a reliability tool, so critical behaviors are closer to `pass^k`. The same guidance records that shared state can inflate scores—one internal agent gained an unfair advantage by reading prior trials' Git history—and recommends clean isolated environments. ([first-party practitioner primary](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents))

The local 2.37× read-amplification result is direct evidence that “same rounds” is not cost parity. Aletheia's current scorer has already added the right primitives: retrieval passes, read attempts/successes, read seconds, total persisted read artifacts, and direct/manual artifacts. ([project implementation, local primary](https://github.com/alphaxia2100/aletheia-openai/blob/addfaf648ca5577e00e393b2cb1c692a6302eac2/.cursor/skills/aletheia-research/scripts/report.py))

**Frozen execution protocol:** 

- Run **three independent generator trials per arm/topic**, interleaved baseline/candidate within the same time block. Aggregate trials within topic before any across-topic test.
- Start each trial from an isolated tag/commit worktree and fresh run/CODEX state; disable the Consilient Atlas, prior runs, cross-trial caches, and Git-history access. Record model snapshot, prompt/skill/runtime hashes, channel config/health, time, and seed where exposed.
- Give both arms the same predeclared per-complexity resource envelope. Enforce and report total generator input/output tokens, model cost, retrieval passes/API calls, read attempts, successful **unique read characters and artifacts including manual/full rereads**, wall time, and final artifact bytes. “Rounds” remains diagnostic only.
- Report median, worst trial, variance, and `pass^3` for every critical criterion. Use a topic-clustered paired bootstrap (10,000 resamples) and a Wilson interval over topic wins; trials are not independent topics.
- If an arm exceeds any hard envelope, label the result “quality at higher cost,” never a matched-cost win. Preserve it on an experimental branch rather than discarding the useful quality signal.

**Corroboration:** External practitioner guidance and internal measured amplification agree. **Disconfirming evidence:** Three trials cannot characterize tail risk precisely; it is a pragmatic minimum, not proof of production reliability. An inconclusive result should add held-out topics/trials, not relax the gate.

## Claim 6 — Test adaptive reach with seeded-but-real disagreement/gap probes, and require trace activation before attributing an improvement to a mechanism

The creatine bakeoff separated systems primarily by whether they happened to recover the EFSA decision, the largest RCT, and the statistical critique—exactly the “decisive source” and disagreement-recovery behaviors Aletheia claims to improve. ResearchRubrics reports that implicit requirements and synthesis dominate failures even when explicit retrieval looks good. These findings imply that an easy benchmark of settled questions will not exercise Aletheia's distinctive mechanisms.

Add six **diagnostic mechanism probes** outside the headline quality set, each based on real primaries and captured retrieval fixtures where necessary:

1. **Echo laundering:** many domains repeat one origin; success requires collapsing them and not calling repetition independent agreement.
2. **Decisive-primary chase:** the settling primary is reachable only through a review/citation trail; success requires reading and citing the primary.
3. **Live disagreement:** two credible camps use different populations/definitions; success requires both, the mechanism of disagreement, and calibrated conclusion.
4. **Degraded channel:** one expected channel is unavailable; success requires alternate routing and an explicit gap, not silent confidence.
5. **Untrusted snippet/truncation:** a candidate snippet contains an instruction and a load-bearing paper is truncated; success requires ignoring the instruction and performing an uncapped reread.
6. **Claim-scope omission:** the draft contains an uncatalogued load-bearing assertion; success requires the scope verifier to add/check or remove it.

For each proposed mechanism, predeclare an eligibility predicate and a machine-observable activation marker (for example: distinct adversary origins read; a `notes/full` reread; an added claim in the scope audit; an explicit abstention/gap). A mechanism gets causal credit only when it activates in at least 80% of eligible probes **and** the feature-on branch improves its feature-specific outcome over both prod and a feature-off ablation at the same resource envelope. Trace activation is an eligibility check, not a quality score; a beautiful trace cannot compensate for a bad answer.

**Corroboration:** Internal bakeoff and forward-test records directly show missed decisive sources, hidden claims, and hidden reads; ResearchRubrics independently finds implicit/synthesis gaps. **Disconfirming evidence:** Seeded probes can become narrow unit tests and be gamed. Keep them diagnostic, rotate their surface form/sources, and never include them in the headline field-quality win rate.

## Claim 7 — Freeze the evaluator outside the experiment and use one-change branches plus feature-off ablations; otherwise iteration will optimize the judge

The current repository already records executable runtime hashes and intends baselines to run from immutable tags. Preserve that. The visible `scripts/eval/topics.jsonl`, however, is not genuinely held out from an agent editing the skill, and the current judge prompt/rubric is in the same repository. Repeated iteration against it invites topic and metric leakage.

**Frozen branch/evaluator design:** 

- `codex/prod` (and an immutable prod tag) is the baseline. Every experiment branches from that exact commit and changes one named mechanism: e.g. `codex/exp-agent-evidence-tree-v1`.
- For a nontrivial mechanism create a sibling feature-off ablation from the candidate commit, not an ad hoc edit after seeing results: `codex/abl-agent-evidence-tree-v1`.
- Store the gate topics, rubrics, downstream questions, source/camp keys, and judge controls outside all candidate worktrees. The proposer sees only the public development suite and the metric schema, never hidden item content.
- Use 12 hidden quality topics spanning six domains (biomedical/science, policy/legal, consumer, software/technical, business/economics, history/current events), two per domain, stratified by ResearchRubrics' breadth/nesting/exploration dimensions. Refresh at least half the hidden set after two release decisions. Include newly published/time-bounded sources and two nonce evidence-packet contamination controls.
- Keep a separate frozen regression suite of previously solved failures; capability topics must remain difficult enough to discriminate. Never tune a candidate after opening hidden per-item results and then reuse those items as “held out.”
- Persist every brief, full agent bundle, consumer trace, resource ledger, rubric verdict, judge AB/BA result, human anchor, channel-health report, commit/tag, and runtime hash. The evaluator code and rubric weights are versioned and locked before generation.

**Corroboration:** Anthropic documents cross-trial Git-history leakage and the need for isolated environments; the local Aletheia scorer/runtime fingerprinting supplies the audit primitives. **Disconfirming evidence / practicality:** A truly private multi-domain SME set is expensive for a solo project. If only public topics are affordable, call the result a development comparison—not a held-out generalization claim—and require a fresh human-reviewed topic batch before prod promotion.

## Frozen promotion protocol v1 (recommended)

| Item | Predeclared protocol |
|---|---|
| Arms | Immutable `prod` tag vs one-change candidate commit; add candidate-minus-feature ablation for any claimed mechanism. Same generator model/harness. |
| Suite | 12 hidden quality topics × 3 generator trials/arm, plus 6 rotating mechanism probes not counted in headline quality. Two topics in each of six domains; stratify breadth, nesting, and exploration. |
| Artifact under test | `verbosity: agent` complete run directory/bundle, including tree/findings/evidence/reads/claims/verification; do not substitute the short human brief. |
| Resource control | Same hard envelope by complexity bucket. Count all LLM tokens/cost, retrieval calls/passes, read attempts/successes, unique read characters/artifacts (including direct/manual/full), wall time, and artifact bytes. |
| Primary score | **Agent Field Quality Score (AFQS):** 30% mandatory must-cover recall; 20% downstream QA/decision score; 15% disagreement/mechanism map; 15% claim support + calibrated abstention; 10% hidden-gap recovery; 10% evidence-navigation/time-to-evidence. Freeze weights before runs. |
| Non-compensable gates | Final claim coverage = 1.0; supported-claim precision no worse than prod by >2 percentage points; no increase in critical harmful omissions/unsupported high-stakes recommendations; all citations resolve; no resource-envelope breach; mechanism activation gate passes when relevant. |
| Verbosity diagnostics | Useful weighted criteria per 1,000 output tokens; unsupported/irrelevant claims per 1,000; downstream consumer tokens/tool calls; repetitive-padding judge controls. Length alone is neither reward nor penalty. |
| Robustness | Per-topic median and worst trial, variance, critical-criterion `pass^3`, gap-recovery rate, and activation rate. Interleave arms in time and isolate state. |
| Judge | Criterion-atomic binary graders first. Secondary holistic pairwise uses exact AB+BA and two judge families; inconsistent pair = tie. Human/SME anchor n≥12; require Macro-F1 ≥0.75 and κ≥0.60. |
| Statistics | Aggregate trials within topic. Paired topic-cluster bootstrap, 10,000 resamples, for AFQS delta; Wilson 95% CI for topic wins. Promotion requires AFQS lower CI >0, topic-win lower CI >0.5, and every non-compensable gate. Otherwise “inconclusive” or “quality at higher cost.” |
| Decision hygiene | Evaluator and hidden items locked before generation. No metric changes, cherry-picking, or new candidate edits after hidden results. A failed/inconclusive branch remains archived with full lineage. |

## Gaps and limitations

- **No direct evidence for evidence-tree usability:** focused searches did not find a controlled primary comparison of hierarchical versus flat research bundles on downstream agent outcomes. The proposed consumer-agent A/B is intentionally the missing experiment.
- **Power is not magically solved:** 12 topics × 3 trials is a strict, affordable promotion screen; it will often return “inconclusive.” It is not a population-wide estimate. Increase topics rather than treating generator trials as independent samples.
- **Human gold is fallible:** ResearchRubrics' “experts” were generally strong STEM task designers working in familiar domains, not a specialist for every prompt; DeepResearch Bench's reference-based judge and ReportBench's survey overlap can anchor valid answers. Store adjudication disagreement and allow “rubric/source key incomplete” corrections before unblinding arms.
- **Live-web fairness is difficult:** changing pages, rate limits, and channel health add paired noise. Interleaving, snapshots/fixtures for probes, and health logs reduce but do not eliminate it.
- **Judge/model drift:** API model aliases and judge behavior change. Pin exact snapshots when possible and re-run human calibration whenever the judge snapshot or rubric changes.
- **Channel gap in this survey:** Brave was degraded (no API key). DuckDuckGo and Marginalia substituted for independent-web discovery. ArXiv was initially rate-limited but later recovered; decisive papers were reread directly in full. GitHub's anonymous API also briefly returned 403 during retrieval.

## Source independence and provenance

- **Local project evidence:** creatine bakeoff; 0.5 forward test; evaluator/scorer implementations. Same project/team, so these are direct observations but not independent replications.
- **Deep-research benchmark origins:** ResearchRubrics (Scale/academic coauthors), ReportBench (ByteDance BandAI), DeepResearch Bench (USTC/independent project). Distinct teams; they disagree usefully about human criteria versus reference reports.
- **Judge-bias origins:** FairEval positional-bias study, LMSYS MT-Bench/Arena, and Self-Preference Bias. Distinct author groups/datasets with convergent failure modes and a shared disconfirming result: controlled strong judges can still be useful.
- **Practitioner origin:** Anthropic's agent-eval guidance is first-party operational evidence, not an independent academic benchmark; it is used for execution/isolation design, not as proof that the proposed AFQS weights are optimal.

## Stop reason

Stopped after four gap-driven Aletheia rounds plus full rereads and direct decisive-source chasing. The first three rounds converged on atomic expert rubrics, factual/support scoring, repeated outcome trials, and controlled LLM judging from distinct origins. A fourth round and tighter requery produced no qualifying primary study of hierarchical research-artifact navigation; it was explicitly rejected rather than padded with generic surveys. Further retrieval was repeating benchmark surveys or unrelated QA/report-format material, while the remaining uncertainty is best resolved by the proposed A/B itself.
