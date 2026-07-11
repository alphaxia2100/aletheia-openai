# First accuracy forward-run audit

Date: 2026-07-11  
Audit status: post-hoc (the exact topic rubric was not frozen before output)  
Tested runtime: `aletheia-research-accuracy 0.6.0-accuracy.1`, commit `32b389a`  
Run: `/Users/daemon1/Developer/Personal/Aletheia/runs/aletheia-research-accuracy/2026-07-11-111905-home-insurance-requirement-net-effects`

## Outcome

The answer is substantively useful and its 21 narrow final factual claims are generally well supported,
but the run does not validate the promised accuracy architecture. The original structural grader gave
85/B; the hardened grader gives **25/F**. The post-hoc semantic grade is **69/100**.

| Dimension | Weight | Score | Finding |
|---|---:|---:|---|
| Real-world factual correctness | 25 | 21 | The 21 extracted legal, numeric, and study-description claims are mostly supported by the captured primaries. The unsupported load-bearing inference is the positive national net sign. |
| Must-cover recall | 20 | 14 | Good treatment of mechanisms, distribution, force placement, underinsurance, and causal limitations. Earliest adoption, fifty-state history, ordinary-policy voluntary take-up, race/wealth heterogeneity, and covenant effects on credit terms remain unanswered. |
| Citation/claim support | 15 | 11 | Final rows have strong apparent entailment, but none maps to the atomic ledger and the headline conclusion was omitted from the denominator. |
| Decisive-source/source-role quality | 10 | 8 | Strong regulator, statute, contract, working-paper, and peer-reviewed sources. The decisive ordinary-covenant counterfactual does not exist in the run; flood analogues cannot settle it. |
| Contradiction, uncertainty, temporal handling | 10 | 6 | The brief carefully scopes old LPI evidence and current reforms, but contradicts its own causal branch by converting “not identified” into “probably helped.” |
| Accuracy architecture activation | 10 | 2.5 | Hardened structural score 25/100. |
| Decision usefulness | 5 | 3.5 | The affected-group analysis is useful, but the positive headline can steer a decision beyond the evidence. |
| Cost/cap discipline | 5 | 3 | About 3,195 seconds and 141 artifacts stayed below nominal ceilings, but only 86 reads were reserved and the run recorded no coherent termination. |

## Central semantic defect

The causal-counterfactual branch concluded:

> Not identified: whether the ordinary homeowners-insurance covenant has, on balance, helped or hurt
> Americans since implementation, or the magnitude of any national net effect. A categorical net
> verdict would exceed the causal evidence.

The final brief nevertheless said “probably helped on balance” in both its opening and final sentence.
The positive sign is not a directly sourced fact; it is an inference combining coverage benefits,
premium harms, voluntary take-up, and lender responses. It was absent from `claims.jsonl`, so 21/21
factual citation accuracy could not test it. At least seven other answer-level judgments (typical
mortgagor sign, lender benefit, LPI subgroup sign, and related assertions) also escaped the factual
claim denominator.

The appropriate conclusion from this evidence is: **the national incremental net sign is unknown**.
Coverage has demonstrated value, premium/LPI harms are demonstrated, and the covenant's incremental
effect depends on an unmeasured voluntary-coverage and lender-pricing counterfactual.

## Structural defects reproduced by the run

1. No unified chronology, run ID, exact request artifact, channel-health snapshot, worker/model
   lifecycle, command trace, synthesis history, or completion event.
2. `runtime-events.jsonl`, 156 node decisions, 111 telemetry rows, and 59 claim events use incompatible
   schemas and have no shared sequence/correlation identity. Logging existed, but replayable logging did not.
3. Candidate manifests were transient and deleted after selection, preventing selection-quality audit.
4. The triage subprocess serialized `ranked` and `read_pool` into separate objects. Read metadata was
   attached to one copy and the other was persisted: 80 successful engine reads became zero recorded
   engine artifacts; synthesis fell back to all search hits.
5. Forty-four full and seventeen decisive rereads bypassed the read reservation ledger. Verification
   fallback could do the same.
6. Reported elapsed time stopped at the last network reservation (2,416 seconds), omitting about 779
   seconds of synthesis/verification. Actual run duration was about 3,195 seconds.
7. Nine atomic ledger claims and 21 final claims had no IDs or reconciliation. The final answer could
   bypass the mechanism advertised as its epistemic source of truth.
8. `C9_identification_gap` remained unresolved with zero of two required origins, but `run.json` was
   still marked `complete`; the old grader awarded the separate deliverables gate.
9. The final coverage auditor added 7/21 claims (33%), a measured claim-recall weakness that did not
   affect the release grade.
10. Parallel workers updated the shared global source index without a locked atomic upsert; later read
    metadata remained node-local.

## Root cause

The design treated logs as several component artifacts, not as a cross-cutting architecture invariant.
Unit tests proved individual counters and ledgers but did not execute the subprocess boundary that lost
read identity, did not require replay of a source choice, and mocked the grader's happy path. The empty
smoke run proved fail-closed empty-ledger behavior but could not exercise multi-agent orchestration,
manual rereads, synthesis, or completion. The first real forward run was therefore the first true
integration test.

## Accuracy.2 hardening

Branch: `codex/accuracy-observability-v06`

- Locked, hash-chained `run-events.jsonl` with run/node/correlation IDs and elapsed time.
- Exact `request.md`, persisted `channel-health.json`, writer and worker/model lifecycle records.
- Immutable per-round candidate manifests and explicit selected/rejected URL events.
- Fixed subprocess read-metadata propagation; synthesis now fails instead of treating search hits as
  read evidence.
- `tracked_read.py` and instrumented verification fallbacks share the run-wide cap and provenance.
- Locked atomic global source-index upsert with read metadata synchronization.
- Full elapsed-time checkpoints across synthesis and verification.
- Root synthesis requires ledger completion or an explicit partial-result termination.
- Final claims require exact `claim_id`/text/source reconciliation with the ledger.
- Typed inferential claims require supported premises plus an independent argument verdict; an
  underdetermined net sign cannot become a positive prose conclusion.
- Hardened structural grading makes log, manifests, read identity, claim reconciliation, and lifecycle
  consistency release gates.

The preserved run is never retroactively repaired. Its missing provenance is reported as missing.

## Remaining limits

- The hash chain is tamper-evident relative to its current head, not externally signed or timestamped;
  a fully privileged developer could rewrite the whole chain.
- Worker/model/context identity is host-reported. Codex does not expose a signed model-attestation or
  token-usage receipt to this filesystem runtime.
- A host-native browser/tool call made outside the instrumented commands is invisible unless its
  artifact lands under the run (which creates an accounting failure) or the orchestrator logs it.
- Exact claim extraction and the quality of an inference verdict remain semantic judgments. The new
  gates make omissions and self-attestation harder to hide but do not turn an LLM into a truth oracle.
