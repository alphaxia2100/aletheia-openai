# Aletheia v2 control plane

**Status:** ground-up design recommendation, not an implementation.
**Decision:** v2 should be a bounded research execution ledger controlled by one transactional
authority. Agents are leased workers that may propose and submit results, not authors of state.

The v0 runtime has thoughtful research ideas, but mutable directories, JSON files, and Markdown are
simultaneously its task graph, current state, evidence store, audit trail, and gate signal. v2 should
separate those responsibilities:

1. A controller validates every command and is the only state-changing authority.
2. A transactional database stores an append-only typed execution ledger plus current projections.
3. An immutable content store holds source bodies and generated artifacts by digest.
4. A tool gateway holds provider/browser credentials and enforces capability grants.
5. Markdown and directories are read-only exports for people, never control-plane input.

The default workflow remains a bounded single lead and, when warranted, a separately budgeted
verifier. Parallel specialists are an explicit escalation, not a default ritual.

## Evidence status and constraints

Items called **confirmed** are facts from the prior audit or cited primary documentation. Items
called **recommendation** are deliberate design choices.

The local constraint is the [deep runtime audit](../../2026-07-28-deep-runtime-and-head-to-head/report.md)
and its [literal control-plane review](../../2026-07-28-deep-runtime-and-head-to-head/line-review/control-plane.md).
The four reviewed runtime control-plane files had no scoped diff from the audited candidate at the
start of this work.

| Confirmed v0 behavior | Consequence for v2 |
|---|---|
| Unlocked file read-modify-write operations produced duplicate QIDs, duplicate source index entries, and seven nodes after concurrent splits under a five-node cap. | Cross-worker invariants must be checked and committed in one transaction. |
| Replaying a split leaves old child directories; synthesis enumerates disk children rather than declared state. | The task graph must be an immutable controller-owned projection, never a filesystem scan. |
| A nonexistent QID plus empty answer can clear the ask-before-authoring gate. | Questions/answers need stable server IDs, relationship validation, and explicit gate predicates. |
| Read success is based on length; a hash-named note is not bound to requested/final URL or observed work identity. | Source identity must be a typed state transition before a body carries evidence weight. |
| Default unlimited has finite tree backstops but no hard cap on model tokens, dollars, time, requests, reads, browser work, or human review. | A run plan must define finite resource envelopes and reservation rules. |
| Ordinary writes can bypass synthesis gates; status fields are arbitrary mutable values. | Finalization and state gates must live in the controller, not optional CLI order. |
| Corrupt input may disappear and weaker provenance fallback may be presented as structural independence. | Control corruption/degradation must be explicit and block affected quality claims. |

## External evidence used

Raw retrieved copies are intentionally ignored under the research-run directory. The following are
primary sources read on 2026-07-29. Channel health was 12 of 13 core channels live; Brave was
keyless/degraded, so this is not a claim of exhaustive web coverage.

| Source | Confirmed point | Design use |
|---|---|---|
| [SQLite transactions](https://sqlite.org/lang_transaction.html) | SQLite allows multiple readers but one simultaneous writer; immediate write transactions can be busy. | Local mode needs one controller and short retryable transactions, not a shared writable folder. |
| [SQLite WAL](https://sqlite.org/wal.html) | WAL allows readers with a writer but still only one writer and requires all processes on the same host. | SQLite/WAL is valid for a single-host v2, not NFS, Dropbox, or multi-host writers. |
| [Temporal event history](https://docs.temporal.io/workflow-execution/event) | Durable recovery uses append-only history; activities retry; histories have size limits. | Compact typed events and external idempotency are needed; do not store bodies or reasoning traces in the ledger. |
| [AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) | Database plus notification is a dual-write problem; consumers can receive duplicates and must be idempotent. | Commit domain event/projection/outbox atomically; dispatch is at least once. |
| [Azure event sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) | Event sourcing brings real concurrency, schema, projection, privacy, and migration costs. | Apply it only to the run control plane where replay/audit earn it. |
| [PostgreSQL locking](https://www.postgresql.org/docs/current/explicit-locking.html) | Row locks prevent conflicting writers but deadlocks/conflicts need bounded retry and lock discipline. | Multi-host service mode needs DB-enforced versions/constraints, not advisory coordination alone. |

No append-only table is administrator-proof. A hash chain detects ordinary damage only if an attacker
cannot rewrite both it and its trusted root. High-assurance deployment needs externally held signing
keys plus periodically anchored signed checkpoints.

## Architecture

~~~text
user/API -> command controller -> transactional run store -> scheduler -> leased workers
                 |                   |       |                  |
                 |                   |       +-> outbox --------+
                 |                   +-> events/projections/budgets
                 v
          tool gateway -> model/retrieval/browser providers
                 |
                 v
       immutable blob/content store <-> source and artifact manifests
~~~

| Component | May do | Must not do |
|---|---|---|
| Controller | validate state, append accepted events, reserve budget, issue/revoke grants/leases, finalize reports | run provider calls inside a DB transaction |
| Scheduler | select ready tasks and request leases | invent tasks or raise budgets |
| Worker | propose plan/source/claim and submit leased result | write DB, choose unrestricted tools, self-attest verification |
| Tool gateway | validate grant, call provider, persist receipt/blob reference | trust a prompt as authority or expose provider secrets |
| Evidence service | assess source identity and record evidence spans | treat body length or URL filename as identity |
| Exporter | create Markdown/archive views | be a source of state or graph discovery |
| Human reviewer | approve a scoped decision | edit history in place without a superseding event |

## Immutable run plan

A mutable draft is not a run. Admission creates a canonical immutable plan version, hashes it, and
emits PlanAdmitted. Every later event carries the admitted plan hash. Scope/model/channel/budget/
parallelism/verifier/capability changes require a new plan version and the policy-designated approver.
A worker may propose an amendment but cannot self-approve it.

~~~yaml
schema_version: 1
run_id: controller-generated UUID
request:
  question: canonical user request
  output_contract: audience, sections, format
  scope: in-scope, exclusions, time/jurisdiction limits, stakes
workflow:
  roles: lead plus explicit optional verifier/reviewer
  initial_task_graph: finite tasks and permitted one-shot decomposition points
  max_parallel_tasks: finite integer
  retry_policy: per operation attempt/backoff limits
  required_gates: questions, verification, review, final coverage
research_policy:
  source_classes: evidence, lead-only, color-only
  identity_requirements: identifiers/metadata required per source type
  citation_policy: evidence span and verdict rules
  independence_method: algorithm/version and degradation behavior
budget_envelope:
  model_input_tokens: hard ceiling
  model_output_tokens: hard ceiling
  provider_cost_microcents: hard ceiling or explicitly not-hard-enforceable
  elapsed_deadline: fixed deadline
  tool_requests: caps by provider/channel
  source_reads_and_bytes: hard ceilings
  browser_pages: zero unless explicitly granted
  attempts_concurrency_human_review: finite caps
capability_policy:
  allowed_tools_models_channels_data_classes
  role permissions and approvals
provenance:
  runtime_config_prompt_policy_price_table digests
approval:
  authenticated principal, time, plan hash, amendment policy
~~~

Admission rejects NaN/Infinity/unbounded numbers; cyclic/duplicate graph; child allocations above
the envelope; unapproved tools/models/channels; missing budget for a required verifier; policy-invalid
parallelism; or a purported hard price cap that cannot be bounded and reconciled.

Decomposition is a command. A worker can submit DecompositionProposed, but only the controller can
accept DecompositionApproved after checking the parent revision, policy, finite capacity, and budget.
The same idempotency key returns the original child IDs on retry; it cannot create a second branch.

## Event ledger

Events record accepted business facts and decisions, not chain-of-thought. Large/sensitive data is a
blob with a content digest and access class.

~~~json
{
  "event_id": "controller UUID",
  "run_id": "UUID",
  "stream": "run or task/source stream",
  "sequence": 184,
  "event_type": "TaskLeaseGranted",
  "schema_version": 1,
  "occurred_at_utc": "server timestamp",
  "actor": {"principal_id": "authenticated identity", "role": "controller|worker|reviewer|gateway"},
  "causation_id": "command or earlier event ID",
  "correlation_id": "request/run trace ID",
  "idempotency_key": "opaque operation key",
  "plan_hash": "SHA-256 canonical admitted plan",
  "expected_stream_version": 23,
  "lease_fence": 7,
  "payload": {"type-specific schema": "validated"},
  "payload_sha256": "canonical payload digest",
  "previous_event_hash": "prior stream event digest",
  "event_hash": "envelope digest"
}
~~~

The authoritative order is the database sequence, not a worker clock. IDs are opaque UUIDs, never
line numbers or path slugs. Schemas have a tested version/upcaster policy; unsupported schemas stop a
quality-critical projection instead of becoming arbitrary dictionaries.

| Event family | Essential events |
|---|---|
| Run | RunDrafted, PlanAdmitted, RunStarted, RunPaused, RunCompleted, RunAbstained, RunExhausted, RunIntegrityFailed |
| Graph/task | TaskDefined, DecompositionProposed, DecompositionApproved, TaskReady, TaskBlocked, TaskSucceeded, TaskFailedFinal |
| Lease/attempt | TaskLeaseGranted, TaskStarted, LeaseRenewed, LeaseExpired, CompletionRejected |
| Budget | BudgetEnvelopeSet, BudgetReserved, BudgetSettled, BudgetReleased, BudgetUncertain, BudgetExhausted |
| Capability/tool | CapabilityGranted, CapabilityDenied, CapabilityRevoked, ToolInvocationPlanned, ToolReceiptRecorded |
| Evidence | SourceCandidateRecorded, FetchObserved, BlobStored, IdentityAssessed, EvidenceSpanRecorded, SourceRejected |
| Claims | ClaimDrafted, ClaimScopeFrozen, VerificationAssigned, ClaimVerdicted, CoverageAudited, FinalArtifactFrozen |
| Integrity | DegradationDetected, BlobHashMismatch, SchemaUnsupported, RecoveryStarted, RecoveryCompleted |

Events are append-only under the normal application role. Correction appends a typed superseding event
with reason; it does not alter history. Projections and snapshots carry last-applied sequence/checksum
and are rebuildable; they are not sources of truth.

## State machines

### Run lifecycle

~~~text
DRAFT -> AWAITING_APPROVAL -> ADMITTED -> EXECUTING
                                             |-> WAITING_HUMAN -> EXECUTING
                                             |-> PAUSED -> EXECUTING
                                             |-> VERIFYING -> FINALIZING -> COMPLETED
                                             +-> ABSTAINED | EXHAUSTED | BLOCKED_POLICY
                                                 | CANCELLED | FAILED_OPERATIONAL | FAILED_INTEGRITY
~~~

| State | Meaning |
|---|---|
| Draft / awaiting approval | No external work; user/human is deciding scope. |
| Admitted | Immutable finite plan accepted; reservations may begin. |
| Executing | Controller may issue only allowed, affordable leases. |
| Waiting human / paused | No hidden autonomous progress; deadline/budget policy stays visible. |
| Verifying | Claim/final artifact input is frozen; repair is a bounded new task/revision. |
| Finalizing | Controller evaluates final predicate and binds artifact manifest. |
| Completed | All plan-required gates pass for exact frozen inputs. |
| Abstained / exhausted / blocked policy | Explicitly incomplete but useful outcomes with distinct reasons. |
| Failed operational / integrity | Provider/retry exhaustion versus damaged/untrustworthy state. |

### Task and attempt lifecycle

~~~text
TaskDefined -> READY -> LEASED -> RUNNING -> SUCCEEDED
                                 -> RETRY_WAIT -> READY
                                 -> BLOCKED | FAILED_FINAL | CANCELLED
LEASED/RUNNING --lease expires--> READY with a new attempt and higher fence
~~~

Task specifications are immutable. A completion is accepted only when it matches current task
revision, attempt, lease ID, fence, capability, required artifacts, and budget state. Finalization
requires mandatory tasks/gates, accepted source identity, final claim coverage, exact artifact digest,
no unresolved tool outcome, and no blocking integrity/degradation incident. A report edited after
verification is a new revision and reopens coverage.

## Transactional command, idempotency, and lease contract

Every state-changing request includes authenticated principal/role, command schema/type, run/task ID,
idempotency key, canonical payload digest, expected stream version, and for worker outcomes current
lease ID/fence.

~~~text
BEGIN short database transaction
  load run/task/budget/capability rows at expected version
  reject stale state, invalid lease/grant, or budget shortfall
  same key plus same payload digest -> return original accepted result
  same key plus different digest -> reject key reuse
  append event(s), update synchronous projections
  insert reservation and outbox row in same transaction
  persist idempotency result
COMMIT
dispatch outbox only after commit
~~~

| Operation | Idempotency scope | Required duplicate behavior |
|---|---|---|
| Create run | caller plus request key | Return original run; mismatch under same key is error |
| Admit/amend plan | run plus plan revision | One plan version/graph only |
| Schedule | task logical execution | Return existing current assignment or state conflict |
| Tool invocation | task attempt plus normalized input digest | Reuse receipt/result if safe, otherwise mark outcome uncertain |
| Worker completion | task attempt plus completion key | First valid completion wins; stale/different result rejected |
| Claim verdict | claim version plus verifier assignment | One canonical verdict; correction is a new superseding event |
| Finalize | run plus artifact digest | Same artifact returns prior result; changed artifact requires new verification |

A lease contains controller task/attempt UUID, authenticated worker, opaque lease ID, monotonic fencing
integer, expiry, allowed operation grant IDs, and immutable input-manifest digest. The task projection
holds the current lease/fence. A completion with an expired/lower fence is recorded as rejected but
cannot change evidence, budget, or the brief. This is the concrete fix for duplicate scheduling and
late stale workers.

No DB transaction can atomically include an arbitrary provider. The required protocol is:
1. atomically append ToolInvocationPlanned and reserve resources;
2. tool gateway calls provider under an invocation ID and provider idempotency key where supported;
3. gateway persists receipt/blob reference;
4. controller settles/release-reserves only from valid receipt.

A crash after a provider accepts work but before receipt is **uncertain**. Keep the reservation and
reconcile by invocation key/provider lookup or stop; do not blindly retry. An outbox makes internal
dispatch at least once, so consumers deduplicate event IDs/sequences.

## Budget reservations

Use integer units or fixed-decimal money, never floats. A v2 plan exposes material dimensions even
where exact pricing is unavailable: model input/output tokens, provider microcents, deadline,
tool requests, source reads/bytes, browser pages, task attempts/concurrency, human review, and
artifact/export bytes.

~~~text
available = hard_cap - settled - active_reservations
if conservative_maximum(operation) > available:
    deny schedule
else:
    atomically append BudgetReserved with TaskReady or ToolInvocationPlanned
on receipt:
    append BudgetSettled(actual), then release unused reserved amount
~~~

For models, reserve known input plus maximum permitted output under an immutable model/price snapshot.
If actual usage appears only after call, reserve worst allowed response. If provider price/usage cannot
be bounded and reconciled, state that dollar cap is not hard-enforceable; retain hard request/token/
timeout limits. Budget verifier, synthesis, retry, and human-review work too.

Branch allocations are finite upper bounds, not permission to spend freely. A worker cannot move
funds across branches. Report allocated, reserved, settled, released, uncertain, remaining, forecast,
and denied work. There is no automatic escalation to unlimited: a user-authorized plan amendment
states incremental maximum resources and rationale.

## Capability gates

The authority chain is:

~~~text
admitted policy -> controller grant -> lease-scoped invocation authorization
                -> gateway receipt -> evidence/claim transition
~~~

A capability grant is server-verified and bound to run/task/attempt/role, exact tool action,
allowed channel/model/data class and normalized scope, input digest or narrow rule, request/byte/
token/time limits, reservation reference, expiry, nonce, revocation epoch, plan hash, and approver.
The gateway validates it on every call. Workers receive no provider credentials and cannot bypass
policy by importing a connector.

High-risk capabilities require separate visible approval:
- authenticated browser/session: narrow URL/domain, stated reason, fresh-navigation identity receipt,
  page/time cap;
- private corpus: classification, access/retention/export controls;
- code execution/download: sandbox/network/output policy;
- new connector or paid model: plan/policy approval and budget reservation;
- sharing/export: audience/redaction/classification policy.

Retrieved text is untrusted data. It cannot grant a capability, change a budget, or create an event.
Revocation emits CapabilityRevoked and increments policy epoch; old leases/grants fail validation while
outstanding provider calls are reconciled.

## Persistence and evidence identity

| Deployment | Recommended store | Boundary |
|---|---|---|
| Local experimental v2 | SQLite WAL, one controller process, local immutable content store | Single host only; no shared filesystem or hosted high-availability claim |
| Team/service v2 | PostgreSQL event/projection store plus object storage and controller API | Multi-host/user use; migrations/backups/access control/row conflicts required |
| Optional managed durable workflow | Temporal or equivalent for timers/retries/dispatch while retaining domain ledger | Workflow history does not replace source identity, budget, or policy ledger |

Illustrative relational tables: runs; plan_versions; event_log; task_specs; task_projection;
task_attempts; idempotency_records; budget_accounts/reservations; capability_grants; tool_invocations;
source_versions/identity_assessments; artifacts/manifests; outbox/consumer_offsets; projection_checkpoints.

Raw source and artifact blobs must be content-addressed and include/point to requested and final URL,
redirect chain, response status/content type, retrieval time/method, byte size, headers, extractor
version, and content digest. A source moves through:
Candidate -> FetchRequested -> FetchObserved -> BlobStored -> IdentityAccepted or
IdentityMismatch/Indeterminate -> EvidenceSpanRecorded -> CitationBound.
A long anti-bot page, stale browser page, or wrong work is archived diagnostically but never becomes
accepted evidence. A verifier verdict binds a claim to source-version IDs and extracted spans; lexical
screening never counts as semantic support.

If structural provenance clustering fails, emit DegradationDetected naming requested method, fallback,
error, affected claims, and unavailable metrics. Never label a weaker fallback as structural
independence.

## Failure and recovery rules

| Failure | Required behavior | Forbidden behavior |
|---|---|---|
| Worker crash before external call | Lease expiry then bounded retry | Mark success from a file |
| Crash after external call before receipt | Budget/tool outcome uncertain; reconcile first | Blind duplicate retry |
| Late result | Record rejected stale completion | Let last finisher overwrite accepted work |
| Controller crash during command | Atomic all-or-none event/projection/reservation/outbox result | Infer intent from partial JSON |
| Blob/event/schema corruption | Integrity hold/failure and diagnostic preservation | Drop malformed rows and synthesize normally |
| Source identity mismatch | Retain rejected observation, report gap | Count as successful evidence read |
| Provider outage/rate limit | Bounded retry/backoff then operational failure/abstention | Infinite retry or unplanned route change |
| Budget/deadline ended | Stop new work, reconcile active work, terminal exhausted/abstained | Silent expansion or completion label |
| Review timeout | Wait only through plan deadline then terminal explicit state | Pretend approval |
| Final brief changes | New artifact revision and new coverage audit | Post-audit edit without invalidation |

Restart sequence: verify database/event/blob/checkpoint integrity; rebuild stale projections; expire/
renew authoritative leases; reconcile planned/uncertain tools; recompute ready tasks from immutable
graph; emit recovery/degradation event. Integrity repair is an operator procedure using preserved
snapshots and externally anchored checkpoint where available, not a normal automatic retry.

## Migration constraints and deployment phases

Do **not** dual-write a live v0 run and a v2 ledger. New v2 runs use a new ID namespace; v0 stays a
read-only artifact. A v0 importer preserves, but does not certify:
- run/runtime/config hashes as LegacyRunImported metadata;
- tree/status as legacy graph observations, retaining stale/conflicting descendants;
- findings/brief/decisions as digested legacy blobs;
- sources/notes as legacy observations, never IdentityAccepted evidence until revalidated;
- claims/verdicts as legacy assertions, not a v2 completion badge;
- missing/corrupt lines as explicit import/degradation warnings.

It cannot reconstruct trustworthy chronology from mtimes/path order/overwritten status. v2 exports can
remain directory/Markdown compatible, but they are read-only manifests and never feed the controller.

| Phase | Build | Exit criterion |
|---|---|---|
| 0 | Freeze v0, retain probes, define quality-cost-latency baseline | No rewrite before measurable keep/revert criteria |
| 1 | Event/schema/state/plan/budget/identity contract tests | Deterministic concurrency/crash/source-swap tests pass |
| 2 | Local single-controller SQLite prototype, blob manifest, bounded single lead | Workers cannot mutate state directly; recovery passes |
| 3 | Shadow matched-budget runs versus strong bounded baseline | Compare factual quality, identity, cost, latency |
| 4 | Add one optional adversary/parallel feature at a time | Retain only predeclared measurable gains |
| 5 | If earned, PostgreSQL/controller API/object store service | Load, backup/restore, migration, access review pass |

## Release gates and bottom line

Before a high-stakes/default readiness claim, test at minimum: 100+ concurrent idempotent command
retries; conflicting splits; stale lease completion; crash at each persistence/tool receipt point;
budget race; unknown provider outcome; wrong long source body; blob mutation; bogus QID; missing
verifier; post-audit brief edit; provenance/parser failure; exhaustive export manifest; and import of a
stale v0 tree.

v2 should not be “more agents, but safer.” It should be **one accountable controller, finite approved
work, immutable evidence/execution facts, and delegation that must earn its cost**. This is more
complex than a simple agent, so the default must stay small and bounded. The broader multi-agent
system should ship only after matched-budget evaluation demonstrates that each additional mechanism
improves outcomes enough to justify its latency and spend.
