# Independent method audit — controlled head-to-head

## Verdict

This is a useful **frozen-packet synthesis exercise**, not a valid general performance
comparison of Aletheia against direct-agent alternatives.  Its strongest supported result is:

> With the stipulated process, a four-leaf, centrally synthesized answer that received a
> fresh review was judged preferable by one judge on a single audit-shaped source packet.

It does **not** establish that Aletheia is better, faster, cheaper, more accurate on live research,
or worth its normal orchestration overhead.  More importantly, the reported factual win for Output B
does not survive a strict application of the comparison's own rubric: the defensible factual score is
**11/20 for A and 11/20 for B**, with a qualitative preference recorded but not independently
verifiable as blind.

This audit preserves the original judgment rather than editing it.  The correction is about the
interpretation carried forward from it.

## What I independently verified

| Check | Result | Evidence |
|---|---|---|
| Frozen packet identity | **Pass.** I recomputed SHA-256 for all eight files from `git show bd5e1a5:<path>`; all eight equal [source-fingerprints.json](source-fingerprints.json). | [source manifest](source-manifest.md) says the packet is local/read-only at the frozen commit (lines 1–16). |
| Output integrity | **Pass, after artifact creation.** `output-A.md` is byte-identical to `direct-raw.md`; `output-B.md` is byte-identical to `aletheia-raw.md`; both hashes equal [blind-map.json](blind-map.json) (lines 4–14). | Current hashes: A `806731…f85d`; B `08fe9b…a09`. |
| Stated word-limit basis | **Pass.** Prose before the source tables is 1,182 words for A and 1,297 for B. | The recorded counts match [direct metadata](direct-metadata.json) lines 7–8 and [Aletheia metadata](aletheia-metadata.json) lines 33–35. |
| Same source packet / no retrieval | **Supported by the saved artifacts, not independently enforceable.** Both metadata files say no external retrieval, and the Aletheia tree declares constrained packet subsets. | [protocol](protocol.md) lines 12–19; [tree decision log](../research-runs/2026-07-28-192537-controlled-head-to-head/tree/root/decisions.jsonl) lines 1–2. |
| End-to-end Aletheia runtime exercised | **No.** The tree was initialized and split, but it has no notes, telemetry, populated `sources.jsonl`, claim audit, score, root findings, or final brief. The root run remains `investigating` and root node `split`. | [results](results.md) lines 62–65 expressly says retrieval and `report.py score` were not tested; see [run.json](../research-runs/2026-07-28-192537-controlled-head-to-head/run.json) lines 28–36 and the empty [source index](../research-runs/2026-07-28-192537-controlled-head-to-head/index/sources.jsonl). |

The runtime used to make the local tree records `cbed478…` and `git_dirty: true`, while the source
packet is `bd5e1a5…` ([run.json](../research-runs/2026-07-28-192537-controlled-head-to-head/run.json)
lines 24–26).  I separately confirmed the portable skill closure is byte-identical between those two
commits.  That removes a code-drift concern, but it does not create a reproducible, immutable record
of the comparison execution.

## Material scoring error

The judgment says it used an all-or-nothing rule: partial coverage is “Missing”
([blind judgment](blind-judgment.md) lines 13–15).  Rubric item 17 requires that the answer state
that the positive 0.5 evidence has **two favorable capped-triage topics**
([rubric](rubric.md) line 31).

Output A does state “two topics” ([output A](output-A.md) line 27).  Output B does not.  Its only
positive capped-triage example is the **biomedical** forward test; it never names the consumer test
or says there were two topics ([output B](output-B.md) line 23).  Yet row 17 credits B for describing
“the consumer and biomedical capped evidence” ([blind judgment](blind-judgment.md) line 38).  That
description is not present in Output B.  The underlying frozen source does contain both headings
([S7](../../../docs/evals/openai-v0.5-forward-test.md) lines 18–42), which makes this a grading error,
not a source error.

Therefore, under the stated rule, B loses one point: **A 11/20; B 11/20**.  The B preference cannot
be represented as a factual-score win.

Row 7 is also less secure than the judgment implies.  B accurately lists telemetry counters and says
they are post-hoc ([output B](output-B.md) line 13), but it does not explicitly say that there is no
model-token, dollar, or total-run wall-clock *ledger*—the omitted half of rubric item 7
([rubric](rubric.md) lines 18–19).  A generous reader can infer that from the enumerated counters;
a literal all-or-nothing reader can mark it partial.  I do **not** deduct it in the primary correction,
but it means B's score is plausibly 10–11, never a robust 12.

I found no other unambiguous factual-credit error.  The remaining scored items are either clearly
present/absent in both outputs or subjective in the same direction for both.  The 1–5 ratings remain
opinions, not measurements; their only evidentiary value is that this one judge preferred B's
calibration and organization.

### Exact recommended replacement language

Replace the first two sentences of [results.md](results.md) lines 10–12 with:

> The original blind judgment recorded a narrow preference for Output B, 12/20 versus 11/20.
> An independent method audit found that row 17 incorrectly credited Output B with naming two
> favorable capped-triage topics; it names only the biomedical test.  Applying the rubric's stated
> all-or-nothing rule changes the factual score to **11/20 versus 11/20**.  The result is therefore a
> one-judge qualitative preference in a tied, frozen-source exercise—not a demonstrated Aletheia win.

Keep the original [blind judgment](blind-judgment.md) intact as an historical record, and add this
qualification wherever the 12–11 result is cited.

## Hidden asymmetries and why they matter

### 1. This is not resource matched

The protocol intentionally compares one author/self-check with four leaf workers, one synthesizer,
and one fresh reviewer ([protocol](protocol.md) lines 23–31).  The declared read assignments are
8 for A versus 28 for B—12 leaf assignments, 8 synthesis reads, and 8 reviewer reads
([results](results.md) lines 30–42).  B's fresh review made a substantive correction: it required a
scope qualification that was then incorporated ([fresh review](aletheia-fresh-review.md) lines 13–15).

That is a legitimate *workflow feature*, but it is not a fair test of whether the Aletheia machinery
beats realistic alternatives at the same budget.  The causal contrast is a heavily staffed,
reviewed process versus a less-resourced single-author/self-check process.  A better control
would include at least a bounded direct agent plus an independent critic, and separately compare it
with four-leaf decomposition at equal token, call, and wall-time budgets.

The 28:8 figure is only an assignment-count proxy.  No model identity/version, reasoning setting,
input/output tokens, cache use, agent-turn log, provider price, worker start/end time, or scheduler
trace was captured.  It supports “more declared repeated reading and roles,” not “3.5× cost” or a
latency claim.  The protocol itself correctly excludes those outcomes ([protocol](protocol.md)
lines 17–19, 28–31).

There is an auditability asymmetry too: B has a retained draft and a reviewer memo showing a required
revision, whereas A's self-check is only asserted in metadata and the final prose.  That does not
invalidate either answer, but it means the treatment's review process is better documented than the
control's.

### 2. It tests a hand-executed subset of the product

The Aletheia condition used a real `deep` tree and four written leaf findings, but retrieval was
deliberately bypassed.  Every tree `sources.jsonl` is empty, there are no read notes or telemetry,
and the generated synthesis reports zero sources/origins.  Thus it exercises decomposition plus
human/model-authored artifact handoff; it does not exercise routing, retrieval, ranking, source
identity, read success, provenance, independence computation, claim verification, or scoring.

Calling it an “Aletheia protocol condition” is fair only with that qualifier.  It is not evidence for
the runtime features most relevant to live research performance or the project’s cost/quality claims.
The result document discloses part of this limitation ([results](results.md) lines 62–65), but the
headline “win” is easy to overread without it.

### 3. The task is confirmatory and internally sourced

The question asks whether a high-stakes run should be allowed without a resource envelope.  Its packet
is project code plus first-party historical records, and the portfolio's leading hypothesis is already
“Default is unsafe without a human resource envelope”
([portfolio](../research-runs/2026-07-28-192537-controlled-head-to-head/portfolio.md) lines 10–19).
The adversary is limited to the same seven internal entries.  This is reasonable for a code-audit
memo, but it cannot test open-web discovery, source diversity, source-conflict resolution, or whether
Aletheia finds a conclusion that is not prefigured by the packet.

The tree also has no source provenance records, so the protocol's independence mechanism is not
demonstrated here.  “Adversary” denotes a prompted role, not an independent evidence base.

### 4. Blinding, randomization, and isolation are asserted, not auditable

The mapping file says a `secrets` draw occurred before output creation
([blind map](blind-map.json) lines 1–3), and the protocol says the judge received only the two outputs,
question, packet, and rubric ([protocol](protocol.md) lines 33–37).  No pre-judgment commitment,
random draw record, judge prompt/transcript, sandbox/access log, or signed timestamp exists.  The
mapping, outputs, metadata, protocol, and rubric were untracked working-tree files when audited.
Their current hashes prove present-file consistency, not that labels were hidden or the rubric was
locked before authors wrote.

The detailed tree state is also ignored by this audit directory's `.gitignore`.  If it is not
separately preserved, a future clone receives the conclusions and metadata but not the local execution
state used to substantiate the four-leaf claim.

There is a concrete contamination opportunity: A's final file timestamp precedes B's draft by about
five minutes.  Since both conditions used the same shared workspace, no recorded access control
prevents the B side from seeing A.  This is **not evidence that it did**; it is evidence that
independence was not established.  The same problem applies to the judge, which had no recorded
filesystem isolation from condition-named raw files and metadata.

## What the comparison can and cannot support

It can support a hypothesis worth retesting: decomposition plus a fresh reviewer may improve
calibration on dense, adversarial code-audit writing.  It can also show that the direct answer was
already close: both reached the same decision, and after correction their factual coverage ties.

It cannot support a claim about:

- Aletheia's general answer-quality win rate, live retrieval quality, source correctness, or
  high-stakes reliability;
- dollar cost, token cost, throughput, latency, or quality per dollar;
- superiority over a cost-matched single-agent-plus-critic, Karpathy-style bounded workflow, or a
  managed research product;
- performance of `unlimited`, because the evaluated tree used `deep` and never performed unlimited
  retrieval/round behavior; or
- a causal effect of the Aletheia runtime rather than the extra workers, source allocation, reviewer,
  and bespoke prompt structure.

## Minimum credible follow-up

For a comparative claim, preregister and commit the task set, prompts, rubric, output hashes, model
IDs/settings, and random assignment before execution.  Run both sides in isolated workspaces; give
the judge only anonymously named final outputs in an isolated harness.  Record tokens, tool calls,
cache state, provider cost, wall time, and per-worker timing.

Use multiple held-out tasks with outcomes that can favor either workflow.  Compare: (1) a bounded
single agent, (2) the same agent plus fresh critic, and (3) Aletheia's actual end-to-end tree, with
matched resource envelopes.  Include frozen fixtures for retrieval/identity failures and live tasks
only when reproducible capture is permissible.  Use independent human/domain adjudication for the
high-stakes subset.  Report effect sizes, confidence intervals, abstentions, and failures—not a
single model-judge preference.
