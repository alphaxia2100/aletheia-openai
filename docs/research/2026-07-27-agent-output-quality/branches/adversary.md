# Adversary finding: hierarchy is not the main bottleneck

## Bottom line

The leading hypothesis is too architectural and too flattering to the current system. Aletheia does
not primarily need a deeper tree, more traces, or a larger final bundle. Its strongest measured gains
come from getting the right evidence into the system; its most dangerous observed failures come from
letting unsupported or omitted claims escape the evidence state. Hierarchy is useful only in the
narrower roles of parallel breadth, context isolation, and navigable progressive disclosure.

The best current ordering of bottlenecks is:

1. **Retrieval recall, query formulation, source selection, and primary resolution.**
2. **Final-answer claim coverage, inferential verification, and contradiction handling.**
3. **Read integrity and evidence-addressed context assembly.**
4. **Task-aware coordination: choose single-agent, parallel breadth, or centralized verification by
   task structure instead of making a tree the default.**
5. **Stopping, budget integrity, and marginal-value control.**
6. **Claim-specific source independence and provenance.**
7. **Output navigation/progressive disclosure.** This matters to the calling agent, but it is a
   presentation and context-management layer, not an epistemic substitute for items 1–6.

The repository's own evidence is more probative than design rhetoric: the only Aletheia dynamic-outline
trial that judges preferred used **2.37x** the observed reads; the small-N flat-vs-tree bakeoff called
the systems roughly comparable and attributed the difference mainly to retrieval luck; the high-
accuracy ledger variant still emitted an unsupported headline that was absent from its claim set and
received a hardened structural grade of **25/F**.

## Claim 1 — retrieval and selection currently have the strongest causal evidence of improving output

**Verdict: corroborated; highest-priority bottleneck.** Three substantively independent origins support
this conclusion: Aletheia's own source-triage A/B, controlled deep-search retrieval experiments, and a
separate adaptive-RAG failure study. BrowseComp-Plus and the SIGIR text-ranking paper share benchmark
lineage and should not be counted as fully independent replications.

- **Aletheia operational A/B, local primary evidence.** At pinned prod commit
  `addfaf648ca5577e00e393b2cb1c692a6302eac2`,
  `docs/evals/openai-v0.5-forward-test.md` reports that topic-relative selection found exact manuals,
  owner repair accounts, and OEM catalogs in eight reads while the baseline spent seven reads mostly
  on unrelated plumbing threads, affiliate material, and a marketplace listing. Both reversed-order
  judges preferred the selector candidate at 0.98 confidence. On the biomedical no-regression topic,
  the candidate and baseline had the same three engine passes; both reversed-order judges preferred
  the candidate at 0.78/0.77. **Class:** primary operational mechanism test. **Quote:** “Candidate:
  eight reads, including exact manuals, owner repair accounts, and OEM parts catalogs.” **Limit:** two
  topics, LLM judges, and imperfect read-cost equivalence on the consumer topic.

- **BrowseComp-Plus, peer-reviewed primary benchmark.** On a fixed human-verified corpus, changing only
  GPT-5's retriever from BM25 to Qwen3-Embedding-8B raised answer accuracy from **55.90% to 70.12%**
  while reducing mean search calls from **23.23 to 21.74**. For GPT-4.1, adding a Qwen3 reranker raised
  end-to-end accuracy from **35.42% to 47.11%** with essentially unchanged calls. URL:
  https://aclanthology.org/2026.acl-long.1023/ . **Class:** peer-reviewed primary controlled benchmark.
  **Quote:** “better retrieval systems not only improve the overall accuracy but also reduce the
  number of search calls.”

- **Revisiting Text Ranking in Deep Research, primary SIGIR study.** Passage BM25 with a 20B agent
  reached **0.572** accuracy; BM25 plus the non-reasoning monoT5-3B reranker reached **0.689** accuracy
  and **0.716** recall, close to the cited GPT-5 result of 0.701. The reasoning reranker had no clear
  advantage because it often misread keyword-rich web queries. URL: https://arxiv.org/abs/2602.21456 .
  **Class:** primary controlled retrieval/reranking study (SIGIR 2026). **Quote:** “re-ranking
  consistently improves ranking effectiveness and answer accuracy while reducing search calls.”

- **FAIR-RAG, distinct primary error study.** Human-validated, LLM-assisted classification of 200
  failed cases assigned **32.5%** to retrieval failure, the largest single category, and another
  **31.0%** to generation failure after correct evidence had arrived. URL:
  https://arxiv.org/abs/2510.22344 . **Class:** primary author-run benchmark and failure analysis.
  **Quote:** “Retrieval Failure (32.5%): This was the single largest source of error.”

**Disconfirming evidence.** Retrieval is not sufficient: on the same BM25 corpus, GPT-5 substantially
outperformed weaker agents, and FAIR-RAG still attributed 31% of failures to generation. The claim is
that retrieval/selection is the first bottleneck to attack, not that it is the only one.

**Aletheia implication.** Test a query portfolio, passage-level retrieval, retriever-matched query
forms, reranking, citation-chain/primary resolution, and persistent selector manifests before adding
tree depth. Measure decisive-primary recall and must-cover recall, not retrieved-domain count.

## Claim 2 — multi-agent hierarchy is conditional; matched-compute evidence rejects it as a universal default

**Verdict: strongly corroborated for “not universal,” not enough evidence to reject all parallelism.**

- **Equal-token SAS-vs-MAS primary experiment.** Tran and Kiela compared a single agent with sequential,
  subtask-parallel, role-parallel, debate, and ensemble systems across three model families and two
  multi-hop datasets. Above the unusable 100-token regime, the single agent was best or statistically
  indistinguishable from best at every budget and generally used fewer actual thinking tokens. URL:
  https://arxiv.org/abs/2604.02460 . **Class:** primary controlled preprint. **Quote:** “SAS is the
  strongest default architecture for multi-hop reasoning.” **Limit:** text-only concise-answer tasks;
  search tools and open-ended long-form surveys are out of scope.

- **Google/MIT controlled scaling study.** Across **260** matched-compute configurations, six agentic
  benchmarks, five architectures, and three model families, relative MAS performance ranged from
  **+80.8%** on decomposable financial reasoning to **-70.0%** on sequential planning. Dynamic web
  navigation favored decentralized exploration by **+9.2%**, while every MAS variant degraded
  sequential planning by **39–70%**. Independent teams amplified trace-level error **17.2x** versus
  **4.4x** with centralized verification. URL: https://arxiv.org/abs/2512.08296 . **Class:** primary
  controlled preprint. **Quote:** “architecture-task alignment, not number of agents, determines
  collaborative success.” **Caveat:** only six dataset clusters; several regression terms do not
  survive cluster-robust inference, while capability saturation is the most robust result.

- **MAST, peer-reviewed trace evidence.** The authors observed **41–86.7%** task failure across seven
  multi-agent systems and annotated 1,642 traces into system-design, inter-agent-misalignment, and
  verification failures. URL:
  https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html .
  **Class:** peer-reviewed primary trace dataset. **Quote:** “performance gains often remain minimal
  compared to single-agent frameworks or simple baselines like best-of-N sampling.”

- **Aletheia's own flat-vs-tree bakeoff, local primary evidence.** At commit
  `1084f2a1c173587f84424da11c26912a2e6389e1`, the tree won three of five judges and lost two, with Borda
  scores 6/5/4. The record explicitly concludes “no clear quality winner; roughly comparable” and
  says the gap was mainly “which sources each run happened to find (retrieval luck), not architecture.”
  **Class:** local small-N operational A/B.

**Strongest disconfirmation / what hierarchy survives.** Anthropic reports an internal **90.2%**
multi-agent win over single-agent Opus 4 on breadth-first research, and parallelism cut latency by up
to 90%. But the same primary operational report says token use alone explained **80%** of BrowseComp
variance, the system used about **15x** chat tokens, and dependent/shared-context tasks were poor fits.
URL: https://www.anthropic.com/engineering/multi-agent-research-system . **Class:** first-party
production report; not an independent or cost-matched evaluation. **Quote:** “Multi-agent systems
work mainly because they help spend enough tokens to solve the problem.”

What survives is **bounded, read-only parallel breadth for genuinely decomposable, high-entropy
search**, plus centralized verification and filesystem artifacts. Recursive hierarchy should be an
adaptive action earned by measured source/claim divergence, not the default shape of every survey.

## Claim 3 — claim coverage and inferential verification are a more dangerous downstream failure than answer length

**Verdict: strongly corroborated by repeated Aletheia runs and two external trace studies.**

- In the prod biomedical forward test, a fresh auditor expanded **17** writer-selected claims to
  **32**. In the high-accuracy architecture research brief, the writer extracted 16 claims and the
  auditor added 17. Those are not cosmetic misses; the verification denominator roughly doubled.

- The first high-accuracy user run is decisive operational evidence. On branch
  `codex/accuracy-observability-v06` at commit `2edfffbe5548a8a3e793f76213088b0d66a133f9`, the causal branch
  said the national net sign was not identified, but the final answer said “probably helped on
  balance.” That conclusion was absent from `claims.jsonl`, so **21/21** supported factual rows could
  not test it. The run contained 156 node decisions, 111 telemetry rows, and 59 claim events, yet the
  hardened structural grade was **25/F** and the semantic grade **69/100**. Source:
  `codex/accuracy-observability-v06:docs/experiments/high-accuracy-v06/first-forward-run-audit.md`.
  **Class:** primary operational postmortem. **Quote:** “Logging existed, but replayable logging did
  not.” This is direct evidence that more trace can create false confidence when the conclusion is
  outside the epistemic state.

- FAIR-RAG's 200-error study attributed **31.0%** to generation despite correct evidence and **24.5%**
  to its structured evidence assessor; common faults were flawed inference and premature sufficiency.
  MAST assigned **21.3%** of its initial trace sample to task-verification failures and improved one
  system's success by 15.6 points by adding high-level objective verification.

**Disconfirming evidence.** Fresh whole-answer verification can repair these failures: the prod tests
eventually reached complete supported claim sets. A structured claim ledger is therefore promising.
But the accuracy run proves a ledger does not solve claim recall merely by existing; the final prose
must be exactly reconciled to atomic factual, inferential, normative, and forecast claims.

**Aletheia implication.** Make the epistemic unit an atomic claim with exact evidence spans, polarity,
scope, time, magnitude/units, origin cluster, and contradiction state. Require every final sentence
and headline inference to map to claim IDs. Verify arguments separately from factual premises. A
hash of a self-attested claim list is integrity, not semantic completeness.

## Claim 4 — more hierarchy, trace, and output can lower agent performance; the useful mechanism is focused context

**Verdict: independently corroborated.** A tree-of-outputs is valuable only if it enables selective
retrieval; loading the entire tree into the synthesizer is actively risky.

- A controlled study across five models and math, QA, and coding found performance drops of
  **13.9–85%** as context grew despite exact retrieval of all relevant evidence. The effect persisted
  with whitespace, masked distractors, and evidence immediately before the question. A simple
  retrieve-then-solve short-context transformation improved GPT-4o by up to four points. URL:
  https://arxiv.org/abs/2510.05381 . **Class:** primary controlled preprint. **Quote:** “the sheer
  length of the input alone can hurt LLM performance, independent of retrieval quality.”

- Tran and Kiela's error analysis found the sequential MAS often explored more entities but drifted
  from the question; in the Gemini slice it lost a previously surfaced correct answer at finalization
  in 23 cases. Their summary is apt: breadth without pruning degrades precision.

- FAIR-RAG's iteration ablation found the optimum at two or three rounds for complex tasks; the fourth
  round degraded quality while cost rose linearly. On simple TriviaQA, every round after the first was
  detrimental. **Quote:** “an additional retrieval cycle is more likely to introduce noisy or
  tangentially related information.”

- **The strongest hierarchy-positive result actually supports context addressing.** WebWeaver's
  section-wise writer improved citation accuracy **86.73→93.37** and support **90.95→98.73** versus a
  brute-force writer that received the entire memory bank. URL: https://arxiv.org/abs/2509.13312 .
  **Class:** primary author-run benchmark/ablation. Its own mechanism is smaller per-step context,
  citation-addressed evidence, and pruning. It did not compare hierarchy against a flat writer given
  the same focused evidence, did not cost-match total output, and used LLM judges. Thus it decisively
  rejects “hierarchy has no value,” but it does **not** establish hierarchy as Aletheia's main
  bottleneck.

**Aletheia implication.** Separate the **audit plane** from the **working-context plane**. Persist all
traces, but give the agent a compact claim/gap index and fetch dossiers lazily. A useful output tree is:
`index -> question/claim node -> synthesized evidence/counterevidence -> exact spans -> raw read`.
Do not make the full bundle the default model input. Measure downstream agent task accuracy with the
tree versus a flat bundle; do not use preference for a longer report as the endpoint.

## Claim 5 — stopping and read integrity are live prod defects, not speculative refinements

**Verdict: directly observed in the current run and corroborated by external operational evidence.**

- Prod declares `unlimited` the default and makes “agent-paced convergence” the stop, with 512/2048
  nodes only as runaway backstops. There is no machine-observable marginal-value or recall estimator.
  `codex/accuracy-observability-v06:docs/experiments/high-accuracy-v06/architecture-audit.md` therefore
  correctly states that `unlimited` and `max` have no true budget.

- The live prod candidate path accepts `--reads` but does not pass it into `gather_candidates`
  (`investigate.py` lines 686–697 and 856–866), so reads remain coupled to the scrutiny unit. The
  documented uncapped browser reread passes `max_chars or 40000` (`channel-retrieval/scripts/read.py`
  line 72), silently restoring the cap when `--max-chars 0` falls back to the browser. Candidate state
  is written to one `.triage.json` and deleted on read, so manifests are not durably replayable.

- This adversary leaf itself completed nine rounds from **11 manifests / 207 retrieved records** but
  judged only **9** worth reading. The anchoring function prefixed every focused query with the noisy
  phrase `should agent-facing field-survey`; exact agent-scaling searches then returned gravitational-
  wave papers and the same irrelevant Stack Overflow survey-statistics question. **Seven of nine**
  engine reads hit the 40,000-character truncation flag and required seven manual uncapped rereads.
  Primary artifacts: this node's `telemetry.jsonl`, `sources.jsonl`, `notes/`, and `notes/full/`.

- Channel health was not clean: Brave was degraded (missing an independent web index), arXiv entered
  transient 429 cooldowns in early rounds, and GitHub returned a 403 in round one. These are coverage
  gaps, not harmless telemetry.

- Anthropic reports early agents spawning 50 subagents for simple tasks and searching endlessly for
  nonexistent sources; they added explicit effort-scaling rules. FAIR-RAG independently shows both
  premature sufficiency and over-retrieval: 24.5% of sampled errors came from its controller, while
  extra iterations eventually degraded output.

**Disconfirming evidence.** Fixed small budgets can miss a rare decisive source. The answer is not a
hard universal round cap. Use claim/gap state plus monotonic cost: stop only after load-bearing gaps are
closed or explicitly unresolved, a fresh alternate-channel/origin probe adds nothing, and a later
confirmation pass adds nothing. Always retain a wall/read cap and label cap exhaustion honestly.

## Claim 6 — independence and output hierarchy are valuable safeguards, but downstream of claim-specific evidence

**Verdict: important, incompletely implemented, not the main current bottleneck.**

The prod origin clustering is better than domain counting, but the repository audit at commit
`52aaca93d48a4645ec9da73ba55219268f8af902` documents that it does not systematically model shared
authors, institutions, datasets, funding, press releases, or multiple papers from one study. More
importantly, the run-wide “independent origins” count is not claim-specific corroboration. A survey can
therefore show many origins while a load-bearing conclusion remains single-origin.

The creatine bakeoff illustrates the failure: several reviews repeatedly pooled the same small RCT
set, while decisive outcomes depended on which run happened to retrieve EFSA or the largest trial.
More branches and domains did not make those duplicated underlying studies independent.

**Aletheia implication.** Put origin independence on claim-evidence edges, not on the run headline.
The navigable tree should show, per claim, support and contradiction spans, origin clusters, common
dataset/author/funding links, and missing corroboration. This is where hierarchical presentation is
genuinely useful: it lets a calling agent drill from the conclusion into a claim dossier without
mistaking artifact volume for independent confirmation.

## Decisive test that would change this verdict

The adversary position should be rejected if a frozen, multi-topic A/B shows that a hierarchical
Aletheia variant beats a strong flat or claim-ledger workflow under the **same candidate pools, primary
read attempts, wall clock, model, verifier, and answer-length band**, with gains in decisive-primary
recall, must-cover recall, atomic support, contradiction discovery, and claim-specific independent
origins—and no material domain regression. No existing Aletheia experiment meets that standard.

The strongest current pro-hierarchy evidence (Anthropic and WebWeaver) establishes narrower claims:
parallel breadth can buy coverage and section-scoped evidence can protect attention. It does not show
that deeper recursive synthesis is the highest-value next improvement to prod.

## Gaps and provenance limits

- No cost-matched, human-calibrated A/B directly compares Aletheia's current tree with a strong flat
  claim/evidence workflow on open-ended long-form field surveys.
- Aletheia's existing promotion evidence is small-N and largely LLM-judged. The dynamic-outline test
  is explicitly invalid as a cost-matched comparison: 97 versus 41 persisted reads.
- Anthropic's 90.2% result is internal, opaque, and confounded by roughly 15x chat token use.
- WebWeaver and FAIR-RAG are author-run and largely LLM-judged; FAIR-RAG covers QA over finite corpora,
  not independent open-web field surveying. WebWeaver's hierarchy ablation is against a memory dump,
  not an equal-context flat writer.
- BrowseComp-Plus and the text-ranking paper share a corpus and research lineage. They are mutually
  informative ablations, not two fully independent replications.
- Brave was degraded; arXiv rate-limited transiently; GitHub was unauthenticated/rate-limited. The
  current live survey therefore lacks one independent web index and complete repository retrieval.
- There is no direct evaluation of an **agent consuming** a progressive output tree versus a flat
  bundle. That is the correct test for the user's proposed tree interface.

## Saturation log

- Rounds 1–4 established retrieval/reranking, MAS failure, and equal-token SAS-vs-MAS evidence.
- Rounds 5–7 deliberately sought decisive disconfirmation: Anthropic's production multi-agent win,
  long-context harm, and WebWeaver's hierarchy-positive ablation.
- Round 8 added an independent matched-compute, six-benchmark scaling study. It strengthened the
  task-conditional coordination conclusion but introduced no new bottleneck class.
- Round 9 targeted stopping and controller failure. It added non-monotonic iteration evidence and a
  200-error distribution (retrieval 32.5%, generation 31.0%, SEA 24.5%), leaving the ranking stable.
- Stop condition: two consecutive focused rounds changed qualifications and mechanism detail but not
  the ordering or the surviving design. Totals: 9 completed rounds, 11 manifests, 207 retrieved,
  9 selected reads, 7 manual full rereads. Further broad retrieval would now be evidence accumulation,
  not gap closure.
