# Adversarial addendum — performance, cost, and complexity

**Scope.** Independent adversarial review of the frozen portable runtime at
`bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`, with emphasis on whether the
audit's performance/cost conclusion is warranted. This addendum does not
replace the exhaustive line reviews; it tests the interpretation of their
evidence and records one additional, hermetically reproduced scaling defect.

## Bottom line

The evidence strongly supports this narrower claim:

> Aletheia's default protocol is **not resource-governed** and can incur much
> more orchestration, repeated reading, and failure-mode latency than a bounded
> single-agent pass.

It does **not** support a measured claim that Aletheia is intrinsically “too
slow,” costs a particular amount, or loses to a particular Karpathy/other-agent
workflow. No run records host-model tokens, provider price, cache hits,
end-to-end clock time, or comparable scheduling. The runtime itself does not
make host-model calls; the skill asks the host to create workers and a verifier
([`SKILL.md:201-205,242`](../../.cursor/skills/aletheia-research/SKILL.md)),
while its Python telemetry measures retrieval/read artifacts and reader seconds
only ([`report.py:229-287`](../../.cursor/skills/aletheia-research/scripts/report.py)).

That distinction matters. The recommended product decision — bounded direct
work by default, Aletheia as an explicitly budgeted escalation — remains well
supported. A categorical *performance ranking* does not.

## AD-01 — P2: the global index does not prevent cross-leaf re-reads

**Type:** confirmed cost/latency scaling defect, not an evidence-correctness
failure by itself.

The code has a run-global `index/sources.jsonl`, but it is bookkeeping for
deduplication/independence rather than a run-global source/read cache:

- [`investigate.py:547-550`](../../.cursor/skills/aletheia-research/scripts/investigate.py)
  reads only the current node's `sources.jsonl`, derives `already_read` only
  from that node, and forms `read_pool` only against those local records.
- [`treestate.py:391-414`](../../.cursor/skills/aletheia-research/scripts/treestate.py)
  appends every record to the node file. It suppresses only a duplicate *global
  index row*; it does not return an existing note, block the leaf read, or
  coordinate a shared content cache.
- [`investigate.py:590-612`](../../.cursor/skills/aletheia-research/scripts/investigate.py)
  therefore performs the selected full read independently for every leaf.

**Hermetic reproduction.** The audit-only
[`cross_leaf_reread.py`](probes/cross_leaf_reread.py) initializes a `quick`
run in a temporary directory, splits it into two leaves, gives both the same
local stub candidate, and replaces the reader with a local 2,250-character
response. Its checked-in [result](probes/cross_leaf_reread-result.json) and
an independent rerun produced:

```json
{
  "global_index_rows": 1,
  "per_leaf_note_counts": [1, 1],
  "reader_calls": 2,
  "urls_called": [
    "https://example.com/shared-paper",
    "https://example.com/shared-paper"
  ]
}
```

No network request was made. Thus one shared source can be read and placed in
model context once per overlapping framing even though the global index reports
one unique URL. The runtime telemetry can count the two read attempts, but it
does not label them as avoidable cross-leaf duplication or charge them to a
run-wide envelope.

There is a legitimate counterargument: independent workers may intentionally
re-read a pivotal source through different lenses, rather than inherit another
worker's summary. That is an epistemic choice, not a bug. The defect is that
the runtime makes it implicit, unmetered, and uncapped. A run-wide content
ledger should permit an explicit choice between (a) reuse a verified immutable
read, (b) request a separately justified independent re-read, and (c) pay and
record the duplicate work.

## What the code actually says about speed

Neither “serial” nor “parallel” alone describes the system.

| Property | Exact evidence | Consequence |
|---|---|---|
| Retrieval within a leaf is parallel | [`investigate.py:320-359`](../../.cursor/skills/aletheia-research/scripts/investigate.py) creates one executor task per supplied channel. | Normal channel fan-out need not add linearly to leaf wall time. With enough host capacity, parallel leaves can also reduce elapsed time. |
| Full reads within a leaf are serial | [`investigate.py:590-612`](../../.cursor/skills/aletheia-research/scripts/investigate.py) loops over selected records without an executor. | A slow selected source adds directly to that leaf's tail latency. The existing four-read stub probe supports this behavior. |
| Failure time is larger than the apparent timeout | [`_http.py:247-279`](../../.cursor/skills/channel-retrieval/scripts/_http.py) retries with sleeps; the boundary review documents additional adapter/browser retry layers and timeout floors. | A nominal per-call timeout is not a leaf or run deadline. This is a credible source of slowness, especially on degraded channels. |
| Leaf scheduling is outside this runtime | The skill directs the host to create one worker per leaf in parallel ([`SKILL.md:201-205`](../../.cursor/skills/aletheia-research/SKILL.md)); no scheduler, worker-slot limit, or total deadline exists in `treestate.py`/`investigate.py`. | Available agent slots, provider queuing, rate limits, and host behavior determine real elapsed time. It cannot be inferred from Python code alone. |

So the defensible statement is **high and unpredictable tail latency**, not a
universal latency ratio. Parallelism can hide wall-clock time while increasing
aggregate requests and model work; serial full reads and retry nesting make
the long tail real.

## Finite topology is a counterweight, but not a spend limit

The report should retain the qualification that `unlimited` is not literally
infinite in tree shape. [`treestate.py:199-207`](../../.cursor/skills/aletheia-research/scripts/treestate.py)
sets `unlimited` to 512 nodes/6 children and `max` to 2,048 nodes/8 children;
[`investigate.py:495-500`](../../.cursor/skills/aletheia-research/scripts/investigate.py)
removes the per-leaf round cap for both tiers.

Before races, those node/child caps permit at most 426 leaves for `unlimited`
and 1,792 leaves for `max` (`leaves <= N - ceil((N-1)/K)`). With the default
unit of four, one fully populated first round can select up to 1,704 or 7,168
full reads respectively ([`investigate.py:521`](../../.cursor/skills/aletheia-research/scripts/investigate.py)).
Those are *upper-bound scenarios*, not expected run counts: saturation can stop
earlier and a leaf can select fewer sources. They nevertheless show why a
topology cap is not a usable cost promise — and subsequent unlimited rounds,
manual primary chasing, and bundle handoff have no finite run-level bound.

The same caveat cuts both ways: do not describe the code as capable of an
actually infinite number of nodes, and do not mistake a 512-node guardrail for
a token/dollar/time reservation. The prescribed agent-mode bundle also inlines every
read with no per-read limit when `max_chars=0`
([`report.py:303-378`](../../.cursor/skills/aletheia-research/scripts/report.py));
this can move a large fraction of the research corpus back into a later model
context rather than solve the context-cost problem.

## What the controlled comparison establishes — and does not

The comparison is a useful but weak *quality hypothesis*, not a product
benchmark. Its authoritative post-audit factual result is a tie: **11/20 for
the direct baseline and 11/20 for the Aletheia-protocol condition**
([corrected results](comparison/results.md) and the
[independent method audit](comparison/independent-method-audit.md)). The
original blind record's 12/20 versus 11/20 and 0.62 preference for Output B is
preserved only as a historical qualitative observation; a rubric-credit error
means it is not a demonstrated factual win.

It is not cost or latency parity:

- The direct condition used one author/self-check and eight declared document
  assignments; the Aletheia condition used four leaves, a synthesizer, a fresh
  reviewer, and 28 assignments. The extra review may be exactly what bought
  the recorded qualitative preference; it did not establish a factual-score
  advantage and confounds any claim that the protocol is more efficient.
- Both conditions deliberately bypassed live retrieval. The result cannot
  validate router quality, reader success, retries, source identity, or
  real-world run speed.
- The metadata records creation/revision timestamps, but no controlled start/
  finish clock, queue state, tokens, model pricing, or cache state. It would be
  invalid to turn those timestamps into a latency ratio.
- One rubric, one packet, and one judge cannot estimate a general win rate.
  Moreover, the retained artifacts do not independently establish the claimed
  blinding, randomization, or workspace isolation.

There is also no defined “Karpathy workflow” implementation, model, task set,
or budget in this audit. Comparing Aletheia to that label would be rhetoric,
not evidence. The valid current alternative is the specific bounded direct
baseline used here; its result is “tied factual coverage with far less visible
orchestration,” not “universally better.”

## Calibrated conclusion and release implication

The local implementation is not inherently bloated: the portable closure is
small enough to inspect, standard-library-heavy, artifact-first, and has useful
parallel retrieval. Its complexity is **operational and epistemic**: a host
must coordinate multiple agents, mutable files, source selection, retries,
verification, and eventual context handoff. That complexity is defensible for
a genuinely consequential, human-supervised investigation; it is a poor silent
default for ordinary questions.

I would grade the claims as follows:

| Claim | Audit judgment |
|---|---|
| “The default lacks enforceable resource governance.” | **Confirmed, high confidence.** |
| “It can be materially more expensive in aggregate than a bounded direct pass.” | **Confirmed structurally, not dollar-quantified.** Worker/re-read multiplication and absent envelopes establish the mechanism. |
| “It is always slower.” | **Not established.** Tail-latency risk is confirmed; actual wall time depends on host parallelism and channel health. |
| “It is generally worse/better than alternatives.” | **Not established.** The corrected one-judge, unequal-resource exercise ties on factual coverage; its recorded qualitative preference is not independently validated. |
| “Use it as the default unlimited research workflow.” | **Not justified.** The current integrity and resource defects are sufficient to reject that product default. |

Before treating it as a high-stakes escalation, add a shared immutable
source/content ledger, an explicit re-read policy, global request/read/byte/
deadline/concurrency budgets, and host-model cost integration where the host
exposes it. Then run preregistered, repeated, matched-budget comparisons against
a specified bounded single-agent workflow and any named external alternative.
