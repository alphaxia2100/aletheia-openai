# Frozen source packet

All paths are evaluated at source commit `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`. The packet is
local and read-only; neither condition may retrieve outside it.

| ID | Path | Required issue it can settle |
|---|---|---|
| S1 | `.cursor/skills/aletheia-research/SKILL.md` | User-facing default, intended stop condition, worker/verification contract. |
| S2 | `.cursor/skills/aletheia-research/scripts/treestate.py` | Actual tier selection and structural tree caps. |
| S3 | `.cursor/skills/aletheia-research/scripts/investigate.py` | Per-leaf round behavior and read-success predicate. |
| S4 | `.cursor/skills/aletheia-research/scripts/report.py` | What persisted runtime telemetry can and cannot measure. |
| S5 | `docs/research/2026-07-27-agent-output-quality/internal-observations.md` | Historical wrong-body and routing/claim-scope evidence, with its prior-state limitation. |
| S6 | `docs/BRANCHES.md` and `docs/PORTABILITY.md` | Candidate versus stable release state and security boundary. |
| S7 | `docs/evals/openai-v0.5-forward-test.md` | Existing comparative-evidence denominator and the cost-parity failure. |

Line-level references must be cited in both outputs. S5 and S7 are first-party historical records;
they support documented observations, not a current prevalence or general-quality estimate.
