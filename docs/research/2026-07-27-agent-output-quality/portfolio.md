# Hypothesis portfolio — How should Aletheia be improved as an agent-facing deep field-survey tool to produce more robust, nuanced, context-rich, adaptively navigable research while avoiding common agentic-research failure modes?

_(orchestrator writes 4-6 competing framings here before any search)_
# Competing framing portfolio

No framing is accepted in advance. The provisional leading hypothesis is that Aletheia's largest
output-quality constraint is no longer raw retrieval breadth but the conversion of a large evidence
tree into a navigable, decision-relevant model that preserves disagreements, mechanisms, and
uncertainty. The adversary branch is explicitly tasked with breaking that hypothesis.

## 1. Research-methods / epistemic-quality framing

Question: Which practices from systematic review, evidence synthesis, information retrieval, and
meta-research most improve the completeness, calibration, source independence, contradiction
handling, and useful nuance of an adaptive field survey?

Distinct source base: peer-reviewed primary studies, benchmark papers, systematic-review standards,
and scholarly indexes (OpenAlex, arXiv where methodologically relevant, independent web for standards).

## 2. Agent-architecture / durable-state framing

Question: Which architectures let research agents expand and revise a question tree, retain
provenance and rejected paths, manage context without destructive compression, and resume reliably
across workers and context windows?

Distinct source base: primary agent-system papers, open-source implementations and issue trackers,
technical reports, and code/QA ecosystems (arXiv/OpenAlex, GitHub, Stack Exchange, web).

## 3. Reader-and-caller interface / progressive-disclosure framing

Question: How should an agent-facing research artifact expose a compact map, branch syntheses,
claim-level evidence, unresolved contradictions, and full reads so a caller can choose its own depth
without drilling through raw worker transcripts?

Distinct source base: HCI and information-visualization research, sensemaking and progressive-
disclosure literature, documentation systems, and working examples in research products.

## 4. Practitioner / field-failure framing

Question: What failures and successful workarounds do builders and heavy users of deep-research
agents actually observe—query drift, citation laundering, shallow synthesis, duplicate sources,
premature stopping, context loss, instruction overload, and unusable artifact volume?

Distinct source base: GitHub issues and discussions, Hacker News, Reddit and first-hand engineering
reports as lead generation, followed to code, primary incident artifacts, or reproducible examples.

## 5. Evaluation-science / useful-experiment framing

Question: Which evaluations can distinguish a genuinely better field survey from a longer or more
confident one, while controlling search/read cost, judge bias, topic leakage, stochasticity, and
implementation non-activation?

Distinct source base: evaluation and measurement papers, benchmark protocols, judge-bias studies,
reliability literature, plus this repository's held-out A/B traces and score artifacts.

## 6. Adversary / strongest case against the leading hypothesis

Question: Is the proposed emphasis on richer hierarchical synthesis wrong—because Aletheia's real
bottleneck is retrieval recall, source selection, factual verification, orchestration compliance, or
excessive procedural complexity—and could a simpler competing workflow yield more accurate and more
usable outputs at equal cost?

Distinct source base: negative and null findings on multi-agent/deep-research systems, failure
analyses, simple-agent baselines, strongest competing research tools and workflows, and direct
A/B evidence from the repository. This branch receives the highest scrutiny weight.

## Known channel constraints at framing time

- Brave is degraded because no API key is configured; use DuckDuckGo and Marginalia as independent
  web indexes and record the loss of Brave coverage as a final gap.
- GitHub is live but unauthenticated and limited to 60 requests/hour; preserve quota for decisive
  repository and issue reads.
