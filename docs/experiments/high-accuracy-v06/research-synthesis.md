# Research synthesis and architecture direction

This memo records the evidence used to choose experiments. It is not a promotion result.

## Most defensible conclusions

1. **Retrieval quality can dominate reasoning scale.** On 830 human-verified BrowseComp-Plus
   queries, passage BM25 scored 0.572 accuracy and BM25→monoT5 depth-50 scored 0.689 while using
   10.98% fewer searches. Query reformulation helped neural retrieval and hurt BM25, so query form
   must match the retriever rather than being globally “improved.”
   Primary: https://arxiv.org/html/2602.21456
2. **Evidence-responsive outlines help, but unrestricted revision is unsafe.** WebWeaver, STORM, and
   SciRAG support outline-guided planning. No located experiment isolates outline deletion, and
   MRDRE reports 31% breakage under content feedback. Changes should be typed patches with rollback,
   not wholesale regeneration.
   Primaries: https://arxiv.org/abs/2509.13312 · https://arxiv.org/abs/2402.14207 ·
   https://aclanthology.org/2026.eacl-long.303/ · https://arxiv.org/abs/2601.13217
3. **Focused evidence-addressed synthesis is the strongest near-term mechanism.** WebWeaver's
   section-scoped writer improved citation accuracy 86.73→93.37 and support 90.95→98.73 versus a
   whole-memory writer. This motivates claim→span context assembly before any larger planner.
4. **More retrieval is non-monotonic.** FLARE, SciRAG, and FAIR-RAG all report regimes where extra
   retrieval degrades quality. Evidence-derived gaps should allocate work; confidence never changes
   support state by itself.
   Primaries: https://aclanthology.org/2023.emnlp-main.495/ ·
   https://aclanthology.org/2026.eacl-long.303/ · https://arxiv.org/abs/2510.22344
5. **Citation chasing is discovery, not entailment.** Backward/forward citation traversal can recover
   terminologically disconnected sources, but citation edges can express disagreement, perfunctory
   attribution, or copying. Maintain separate discovery and atomic support graphs.
   Primaries: https://onlinelibrary.wiley.com/doi/full/10.1002/jrsm.1563 ·
   https://arxiv.org/html/2501.15067v1
6. **Open-web stopping has no validated recall estimator.** Finite-corpus screening supports
   statistical/confirmation stops and rejects simple “N irrelevant results” streaks, but those
   guarantees do not transfer directly to an unbounded web. Use an independent novelty probe plus a
   confirmation pass and label cap exhaustion honestly.
   Primary: https://doi.org/10.1186/s13643-020-01521-4

## Working-repository audit

- LangChain Open Deep Research, pinned `408da442a661ea5e40a6163329f82e3f22628949`: useful supervisor,
  parallel researcher, compression, and cap patterns; no claim→span ledger. Its inspected exception
  path contains `if is_token_limit_exceeded(...) or True`, which collapses recoverable errors into
  termination.
- GPT Researcher, pinned `18d405166948e11b4a0304c0c4ec440bead9e4a5`: useful search-informed
  subqueries and concurrent scraping; its curator explicitly errs toward inclusion and does not
  require a supporting span.
- Text Ranking in Deep Research, pinned `7d5b6444fd643a570b7cfaf5c5714e9f853541f9`: reproducible
  BM25/SPLADE/dense/reranking separation suitable for retrieval ablations.

Local clones: `/tmp/aletheia-high-accuracy-repos/`.

## Candidate architecture

```text
query portfolio → discovery graph → full immutable reads
                                  ↓
atomic claim requirements → exact evidence spans → verified support graph
                                  ↓
claim-risk scheduler → focused synthesis → independent coverage/adversary pass
```

Each new source updates claim support, contradiction, independent origin, scope, and time state.
Controller actions are typed and logged. Outline/report changes are staged and regression-tested.
Stopping requires closed load-bearing claims, surfaced disputes, a fresh alternate-channel/origin
probe, and a confirmation pass. Budget exhaustion is never described as epistemic completeness.

## Falsifiable evaluation order

1. Freeze evaluator code and hashes; acquire at least 30 independently labeled, class-balanced
   anchors and topic-specific truth/coverage/source/temporal rubrics.
2. Validate the evaluator on untouched defect cases and correct controls; require paired A/B+B/A
   order agreement and persist every judge artifact.
3. Compare fixed prose state versus claim/span ledger with identical candidate pools, reads, writer,
   answer length band, and verifier. Primary outcomes: atomic factual support, harmful omission,
   decisive-primary recall, contradiction discovery, and claim-specific independent origins.
4. Only if the ledger wins, cross it with passage reranking, one-hop citation chasing, and typed
   outline patches one mechanism at a time.
5. Evaluate read scaling separately in tranches; report marginal verified claims and origin novelty
   per read. A gain from uncontrolled extra work is a scaling result, not an architecture result.
6. Use the sealed 12-topic forward set once. Any failure reopens design; it must not become training
   data for the same release decision.

## Evidence limits

Most deep-research results are author-run, small, heterogeneous, and partially LLM-judged. No source
validates the combined architecture, explicit contraction, or open-web recall. Brave was degraded in
this research run, so DuckDuckGo/Marginalia and direct primary reads supplied web discovery. These
limitations lower confidence but do not erase the concrete defect tests or repository findings.

