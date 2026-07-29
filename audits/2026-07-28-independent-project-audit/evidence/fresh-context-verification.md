# Fresh-context claim verification

**Verifier:** independent fresh-context pass, 2026-07-28.

**Baseline:** `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5` (confirmed with `git rev-parse HEAD`). The audit directory was untracked; no production file was edited.

I inspected the candidate code and commit-pinned records directly, rather than treating prior audit conclusions as evidence. I also reproduced: default initialization, the full unit suite, the offline scheduler probe, and the length-only read-success path. External comparison pages were read from their first-party URLs; they establish product/documentation facts, not cross-product outcome superiority.

## Claim ledger

1. **“The default is `unlimited`.” — Supported.**

   [`init_run()`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L210-L258) chooses `unlimited` when neither tier nor budget is supplied. My fresh no-tier fixture emitted `thoroughness="unlimited"`, `budget=1000000.0`, `max_depth=99`, `max_children=6`, and `max_nodes=512`. The user-facing policy says the same ([`SKILL.md:59-78`](../../../.cursor/skills/aletheia-research/SKILL.md#L59-L78)).

   **Required wording:** “The default is agent-paced `unlimited`, with no per-leaf round cap and no run-level resource/cost governor.” Do **not** call it literally capless/unbounded: the implementation has finite synthetic tree backstops—1,000,000 logical budget, depth 99, and 512 nodes ([`treestate.py:199-207`](../../../.cursor/skills/aletheia-research/scripts/treestate.py#L199-L207)); only `unlimited`/`max` return `None` for the *round* cap ([`investigate.py:495-517`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L495-L517)).

2. **“The runtime does not meter model/token/dollar cost or total wall time.” — Supported, with scope.**

   The complete runtime aggregate is the fixed dictionary at [`report.py:229-287`](../../../.cursor/skills/aletheia-research/scripts/report.py#L229-L287): retrieval/read counts, read failures, `read_seconds`, and artifact counts. The emitted per-round event likewise has counts and summed read seconds only ([`investigate.py:635-652`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L635-L652)). The orchestration runtime contains no token counter, price table, currency field, or whole-run elapsed-time ledger.

   **Safe conclusion:** a run's Aletheia artifacts cannot derive model tokens, model dollars, connector billing, worker-turn cost, or end-to-end elapsed time. **Do not** say those quantities are unknowable from every possible *host/harness* log; that is outside this Python runtime.

3. **“Retrieval is parallel but selected reads are serial.” — Supported, with scope.**

   [`retrieve()`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L320-L359) submits one job per channel to a `ThreadPoolExecutor`; [`_execute_reads()`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L578-L613) then calls `_read_source()` in a plain `for` loop. I reran the offline five-trial scheduler probe ([driver](../benchmarks/runtime_microbenchmark.py#L1-L12)): median retrieval work/wall was 0.3213/0.1094 s, while four reads were 0.2302/0.2319 s and `reads_overlapped=false` in all five trials.

   **Required wording:** this applies to full-text reads *within one leaf-engine invocation*. It must not become “all reads in the whole system are serial”: the skill instructs a host to run separate leaf workers in parallel ([`SKILL.md:201-209`](../../../.cursor/skills/aletheia-research/SKILL.md#L201-L209)), and actual host scheduling is not controlled by this code.

4. **“The test suite passed.” — Supported, narrowly.**

   I ran the documented command ([`tests/test_aletheia.py:1-15`](../../../tests/test_aletheia.py#L1-L15)) at the audited HEAD: `python3 -m unittest discover -s tests -v` completed **186 tests in 12.592 s, OK**. The source inventory contains 157 + 7 + 10 + 12 test methods across the four discovered test files.

   **Do not infer** agent compliance, live-web reliability/load behavior, external-service availability, human research quality, or model independence from this pass.

5. **“A long wrong/blocked body can count as a successful read.” — Supported for the audited candidate.**

   Current candidate code accepts a normal read after only `len(text.strip()) >= 1500`; it records no expected-versus-observed title/identifier verdict ([`investigate.py:393-410`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L393-L410), [`investigate.py:590-609`](../../../.cursor/skills/aletheia-research/scripts/investigate.py#L590-L609)). My controlled probe replaced the reader with a 1,982-character string headed “Checking your browser / anti-bot challenge”; it produced `result_reads_ok=1` and persisted `_read_ok=true`.

   The precise historical examples (two wrong documents, an anti-bot interstitial, and an arXiv error shell) are observations from the *prior production* run, not a new prevalence estimate for this candidate ([`internal-observations.md:37-101`](../../../docs/research/2026-07-27-agent-output-quality/internal-observations.md#L37-L101)). The separate identity-gate branch reports 7/11 correct versus 11/11 on its 11-case diagnostic, but explicitly says it remains experimental and unpromoted ([historical result: lines 1-36](https://github.com/alphaxia2100/aletheia-openai/blob/fa4b26d/docs/experiments/read-identity-gate-v06/results.md#L1-L36)). The audited tree has no `read_identity.py` or identity-experiment path, whereas that branch does.

   **Do not say** the gate is shipped here, that four failures are a current failure rate, or that every long body is wrong. The tested claim is a real missing identity invariant.

6. **“This checkout is a production release / security-certified sandbox.” — Contradicted.**

   Project release topology labels `prod` the stable line and `codex/exp-portable-sandbox-v06` a “release candidate, unpromoted” ([`docs/BRANCHES.md:3-20`](../../../docs/BRANCHES.md#L3-L20)). `bd5e1a50` is contained by the latter branch, not `prod`; `prod` resolves to `7cc657b`, while the immutable production runtime tag resolves to `addfaf6`. The portability document says plainly that this is an unpromoted candidate and “not … an OS sandbox or a security-certified release” ([`docs/PORTABILITY.md:1-7`](../../../docs/PORTABILITY.md#L1-L7), [`docs/PORTABILITY.md:32-40`](../../../docs/PORTABILITY.md#L32-L40)).

   **Safe wording:** “audited portable-runtime release candidate, unpromoted; the project documents `prod` as stable.” This is a project-state claim, not independent release certification.

7. **“Existing quality evidence is small-N and does not establish general comparative advantage.” — Supported, but give the sample correctly.**

   The accepted 0.5 source-triage record has **two** topic-level forward tests (consumer and biomedical), two model judges each, and itself says they do not estimate general win rate ([`forward test:18-42`](../../../docs/evals/openai-v0.5-forward-test.md#L18-L42)). It also includes a **third**, dynamic-outline topic, but rejects it as a cost-matched promotion because observed reads were 97 versus 41 (2.37x) ([`forward test:44-65`](../../../docs/evals/openai-v0.5-forward-test.md#L44-L65)). The earlier bakeoff is an additional, older **N=1 topic / one run per skill** comparison ([`bakeoff:8-25`](../../../docs/evals/2026-07-08-creatine-cognition-bakeoff.md#L8-L25)).

   **Required wording:** “two favorable forward-test topics for capped triage; one additional dynamic-outline diagnostic failed cost matching; plus an earlier N=1 bakeoff.” “There are only two quality samples total” is false. “No cost-matched, human-calibrated multi-topic A/B is present in the audited repository” is supported by the project record's explicit limitation ([`adversary.md:249-276`](../../../docs/research/2026-07-27-agent-output-quality/branches/adversary.md#L249-L276)), but should not be inflated into a claim about unpublished or external work.

   The 2026-07-27 self-audit's 97/97 supported rows are internally consistent (`claims.jsonl` and `verify.jsonl` each have 97 rows; the score declares completed coverage), and its own README correctly limits this to a research record rather than a promoted product result ([`README:1-38`](../../../docs/research/2026-07-27-agent-output-quality/README.md#L1-L38)). It is evidence of an audited claim set, **not** a 97-task quality benchmark or proof of complete/factually superior research.

8. **“Aletheia is better/worse than named alternatives, or a bounded single agent will probably win ordinary work.” — Needs narrower wording.**

   I independently checked the cited first-party sources. They support several *descriptive* facts: Karpathy's `autoresearch` has a fixed five-minute single-GPU experiment and `val_bpb` loop ([pinned README](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/README.md#L296-L308)); OpenAI documents web/MCP/file search, `max_tool_calls`, background execution, and that deep-research requests can take tens of minutes ([guide](https://developers.openai.com/api/docs/guides/deep-research)); Anthropic reports its own internal 90.2% result, up-to-90% research-time reduction, and roughly 15x chat-token use ([report](https://www.anthropic.com/engineering/multi-agent-research-system)); Cognition describes a coding-agent pattern of single-threaded writes plus contributing agents ([post](https://cognition.com/blog/multi-agents-working)); and the pinned LangChain/GPT Researcher READMEs publish their own cost/configuration figures.

   None is a common-task, matched-cost, human-calibrated comparison with this Aletheia candidate. Anthropic, Cognition, LangChain, and GPT Researcher are vendor/maintainer reports—**not independent external validation**. The audit may say Aletheia's outcome superiority is unproven and that its alternatives have different scopes; it must present “best utility,” “mature,” “faster,” “cheaper,” or “best external validation” as a recommendation/hypothesis, not a measured fact. The comparison artifact's own framing that it is not a vendor bake-off is appropriate ([`alternatives.md:1-33`](../comparisons/alternatives.md#L1-L33)).

## Non-negotiable report safeguards

- Distinguish *no resource/cost cap* from *no structural cap*.
- Scope serial-read findings to one leaf engine, and telemetry absence to Aletheia's persisted runtime artifacts.
- Keep the identity defect separate from its historical four-case diagnostic and from the unpromoted remediation branch.
- Label the candidate as unpromoted and not OS-sandbox/security-certified.
- Give the full quality-evidence denominator; do not turn citation-row completion, test count, or a small-N mechanism result into product-quality proof.
- Do not use competitor vendor figures or architecture analogies as comparative superiority evidence.
