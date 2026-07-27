# Field-dossier v0.6 results

Status: **mechanism passed its first diagnostic; remains experimental and is not promoted**
Implementation checkpoint: `be26c9f`

## Executable checks

- Production baseline at `addfaf6`: 156/156 tests passed before any edit.
- Candidate checkpoint: 158/158 tests passed.
- New regressions prove the dossier embeds all branch syntheses, exposes material decisions and claim
  verdicts, excludes full reads from default context, content-addresses every raw artifact, detects
  duplicate bodies, resolves local links, and keeps the inline fallback complete/answer-first.

## Static same-run A/B

Both conditions were generated from the same completed research directory. No retrieval or synthesis
changed.

| Run | Production flat bundle | Candidate dossier | Reduction | Manifest coverage | Branches | Full reads | Local links | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Magnesium brief comparison (narrow) | 950,921 B | 28,782 B | 96.97% | 51/51 | 3/3 | 17 referenced, 0 inlined | 38/38 | pass |
| Agentic coding harness survey (broad) | 11,948,951 B | 185,020 B | 98.45% | 280/280 | 7/7 | 202 referenced, 0 inlined | 88/88 | pass |

Both manifests had zero missing/stale rows, hash mismatches, broken local links, or omitted branch
syntheses. The narrow production bundle placed the exact brief at byte 943,402 (99.51% through the
file); the dossier placed it at byte 1,359 (4.75%). On the broad run, root findings already duplicate
the brief near the front of the production bundle, so answer-offset is not a discriminating measure.

Static artifacts:

- `/tmp/aletheia-field-dossier-eval/magnesium/static-check.json`
- `/tmp/aletheia-field-dossier-eval/harnesses/static-check.json`

These paths are local working evidence, not committed benchmark fixtures.

## Objective downstream lookup diagnostic

Two fresh-context agents received identical seven-question tasks about the broad harness survey. One
could use only the 11.95 MB flat bundle. The other started from the dossier and could follow its
manifest/links. Neither could use the web.

| Task class | Flat bundle | Dossier tree |
|---|---:|---:|
| top recommendation | correct | correct |
| causal harness evidence / limitation | correct | correct |
| Ruflo security scope/qualifier | correct | correct |
| explicit evidence gap | correct | correct |
| exact rejected-candidate rationale | **absent / not found** | **correct, with `decisions.jsonl` line** |
| raw advisory artifact + quote | correct | correct |
| stars-as-effectiveness classification | correct | correct |
| total | **6/7** | **7/7** |

The flat evaluator used 15 read/search commands and correctly refused to invent the missing trace. The
dossier evaluator reported five classes of file/search operations; elapsed time and tool-call counts
were not instrumented comparably, so no speed claim is made. The one outcome difference is directly
explained by production `bundle()` omitting decision logs, not by prose style.

## Interpretation

The candidate passes the isolated handoff hypothesis's first diagnostic:

- it removes raw-context flooding without deleting evidence;
- it proves artifact/branch coverage mechanically;
- it exposes provenance that the production bundle falsely described as included;
- a fresh caller recovered one otherwise unavailable rejected-path answer.

It does **not** establish better research truth, retrieval, primary-source recall, contradiction
handling, or synthesis. The Aletheia adversary survey ranked output navigation seventh behind
retrieval/selection, whole-answer claim and inference verification, semantic read integrity, task-
aware coordination, stopping/cost control, and claim-specific independence.

## Decision

Keep `codex/exp-field-dossier-v06` as a usable experimental candidate. Do not move it to `prod` yet.
Promotion still requires the frozen multi-topic/repeated downstream protocol, a weaker-navigator
condition, observed elapsed/tool/token cost, and no regression in evidence use. The next independent
engineering experiment should target semantic read identity, because this self-survey twice accepted
unrelated document bodies as successful reads—a more direct epistemic failure than output layout.
