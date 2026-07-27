# Production handoff audit

Audited commit: `addfaf6` (`aletheia-research 0.5.0-openai.1`)  
Baseline test result: 156/156 passing on 2026-07-27

## Observed output cliff

Preserved run:
`runs/aletheia-research/2026-07-10-124542-blind-magnesium-cramps-order2`

| Artifact | Lines | Bytes |
|---|---:|---:|
| `brief.md` | 72 | 4,606 |
| `bundle.md` | 9,077 | 950,921 |
| full-read artifacts | — | 908,252 |

The bundle places the synthesized brief after the node evidence and full reads. A caller must either
trust the 72-line top product or traverse almost a megabyte of concatenated material without a branch
map.

## The “full bundle” is not the full trace

At production `report.py:303-378`, `bundle()` includes findings, evidence, telemetry, source lists,
and optional reads. It does **not** include node `decisions.jsonl`, `questions.jsonl`,
`answers.jsonl`, `spec.md`, `status.json`, or `proposal.json`, despite describing itself as the
complete research artifact set.

This matters in broad runs. The preserved 2026-07-13 agentic-coding-harness survey contains 182
logged decisions, including exact source-selection rationales, rejected candidate rounds, and the
local saturation decision. None appears in the production bundle.

## Existing strengths to retain

- The run directory is already a real evidence tree.
- Branch `findings.md` files are usually self-contained enough to serve as intermediate views.
- Raw reads, evidence packs, telemetry, source indexes, and decisions persist outside model context.
- `run.json` fingerprints the implementation, and final claim artifacts are hash-attested.

The experiment therefore adds an entry point and manifest rather than replacing the durable run.

## Direct baseline risks

1. **Context flooding:** full reads dominate the bundle and compete with synthesis for attention.
2. **False completeness label:** important provenance files are omitted.
3. **Answer-at-end orientation:** the most decision-relevant artifact is encountered last.
4. **No addressable map:** a caller cannot cheaply decide which branch or claim to expand.
5. **Transport/audience conflation:** “agent” is equated with “inline everything,” even when caller
   and worker share a filesystem.
6. **No content inventory:** there is no single machine-readable map proving that all artifacts are
   present or revealing duplicate bodies.

