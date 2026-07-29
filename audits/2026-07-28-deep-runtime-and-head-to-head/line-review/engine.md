# Literal engine line review

## Scope and verdict

This is a literal review of every line, including contract-bearing comments, in:

- `.cursor/skills/aletheia-research/scripts/investigate.py` (902 lines)
- `.cursor/skills/aletheia-research/scripts/router.py` (217 lines)
- `.cursor/skills/aletheia-research/scripts/rank.py` (216 lines)

The audited code is frozen commit `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`. The current checkout is at `cbed4789a1c4b283189ec62742eb6ae1ea40f087`; `git diff --quiet` confirmed that none of these three files changed between the two commits. No production file was modified for this audit.

The engine has real strengths: it is compact, inspectable, capable-gated, artifact-first, and substantially more disciplined than a generic web-agent loop. Its happy-path tests are also unusually broad for a skill-level project.

However, several of its strongest promises are not mechanically true today. In particular, a long wrong body becomes a successful read; dual-domain routing can cancel both specialist sources; an empty or failed route can consume a bounded research round as `investigated`; primary sources have no actual selection quota; and cost controls are advisory/caller-dependent rather than enforced. Those are engine properties, not merely documentation shortcomings.

Severity convention:

- **P0** — can make a high-stakes evidence claim appear grounded when it is not.
- **P1** — a normal configuration, caller mistake, or common source pattern can materially damage quality, state correctness, or cost control.
- **P2** — substantial performance/reliability/design limitation; harmful under plausible conditions but not demonstrated as a universal failure.
- **P3** — drift, observability, or maintainability problem.

`engine-coverage.json` is the machine-readable line-accounting and reproduction record accompanying this report.

## Confirmed defects and contract failures

### E-01 — P0: read success is body-length success, not document-identity success

**References:** `investigate.py:376-410`, especially `402-407`; `investigate.py:590-609`, especially `599-605`.

`_read_source()` accepts a generic page once `len(text.strip()) >= 1500`. `_execute_reads()` then independently sets `_read_ok` using the same length test. It records a requested URL and a resolved URL but never checks whether the returned body is the requested work: no title/DOI/PMID/arXiv/content identity comparison, redirect policy, shell classifier beyond the reader's small marker list, or hash-backed identity state.

This makes a long login page, anti-bot page with unfamiliar wording, publisher landing page, unrelated redirected article, or wrong resolver result usable as evidence. The arXiv special case avoids a known abstract-page failure, but it does not supply a general identity gate.

**Executed hermetic reproduction:** monkey-patching the reader to return a long unrelated landing page for `https://expected.example/paper` produced:

```json
{"reads_ok": 1, "source_read_ok": true, "resolved_url": "https://expected.example/paper"}
```

The full incorrect body was persisted and counted as a successful evidence read. This is a direct property of the current code, not a judgment about any particular live source.

**Test status:** the target tests cover successful arXiv endpoint selection and YouTube branches at `tests/test_aletheia.py:1398-1449`, but do not test a long wrong body, redirect mismatch, unknown anti-bot shell, or identity mismatch.

**Repair:** make reads typed. Persist `requested_url`, `resolved_url`, expected typed identifiers, observed identifiers/title, content state, and an identity verdict. Only an identity-compatible, content-usable result should set `_read_ok`; retain failed bodies as artifacts with `_read_state`, not evidence success.

### E-02 — P1: combining two domains removes both domains' specialist routes

**References:** `router.py:157-195`, especially `160-162`, `168-191`.

For multiple detected domains, `route()` unions every domain's `exclude` list. A channel needed by either domain is therefore discarded when the other domain marks it off-topic. This is the opposite of a multi-domain union of relevant evidence sources.

**Executed reproduction:**

```bash
ALETHEIA_CONFIG_DIR=/tmp/aletheia-audit-nonexistent-20260728 BRAVE_API_KEY='' \
  python3 .cursor/skills/aletheia-research/scripts/router.py \
  'machine learning model for cancer clinical trial' --json --max 6
```

Expected/current result includes:

```json
{
  "domains": ["biomed", "cs_software"],
  "channels": ["duckduckgo", "marginalia", "openalex", "reddit", "hackernews"],
  "excluded": ["arxiv", "europepmc", "github", "googlebooks", "gutenberg", "stackexchange"]
}
```

`europepmc` is excluded by `cs_software`; `arxiv`, `github`, and `stackexchange` are excluded by `biomed`. The hybrid question keeps generic OpenAlex but loses the biomed and CS-specific connectors it needs. The same shape can affect other dual-domain queries.

**Test status:** router tests cover single-domain routes and one policy/health ambiguity (`tests/test_aletheia.py:638-735`), but no test asserts that a multi-domain route preserves a specialist source for *each* selected domain.

**Repair:** make exclusions candidate-specific, or exclude a channel only when *all* selected domains exclude it. Add a role/coverage assertion that each detected domain retains at least one appropriate specialist connector after filtering and max-channel trimming.

### E-03 — P1: unavailable/invalid routing can consume a research round as completed

**References:** `router.py:143-147`; `investigate.py:503-553`; `investigate.py:578-657`; agent-visible error elision at `investigate.py:751-754`.

The router correctly fails closed to an empty enabled-channel set when a preference overlay is malformed or disables everything. The investigation engine then sets the node `active`, calls `retrieve()` with zero channels, writes an empty evidence/telemetry round, and sets the node to `investigated`. Per-channel exceptions are also converted to `{n: 0, error: ...}` rather than causing a retry/block state. In the agent-triage response, the `error` field is then discarded and only `v["n"]` is returned.

**Executed hermetic reproduction:** a valid private overlay with `enabled: []`, a fresh `quick` run, and one plain `investigate.py --node ...` invocation returned success:

```json
{"returncode": 0, "reads_ok": 0, "state": "investigated", "rounds": 1}
```

That burns the only quick-tier round without either a usable source or an actionable failure state. An unknown explicit channel has a related behavior: it reaches `DISPATCH[ch]`, becomes a swallowed `KeyError`, and candidate output exposes it only as a zero count.

**Test status:** `tests/test_portable_security.py:84-103` correctly checks that an explicitly named, known-but-disabled connector is rejected *before* I/O. It does not cover zero enabled channels, all endpoints failing, an unknown channel, or state after those cases.

**Repair:** validate nonempty, known, unique channels before setting `active`; fail the command with a structured diagnostic when none are usable. Treat an all-failed retrieval/read round as `blocked`/`degraded`/`retryable`, not `investigated`, and preserve channel errors in the agent-facing candidate response.

### E-04 — P1: resource controls are bypassable, and triage silently ignores `--reads`

**References:** `investigate.py:320-359`, `495-521`, `660-674`, `708-760`, `770-805`, and `868-896`.

The engine has useful local safeguards — two candidate manifests and bounded-tier round counts — but no enforced per-run request, read, timeout, worker, byte, or cost ledger. More specifically:

- A zero-result channel can make up to three retrieval calls (`328-341`).
- `ThreadPoolExecutor(max_workers=len(channels))` creates one worker per supplied channel (`348`), while explicit channel lists are neither deduplicated nor capped at parse time (`886`).
- `--limit`, `--reads`, and `--timeout` have no run-budget validation.
- The CLI parses `--reads` (`878`) but the `candidates` branch invokes `gather_candidates()` without it (`887-889`). Its persisted cap therefore comes from the scrutiny unit rather than the user's requested ceiling.

**Executed reproductions:**

- Supplying `['audit_stub', 'audit_stub', 'audit_stub']` directly to `retrieve()` made **3 connector calls and 3 records**, but the telemetry map had only one key, `audit_stub`. This can multiply endpoint work while hiding it in per-channel counting.
- A fresh quick run invoked as `investigate.py candidates --reads 1 --channels not-a-channel` returned exit 0 with `reads_suggested: 4` and persisted `reads: 4`. The requested one-read ceiling had no effect.

The current default `unlimited` behavior magnifies this: `_round_cap()` intentionally returns `None` for `unlimited`/`max` (`495-500`), while the engine itself does not meter the host model or external calls.

**Test status:** tests prove a bounded round cap and a two-manifest triage cap (`tests/test_aletheia.py:1693-1753`). They do not test duplicate explicit channels, parameter propagation in the triage CLI, large explicit limits/reads, or run-wide spend limits.

**Repair:** canonicalize/reject duplicate and unknown channels; make `--reads` semantics explicit and pass it through triage; constrain caller overrides by an explicit run envelope; record attempts (including relaxation) and response bytes; add global request/read/time/model-cost counters and hard stops.

### E-05 — P1: parallel retrieval turns same-work source choice into a latency race

**References:** `investigate.py:348-355`, `538-546`, and `238-285`.

Retrieval results are appended in `as_completed()` order. `_gather()` deduplicates that completion-ordered list *before* ranking. `_dedupe_records()` retains the first equivalent work and drops later aliases. Thus, if a low-quality mirror returns first and a primary source returns later with the same DOI/arXiv/title identity, ranking never sees the primary source at all.

**Executed hermetic reproduction:** two records shared DOI `10.1000/same-work`; only sleep timing changed.

```json
{
  "mirror_faster": "https://mirror.example/same-work",
  "primary_faster": "https://arxiv.org/abs/2501.12345"
}
```

The selected surviving URL changes solely with endpoint latency. This is particularly damaging because the stated design uses concurrent, heterogeneous indexes specifically to surface better evidence.

**Test status:** dedup tests validate counts and several title variants (`tests/test_aletheia.py:1345-1383`), but do not test which representative survives, source-quality preference among aliases, or completion-order nondeterminism.

**Repair:** group equivalent records first, then select a deterministic representative using identity confidence, source authority, primary flag, directness, URL kind, and stable tie-breakers. Sort channel output deterministically before any order-sensitive logic. Keep aliases in provenance rather than dropping them invisibly.

### E-06 — P1: “primaries are always read” is not implemented

**References:** `rank.py:4-11`, `103-128`, and `137-191`; supporting workflow promise at `SKILL.md:150-175` and `189-200`.

The ranker has an **evidence-class** quota, not a **primary-source** quota. The `primary` field yields only a 5% multiplicative score bump (`116`). `select_reads()` never examines `primary`; it takes top evidence records, then one lead generator, then score-fills. A lower-scoring primary can be skipped entirely.

**Executed counterexample:** three higher-score non-primary evidence records, one lower-score primary evidence record, and one lead generated this selection for `k=3`:

```json
[
  "https://secondary.example/0",
  "https://secondary.example/1",
  "https://lead.example/thread"
]
```

The primary was omitted. The comments/docstring claim that class quotas ensure primaries are read, but class and primary are different fields with different epistemic meanings.

**Test status:** `tests/test_aletheia.py:1528-1540` checks the evidence/lead/color distribution only; no test requires a primary to survive when an eligible primary is present.

**Repair:** distinguish primary/direct/secondary at record level. Reserve a configurable primary slot (or explicitly admit no verified primary exists); make the deterministic fallback’s wording match the actual guarantee; let agent triage see provenance/directness signals rather than channel class alone.

### E-07 — P2: the “hard relevance gate” is relative, not an absolute off-topic guard

**References:** `rank.py:103-128`, `131-160`; deterministic bypass at `investigate.py:556-575`.

`_relnorm` is each record's raw TF-IDF cosine divided by the maximum cosine among that batch. The best weak hit is always normalized to `1.0` if it has any nonzero overlap. `REL_READ = 0.25` therefore gates only relative rank; it does not establish meaningful absolute relevance. The read-floor can then bypass the subject gate using this same relative value.

**Executed counterexample:** a 19-token query and a one-token-overlap document had raw cosine `0.1559`, normalized relevance `1.0`, and was selected by `select_reads(..., 1)`.

This does not prove every weak match is useless; it proves the code cannot support the stronger claim that the threshold itself prevents weak/off-topic reads. Root-subject matching partially mitigates this in common paths, but the read-floor is explicitly designed to override it.

**Test status:** the thin-pool test uses exactly zero-overlap records (`tests/test_aletheia.py:1503-1509`), which does not exercise a weak nonzero top hit.

**Repair:** retain raw relevance and require a calibrated absolute floor (ideally domain-aware/semantic), require a minimum query-term coverage or explicit agent approval, and make the read-floor more conservative than the normal selector rather than less.

### E-08 — P2: work-level deduplication disagrees with the project's own arXiv identity model

**References:** `investigate.py:145-179`, `238-285`; comparison implementation `provenance_graph.py:56-84`.

The research engine's `_strong_keys()` recognizes arXiv IDs only from URLs. The provenance graph recognizes `arxiv_id` and `arxiv` metadata fields too. Consequently, two records for the same work — one with an arXiv URL and one with a non-arXiv URL plus `arxiv_id` — are treated as distinct by the engine even though later provenance code recognizes their shared work identity.

**Executed counterexample:**

```python
_dedupe_records([
  {"url": "https://arxiv.org/abs/2503.13657", "title": ""},
  {"url": "https://news.example/item", "arxiv_id": "arXiv:2503.13657", "title": ""},
])
```

returned **2** records.

This can spend duplicate read slots and make retrieval breadth look broader than it is when an adapter supplies metadata in the latter form. The frequency in current connector output was not measured here.

**Test status:** `tests/test_aletheia.py:117-134` tests this identity form in the provenance layer, not in this engine’s `_dedupe_records()` path. Target-engine dedup tests do not cover it.

**Repair:** factor one typed work-identity helper and use it for retrieval dedup, node dedup, global provenance, and report aggregation.

### E-09 — P3: several public/internal contracts drift from implementation

**References:** `router.py:143-147`, `157-195`; `rank.py:4-11`, `137-142`; `investigate.py:13`, `708-719`, `875-896`; `SKILL.md:150-200`.

- The router comment says a malformed overlay fails closed while explicit `--channels` remains available (`router.py:146`), but known explicit channels are correctly refused by `investigate.py:525-533`. The capability behavior is safer than the comment.
- The router/workflow promises web + primary + community coverage. `route(..., max_channels=2)` currently returns `['duckduckgo', 'europepmc']` for a biomed question, silently dropping the community role after post-composition truncation (`router.py:191`). `--max` has no validation for zero/negative values either.
- The generic CLI usage advertises `--reads K`, but agent triage ignores it (E-04).
- The rank module says its quota means primaries are always read, but E-06 shows it does not.

These statements should either become tested invariants or be made narrower and explicit about their conditions.

## Confirmed performance/design limits (not bugs by themselves)

### D-01 — retrieval is parallel; selected full reads are intentionally serial

**References:** `investigate.py:320-359` versus `578-613`.

This is a clear architecture choice. The `ThreadPoolExecutor` concurrently fans out retrieval. `_execute_reads()` then loops through selected sources without an executor, so each selected full read adds directly to leaf latency. A hermetic four-read probe with each reader sleeping 50 ms took **0.219 seconds**, consistent with serial rather than parallel execution.

Serial reads can be rational for rate limits, browser/session safety, and simple artifacts. The cost is material when every read can wait up to 30 seconds and an arXiv `/abs/` read may try both HTML and PDF. There is no whole-leaf or whole-run deadline, tail cancellation, or cross-worker concurrency limiter in this engine.

### D-02 — zero-result relaxation favors recall but can triple connector traffic

**References:** `investigate.py:328-341`.

The engine does the right thing by retrying only after a true zero and by limiting relaxation to two shorter variants. That is a sound recall guard. It still means every empty channel can make three endpoint calls, and telemetry records only the final relaxed query rather than an attempt count. In a slow/degraded multi-channel run, latency and request cost are therefore understated.

### D-03 — agent triage is a valuable control point but not a technical prompt-injection boundary

**References:** `investigate.py:688-704`, `708-760`; `SKILL.md:157-172`.

The code honestly comments that snippets are untrusted and that truncating them does not neutralize prompt injection. The manifest then supplies title/snippet text directly to the selecting agent. The instruction “quote, never obey” is a procedural defense, not isolation or a policy-enforced boundary.

No exploit was executed in this audit, and this is not a claim that a particular model will be compromised. It is a credible autonomous-agent risk: a search result can influence which sources the agent opens before the agent has independently evaluated it. Add adversarial snippets to tests, structured provenance labels, a separate untrusted-data rendering context where possible, and tool-policy enforcement that does not depend solely on natural-language admonitions.

## Credible but not dynamically demonstrated concurrency risks

### R-01 — no lock/CAS protects a node's triage state or finalization writes

**References:** `investigate.py:684-805`, `826-865`, `626-657`; dependency behavior in `treestate.py:126-143`, `164-172`, `391-414`.

The skill asks the host to use parallel leaf workers. Separate leaves are a sensible scope boundary, but this engine has no per-node lease, atomic compare-and-swap, sequence number, or lock around `.triage.json`, `sources.jsonl`, `evidence.md`, `telemetry.jsonl`, or `status.json`. A duplicate scheduler delivery, a resume racing a late worker, or two humans/agents operating the same node can overwrite a manifest, read the same work twice, append conflicting evidence rounds, or lose a status field through read-modify-write races.

This report does **not** claim an observed live corruption. It is a static concurrency finding with high reproduction feasibility: launch two `candidates`/`read` sequences against the same node with barriers around the named file writes. Existing tests are sequential and do not exercise it.

**Repair:** use a per-node lease and monotonic round/generation IDs; atomically write JSON state; append event records with idempotency keys; reject a read request whose manifest generation no longer matches; serialize global index updates or make them set-union/idempotent.

## Strengths confirmed in the line pass

- **Capability boundary is real for known channels.** `_gather()` validates known requested connectors before retrieval (`investigate.py:523-533`), and the portable security test proves a disabled explicit channel cannot be revived.
- **The happy-path retrieval topology is efficient.** Fan-out runs concurrently (`320-355`), and zero-result relaxation is capped and only triggered after an initial zero (`328-341`).
- **Source identity handling is stronger than typical URL-only dedup.** DOI, arXiv URL, PMID, title decorations, truncated search titles, and cross-round aliases get careful treatment (`145-285`, `452-470`), with substantial regression coverage. E-08 is a specific missing metadata form, not a dismissal of that work.
- **The agent-triage split is well conceived.** It separates retrieval from epistemic source choice, caps hidden requeries at two, retains a pending manifest after invalid selection, and supports an explicit zero-read abstention (`708-823`). These are meaningful improvements over a fixed top-k agent loop.
- **Artifact and telemetry surfaces are unusually good.** Notes, evidence, source rows, decisions, and round telemetry make postmortem analysis possible (`478-492`, `626-657`, `826-865`).
- **State is at least crash-aware.** The engine marks a node `active` before work, and the broader state system has a resumable frontier. That is better than silently losing an interrupted task; R-01 concerns duplicate ownership, not the existence of resume support.
- **Ranker preserves valuable class diversity.** The evidence/lead/color quota mechanics are real and regression-tested; the issue is that this should not be described as a primary-source guarantee.

## Tests reviewed and what they do not establish

I ran:

```bash
python3 tests/test_aletheia.py
# Ran 157 tests in 9.061s — OK

python3 tests/test_portable_security.py
# Ran 10 tests in 0.659s — OK
```

Relevant direct target coverage is concentrated in:

- `tests/test_aletheia.py:622-735` — router subprocess routes and user overlay behavior.
- `tests/test_aletheia.py:1284-1788` — isolated aletheia-research module loads for anchoring, dedup, full-text branches, rank behavior, triage, and caps.
- `tests/test_aletheia.py:1950-1987` — configuration overlay reaches a router subprocess.
- `tests/test_portable_security.py:84-103` — disabled explicit channel refusal.

There is an important module-name trap: `tests/test_aletheia.py:22-42` imports `deep-aletheia`'s `investigate` and `router` first. Accordingly, `TestInvestigateRounds` at `525-571` and `TestRouterClassify` at `573-581` test the old/frozen module, not this `aletheia-research` engine. The later subprocess and isolated-loader tests are the applicable ones.

Passing tests establish that many targeted regression cases work. They do not establish resource bounds, a live connector's health, source identity, cost, race safety, adversarial snippet resistance, or quality superiority over a bounded single-agent baseline.

## Reproduction commands

These commands are hermetic unless explicitly noted. They are designed to demonstrate the current behavior, not to change the repository.

### P-01 — specialist-source cancellation in a dual-domain route

```bash
ALETHEIA_CONFIG_DIR=/tmp/aletheia-audit-nonexistent-20260728 BRAVE_API_KEY='' \
  python3 .cursor/skills/aletheia-research/scripts/router.py \
  'machine learning model for cancer clinical trial' --json --max 6
```

Expected: `domains` is `biomed, cs_software`; `arxiv`, `europepmc`, `github`, and `stackexchange` appear under `excluded`; only generic `openalex` remains as an academic connector.

### P-02 — primary field is not a quota

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path

p = Path('.cursor/skills/aletheia-research/scripts/rank.py')
s = importlib.util.spec_from_file_location('rank_probe', p)
r = importlib.util.module_from_spec(s); s.loader.exec_module(r)
rows = [
    {'url': f'https://secondary.example/{i}', '_class': 'evidence', '_relnorm': 1.0,
     'score': 1.0 - i * .01, 'primary': False} for i in range(3)
] + [
    {'url': 'https://primary.example/study', '_class': 'evidence', '_relnorm': 1.0,
     'score': .10, 'primary': True},
    {'url': 'https://lead.example/thread', '_class': 'lead_gen', '_relnorm': 1.0, 'score': .09},
]
print([x['url'] for x in r.select_reads(rows, 3)])
PY
```

Expected: the two high-score secondary `evidence` rows plus the lead row are selected; the eligible primary is absent.

### P-03 — relative relevance gate accepts a weak best match

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path

p = Path('.cursor/skills/aletheia-research/scripts/rank.py')
s = importlib.util.spec_from_file_location('rank_probe', p)
r = importlib.util.module_from_spec(s); s.loader.exec_module(r)
q = 'alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau'
rows = r.rank(q, [
    {'url': 'https://weak.example/a', 'title': 'alpha', '_class': 'evidence'},
    {'url': 'https://zero.example/b', 'title': 'unrelated banana', '_class': 'evidence'},
])
print([(x['url'], x['relevance'], x['_relnorm']) for x in rows])
print([x['url'] for x in r.select_reads(rows, 1)])
PY
```

Expected: the weak one-token result has approximately `(0.1559, 1.0)` for `(raw, normalized)` relevance and is selected.

### P-04 — no enabled channels produces a successful empty completed round

```bash
python3 - <<'PY'
import json, os, pathlib, subprocess, sys, tempfile

root = pathlib.Path.cwd()
s = root / '.cursor/skills/aletheia-research/scripts'
with tempfile.TemporaryDirectory() as d:
    cfg = pathlib.Path(d) / 'config'; cfg.mkdir()
    p = cfg / 'channels.json'
    p.write_text(json.dumps({'schema_version': 1, 'enabled': []}))
    os.chmod(p, 0o600)
    env = dict(os.environ, ALETHEIA_CONFIG_DIR=str(cfg), PYTHONNOUSERSITE='1')
    run = subprocess.check_output([sys.executable, s/'treestate.py', 'init', 'none',
                                   '--thoroughness', 'quick', '--base', d], text=True, env=env).strip()
    node = pathlib.Path(run) / 'tree/root'
    done = subprocess.run([sys.executable, s/'investigate.py', '--node', node],
                          text=True, capture_output=True, env=env)
    status = json.loads((node/'status.json').read_text())
    body = json.loads(done.stdout)
    print({'returncode': done.returncode, 'reads_ok': body['reads_ok'],
           'state': status['state'], 'rounds': status['rounds']})
PY
```

Expected: `{'returncode': 0, 'reads_ok': 0, 'state': 'investigated', 'rounds': 1}`.

### P-05 — completion timing controls retained same-work alias

```bash
python3 - <<'PY'
import importlib.util, time
from pathlib import Path

p = Path('.cursor/skills/aletheia-research/scripts/investigate.py')
s = importlib.util.spec_from_file_location('investigate_probe', p)
i = importlib.util.module_from_spec(s); s.loader.exec_module(i)
i._cfg_classes = lambda: {'p': {'class': 'evidence'}, 'm': {'class': 'evidence'}}
def choose(pd, md):
    def primary(*_):
        time.sleep(pd); return [{'url': 'https://arxiv.org/abs/2501.12345', 'doi': '10.1000/same-work'}]
    def mirror(*_):
        time.sleep(md); return [{'url': 'https://mirror.example/same-work', 'doi': '10.1000/same-work'}]
    i.DISPATCH.update(p=primary, m=mirror)
    rows, _ = i.retrieve('q', ['p', 'm'], 1, 1)
    return i._dedupe_records(rows)[0]['url']
print({'mirror_faster': choose(.04, 0), 'primary_faster': choose(0, .04)})
PY
```

Expected: the mirror survives when it is faster; the arXiv URL survives when it is faster.

### P-06 — run the existing direct tests

```bash
python3 tests/test_aletheia.py
python3 tests/test_portable_security.py
```

Expected at the frozen target: 157 and 10 passing tests respectively. Their passing status does not contradict the untested paths listed above.

## Per-file line-range coverage manifest

Every listed range was displayed with `nl -ba`. Ranges are contiguous and exhaustive; “no material finding” means no additional issue rose to the severity threshold after the line-level review, not that the code is unimportant.

### `investigate.py` — 1–902 fully accounted for

| Lines | Inspected behavior | Outcome |
|---:|---|---|
| 1–14 | module purpose, artifact/CLI contract | Contract overstates full-read assurance in light of E-01/E-06; otherwise clear. |
| 15–42 | imports, path insertion, dependency surface | No material finding; shared module-name/path complexity contributes to test caveat. |
| 43–67 | caps and lexical constants | Triage cap is positive; `MAX_READ_CHARS` is a content cap, not an identity guarantee. |
| 68–110 | run topic/proper-noun/subject-term extraction | No material finding; covered by anchor regressions. |
| 111–144 | query anchoring | No material finding; nuanced, well-regression-tested behavior. |
| 145–237 | work identities and title matching | E-08: misses `arxiv_id`/`arxiv` metadata parity. |
| 238–287 | work/title dedup | E-05: first arrival becomes the representative; E-08 propagates here. |
| 288–315 | dispatch table | Manual dispatch surface is coherent; duplicate/unknown caller input is not validated (E-03/E-04). |
| 316–361 | parallel retrieval and relaxation | E-04 cost/telemetry limits; E-05 nondeterministic completion order. |
| 362–412 | note persistence/full-text reader | E-01 length-only success. ArXiv fallback itself is a strength. |
| 413–472 | existing artifact lookup/merge | No material new defect; non-atomic rewrite contributes to R-01 under concurrent writers. |
| 473–502 | config, telemetry, round cap | E-04: rounds are not a resource ledger; unlimited/max deliberately uncapped. |
| 503–555 | gather state/routing/ranking | E-02 routing consequence and E-03 empty/failing round state transition. |
| 556–577 | read-floor | E-07: relative score can override stricter subject filtering. |
| 578–659 | read loop, evidence/source/status telemetry | E-01, E-03, D-01, and R-01 apply. |
| 660–676 | one-shot deterministic path | Inherits E-01/E-04/E-06/E-07; well-scoped fallback documentation. |
| 677–707 | triage protocol/snippet shaping | D-03 prompt-injection boundary limitation is explicitly acknowledged but not solved. |
| 708–762 | gather candidates/persist manifest | E-03 errors hidden from agent output; E-04 `--reads` not accepted here; R-01 stale-manifest risk. |
| 763–806 | context/pick execution | Bounded selection is a strength; R-01 lacks generation/lease protection. |
| 807–825 | explicit reject | Strong honest-abstention behavior; no material finding. |
| 826–867 | evidence serialization | Good artifact trail; non-atomic append/write is part of R-01. |
| 868–902 | CLI parsing/dispatch | E-04 candidate path drops parsed `--reads`; parser otherwise straightforward. |

### `router.py` — 1–217 fully accounted for

| Lines | Inspected behavior | Outcome |
|---:|---|---|
| 1–11 | module routing contract | Role/primary language is stronger than guarantees under E-02/E-09. |
| 12–35 | imports/env/available map | No material finding; manual sync with dispatch remains a maintenance concern. |
| 36–106 | taxonomy/signals | Keyword taxonomy is intentionally simple; ambiguous-domain limitation is acknowledged by design, not separately confirmed as a bug. |
| 107–130 | boundary matching/domain selection | Word-boundary repair is sound; tie/ambiguity has no confidence/abstain path, a design limitation. |
| 131–156 | enabled config and web fallback | Fail-closed config is a strength; stale comment at 146 and E-03 downstream behavior matter. |
| 157–197 | route construction/filtering/truncation | E-02 union-exclusion bug and E-09 role loss under small/invalid `max`. |
| 198–217 | CLI | No material finding beyond unvalidated `--max` feeding E-09. |

### `rank.py` — 1–216 fully accounted for

| Lines | Inspected behavior | Outcome |
|---:|---|---|
| 1–15 | module promise | E-06: “primaries always read” is inaccurate. |
| 16–36 | relevance/class constants | E-07 stems from normalized rather than absolute relevance semantics. |
| 37–63 | authority lists | Useful pragmatic guard; necessarily incomplete/hardcoded but no discrete defect found. |
| 64–102 | authority and subject helper functions | No material finding; subject matching is intentionally conservative. |
| 103–130 | rerank/scoring | E-06 only 5% primary boost; E-07 relative normalization. |
| 131–193 | read selection/quotas | E-06 no primary quota; E-07 relative eligibility; class quotas themselves work. |
| 194–216 | CLI | No material finding. |

## Recommended repair order

1. **Ship the typed read-identity gate before presenting “read in full” as evidence success.** This is the high-stakes correctness prerequisite.
2. **Fix route composition and no-channel/all-failed state transitions.** A system should never silently call an empty/failed round investigated.
3. **Make cost controls executable.** Validate/normalize channel input, pass `--reads` through triage, impose a global ledger and resource caps, and count every retry.
4. **Make source representative choice deterministic and provenance-aware.** Cluster aliases before selecting the best record.
5. **Replace the primary promise with an actual primary/direct-source invariant or an explicit absence state.** Calibrate relevance against absolute evidence rather than batch-relative rank.
6. **Add concurrency ownership and adversarial-manifest tests.** Keep the attractive artifact-first architecture, but make its multi-agent boundary mechanically safe.
