# Decision on default `unlimited` for consequential investigations

## Decision

**No.** At the audited runtime candidate, a consequential medical, legal, or policy investigation should not be allowed to enter the default `unlimited` mode unless a human has first set an explicit, enforceable resource envelope. The appropriate default for such work is a bounded run whose maximum requests, reads, elapsed time, provider spend/token allowance, and permissible manual or linked-primary work are declared before retrieval begins. The existing design is serious about evidence quality and makes useful progress toward traceability, but neither its instructions nor the inspected runtime make “continue until saturated” an adequate authorization to spend unbounded external resources or to make a high-stakes conclusion.

This is not a claim that the code literally runs forever. On initialization, absent a tier or budget, the runtime selects `unlimited`; the frozen tier configuration persists a numeric budget of 1,000,000, maximum depth 99, six children per split, and 512 nodes. In `can_split`, enforcement covers depth, budget, node slots, and child count. Those are tree guardrails, but they are not a human-selected money, time, request, token, or total-read limit. The persisted run configuration contains these structural fields, not a deadline or resource reservation. [S2, `.cursor/skills/aletheia-research/scripts/treestate.py`:199–207, 222–252, 272–289]

## Precise implementation boundary

The specification calls `unlimited` the default and defines its stopping criterion as agent-paced convergence: deepen until new rounds yield no distinct origins or claims; its high node cap is described as a runaway backstop. In the inspected tree code, however, `can_split` evaluates only the numeric tree conditions above. It does not calculate distinct-origin/claim saturation or turn a convergence assessment into a forced stop. The specification also limits an individual investigation round to an initial candidate manifest plus one requery and permits an explicit abstention. That prevents a narrow retrieval loop from silently spinning, but it does not bound the number of leaf rounds, aggregate manual primary chasing, or total work across a run. [S1, `.cursor/skills/aletheia-research/SKILL.md`:59–78, 167–184; S2, `.cursor/skills/aletheia-research/scripts/treestate.py`:272–289]

Reporting is observability, not interdiction. The report runtime totals retrieval passes, selected sources, attempts, successful reads, failures, read seconds, and both engine and direct/manual read artifacts; the scorer returns those totals after the fact. Neither function accepts an allowed spend, request count, or deadline, or interrupts a run when one is exceeded. Therefore, telemetry can support a post-run comparison but cannot substitute for an authorization boundary in a high-stakes live investigation. [S4, `.cursor/skills/aletheia-research/scripts/report.py`:229–287, 462–504]

There is a second boundary at the evidence object itself. The frozen reader saves a body under a hash of the requested URL, records its method and any resolved URL, and sets `_read_ok` once stripped text reaches 1,500 characters. The arXiv path narrows a known abstract-page problem by requiring a sufficiently long HTML or PDF body, but the shown success path does not compare expected title, DOI, author, or other requested-work identifier with an identifier extracted from that body. A readable substitute document could therefore be internally well-provenanced as a fetch while still not be the document the investigator meant to read. [S3, `.cursor/skills/aletheia-research/scripts/investigate.py`:362–410, 590–609, 696–705]

The historic record is important counterevidence but must be stated accurately. It records two wrong-document bodies accepted as `_read_ok` in a 2026-07-27 run at a different implementation commit, and explicitly says that the incidents do not estimate prevalence. It is not a replay showing that the frozen candidate executed those incidents. It does, however, illustrate the exact failure class left unverified by the frozen length-based gate, so a consequential finding cannot treat `_read_ok` as document-identity proof. [S5, `docs/research/2026-07-27-agent-output-quality/internal-observations.md`:5–11, 37–101; S3, `.cursor/skills/aletheia-research/scripts/investigate.py`:376–410, 598–609]

## Strongest case for allowing depth—and why it is insufficient

The contrary evidence is real, but it establishes specified and code-backed safeguards when the workflow is performed, not that they executed in a consequential run. The workflow specifies retrieval separated from topic-relative reading, distinct origins and a high-weight adversary, per-round manifest caps, decision and telemetry records, and a fresh-context verifier for every load-bearing final claim plus omissions. Its score code withholds headline citation accuracy until coverage and the claim-scope audit are complete, while the workflow specifies hashing the final brief, claim set, and verdict file. These are substantive controls against shallow retrieval, correlated evidence, and polished but unscoped prose; their availability is not execution evidence. [S1, `.cursor/skills/aletheia-research/SKILL.md`:113–143, 152–182, 217–266; S4, `.cursor/skills/aletheia-research/scripts/report.py`:462–504]

Outcome evidence is favorable but limited: the forward record explicitly describes its positive results as small-N and model-judged, without a human-calibrated multi-topic benchmark. Within that limitation, a capped biomedical forward test reported six successful reads recovering a Cochrane review, RCTs, safety guidance, and an attribution issue; a fresh verifier expanded 17 writer claims to 32 supported claims with valid hash audit, and two reversed-order judges preferred the candidate. That supports component-level triage and verification, not an unlimited default. The same forward record reports a dynamic-outline comparison whose quality result used 97 rather than 41 persisted read artifacts—2.37 times the observed footprint—despite equal configured rounds, and it remains experimental pending enforceable linked-primary budgets and a cost-matched blind rerun. [S7, `docs/evals/openai-v0.5-forward-test.md`:28–42, 46–72]

## Required release gates

Before a strong high-stakes claim is credible, I would require all of the following release gates, with failure of any gate blocking the claim rather than merely adding a caveat.

1. **Human-set, runtime-enforced envelope.** Before work starts, record and enforce run-wide ceilings for wall time, requests by channel, attempted and successful reads, direct/manual reads, provider tokens/spend, concurrency, and allowed browser/manual escalation. The ceiling must cover every child and re-read, stop the run on exhaustion, and preserve an auditable refusal/partial-result state. The project itself identifies an experimental runtime-ledger branch for run-wide search/read/time reservations, which underscores that this capability is not established by the audited default. [S6, `docs/BRANCHES.md`:38–44]

2. **Semantic read-identity gate.** Promotion must require expected-versus-observed identity checks using strong identifiers where available, title/author/date consistency otherwise, typed failure states for blocked or substituted bodies, and retention of failed-attempt provenance. The repository labels such a mechanism experimental and unpromoted; it cannot be assumed from the current `_read_ok` flag. [S6, `docs/BRANCHES.md`:14–19, 38–44; S3, `.cursor/skills/aletheia-research/scripts/investigate.py`:598–609]

3. **Final-claim evidence gate.** Every load-bearing claim in the exact delivered brief must receive independent, fresh-context verification; omitted claims must be added; the scoped claim set, verdicts, and brief must be hash-attested; and post-attestation edits must invalidate the result. This is already the documented design intent, so the release gate is demonstrated execution on the actual high-stakes artifact, not mere availability of the script. [S1, `.cursor/skills/aletheia-research/SKILL.md`:225–266]

4. **Live, cost-matched high-stakes evaluation.** Use a frozen, multi-topic medical/legal/policy benchmark with human-calibrated adjudication, reversed-order blinding, held-out evaluation, failure analysis, and a bounded-envelope comparator. Account for actual requests, full and manual reads, elapsed time, provider tokens, and cost. The current forward record says its favorable results are small-N and model-judged, lacks a human-calibrated multi-topic benchmark, and shows why equal round counts alone are not cost parity. [S7, `docs/evals/openai-v0.5-forward-test.md`:52–72]

5. **Release and host integrity.** Bind the evaluated runtime to an immutable signed release with SBOM/CI provenance, repeat its copied-runtime checks on a fresh host, and deploy it under separately audited identity, workspace, egress, credential, and browser controls. The portable candidate explicitly disclaims OS-sandbox/security certification and lacks a signed tag, SBOM, and independent supply-chain attestation; its own promotion guidance calls for a fresh-host repeat and release-integrity decision. [S6, `docs/PORTABILITY.md`:3–7, 36–40, 151–164, 230–235]

The source-controlled comparison is deliberately narrower than those gates: it does not test live retrieval behavior or token-cost parity. It can establish what the frozen documents and code specify, not that a production host, provider, channel, or investigator will honor the intended controls.

## Self-check

I checked the conclusion against the strongest favorable evidence: finite tree caps, per-round manifest restraint, specified/code-backed diversity and claim-verification safeguards when performed, and the clean capped biomedical result. None supplies the missing human-authorized, run-wide enforcement or a live high-stakes, cost-matched validation. The decision is consequently a deployment boundary, not a dismissal of the research mechanisms.

## Compact source table

Seven source entries span eight frozen documents; S6 contains two documents.

| ID | Frozen path(s) | Main use |
| --- | --- | --- |
| S1 | `.cursor/skills/aletheia-research/SKILL.md` | Default, convergence, workflow, verification specification |
| S2 | `.cursor/skills/aletheia-research/scripts/treestate.py` | Default initialization and structural tree limits |
| S3 | `.cursor/skills/aletheia-research/scripts/investigate.py` | Read success, persistence, and triage implementation |
| S4 | `.cursor/skills/aletheia-research/scripts/report.py` | Post hoc telemetry and score behavior |
| S5 | `docs/research/2026-07-27-agent-output-quality/internal-observations.md` | Historical, different-commit identity incidents |
| S6 | `docs/BRANCHES.md`; `docs/PORTABILITY.md` | Promotion status, experimental mechanisms, release/host boundary |
| S7 | `docs/evals/openai-v0.5-forward-test.md` | Capped forward evidence and cost-validity failure |
