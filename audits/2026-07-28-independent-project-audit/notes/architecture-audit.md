# Architecture and codebase audit

**Auditor:** independent codebase review
**Audit date:** 2026-07-28
**Audited checkout:** `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5` on `codex/independent-audit-2026-07-28`, which points at the unpromoted `codex/exp-portable-sandbox-v06` candidate.
**Stable runtime:** `prod` is documentation-forward from the immutable runtime tag `aletheia-prod-v0.5.0-openai.1^{}` = `addfaf648ca5577e00e393b2cb1c692a6302eac2`.

## Bottom line

Aletheia is a serious, unusually reflective **research-engineering workbench**, not yet a demonstrated superior research product. Its strongest contribution is procedural: it forces a capable agent to externalize evidence, disagreement, source provenance, failure state, and a final review trail. That is valuable for an expensive investigation that a human will inspect.

It does **not** yet earn its default complexity for ordinary research. The default is deliberately an agent-paced, effectively unbounded survey; it asks the harness to fan out subagents, fetch and read many documents, and conduct an independent semantic verification pass. The project has no completed, cost-matched, human-calibrated multi-topic evidence that this architecture beats a strong single-agent/flat-evidence workflow. Its own records say as much. The correct public positioning today is: **experimental high-scrutiny method for a power user, with useful instrumentation and known correctness gaps—not “better deep research” by default.**

For high-stakes work, the current audited runtime—and the stable production lineage from which it is derived—has a release-blocking trust gap: a fetched body is accepted as a successful read solely when it is at least 1,500 characters. The project has already reproduced wrong-document, anti-bot-page, and error-shell false successes; the more conservative identity gate exists only on a separate, unpromoted branch.

## What is actually implemented

This is a skill bundle, not a standalone agent service. The public `aletheia-research` skill instructs the host model to:

1. frame competing hypotheses;
2. create a filesystem-backed research tree;
3. retrieve and rank sources through sibling channel clients;
4. have the model choose sources to read;
5. use separate worker agents for broad/deep runs;
6. synthesize centrally and ask a fresh verifier to make semantic entailment judgments; and
7. write a score and artifact bundle.

The deterministic pieces are real Python tools; the most important judgments and orchestration remain prompt/harness behavior. Relative imports make the public skill depend on `channel-retrieval` and `provenance-audit` ([`.cursor/skills/aletheia-research/scripts/investigate.py:27-41`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L27-L41)). The portable candidate packages exactly those three skills ([`scripts/install.sh:73-77`](../../../scripts/install.sh#L73-L77)).

The architecture is coherent:

```text
host agent + long SKILL.md
  -> treestate.py (directory-backed run/tree/status/decisions)
  -> router.py + channel-retrieval clients (parallel retrieval)
  -> rank.py + agent-selected candidate manifest
  -> investigate.py (read artifacts, telemetry, source index)
  -> human/model-written findings + centralized synthesis
  -> lexical verification + separate semantic verifier
  -> claim-scope hash attestation + report/score/bundle
```

The central design split—deterministic plumbing in code, epistemic judgment in an agent—is defensible. It is also the source of most of the system's operating risk: a passing Python test suite cannot establish that a host model actually follows a 300-line workflow, chooses good framings, notices a bad source, stops appropriately, or performs a genuinely independent review.

## What is strong

### 1. Better observability than most research-agent prototypes

- Runs persist node status, questions, answers, decisions, source rows, full reads, and telemetry in a resumable filesystem tree ([`treestate.py:2-37`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L2-L37), [`treestate.py:466-476`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L466-L476)). This is much better than an opaque chat transcript for postmortem work.
- The runtime fingerprints executable skill/dependency bytes, effective channel configuration, Git commit, and dirty state ([`treestate.py:86-123`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L86-L123)). That is a real reproducibility improvement, even though it cannot recreate model behavior or remote web results.
- Retrieval and source selection are separately observable, and direct/manual reads are counted separately from engine reads ([`report.py:229-287`](../../../.cursor/skills/aletheia-research/scripts/report.py#L229-L287)). This is a good response to a common research-agent failure: hiding expensive primary chasing outside the nominal read budget.

### 2. The project is candid about what verification does and does not prove

- The lexical verifier explicitly refuses to label any source as `supported`; it only establishes that a readable source has lexical overlap, then requires a separate semantic verifier ([`verify.py:8-23`](../../../.cursor/skills/aletheia-research/scripts/verify.py#L8-L23), [`verify.py:105-159`](../../../.cursor/skills/aletheia-research/scripts/verify.py#L105-L159)). That restraint is intellectually correct.
- The score gates headline citation accuracy on a completed row-level pass and a content-hash claim-scope attestation ([`report.py:462-504`](../../../.cursor/skills/aletheia-research/scripts/report.py#L462-L504)). It is a meaningful integrity guard against editing a brief after audit.
- The project does not silently treat a degraded tool as a clean run. The current health check found 11 of 13 core probes live, with Brave degraded because no key is configured and Reddit down with HTTP 502. The doctor itself calls this a single functional probe rather than a load test ([`doctor.py:248-308`](../../../.cursor/skills/channel-retrieval/scripts/doctor.py#L248-L308)).

### 3. Engineering hygiene is materially better than the project’s size might suggest

- `python3 scripts/preflight.py` passed in this checkout. `python3 -m unittest discover -s tests -v` passed **186/186** tests in 12.764 seconds. The tests cover state caps, retrieval/routing cases, verification gates, portability, URL/capability boundaries, and regressions.
- The portable candidate is careful about user-scoped connector configuration, private permissions, disabled-channel enforcement, no automatic browser-session fallback, and public-URL checks ([`.cursor/skills/channel-retrieval/scripts/_config.py:115-195`](../../../.cursor/skills/channel-retrieval/scripts/_config.py#L115-L195), [`.cursor/skills/channel-retrieval/scripts/_http.py:197-279`](../../../.cursor/skills/channel-retrieval/scripts/_http.py#L197-L279)).
- The installer’s copy mode is deliberately Git-pinned, verifies a manifest, and refuses unmanaged replacements by default ([`scripts/install.sh:152-182`](../../../scripts/install.sh#L152-L182), [`scripts/preflight.py:19-40`](../../../scripts/preflight.py#L19-L40)). This is good release discipline for a personal skill bundle.

### 4. The project has unusually good scientific self-critique

The checked-in self-audit is not proof of product quality, but it is evidence of healthy engineering culture. It documents wrong-body reads, claim-scope failures, router defects, opaque convergence, and output compression failure rather than burying them ([`docs/research/2026-07-27-agent-output-quality/README.md:9-28`](../../../docs/research/2026-07-27-agent-output-quality/README.md#L9-L28)). The branch map retains failed and inconclusive work rather than rewriting history ([`docs/BRANCHES.md:1-20`](../../../docs/BRANCHES.md#L1-L20)).

## Material findings and risks

| ID | Severity | Finding | Evidence and implication |
|---|---|---|---|
| A-01 | **P0 for high-stakes truth claims** | A long but wrong/blocked body can be accepted as a successful primary read. | Current `_execute_reads()` sets `_read_ok` solely from `len(txt.strip()) >= 1500` ([`investigate.py:590-609`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L590-L609)). The project’s own reproduction found two wrong GRADE bodies, an anti-bot interstitial, and an arXiv error shell accepted in a prior run ([`internal-observations.md:37-101`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L37-L101)). The unmerged identity-gate experiment reports an 11-fixture result of 7/11 correct with four false accepts for production versus 11/11 for the candidate (`fa4b26d:docs/experiments/read-identity-gate-v06/results.md:18-36`); the branch is explicitly still experimental ([`docs/BRANCHES.md:15-18`](../../../docs/BRANCHES.md#L15-L18)). Do not market “reads primaries in full” as a current invariant. |
| A-02 | **P1** | Default work is effectively unbounded in time, token use, web requests, and money. | With no tier or budget, `init_run()` selects `unlimited`; its implemented limits are synthetic budget `1,000,000`, depth 99, up to 6 children, and 512 nodes ([`treestate.py:190-258`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L190-L258)). The skill directs a read-only subagent per leaf at `deep` and above—therefore at its default ([`SKILL.md:201-205`](../../../.cursor/skills/aletheia-research/SKILL.md#L201-L205)). The stop condition is an agent’s judgment of saturation, not a budget or recall certificate. This is appropriate only when the user explicitly wants an expensive investigation. |
| A-03 | **P1** | “Budget” is not an enforceable cost envelope. | It controls tree arithmetic and per-round source selection, but not model tokens, subagent count actually spawned by the harness, wall time, human time, paid API fees, or uncapped direct reads. Runtime telemetry records retrieval/read counts and read seconds, but no token, model, dollar, or wall-clock ledger ([`report.py:263-287`](../../../.cursor/skills/aletheia-research/scripts/report.py#L263-L287)). A prior dynamic-outline comparison produced 97 persisted read artifacts versus 41 at the same configured rounds (2.37×), so the project correctly rejected it as not cost-matched ([`docs/evals/openai-v0.5-forward-test.md:46-65`](../../../docs/evals/openai-v0.5-forward-test.md#L46-L65)). |
| A-04 | **P1** | Citation score is narrower than research correctness and still relies on an asserted semantic audit. | `audit_claim_scope()` verifies hashes and row correspondence but accepts the supplied auditor identity/claim-count as semantic truth ([`report.py:186-226`](../../../.cursor/skills/aletheia-research/scripts/report.py#L186-L226)). A `citation_accuracy=1.0` thus means “the extracted, cited claims received supported verdicts under the conducted review,” not complete factual accuracy, unbiased coverage, or absence of omitted decisive evidence. A fresh audit of the project’s own research initially found 29 omitted load-bearing claims and 10 unsupported rows ([`internal-observations.md:176-196`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L176-L196)). |
| A-05 | **P1** | Source routing remains a brittle keyword taxonomy, even after agent-selected source triage improved the last stage. | The router’s categories and signals are handwritten ([`router.py:38-104`](../../../.cursor/skills/aletheia-research/scripts/router.py#L38-L104)) and choose `openalex` as the “primary” for finance and legal despite comments admitting missing SEC EDGAR/CourtListener clients ([`router.py:76-94`](../../../.cursor/skills/aletheia-research/scripts/router.py#L76-L94)). The project reproduced a systematic-review/meta-research question routed to `products_consumer` and required manual academic overrides ([`internal-observations.md:83-101`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L83-L101)). The agent can override routes, but that moves correctness back into prompt compliance. |
| A-06 | **P1** | There is no demonstrated comparative quality advantage commensurate with the complexity. | The most favorable forward tests cover two topics and say directly that they do not estimate a general win rate ([`docs/evals/openai-v0.5-forward-test.md:18-42`](../../../docs/evals/openai-v0.5-forward-test.md#L18-L42)). The earlier three-way bakeoff was one topic/one run, retrieval-luck dominated, and did not show a clear winner ([`docs/evals/2026-07-08-creatine-cognition-bakeoff.md:20-25`](../../../docs/evals/2026-07-08-creatine-cognition-bakeoff.md#L20-L25), [`docs/evals/2026-07-08-creatine-cognition-bakeoff.md:39-63`](../../../docs/evals/2026-07-08-creatine-cognition-bakeoff.md#L39-L63)). The project’s own adversary review says no existing experiment meets the needed cost-matched, multi-topic, human-calibrated test ([`branches/adversary.md:249-276`](../../../docs/research/2026-07-27-agent-output-quality/branches/adversary.md#L249-L276)). |
| A-07 | **P2** | The full-bundle handoff is both too large and incompletely “complete.” | `report.bundle()` calls itself a complete artifact set but emits findings, evidence, telemetry, source rows, optionally full reads, and a status summary—not `decisions.jsonl`, questions, answers, specs, proposals, or raw status artifacts ([`report.py:303-378`](../../../.cursor/skills/aletheia-research/scripts/report.py#L303-L378)). A project diagnostic found a 950,921-byte production bundle versus a 28,782-byte experimental dossier and one missed trace answer in the flat bundle ([`internal-observations.md:103-120`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L103-L120)). This makes agent-to-agent handoff needlessly expensive and risks context truncation. |
| A-08 | **P2** | Release topology is mature for a research project but confusing for a user-facing product. | The local repository has 31 local heads and 30 remote heads, including separate portability, identity, ledger, accuracy, field-dossier, and archive lines. `prod` is stable while the audited HEAD is explicitly an unpromoted candidate ([`docs/BRANCHES.md:12-20`](../../../docs/BRANCHES.md#L12-L20)). This is disciplined experimentation, not a single coherent release train; users can easily assume features documented on sibling branches are in production when they are not. |
| A-09 | **P2** | The portable candidate hardens accidental exposure, not the host agent. | Documentation is refreshingly explicit that it is not an OS sandbox, lacks a signed tag/SBOM/independent supply-chain attestation, and uses an unpinned container base ([`docs/PORTABILITY.md:1-7`](../../../docs/PORTABILITY.md#L1-L7), [`docs/PORTABILITY.md:32-40`](../../../docs/PORTABILITY.md#L32-L40), [`docs/PORTABILITY.md:194-200`](../../../docs/PORTABILITY.md#L194-L200)). That is fine if accurately labeled; it is not sufficient isolation for untrusted prompt/content execution. |
| A-10 | **P3** | Tests are strong at deterministic regressions but there is no repository CI configuration or end-to-end quality gate. | The audit found no `.github/workflows`, GitLab CI, package test configuration, or checked-in broad benchmark result. The 186 passing unit/integration tests should be preserved, but they do not exercise model compliance, cross-model verification independence, live web variance, or task quality. |

## Is it too slow, expensive, complex, or weak versus simpler workflows?

### Speed and cost: yes by default

The answer is **yes for normal use**. Aletheia’s default deliberately targets roughly a day of research and its `max` mode roughly a week; that is in the tool’s own design, not an accidental implementation inefficiency ([`SKILL.md:59-77`](../../../.cursor/skills/aletheia-research/SKILL.md#L59-L77)). Retrieval is parallel, but selected reads are performed serially inside `_execute_reads()` ([`investigate.py:590-612`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L590-L612)); semantic verification and synthesis add independent agent turns. The cost is not currently priced or bounded in real units.

The project’s 2026-07-27 self-survey provides a realistic scale signal, not a general benchmark: 37 rounds, 1,137 retrieved records, 72 engine-selected reads (65 successful), 97 additional direct/manual read artifacts, and 347.4 seconds of recorded read time—before counting model time/tokens and human review ([`docs/research/2026-07-27-agent-output-quality/score.json:41-65`](../../../docs/research/2026-07-27-agent-output-quality/score.json#L41-L65)). That is appropriate only when a traceable research dossier is worth substantially more than a fast answer.

### Complexity: it is mostly justified machinery, but too much is in the prompt

There is real value in state files, provenance clustering, channel safety, artifact fingerprints, and post-run auditing. The code is not gratuitous in the way many agent frameworks are. The problem is the **control plane**: major correctness properties are a long natural-language contract rather than executable constraints. The SKILL requires a particular portfolio, breadth-first scheduling, independent agents, primary chasing, adversarial review, semantic verification, and a second coverage audit. A harness/model that performs only 80% of this sequence can still generate a polished answer and artifacts while missing the claimed guarantee.

The project must decide whether it is optimizing for an expert operator who consciously executes a research protocol or for a repeatable product workflow. It cannot honestly claim both yet.

### Relative merit versus a simple, disciplined agent loop

A simple workflow—one capable agent, a small number of well-chosen sources, a compact claim/evidence table, an explicit cost cap, and a fresh final reviewer—will usually be faster, cheaper, easier to debug, and more reproducible in the practical sense. It has fewer context transfers, fewer routing decisions, fewer synchronization failures, and a smaller attack surface for bad tool results.

Aletheia earns its overhead only in the narrower case where these are all true:

- the topic is broad, contested, and valuable enough to warrant many primary reads;
- the user wants disagreement and provenance preserved, not merely a concise answer;
- a human will inspect or reuse the run artifacts; and
- the operator accepts bounded but substantial research cost.

It is not yet shown that the tree/subagent architecture itself, as opposed to simply spending more time and reads, produces better truth-seeking results. That distinction is the central unresolved empirical question.

## Recommended priority order

1. **Make source identity/content validity a prerequisite for any high-stakes use.** Finish the resolver-recovery experiment, then merge an identity/content gate only with a measured recall tradeoff. Do this before adding hierarchy, more channels, or autonomous self-improvement.
2. **Change the product default to a bounded `standard` envelope.** Require explicit opt-in for `deep`, `unlimited`, and `max`; expose limits for model tokens, worker count, retrievals, reads, wall time, output bytes, and external spend. Synthetic scrutiny budget should not be presented as cost control.
3. **Promote one integrated release candidate, not a menu of promising branches.** Keep experiments, but publish a feature matrix that says exactly which correctness/security/UX guarantees are in `prod`, candidate, and experimental branches.
4. **Build the missing benchmark before claiming superiority.** Use the project’s own proposed standard: frozen multi-topic tasks, repeated runs, same model/harness/candidate pools/read attempts/tokens/wall time, human-calibrated judging, must-cover and harmful-omission criteria, and a strong flat/single-agent baseline ([`synthesis.md:280-313`](../../../docs/research/2026-07-27-agent-output-quality/synthesis.md#L280-L313)).
5. **Move claim-specific provenance into the data model.** A run-wide origin count cannot prove that a particular conclusion has independent support ([`internal-observations.md:136-139`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L136-L139)).
6. **Replace the raw “full bundle” default with progressive disclosure.** A compact map, branch summaries, claim/evidence ledger, decision trace, and on-demand raw reads would improve both agent usability and cost without pretending that detail is lost.
7. **Scope support honestly by domain.** Either add authoritative legal/finance/policy sources or make those domains explicitly experimental; a generic academic index is not a substitute for the relevant primary record.
8. **Add release automation.** A repository CI job running preflight, tests, and portable-install smoke tests plus signed tags/SBOM/provenance would convert the current careful local discipline into a more trustworthy release process.

## Audit limitations

This review independently inspected the working code, current health snapshot, tests, Git topology, and checked-in historical evidence. It did **not** independently re-run every historical live survey or validate factual claims in old research briefs; those records are treated as project-authored evidence of observed behavior, not proof of general performance. Comparative benchmarking and external-workflow research are reported separately in this audit directory.
