# Independent project audit — 2026-07-28

## Scope

This directory contains a reproducible, evidence-backed audit of the Aletheia OpenAI project as it existed at the start of the audit:

- repository and runtime behavior;
- usability, reliability, performance, and operating cost;
- comparison with lighter-weight research workflows and relevant alternatives;
- an adversarial assessment of whether the project earns its complexity.

The auditor works on branch `codex/independent-audit-2026-07-28`; the audited baseline is recorded in `evidence/baseline.json`.

## Independence and limitations

The audit is performed from the repository checkout, but conclusions are based on observed code, documentation, tests, benchmark runs, and primary external sources where available. Findings distinguish verified behavior from inference. The project’s own research-channel health check was run before analysis; 11 of 13 core channels were live, while Brave was degraded without a key and Reddit returned HTTP 502. That source-coverage limitation is preserved in the evidence.

## Contents

- [`report.md`](report.md) — final independent assessment and recommended product direction.
- `evidence/` — command outputs, repository inventory, and cited observations.
- `benchmarks/` — reproducible performance and cost experiments.
- `comparisons/` — alternative-workflow research and comparison matrix.
- `notes/` — working notes and method log.
- `research-runs/` — ignored local Aletheia run state and fetched third-party pages used for
  verification; it is retained for replay without committing external page copies.

No production runtime files are modified by this audit.

## Repeatability convention

Future audits should use a new date-and-slug directory under `audits/`, record the exact audited
commit and stable runtime tag in `evidence/baseline.json`, keep generated fixtures and raw third-party
reads ignored, and commit only the human-authored report, reproducible scripts/results, and compact
evidence records. This prevents an audit from silently changing the product or bloating the repository
with web snapshots.
