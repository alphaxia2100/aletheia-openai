# Literal runtime-boundary review

Frozen product snapshot reviewed: Git commit bd5e1a50a491ee7c5ebe1382ace35c21f7909de5 on 2026-07-28. The current audit branch commit was cbed4789a1c4b283189ec62742eb6ae1ea40f087; a scoped Git diff was empty, so every reviewed boundary file is byte-for-byte unchanged between those commits.

Scope: the original 4,316-line assignment—every executable Python line under .cursor/skills/channel-retrieval/scripts and .cursor/skills/provenance-audit/scripts, plus scripts/install.sh and scripts/preflight.py—was completely reviewed. The closure expansion adds scripts/install_claude.sh, containers/run-sandbox.sh, behavior-changing channel-retrieval/channels.json and aletheia-research/agents/openai.yaml, and containers/Dockerfile because run-sandbox builds and runs it. The companion boundary-coverage.json accounts for all 4,570 scoped lines and records each exact inspected range, including ranges with no separate finding. This was a literal line-numbered review, including contract-bearing comments and command help; it was not a review of only files reached by the normal happy path.

Test evidence: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests completed with 186 passing tests in 12.971 seconds. Passing tests establish the cases they exercise; they do not invalidate the untested boundary cases below.

Severity here is product impact, not a CVSS score. “High” means a realistic route to wrongly attributed evidence, an unenforced advertised control, or a failed integrity/safety property. No production files were changed.

## Confirmation status and hermetic probes

The findings are separated deliberately:

| Status | Meaning | Findings |
| --- | --- | --- |
| Confirmed by executable, no-network probe | The behavior below was observed against the frozen-equivalent source. | BND-H1, BND-H2, BND-H3, BND-H5, BND-H8 reporting portions, BND-H9 |
| Confirmed by deterministic control flow | The stated path follows directly from inspected code, but exercising it would require destructive setup, a real container engine, or an external service. | BND-H4, BND-H6, BND-H7, BND-H8 executable path, BND-M1, BND-M3 |
| Hardening / threat-precondition concern | The code admits the condition if a same-UID race, malicious upstream body, permissive preexisting directory, or untrusted harness environment exists. This review did not claim a cross-user exploit. | BND-M2, BND-M5, BND-M6 |

The following commands are reproducible from the repository root. They use monkeypatches and temporary directories only; they make no network request and do not modify the checkout.

Frozen-source equivalence:

    git diff --quiet bd5e1a50a491ee7c5ebe1382ace35c21f7909de5 cbed4789a1c4b283189ec62742eb6ae1ea40f087 -- .cursor/skills/channel-retrieval/scripts .cursor/skills/provenance-audit/scripts scripts/install.sh scripts/install_claude.sh scripts/preflight.py containers/run-sandbox.sh containers/Dockerfile .cursor/skills/channel-retrieval/channels.json .cursor/skills/aletheia-research/agents/openai.yaml && echo "PASS: same scoped source"

Expected output:

    PASS: same scoped source

Direct generic connector bypass, stale browser extraction after a failed open, reader exception classification, and portable-marker manifest bypass:

    PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
    import importlib.util, json, pathlib, shutil, sys, tempfile
    sys.path.insert(0, ".cursor/skills/channel-retrieval/scripts")
    import _config, _http, _agentreach, openalex
    import read as reader

    _config.require_enabled = lambda _: (_ for _ in ()).throw(AssertionError("gate was called"))
    openalex._http.get_json = lambda *_a, **_k: {"results": []}
    print("H1 direct generic search:", "BYPASS" if openalex.search("q", 1, 1) == [] else "UNEXPECTED")

    _http.validate_public_url = lambda _: None
    _agentreach._config.browser_authorized = lambda _: True
    _agentreach.find_cli = lambda _: "/safe/opencli"
    outputs = iter(["", json.dumps({"content": "STALE-PAGE"})])
    _agentreach._run = lambda *_a, **_k: next(outputs)
    print("H2 failed-open extract:", _agentreach.browser_extract("https://example.invalid/a", 1))

    reader._http.validate_public_url = lambda _: None
    reader._jina = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("reader failed"))
    print("H3 reader exception result:", reader.read_url("https://example.invalid/a", 1, 100))

    spec = importlib.util.spec_from_file_location("audit_preflight", "scripts/preflight.py")
    pf = importlib.util.module_from_spec(spec); spec.loader.exec_module(pf)
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        shutil.copytree(".cursor/skills", root / ".cursor" / "skills")
        pf.write_manifest(str(root))
        marker = root / ".aletheia-install.json"
        marker.write_text('{"mode":"portable-copy"}\n', encoding="utf-8")
        target = root / ".cursor" / "skills" / "channel-retrieval" / "scripts" / "_http.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# mutated\n", encoding="utf-8")
        marker.write_text('{"mode":"not-portable"}\n', encoding="utf-8")
        report = pf.check(str(root))
        print("H5 marker bypass:", report["ok"], report["manifest"], len(report["errors"]))
    PY

Expected output:

    H1 direct generic search: BYPASS
    H2 failed-open extract: ('STALE-PAGE', None)
    H3 reader exception result: ('', 'jina')
    H5 marker bypass: True not-applicable 0

Doctor false-green/misclassification and index-group non-collapse:

    PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
    import os, sys
    sys.path.insert(0, ".cursor/skills/channel-retrieval/scripts")
    sys.path.insert(0, ".cursor/skills/provenance-audit/scripts")
    import doctor, provenance_graph as pg
    doctor._config.browser_authorized = lambda _: True
    doctor._has_cli = lambda _: True
    print("H8 reddit binary-present:", doctor.p_reddit(1))
    os.environ["EXA_API_KEY"] = "nonempty-but-unverified"
    print("H8 key-only:", doctor.p_keyonly("exa", "exa_neural", "EXA_API_KEY"))
    doctor.live = lambda *_a, **_k: (False, "URLError")
    print("H8 S2 outage label:", doctor.p_s2(1))
    sources = [
        {"id": "a", "url": "https://one.example/a", "authors": [{"name": "A"}],
         "index_of_origin": "google_serper"},
        {"id": "b", "url": "https://two.example/b", "authors": [{"name": "B"}],
         "index_of_origin": "serpapi"},
    ]
    r = pg.audit(sources, [{"id": "c", "support": ["a", "b"]}])["claims"][0]
    print("H9 index-group result:", r["independent_sources"], r["index_groups"], r["flags"])
    PY

Expected output:

    H8 reddit binary-present: ('reddit', 'reddit', 'ok', 'agent-reach', 'live/authed via opencli (browser session)')
    H8 key-only: ('exa', 'exa_neural', 'ok', 'exa', 'EXA_API_KEY set')
    H8 S2 outage label: ('semantic_scholar', 'semantic_scholar', 'warn', 'semantic_scholar', 'shared anon pool throttles (429); add SEMANTIC_SCHOLAR_API_KEY')
    H9 index-group result: 2 ['google'] ['no_primary_source', 'discovery_monoculture']

## Bottom line

The code has real defensive work: private user overlays, no-follow secret-file reads, a bounded shared HTTP helper, disabled-by-default browser/session access, an atomic channel overlay, and a portable-file manifest. The problem is inconsistency. The strongest controls are often implemented in one route, while a neighboring route bypasses them; some status and provenance outputs claim stronger facts than the code can establish.

The most consequential current risks are:

1. A retrieval result can be attributed to the requested URL even when the browser did not open it, or when a reader returned an unrelated long page.
2. The enabled-channel configuration is not a complete capability boundary for programmatic callers.
3. A one-line change to the unmanifested install marker disables portable-runtime manifest verification.
4. The diagnostic tool can report nonfunctional or nonexistent backends as “ok”.
5. The “independent sources” count is a useful heuristic, not a defensible measurement of epistemic independence as named.
6. The configuration says same-index search channels are collapsed, but the report only warns after counting them separately.

## High findings

### BND-H1 — Channel enablement is a CLI convention, not an enforced callable boundary

Evidence:

- .cursor/skills/channel-retrieval/scripts/_http.py:349-370 checks enablement only inside run_client, after deriving a channel from sys.argv[0].
- The public search functions in arxiv.py:119-139, brave.py:19-47, crossref.py:18-42, europepmc.py:17-38, github.py:17-35, googlebooks.py:19-38, gutendex.py:23-37, hn.py:16-34, openalex.py:39-77, openlibrary.py:17-33, semanticscholar.py:26-59, stackexchange.py:29-49, web_ddg.py:41-58, web_marginalia.py:32-56, and wikipedia.py:18-32 make network calls without calling _config.require_enabled.
- doctor.py:95-103 imports these modules and calls search directly. doctor.py:248-268 filters probes, but doctor.py:277-278 intentionally exposes a command-line switch that probes disabled channels.

Impact:

A caller that imports one of those functions can make connector requests even when its channel is absent from the enabled overlay. This does not create a sandbox escape for a caller already allowed arbitrary shell/Python execution, but it contradicts the project’s repeated “capability boundary” framing and prevents the setting from being a reliable policy control inside an agent harness. It also means internal callers must all be trusted to remember the policy.

Test status:

tests/test_portable_security.py:61-73 tests only the run_client wrapper. It does not invoke a real generic search function with a disabled configuration. The custom YouTube and Reddit paths do call require_enabled and have separate coverage.

Required correction:

Enforce authorization at every network-capable public function, or route all connectors through one broker that receives an unforgeable/host-provided capability. Keep doctor’s “all” mode explicitly outside that boundary, with a distinct operator-facing warning and audit record.

### BND-H2 — Browser reads can return stale/wrong content under the requested URL

Evidence:

- _agentreach.py:217-254 uses a shared default browser session named “aletheia”.
- _agentreach.py:235 starts an open operation but discards its result. Lines 239-251 then extract whatever page is currently in that session.
- The extracted JSON is not checked for a final URL, requested URL, title, navigation completion, or an error from the open operation.
- read.py:83-91 accepts any nonempty browser text as successful “opencli-browser” content. read.py:94-100 writes a source comment naming the caller-supplied URL.

Impact:

If open fails, a prior page in the shared session can be extracted and saved as if it came from the requested URL. Concurrent reads sharing the fixed session can similarly race. That is a provenance and correctness failure; with an authenticated browser, it can also put content from one authorized navigation into the evidence artifact for another. Browser host authorization is checked correctly before this path, but it does not establish document identity.

Test status:

tests/test_portable_security.py:107-137 and tests/test_aletheia.py:299-331 cover denial before browser probing and a happy-path adapter result. There is no test for a failed open followed by successful extraction, response/final-URL matching, or concurrent shared-session reads.

Required correction:

Use a unique, run-scoped browser context; require a successful navigation result; verify the browser-reported final URL against the requested public target under a documented redirect policy; store both requested and final URL; and reject a result that cannot prove its identity.

### BND-H3 — Reader failures and wrong bodies are persisted as apparently successful evidence

Evidence:

- read.py:32 calls _STUB “bytes”, but the rest of the file uses decoded Python string character counts.
- read.py:50-56 accepts Jina text without response identity metadata. It only truncates text.
- read.py:74-76 converts every Jina exception into an empty string. read.py:89-91 then returns that as method “jina”, not an error.
- read.py:94-100 persists the empty or unverified text. read.py:123-138 returns overall success unless an exception escapes; an empty Jina failure therefore produces an artifact and a zero process exit status.
- read.py:41-43 detects only a small marker list in the first 2,000 characters. A long error shell, wrong document, soft paywall, or unrelated response can pass.

Impact:

The artifact convention conflates “the reader returned a body” with “this is the requested document.” The visible short/stub suffix is advisory only, and long false bodies are not distinguished at all. Downstream agents may count or summarize these artifacts as reads.

Test status:

tests/test_aletheia.py:299-311 intentionally accepts a short public Jina result; tests/test_portable_security.py:107-125 covers denied browser behavior. Neither tests Jina exception-to-success behavior, long unrelated content, response identity, or nonzero exit for an unreadable URL.

Required correction:

Make read success a structured object containing requested URL, resolved/final URL, retrieval method, status/error, content length, and identity evidence. Do not save or count a failed fetch as a successful read. Treat content screening as a secondary signal, not identity proof.

### BND-H4 — DuckDuckGo bypasses the shared HTTP safety and resource policy

Evidence:

- _http.py:197-279 validates public targets, disables ambient proxies, validates redirects, retries boundedly, and caps response bytes.
- web_ddg.py:41-48 directly uses urllib.request.urlopen instead of _http.get_bytes.
- That direct path inherits proxy configuration, uses urllib’s default redirect policy, has no response byte cap, and does not apply the shared public-redirect validator.

Impact:

The initial endpoint is a fixed DuckDuckGo host, so this is not the same risk as passing arbitrary user URLs to urlopen. It is still a material policy bypass: an upstream redirect, hostile proxy, or unexpectedly large response takes a route that the common boundary explicitly says it protects. It also makes this no-key fallback less predictable than every adapter using _http.

Test status:

tests/test_aletheia.py:271-293 exercises validate_public_url in isolation. No test invokes web_ddg.search under a proxy, redirect, or oversized response.

Required correction:

Route this request through the shared helper, adding bounded POST support if necessary, or implement the same no-proxy, redirect-validation, timeout, and byte-cap contract locally with tests.

### BND-H5 — Portable manifest enforcement is disabled by changing an excluded marker

Evidence:

- scripts/preflight.py:76-90 deliberately excludes .aletheia-install.json from manifest rows.
- scripts/preflight.py:163-171 decides whether a runtime is “portable” only by parsing that unverified marker and checking mode.
- scripts/preflight.py:220-232 performs symlink checks, dotenv checks, and manifest verification only when that decision is true.

Impact:

Changing the marker’s mode or making it unparsable changes a copied runtime into a purported checkout. Preflight then skips the manifest and returns “not-applicable” after only required-file and compile checks. Because the marker is excluded from the manifest, this is a simple integrity-bypass path rather than a manifest mismatch. The documentation accurately says the manifest is not a signature, but it still describes this mode as a copied-runtime corruption/tamper-evidence check; that check should not silently turn itself off.

Test status:

tests/test_portable_release.py:53-81 covers a modified manifest-listed file and an unexpected file with the marker intact. It does not mutate the marker, add a symlink after changing the marker, or assert that a portable manifest must remain enforced.

Required correction:

Bind portable-runtime detection to a protected invariant: for example, require a manifest whenever MANIFEST.sha256 is present, validate a strict marker schema independent of its manifest exclusion, and fail closed if a runtime has portable layout/marker ambiguity. If adversarial tamper resistance is a product promise, add a release signature outside the writable runtime.

### BND-H6 — Reddit thread records can claim an arbitrary URL while containing Reddit data

Evidence:

- _agentreach.py:259-265 extracts a Reddit post ID from any string containing “comments/<id>”; it does not validate the hostname.
- reddit.py:196-225 uses that ID to fetch content from PullPush or the authenticated Reddit reader.
- reddit.py:226 preserves any input beginning with “http” as the normalized record URL.
- read.py:46-47 and reddit.py:121-127 likewise recognize Reddit URLs with substring tests such as “reddit.com” rather than a parsed host equality/suffix check.

Impact:

An input such as an arbitrary HTTPS host containing /comments/<valid-id> can produce a record whose URL is that arbitrary host while the text came from a Reddit archive/API. This breaks source attribution and can contaminate a provenance graph. The browser reader has its own reddit.com authorization check, but that does not repair the output URL.

Test status:

tests/test_aletheia.py:333-357 uses a bare ID or a real Reddit URL. It does not test hostile lookalike hosts, source URL normalization, or archive response identity.

Required correction:

Parse URLs with urllib, require reddit.com or a documented subdomain, construct the canonical reddit.com permalink from the validated ID, and record requested versus canonical/archive source separately.

### BND-H7 — Installer replacement is nontransactional and its “managed” check is spoofable

Evidence:

- scripts/install.sh:89-99 treats any target containing .aletheia-install.json as managed without validating its schema, ownership, manifest, or relationship to the intended runtime.
- scripts/install.sh:128-135 moves an existing target to backup before a replacement has been built or verified.
- scripts/install.sh:203-208 builds copied skills after that removal. scripts/install.sh:237-264 does the same for the Codex runtime.
- There is no rollback/trap that restores the previous target if git archive, cp, tar, Python preflight, or mv fails.
- scripts/install.sh:171-180 documents “uncommitted runtime files” but copies only git ls-files paths. Untracked runtime files are silently omitted; deleted tracked files cause failure after backup.

Impact:

A target with a spoofed marker can be replaced without --force. More generally, a failed upgrade can leave the old runtime only in a backup and the active target absent; a multi-target install can be partially upgraded. This is a reliability/safety issue rather than a remote code-execution claim.

Test status:

tests/test_portable_release.py:112-149 covers an unmanaged directory, dry run, and permissions. tests/test_portable_release.py:84-110 tests one dirty tracked file. No test uses a spoofed marker, injects a mid-copy failure, asserts rollback, or supplies an untracked file under --allow-dirty.

Required correction:

Build and preflight a new sibling tree first, then atomically swap only after it is complete; retain the old target until the swap succeeds. Validate managed markers strictly and use a unique mktemp-style staging directory plus cleanup/rollback traps.

### BND-H8 — Doctor can execute an unchecked fallback and report unavailable backends as live

Evidence:

- _agentreach.py:57-71 provides _safe_executable, but doctor.py:126-130 bypasses it for ~/.aletheia-agentreach/bin/twitter by checking only os.path.exists. doctor.py:130 then passes that path to _agentreach._run, which executes its supplied command at _agentreach.py:116-121.
- doctor.py:158-164 marks Reddit “ok” if an authorized browser capability and a CLI path exist; it does not perform an authentication or functional query.
- doctor.py:122-125 says paid X keys have no bundled adapter when browser capability is absent, while doctor.py:136-138 reports “ok” for such a key when browser capability is present but no CLI is found.
- doctor.py:195-199 marks every key-only integration “ok” solely because an environment variable is nonempty.
- doctor.py:176-181 and 184-192 turn non-429 Semantic Scholar/Google Books failures into throttling/key messages instead of reporting the actual failure.

Impact:

The doctor output is not a trustworthy readiness signal. Its “ok” rows mix a live functional check, a configured secret, a binary presence check, and an unsupported hypothetical paid backend. The X fallback also weakens the executable-integrity policy exactly in an authenticated-browser path.

Test status:

tests/test_aletheia.py:229-268 covers HTTP 401, a bad Brave key, and enabled-channel filtering. It does not cover the X fallback path, false-green Reddit/KEYONLY rows, or outage classification.

Required correction:

Separate statuses such as live, configured-unverified, binary-present, unsupported, and down. Never label a key or executable as live without a bounded functional probe. Route every executable through _safe_executable.

### BND-H9 — The channel configuration promises same-index collapse that provenance_graph does not perform

Evidence:

- channel-retrieval/channels.json:2 says index_group “is what independence is counted over.”
- channels.json:51-55 says provenance_graph.py collapses channels sharing the same index group.
- provenance_graph.py:166-237 builds independence clusters from work IDs, canonical URLs, voice keys, derives_from, and text shingles. It never uses index_group there.
- provenance_graph.py:291-354 calculates independent_sources from those clusters. It uses _index_group_map only to populate a separate index_groups list and add discovery_monoculture at lines 327-329.

Confirmed behavior:

The no-network probe above supplies two distinct records from google_serper and serpapi, both in the configured Google index group. The report returns two independent_sources and only flags discovery_monoculture. It does not collapse the count to one, contrary to the configuration’s explicit claim.

Impact:

The result carries a warning, but consumers that read the headline independent_sources or use it for a threshold can still count fake search-index diversity as corroboration. The mismatch is especially consequential because the configuration calls itself the “single source of truth” and other skill documentation repeats the collapse claim.

Test status:

tests/test_aletheia.py:105-108 tests that a single source does not trigger discovery_monoculture. It does not test two sources from the same index group or the documented count-collapse behavior.

Required correction:

Choose one semantics and implement/document it consistently. If index group is a discovery-diversity warning only, rename the field and remove “collapsed” language. If it is part of independence, union same-group discovery records before the count or expose a distinct index-independent count beside work/voice independence.

## Medium findings

### BND-M1 — Retry layering and timeout floors make ordinary failures much slower than callers request

Evidence:

- _http.py:247-279 retries a request up to three times by default, with sleep.
- semanticscholar.py:22 and 26-42 adds an outer four-attempt loop for keyless calls and catches every exception, not only 429. Because each outer call uses _http.get_json with its default retry count, continuous failure can make up to 12 HTTP attempts, with both inner and outer backoffs.
- _agentreach.py:235-254 can issue one browser open plus up to six extraction commands; each receives the supplied timeout.
- read.py:66 and 83 raise user-provided timeouts to 90 and 60 seconds respectively. youtube.py:173 raises the Whisper download timeout to 120 seconds.
- _agentreach.py:116-121 and youtube.py:104-107,147-150 use capture_output without an output-size limit. youtube.py:116-123 has no time budget for model loading/transcription after download.

Impact:

The local Python control plane may be fast, but failure-mode wall time and subprocess/resource use are unbounded at the operation level. A nominal 10-second connector timeout is not a total budget. This directly affects perceived agent slowness and makes cost/runtime predictions unreliable.

Test status:

No test counts nested Semantic Scholar retries, bounds browser wall time, bounds captured output, or sets a total read/transcription budget.

Required correction:

Use one run/leaf deadline propagated to all retries and subprocesses; make retry policy aware of source status; cap stdout/stderr and input/output bytes; expose attempted-request and elapsed-time telemetry.

### BND-M2 — Input/output work is broadly unbounded, and raw artifact writes are not no-follow/atomic

Evidence:

- read.py:116-120 loads an entire source file into memory and read.py:124-138 has no URL-count cap or deduplication. Nonpositive max-chars returns the entire bounded HTTP body at read.py:56 and 68.
- rerank.py:81-92 loads all JSONL records in memory. provenance_graph.py:138-153 does the same for sources.
- Most search clients apply min(limit, N) but no lower bound or call-wide quota; direct callers can request invalid/huge limits. web_ddg.py:47-48 also has no response cap.
- read.py:94-100, reddit.py:222-225, and youtube.py:178-182 write predictable paths with ordinary open(..., "w"), rather than no-follow atomic writes. The containing directory is made private, which is good, but a same-user race/preexisting symlink can still redirect a predictable output path.
- stackexchange.py:22-26 limits compressed response bytes through _http but then gzip.decompresses without an output-size cap.

Impact:

The runtime gives no enforceable per-command read count, record count, output byte, disk, or CPU ceiling. The write issue is primarily a local same-UID/race concern, not a claim that an unrelated user can normally enter a 0700 directory.

Test status:

tests/test_portable_security.py:166-190 verifies normal output mode bits, not no-follow/atomic output behavior or resource caps.

Required correction:

Validate positive bounded inputs; impose a global operation budget; stream rather than materialize untrusted JSONL where possible; use secure atomic no-follow artifact writes; and bound decompression output.

### BND-M3 — The provenance score is a structural heuristic whose naming and identity rules can overstate independence

Evidence:

- provenance_graph.py:291-368 accepts the caller’s support IDs as support. It does not determine entailment, stance, or date applicability; source identity is only the supplied metadata plus the code’s URL/author/text heuristics.
- dedupe.py:151-176 gives a DOI priority over author/domain. Two different DOI works by the same author/domain therefore become different “voices”.
- provenance_graph.py:346-354 calls the resulting cluster count independent_sources. This is a work-level anti-duplication count in many cases, not a measurement of independent origin, funding, authorship, or editorial influence.
- provenance_graph.py:409-416 prefers normalized display name over a stable author ID. Same-name authors can collapse; one author with name variants but the same ID can split.
- provenance_graph.py:422-425 says labs are not merged, yet _citation_verdict at 453-461 can describe the result as “one author/lab”; no lab identity is computed.
- provenance_graph.py:240-255 maps raw DOI/reference strings without normalizing all DOI representations, so a bare DOI and doi.org URI need not connect unless some other URL key happens to bridge them.
- provenance_graph.py:215-235 performs all pairwise shingle comparisons with no source-count/input-size guard. This is quadratic before shingle-set costs.

Impact:

The code is useful for surfacing obvious echoes, but a high independent_sources number is not enough to claim genuinely independent support. The same-author/different-DOI decision may be a conscious policy choice; if so, the output label and documentation need to say “distinct work clusters,” not “independent sources.” Large source bundles can also become disproportionately slow.

Test status:

tests/test_aletheia.py:59-226 covers many normal dedupe/cycle cases, and deliberately locks in distinct DOI works. It does not test same-author different-DOI independence, stable-ID-versus-name conflicts, DOI reference notation variants, semantic support validity, or pairwise-scale limits.

Required correction:

Publish the metric’s limits in its output, separate work identity from independence/voice correlation, prefer stable IDs when present, normalize all reference identifiers, and replace or cap the all-pairs near-duplicate pass.

### BND-M4 — Error handling often degrades to empty output with insufficient causal evidence

Evidence:

- _agentreach.py:116-121 returns an empty string for every subprocess error and discards stderr/exit code.
- arxiv.py:124-139 turns non-429 HTTP, parse, and network errors into an empty result after its one listed host fails.
- semanticscholar.py:34-42 retries every exception as if it were transient throttling.
- reddit.py:159-169 aggregates backend exception class names but loses details; _rerank_filter at 135-143 silently falls back to unranked results.
- _http.py:286-295 converts any configuration exception into an empty channel map.

Impact:

“No result,” “disabled,” “rate-limited,” malformed upstream data, and local programming/configuration failures are frequently indistinguishable to the caller. That encourages unnecessary retries and prevents accurate run-cost/quality diagnosis.

Required correction:

Return typed result/status records with safe error categories and request IDs. Preserve bounded stderr/HTTP status in telemetry without emitting secrets.

### BND-M5 — The sandbox wrapper relies on trusted environment selection for its engine and online egress policy

Evidence:

- containers/run-sandbox.sh:27 uses ALETHEIA_CONTAINER_ENGINE directly; lines 49 and 121 validate only that the named executable is on PATH, then execute it.
- containers/run-sandbox.sh:60-65 accepts any nonempty ALETHEIA_EGRESS_NETWORK name when --online is set. It does not verify that the name refers to an externally restricted network; a caller can name Docker’s ordinary bridge or host network.
- containers/run-sandbox.sh:56-59 creates a new work directory under umask 077, but leaves an existing work directory’s owner/mode unchanged before mounting it writable at line 119.
- containers/run-sandbox.sh:100-121 does impose useful container-side controls: read-only root, capability drop, no-new-privileges, pids/memory/CPU limits, no-network default, and tmpfs.

Impact:

This is not a claim that the wrapper can determine Docker network policy by itself. It is a trust-boundary clarification: the wrapper only provides its advertised least-privilege properties when the caller’s environment and preexisting mount paths are trusted. An untrusted agent environment can point ENGINE at another host executable or choose an unrestricted online network.

Test status:

tests/test_portable_release.py:150-160 intentionally substitutes the harmless true executable as the container engine to test new-work-directory permissions. It does not test engine allowlisting, existing work-directory modes, or egress-network policy.

Required correction:

Treat engine path and online network as harness-owned configuration, not agent-controlled environment. Allowlist/vet engines, resolve an approved network policy outside the process, and reject or warn on an existing non-private work/config directory.

### BND-M6 — The reference image is not pinned to an immutable base digest in source

Evidence:

- containers/Dockerfile:2-5 says a release pipeline should pin PYTHON_IMAGE to a digest, but the default is the mutable tag python:3.11.14-slim-bookworm.
- containers/run-sandbox.sh:92-94 builds with --pull, which intentionally refreshes that tag.
- The runtime manifest generated at Dockerfile:25-28 covers copied Aletheia files, not the base image/OS layer.

Impact:

Identical Git commits can build materially different images as the upstream tag changes. This is a reproducibility and supply-chain hardening concern, not evidence that a base image is currently compromised.

Required correction:

Pin the default base by digest (with a documented multi-architecture release process) and record the source commit plus base digest in image labels/build provenance.

## Lower-severity contract and documentation mismatches

- arxiv.py:4-8 says the client has “a mirror host,” but _HOSTS at line 28 contains only export.arxiv.org. The loop therefore provides no real host failover.
- read.py:32 calls a character threshold “bytes.”
- gutendex.py:3-4 says every record URL is a readable text/html format, but _best_format at 17-20 can choose application/epub+zip.
- doctor.py:4-8 says key-gated channels are reported configured/not-configured, while p_keyonly at 195-199 emits status “ok”.
- scripts/install.sh:30 says --allow-dirty copies uncommitted runtime files, but 174-180 intentionally excludes untracked files.
- _config.py:25-36 changes the process-wide umask during import. That is an understandable privacy default, but it affects every later file created by the hosting interpreter, not just Aletheia artifacts; the comment’s scope should be explicit.
- channels.json:6 calls the default core “SAFE NO-KEY FIRST” while the core includes Brave (channels.json:3, auth free_key at line 29) and OpenAlex (auth free_key_since_2026 at line 13). The clients degrade when keys are absent, but the wording obscures that normal core fan-out includes unavailable key upgrades.
- channels.json:25, 26, and 46 do not match current runtime behavior cleanly: Reddit defaults to no-key archives, X has no bundled paid adapter and uses an opt-in browser CLI, and YouTube has a no-key captions path plus optional local transcription.

## Per-file disposition

“Reviewed” means every numbered line is covered by the companion manifest. “No separate finding” means no additional material issue beyond shared findings, not that the file has been formally proved correct.

| File | Disposition |
| --- | --- |
| channel-retrieval/scripts/_agentreach.py | BND-H2, BND-H8, BND-M1, BND-M4 |
| channel-retrieval/scripts/_config.py | shared capability model; import-wide umask contract note |
| channel-retrieval/scripts/_http.py | BND-H1, BND-M1, BND-M4; its own public-URL protections are otherwise a strong baseline |
| channel-retrieval/scripts/arxiv.py | BND-H1, BND-M4, mirror documentation mismatch |
| channel-retrieval/scripts/brave.py | BND-H1; retry can add an unmetered second request on 422 |
| channel-retrieval/scripts/channels.py | no separate material finding; delegates secure overlay writing to _config |
| channel-retrieval/scripts/crossref.py | BND-H1 |
| channel-retrieval/scripts/doctor.py | BND-H1, BND-H8, BND-M1 |
| channel-retrieval/scripts/europepmc.py | BND-H1 |
| channel-retrieval/scripts/github.py | BND-H1 |
| channel-retrieval/scripts/googlebooks.py | BND-H1, BND-H8 status classification |
| channel-retrieval/scripts/gutendex.py | BND-H1 and format documentation mismatch |
| channel-retrieval/scripts/hn.py | BND-H1 |
| channel-retrieval/scripts/openalex.py | BND-H1 |
| channel-retrieval/scripts/openlibrary.py | BND-H1 |
| channel-retrieval/scripts/read.py | BND-H2, BND-H3, BND-M1, BND-M2 |
| channel-retrieval/scripts/reddit.py | BND-H6, BND-M1, BND-M2, BND-M4 |
| channel-retrieval/scripts/rerank.py | BND-M2; lexical ranking is accurately documented as nonsemantic |
| channel-retrieval/scripts/semanticscholar.py | BND-H1, BND-M1, BND-M4 |
| channel-retrieval/scripts/stackexchange.py | BND-H1, BND-M2 |
| channel-retrieval/scripts/web_ddg.py | BND-H1, BND-H4, BND-M2 |
| channel-retrieval/scripts/web_marginalia.py | BND-H1 |
| channel-retrieval/scripts/wikipedia.py | BND-H1 |
| channel-retrieval/scripts/x.py | uses explicit enable/browser checks; inherits _agentreach execution and timeout concerns |
| channel-retrieval/scripts/youtube.py | BND-M1, BND-M2; explicit channel gate is present |
| provenance-audit/scripts/dedupe.py | BND-M3 |
| provenance-audit/scripts/provenance_graph.py | BND-H9, BND-M2, BND-M3 |
| scripts/install.sh | BND-H7 and --allow-dirty documentation mismatch |
| scripts/install_claude.sh | delegates to install.sh; no separate material finding |
| scripts/preflight.py | BND-H5; compile-only preflight is deliberately non-executing but not a semantic smoke test |
| containers/run-sandbox.sh | BND-M5; useful default offline container restrictions are present |
| containers/Dockerfile | BND-M6; closure copying and runtime read-only permissions are otherwise deliberate |
| channel-retrieval/channels.json | BND-H9 plus channel/auth contract mismatches |
| aletheia-research/agents/openai.yaml | reviewed; no separate material finding beyond routing users toward the high-scrutiny workflow |

## Test-gap map

The suite is strong on regression examples and normal installation behavior. The most important untested cases for this boundary are:

1. Disabled generic search called programmatically, including doctor’s direct import path.
2. Browser open failure, stale/shared-session extraction, final-URL verification, and concurrent browser reads.
3. Jina exception/long error page behavior and propagation of a failed read to exit status/run telemetry.
4. Proxy/redirect/large-body behavior of web_ddg.
5. Marker tampering or ambiguity in portable preflight.
6. Failed installation after backup, restoration, marker spoofing, and untracked dirty files.
7. Doctor false-green rows and the unsafe X fallback executable.
8. Nested retry counts, total deadlines, output size limits, Whisper runtime, and resource ceilings.
9. Same-author/different-DOI and stable-author-ID provenance cases, DOI reference normalization, and large N near-duplicate behavior.
10. Same-index-group sources being counted as one if that is the intended configuration contract.
11. Sandbox engine/network environment trust, existing mount permissions, and immutable base-image provenance.

## Recommended remediation order

1. Repair read identity before relying on provenance scores: distinguish failure from success, record final identity, and isolate browser state.
2. Decide whether channel configuration is a usability filter or a real capability control. If it is a control, enforce it at every callable connector boundary.
3. Make copied-runtime verification fail closed even if the marker is altered; make installs build-then-swap with rollback.
4. Replace doctor’s overloaded “ok” with evidence-backed status categories and safe executable validation.
5. Add end-to-end run/leaf quotas for time, requests, reads, bytes, subprocess output, and local transcription.
6. Make the configuration’s index-group semantics match the provenance count, then rename/refine the provenance metric so it cannot be mistaken for independent empirical support.
7. Treat the sandbox wrapper’s engine and egress network as harness-owned policy; pin the container base by digest.
