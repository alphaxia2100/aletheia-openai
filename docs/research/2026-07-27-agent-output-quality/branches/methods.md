# Findings — research methods and epistemic quality

## Bottom line

Aletheia should be improved less by adding another generic search pass than by making its research state **claim-centred, origin-aware, type-aware, and replayable**. The strongest cross-method pattern is: retain the complete search and decision trace; expand adaptively from high-value sources; stop only when several convergence tests agree; model shared evidence origins so echoes are not counted as corroboration; preserve contradictions with their contexts; and return a layered evidence tree in which an agent can move from synthesis to claims, conflicts, source spans, and search history without reopening every worker trace.

The evidence below comes mainly from systematic-review methodology. That literature supplies useful design principles, not a validated recipe for open-domain research agents. Transfer to Aletheia therefore needs controlled A/B evaluation.

## Substantive claims

### 1. Make the search and selection process replayable, then peer-review it before expensive execution

**Status:** Corroborated by two related primary guideline efforts, although their contributor communities overlap and neither proves that compliant reporting produces a good search.

- [PRISMA-S (Rethlefsen et al., 2021)](https://doi.org/10.1186/s13643-020-01542-z) — **primary reporting guideline; Delphi, consensus conference, public review.** Quote: “the final checklist includes 16 reporting items” intended to verify that “each component of a search is completely reported and therefore reproducible.” It further says to document a strategy “exactly as run,” including the database/resource, platform or web address, and full strategies for all information sources.
- [PRESS 2015 (McGowan et al., 2016)](https://doi.org/10.1016/j.jclinepi.2016.01.021) — **primary search-peer-review guideline; systematic review, expert survey, consensus forum.** Quote: “structured PRESS could identify search errors and improve the selection of search terms”; its retained checks cover question translation, Boolean/proximity operators, subject headings, text words, syntax, and limits/filters.

**Implication for Aletheia:** persist a machine-readable replay record for every retrieval action: original question and structured intent; exact query; channel, index, interface/version and time; result order; inclusion/rejection rationale; resolver chain; parse quality; and source-span hashes. Add an optional PRESS-like, fresh-context search critic before high-cost branches execute. The critic should test missing concepts, invalid operators, unjustified limits, and source-class omissions. Reporting and conduct must remain separate scores: a perfectly replayable bad search is still bad.

### 2. Complex field surveys require adaptive source-network expansion, not database queries alone

**Status:** Strong single-origin empirical signal, supported by later consensus guidance; generalizability is limited because the audit concerned one complex health-services review.

- [Greenhalgh & Peacock (2005)](https://doi.org/10.1136/bmj.38636.593461.68) — **primary audit of 495 included sources.** Quote: “Only 30% of sources were obtained from the protocol defined at the outset”; 51% came from “snowballing” and 24% from personal knowledge or contacts. Their conclusion was that reviews of complex evidence “cannot rely solely on protocol-driven search strategies.”
- [PRISMA-S (2021)](https://doi.org/10.1186/s13643-020-01542-z) — **primary reporting guideline.** It treats backward and forward citation searching, browsing, registries, websites, and expert/author contact as distinct methods that should be explicitly recorded, including the base articles used for citation searching.

**Implication for Aletheia:** once a branch finds a decisive or unusually generative source, expand along backward/forward citations, related works, authors/research groups, named datasets, terminology, and cited dissent. Record discovery-path yield so the agent learns which expansion methods are productive for that field. Adaptivity should be conditional: the 30/51/24 result does not justify snowballing every narrow, settled query.

### 3. Stop on converging epistemic signals, not on budget exhaustion or one novelty counter

**Status:** Single-origin methodological synthesis; the source itself says comparative validation is weak.

- [Booth (2010)](https://doi.org/10.1017/S0266462310000966) — **primary methodological review of search-stopping approaches.** Quote: eight methods included “Capture–recapture,” commissioner feedback, a “Disconfirming case,” a known gold standard, known-item retrieval, diminishing returns, *a priori* stopping rules, and theoretical saturation. Crucially, “there has been very little formal evaluation of the specific strengths and weaknesses of the different techniques.”

**Implication for Aletheia:** expose a multi-signal stop card per branch rather than a binary `saturated` flag. Candidate signals include: marginal new claims; marginal new **independent origins**; stability of conclusions/confidence under query perturbations; successful retrieval of known landmarks; coverage of a deliberately sought disconfirming case; unresolved high-value questions; and estimated cost of the next round. Stop only when the relevant signals converge, and report residual risk. Capture–recapture or unseen-mass estimates can be experimental diagnostics, not universal gates, because source channels are dependent and their assumptions often fail.

### 4. Measure independent information origins, not documents, domains, reviews, or agreeing prose

**Status:** Corroborated across an original overlap study and a methodological extension, but not fully independent (Dawid Pieper is an author in both).

- [Pieper et al. (2014)](https://doi.org/10.1016/j.jclinepi.2013.11.007) — **primary empirical methods study.** Quote: only “32 of 60 overviews mentioned overlaps”; the study represented reviews × primary publications in a matrix and introduced corrected covered area (CCA) to quantify repeated primary evidence.
- [Ying et al. (2025), weighted CCA](https://doi.org/10.1017/rsm.2025.19) — **primary methodological extension.** Quote: “Double-counting primary studies can magnify certain findings and skew overall conclusions.” The paper notes that ordinary CCA “treats all primary studies equally” and proposes weighting by information contribution; it also cautions that “a low overall overlap does not necessarily indicate minimal duplicate information within all individual reviews.”

**Implication for Aletheia:** extend the current origin-echo concept into a claim–source–origin graph. Resolve multiple reports to the underlying study, dataset, event, legal decision, standard, or first-hand observation; retain review-to-primary descent; and record author/institution/funding/citation lineage as softer dependence edges. Report at least (a) document count, (b) unique underlying origins, (c) origin overlap among branches, and (d) influence-weighted origin concentration. Domain diversity must never substitute for origin diversity.

### 5. Treat contradictions as typed, decision-relative structure; do not smooth them into a consensus count

**Status:** Same-origin methodological lineage (GRADE 2011 plus its 2023 update), so this is authoritative guidance rather than independent corroboration.

- [GRADE inconsistency guidance (Guyatt et al., 2011)](https://doi.org/10.1016/j.jclinepi.2011.03.017) — **primary methods guidance.** Quote: inconsistency judgments consider “similarity of point estimates, extent of overlap of confidence intervals, and statistical criteria,” but should downgrade confidence particularly when some studies imply “substantial benefit, and others no effect or harm.” Explanations should come from a small number of *a priori* hypotheses; apparent subgroup effects may be spurious.
- [Updated GRADE guidance (Zeng et al., 2023)](https://doi.org/10.1016/j.jclinepi.2023.03.003) — **primary updated methods guidance.** Quote: inconsistency is “variability in results, not in study characteristics”; the same evidence can warrant different judgments depending on the target threshold or range. It says popular fixed I² thresholds are inappropriate without context.

**Implication for Aletheia:** each atomic claim should carry scope (population, time, place, intervention/exposure, outcome), polarity, magnitude, uncertainty, method, and decision threshold. A contradiction record should say whether sources differ in direction, magnitude, scope, outcome definition, or method. Explanations discovered after seeing the conflict must be labeled post hoc; unexplained decision-relevant conflicts reduce confidence. “Three sources agree, one disagrees” is not a synthesis until origin dependence, precision, scope, and relevance are considered.

### 6. Use evidence-type-specific synthesis and expose it as a navigable claim tree

**Status:** Corroborated in principle by two distinct frameworks for heterogeneous quantitative and qualitative evidence, with some overlap in the broader evidence-synthesis community.

- [SWiM guideline (Campbell et al., 2020)](https://doi.org/10.1136/bmj.l6890) — **primary reporting guideline for synthesis without meta-analysis.** Quote: its nine items require the rationale for study groupings, the synthesis method, examination of heterogeneity, presentation, and “limitations of the synthesis.” It warns that post-protocol regrouping should be reported so readers can assess whether findings influenced it, and explicitly says SWiM is a reporting guideline, not conduct guidance.
- [GRADE-CERQual introduction (Lewin et al., 2018)](https://doi.org/10.1186/s13012-017-0688-3) — **primary qualitative-evidence confidence framework.** Quote: confidence in each qualitative finding is assessed through “(1) methodological limitations, (2) coherence, (3) adequacy of data, and (4) relevance”; the authors describe the approach as emerging and emphasize preserving primary-study context.

**Implication for Aletheia:** replace a monolithic brief as the sole synthesis product with a layered artifact tree:

1. an index of major claims, confidence, and open conflicts;
2. one node per claim or tightly related claim family;
3. within each node, scope/context, evidence-type-specific synthesis, supporting and contradicting origins, quote spans, confidence concerns, and unanswered questions;
4. links to source notes and the exact search/decision trace that produced them.

Quantitative effects, qualitative mechanisms/experiences, legal rules, standards, first-hand reports, and expert interpretations should not share one generic authority rubric. A calling agent can read only the index, traverse disputed claims, or descend to primary spans without depending on opaque worker transcripts.

### 7. Optimize epistemic utility, not report length or source count

**Status:** Single-origin meta-research critique plus a design inference; it is disconfirming evidence against the simple hypothesis that “more synthesis” or a longer final report is inherently better.

- [Ioannidis (2016)](https://doi.org/10.1111/1468-0009.12210) — **primary meta-research investigation/commentary using PubMed surveys and empirical evaluations.** Quote: there is “massive production of unnecessary, misleading, and conflicted systematic reviews and meta-analyses”; same-topic meta-analyses may exceed 20, while “few systematic reviews and meta-analyses are both non-misleading and useful.”

**Implication for Aletheia:** make the user-facing/agent-facing distinction structural. The agent-facing product can be large because it is layered and selectively traversable; the top synthesis should grow only when it adds context, changes confidence, resolves disagreement, or exposes a decision-relevant gap. Track coverage of important claim families, independent-origin support, contradiction resolution, and provenance completeness—not paragraphs, citations, or worker count. This is an extrapolation: Ioannidis did not study research agents or output interfaces.

## Observed Aletheia-specific failure modes in this node

These are direct run traces, not claims from the external literature:

- **Router/category error:** the default router classified a systematic-review/meta-research question as `products_consumer`. Explicit academic-channel overrides were required. A domain classifier should expose confidence and salient terms, detect methods/meta-research as its own category, and warn when framing and routed channels conflict.
- **Anchor pollution:** the root-topic anchor prepended “agent-facing field-survey” to named-method searches. This reduced exact retrieval and caused highly cited but irrelevant “agent” and generic “survey” results. Keep subject constraints in structured retrieval fields where supported; do not blindly concatenate them into every lexical query.
- **Relevance gate failure:** round 1 admitted 12 OpenAlex candidates with `subject_hits=0`; the highest-ranked items were unrelated domain surveys. Citation count and weak lexical similarity overwhelmed subject fit. Require a nonzero semantic/subject entailment check before eligibility, and measure whether a candidate can answer the node question rather than merely share generic terms.
- **Discovery class was confused with evidence class:** primary publisher PDFs and full journal articles discovered through DuckDuckGo were labeled `lead_gen` because the class followed the discovery channel. Store separate fields for discovery channel/index, document type, epistemic role, and primary/secondary relationship.
- **Syntactic “read success” was not semantic success:** a 1,952-character anti-bot challenge was counted `read=ok`; a scanned PMC article contained metadata and page images but no usable body text; several publisher URLs returned paywall/cookie shells. A read-quality gate should detect challenges, login/paywall shells, image-only bodies, missing expected title/sections, and content mismatch; then automatically try DOI, PMC/Europe PMC, repository, HTML, and PDF/OCR resolvers before counting a successful read.
- **Manual primary chasing was epistemically necessary but operationally separate:** decisive full texts were recovered through PMC and uncapped rereads after normal reads failed or truncated. These actions must enter the same cost, provenance, and success telemetry as engine reads.

Relevant local provenance: `evidence.md`, `telemetry.jsonl`, `decisions.jsonl`, and the notes `c00db0537e.md` (anti-bot shell), `648b9229fe.md` (scanned article), plus `notes/full/` and `notes/decisive/` (manual primary recovery).

## Disconfirming evidence and tensions

- PRISMA-S and SWiM primarily improve **reporting**. They explicitly do not establish that the underlying search or synthesis is valid. Aletheia therefore needs separate trace-completeness and epistemic-quality gates.
- Greenhalgh and Peacock's adaptive-search result is one complex-review audit. Narrow questions with stable terminology may perform well with prespecified database searches; adaptivity can also introduce researcher degrees of freedom and confirmation bias.
- Booth found multiple plausible stopping rules but “very little formal evaluation.” No literature-backed universal saturation threshold was found.
- CCA/wCCA concern overlap among health reviews and primary studies. Mapping open-domain sources to underlying origins (events, datasets, standards, legal decisions, testimony) is harder, and sample size is often not a meaningful information-weight proxy.
- GRADE and CERQual are domain-shaped frameworks. Their principles transfer; their categories and thresholds should not be copied mechanically to every claim type.
- CERQual itself records a live methodological objection: some qualitative researchers argue that cross-study synthesis can damage the integrity and context of primary studies. Its answer is to preserve context and make confidence judgments transparent, not to deny the risk.
- Longer output can create redundancy, false authority, and navigation cost. The proposed tree is intended to expand recoverable context while keeping the top layer selective; whether it improves downstream agent decisions remains untested.

## Explicit gaps

1. No direct experiment located here tests these methods inside autonomous deep-research agents.
2. No validated cross-domain ontology was found for resolving documents to independent underlying origins or for weighting origin influence outside conventional studies.
3. No strong empirical comparison was found among multi-signal stopping policies for open-web field surveys.
4. No evidence yet shows that the proposed layered claim tree improves factual accuracy, calibration, downstream task performance, or user/agent comprehension versus a long brief plus raw bundle.
5. Search-channel health was incomplete during this node: Brave lacked a key and arXiv was temporarily rate-limited; DuckDuckGo, OpenAlex, Europe PMC, and direct primary resolution carried most retrieval.
6. Publication/dissemination bias, paywalled material, non-English evidence, books, practitioner communities, and first-hand field evidence were not comprehensively studied in this methods branch.

## Evaluation hypotheses for the parent

- A/B test current Aletheia against a **claim-tree + type-aware confidence** branch on broad, contested, and interdisciplinary topics. Blind graders should score omitted important perspectives, context preservation, contradiction fidelity, origin-level corroboration, citation support, and downstream question-answering from the artifact—not prose preference.
- Separately ablate replay trace, adaptive citation expansion, origin clustering, contradiction ledger, semantic read-quality gate, and multi-signal stopping. Equalize retrieval/read cost and count manual resolver work.
- Test navigation by giving a fresh agent follow-up questions that require (a) the top-level answer, (b) a disputed subclaim, and (c) exact primary support. Measure answer accuracy, time/reads, and whether it can identify what remains unknown.
