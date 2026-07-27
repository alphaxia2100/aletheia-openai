# Aletheia agent-output quality survey — 2026-07-27

Status: **verified research record; documentation only; no candidate promoted**

Production runtime under study: `addfaf648ca5577e00e393b2cb1c692a6302eac2`  
Immutable tag: `aletheia-prod-v0.5.0-openai.1`  
Research mode: Aletheia `unlimited`, agent-facing output

## Outcome

The survey found that Aletheia 0.5 is a useful baseline but not a finished research system. It directly
reproduced wrong-document read success, final-answer claim-scope escape, retrieval/router defects,
opaque convergence, run-level rather than claim-level independence, and a compression cliff between a
short brief and a multi-megabyte flat bundle.

Two isolated candidates were implemented and kept experimental:

- `codex/exp-field-dossier-v06` passed its artifact-coverage and fresh-agent lookup diagnostic. It
  reduced the two same-run entry artifacts by 96.97% and 98.45%, preserved every referenced artifact
  and branch synthesis, and recovered 7/7 requested facts versus 6/7 from the flat bundle. It does not
  establish better research truth.
- `codex/exp-read-identity-gate-v06` passed 164/164 repository tests, improved the portable defect set
  from 7/11 to 11/11, and rejected four false-success reads on replay. It still needs broad calibration
  and resolver-recovery evaluation.

The provisional next sequence is: preserve the identity gate as experimental; harden whole-answer
claim/evidence coverage; test retrieval and reranking; only later test an adaptive question graph and
observable stop controller. This is risk-based project policy, not a comparative expected-value result.

## Verification and scale

- Six source-separated branches; 37 recorded research rounds.
- 668 deduplicated retrieved records and 131 persisted read artifacts, including 97 direct/manual
  primary-recovery artifacts not counted as engine-owned reads.
- 97 final load-bearing claims; 97 supported, none contradicted or unsupported.
- Citation precision and coverage: 1.0; final claim-scope audit: valid.
- 25 cited sources and 25 computed independent origins. This run did not produce claim-specific origin
  requirements, so that number is observability, not proof of corroboration.

Brave was degraded for the whole survey. GitHub was unauthenticated/rate-limited, and arXiv had
transient cooldowns. Absence statements in the synthesis are therefore coverage-qualified.

## Artifact map

- [Verified synthesis](synthesis.md)
- [Portfolio and competing framings](portfolio.md)
- [Atomic claim ledger](claims.jsonl)
- [Final semantic verdicts](verify.jsonl)
- [Claim-scope attestation](claim-audit.json)
- [Machine score](score.json)
- [Runtime provenance](run-provenance.json)
- [Internal operational reproductions](internal-observations.md)
- [Independent audit history](audit-history/README.md)
- [Branch syntheses](branches/README.md)
- [Material decision logs](decisions/README.md)

The complete 6.58 MB full-read bundle and 252 KB navigable experimental dossier remain in the original
local run directory; they are intentionally not duplicated into Git history. The curated files here
retain the synthesis, evidence claims, verifier state, branch reasoning, decisions, and provenance
needed to continue the work.
