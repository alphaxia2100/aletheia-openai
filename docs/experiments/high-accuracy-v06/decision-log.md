# Decision log

Append entries; do not rewrite history. A reversal adds a new entry that names the superseded one.

## D001 — preserve the validated release

- Decision: tag `addfaf6` as `openai-aletheia-v0.5.0-openai.1-checkpoint` and branch experiments into
  a separate worktree.
- Why: installation and prior forward tests remain reproducible while aggressive changes proceed.
- Alternative rejected: experiment directly on the installed branch; it would destroy the rollback.

## D002 — operationalize the user's ceilings conservatively

- Decision: enforce 3,600 seconds, 40 reads per round, and 640 run-wide read attempts/artifacts.
- Assumption: “current cap” refers to the code-enforced four reads per round and the exhaustive tier's
  64-read theoretical maximum; both interpretations are enforced at 10×.
- Why: a wall-clock promise without runtime enforcement and a read promise without manual-artifact
  counting are not real caps.
- Revisit when: cap instrumentation or the user's intended denominator proves different.

## D003 — audit the evaluator before optimizing against it

- Decision: delegate an independent evaluator-validity audit and require known-defect meta-evaluation.
- Why: pairwise preference can reward length and polish while missing unsupported, stale, or omitted
  claims. Optimizing against a weak evaluator would select reward hacking.
- Alternative rejected: immediately restore the dynamic outline because two judges preferred it.

## D004 — keep mechanisms separable

- Decision: treat hard-cap enforcement, claim/evidence state, adaptive control, source acquisition,
  synthesis, and evaluation as independently testable changes.
- Why: a monolithic “high accuracy” prompt cannot identify causality or support rollback.

## D005 — start with a four-framing evidence portfolio

- Decision: investigate adaptive claim planning, retrieval/source quality, verification/evaluation,
  and working-system/adversarial evidence from distinct source bases.
- Leading hypothesis: a claim-and-uncertainty ledger with evidence-directed actions will outperform a
  prose outline alone.
- Adversary: extra planning/reads may amplify noise, context loss, echo, and evaluator gaming.

## D006 — treat the existing read cap as an accidental coupling

- Finding: `candidates --reads N` accepts the argument but the agent path never passes it into the
  gather step; selected reads remain `max(3, round(unit))`, normally four.
- Decision: do not increase `unit` to obtain more reads because that would also change round budgets.
  Add explicit per-round and run-wide read fields if this mechanism is implemented.

## D007 — do not call browser fallback rereads uncapped

- Finding: the real-browser reader uses `max_chars or 40000`; passing zero restores a 40,000-character
  cap even though the CLI describes zero as unlimited.
- Decision: record actual completeness and fix zero semantics before using a long browser-read source
  as decisive evidence.

## D008 — preserve deterministic plumbing, replace prose-only epistemic state

- Decision: retain fetch/dedup/provenance/hash machinery, but investigate a structured claim/evidence
  ledger and evidence-directed controller rather than adding another fixed outline prompt.
- Why: the current system cannot schedule work by claim risk or measure claim-specific corroboration.
- Status: provisional pending external research and evaluator audit.

## D009 — reject the legacy evaluator as an architecture selector

- Finding: the old evaluator detected only 8/24 frozen known defects, falsely allowed headline
  accuracy without a final claim-scope audit, reversed both blind source-choice results, accepted a
  one-anchor κ=1.0, and did not control order or verbosity.
- Decision: no prior dynamic-outline or source-triage preference is promotion evidence. Re-score it
  with the strict evaluator, and treat missing dimensions as `null`, not as wins or zeros.
- Consequence: architecture work may proceed on isolated branches, but the sealed forward set stays
  closed until a genuinely independent release gate exists.

## D010 — prefer evidence-addressed state over unconstrained dynamic planning

- Evidence: WebWeaver's focused section writer improved citation accuracy 86.73→93.37 and support
  90.95→98.73; outline/planner gains also appear in STORM and SciRAG. Conversely, FAIR-RAG reports
  sufficiency-controller errors, MRDRE finds 31% content-feedback breakage, and OpenScholar preferred
  the unrevised answer about 20% of the time.
- Decision: the first architecture candidate is an append-only atomic claim→span support graph with
  transactional history, not whole-outline rewriting or model-confidence stopping.
- Caveat: this exact schema is a design inference. Paper plausibility is not promotion evidence.

## D011 — isolate runtime integrity from answer quality

- Branch/commit: `codex/exp-runtime-ledger-v06` at `087a228`.
- Result: 160/160 tests pass. The candidate honors agent `--reads`, decouples reads from scrutiny
  units, makes browser `--max-chars 0` genuinely unlimited, and reserves work atomically before I/O.
- Decision: retain as experiment-integrity plumbing, but credit it with zero answer-quality gain.
- Remaining gap: manual reads are audited after acquisition and one in-flight network call can cross
  the elapsed-time threshold.

## D012 — freeze the first claim/evidence ledger candidate without promoting it

- Branch/commit: `codex/exp-claim-evidence-ledger-v06` at `35fb82a`.
- Result: 164/164 tests pass. Pending/background edges do not support; required facet checks and
  claim-specific origins fail closed; contradictions become disputed; exact spans are bound to
  hashed artifacts; evidence changes revoke support; stale stop probes are invalidated.
- Decision: freeze for matched-read forward evaluation. Structural defect tests establish invariants,
  not end-to-end accuracy.

## D013 — evaluator v2 remains a meta-evaluation harness

- Finding: evaluator v2 is fail-closed and its calibration artifact scores 24/24 versus 8/24 for the
  legacy evaluator, but the 24 judgments were self-authored rather than independent blind labels.
  Factual truth, answer recall, source quality, temporal correctness, and contradiction recall remain
  explicitly unmeasured.
- Decision: do not open the sealed topic set, merge a candidate, or update the installed Codex skill.
  A fresh model/human must supply topic rubrics and blind paired judgments first.
- Frozen artifact: `codex/exp-accuracy-eval-v2` at `b7c57c8`; 169/169 tests pass on Python 3.9 and
  3.12. An independent freeze review still found forgeable scope coverage, caller-controlled
  calibration, order-dependent tied-confidence AURC, tie-heavy inference, silent topic omission,
  agent-owned blind-copy risk, and incomplete immutable provenance. Status remains NO-GO.

## D014 — invalidate the original sealed forward set after accidental exposure

- Incident: an evaluator-development `rg` for fixture hashes printed the plaintext rows in
  `/tmp/aletheia-high-accuracy-design/sealed-topics.jsonl`. The evaluator author reported the exposure
  immediately and did not tune to topic contents.
- Decision: SHA-256 `c865e76aa07668669c6d26e798676028ea4af374ab4328d11bc08891ec2d4758`
  is permanently invalid for this release decision. Do not run it or describe it as held out.
- Replacement protocol: freeze evaluator and candidate commits first; have an external process/person
  create and retain a new topic set plus rubrics; reveal only opaque run IDs to the generation harness;
  unseal topics and labels once after all outputs and judge prompts are persisted.

## D015 — treat claim extraction as a measured failure surface

- Finding: the architecture research brief's writer extracted 16 claims; the independent whole-brief
  verifier added 17, so 52% of the final 33-claim denominator was absent from the initial claim set.
  It also caught one non-monotonicity overstatement and a percent-versus-percentage-point ambiguity.
- Final result: after correction and a complete second pass, 33/33 claims are supported, coverage and
  precision are both 1.0, and the exact artifacts have a valid content-hashed scope audit.
- Decision: a claim ledger does not solve claim recall by existing. Require independent final-brief
  extraction, compare writer/verifier claim sets, and report the added-claim rate as a first-class
  metric. High addition rates are an architecture defect even when final precision is perfect.
