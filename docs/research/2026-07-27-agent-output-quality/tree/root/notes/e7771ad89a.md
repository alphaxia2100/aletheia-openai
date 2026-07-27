<!-- aletheia://run/2026-07-27-101249/output-quality/internal-observations -->

# Internal operational observations

Captured: 2026-07-27  
Production implementation: `addfaf648ca5577e00e393b2cb1c692a6302eac2`  
Run runtime SHA-256: `486007f615c2d91c05dc928740967c6cd80bff8aef70f8bf16dd14710957a818`

This is a primary observation record for claims about Aletheia's own execution. It separates direct
filesystem/code observations from literature-derived claims. Paths are relative to the run root unless
otherwise stated. The preserved source files remain the authoritative artifacts.

## Run shape and cost

- `run.json` records `thoroughness=unlimited`, `verbosity=agent`, and the production implementation
  commit and runtime hash above.
- The tree contains one root plus six source-separated children: `adversary`, `architecture`,
  `evaluation`, `interface`, `methods`, and `practice`.
- Production `SKILL.md` requires one read-only worker per leaf at deep tiers and assigns bottom-up
  reconciliation and final authorship to the orchestrator. This is a specification/code observation,
  not a claim that every host will execute the instruction correctly.
- The six leaf `sources.jsonl` files contain 34 rows with `_read_ok=true`.
- `index/sources.jsonl` contains 668 unique URL rows.
- These are runtime counters, not evidence-quality claims. In particular, the 34 successful-read count
  is inflated by the identity mismatches below.

Reproduction commands:

```bash
find tree -name status.json | wc -l
jq -s 'map(select(._read_ok == true)) | length' tree/root/children/*/sources.jsonl
jq -s '[.[].url] | unique | length' index/sources.jsonl
```

Observed values: `7`, `34`, `668`.

## Wrong-document reads accepted as success

The interface branch contains two exact identity mismatches.

### PaperTrail candidate

Candidate record:

- expected URL/DOI: `https://doi.org/10.1145/3772318.3791101`
- expected title: *PaperTrail: A Claim-Evidence Interface for Grounding Provenance in LLM-based
  Scholarly Q&A*
- source row: `tree/root/children/interface/sources.jsonl`, OpenAlex work `W7131423702`
- persisted file: `tree/root/children/interface/notes/f399bd6717.md`
- runtime result: `_read_ok=true`, `_truncated=false`

Observed persisted body:

- title: *GRADE guidelines: 7. Rating the quality of evidence—inconsistency*
- observed DOI in body: `10.1016/j.jclinepi.2011.03.017`
- journal/year: *Journal of Clinical Epidemiology*, 2011

The expected and observed strong identifiers conflict. This is a mismatch, not a successful read.

### Systematic-review interface candidate

Candidate record:

- expected URL/DOI: `https://doi.org/10.1145/3742413.3789079`
- expected title: *From Toil to Thought: Designing for Strategic Exploration and Responsible AI in
  Systematic Literature Reviews*
- source row: `tree/root/children/interface/sources.jsonl`, OpenAlex work `W7133324275`
- persisted file: `tree/root/children/interface/notes/857a85841e.md`
- runtime result: `_read_ok=true`, `_truncated=true`

Observed persisted body:

- title: *GRADE guidance 36: updates to GRADE's approach to addressing inconsistency*
- observed DOI in body: `10.1016/j.jclinepi.2023.03.003`
- journal/year: *Journal of Clinical Epidemiology*, 2023

Again, the expected and observed strong identifiers conflict. The body was also truncated, but
truncation is a separate content-completeness state from identity.

Both mismatches are repeated verbatim in `tree/root/children/interface/evidence.md`. The runtime
therefore propagated the wrong bodies into the node evidence pack as if they were successful reads.

## Read gate and retrieval defects observed in the same run

- `tree/root/children/methods/decisions.jsonl` records a systematic-review/meta-research query routed
  as `products_consumer`; explicit academic-channel overrides were required.
- `tree/root/children/methods/telemetry.jsonl` and `evidence.md` show that focused named-method queries
  were prefixed with `agent-facing field-survey`, adding irrelevant lexical anchors.
- The methods worker recorded a 1,952-character anti-bot page counted as `_read_ok=true`.
- Primary publisher documents discovered through a web channel inherited `lead_gen`; the runtime mixed
  discovery channel with document epistemic role.
- Production `investigate.py` delegates success to the read result and records `_read_ok` without an
  expected-versus-observed identifier/title check. Length/readability can therefore establish content
  presence but not document identity.
- Production `SKILL.md` defines `unlimited` convergence as an agent judgment that new rounds add no
  distinct origins or claims. Its 512-node limit is described as a runaway backstop, not a target or
  a recall estimator. The run therefore records a stopping rationale but cannot certify open-web
  completeness.

These observations motivate separate retrieval, classification, and semantic-read experiments. They
do not estimate how often each failure occurs.

## Output handoff observations

The production `report.py bundle()` enumerates node `findings.md`, `evidence.md`, `telemetry.jsonl`,
`sources.jsonl`, and optionally notes. It does not enumerate `decisions.jsonl`, `questions.jsonl`,
`answers.jsonl`, `spec.md`, or `status.json`, despite describing the bundle as complete.

The isolated field-dossier result is recorded at:

`https://github.com/alphaxia2100/aletheia-openai/blob/b7c4814beaba3387e4ef9197950f2daab5c22761/docs/experiments/field-dossier-v06/results.md`

That record reports same-run reductions of 96.97% and 98.45%. On the narrow fixture the production
bundle was 950,921 bytes and the dossier was 28,782 bytes. It reports complete manifest/branch
coverage for the two fixtures (51/51 artifacts and 3/3 branches; 280/280 artifacts and 7/7 branches),
and a fresh-agent lookup result of 7/7 for the dossier versus 6/7 for the flat bundle.
The only outcome difference was an exact rejected-path rationale that production had omitted.
The candidate's regression record also states that the dossier embeds every branch synthesis,
exposes material decisions and claim verdicts, omits full reads from default context while retaining
references to them, and content-addresses the raw artifact manifest.

## Prior evaluation observations

- `docs/evals/2026-07-08-creatine-cognition-bakeoff.md` explicitly labels its result one topic/one run
  and retrieval-luck dominated.
- `docs/evals/openai-v0.5-forward-test.md` records 97 persisted reads for the dynamic-outline candidate
  versus 41 for baseline (2.37x), despite equal configured rounds. It also records a fresh verifier
  expanding 17 writer claims to 32.
- The preserved [high-accuracy forward-run audit](https://github.com/alphaxia2100/aletheia-openai/blob/2edfffbe5548a8a3e793f76213088b0d66a133f9/docs/experiments/high-accuracy-v06/first-forward-run-audit.md)
  reports that its positive national headline was absent from the claim denominator and contradicted
  the causal branch's `not identified` conclusion. The final coverage auditor added 7 of 21 claims.

These records support hard cost parity, whole-answer claim reconciliation, and an explicit
`inconclusive` promotion outcome. They do not establish a general win rate for any branch.

Production `report.py score` aggregates cited sources into one run-level origin/echo result. The
claim and verdict rows do not carry claim-specific origin requirements or origin-cluster verdicts.
Run-wide diversity therefore cannot establish that any particular conclusion is independently
corroborated.

## Final-brief claim-scope hash behavior

Production `report.py audit-claims` records SHA-256 values for the final `brief.md`, `claims.jsonl`,
and `verify.jsonl`. The scorer recomputes each value and reports `brief_changed_after_audit`,
`claims_changed_after_audit`, or `verify_changed_after_audit` when they differ. Repository regression
tests mutate the brief and verdict file after attestation and require `citation_complete=false`.
Therefore post-attestation edits are detectable within the local artifact model. This is not an
externally signed timestamp: a fully privileged actor could rewrite all files and hashes together.

## Channel limitations

The live doctor check on 2026-07-27 reported 14/15 core channels live. Brave was `warn` because no
API key was configured, removing that independent web index. GitHub was usable through the
unauthenticated 60-requests/hour pool; node traces also record transient GitHub 403 and arXiv cooldowns.

## Post-survey semantic read-identity experiment

The survey recommendation was implemented afterward on isolated branch
`codex/exp-read-identity-gate-v06`, commit `fa4b26d`, without changing `prod`. The record is:

`https://github.com/alphaxia2100/aletheia-openai/blob/fa4b26d/docs/experiments/read-identity-gate-v06/results.md`

- 164/164 repository tests passed (production: 156/156).
- On 11 portable exact-defect/boundary cases, production's effective length predicate was correct on
  7/11 with four false accepts; the candidate was correct on 11/11 with no false accepts or false
  rejects among five usable controls.
- Offline replay over all 34 production-success rows in this self-survey retained 30 and rejected the
  two exact ACM/GRADE identity mismatches, one anti-bot interstitial, and one arXiv “No HTML” shell.
- Every attempt records expected/observed identity, independent content state, content hash, resolver
  method, and preserved path. A retry cannot overwrite a prior wrong body.

This passes an exact mechanism diagnostic, not a production promotion gate. Broader multilingual,
legal, standards, books, code, forum, and publisher calibration plus resolver-recovery yield remain
untested.

## Coverage and sequencing qualifications after independent verification

The run has no counted inventory of language, book, newsroom, domain-specialist, or user-organization
coverage. Its retrieved corpus is visibly academic/technical, but the degree of under-sampling was
not measured. Likewise, no targeted absence-search protocol was preserved for a universal origin
ontology or a cross-domain dossier comparison; “not located among successful reads” is the strongest
defensible wording.

The root synthesis records recurring themes across source-separated branch findings—typed evidence,
provenance, selective context, primary resolution, failure/gap state, centralized reconciliation, and
layered output—but no claim-level origin map proves those themes are independently corroborated. The
survey also did not verify an integrated experiment covering the complete proposed evidence, control,
and delivery architecture; that statement is about this run's verification scope, not a universal or
project-history absence proof.

After a fresh verifier found 29 omitted load-bearing claims and 10 unsupported original rows, the
project sequence was restated as risk-based judgment rather than an evidence-ranked expected-value
result: retain the completed identity branch as experimental, harden whole-answer claim coverage
next, then test retrieval/reranking, with question graphs and stop control later. Exact resolver,
claim-graph, question-graph, stop-card, negative-memory, and evaluation schemas remain proposals to
test, not established field-wide requirements.

## Direct branch-state observations

Local Git refs and the pushed repository records were checked after the survey. These observations
establish project state only; they do not establish output-quality gains beyond the named diagnostics.

- `aletheia-prod-v0.5.0-openai.1` points to production runtime commit `addfaf6`; `prod` adds only the
  branch-navigation commit on top of that runtime.
- `codex/exp-field-dossier-v06` points to `b7c4814`; its result record reports a passed artifact and
  fresh-agent lookup diagnostic, while explicitly withholding promotion.
- `codex/exp-read-identity-gate-v06` points to `fa4b26d`; its result record reports the exact-defect
  diagnostic above, while explicitly withholding promotion.
- `codex/exp-claim-evidence-ledger-v06` points to `35fb82a`, whose commit adds `ledger.py`, ledger
  tests, skill instructions, and `docs/experiments/high-accuracy-v06/claim-evidence-ledger.md`.
- `codex/accuracy-observability-v06` points to `2edfffb`, whose commit adds the tracked-read and
  observability hardening recorded in `docs/experiments/high-accuracy-v06/results.md`; it is not on
  `prod`.

Direct records:

- `https://github.com/alphaxia2100/aletheia-openai/tree/aletheia-prod-v0.5.0-openai.1`
- `https://github.com/alphaxia2100/aletheia-openai/blob/b7c4814/docs/experiments/field-dossier-v06/results.md`
- `https://github.com/alphaxia2100/aletheia-openai/blob/fa4b26d/docs/experiments/read-identity-gate-v06/results.md`
- `https://github.com/alphaxia2100/aletheia-openai/blob/35fb82a/docs/experiments/high-accuracy-v06/claim-evidence-ledger.md`
- `https://github.com/alphaxia2100/aletheia-openai/blob/2edfffb/docs/experiments/high-accuracy-v06/results.md`

## Policy provenance after final coverage review

The report now distinguishes direct or externally supported results from authorial project policy:

- The seven-plane order is provisional risk/implementation judgment. This survey did not run a
  comparative value-of-information or expected-value study across those planes, and it does not
  establish whether output hierarchy is the main epistemic bottleneck.
- Retaining the source-separated portfolio is provisional policy; this survey did not A/B that
  structure against a one-model prompt asking for alternative perspectives.
- Because read, router, and channel failures were directly observed but no universal methodology rule
  was established, the report adopts a local policy to record tool failures and empty indexes as
  execution/coverage gaps and never interpret them as scientific null results.
- The exact claim/evidence graph rules, question-graph action vocabulary, monotonic resource ledger,
  and branch-release artifact list are unvalidated proposals or policies, not empirical requirements.
- Structural-origin clustering is implemented, but this survey did not quantify its comparative
  validity or predictive value against domain counting.
- Calling a revision-capable graph a potentially better semantic representation than the directory
  tree is an unvalidated project hypothesis; no comparison was run.
- The epistemic compiler, influence/echo maps, counterfactual dossier queries, compression-loss
  audits, and calibrated exploration portfolios are preserved as unvalidated experimental ideas, not
  implemented capabilities.
- Rejecting hierarchy as the main fix is current project policy derived from conditional examples,
  not a universal empirical rule for field surveys.
- The closing wider-reach, richer-output, and memory sentence states the intended test purpose; it is
  not a forecast that those outcomes have been or will be achieved.
