# V2 acceptance contract — the first buildable vertical slice

**Status:** design contract; no implementation is implied by this document.
**Purpose:** turn the v2 recommendation into testable boundaries before code,
agents, or a framework choose the architecture by accident.

The controller API can be local IPC, an in-process interface, or HTTP. The
semantic contract must be identical: a worker is not allowed to mutate state,
call a provider with unrestricted credentials, or render a completed report by
editing a file. The terms below use `MUST`, `MUST NOT`, and `MAY` as acceptance
criteria for a candidate implementation.

## 1. First-slice scope

The first slice supports one bounded lead, optional bounded verifier, source
acquisition through controlled adapters, typed source identity, atomic claims,
and a terminal report. It excludes a dynamic tree, generic plugins,
authenticated browser sessions, cross-run answer memory, self-modification, and
multi-host orchestration.

The vertical slice is accepted only when all four properties hold together:

1. **Useful:** it can return a compact, source-bound report or a truthful
   partial/abstain result for a normal bounded question.
2. **Authoritative:** no ordinary worker artifact can impersonate a successful
   state/evidence/finalization transition.
3. **Recoverable:** deterministic replay and injected crash/retry cases preserve
   one logical outcome and a truthful ledger.
4. **Measurable:** it emits enough source, claim, resource, and terminal data to
   compare it fairly with a direct baseline.

If an implementation cannot meet all four, call it an experiment—not v2
bounded research.

## 2. Durable objects and ownership

| Object | Owner / writer | Immutable after creation? | Purpose |
|---|---|---:|---|
| `RunManifest` / `PlanVersion` | Controller after authorized admission | Yes; amendments create another version | What work, policy, tools, budget, and assurance level were authorized. |
| `RunEvent` | Controller | Yes; corrections supersede | Canonical chronological fact/decision ledger. |
| Current projections | Controller transaction/replayer | No; rebuildable | Efficient current view of run, tasks, budgets, claims, and sources. |
| `TaskSpec` and task attempt | Controller | Spec yes; attempt state event-derived | Frozen task packet and lease history. |
| `BudgetReservation` / `UsageReceipt` | Controller/gateway | Receipt/reservation facts append-only | Planned, observed, uncertain, and settled resource use. |
| `CapabilityGrant` | Controller; verified by gateway | Grant immutable; revocation append-only | Narrow authority to invoke one class of effect. |
| Raw artifact / generated artifact | Gateway/exporter | Bytes immutable by digest | Body, extraction, report, or provider response bound to a hash. |
| Source identity/evidence/claim/verdict | Controller after schema validation | Revisions supersede | What was intended, observed, usable, asserted, and verified. |
| Markdown / JSON audit bundle | Exporter | A frozen bundle is immutable by manifest hash | Human-readable projection, never authority. |

Workers may own their local scratch space. Scratch data is not a receipt and has
no effect until submitted through a valid lease-scoped command.

## 3. Minimal manifest

Admission must reject absent, unbounded, contradictory, or unsupported critical
fields. A hard cap is a finite nonnegative integer/fixed decimal with a defined
unit—not `null`, infinity, or an informal "be reasonable" instruction.

```json
{
  "schema_version": 1,
  "run_id": "controller-issued UUID",
  "request": {
    "question": "canonical request text",
    "decision_context": "optional; why it matters",
    "scope": {"time": "...", "jurisdiction": "...", "exclusions": []},
    "output_contract": {"audience": "user", "max_words": 1200}
  },
  "mode": "bounded_research",
  "executor": {
    "kind": "direct_lead|managed_adapter|self_hosted_adapter",
    "implementation_digest": "sha256:...",
    "model_or_provider": "declared identity"
  },
  "policy": {
    "version": "policy digest",
    "required_gates": ["source_identity", "claim_coverage"],
    "source_roles": ["evidence", "lead_only", "color_only"],
    "retention_class": "declared policy"
  },
  "envelope": {
    "deadline_utc": "2026-07-29T20:00:00Z",
    "max_tool_requests": 24,
    "max_source_read_attempts": 12,
    "max_evidence_bytes": 4000000,
    "max_active_workers": 1,
    "max_retries_per_operation": 2,
    "max_browser_pages": 0,
    "model_usage": {
      "metering": "opaque",
      "max_input_tokens": 60000,
      "max_output_tokens": 12000
    }
  },
  "capabilities": {
    "allowed_adapters": ["openalex", "publisher_html"],
    "allowed_domains": ["openalex.org", "example-publisher.org"],
    "data_classes": ["public"]
  },
  "review": {"verifier": "optional", "max_review_tasks": 1},
  "approval": {"principal": "user or service principal", "plan_hash": "sha256:..."}
}
```

`model_usage.metering = opaque` does not make the model free. It means the
report must state that a dollar/token ceiling was unavailable and identify the
hard observable caps still enforced. An adapter that exposes only after-the-fact
usage must reserve a conservative maximum before invocation and reconcile a
receipt later.

## 4. Commands and responses

Every mutating command carries:

```text
command_id, idempotency_key, principal/role, schema_version,
run_id, expected_stream_version, plan_hash, payload_digest,
correlation_id, causation_id
```

Repeated command key plus identical digest returns the original accepted result.
The same key plus a different payload is rejected. Any stale expected version,
expired lease, revoked grant, or insufficient reservation is a rejection—not a
best-effort mutation.

| Command | Authorized caller | Preconditions | Success result | Required refusal cases |
|---|---|---|---|---|
| `CreateRun` | User/client | Valid finite draft | Run ID + `RunDrafted` | Invalid units/schema, duplicate caller key. |
| `AdmitPlan` | Policy-authorized human/service | Draft validates; all required caps/policies present | Immutable plan hash + `PlanAdmitted` | Unbounded budget, unapproved tool, unsupported hard spend cap, cyclic task plan. |
| `LeaseTask` | Scheduler/controller | Ready task, enough allocation, capacity available | Lease ID, fence, input manifest, grants | Stale plan, no funds, existing lease, run not executing. |
| `RequestEffect` | Leased worker | Valid lease and requested effect in grant | Planned invocation ID and reservation | Direct URL/tool not allowed, bad input digest, expired/revoked capability, no capacity. |
| `RecordReceipt` | Gateway | Matching invocation/attempt | Receipt/artifact ID and settlement event | Receipt for unknown/revoked invocation, hash/schema failure. |
| `SubmitProposal` | Leased worker | Valid input manifest and output schema | Proposed source/claim/plan action ID | A proposal is not an accepted global mutation. |
| `AcceptEvidence` | Controller/evidence policy | Receipt + artifact + identity/eligibility assessment | Evidence item/event | Missing/mismatched identity, blocked/truncated state where complete body required, invalid span. |
| `FreezeClaims` | Controller | Draft report candidate and material claim set exist | Claim-set digest | Undeclared material claims or unresolved required gaps. |
| `SubmitVerdict` | Assigned verifier/controller | Bounded verifier lease; claim version and cited spans match | Superseding/accepted verdict event | Shared/incorrect assignment, stale claim, unsupported evidence ID. |
| `FinalizeRun` | Controller | Required tasks/gates resolved; exact artifact digest frozen | Terminal state + report/audit manifest | Uncertain external outcome, missing coverage, cap breach, post-verification edit. |
| `ExportBundle` | Read-only client/exporter | Projection/checkpoint consistent | Content-addressed export manifest | It MUST NOT discover or repair controller state from files. |

Command error responses must retain a machine-readable `code`, reason,
controller time, relevant run/task/plan ID, and whether the denial consumed
anything. Suggested codes: `STALE_VERSION`, `LEASE_FENCED`, `CAPABILITY_DENIED`,
`BUDGET_EXHAUSTED`, `UNKNOWN_OUTCOME`, `IDENTITY_MISMATCH`,
`EVIDENCE_INELIGIBLE`, `CLAIM_COVERAGE_INCOMPLETE`, `INTEGRITY_HOLD`.

## 5. External effect protocol

No implementation can make a database commit atomically with an arbitrary HTTP
call, browser action, or model provider. The contract is deliberately explicit:

```text
1. Controller validates request and atomically reserves the maximum allowance.
2. Controller emits ToolInvocationPlanned and supplies a narrow invocation ID.
3. Gateway calls the provider with that ID as idempotency key where supported.
4. Gateway writes immutable body/response bytes and a receipt or failure record.
5. Controller validates the receipt, settles actual use, and emits result events.
6. If the gateway dies between 3 and 4, state is UNKNOWN_OUTCOME until reconciled.
```

The retry policy is effect-specific. A read may be safely repeated only if its
request is idempotent and duplicate fetches are separately charged/recorded as
the policy requires. A paid model call with no provider lookup may remain
uncertain rather than be silently reissued. The correctness objective is
**exactly-once logical accounting** and visible at-least-once external delivery,
not a false exactly-once network claim.

## 6. Source and evidence acceptance predicate

The first slice uses a conservative predicate. It avoids body-length success
while allowing a documented escalation/review path for difficult documents.

```text
evidence_eligible(source, claim_role) iff
  receipt exists AND raw/extracted artifact hash verifies AND
  transport state is usable for the requested claim AND
  identity is VERIFIED_IDENTIFIER or VERIFIED_TITLE
      (or explicit, named human override) AND
  source role is eligible for claim_role AND
  requested evidence span exists in the bound artifact AND
  retention/data policy allows the use
```

The following must persist as separate fields, not an overloaded boolean:

| Dimension | Example values |
|---|---|
| Transport/content | `complete`, `truncated`, `blocked`, `shell`, `image_only`, `unreadable`, `provider_citation_only` |
| Identity | `verified_identifier`, `verified_title`, `indeterminate`, `mismatch`, `human_override` |
| Eligibility | `evidence`, `lead_only`, `case_only`, `color_only`, `quarantined` |
| Semantic relation | `supports`, `contradicts`, `qualifies`, `background`, `insufficient` |

`indeterminate` evidence may produce an `identity_unresolved` gap or a
human-review task; it does not silently downgrade to usable because the agent
wants to finish. A cache hit identifies identical observed bytes; it does not
create a second independent origin or a free re-read.

## 7. Claim and final-report predicate

The claim ledger is intentionally small. It is not a universal knowledge graph.

```json
{
  "claim_id": "UUID",
  "revision": 1,
  "kind": "factual|inferential|normative|forecast",
  "text": "atomic scoped assertion",
  "materiality": "required|context",
  "scope": {"time": "...", "population": "...", "version": "..."},
  "evidence_relations": ["relation UUID"],
  "dependencies": ["claim UUID for inference premise"],
  "status": "draft|supported|contradicted|qualified|insufficient|omitted",
  "risk_class": "normal|consequential"
}
```

Before verification, the controller freezes a `claim_set_digest` for the exact
candidate report. A fresh verifier returns a verdict per required claim plus
any omitted material claims it discovers. If the report changes, the digest no
longer matches and finalization is invalidated. An inference does not become
supported merely because its premises are: it needs a separately recorded
argument verdict or must be labeled as inference/uncertain.

`RunCompleted` is allowed only if all required claims are represented in the
final frozen report and each has a terminal allowed status under the selected
assurance policy. Other terminal outcomes may still render useful prose, but the
audit card must say why they are incomplete.

## 8. Required audit-card fields

Every final output renders an audit card that is derived from the same frozen
projection as the prose:

- exact run/plan/runtime/policy/executor identifiers and hashes;
- terminal status and stop reason;
- allocated, reserved, settled, released, uncertain, and remaining capacities;
- metered dimensions and explicitly opaque dimensions;
- source receipt/identity/content-state counts and degraded channels;
- number of required/context claims by final verdict, verifier lineage, and
  unresolved/omitted claims;
- independent-origin diagnostic (if requested) with its data-quality status;
- export/artifact manifest hash and the post-verification brief/claim-set hash;
- approved continuation/review paths, if any.

The card is not a single "confidence" number. It shows what was actually done,
what was not established, and why work stopped.

## 9. Fixture-driven acceptance suite

An implementation should not graduate because a happy-path demo looks tidy.
The following checked-in deterministic fixtures are minimum gates. They can use
fake adapters and fake time; the property being tested is control/evidence
semantics, not live-web performance.

| Fixture | Must prove |
|---|---|
| Long unrelated body under expected URL | Readable wrong text is `mismatch`/ineligible, never accepted evidence. |
| Redirect to a different work and DOI/title conflict | Expected and observed identity persist; strong conflict cannot be repaired by reference-list text. |
| Valid short official source | No hidden length threshold rejects it merely for being short. |
| Blocked/shell/truncated/browser-stale body | Transport state remains distinct; policy creates a gap/retry/review, not success. |
| Alias/mirror/cache reuse | One content object may be reused; duplicate role work is explicit, charged, and does not inflate origins. |
| Prompt injection in source text | Data cannot grant capabilities, invoke tools, amend plan, or alter policy. |
| Duplicate command/delivery | Same idempotency key returns prior result; changed payload is rejected. |
| Racing leases/plan amendments | One valid completion/plan revision wins; stale fence cannot mutate projections. |
| Crash before effect / after reserve / after provider acceptance / before receipt | Reservation, uncertainty, recovery, and retry behavior are correct and visible. |
| Cap reaches zero in retrieval, verification, or export | No additional effect runs; terminal state and resource receipt are truthful. |
| Post-verification prose edit | Finalization fails until a new claim coverage/verification pass occurs. |
| Event/projection/blob corruption | Integrity hold preserves forensic evidence; normal completion is blocked. |
| Legacy v0 import with stale tree | Imported fields remain legacy observations; no completed v2 run or free resource is created. |

For each fixture, test replay from an empty projection store and assert the
same terminal materialized state, event order, event hashes, artifact hashes,
budget totals, and export manifest. Run randomized/parallel command sequences
to exercise optimistic-concurrency rejection paths, not only serialized calls.

## 10. Implementation boundary and exit criteria

The first accepted implementation may be a local service using SQLite/WAL and a
content-addressed directory store. It must run under a controller account/API;
giving the model direct write access to the SQLite file or provider credentials
invalidates the authority claim. A CLI may invoke the controller, but must not
become a second writer.

Before adding parallel agents, a review must show all of the following:

1. the fixture suite above passes in CI;
2. a crash/restart event replay reconstructs the same state;
3. the bounded direct lead can complete a real end-to-end report and honest
   partial result;
4. the exported audit bundle is independently inspectable without raw worker
   scratch files;
5. a frozen baseline/evaluation protocol exists before feature tuning; and
6. the candidate reports unknown token/cost dimensions honestly.

Before calling the default useful, run the sealed offline matched-budget study
specified in [research/adversary-and-evaluation.md](research/adversary-and-evaluation.md).
Before calling a multi-agent escalation useful, pass a separate predeclared
ablation against the equal-global-budget single-lead control. Neither condition
is satisfied by this design dossier; those are future execution gates.
