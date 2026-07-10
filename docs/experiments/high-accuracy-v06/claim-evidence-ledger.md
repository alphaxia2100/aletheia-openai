# Claim/evidence/span ledger experiment

Branch: `codex/exp-claim-evidence-ledger-v06`  
Base: `52aaca9`

## Factor isolated

Replace prose-only epistemic state with an append-only support graph:

```text
report sentence → atomic claim ID → verified relation → exact source span → immutable read artifact
```

Bibliographic citations remain discovery edges and cannot confer support. Claims become `disputed`
when independently verified support and contradiction coexist. Search priority is derived from claim
importance, contradiction, support deficit, and claim-specific origin deficit. Stopping requires a
fresh independent challenge and a later confirmation; any new claim/evidence/verdict invalidates both.

## Evidence and design choices

- WebWeaver's section-addressed evidence writer improved citation accuracy 86.73→93.37 and support
  90.95→98.73 over a whole-memory writer, although the result does not isolate this ledger schema.
- FAIR-RAG and SciRAG support gap-led retrieval, but FAIR-RAG attributes 24.5% of a sampled error set
  to sufficiency-controller mistakes; therefore controller confidence cannot certify support or stop.
- MRDRE reports 31% content-feedback breakage and OpenScholar retained the prerevision answer about
  20% of the time; therefore records are append-only and corrections never rewrite history.
- Citation-chain research supports discovery of terminologically disconnected evidence, but a
  citation edge can encode disagreement or attribution. The implementation keeps discovery and
  support graphs separate.

The exact schema is a falsifiable design inference, not a paper-proven architecture.

## Structural results

- 164/164 repository tests pass on Python 3.12 (156 checkpoint tests plus 8 ledger tests).
- A verified source without the required polarity/scope/numeric/temporal facets cannot support.
- A quote must exist inside a bound artifact; the artifact SHA-256 is rechecked on every audit and a
  later mutation revokes support.
- Run-wide source diversity cannot satisfy a claim's independent-origin requirement accidentally.
- Background/citation edges, pending evidence, stale stop probes, and conflicting evidence all fail
  closed in targeted defect tests.

## What this does not prove

These tests establish invariants, not end-to-end answer improvement. The branch must still beat the
prose workflow on sealed, matched-read topics under the frozen evaluator. Atomicity and semantic
claim completeness still require independent model/human judgment; exact spans can be cherry-picked;
origin keys can be mislabeled; and the current lock is process-atomic only on POSIX. Outline patching,
citation-chain acquisition, and controller-driven query generation remain separate experiments.

