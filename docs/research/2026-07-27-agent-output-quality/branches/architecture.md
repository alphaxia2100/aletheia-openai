# Findings — agent architecture and durable research state

## Bottom line

The strongest architecture is not “a bigger prompt” or “a longer final report.” It is a durable,
versioned research system in which (1) the question structure can change as evidence arrives, (2)
raw work is never destroyed by summarization, (3) an agent receives a small task-specific view of
that work, (4) every derived artifact has causal provenance, and (5) workers coordinate through
typed artifacts rather than lossy chat handoffs.

For Aletheia, the practical target is an **immutable event/evidence ledger plus a revision-capable
research graph plus several materialized output levels**. A tree remains a useful navigation view,
but it should not be the sole data model: research creates cross-branch dependencies, duplicate
questions, contradictions, merged hypotheses, and reopening conditions. “Lossless memory” should
mean **lossless on durable storage, selectively reconstructed in context**; no prompt can itself be
lossless at field-survey scale.

This is a design synthesis, not an already-established end-to-end result. Individual components have
primary support; no primary study found here evaluates the entire proposed architecture on deep,
source-independent field surveys. That missing integration test is the central experimental gap.

## Research basis and independence

Five gap-driven retrieval rounds produced 13 engine-tracked reads and 11 additional full primary
artifacts under `notes/decisive/`. The decisive origin families were: W3C PROV; OpenHands;
LangGraph; Google ADK; Microsoft Agent Framework; Anthropic Research; MindSearch (Shanghai AI
Lab/USTC); STORM/Co-STORM (Stanford OVAL); Reflexion; ExpeL; and HiAgent. STORM and Co-STORM
are one origin family, and ExpeL explicitly builds on Reflexion, so those are not counted as fully
independent corroboration. Vendor engineering reports are primary accounts of their own systems but
are not peer-reviewed comparative evidence.

## Claim 1 — the research structure should be an evidence-revised question graph, not a frozen decomposition

**Status: corroborated architecture pattern across two independent system origins; efficacy outside
web QA/knowledge curation is unverified.**

- **MindSearch, primary peer-reviewed system paper (ICLR 2025):** the WebPlanner represents
  information seeking as “a dynamic graph construction process,” decomposes a query into atomic
  subquestions, and “progressively extends the graph based on the search result” ([paper and code
  link](https://arxiv.org/pdf/2407.20183)). Its DAG explicitly represents sequential and parallel
  dependencies; executable graph operations also make malformed plans mechanically detectable.
- **Co-STORM, primary peer-reviewed system paper (EMNLP 2024; independent of MindSearch):** it
  “uses a tree-structured mind map … to dynamically organize collected information,” and “each piece
  of information is also associated with the question that leads to its retrieval” ([paper](https://aclanthology.org/2024.emnlp-main.554.pdf)).
  The mind map is updated by insert/reorganize operations and becomes the outline for a cited report.
- **STORM, primary peer-reviewed system paper (NAACL 2024; same Stanford origin as Co-STORM):**
  its pre-writing stage discovers perspectives, runs perspective-conditioned question asking, and
  curates the resulting information into an outline ([paper](https://aclanthology.org/2024.naacl-long.347.pdf)).
  Compared with an outline-driven RAG baseline, its articles were judged organized 25 percentage
  points more often and broad in coverage 10 points more often; this is supporting evidence for
  question/outline construction, not for source accuracy.

**Implication for Aletheia.** Keep the directory tree as a readable projection, but make the canonical
object a versioned, typed research graph. A question node should support `depends_on`, `refines`,
`contradicts`, `duplicates`, `merged_into`, and `motivated_by_evidence` edges. Useful branch states
include `open`, `active`, `answered`, `challenged`, `corroborated`, `single_origin`, `saturated`,
`refuted`, `merged`, `deferred`, and `reopen_if`. The initial portfolio is a prior, not a permanent
taxonomy. After every meaningful read/round, the orchestrator should be able to add a newly exposed
question, revise a question without erasing its former version, merge duplicates, or reopen a branch
whose assumptions were invalidated.

The most important adaptive operation is not “generate more children”; it is **turn a discovered gap
or contradiction into a first-class question with a causal link to the evidence that exposed it**.
Frontier priority can then use claim importance, uncertainty, contradiction, source independence,
expected information gain, and cost rather than depth alone.

**Disconfirming/limiting evidence.** MindSearch reports that facticity improved less than breadth
(the paper explicitly warns that detailed search results can distract the model from the initial
problem). STORM’s authors identify source-bias transfer and over-association of unrelated facts as
remaining failures. Co-STORM used an LLM-based automatic evaluation and a human study of only 20
people; its generated example bibliography also includes weak secondary sources. Thus a dynamic
graph can expand coverage while still expanding error. Aletheia must keep source selection,
independence, contradiction, and claim verification as separate gates.

## Claim 2 — durable control state must be explicit and separate from raw conversation history

**Status: corroborated implementation pattern across multiple independent production frameworks;
semantic quality benefit is not directly isolated.**

- **Google ADK, first-party implementation report:** “The fix isn’t a bigger context window. It’s a
  fundamentally different architecture – one where the agent’s state is explicit, durable, and
  decoupled from raw chat history” ([Google Developers](https://developers.googleblog.com/en/build-long-running-ai-agents-that-pause-resume-and-never-lose-context-with-adk/)).
  The example applies a state transition before the next inference and resumes from persistent
  storage after a process restart.
- **LangGraph, first-party implementation documentation:** checkpointers persist “a thread’s graph
  state as checkpoints,” while stores persist “application-defined data outside the graph state”
  ([persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence)). This separates
  thread-local execution state from cross-thread durable knowledge.
- **Anthropic Research, first-party production report:** its lead researcher saves its plan to memory
  because a context beyond 200,000 tokens will be truncated, then iteratively decides whether to
  spawn more workers or refine the strategy ([engineering report](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **Microsoft Agent Framework, first-party implementation documentation:** durable sessions survive
  restarts and “any worker can resume a session”; deterministic orchestrations replay after failure so
  completed agent calls are not re-executed ([repository documentation](https://github.com/microsoft/agent-framework/tree/main/docs/features/durable-agents)).

**Implication for Aletheia.** Use four distinct state strata:

1. **Control state:** phase, graph frontier, leases/owners, budgets, pending decisions, retries,
   runtime/schema version, and event cursor.
2. **Semantic research state:** questions, hypotheses, claims, evidence spans, contradictions,
   source-origin clusters, decisions, and reopening conditions.
3. **Immutable artifact state:** full source reads, candidate manifests, worker findings, raw tool
   results, and prior versions of every derived artifact.
4. **Transient context views:** the small, task-specific pack assembled for one model call.

Checkpoint at semantic boundaries (candidate set persisted, read completed, worker handoff accepted,
synthesis revision committed), not merely at arbitrary turns. Give external reads/tool calls stable
idempotency keys so replay cannot silently double-spend or duplicate evidence. Resume by rebuilding
the frontier from persisted state; do not ask the model to infer what happened from a transcript.
When code, schema, prompts, or models change, fork from the checkpoint into a new run revision with a
recorded migration rather than mutating the old execution in place.

**Disconfirming/limiting evidence.** Microsoft’s current durable agent implementation persists and
feeds the *full* conversation history, showing that durability and useful context management are
separate problems. Persisting pollution makes it recoverable; it does not make it relevant. Google’s
piece is a first-party tutorial rather than a controlled evaluation. Durable state also cannot make a
bad inference correct; it can faithfully resume the wrong plan.

## Claim 3 — an append-only typed event ledger is a strong substrate for replay, provenance, and versioning

**Status: normative provenance foundation plus one primary production-agent validation; the
application to deep research is a design inference.**

- **W3C PROV-DM, normative Recommendation:** “Provenance is information about entities,
  activities, and people involved in producing a piece of data or thing,” and the model covers usage,
  generation, derivation, agents/responsibility, bundles, and collections
  ([PROV-DM](https://www.w3.org/TR/prov-dm/)). The domain-agnostic model explicitly permits
  extensions.
- **OpenHands SDK, primary peer-reviewed production-system paper (MLSys 2026):** “At V1’s core lies
  an event-sourcing pattern treating all interactions as immutable events appended to a log”
  ([paper](https://arxiv.org/pdf/2511.03690)). It persists events incrementally, reconstructs state by
  replay, and detects incomplete conversations. Across 433 real SWE-Bench traces, median event
  persistence was 0.20 ms and median full replay 4.1 ms; in a 15-day rollout, the broader V1
  redesign reduced system-attributable failures from 78.0 to 30.0 per 1,000 conversations. The
  failure reduction is not attributable to event sourcing alone, but the measurements show its
  overhead need not dominate agent work.

**Implication for Aletheia.** Make an append-only run ledger canonical and generate mutable-looking
files (`status.json`, tree views, maps, scores) as projections. A minimal mapping to PROV is:

- **Entities:** source snapshots, quoted spans, candidate manifests, questions, claims, rejection
  records, worker findings, branch syntheses, context packs, and report revisions.
- **Activities:** route, retrieve, triage, read, reject, split, merge, synthesize, challenge, verify,
  compress, and publish.
- **Agents:** worker/model instance, orchestrator, verifier, human, and exact runtime version.
- **Relations:** `used`, `wasGeneratedBy`, `wasDerivedFrom`, `wasAttributedTo`,
  `wasAssociatedWith`, and `actedOnBehalfOf`, extended with `supports`, `contradicts`, `qualifies`,
  `duplicates`, `rejects`, and `reopens`.

Each event should carry an ID, timestamp, actor/model, runtime and prompt hashes, causal parent IDs,
input/output content hashes, and an idempotency key. A checkpoint is then `(event_cursor,
projection_hashes, schema_version, runtime_fingerprint)`. Prior summaries and decisions remain
addressable revisions instead of being overwritten. W3C bundles are a natural representation for a
worker’s self-contained provenance contribution and for provenance *of* a synthesis.

**Disconfirming/limiting evidence.** W3C PROV records lineage, not truth: a perfectly traceable claim
can still be false. OpenHands’ validation is principally single-agent software work; its paper says
multi-agent coordination “require[s] further design.” Event storage grows linearly, and the V1
rollout’s remaining failures included a condensation bug. The ledger therefore needs retention and
index policies, but raw evidence required for audit should remain content-addressed rather than be
destructively pruned.

## Claim 4 — context compression should be hierarchical and reversible by retrieval

**Status: corroborated by one peer-reviewed memory experiment and independent production/system
accounts; “lossless” refers to storage plus retrieval, not summaries.**

- **HiAgent, primary peer-reviewed paper (ACL 2025):** it replaces completed subgoal trajectories
  with summarized observations but supplies a retrieval operation for the detailed trajectory “when
  necessary” ([paper](https://aclanthology.org/2025.acl-long.1575.pdf)). Across five long-horizon
  tasks it raised average success from 21% to 42%, reduced context tokens by 35.02%, and reduced
  runtime by 19.42%. Removing trajectory retrieval reduced success by 10%, direct evidence that
  summary-only memory is insufficient.
- **Anthropic Research, first-party production report:** subagents can persist outputs directly to an
  artifact system and return lightweight references, which “prevents information loss during
  multi-stage processing” and avoids copying large outputs through conversation history
  ([engineering report](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **MindSearch, primary peer-reviewed paper:** each worker receives its local subquestion plus the
  root and relevant parent response; the paper reports that graph edges help transfer enough context
  without giving every worker the entire search history ([paper](https://arxiv.org/pdf/2407.20183)).

**Implication for Aletheia.** Build a recursively expandable artifact tree:

- **L0 — survey map:** root question, current conclusion set, branch states, decisive disagreements,
  unresolved gaps, and links downward.
- **L1 — branch syntheses:** mechanisms, subquestions, conclusions, counterevidence, and why the
  branch stopped.
- **L2 — claim cards:** atomic claim, status, supporting and contradicting spans, origin clusters,
  uncertainty, derivation history, and downstream dependents.
- **L3 — full artifacts:** reads, source snapshots, candidate sets, worker findings, failed paths,
  and the event trace.

A context assembler should select the smallest level adequate for the next decision and include
references that allow on-demand expansion. Every summary is itself a versioned derived entity with a
coverage manifest: source/claim IDs included, contradictions retained, omissions declared, and the
raw inputs it was derived from. Never overwrite the raw layer. This gives the caller the user’s
proposed “tree of outputs” without forcing it to read worker transcripts.

**Disconfirming/limiting evidence.** HiAgent evaluates deterministic/textual action environments,
not evidence synthesis, and an LLM-generated research summary can change polarity or erase a caveat.
OpenHands’ production rollout found a condensation bug among remaining SDK errors. The architecture
therefore needs a compression-loss check: a fresh verifier compares each summary to its input claim
set and reports omitted/changed claims. Retrieval must remain possible even after a branch is marked
saturated.

## Claim 5 — failed and rejected paths are useful memory only when their interpretation is validated

**Status: partially corroborated by two research systems, but methodologically dependent and not
tested on deep field surveys.**

- **Reflexion, primary peer-reviewed paper (NeurIPS 2023):** agents “maintain their own reflective
  text in an episodic memory buffer” for later trials ([paper](https://arxiv.org/html/2303.11366)).
  The system improved over strong baselines by 22 points on AlfWorld, 20 on HotPotQA, and 11 on
  HumanEval; it distilled long failed trajectories into future “self-hints.”
- **ExpeL, primary peer-reviewed paper (AAAI 2024; builds on Reflexion):** the system collects success
  and failure experiences, abstracts cross-task insights, and retrieves relevant successful
  trajectories ([paper](https://arxiv.org/html/2308.10144)). Its ablation found diverse
  success/failure experience superior to ReAct-only experience. Crucially, adding Reflexion’s
  reflections to insight extraction *hurt* HotPotQA performance (29% versus 39% for ExpeL); the
  authors attribute this to reflections sometimes hallucinating and misleading extraction.

**Implication for Aletheia.** Preserve a rejected path as a structured **negative-memory card**, not
as an unqualified lesson:

- attempted question/query/source/branch and pointer to the raw trace;
- rejection/failure class (`no_evidence`, `duplicate_origin`, `off_topic`, `tool_failure`,
  `contradicted`, `low_value`, `budget_deferred`, `unsafe`, or `superseded`);
- who/what rejected it, why, the evidence available then, and confidence;
- expiry or explicit reopening trigger (new source class, changed date, contradictory primary,
  better tool, or parent assumption invalidated);
- whether the record is a local execution failure, a scientific null result, or substantive
  disconfirming evidence—these must never be conflated.

Only retrieve negative memory relevant to the current question. Promote a failure-derived reusable
rule only after paired success/failure comparison, repeated consistent failures, or an independent
verification pass. Keep both the raw trace and the derived rule so the latter can be challenged.

**Disconfirming/limiting evidence.** Reflexion itself says it depends on the model’s self-evaluation
and has no formal success guarantee; its experiments retain only one to three reflections because of
context limits. ExpeL shows that plausible reflections can actively degrade performance. Neither
paper studies rejected literature-search paths, where a “no result” may reflect index coverage or
query choice rather than absence of evidence.

## Claim 6 — multi-worker research should use branch ownership plus a shared artifact blackboard, not unrestricted shared mutation

**Status: corroborated production pattern with strong caveats; concurrency semantics remain an open
design problem.**

- **Anthropic Research, first-party production report:** without detailed objectives, output formats,
  tool/source guidance, and boundaries, workers “duplicate work, leave gaps, or fail to find
  necessary information” ([engineering report](https://www.anthropic.com/engineering/multi-agent-research-system)).
  The same report recommends persistent artifacts with lightweight references to avoid the
  coordinator becoming a game of telephone.
- **Co-STORM, primary peer-reviewed paper:** its dynamic mind map “track[s] the discourse and
  construct[s] shared knowledge,” while a moderator injects directions based on relevant information
  that prior turns did not use ([paper](https://aclanthology.org/2024.emnlp-main.554.pdf)). This is a
  concrete blackboard/moderator pattern, although it is optimized for interactive discovery.
- **W3C PROV-DM, normative Recommendation:** delegation records that a delegate acts on another
  agent’s behalf while the delegator retains responsibility ([PROV-DM](https://www.w3.org/TR/prov-dm/)).
  This supplies a useful responsibility model for worker-produced claims and orchestrator synthesis.

**Implication for Aletheia.** Give each worker an exclusive branch lease and let it append events and
artifacts within that branch. Workers publish typed deltas—new question, claim, evidence span,
contradiction, gap, rejection, or saturation proposal—to a shared blackboard projection. The
orchestrator (or one designated merger) is the single writer of canonical cross-branch synthesis.
Use content hashes/expected revisions for optimistic concurrency; a stale worker contribution is
preserved but must be rebased or explicitly rejected, never silently overwrite newer state.

Separate two planes:

- **Control plane:** leases, priorities, retries, backpressure, cancellation, versions, and resume.
- **Evidence plane:** immutable source/artifact objects and typed provenance relations.

This supports asynchronous workers without requiring them to stream their full contexts to one
another. A worker handoff contract should require claim cards, exact evidence spans, counterevidence,
gaps, and a stop/reopen rationale; prose findings remain a view of that structured contribution.

**Disconfirming/limiting evidence.** Anthropic reports multi-agent research uses about 15 times the
tokens of chat and is a poor fit when agents require shared context or have many dependencies. Its
current synchronous design blocks on slow workers, but it warns that asynchronous execution adds
state-consistency and error-propagation problems. LangGraph notes that subgraphs have separate
checkpoint namespaces and parent state may not immediately see child updates. OpenHands’ primary
paper likewise says multi-agent coordination still needs design. Therefore, do not allow arbitrary
concurrent writes to one mutable `findings.md` or one global model-visible memory.

## Recommended Aletheia target architecture (design inference)

The six claims imply a compact architecture that preserves Aletheia’s useful file-first character:

| Layer | Canonical durable artifact | Model-visible projection |
|---|---|---|
| Event/provenance | append-only typed events + content-addressed blobs | only events relevant to the current action |
| Research graph | versioned questions, claims, evidence spans, decisions, contradictions | current subgraph/frontier |
| Branch workspace | worker-owned immutable revisions + lease/checkpoint | branch context pack |
| Synthesis | versioned claim/branch/root projections | L0/L1/L2 expandable views |
| Runtime | fingerprinted prompts/models/tools/channels/schema + event cursor | resume capsule |

One possible event shape is:

```json
{
  "event_id": "...",
  "type": "read_completed",
  "actor": {"worker": "architecture", "model": "...", "runtime_hash": "..."},
  "caused_by": ["question:...", "candidate:..."],
  "used": ["source_snapshot:..."],
  "generated": ["read:...", "span:..."],
  "idempotency_key": "...",
  "timestamp": "..."
}
```

The event store need not be the interface agents edit directly. Existing directory artifacts can be
projections for legibility, while a small SQLite/JSONL index provides graph queries, leases, and
replay. The critical invariant is that a projection can be regenerated and that no summary, status
change, or merge destroys the source artifacts or the former revision.

## High-value, non-toy experiments

These tests target the architecture’s actual failure modes rather than rewarding verbosity:

1. **Adaptive graph A/B:** at matched successful-read/tool/token cost, compare the current fixed tree
   with a graph that can add/merge/reopen questions. Use held-out field surveys containing important
   subquestions not obvious from the initial query. Measure discovery of those questions, supported
   claim coverage, contradiction retention, and duplicate-origin work—not report length.
2. **Compression recoverability:** compare flat worker summaries, hierarchical summaries only, and
   hierarchical summaries plus raw retrieval. A fresh verifier receives successive L0→L3 views and
   tests whether it can recover randomly sampled supported claims, caveats, dissent, and unresolved
   gaps. Record polarity changes and silent omissions.
3. **Negative-memory ablation:** no failure memory vs. raw failed traces vs. validated negative-memory
   cards. Measure repeated failed queries, false suppression of later-valid paths, and downstream
   factual accuracy. ExpeL predicts that unvalidated reflective lessons may be worse than no lesson.
4. **Crash/replay test:** inject termination after every semantic boundary and compare the final
   projection hashes, read charges, and source set with an uninterrupted run. This tests actual
   idempotence and resume rather than the presence of checkpoint files.
5. **Artifact-handoff A/B:** coordinator-readable prose blobs vs. typed artifact references at equal
   research cost. Measure claim/span loss through synthesis, duplicated source origins, coordinator
   context usage, and verifier corrections.

## Decisive disconfirmers and cautions

- More exploration can improve breadth faster than factuality (MindSearch), and long-form synthesis
  can inherit source bias or associate unrelated facts (STORM).
- Durable full transcripts can preserve exactly the context pollution that explicit state is meant
  to avoid (Microsoft’s documented implementation is a useful counterexample).
- Summaries are not lossless; on-demand trajectory retrieval was material to HiAgent’s results, and
  OpenHands observed a real condensation failure.
- Reflection is not truth. ExpeL’s reflection-augmented variant performed worse, plausibly because
  reflections hallucinated.
- Provenance explains lineage and responsibility, not validity. Claim verification remains a
  separate gate.
- Multi-agent breadth is expensive and coordination-sensitive; Anthropic’s results are internal,
  vendor-reported, and accompany a roughly 15×-chat token cost.

## Gaps

1. **No integrated field-survey study.** No primary found evaluates adaptive questions, durable
   replay, provenance, reversible compression, rejected-path memory, and multi-worker artifact
   coordination together on deep research. This is the main load-bearing gap and should be closed by
   an Aletheia A/B, not another broad literature round.
2. **Semantic version migration.** The sources support replay within a version but do not settle how
   an in-flight research graph should migrate across changed prompts/models/schema/channel behavior.
   Defaulting to a new branch with explicit derivation is safer than in-place migration.
3. **Concurrency semantics.** First-party sources acknowledge that asynchronous multi-agent state
   consistency is unresolved. Lease ownership, optimistic revision checks, and a canonical merger are
   reasoned design choices needing stress tests.
4. **Compression verification.** HiAgent supports reversible retrieval, but no cited work provides a
   strong guarantee that a research synthesis retains every load-bearing caveat or contradiction.
5. **Source-quality mismatch.** MindSearch/STORM/Co-STORM optimize broad web answers/articles, not
   independent-origin evidence surveys or claim-to-span verification. Their architecture transfers;
   their quality claims do not automatically transfer.
6. **Channel constraints in this run.** Brave was unavailable at framing time; arXiv intermittently
   returned 429s; GitHub became rate-limited in the final targeted round. Official ACL, arXiv PDF,
   first-party documentation, and W3C primaries were chased directly to mitigate this, but channel
   loss still narrows discovery coverage.

## Saturation decision

The scoped branch is locally saturated. Later targeted searches returned the same anchor systems,
surveys that pointed back to them, or off-topic results. Every requested mechanism now has either a
decisive primary/implementation source or an explicitly named integration gap. Additional broad
search would add architectural examples without resolving the decisive unanswered question: whether
the integrated design improves Aletheia field-survey outputs at equal research cost.
