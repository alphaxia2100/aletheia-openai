# Runtime, testability, performance, and cost audit

**Audited implementation:** `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5` (`aletheia-research 0.5.0-openai.1` plus the portable-runtime candidate).
**Scope:** local code behavior, reproducibility, measured control-plane performance, and the operational cost/latency model.
**Non-goal:** this is not a quality benchmark of the resulting research briefs. No paid connector, browser, or model API call was made for this audit.

## Bottom line

The Python machinery itself is light and fast. On this host the entire hermetic suite finishes in 13.19 seconds, offline structural preflight takes 0.09 seconds, a portable install takes 0.35 seconds, and the synthetic scheduler experiment confirms that retrieval fan-out is genuinely parallel.

That does **not** make the end-user research workflow fast or cheap. The expensive part is intentionally outside the Python process: repeated agent reasoning, one or more subagents per leaf, full-text reading, source selection, synthesis, and a separate final fact-check. The current runtime neither invokes nor meters the model, so it cannot report model tokens, model dollars, agent wall time, or a total per-run cost.

The most important operational finding is that the public default is `unlimited`: a logical budget of `1,000,000`, depth 99, and no per-leaf round cap. `max_nodes=512` limits breadth, but not repeated investigation of a leaf. Stopping is delegated to an agent's judgment of convergence. Therefore the default has **no executable upper bound** on requests, full-text reads, model context, elapsed time, or spend. That can be defensible for an explicitly requested day-long investigation; it is an unsafe default for an ordinary research prompt.

My candid assessment is:

- It is a serious, unusually well-tested *research protocol and evidence-artifact system*, not a cheap research assistant.
- It has good local correctness and portability discipline, but no end-to-end cost governor.
- It will feel slow in normal use because it intentionally multiplies agent turns and serializes the most latency-heavy part (full reads).
- Its current complexity is only justified for consequential, contentious questions where auditability, source provenance, disagreement preservation, and adversarial search change the decision. For everyday factual lookup, coding research, or a single decision with a short deadline, a strong single-agent workflow plus a short citation check is likely the better cost/latency trade-off.

## Environment and audit constraints

| Item | Observed value |
|---|---|
| Host | MacBookPro18,3, arm64; macOS 26.5.1 |
| CPU / memory | 8 logical CPUs; 16 GiB RAM |
| Interpreter | `/usr/bin/python3`, Python 3.9.6 |
| Checkout branch | `codex/independent-audit-2026-07-28` |
| Source state | No tracked source diff was observed; the audit directory itself is untracked, so runs created after the audit began correctly record `git_dirty: true`. |
| Paid/model use | None. The only live check was a deliberately keyless connector health probe in an empty Aletheia config directory. |
| Production mutations | None. The benchmark driver, generated fixtures, portable-install fixture, JSON results, and this report are all under this audit directory. |

The `git_dirty` observation is not a product defect: `treestate.py` deliberately calls `git status --porcelain --untracked-files=normal`. It does mean that users who keep run data or unrelated files in a checkout will get a dirty provenance flag even when executable code is unchanged.

## What was measured

### 1. Hermetic regression suite

Command:

```sh
/usr/bin/time -l python3 -m unittest discover -s tests -v
```

Result: **186/186 passed**. Python reported 13.193 seconds for the tests; `/usr/bin/time` reported 13.33 s real, 7.13 s user, 4.92 s system, and 37.45 MB maximum resident set size.

Test inventory:

| File | Tests | What it primarily establishes |
|---|---:|---|
| `tests/test_aletheia.py` | 157 | tree lifecycle, deduplication, ranking, verification bookkeeping, router behavior, source-selection traces, installer behavior, and regression cases |
| `tests/test_portable_release.py` | 7 | copy-install, manifest/preflight, non-destructive replacement, and POSIX modes |
| `tests/test_portable_security.py` | 10 | disabled-channel, browser, private-config, artifact permission, and cache-boundary behavior |
| `tests/test_surveyor.py` | 12 | retired surveyor baseline behavior |

This is a real strength. It catches many failure modes that research-agent projects normally leave as prose promises: duplicate work/read slots, invalid claim-score completion, disabled connector escalation, and partial portable installs.

It is still not an end-to-end performance or quality evaluation. The tests intentionally mock network I/O and model judgment. They do not measure connector availability under rate limits, multi-leaf concurrent load, actual model token usage, dollar cost, quality at equal budget, human time to supervise a run, or degradation from very large evidence packs. No CI workflow/configuration was found in the checkout, and no coverage measurement is produced by the test command, so a passing local suite is not continuous-release evidence or a coverage percentage.

### 2. Offline preflight and portable-install path

Commands:

```sh
/usr/bin/time -l python3 scripts/preflight.py --json

ALETHEIA_CODEX_SKILLS=".../audits/2026-07-28-independent-project-audit/benchmarks/fixtures/portable-install/skills" \
  /usr/bin/time -l bash scripts/install.sh

/usr/bin/time -l python3 \
  audits/2026-07-28-independent-project-audit/benchmarks/fixtures/portable-install/skills/.aletheia-runtime/tools/preflight.py \
  --runtime audits/2026-07-28-independent-project-audit/benchmarks/fixtures/portable-install/skills/.aletheia-runtime \
  --json
```

Results:

| Operation | Result | Wall time | Peak RSS |
|---|---|---:|---:|
| Checkout preflight | PASS; all required files compile; no network | 0.09 s | 19.1 MB |
| Fresh portable copy install | PASS; self-contained runtime plus public symlink | 0.35 s | 19.4 MB |
| Installed-runtime preflight | PASS; manifest verified | 0.08 s | 19.8 MB |

The installed runtime had 47 files and occupied 468 KB. The active portable closure contains 41 source files / 6,667 Python lines across `aletheia-research`, `channel-retrieval`, and `provenance-audit`. This is not large in disk or local execution terms. Complexity is behavioral/orchestration complexity, not local binary size.

### 3. Offline scheduler microbenchmark

Driver: [`runtime_microbenchmark.py`](runtime_microbenchmark.py). It imports the checked-out runtime but replaces every in-memory connector and reader with deterministic sleeps. It makes no network or model calls. Each of five trials uses:

- three retrieval channels, each sleeping 100 ms;
- four selected full-text reads, each sleeping 50 ms;
- the real `investigate.investigate()` retrieval, rank, selection, artifact, and telemetry path.

Command:

```sh
/usr/bin/time -l python3 audits/2026-07-28-independent-project-audit/benchmarks/runtime_microbenchmark.py \
  --base audits/2026-07-28-independent-project-audit/benchmarks/fixtures/microbenchmark
```

Full machine-readable results: [`runtime_microbenchmark-result.json`](runtime_microbenchmark-result.json).

| Median of 5 trials | Measured | Interpretation |
|---|---:|---|
| Retrieval sum of channel work | 0.3047 s | Approximately three 100-ms calls' work |
| Retrieval wall time | 0.1028 s | Confirms `retrieve()` fans out channels concurrently |
| Read sum | 0.2158 s | Four 50-ms synthetic reads plus small overhead |
| Read wall time | 0.2180 s | Essentially the sum; all five trials reported `reads_overlapped: false` |
| End-to-end one-round wall time | 0.3298 s | Local bookkeeping is small relative to I/O |

This establishes the scheduler shape, not a real-world latency number. It corroborates the implementation: `retrieve()` uses a `ThreadPoolExecutor`, while `_execute_reads()` loops over selected sources serially. Parallel retrieval is good; serial full-text reads become the latency bottleneck as soon as the network is nontrivial.

### 4. Keyless live connector health snapshot

Command (isolated environment with no inherited API keys and an empty Aletheia config):

```sh
env -i PATH="/usr/bin:/bin:/usr/sbin:/sbin" PYTHONNOUSERSITE=1 \
  ALETHEIA_CONFIG_DIR=".../audits/2026-07-28-independent-project-audit/benchmarks/fixtures/doctor-keyless-config" \
  /usr/bin/python3 .cursor/skills/channel-retrieval/scripts/doctor.py --timeout 3 --json
```

The probe completed in 1.4 s. The raw result is [`keyless-channel-health-2026-07-28.json`](keyless-channel-health-2026-07-28.json).

- **11 of 13 endpoints were reachable/live**: ten reported `ok`; OpenAlex was reachable but warned that its keyless quota is low.
- **Brave was warned, not tested as usable**, because no `BRAVE_API_KEY` was supplied. The system falls back to DuckDuckGo and Marginalia, but loses the stronger independent web index.
- **Reddit was down** in this snapshot (`HTTP 502`).

This is a time-specific availability snapshot, not a reliability benchmark. It does, however, show why a multi-index workflow needs per-run health evidence: a nominally enabled source can disappear, and the free/default channel mix is materially different from a keyed deployment.

## The actual runtime and cost model

### The logical budget is not a resource budget

`treestate.py` defines the following tiers:

| Tier | Logical budget | Max depth | Max children | Max nodes | Per-leaf round cap |
|---|---:|---:|---:|---:|---|
| `quick` | 8 | 1 | 3 | 8 | `floor(leaf_budget / 4)` |
| `standard` | 16 | 2 | 3 | 16 | same |
| `deep` | 32 | 3 | 4 | 40 | same |
| `exhaustive` | 64 | 3 | 5 | 64 | same |
| `unlimited` (default) | 1,000,000 | 99 | 6 | 512 | **none** |
| `max` | 1,000,000 | 99 | 8 | 2,048 | **none** |

The default was reproduced without a `--thoroughness` argument. Its emitted `run.json` states `thoroughness: "unlimited"`, `budget: 1000000.0`, `max_depth: 99`, `max_children: 6`, and `max_nodes: 512`.

That budget determines tree allocation and bounded-tier round counts. It is **not** a quota on endpoint calls, bytes transferred, selected sources, model tokens, model dollars, elapsed time, or subagent count. The SKILL.md deliberately says that unlimited/max stop only when the agent judges convergence. There is no programmatic convergence detector or cost ceiling in the runtime.

For the normal engine defaults only (unit = 4; `--reads` omitted; no direct/manual primary chasing), budget conservation plus the bounded per-leaf round cap gives this useful *upper-envelope* accounting before verification/model work:

| Bounded tier | At most completed engine rounds across a conserved tree | At most selected engine reads at 4/round | Theoretical zero-result retrieval-attempt shape at 36/round |
|---|---:|---:|---:|
| `quick` | 2 | 8 | 72 |
| `standard` | 4 | 16 | 144 |
| `deep` | 8 | 32 | 288 |
| `exhaustive` | 16 | 64 | 576 |

These are deliberately conservative envelopes, not expected run costs. A real topic may return useful results on the first request, select fewer than four sources, or stop earlier; an agent can also exceed this accounting through a CLI read override, direct primary chase, uncapped reread, extra model work, or a changed execution plan. Unlimited/max have no corresponding finite row.

### One normal investigation round

For the documented default path, one leaf round has these mechanics:

1. The router normally selects at most six channels.
2. Retrieval fans those channels out in parallel.
3. A zero-result query longer than three words can be retried twice with relaxed keywords: up to **three requests per selected channel**.
4. Agent triage permits an initial candidate manifest and one tighter requery: up to **two retrieval passes** before a read/explicit abstention.
5. With the normal `unit=4` and no `--reads` override, a completed round suggests/selects at most **four full-text reads**.
6. Full-text reads execute serially.
7. The agent then has to inspect evidence, write findings, later synthesize, draft, fact-check every relevant/borderline claim with a different model/fresh verifier, and do final scope attestation. Those are workflow instructions, not Python API calls.

Thus the normal worst-case request-count shape before manual primary chasing is approximately:

```text
6 channels × 3 query attempts × 2 triage manifests = 36 retrieval requests per leaf round
4 selected full-text reads, serially
```

This is a shape bound, not a promise that every round makes 36 calls: relaxation only happens after zero results, and a normal healthy round is much smaller. It also is not a global hard cap. `--reads`, `--limit`, and explicit channel lists are caller-controlled; the code does not validate them against a run-level spend budget. Agent workers can additionally chase primaries or perform uncapped rereads outside `investigate.py`; the report code counts such artifact files but cannot price them.

### Latency amplifiers

| Driver | Code behavior | Practical effect |
|---|---|---|
| Full-text reads | Four default reads are serial in `_execute_reads()` | One slow/blocked reader adds directly to leaf wall time; the synthetic test demonstrates no overlap. |
| Retry policy | `_http.get_bytes()` allows 2 retries (3 attempts total), with backoff | A degraded endpoint can consume material wall time even though others returned quickly. |
| Request timeout | `investigate.py` defaults to 30 s | A single read or query can wait through repeated 30-s attempts; there is no whole-run deadline. |
| arXiv full-text resolution | An `/abs/` URL tries HTML then PDF | A failed selected arXiv source can incur two reader paths. |
| Multi-leaf fan-out | The skill asks the host to spawn one worker per leaf at deep tiers | Parallelism reduces elapsed time only if the harness has capacity; it raises concurrent connector and model demand. The Python runtime has no cross-worker/global rate limiter. |
| Agent triage | Candidate manifest → model judgment → exact pick → findings | Adds deliberate model round trips before source content can be used. |
| Verification | Missing local notes cause a sequential live refetch per claim/URL | A citation typo or omitted note can reintroduce slow network I/O late in the run. |

There is a payload control but not a resource budget: many connector reads use `_http.MAX_RESPONSE_BYTES = 8 MiB`, while the saved text cap is 40,000 characters. A reader can therefore transfer far more than the eventual saved excerpt before truncation. DuckDuckGo uses a separate direct `urlopen` implementation, so even that 8-MiB limit is not a universal byte cap. `report.py bundle --reads` defaults to no per-read output cap, so accumulated evidence can create a very large agent handoff despite the normal read cap.

At documented defaults, four successful reads can persist up to **160,000 source characters per leaf round** before headers and evidence/index material. That is not a token measurement—the host decides how much it places into a model context and tokenizer ratios vary—but it is the dominant model-input-cost driver. The artifact can keep growing through rounds and leaf branches, while the user-facing agent bundle is permitted to inline full nested reads with no aggregate size limit.

### Why actual dollar cost cannot currently be calculated

The repository contains no OpenAI client or model-call implementation. It is a skill suite: the host agent/harness executes the reasoning. The only runtime cost telemetry aggregates retrieval counts, selected/read counts, successful reads, failures, elapsed reader seconds, and artifact counts. It records neither:

- model name, input/output/reasoning tokens, cache hits, or model price;
- number/duration of subagent turns;
- connector billing plan, request units, or bytes billed;
- browser/session usage cost;
- total elapsed user wait time;
- human review time.

Optional keys in `.env.example` include paid services (for example Exa, X APIs, Perplexity, Linkup, Firecrawl, and Scite). The default keyless core avoids mandatory paid calls, but users can enable paid paths and the run report will still not calculate dollars. Therefore any claim that Aletheia costs “$X per research run” would currently be invented.

The closest honest statement is: **the minimum connector price can be zero, but the model/token cost and time can range from modest to unbounded depending on the harness, topic, source failures, and whether the agent follows the unlimited default.**

### Evidence map for the claims above

- Tier/default and node caps: `.cursor/skills/aletheia-research/scripts/treestate.py`, lines 190–258.
- Parallel retrieval and zero-result relaxation: `.cursor/skills/aletheia-research/scripts/investigate.py`, lines 320–359.
- Normal read count, no round cap for unlimited, and serial reads: `investigate.py`, lines 495–521 and 578–613.
- Two-manifest agent-triage limit: `investigate.py`, lines 708–760.
- 40,000-character read cap: `investigate.py`, line 43; reader response limit/retries: `.cursor/skills/channel-retrieval/scripts/_http.py`, lines 247–279; reader truncation: `read.py`, lines 50–91.
- What runtime telemetry actually records: `.cursor/skills/aletheia-research/scripts/report.py`, lines 229–287.
- Verification fallback to live reads: `.cursor/skills/aletheia-research/scripts/verify.py`, lines 67–109.

## Testability and engineering-quality assessment

### What is solid

- Standard-library core; no mandatory dependency installation.
- Meaningful hermetic regression coverage for state transitions, provenance/deduplication, capability isolation, and portable installs.
- Reproducible runtime fingerprints include the executable files and effective channel configuration.
- The runtime preserves detailed local artifacts and telemetry, which makes postmortems much more feasible than a chat-only workflow.
- The safety/capability tests are unusually concrete for this kind of project.

### What is still weak or unproven

1. **No end-to-end acceptance test.** There is no pinned, replayable fixture that exercises the real no-key connector stack, full reads, a host model, verification, and final brief while measuring cost and latency.
2. **No cost-matched quality benchmark for the current flagship.** Existing repository evaluations and self-audits are useful diagnostic evidence, but they do not establish that the current full workflow beats a strong flat/single-agent baseline when both receive the same model-token, request, and elapsed-time budget.
3. **No live reliability test in CI.** This is understandable because endpoints are flaky, but it leaves an important gap: local correctness cannot prove a usable research day.
4. **No performance/load test.** The scheduler has no test for 10–100 simultaneous leaves, connector rate-limit behavior, total artifact size, or context-window pressure.
5. **No resource governor.** Provenance records what happened after the fact; it does not prevent an accidental expensive run.
6. **Protocol compliance remains honor-system at the expensive stages.** The skill says to use a distinct verifier model, investigate until convergence, and write findings per leaf. The scripts help record and gate some outputs, but they do not create, constrain, or meter the host-agent work.

## Recommendations, in priority order

1. **Change the default from `unlimited` to a bounded, explicitly named mode** (likely `standard` or a new cheap “scout” tier). Require an explicit user confirmation for unlimited/max that displays planned caps and an estimated resource envelope. This is the highest-leverage usability/cost change.
2. **Implement a run-level resource ledger and hard stop controls.** Record and cap: requests by connector, response bytes, full-read count/bytes, per-leaf and global wall time, active workers, model tokens/cost when the host exposes them, and external-tool cost units. Put these in `run.json`/telemetry and surface them before expanding the tree.
3. **Parallelize full reads with a small, per-host/per-connector concurrency limit.** Keep individual channel backoff, but avoid making four healthy 10-second reads take 40 seconds. Provide a conservative default and fairness/rate-limit controls.
4. **Build a repeatable cost-quality evaluation harness.** Fixed topics, fixed model(s), frozen or cached retrieval corpus, blinded human-calibrated judging, and equal budgets for model tokens, read artifacts, external requests, and wall time. Compare against a competent flat workflow, not a weak straw baseline.
5. **Expose a deliberately small workflow.** A user who wants a five-minute answer should get one question, 1–2 source classes, 2–4 reads, one synthesis, and a visible stop—not the full tree/verification ritual. Preserve the full protocol as a high-assurance mode.
6. **Add CI for hermetic tests, preflight, portable install, and synthetic scheduler regression.** It will not prove external quality, but it prevents portability and behavior regressions from depending on a local manual run.
7. **Report a cost/latency summary in every final brief.** At minimum: tier, elapsed time, leaves, retrieval passes, retrieved/selected/read counts, manual reads, failed channels, and any available model/token metrics. Readers need to know whether an apparently rigorous answer took 4 reads or 114.

## Reproduction notes

All custom scripts and outputs are in this directory. To repeat the deterministic scheduler measurement, run `runtime_microbenchmark.py` against a new subdirectory below `benchmarks/fixtures/`; it cannot invoke a real connector because it replaces the entire dispatch in memory. The health snapshot is intentionally **not** deterministic: repeat it only with the isolated keyless environment above and record the date, timeout, and status changes.

The local measurements answer a narrow but important question: the Python control plane is not the performance problem. The costly, slow, and currently unbounded parts are the deliberate research protocol and the host-agent/model work wrapped around it.
