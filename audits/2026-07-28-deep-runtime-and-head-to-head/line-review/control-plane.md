# Literal control-plane review

Scope: .cursor/skills/aletheia-research/scripts/treestate.py, report.py, verify.py,
and synthesize.py.

Frozen candidate: bd5e1a50a491ee7c5ebe1382ace35c21f7909de5. This review ran from
cbed4789a1c4b283189ec62742eb6ae1ea40f087. A git diff --exit-code confirmed the four
scoped source files are byte-identical between the frozen candidate and audit commit.
The SHA-256 values, exact review chunks, and direct-test mapping are in
[control-plane-coverage.json](control-plane-coverage.json).

## Verdict

The sequential happy path is reasonably engineered: initialization, finite budget
splitting, hashing, strict claim-file parsing, and the lexical verifier's refusal to
claim semantic support are good. The actual control plane is not high-assurance.

| Area | Grade | Assessment |
|---|---:|---|
| Sequential mechanics | B | Normal run/tree operations and score hashes mostly work. |
| Parallel and resume integrity | D | No transaction/lock protocol; reproduced races duplicate QIDs/index rows and bypass the node cap. |
| Citation/read identity | D | A body is trusted from a short hash filename, not established as the cited URL's body. |
| Enforced research gates | D | An answer to a nonexistent QID clears the thin-child gate; tree actions are replayable. |
| Auditability | C+ | Post-audit hashes are useful, but semantic review is a writer assertion and the claimed full bundle omits material artifacts. |
| Cost observability | C- | It counts retrieval/read activity, not model tokens, dollars, whole-agent time, or human review. |

**Overall: C- for supervised experiments, not yet safe to describe as a high-assurance,
fully resumable research system.** The framework's ideas are better than its control
enforcement.

Severity labels: P1 is a confirmed integrity/control failure; P2 is a material
reliability/auditability defect; P3 is a lower-impact documentation/accounting problem.

## Exact source coverage

Every source line was viewed with nl -ba. “No additional finding” means the range was
read and had no issue beyond a cross-reference; it does not assert test coverage.

### treestate.py — 612 of 612 lines

| Lines | Review result |
|---|---|
| 1–38 | Contract/layout and CLI reviewed. The unbounded wording is inaccurate; see D-03. |
| 39–83 | Imports, time, slug, and deterministic file hashing reviewed. No material finding. |
| 86–123 | Runtime fingerprinting reviewed. Good provenance fingerprint, not model/web replayability. |
| 126–188 | JSON/JSONL write and status mutation reviewed. In-place, unlocked writes contribute to CP-03. |
| 190–258 | Tier resolution/init reviewed. Good normal validation and mkdir collision loop; D-03/D-04 apply. |
| 261–300 | Node counting and cap checks reviewed. Check-then-act allows CP-03 under concurrency. |
| 303–367 | Split/allocation reviewed. Normal finite arithmetic is good; CP-04 and CP-07 apply. |
| 370–438 | Proposal/source index/findings reviewed. Replay and nontransactional writes contribute to CP-03/CP-04. |
| 439–486 | Ask/answer/frontier reviewed. CP-01 and corrupt-state behavior in CP-03 occur here. |
| 489–509 | Tree rendering reviewed. It traverses stale child directories from CP-04. |
| 512–612 | CLI reviewed. Python-permissive numeric JSON reaches CP-07. |

### report.py — 568 of 568 lines

| Lines | Review result |
|---|---|
| 1–40 | Full/complete bundle contract reviewed; CP-06. |
| 43–131 | Lenient display reader and strict gate reader reviewed. Good distinction; declared multi-URL matching is clear. |
| 134–183 | Hash-based claim state reviewed. Correct invalidation after changed artifacts; D-01 remains. |
| 186–226 | Attestation writer reviewed. Strict hashes, but CP-05 and self-asserted semantics apply. |
| 229–300 | Activity telemetry reviewed. Useful reconciliation but not total cost; D-04. |
| 303–396 | Bundle and outline reviewed. Resilient display behavior, incomplete claimed pack; CP-06. |
| 399–459 | Claim-source/origin selection reviewed. Reasonable normal path; no additional material finding. |
| 462–514 | Score/lifecycle reviewed. CP-05; ordinary pending/broken-row blocking is good. |
| 517–568 | CLI reviewed. No additional material finding. |

### verify.py — 183 of 183 lines

| Lines | Review result |
|---|---|
| 1–28 | Layer contract reviewed. Correctly separates lexical relevance and entailment; CP-05 mismatch noted. |
| 29–65 | Imports, thresholds, stemmer reviewed. Conservative lexical heuristic; no semantic overclaim in code. |
| 67–103 | Note lookup/live fallback reviewed. CP-02 source identity failure. |
| 105–142 | Per-claim result reviewed. Never emits supported, but 200-character body rule is not identity; CP-02. |
| 145–159 | Batch summary reviewed. No additional material finding. |
| 162–183 | CLI reviewed. No additional material finding. |

### synthesize.py — 210 of 210 lines

| Lines | Review result |
|---|---|
| 1–35 | Contract, private umask, imports reviewed. Good private default; enforcement claim is too strong. |
| 37–76 | JSONL loading, answer test, child discovery reviewed. CP-01 and CP-04. |
| 79–115 | Recursive sources/instance dedupe reviewed. Normal dedupe is sound; assumes well-formed tree. |
| 116–137 | Independence metrics reviewed. Hidden fallback is CP-08. |
| 139–191 | Gate/write behavior reviewed. CP-01 and corrupt-row hiding CP-09. |
| 194–210 | CLI gate reviewed. It returns the expected code but cannot enforce findings writer behavior; CP-04. |

## Confirmed defects

### CP-01 — P1 — A wrong answer QID clears the ask-before-authoring gate

**Type:** confirmed correctness bug.

**Code:** treestate.py:439–463; synthesize.py:62–68, 139–156, 194–205.

answer() accepts any QID, appends it, and marks the node answered. _answered() only
checks whether answers.jsonl has any nonblank line; it neither parses an answer nor
matches it to an outstanding question. Thus a real unanswered question can be bypassed
by a typoed QID, even with an empty answer body.

Executed probe:

~~~bash
python3 - <<'PY'
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.getcwd(), ".cursor/skills/aletheia-research/scripts"))
import treestate, synthesize
with tempfile.TemporaryDirectory() as base:
    run = treestate.init_run("gate", budget=16, unit=4, base=base)
    root = os.path.join(run, "tree", "root")
    a, b = treestate.split_node(root, [["a", "substantial"], ["b", "thin"]])
    treestate.write_findings(a, "a" * 200)
    treestate.write_findings(b, "x")
    qid = treestate.ask(b, root, "What evidence supports this?")
    treestate.answer(b, "not-" + qid, "")
    q = json.loads(open(os.path.join(b, "questions.jsonl")).read())
    result = synthesize.synthesis_input(root)
    rc = synthesize.main(["--node", root, "--gate"])
    print({"question_answered": q["answered"], "unresolved": result["unresolved"], "gate_rc": rc})
PY
~~~

Observed output:

~~~text
{'question_answered': False, 'unresolved': [], 'gate_rc': 0}
~~~

This is especially revealing because tests/test_aletheia.py:597–602 clears the gate by
calling answer with q1 without first creating a question. It tests the weak condition,
not a real QID match.

**Repair:** generate immutable QIDs, reject unknown/duplicate answers, reconcile parsed
questions and answers, and require all designated questions to be answered before a gate
is clear.

### CP-02 — P1 — Verification does not prove that stored text came from the cited URL

**Type:** confirmed evidence-identity bug.

**Code:** verify.py:67–98 and 105–142. Supporting storage format only:
channel-retrieval/scripts/read.py:94–100 and
aletheia-research/scripts/investigate.py:362–373.

_note_path derives a ten-hex-character, 40-bit SHA-1 filename from the requested URL and
returns a matching file. _source_text then trusts its contents. It does not compare the
stored note header, a resolved URL, a source-record binding, response status, content
type, or a content hash. verify_claim calls any body of at least 200 characters a working
link and scores lexical overlap.

Executed probe:

~~~bash
python3 - <<'PY'
import hashlib, os, sys, tempfile
sys.path.insert(0, os.path.join(os.getcwd(), ".cursor/skills/aletheia-research/scripts"))
import verify
with tempfile.TemporaryDirectory() as reads:
    cited = "https://cited.example/paper"
    wrong = "https://wrong.example/anti-bot"
    p = os.path.join(reads, hashlib.sha1(cited.encode()).hexdigest()[:10] + ".md")
    open(p, "w").write("<!-- source: %s -->\n\n" % wrong +
                       "Vaccines reduce severe disease and hospitalization. " * 8)
    v = verify.verify_claim("Vaccines reduce severe disease and hospitalization",
                            [cited], None, reads, 0.1)
    print({k: v[k] for k in ("url", "link_works", "verdict")})
PY
~~~

Observed output:

~~~text
{'url': 'https://cited.example/paper', 'link_works': True, 'verdict': 'relevant'}
~~~

The saved body says it came from the wrong URL. This does not rely on a SHA-1 collision:
a stale/misfiled file or a long error shell is enough. Existing verify tests create
arbitrary hash-named note content (tests/test_aletheia.py:419–426) and test recursive
lookup (1451–1469), but do not bind body to source identity.

**Repair:** persist/read structured metadata containing requested URL, resolved URL,
response status/content type, full content hash, and exact source-record path; fail
closed on mismatch. A length threshold is not an identity gate.

### CP-03 — P1 — Parallel and crash-resume invariants are not transactional

**Type:** confirmed concurrency and crash-recovery defect.

**Code:** treestate.py:126–143, 164–172, 267–289, 303–367, 391–414, 439–486.

The documented workflow creates parallel leaf workers, but shared state is built from
unlocked read/modify/write and check/then-act operations. ask counts lines then appends;
add_sources reads a dedupe set then appends; can_split counts nodes then later creates
children; status JSON is overwritten in place.

Controlled barrier probes produced all of these confirmed outcomes:

| Scenario | Expected invariant | Observed |
|---|---|---|
| Two concurrent ask calls | unique QIDs | both returned and persisted q1 |
| Two concurrent add_sources calls for the same URL from two leaves | one global index row | both returned 1; two equal URL rows persisted |
| Two concurrent child splits after each observed two slots, max_nodes=5 | actual nodes ≤5 | no error; count_nodes was 7 |
| Truncated status.json | visible recovery error/frontier node | resumable frontier returned an empty list and tree showed unknown state |

Executable race probe:

~~~bash
python3 - <<'PY'
import os, sys, tempfile, threading
sys.path.insert(0, os.path.join(os.getcwd(), ".cursor/skills/aletheia-research/scripts"))
import treestate
with tempfile.TemporaryDirectory() as base:
    r = treestate.init_run("race", budget=8, unit=4, base=base)
    n = os.path.join(r, "tree", "root")
    old, barrier = treestate._append_jsonl, threading.Barrier(2)
    def append(path, row):
        if path.endswith("questions.jsonl"): barrier.wait(timeout=3)
        return old(path, row)
    treestate._append_jsonl = append
    got = []
    ts = [threading.Thread(target=lambda i=i: got.append(treestate.ask(n, str(i), "q")))
          for i in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]; treestate._append_jsonl = old
    print("qids", sorted(got))

    r = treestate.init_run("cap", budget=32, unit=4, max_depth=3,
                            max_children=2, max_nodes=5, base=base)
    root = os.path.join(r, "tree", "root")
    a, b = treestate.split_node(root, [["a", "a"], ["b", "b"]])
    old, barrier = treestate.can_split, threading.Barrier(2)
    def check(node):
        out = old(node); barrier.wait(timeout=3); return out
    treestate.can_split = check
    ts = [
        threading.Thread(target=treestate.split_node, args=(a, [["a1", "a1"], ["a2", "a2"]])),
        threading.Thread(target=treestate.split_node, args=(b, [["b1", "b1"], ["b2", "b2"]]))
    ]
    [t.start() for t in ts]; [t.join() for t in ts]; treestate.can_split = old
    print("max_nodes=5 actual", treestate.count_nodes(r))
PY
~~~

Observed output:

~~~text
qids ['q1', 'q1']
max_nodes=5 actual 7
~~~

The test suite only covers sequential versions: tests/test_aletheia.py:525–571,
1227–1241, and 1790–1798. It has no concurrent-writer, interruption, or atomic-write
test.

**Repair:** use a single materializer or a transactional store such as SQLite. At a
minimum, lock per-run mutations, write JSON through fsync plus atomic replace, use UUID
QIDs, make index insertion idempotent, and treat corrupt status as an explicit failure.

### CP-04 — P1 — Splits can replay and silently mix stale branches into synthesis

**Type:** confirmed state-machine bug.

**Code:** treestate.py:164–172, 303–367, 370–388, 429–436, 489–509; synthesize.py:71–84,
139–156, 194–205.

split_node has no requirement that a node is pending or has no children. Repeating it
changes the parent status list but leaves old child directories in place. Synthesis
enumerates all filesystem child directories, not that declared status list. Same-QID
replay overwrites status/spec but leaves old findings/evidence/questions, producing a
hybrid branch. write_findings never requires a passing synthesis gate.

Observed replay probe:

~~~json
{
  "status_children": ["c", "d"],
  "disk_children": ["a", "b", "c", "d"],
  "synthesis_children": 4,
  "old_marker_still_present": true
}
~~~

This can happen through retry or materializing a proposal twice; no malformed path is
needed. The lifecycle test at tests/test_aletheia.py:1134–1162 tests happy transitions
only and even writes root findings immediately after a split.

**Repair:** make node transitions versioned and one-shot, reject an already materialized
split, consume a signed/authoritative child manifest rather than arbitrary directories,
and require gate success before writing parent findings.

### CP-05 — P2 — A lexical row marked needs_llm_check can still make a current run citation_complete

**Type:** confirmed state-contract inconsistency.

**Code:** verify.py:11–23 and 128–142; report.py:186–226 and 462–504.

verify attaches needs_llm_check: True to every result. audit_claim_scope accepts
off_topic as final and ignores that flag; score counts it as judged. A current run can
therefore claim completion with a lexical-stage row that says it still needs checking.

Probe outcome after writing one matching claim, one
{verdict: off_topic, needs_llm_check: true} row, a brief, and an audit:

~~~json
{"citation_accuracy": 0.0, "citation_complete": true,
 "needs_llm_check_still_present": true}
~~~

This does not inflate accuracy, but it falsely states completion. verify.py says every
result needs the flag while SKILL.md:232–239 tells the operator to fact-check only
relevant and borderline; the schema must choose and encode one policy.

**Repair:** use explicit lexical/semantic stages, reject any lexical-stage row in score
and audit-claims, or record why off_topic is semantically terminal. Include verifier
identity/evidence span/model provenance.

### CP-06 — P2 — The claimed FULL/COMPLETE bundle omits audit-critical artifacts

**Type:** confirmed contract mismatch.

**Code:** report.py:3–17, 303–378, 381–396.

The bundle says it is the full/complete pack and includes the source index. It omits
global index/sources.jsonl contents and node decisions.jsonl, questions.jsonl,
answers.jsonl, spec.md, status.json, and proposal.json. It also formats rather than
reproduces raw per-node source records.

Probe result after adding markers only to the global index and a decision log:

~~~json
{"index_marker_in_bundle": false, "decision_marker_in_bundle": false}
~~~

Rejected evidence, unresolved questions, and decision rationale are exactly what a
calling auditor needs. Bundle tests at 809–833 and 1104–1123 assert inclusion of selected
positive markers but do not inventory all advertised artifacts.

**Repair:** produce a true manifest/archive with all artifacts or rename the output a
bounded handoff dossier and state omissions. Add a safe, explicit all-artifacts mode.

### CP-07 — P2 — Infinity weight input produces NaN state and a later crash

**Type:** confirmed input-validation bug.

**Code:** treestate.py:329–354 and 579–580.

Python json.loads accepts Infinity. The code checks length and positivity but not finite
numeric values. [Infinity, 1] makes inf/inf into NaN; json.dump persists NaN and a later
can_split throws when converting it to an integer.

Observed probe:

~~~json
{"budgets": [NaN, 4.0], "first_budget_is_nan": true,
 "can_split_after": "ValueError: cannot convert float NaN to integer"}
~~~

tests/test_aletheia.py:1800–1805 tests only a wrong number of weights.

**Repair:** require finite real numeric values, write JSON with allow_nan=False, and
validate persisted numeric config/state when loading.

### CP-08 — P2 — Structural-origin failure is silently reported as structural independence

**Type:** confirmed degraded-mode observability defect.

**Code:** synthesize.py:86–99 and 116–137.

When provenance_graph.build_clusters raises, _origin_clusters returns the weaker
voice_key count but exposes it as independent_origins/origin_echo_ratio with no method,
degraded, or error field. A controlled failure on six cross-domain near-duplicate records
changed normal values of voices=6, independent_origins=1, origin_echo_ratio=0.833 into
voices=6, independent_origins=6, origin_echo_ratio=0.0 under the exact same schema.

Tests at 1243–1260 cover structural success only.

**Repair:** record origin_method as structural or voice_fallback plus an error flag, and
block claims that structural independence was measured when fallback occurred.

### CP-09 — P2 — Corrupt source rows disappear before independence is calculated

**Type:** confirmed fail-open design choice.

**Code:** synthesize.py:45–59, 79–84, 139–191; contrast report.py:88–106.

_load_jsonl silently skips malformed JSON and non-object rows. Synthesis emits a normal
independence result with no corrupt-row count or warning. This combines with CP-03:
partially written evidence can vanish from the artifact meant to surface evidence gaps.
The behavior is intentionally locked in by tests/test_aletheia.py:1262–1273.

**Repair:** retain display resilience, but count/report corrupt rows and block or clearly
degrade research-quality independence/synthesis until repair.

## Supplemental executed probes

The following compact probe was also run from repository root. It supplies executable
evidence for CP-04 through CP-08 rather than relying only on code inspection.

~~~bash
python3 - <<'PY'
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.getcwd(), ".cursor/skills/aletheia-research/scripts"))
import treestate, synthesize, report

with tempfile.TemporaryDirectory() as base:
    # CP-04: stale branches after replayed split.
    run = treestate.init_run("replay", budget=32, unit=4, base=base)
    root = os.path.join(run, "tree", "root")
    treestate.split_node(root, [["a", "old"], ["b", "old"]])
    treestate.write_findings(os.path.join(root, "children", "a"), "OLD_MARKER")
    treestate.split_node(root, [["c", "new"], ["d", "new"]])
    print("replay", treestate._read_json(os.path.join(root, "status.json"))["children"],
          sorted(os.listdir(os.path.join(root, "children"))),
          synthesize.synthesis_input(root)["children"])

    # CP-07: Python JSON Infinity becomes persistent NaN.
    run = treestate.init_run("weights", budget=16, unit=4, base=base)
    root = os.path.join(run, "tree", "root")
    child = treestate.split_node(root, [["inf", "i"], ["one", "o"]],
                                 weights=json.loads("[Infinity, 1]"))[0]
    print("nan budget", treestate._read_json(os.path.join(child, "status.json"))["budget"])
    try:
        treestate.can_split(child)
    except Exception as exc:
        print("nan resumes as", type(exc).__name__)

    # CP-05: direct lexical off_topic remains needs_llm_check but completes.
    run = treestate.init_run("state", budget=8, unit=4, base=base)
    claim = {"claim": "assertion", "url": "https://example.invalid/source"}
    open(os.path.join(run, "claims.jsonl"), "w").write(json.dumps(claim) + "\n")
    open(os.path.join(run, "verify.jsonl"), "w").write(
        json.dumps(dict(claim, verdict="off_topic", needs_llm_check=True)) + "\n")
    report.write_brief(run, "# brief")
    report.audit_claim_scope(run, "test-attestor")
    print("completion", report.score(run)["citation_complete"])

    # CP-06: claimed full bundle lacks both markers.
    run = treestate.init_run("bundle", budget=8, unit=4, base=base)
    root = os.path.join(run, "tree", "root")
    open(os.path.join(run, "index", "sources.jsonl"), "a").write('{"marker":"INDEX_ONLY"}\n')
    treestate.log_decision(root, "test", "DECISION_ONLY")
    pack = report.bundle(run, reads=True)
    print("bundle", "INDEX_ONLY" in pack, "DECISION_ONLY" in pack)
PY
~~~

Observed output shape:

~~~text
replay ['c', 'd'] ['a', 'b', 'c', 'd'] 4
nan budget nan
nan resumes as ValueError
completion True
bundle False False
~~~

For CP-08, normal provenance clustering of six near-duplicate, cross-domain records
returned independent_origins=1 and origin_echo_ratio=0.833. Replacing only
synthesize.pg.build_clusters with a function that raises produced
independent_origins=6 and origin_echo_ratio=0.0 with no fallback/degradation field.

## Design limitations and documentation mismatches

### D-01 — P2 — Hashes prove artifact identity after audit, not independent semantic review

report.py:186–226 correctly binds brief, claims, and verdict files after an attestation.
It cannot prove a different model/person read the source, checked entailment, or found
omitted claims; any nonempty auditor string is accepted. This is an acceptable explicit
trust boundary, not evidence of independent verification.

### D-02 — P2 — “Enforced” gate language describes an advisory protocol

synthesize --gate returns 3, but treestate.write_findings at 429–436 does not require it
to run or pass. set_status at 164–172 and the status CLI can also write arbitrary state
fields. This is a design limitation under a trusted orchestrator but conflicts with
“enforced back-and-forth” language in SKILL.md:211–215.

### D-03 — P3 — Unlimited is finite structural configuration, not infinity

treestate.py:26–28 and 193–198 call default work unbounded/effectively unbounded, while
199–206 configures 1,000,000 logical budget, depth 99, six children, and 512 nodes
(2,048 for max). SKILL.md:59–75 presents infinity. Say agent-paced with high finite
structural backstops instead. These still do not cap tokens, dollars, time, or direct
reads.

### D-04 — P2 — Telemetry cannot support a cost or speed claim

report.py:229–287 tracks retrieval/read counts, read seconds, and artifacts. It has no
model token, provider price, end-to-end subagent wall time, synthesizer/verifier time, or
human-review ledger. It is useful activity telemetry, not an A/B cost envelope.

### D-05 — P2 — Default full-read handoff can be arbitrarily large

report.bundle with reads=True and max_chars=0 at 303–378 inlines all reads without a
per-read cap. That is valid archival behavior but a poor default for an ordinary agent
handoff: it adds context latency/cost and risks truncation. Use a manifest-first bounded
default.

## What is correct

- treestate.init_run validates topic/budget/unit at 214–221, creates unique directories
  at 235–245, fingerprints implementation/configuration at 246–252, and prevents sibling
  slug collision at 317–326.
- Normal finite split arithmetic floors children and repairs rounding drift at 329–354;
  tests 1203–1225 cover weighted and uniform paths.
- report strict JSONL parsing at 88–106 and artifact hash invalidation at 153–175 are
  sound. Tests 938–985 cover changed brief/verdict invalidation.
- verify never emits supported from lexical overlap at 20–23 and 128–142. The
  opposite-polarity regression at tests 428–435 is correctly only relevant.
- Telemetry avoids double-counting new agent gathers against their completed round at
  report.py:250–257.
- The display bundle survives damaged text at 43–50 and 353–364; retain that behavior
  for display while calculations expose degradation.
- Structural clustering and read-only source-basis paths have meaningful success tests
  at 1243–1260 and 1470–1482. The problem is hidden fallback, not lack of a normal path.

## Tests, exclusions, and repair order

Baseline execution at the reviewed bytes:

~~~bash
python3 -m unittest discover -s tests -p 'test_*.py'
~~~

Result: **186 tests passed in 12.930 seconds**. This is baseline regression evidence
only. It is not full source/test coverage, mutation coverage, connector validation, or a
review of out-of-scope runtime modules. Exact direct-test ranges and every source range
are recorded in control-plane-coverage.json.

Repair priority:

1. Fix CP-01, CP-02, CP-04, and CP-05 before treating any complete state or citation
   score as high assurance.
2. Add a real transactional/locking protocol and interruption tests for CP-03.
3. Bind read identity and type lexical, semantic, and audited claim states.
4. Surface degraded provenance/corruption instead of silently falling back or dropping it.
5. Make bundle/cost claims honest before any serious quality-per-dollar head-to-head.
