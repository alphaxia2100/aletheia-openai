# Practitioner and field evidence: failure modes and workable controls

## Scope and evidence standard

This leaf examined observed and reproducible failures in deployed or open-source research-agent systems. GitHub issues and community reports are used only as **labeled cases**, never as prevalence estimates. Where possible, issue leads were chased to code, regression tests, merged fixes, engineering retrospectives, or primary benchmark artifacts. Five candidates→judge→read rounds produced 16 engine-tracked full reads; direct primary chasing brought the node to 34 persisted read artifacts. The main independent origin clusters are Anthropic, LangChain/Open Deep Research, Microsoft/Magentic-One, Google Research, GPT Researcher, ReportBench/DeepResearch Bench, and the Databricks Deep Research Agent project. Multiple pages from one organization count as one origin.

## 1. Completion must be a typed, verified state transition; “normal-looking final report” is not proof that research finished

**Claim.** Premature stopping in multi-agent research is often a control-flow or error-semantics defect, not merely an LLM judgment error. A system can silently convert partial or failed research into a polished final answer unless it has an all-branch barrier, typed failure states, and explicit partial-result semantics.

**Primary evidence.**

- LangChain Open Deep Research issue [#284](https://github.com/langchain-ai/open_deep_research/issues/284) gives a runnable source-level reproduction at commit `1f24f114…`: “the presence of *any* completed section is enough to switch the supervisor into completion mode.” One child can therefore trigger introduction/conclusion writing while siblings are still pending. `[reproducible code issue; single reporter/codebase]`
- The adjacent but distinct exception path in [#283](https://github.com/langchain-ai/open_deep_research/issues/283) contains `if is_token_limit_exceeded(...) or True`; the reproduction returns `goto = __end__` with empty notes after a child throws. The outer graph then proceeds to final-report generation. PR [#286](https://github.com/langchain-ai/open_deep_research/pull/286) adds regression tests and surfaces non-token-limit exceptions, but remained open on 2026-07-27. `[reproducible code issue + proposed tested fix; same reporter and codebase as #284, so not independent corroboration]`
- GPT Researcher issue [#1881](https://github.com/assafelovic/gpt-researcher/issues/1881) found that a reviewer accepted any response *containing* `None` and that the reviewer/reviser loop had no bound. Thus “None of the criteria are met” could publish a bad draft, while continued criticism could end only in a framework recursion error. Merged PR [#1909](https://github.com/assafelovic/gpt-researcher/pull/1909) replaced substring sentinels with exact parsing, added explicit revision ceilings, and reported 17 passing tests. `[independent open-source code audit; maintainer-merged regression fix]`
- Anthropic’s production retrospective says “Agents are stateful and errors compound” and describes deterministic retries, checkpoints, and resume-from-failure rather than restart ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand production engineering report]`

**Implication for Aletheia.** Track an expected branch set and require every branch to end as `complete`, `failed`, or `abstained`, with a reason and artifact pointer. Synthesis should refuse an unlabelled partial tree. A graceful partial answer is legitimate only if failed/missing branches and their impact are visible. Use typed structured decisions rather than natural-language sentinels; bound every revise/review cycle; checkpoint after each successful read and child handoff.

**Disconfirming evidence / boundary.** Failing hard on every tool error can discard useful sibling results. The safer rule is not “all errors abort,” but “no error is silently reclassified as success”: retain successful siblings, expose the failed branch, and let an explicit policy choose retry, partial synthesis, or abort.

**Corroboration status:** strong mechanism evidence across two independent codebases plus one production operator; no prevalence claim.

## 2. Adaptive effort needs both a progress ledger and task-topology routing; more agents and more searching are not monotonic improvements

**Claim.** Query drift, endless search, and shallow stopping are dual failures of the same missing controller: the agent lacks an explicit model of required coverage, current progress, and whether the task is decomposable. A progress ledger helps, but topology selection matters as much as ledgering.

**Primary evidence.**

- Anthropic reports early agents “spawning 50 subagents for simple queries, scouring the web endlessly for nonexistent sources,” continuing after sufficient results, and issuing over-specific queries. Its mitigations were explicit effort bands, broad→narrow search, detailed delegation boundaries, and step-level simulations/traces ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand production engineering report]`
- Magentic-One maintains a task ledger (verified facts, facts to find/derive, guarded guesses, plan) and a per-step progress ledger asking whether the request is satisfied, the team is looping, forward progress exists, who acts next, and with what instruction ([paper](https://arxiv.org/html/2411.04468v1); [current implementation docs](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/magentic-one.html)). A stall counter triggers reflection and replanning. Removing the full ledgers reduced GAIA-validation performance by 31%. `[primary paper + open-source implementation; one origin]`
- The same Magentic-One error analysis found persistent inefficient actions and insufficient verification among its leading coded failure themes; examples include unchanged failed searches and tasks marked complete without validation. The ledger is therefore helpful, not sufficient. `[primary log analysis; automated qualitative coding, not a human prevalence study]`
- A controlled Google study across 260 configurations found multi-agent performance ranging from +80.8% on decomposable financial reasoning to −70.0% on sequential planning. Independent multi-agent systems amplified trace-level errors 17.2× versus 4.4× under centralized coordination ([paper](https://arxiv.org/html/2512.08296)). `[primary controlled benchmark study]`
- Anthropic’s own internal breadth-oriented research eval supplies the positive boundary: its multi-agent configuration outperformed a single-agent configuration by 90.2% on that eval ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand internal eval; task set and raw results not public]`

**Implication for Aletheia.** Before fan-out, classify subquestions by independence and sequential dependency. Parallelize only separable discovery branches; keep dependent reasoning in one coherent state stream. Maintain a compact progress ledger with: required facets, answered facets, unresolved contradictions, new independent origins this round, failed tools, repeated-query/loop signal, and the highest-value next gap. A stall should trigger a changed hypothesis/query/channel—not another semantically identical search. Stopping should require coverage and evidence gates, not the model’s bare feeling that it is done.

**Disconfirming evidence / boundary.** Google’s paper used six benchmarks, standardized rather than model-optimized prompts, only 20 instances for two expensive benchmarks, and six dataset clusters; the authors frame several cross-domain effects as directional. Its architecture predictor generalizes only in a restricted sense. Treat the exact thresholds as hypotheses for Aletheia A/Bs, not universal constants.

**Corroboration status:** strong, multi-origin, with both positive and negative results.

## 3. Context loss is an information-governance problem, not a request for a larger window

**Claim.** Raw tool output eventually overwhelms a monolithic context, but naive compression can erase precisely the latest progress, user constraints, source identity, or dissent that synthesis needs. Reliable long-horizon research separates durable state from disposable conversational tokens.

**Primary evidence.**

- Anthropic saves the lead plan to external memory because a context beyond 200,000 tokens will be truncated; it also recommends phase summaries, clean-context subagents, and filesystem artifacts that pass lightweight references “to minimize the ‘game of telephone’” ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand production engineering report]`
- LangChain issue [#252](https://github.com/langchain-ai/open_deep_research/issues/252) traces token-limit recovery to a helper that searches backward and returns `messages[:i]`, removing the most recent AI exchange and everything after it—the opposite of its “remove older messages” comment. PR [#254](https://github.com/langchain-ai/open_deep_research/pull/254) supplies regression tests and a forward-search fix but remained open. `[source-level issue + tested proposed fix; merge not confirmed]`
- LangChain issue [#83](https://github.com/langchain-ai/open_deep_research/issues/83) showed iterative human feedback being overwritten rather than appended: “past feedback is not retained.” Maintainer PR [#101](https://github.com/langchain-ai/open_deep_research/pull/101) merged a preservation fix. `[user-discovered source bug + maintainer-confirmed fix]`
- LangChain’s own architecture experiments found that a single agent juggling multiple subtopics researched each less deeply and encountered context-window limits; its workaround is a focused research brief plus isolated subtopic contexts and a cleanup call before returning findings ([source](https://www.langchain.com/blog/open-deep-research)). `[first-hand engineering report; no public ablation data]`

**Implication for Aletheia.** Make the research brief, user constraints, branch plan, decisions, source identities, exact evidence spans, contradictions, and gaps durable typed state. Compression may summarize prose, but it must preserve these invariants and point back to raw artifacts. Keep feedback append-only with the plan version it modified. Favor phase-boundary summaries, fresh-context workers, and file references over repeated copy-through-chat. Test compression with adversarial fixtures: newest finding, minority view, negation, numeric qualifier, URL, and unresolved question must survive.

**Disconfirming evidence / boundary.** Cleaned summaries reduce token load but can hide discarded nuance and provenance. Therefore do not replace raw reads: retain the full tree and provide layered views. Larger windows still help some tasks, but they do not fix conflicting or lossy state transformations.

**Corroboration status:** strong mechanism evidence across production design, two concrete bugs, and one engineering comparison.

## 4. Parallel evidence gathering is useful; parallel prose generation predictably fragments the report

**Claim.** Parallel workers are most reliable as evidence collectors with bounded scopes, not as authors of independently polished final sections. Without a global synthesis pass, section-local optimization creates redundant citations, repeated claims, inconsistent framing, and a report that is less than the sum of its parts.

**Primary evidence.**

- LangChain says its earlier system wrote report sections in parallel: “It was fast, but … the reports were disjoint.” It changed the architecture to parallelize research only and write after research was complete ([source](https://www.langchain.com/blog/open-deep-research)). `[first-hand engineering report]`
- A LangChain user reported “fragmented” sections with “overlapping or redundant content” and repeated citations in [#64](https://github.com/langchain-ai/open_deep_research/issues/64); a maintainer confirmed that main-body sections were written independently in parallel. `[labeled first-hand case + architecture confirmation; not prevalence]`
- GPT Researcher issue [#1419](https://github.com/assafelovic/gpt-researcher/issues/1419) reports redundant/disorganized reports over hundreds of executions and traces the design: each section is researched and reviewed in isolation and “there is no holistic post-assembly” review. The issue was later closed in backlog cleanup explicitly without a validity judgment. Issue [#1495](https://github.com/assafelovic/gpt-researcher/issues/1495) separately reproduces repeated chapter content on then-current master. `[two user cases in one codebase; one detailed architectural trace, one unconfirmed reproduction]`
- The positive case remains real: Anthropic and LangChain both find isolated contexts beneficial for independent research subtopics, while Anthropic reports large gains on breadth-first queries. `[first-hand engineering reports]`

**Implication for Aletheia.** Workers should return structured claims, evidence spans, source/origin identities, contradictions, and gaps—not final prose sections. Synthesize bottom-up, then run a global pass that can move claims across sections, merge duplicates, compare branches, and preserve disagreements. The agent-facing deliverable should be a navigable tree: root synthesis → branch syntheses → claims/evidence → full reads. This preserves breadth without forcing the caller to read every trace.

**Disconfirming evidence / boundary.** A single one-shot global writer can itself overflow context or flatten minority evidence. Prefer hierarchical synthesis with a final global coherence and contradiction pass, not one enormous prompt. Parallel writing may work when sections are genuinely independent deliverables; the risk arises when they must form one argument.

**Corroboration status:** strong qualitative convergence across two independent open-source projects and two vendor teams; no controlled report-coherence A/B was found.

## 5. Citation quality must be enforced at claim↔evidence-span time; post-hoc URLs and “source sections” are insufficient

**Claim.** Citation laundering can arise through mundane pipeline defects: snippets are mistaken for read documents, URLs are dropped during compression, or the writer is asked to cite with empty context. Even leading products retain nontrivial citation-support error in independent benchmarks. The robust unit is an atomic claim bound to a saved evidence span, not a URL appended after prose generation.

**Primary evidence.**

- GPT Researcher issue [#1892](https://github.com/assafelovic/gpt-researcher/issues/1892) shows released version 0.15.1 treating >100-character search snippets as prefetched full content, logging “Scraping content from 0 URLs...” and writing from snippets. A second contributor reproduced it in a clean Python container and traced a release/master divergence; PR [#1959](https://github.com/assafelovic/gpt-researcher/pull/1959) proposes the one-key fix. `[reproducible released-code failure with independent reproduction; current-main status disputed, release gap confirmed]`
- Companion issue [#1893](https://github.com/assafelovic/gpt-researcher/issues/1893) traces a metadata-key mismatch (`url` versus `source`) that rendered `Source: None`; reports then cited `https://example.com` dozens of times. Merged PR [#1906](https://github.com/assafelovic/gpt-researcher/pull/1906) re-applied the fix and passed a 50-test offline suite. `[source-level case + maintainer-merged regression fix; original reporter overlaps #1892]`
- In the single-origin practitioner case [#1572](https://github.com/assafelovic/gpt-researcher/issues/1572), empty retrieved context still produced plausible-looking real and dead URLs; the user’s effective guard was `NO_RESULTS_FOUND`, later augmented by URL allowlisting and quote-first sourcing in a second practitioner comment. `[labeled case reports; not independently reproduced here]`
- ReportBench measured citation-statement match rates of 78.87% for OpenAI Deep Research and 72.94% for Gemini Deep Research on its 100 academic-survey tasks ([artifact](https://github.com/ByteDance-BandAI/ReportBench)). DeepResearch Bench reported citation-accuracy values of 77.96% (OpenAI), 81.44% (Gemini), and 90.24% (Perplexity) under its different FACT metric ([artifact](https://deepresearch-bench.github.io/)). Metrics are not interchangeable, but neither benchmark supports treating citation-rich output as automatically entailed. `[primary benchmark artifacts]`
- The Databricks Deep Research Agent documents a concrete seven-stage alternative: evidence preselection, interleaved claim/evidence generation, confidence routing, isolated verdicts, citation correction, numeric QA, and atomic revision; unsupported output receives a visible warning ([docs](https://mshtelma.github.io/databricks-deep-research-agent/concepts/citation-pipeline/)). `[open-source system documentation; claimed performance not independently verified in this leaf]`

**Implication for Aletheia.** Persist exact quote/span, source URL, retrieval/read status, and claim polarity together. Forbid citation to a source not successfully read; allowlist final URLs from the evidence store; atomize compound claims; verify with an isolated model/process; perform dedicated numeric/polarity checks; make `unsupported`, `contradicted`, `broken`, and `unread` visible outcomes. A broken or missing evidence pointer must block “verified” status. Preserve a no-evidence abstention path.

**Disconfirming evidence / boundary.** ReportBench’s expert-survey references are not an exhaustive set of all valid sources, and both benchmark pipelines use model-assisted extraction/judging. Their numbers diagnose residual risk but are not direct estimates of every product’s real-world citation error. The seven-stage Databricks design is promising architecture evidence, not yet a decisive comparative result.

**Corroboration status:** strong mechanism evidence and two benchmark origins; exact prevalence remains unknown.

## 6. URL count is not epistemic breadth; source lineage and independent origin must be first-class

**Claim.** Duplicate-source echo and poor source selection can make a report look broad while adding little independent evidence. Counting citations or domains rewards mirrors, syndicated summaries, repeated section citations, and search-optimized content.

**Primary evidence.**

- Anthropic’s human testers found early agents “consistently chose SEO-optimized content farms over authoritative but less highly-ranked sources like academic PDFs or personal blogs”; source-quality heuristics were added in response ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand production testing]`
- ReportBench found Gemini Deep Research averaging 32.42 references versus OpenAI’s 9.89, but with only marginally higher recall (0.036 versus 0.033) and lower precision (0.145 versus 0.385); the authors call this “over-generation without proportional coverage benefits” ([artifact](https://github.com/ByteDance-BandAI/ReportBench)). `[primary benchmark; reference-overlap metrics, not origin clustering]`
- LangChain issue [#64](https://github.com/langchain-ai/open_deep_research/issues/64) directly reports citations repeated across independently written sections, while the GPT Researcher cases in claim 4 report repeated content across sections. `[labeled user cases]`

**Implication for Aletheia.** Canonicalize URLs, then cluster by upstream origin: same paper/filing/press release/dataset/authoritative record should count once even when mirrored or summarized by many domains. Record publisher, author, cited upstream work, and content fingerprint where available. Report both URL breadth and **independent-origin breadth**. Corroboration requires distinct origins; primary chase should replace a secondary lead in the final claim graph rather than add another apparent vote. Deduplicate at claim level before synthesis, not only in the bibliography.

**Disconfirming evidence / boundary.** More sources can legitimately add facets, and several claims may correctly rely on one decisive authority. DeepResearch Bench found Gemini’s many effective citations coinciding with strong report scores. Origin deduplication must not erase distinct evidence spans or penalize a decisive primary merely for supporting many claims.

**Corroboration status:** moderate. Source-volume and selection failures are observed; a direct origin-echo benchmark was not found. The proposed lineage metric is a high-priority experiment, not an established universal measure.

## 7. Observability and artifact design are part of research quality, not debugging garnish

**Claim.** Long-horizon research cannot be improved reliably if only the final prose survives. Decision traces, branch state, intermediate artifacts, and replayable provenance are necessary both for diagnosis and for an agent caller that wants to drill below a synthesis.

**Primary evidence.**

- Anthropic reports users saying agents failed to find obvious information while engineers could not distinguish bad queries, poor sources, and tool failures until full production tracing was added. It monitors decision patterns and interaction structures, and recommends filesystem artifacts so specialist output persists without repeated lossy relay ([source](https://www.anthropic.com/engineering/multi-agent-research-system)). `[first-hand production report]`
- Microsoft’s current Magentic implementation emits separate initial-plan, replan, and per-round progress-ledger events; its progress event exposes request satisfaction, looping, forward progress, next speaker, and instruction ([docs](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic)). The same documentation cautions that performance outside the original Magentic-One team design is untested. `[open-source production-framework documentation]`
- Magentic-One’s paper says detailed logs revealed “mistakes, missed opportunities, dead-ends, and run-time errors”; it generated per-run postmortems and iteratively clustered codes to find systematic improvement opportunities ([paper](https://arxiv.org/html/2411.04468v1)). `[primary research log analysis]`
- The GitHub cases above repeatedly show a polished or apparently successful terminal output masking an empty context, failed branch, unread source, or lost constraint. `[cross-case synthesis]`

**Implication for Aletheia.** Produce two linked artifacts: (1) a machine-oriented research tree/claim graph with branch status, queries, decisions, costs, source/read lineage, evidence spans, gaps, verification verdicts, and stop reason; (2) a layered synthesis whose nodes link downward to branch summaries and raw reads. Version and hash artifacts so a resumed run or verifier can detect drift. Preserve observable decisions and tool results rather than private chain-of-thought. Add per-run postmortems that distinguish retrieval, selection, reading, synthesis, and verification failures.

**Disconfirming evidence / boundary.** Raw traces can overwhelm callers, leak sensitive content, and increase storage/cost. Anthropic explicitly uses high-level observability without monitoring conversation contents for privacy. The answer is tiered access and retention controls, not dumping every token into the default view.

**Corroboration status:** strong multi-origin mechanism evidence; user-facing usability of a tree output still needs a direct consumption A/B.

## High-value experiments for Aletheia

1. **Silent-partial regression suite.** Inject one failed child, one late child, one empty read, and one token-limit error. The run passes only if the final artifact either waits, retries, or visibly declares the exact partial scope.
2. **Topology A/B.** Pair breadth/decomposable surveys with sequential/dependent questions; compare single-thread, independent fan-out, and centralized fan-out under matched read/tool/token budgets. Measure coverage, contradiction retention, claim accuracy, and error amplification—not verbosity alone.
3. **Parallel-writing ablation.** Hold research artifacts fixed; compare parallel section prose, bottom-up branch summaries plus global synthesis, and one-shot global writing. Human/agent judges should mark cross-section duplication, contradiction handling, narrative cohesion, and retrievability of evidence.
4. **Claim-span citation gate.** Compare post-hoc URL attachment against evidence-interleaved generation plus isolated verification. Include empty context, snippets-only retrieval, mirrored sources, numeric claims, negation, and a broken URL.
5. **Origin-echo challenge set.** Seed ten URLs derived from one press release beside two independent primaries. Score URL breadth separately from origin breadth and test whether synthesis overweights the ten-domain echo.
6. **Compression invariants.** Force context overflow and assert survival of the latest finding, user feedback history, one dissenting claim, one number with qualifier, source URL/span, unresolved gap, and branch failure state.
7. **Agent-consumption usability test.** Give a fresh agent either a flat bundle, a short summary, or a layered tree and ask it to answer follow-ups, audit a claim, and resume research. Measure time/tool calls, correct provenance recovery, and omitted nuance.

## Provenance failures and gaps

- **No prevalence estimate.** GitHub issues are selected, often self-reported cases. Several detailed reports came from a small number of auditors; two LangChain premature-stop issues share one reporter, and GPT Researcher #1892/#1893 share another. They establish possible mechanisms, not frequency.
- **Version ambiguity matters.** GPT Researcher #1892 was independently reproduced in released 0.15.1, while one commenter found the corresponding path fixed on a source branch; the installed release remained affected. Findings must pin commit/package/runtime, not just project name.
- **Vendor self-interest.** Anthropic, LangChain, Microsoft, Google, Hugging Face, and Databricks describe their own systems. Their concrete code paths, limitations, and negative results carry more weight than product claims; proprietary internal eval claims remain single-origin.
- **Benchmark limits.** ReportBench and DeepResearch Bench use model-assisted judges and domain-specific task constructions. Google’s scaling study is broader but still benchmark-bound, with small subsets for two tasks and limited dataset clusters. None directly measures Aletheia’s full field-survey objective or agent-facing artifact utility.
- **Origin echo is under-measured.** Evidence shows citation over-generation, repetition, and poor source selection, but no retrieved primary directly benchmarks shared upstream origin. Treat origin clustering as an experimental requirement.
- **Community-channel gap.** Reddit/Hacker News retrieval produced no useful first-hand cases after relevance filtering; GitHub’s routed candidate channel returned zero on broad queries, so authenticated direct GitHub API/page reads were used for primary chasing. This narrows community variety.
- **Channel health.** Brave was degraded because no API key was configured, removing one independent web index. arXiv also returned transient 429s in round 3; full texts were later recovered through direct reads/other indexes. Both should appear in the run-level gap accounting.
- **No controlled A/B of layered output.** The tree-of-syntheses design is strongly motivated by information-loss and usability mechanisms, but its benefit to a fresh agent caller remains unmeasured; experiment 7 is decisive.

## Stop decision

**Stop: focused local saturation reached after five rounds.** The fifth, adversarial round added one genuinely new origin (Google’s controlled architecture-scaling study) and bounded the multi-agent claim; its other 31 candidates were generic surveys, duplicate Anthropic material, unrelated multi-agent RL, or low-evidence commentary. The main failure classes now have either (a) two independent implementations, (b) a reproducible code artifact plus fix, or (c) a primary experiment with explicit limitations. Further searching is more likely to add duplicate anecdotes than change the seven mechanisms above. Remaining uncertainties require targeted A/Bs or telemetry from Aletheia itself, not more source-count padding.
