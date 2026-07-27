# Branch and version map

`prod` is the stable line. The immutable code checkpoint is tagged
`aletheia-prod-v0.5.0-openai.1`; the `prod` branch may receive documentation-only navigation updates
without changing that runtime.

Every experimental mechanism remains on its own branch until it clears a frozen promotion gate.
Inconclusive and failed branches are retained because their traces prevent repeated mistakes.

## Start here

| Line | Status | Purpose |
|---|---|---|
| `prod` | **production** | Stable OpenAI/Codex 0.5 runtime. Default GitHub branch. |
| `codex/exp-field-dossier-v06` | experimental, diagnostic passed, not promoted | Agent-first progressive-disclosure dossier and content-addressed artifact map. |
| `codex/exp-read-identity-gate-v06` | experimental, exact-defect diagnostic passed, not promoted | Typed expected/observed document identity and content gate with lossless failed-attempt provenance. |
| `codex/accuracy-observability-v06` | experimental, not promoted | Hash-chained chronology, persisted manifests, unified read/claim provenance, terminal consistency. |
| `codex/high-accuracy-candidate-v06` | experimental, not promoted | Side-by-side high-accuracy skill candidate. |
| `codex/high-accuracy-aletheia-v06` | research/integration record, no-go | Accuracy architecture, evaluator audit, and promotion decision. |

## Isolated mechanism branches

### Retrieval and source selection

| Branch | Mechanism |
|---|---|
| `codex/exp-safe-read-floor` | Prevent silent zero-read rounds without forcing irrelevant reads. |
| `codex/exp-claude-triage` | Agent-judged, topic-relative source triage. |
| `codex/exp-hardened-triage` | Triage invariants and failure handling. |
| `codex/exp-observable-triage` | Selector activation and cost telemetry. |
| `codex/exp-budgeted-triage` | Explicit triage retrieval/read cost bounds. |

### Evidence state, verification, and runtime integrity

| Branch | Mechanism |
|---|---|
| `codex/exp-claim-scope-gate` | Gate citation scores on final-brief claim coverage. |
| `codex/exp-hardened-claim-scope-gate` | Exact claim/verdict reconciliation and artifact hardening. |
| `codex/exp-claim-evidence-ledger-v06` | Atomic claim → exact evidence span → immutable read ledger. |
| `codex/exp-runtime-ledger-v06` | Enforced run-wide search/read/time reservations. |
| `codex/exp-traceable-runtime` | Executable runtime and channel fingerprints. |
| `codex/exp-accuracy-eval-v2` | Hardened accuracy evaluator and known-defect suite. |
| `codex/exp-read-identity-gate-v06` | Rejects mismatched, blocked, shell, and unverified bodies without deleting the attempted read. |

### Planning and outline evolution

| Branch | Mechanism / result |
|---|---|
| `codex/exp-dynamic-outline` | Evidence-conditioned question/outline growth. |
| `codex/exp-hardened-dynamic-outline` | Typed, safer outline evolution. |
| `codex/exp-budgeted-dynamic-outline` | Conserves unspent budget across evidence-driven splits; quality diagnostic used 2.37× observed reads and was not promoted. |
| `aletheia-0.5-bilevel` | Broader bilevel research/eval line and expanded held-out set. |

### Portability and lineage

| Branch | Purpose |
|---|---|
| `codex/openai-aletheia-v05` | Exact validated OpenAI 0.5 development/release line. |
| `codex/openai-aletheia` / `codex/bilevel-eval` | 0.5 design/evaluator groundwork. |
| `codex/exp-codex-only-install` | Codex installation without changing Cursor/Claude roots. |
| `main` | Older evaluator-foundation lineage; **not production**. |

## Release tags

Historical releases are immutable tags, including:

- `deep-aletheia-v0.2.0`
- `aletheia-research-v0.3.0` through `aletheia-research-v0.3.3`
- `aletheia-research-v0.4.0`, `v0.4.1`, and `v0.4.3`
- `aletheia-research-v0.5.0-dev.1` through `dev.3`
- `openai-aletheia-v0.5.0-openai.1-checkpoint`
- `aletheia-prod-v0.5.0-openai.1`

Tags identify immutable runtime points. Branches contain experiment chronology and documentation.

## Navigation recipes

```bash
# Stable code
git switch prod

# Inspect or test one candidate
git switch codex/exp-field-dossier-v06

# See only the candidate's history and changes
git log --oneline prod..codex/exp-field-dossier-v06
git diff --stat prod...codex/exp-field-dossier-v06

# Return to production
git switch prod
```

Use a worktree when two variants must run side by side. Never edit the baseline artifact or evaluator
result in place; create a new branch from the exact parent commit and record the mechanism, falsifier,
activation trace, observed cost, result, and promotion/rejection decision.

## Naming policy for the next experiments

- `codex/exp-<one-mechanism>-vNN`: isolated candidate.
- `codex/abl-<mechanism>-vNN`: feature-off ablation from the candidate.
- `prod`: only independently justified promotions and documentation.
- Tags: immutable releases/checkpoints, never moving aliases.

The first two post-production experiments both passed their narrow mechanism diagnostics but remain
unpromoted:

- `codex/exp-field-dossier-v06` improves agent handoff navigation without changing research mechanics.
- `codex/exp-read-identity-gate-v06` catches the exact wrong-body failures and preserves per-attempt
  provenance, but still needs broad resolver-recovery and false-rejection evaluation.

All local historical branches and release tags in this catalog were mirrored to GitHub on 2026-07-27.

## Research record behind the next sequence

The verified [2026-07-27 agent-output quality survey](research/2026-07-27-agent-output-quality/README.md)
preserves the synthesis, 97-claim ledger, semantic verdicts, branch findings, decision logs, operational
reproductions, and iterative independent-audit history. It recommends claim/evidence coverage and then
retrieval/reranking as the next isolated mechanisms; that ordering is provisional project judgment,
not a measured expected-value ranking.
