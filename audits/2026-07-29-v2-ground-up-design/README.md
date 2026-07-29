# Aletheia v2 — ground-up architecture investigation

**Status:** completed design/audit dossier; no production v2 implementation is included.

## Decision

Do not make v2 a larger version of the v0.5 filesystem tree. Build a bounded
research-control kernel: one authoritative controller, finite run contracts,
capability-gated tools, immutable source receipts/artifacts, a typed
claim/evidence/verdict ledger, and truthful terminal states. Make a single
accountable lead the default. Treat fresh review, adversarial retrieval, and
parallel specialists as explicit experiments that must earn their latency and
cost against a competent direct baseline.

This is a safety and product recommendation, not a claim that v2 is already
better than managed research APIs or other agents. The only local controlled
comparison corrected to an **11–11 factual-rubric tie** while the elaborate
condition assigned 28 reads versus 8 for the direct condition. The project has
not established a general quality, speed, or cost advantage for its present
multi-agent ritual.

## Read in this order

| Document | Purpose |
|---|---|
| [v2-design.md](v2-design.md) | Integrated recommendation: product modes, architecture, invariants, service boundary, smallest vertical slice, and build gates. |
| [acceptance-contract.md](acceptance-contract.md) | Build-facing command/API contract and executable acceptance predicates for the first vertical slice. |
| [research/control-plane.md](research/control-plane.md) | Transaction/event ledger, fenced leases, reservations, capability gateway, state machines, recovery, and storage choices. |
| [research/workflows-and-alternatives.md](research/workflows-and-alternatives.md) | Independent comparison with direct, managed, open, and multi-agent alternatives; includes Karpathy-style evaluation discipline. |
| [research/adversary-and-evaluation.md](research/adversary-and-evaluation.md) | Destructive critique, fixture matrix, preregistered ablations, release rings, no-go conditions, and migration plan. |
| [decision-log.md](decision-log.md) | Durable design decisions, evidence basis, and explicit reversal conditions for future audits. |
| [audit-manifest.json](audit-manifest.json) | Machine-readable audit scope, constraints, artifacts, and limitations. |
| [validate_dossier.py](validate_dossier.py) | Standard-library validation of the manifest, required documents, and local Markdown links. |
| [research/channel-health-2026-07-29.md](research/channel-health-2026-07-29.md) | Point-in-time retrieval qualification: 12/13 core channels live; Brave degraded without an API key. |

The binding evidence about the current system is the earlier [deep runtime
audit](../2026-07-28-deep-runtime-and-head-to-head/report.md), including its
[corrected controlled comparison](../2026-07-28-deep-runtime-and-head-to-head/comparison/results.md).

## Scope and evidence boundary

This dossier investigated a replacement architecture from first principles. It
reviewed the frozen v0.5 audit, isolated experimental branches, project
evaluation records, direct documentation for selected alternatives, and three
independent design branches (control plane, workflows/alternatives, and
adversarial evaluation). It deliberately used an `exhaustive` bounded research
run rather than v0.5's unsafe default `unlimited` behavior.

It does **not** benchmark v2: no v2 exists yet. Nor does it establish a
cross-vendor quality ranking. Claims about external products are limited to
documented capabilities and are cited with their limitations in the research
artifacts. The raw retrieved bodies and mutable run state are intentionally
ignored; committed documents contain the reasoning, source indexes, decision
record, and links needed for a later audit to reconstruct the argument.

## Future-audit convention

Future architecture or performance audits should create a sibling directory
under `audits/YYYY-MM-DD-<scope>/` and include at least:

```text
README.md                 # conclusion, scope, read order
audit-manifest.json       # baseline hashes, limits, artifact inventory
research/                 # independent research and adversarial reviews
fixtures/                 # checked-in deterministic inputs/results, if any
decision-log.md           # keep/revise/revert decisions and reversal triggers
validate_dossier.py       # checks manifest and local references before commit
```

Raw network bodies, secrets, browser state, and mutable working runs stay
gitignored unless a specific legal/privacy review says otherwise. A future
benchmark must add frozen source packets, pre-registered rubric, anonymous
outputs, resource receipts, and a corrected-results protocol; a visually
impressive report is not an evaluation artifact.

## Non-changes

This folder makes no production runtime change. Existing uncommitted edits in
`.cursor/skills/channel-retrieval/scripts/doctor.py` and `tests/test_aletheia.py`
are outside this dossier and are intentionally not claimed, staged, or modified
by it.
