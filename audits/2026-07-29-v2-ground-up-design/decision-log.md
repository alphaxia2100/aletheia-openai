# Aletheia v2 decision log

This log records architecture decisions made by the 2026-07-29 ground-up
investigation. A decision is not permanent merely because it is documented. Each
entry names the evidence boundary and what would justify changing it, so a later
audit can distinguish a measured result from a design preference.

| ID | Decision | Status | Evidence / rationale | Reconsider when |
|---|---|---|---|---|
| D-01 | Do not patch the v0.5 directory tree into v2. | **Accepted** | The prior audit reproduced wrong-body evidence acceptance, stale replay, duplicate IDs/index rows, cap races, and host-model resource opacity. A larger tree would preserve its authority failure. | A future implementation proves a filesystem layer can provide the same transactional/capability semantics without bypasses; this is unlikely to be the lowest-risk route. |
| D-02 | Make one bounded, accountable lead the default execution shape. | **Accepted** | The corrected local comparison is 11–11 while the elaborate condition used 28 versus 8 declared read assignments. Direct execution has lower handoff and duplication overhead. | A sealed, cost-matched study shows a multi-agent or managed path has a durable default-tier advantage for representative tasks. |
| D-03 | Treat managed and open research systems as executor adapters, not feature checklists to rebuild. | **Accepted** | Their browser/job/model operations can be valuable, but their citations/traces do not automatically establish Aletheia's evidence/claim assurance. The differentiated layer is policy, provenance, and evaluation. | An adapter cannot expose enough trace/source/usage detail for an advertised assurance tier, or an adapter abstraction materially harms a validated executor. |
| D-04 | Put plan, state transitions, leases, budgets, and finalization behind one controller-owned transactional authority. | **Accepted** | v0.5 check-then-write behavior created concurrency/replay defects. Workers must propose, not self-certify state. | A simpler authority boundary meets the same fault-injection suite and reduces operational risk. |
| D-05 | Use append-only typed events plus rebuildable projections, not Markdown/JSON files, as canonical state. | **Accepted** | Crash recovery, idempotency, supersession, and postmortem reconstruction require durable ordering and schema validation. Export files remain valuable human views. | Event sourcing's migration/projection cost demonstrably exceeds a simpler transactional journal for the scoped kernel. If changed, retain immutable audit history and replay tests. |
| D-06 | Admit only finite run manifests; delete `unlimited` as a product mode. | **Accepted** | The existing setting has structural backstops but no user-enforceable cost/deadline/read/model contract. "Saturation" is an agent judgment, not authority to spend indefinitely. | A user explicitly approves a new finite envelope; this is an amendment, not a return of autonomous unlimited mode. |
| D-07 | Separate transport, identity, evidence eligibility, and semantic entailment. | **Accepted** | A long body and a cited URL did not identify the intended work; a real source can still be ineligible for a claim or fail to entail it. | A narrower domain has a formally justified equivalent identity/entailment model that passes the same adversarial fixtures. |
| D-08 | Persist failed/ambiguous fetches and provider outcomes; do not erase them on retry. | **Accepted** | Retaining failed attempts is necessary to audit wrong-body, stale-browser, and cost/retry behavior. | Privacy/copyright/retention policy requires deletion; retain an appropriate receipt/hash/tombstone and state the new assurance limitation. |
| D-09 | Meter/model-budget only what the runtime can observe; label missing usage as unknown. | **Accepted** | A skill running through a host cannot honestly enforce model dollars/tokens it cannot see. Requests/time/bytes/reads still supply hard observable caps. | The host exposes verifiable usage receipts; then promote token/cost dimensions to hard caps after reconciliation testing. |
| D-10 | Use SQLite/WAL with one controller for the first local vertical slice. | **Accepted** | It gives transactional local state and one intentional writer without premature distributed operational complexity. | A measured multi-host, availability, throughput, or organizational access-control need justifies Postgres/service migration; preserve the same contract/conformance tests. |
| D-11 | Defer generic plugins, authenticated browser sessions, cross-run answer memory, distributed orchestration, autonomous self-modification, and default multi-agent trees. | **Accepted / defer** | Each enlarges authority, retention, security, or coordination surface before the kernel has shown value. | An isolated proposal names a concrete user failure, threat model, capability policy, bounded cost, removal plan, and passed frozen-baseline ablation. |
| D-12 | Make a verifier, adversarial retrieval, origin clustering, and extra specialists feature flags rather than permanent ritual. | **Accepted** | Each addresses a plausible failure mode, but current evidence does not establish a net benefit at matched resources. | Its preregistered ablation passes the integrity gate and shows a replicated benefit against the equal-budget control. |
| D-13 | Require an audit card and explicit terminal state for every mode. | **Accepted** | The important user information is often why work stopped, what is unverified, which channels degraded, and what was spent—not only prose fluency. | A simpler presentation preserves the same information and is validated as more usable; never remove the underlying receipt/terminal data. |
| D-14 | Preserve v0.5 only as a read-only historical baseline; import artifacts one-way as legacy observations. | **Accepted** | Existing tree state cannot safely become v2 authority, and old `_read_ok` is not v2 identity verification. | A deterministic importer can prove full semantics from a v0 run without ambiguous/stale state; imported records must still retain legacy labels. |
| D-15 | Build the evaluation harness in parallel with the bounded vertical slice. | **Accepted** | A redesign without frozen, resource-matched comparison would reproduce the project's prior risk of attractive but unearned mechanisms. | Never; the exact harness can evolve under versioned/provenance-controlled evaluation changes, but comparison discipline is a permanent requirement. |

## Decision rule for future changes

Every v2 change request should attach an experiment/decision card:

```text
Observed failure or user need:
Mechanism and authority boundary:
Baseline and immutable hash:
Task strata / source-access policy:
Global resource envelope:
Primary outcome and denominator:
Non-negotiable integrity fixtures:
Keep / revise / revert threshold:
Owner, feature-flag expiry, and removal plan:
```

If any field is unavailable, the proposal remains a research note rather than a
default behavior. A failed or inconclusive candidate is retained as a negative
result with its flag off; it is not silently carried into the next composite
experiment.
