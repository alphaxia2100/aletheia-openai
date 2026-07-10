# Architecture and assumption audit of the checkpoint

Checkpoint audited: `addfaf6`. This inventory separates deterministic guarantees from instructions
that rely on an agent remembering to comply.

## 1. Scope and effort policy

| Decision | Current assumption | Strength | Accuracy risk / improvement question |
|---|---|---|---|
| Default `unlimited` | subjective saturation is safer than a fixed budget | permits depth | no wall-clock/read ceiling; “saturation” is not machine-observable |
| Tier budget | one `unit=4` buys one round and implicitly four reads | simple accounting | conflates reasoning rounds with source reads and source difficulty |
| Weighted children | contestedness weights can be judged before/after scouting | avoids uniform allocation | weights are uncalibrated prose judgments and cannot contract branches |
| Breadth-first order | early source diversity is valuable | limits anchoring | urgency and high-risk claims may deserve priority over tree depth |

The tree enforces node/depth/round caps for bounded tiers, but it does not enforce elapsed time,
run-wide reads, manual reads, or marginal-value stopping. `unlimited` and `max` have no true budget.

## 2. Framing and decomposition

- Four-to-six competing framings and an adversary reduce initial anchoring, but framing quality is
  asserted rather than measured against distinct expected evidence.
- The initial tree is fixed before evidence. `propose_split`/`materialize_proposal` exist, but there is
  no contraction, merge, reprioritization, or claim-driven scheduler in the shipped workflow.
- A split transfers all parent budget even when the parent already spent a scout round unless the
  orchestrator manually accounts for it; the quarantined dynamic experiment fixed this locally.
- Child output is prose `findings.md`; parent synthesis has no structured claim/evidence interface.

Candidate improvement: make claims, uncertainties, conflicts, and evidence gaps first-class state;
let evidence propose expand, merge, contract, corroborate, contradict, or stop actions under a
monotonic ledger.

## 3. Retrieval and routing

- Routing is a keyword taxonomy. It is deterministic and inspectable but brittle for mixed domains,
  unfamiliar terminology, and questions whose epistemic source class is not implied by nouns.
- Query anchoring and subject gates are handcrafted lexical heuristics. Agent triage reduces their
  authority but cannot recover a source absent from first-stage retrieval.
- Each round executes one query over a small channel set. There is no explicit query portfolio for
  synonyms, entities, dissent, temporal status, primary documents, or known counterclaims.
- Zero-result relaxation shortens queries, which improves recall but can silently change intent.
- There is no first-class backward/forward citation chasing, primary-source resolution chain, or
  source-version/as-of query despite these being core systematic-search techniques.
- Candidate snippets are capped at 280 characters and preserve result ordering, exposing judgment to
  missing context, position bias, keyword stuffing, and prompt injection.

Empirical relevance: recent BrowseComp-Plus work reports passage-level retrieval, correct BM25
normalization, reranking, and query-format matching materially change end-to-end answer accuracy.

## 4. Selection and reading

- Agent selection is topic-relative and can abstain, but its rationale is free text rather than a
  checkable decision record (question fit, source role, primary status, expected claim, novelty).
- `investigate.py candidates --reads N` parses `--reads` but does not pass it to
  `gather_candidates`; the agent path therefore remains implicitly capped at `unit` (four).
- Reads are sequential within a leaf and are considered successful at 1,500 characters; navigation
  chrome or a partial document can satisfy that threshold.
- The standard read cap is 40,000 characters. A documented `--max-chars 0` reread is uncapped through
  Jina, but browser fallback evaluates `max_chars or 40000`, silently restoring the cap.
- A URL hash identifies an artifact, but the content body, retrieval timestamp/version, source date,
  and HTTP validators are not bound into claim provenance.
- Direct/manual reads are counted after the fact but can bypass source-index metadata and hard limits.

Candidate improvement: enforce a run ledger before every search/read; persist content hashes,
retrieval/version dates, actual completeness status, and claim-relevant passages.

## 5. Evidence representation and independence

- `sources.jsonl` stores ranked retrieval records, while `notes/` stores read bodies. The link is
  optional for manual reads and a source does not declare which claim or passage it supports.
- Findings are requested as 3–8 claims but remain Markdown without a schema, atomicity check, scope,
  confidence, source spans, or contradiction state.
- Structural origin clustering catches URLs, identifiers, `derives_from`, and textual syndication,
  which is stronger than domain counts. It still does not systematically model common authors,
  institutions, datasets, funding, press releases, or one study reported through multiple papers.
- “Independent origins” counts are not claim-specific corroboration unless each cited source is
  explicitly attached to the same claim.

Candidate improvement: an append-only evidence ledger with atomic claims, quoted spans, source role,
origin cluster, support polarity, temporal scope, and independent corroboration requirements.

## 6. Synthesis

- One writer reduces inter-agent inconsistency, but synthesis is manual prose over compressed child
  findings. It can lose important caveats in notes or turn adjacent evidence into a broader claim.
- The thin-child gate uses a 120-character threshold, which measures length rather than answeredness.
- Required sections expose disagreement and gaps, but there is no pre-draft coverage matrix against
  the user's dimensions or evidence ledger.
- There is no deterministic numerical/unit consistency check, entity-resolution check, or explicit
  separation of observation, inference, forecast, and recommendation.

Candidate improvement: synthesize from an evidence table and dimension checklist; generate prose only
from approved claim rows and retain claim identifiers through verification.

## 7. Verification and temporal correctness

- The deterministic layer proves readability and lexical relevance, not entailment. This boundary is
  correctly stated.
- Whole-document overlap can select a nearby but non-supporting passage; only one “best” URL survives
  when a claim cites multiple sources.
- Final support is manually assigned by an LLM with no required quoted span, polarity decomposition,
  numerical check, population/intervention scope, source date, or current-status check.
- The final claim-scope audit hashes artifacts and prevents post-audit edits, but semantic completeness
  is an auditor attestation. It cannot prove omitted claims were found.
- No structured contradiction search connects mutually inconsistent claims or sources.

Candidate improvement: require atomic claim facets plus verbatim support/contradiction spans; run
separate polarity, magnitude/unit, scope, and temporal/version checks; retain all cited-source verdicts.

## 8. Scoring and evaluation

- Citation precision/coverage are code-gated, but the final support labels are model judgments without
  gold labels. A self-consistent verifier can produce 1.0 on an incorrect brief.
- There is no ground-truth claim-recall denominator, so a concise answer can omit decisive dimensions
  and still score perfectly.
- Pairwise judging covers completeness and calibration but is sensitive to verbosity, order, model
  self-preference, and topic contamination. The repository's trust gate requires a human anchor, yet
  recent forward tests are explicitly uncalibrated and small-N.
- Source count/independence do not measure source authority, decisive-primary recall, freshness, or
  whether corroborating origins support the same claim.
- Current topics mix frozen and development items; the Claude branch recently added more topics, but
  adding topics after observing a mechanism is not equivalent to a sealed held-out suite.

Required before selection: seed known defects into prior briefs, compare old/new evaluator detection,
seal fresh topics, randomize position, normalize presentation, and keep objective claim/source checks
separate from holistic preference.

## 9. Security and robustness

- The skill tells agents to treat snippets as untrusted but does not structurally delimit or sanitize
  retrieved instructions.
- Repository clones, rendered pages, community posts, and source notes can all contain model-directed
  text. There is no canary or injection-resistance eval.
- Network and channel failures are surfaced, but rate limits under parallel fan-out are not globally
  coordinated.

## 10. What should remain

The filesystem blackboard, immutable runtime fingerprints, explicit channel health, primary-first
policy, agent abstention, adversary branch, structural provenance, final artifact hashes, fresh-context
verification, and read-amplification accounting are valuable foundations. The next architecture should
extend these rather than replace them with an opaque autonomous loop.

