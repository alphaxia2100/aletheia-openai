#!/usr/bin/env python3
"""Aletheia Research — output assembler (the VERBOSITY dial).

Two audiences need very different outputs (0.4.0):
  - `bundle` (verbosity=agent): the FULL research pack — every node's findings.md and evidence.md
    verbatim, the source index, and with --reads the actual primaries read in full (notes/*.md). A
    calling AGENT wants everything, not a summary; nuance lives in the raw files. This is what the
    skill hands back when another session invoked it.
  - the user-facing MULTI-PAGE summary is authored by the orchestrator (brief.md); `outline` here just
    prints the tree + where every artifact is, so that synthesis is grounded and complete.

Usage:
  report.py bundle  --run RUN_DIR [--reads] [--max-chars N] [--output FILE]
  report.py outline --run RUN_DIR
  report.py score   --run RUN_DIR [--output FILE]
  report.py audit-claims --run RUN_DIR --auditor "fresh-context verifier" [--added-claims N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
# sibling skills resolve via realpath (works through ~/.cursor, ~/.claude, or ~/.codex symlinks),
# so `score` is self-contained WITH the skill — no dependency on the repo's scripts/eval or deep-aletheia.
_PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
for _p in (HERE, _PROV):
    sys.path.insert(0, _p)
import treestate  # noqa: E402
import ledger  # noqa: E402
try:
    import provenance_graph as _pg  # noqa: E402  (structural independence)
    import dedupe as _dedupe  # noqa: E402
except Exception:  # noqa: BLE001 — score still runs (independence degrades to identity voices)
    _pg = _dedupe = None
from collections import Counter  # noqa: E402


def _read(p: str, default: str = "") -> str:
    # errors="replace": the bundle must robustly hand back EVERY artifact — a single stray non-UTF-8
    # byte (corrupt/hand-edited/cross-system file) must not abort the whole pack into an empty result.
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return default


def _nodes_depth_first(run: str) -> List[str]:
    out = []
    for d, _s, fs in os.walk(os.path.join(run, "tree")):
        if "status.json" in fs:
            out.append(d)
    out.sort(key=lambda p: (int((treestate._read_json(os.path.join(p, "status.json"), {}) or {}).get("depth", 0)), p))
    return out


def _cfg(run: str) -> Dict[str, Any]:
    return treestate._read_json(os.path.join(run, "run.json"), {}) or {}


def _jsonl_dicts(path: str) -> List[Dict[str, Any]]:
    rows = []
    for line in _read(path).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _file_sha256(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def _strict_jsonl_dicts(path: str, label: str) -> List[Dict[str, Any]]:
    """Read gate-critical JSONL without the bundle reader's corruption-tolerant skipping."""
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = list(fh)
    except OSError as exc:
        raise ValueError("%s is missing or unreadable" % label) from exc
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError("%s line %d is invalid JSON" % (label, lineno)) from exc
        if not isinstance(row, dict):
            raise ValueError("%s line %d must be a JSON object" % (label, lineno))
        rows.append(row)
    return rows


def _claim_urls(row: Dict[str, Any]) -> List[str]:
    raw = row.get("urls")
    if not isinstance(raw, list):
        raw = [row.get("url")]
    return [str(url).strip() for url in raw if str(url or "").strip()]


def _claim_verdict_sets_match(claims: List[Dict[str, Any]],
                              verdicts: List[Dict[str, Any]]) -> bool:
    """Match each claim to one verdict; a multi-source claim may resolve to any declared URL."""
    remaining = list(verdicts)
    for claim in claims:
        text = str(claim.get("claim") or "").strip()
        allowed = set(_claim_urls(claim))
        if not text or not allowed:
            return False
        found = next((i for i, verdict in enumerate(remaining)
                      if str(verdict.get("claim") or "").strip() == text
                      and str(verdict.get("url") or "").strip() in allowed), None)
        if found is None:
            return False
        remaining.pop(found)
    return not remaining


def _claim_scope_required(run: str) -> bool:
    """New 0.5 runs require the gate; preserve read-only scoring compatibility for older runs."""
    version = str(_cfg(run).get("version") or "")
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)(?:\.|\b)", version)
    return True if match is None else (int(match.group(1)), int(match.group(2))) >= (0, 5)


def _claim_scope_state(run: str) -> Dict[str, Any]:
    """Validate the claim-coverage attestation against the exact final artifacts."""
    audit = treestate._read_json(os.path.join(run, "claim_audit.json"), {}) or {}
    required = _claim_scope_required(run)
    if not required and not audit:
        return {"required": False, "valid": True, "auditor": None, "claim_count": None,
                "added_claims": 0, "reasons": []}
    reasons = []
    if audit.get("status") != "complete":
        reasons.append("missing_complete_attestation")
    if not str(audit.get("auditor") or "").strip():
        reasons.append("missing_auditor")
    brief_hash = _file_sha256(os.path.join(run, "brief.md"))
    claims_hash = _file_sha256(os.path.join(run, "claims.jsonl"))
    verify_hash = _file_sha256(os.path.join(run, "verify.jsonl"))
    if not brief_hash:
        reasons.append("missing_brief")
    elif audit.get("brief_sha256") != brief_hash:
        reasons.append("brief_changed_after_audit")
    if not claims_hash:
        reasons.append("missing_claims")
    elif audit.get("claims_sha256") != claims_hash:
        reasons.append("claims_changed_after_audit")
    if not verify_hash:
        reasons.append("missing_verify")
    elif audit.get("verify_sha256") != verify_hash:
        reasons.append("verify_changed_after_audit")
    try:
        claims = _strict_jsonl_dicts(os.path.join(run, "claims.jsonl"), "claims.jsonl")
        _strict_jsonl_dicts(os.path.join(run, "verify.jsonl"), "verify.jsonl")
    except ValueError:
        claims = []
        reasons.append("invalid_claim_or_verify_jsonl")
    if int(audit.get("claim_count", -1) or -1) != len(claims):
        reasons.append("claim_count_mismatch")
    return {
        "required": required,
        "valid": not reasons,
        "auditor": audit.get("auditor"),
        "claim_count": len(claims),
        "added_claims": int(audit.get("added_claims", 0) or 0),
        "reasons": reasons,
    }


def audit_claim_scope(run: str, auditor: str, added_claims: int = 0,
                      notes: str = "") -> Dict[str, Any]:
    """Attest that a verifier compared the final brief with the complete claim set.

    Code enforces artifact identity and completed row verification. The auditor supplies the semantic
    judgment that every load-bearing factual assertion was extracted; hashes make any later edit
    invalidate the attestation.
    """
    auditor = str(auditor or "").strip()
    if not auditor:
        raise ValueError("auditor must identify the fresh-context verification pass")
    if added_claims < 0:
        raise ValueError("added_claims must be non-negative")
    brief_path = os.path.join(run, "brief.md")
    claims_path = os.path.join(run, "claims.jsonl")
    claims = _strict_jsonl_dicts(claims_path, "claims.jsonl")
    verdicts = _strict_jsonl_dicts(os.path.join(run, "verify.jsonl"), "verify.jsonl")
    if not _file_sha256(brief_path):
        raise ValueError("write the final brief before attesting claim coverage")
    if not claims:
        raise ValueError("claims.jsonl is empty")
    final = {"supported", "contradicted", "unsupported", "off_topic"}
    if len(verdicts) != len(claims) or any(v.get("verdict") not in final for v in verdicts):
        raise ValueError("every extracted claim must have a final readable verdict before attestation")
    if not _claim_verdict_sets_match(claims, verdicts):
        raise ValueError("claims.jsonl and verify.jsonl do not describe the same claim/source set")
    payload = {
        "status": "complete",
        "auditor": auditor,
        "attestation": ("Auditor read the final brief, added every omitted load-bearing empirical or "
                        "inferential claim, "
                        "and checked the final claim/url set against verify.jsonl."),
        "claim_count": len(claims),
        "added_claims": added_claims,
        "brief_sha256": _file_sha256(brief_path),
        "claims_sha256": _file_sha256(claims_path),
        "verify_sha256": _file_sha256(os.path.join(run, "verify.jsonl")),
        "notes": notes,
        "created": treestate._now(),
    }
    treestate._write_json(os.path.join(run, "claim_audit.json"), payload)
    treestate.log_run_event(run, "claim_scope_audit_completed", actor=auditor,
                            component="report",
                            data={"claim_count": len(claims), "added_claims": added_claims,
                                  "artifact": "claim_audit.json",
                                  "sha256": _file_sha256(os.path.join(run, "claim_audit.json"))})
    return payload


def _strict_accuracy_run(run: str) -> bool:
    cfg = _cfg(run)
    return (str(cfg.get("version") or "").startswith("aletheia-research-accuracy ")
            and cfg.get("thoroughness") in {"accuracy", "unlimited", "max"})


def _canon_url(url: str) -> str:
    if _dedupe is not None:
        try:
            return str(_dedupe.canonical_url(url or ""))
        except Exception:  # noqa: BLE001
            pass
    return str(url or "").split("#", 1)[0].rstrip("/").lower()


def _claim_reconciliation(run: str) -> Dict[str, Any]:
    """Prove that final-answer claims did not bypass the atomic claim/evidence ledger."""
    required = _strict_accuracy_run(run)
    if not required:
        return {"required": False, "valid": True, "final_claims": 0, "mapped_claims": 0,
                "issues": [], "unrepresented_load_bearing_claim_ids": []}
    try:
        final_rows = _strict_jsonl_dicts(os.path.join(run, "claims.jsonl"), "claims.jsonl")
        state = ledger.materialize(run)
        led_audit = ledger.audit(run)
    except (ValueError, OSError) as exc:
        return {"required": True, "valid": False, "final_claims": 0, "mapped_claims": 0,
                "issues": [str(exc)], "unrepresented_load_bearing_claim_ids": []}
    claims = state.get("claims") or {}
    evidence = state.get("evidence") or {}
    verdicts = state.get("verdicts") or {}
    supported_urls: Dict[str, set] = {}
    for eid, ev in evidence.items():
        verdict = verdicts.get(eid) or {}
        if (ev.get("relation_to_claim") == "supports" and ev.get("artifact_valid") is True
                and verdict.get("result") == "verified"):
            supported_urls.setdefault(str(ev.get("claim_id")), set()).add(
                _canon_url(str(ev.get("source_url") or "")))
    issues, represented = [], set()
    for index, row in enumerate(final_rows, 1):
        claim_id = str(row.get("claim_id") or "").strip()
        if not claim_id:
            issues.append("final claim %d has no claim_id" % index)
            continue
        if claim_id not in claims:
            issues.append("final claim %d references unknown ledger claim %s" % (index, claim_id))
            continue
        represented.add(claim_id)
        final_text = " ".join(str(row.get("claim") or "").split())
        ledger_text = " ".join(str(claims[claim_id].get("canonical_text") or "").split())
        if final_text != ledger_text:
            issues.append("final claim %d text differs from ledger claim %s" % (index, claim_id))
        urls = {_canon_url(url) for url in _claim_urls(row)}
        allowed_urls = set(supported_urls.get(claim_id, set()))
        if (claims[claim_id].get("claim_kind") or "empirical") != "empirical":
            for premise in claims[claim_id].get("depends_on_claim_ids") or []:
                allowed_urls.update(supported_urls.get(premise, set()))
        if not urls:
            issues.append("final claim %d has no source URL" % index)
        elif not urls.issubset(allowed_urls):
            issues.append("final claim %d cites URL not verified for ledger claim %s" %
                          (index, claim_id))
    required_ids = {cid for cid, claim in claims.items()
                    if claim.get("importance") == "load_bearing"}
    unrepresented = sorted(required_ids - represented)
    if unrepresented:
        issues.append("load-bearing ledger claims absent from final claim set: %s" %
                      ", ".join(unrepresented))
    if led_audit.get("epistemically_complete") is not True:
        issues.append("claim ledger is not epistemically complete")
    return {"required": True, "valid": bool(final_rows) and not issues,
            "final_claims": len(final_rows), "mapped_claims": len(represented),
            "ledger_claims": len(claims), "issues": issues,
            "unrepresented_load_bearing_claim_ids": unrepresented}


def _runtime_telemetry(run: str) -> Dict[str, Any]:
    """Aggregate selection-path activation and cost counters emitted by investigate.py."""
    events = []
    read_artifacts = set()
    engine_artifacts = set()
    for node in _nodes_depth_first(run):
        notes = os.path.join(node, "notes")
        for _rel, path in _note_files(notes):
            read_artifacts.add(os.path.realpath(path))
        for source in _jsonl_dicts(os.path.join(node, "sources.jsonl")):
            rel = str(source.get("_read_file") or "").strip()
            if rel:
                path = os.path.realpath(os.path.join(node, rel))
                if os.path.isfile(path):
                    engine_artifacts.add(path)
        for event in _jsonl_dicts(os.path.join(node, "telemetry.jsonl")):
            tagged = dict(event)
            tagged["_node"] = node       # disambiguate equal round numbers across different leaves
            events.append(tagged)
    rounds = [e for e in events if e.get("event") == "investigation_round"]
    gathers = [e for e in events if e.get("event") == "candidate_gather"]
    # Agent rounds repeat the final gather's retrieval counts, so use gather events for agent search
    # cost and completed-round events only for deterministic search. Match per node+round so a run
    # resumed across an upgrade still counts its older agent rounds that lack candidate_gather events.
    deterministic_search = [e for e in rounds if e.get("selection_mode") != "agent"]
    gather_rounds = {(e.get("_node"), e.get("round")) for e in gathers}
    legacy_agent_search = [e for e in rounds if e.get("selection_mode") == "agent"
                           and (e.get("_node"), e.get("round")) not in gather_rounds]
    searches = gathers + deterministic_search + legacy_agent_search
    modes = Counter(str(e.get("selection_mode") or "unknown") for e in rounds)

    def total(field: str, rows=rounds) -> int:
        return sum(int(e.get(field, 0) or 0) for e in rows)

    return {
        "rounds": len(rounds),
        "rounds_by_selection_mode": dict(sorted(modes.items())),
        "retrieval_passes": len(searches),
        "candidate_gathers": len(gathers),
        "retrieved": total("retrieved", searches),
        "unique": total("unique", searches),
        "eligible": total("eligible", searches),
        "completed_round_retrieved": total("retrieved"),
        "selected": total("selected"),
        "read_attempts": total("read_attempts"),
        "reads_ok": total("reads_ok"),
        "read_failures": total("read_failures"),
        "zero_selection_rounds": sum(1 for e in rounds if int(e.get("selected", 0) or 0) == 0),
        "zero_success_rounds": sum(1 for e in rounds if int(e.get("reads_ok", 0) or 0) == 0),
        "floor_engagements": sum(1 for e in rounds if e.get("floor_engaged") is True),
        "abstained_rounds": sum(1 for e in rounds if e.get("abstained") is True),
        "triage_requeries": sum(1 for e in events if e.get("event") == "triage_requery"),
        "read_seconds": round(sum(float(e.get("read_seconds", 0) or 0) for e in rounds), 1),
        # Workers may chase a linked primary or make an uncapped reread outside investigate.py. Those
        # files are valid evidence, but they are additional cost and must not disappear from an A/B.
        "read_artifacts": len(read_artifacts),
        "engine_read_artifacts": len(read_artifacts & engine_artifacts),
        "direct_or_manual_read_artifacts": len(read_artifacts - engine_artifacts),
    }


def _observability(run: str, runtime: Dict[str, Any]) -> Dict[str, Any]:
    """Audit whether cost, selection, and lifecycle claims can be replayed from durable evidence."""
    cfg = _cfg(run)
    required = _strict_accuracy_run(run)
    run_log = treestate.audit_run_events(run)
    try:
        events = treestate._read_run_events(run)
    except ValueError:
        events = []
    completed = [row for row in events if row.get("event") == "source_read_completed"]
    failed = [row for row in events if row.get("event") == "source_read_failed"]
    logged_artifacts = {str((row.get("data") or {}).get("artifact") or "")
                        for row in completed if (row.get("data") or {}).get("artifact")}
    actual_artifacts = set()
    for node in _nodes_depth_first(run):
        for _rel, path in _note_files(os.path.join(node, "notes")):
            actual_artifacts.add(os.path.relpath(path, run))
    runtime_ledger = treestate._read_json(os.path.join(run, "runtime-ledger.json"), {}) or {}
    reserved = int(runtime_ledger.get("read_attempts_reserved", 0) or 0)
    logged_attempts = len(completed) + len(failed)
    untracked = sorted(actual_artifacts - logged_artifacts)
    missing_artifacts = sorted(logged_artifacts - actual_artifacts)
    request_path = os.path.join(run, "request.md")
    request_hash = _file_sha256(request_path)
    request_valid = bool(request_hash and request_hash == cfg.get("request_sha256"))
    health_path = os.path.join(run, "channel-health.json")
    health_events = [row for row in events if row.get("event") == "channel_health_captured"]
    health_hash = _file_sha256(health_path)
    health_valid = bool(health_hash and any(
        str((row.get("data") or {}).get("sha256") or "") == health_hash for row in health_events))
    manifest_events = [row for row in events if row.get("event") == "candidate_manifest_persisted"]
    invalid_manifests = []
    for row in manifest_events:
        data = row.get("data") or {}
        rel = str(data.get("artifact") or "")
        expected = str(data.get("sha256") or "")
        if not rel or not expected or _file_sha256(os.path.join(run, rel)) != expected:
            invalid_manifests.append(rel or "<missing path>")
    manifest_integrity_valid = not invalid_manifests
    dispatched = [row for row in events if row.get("event") == "agent_dispatched"]
    completed_agents = [row for row in events if row.get("event") == "agent_completed"]
    writers = [row for row in events if row.get("event") == "writer_registered"]
    dispatch_ids = {str((row.get("data") or {}).get("worker_id") or "") for row in dispatched}
    complete_ids = {str((row.get("data") or {}).get("worker_id") or "") for row in completed_agents}
    dispatch_ids.discard(""); complete_ids.discard("")
    agent_required = len(_nodes_depth_first(run)) > 1
    missing_model = [str((row.get("data") or {}).get("worker_id") or "?") for row in dispatched
                     if not str((row.get("data") or {}).get("model") or "").strip()]
    writer_valid = any(str((row.get("data") or {}).get("worker_id") or "").strip()
                       and str((row.get("data") or {}).get("model") or "").strip()
                       and str((row.get("data") or {}).get("context_id") or "").strip()
                       for row in writers)
    agent_lifecycle_valid = (not agent_required or
                             (bool(dispatch_ids) and dispatch_ids <= complete_ids
                              and not missing_model and len(dispatch_ids) == len(dispatched)
                              and writer_valid))
    started = float(cfg.get("started_epoch") or 0)
    if cfg.get("finished_epoch"):
        end = float(cfg.get("finished_epoch"))
    elif cfg.get("state") in {"complete", "delivered_with_gaps", "terminated", "failed"}:
        try:
            end = os.path.getmtime(os.path.join(run, "run.json"))
        except OSError:
            end = started
    else:
        end = time.time()
    elapsed = round(max(0.0, end - started), 3) if started else 0.0
    max_seconds = float((cfg.get("limits") or {}).get("max_seconds") or 0)
    read_accounting_valid = (reserved == logged_attempts and not untracked
                             and not missing_artifacts)
    log_valid = (run_log.get("chain_valid") is True
                 and not run_log.get("missing_required_events"))
    valid = (not required or (log_valid and read_accounting_valid and request_valid
                              and health_valid and agent_lifecycle_valid and manifest_integrity_valid
                              and (not max_seconds or elapsed <= max_seconds)))
    return {"required": required, "valid": valid, "run_log": run_log,
            "request_preserved": request_valid, "channel_health_preserved": health_valid,
            "manifest_integrity": {"valid": manifest_integrity_valid,
                                   "manifests": len(manifest_events),
                                   "invalid_artifacts": invalid_manifests[:25]},
            "agent_lifecycle": {"required": agent_required, "valid": agent_lifecycle_valid,
                                "dispatched": len(dispatched), "completed": len(completed_agents),
                                "writer_registered": writer_valid,
                                "missing_completion_worker_ids": sorted(dispatch_ids - complete_ids),
                                "missing_model_worker_ids": missing_model},
            "elapsed_seconds": elapsed, "max_seconds": max_seconds,
            "read_accounting": {"valid": read_accounting_valid,
                                "reserved_attempts": reserved,
                                "logged_attempts": logged_attempts,
                                "logged_successes": len(completed),
                                "logged_failures": len(failed),
                                "read_artifacts": len(actual_artifacts),
                                "untracked_artifact_count": len(untracked),
                                "untracked_artifacts": untracked[:25],
                                "missing_logged_artifact_count": len(missing_artifacts),
                                "missing_logged_artifacts": missing_artifacts[:25],
                                "engine_read_artifacts": runtime.get("engine_read_artifacts", 0),
                                "direct_or_manual_read_artifacts":
                                    runtime.get("direct_or_manual_read_artifacts", 0)}}


def _note_files(notes_dir: str):
    """Yield nested read artifacts deterministically (workers may store full/decisive rereads)."""
    if not os.path.isdir(notes_dir):
        return []
    out = []
    for directory, _subdirs, files in os.walk(notes_dir):
        for filename in files:
            if filename.endswith(".md"):
                path = os.path.join(directory, filename)
                out.append((os.path.relpath(path, notes_dir), path))
    return sorted(out)


def bundle(run: str, reads: bool = False, max_chars: int = 0) -> str:
    """The FULL pack for an agent caller — every artifact, verbatim. `reads` also inlines the primaries
    read in full (notes/*.md). `max_chars` optionally truncates each read (0 = no truncation)."""
    cfg = _cfg(run)
    L: List[str] = []
    L.append("# Aletheia Research — FULL BUNDLE (agent verbosity)")
    L.append("")
    L.append("**Topic:** %s" % cfg.get("topic", ""))
    L.append("**Thoroughness:** %s · **Verbosity:** %s · **Version:** %s"
             % (cfg.get("thoroughness"), cfg.get("verbosity"), cfg.get("version")))
    impl = cfg.get("implementation") or {}
    if impl:
        L.append("**Implementation:** commit=%s · dirty=%s · runtime_sha256=%s"
                 % (impl.get("git_commit"), impl.get("git_dirty"), impl.get("runtime_sha256")))
    L.append("")
    L.append("This is the COMPLETE research artifact set — not a summary. Every node's findings and "
             "evidence are included verbatim so no nuance is lost. Read it in full; cite the primaries.")
    L.append("")
    L.append("## Portfolio (competing framings)")
    L.append(_read(os.path.join(run, "portfolio.md"), "_(none)_"))
    L.append("")
    L.append(treestate.tree_view(run))
    L.append("")
    for artifact in ("claims.jsonl", "verify.jsonl", "claim_audit.json", "score.json"):
        content = _read(os.path.join(run, artifact))
        if content.strip():
            L.append("## %s" % artifact)
            L.append(content)
            L.append("")
    for node in _nodes_depth_first(run):
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        rel = os.path.relpath(node, run)
        L.append("\n" + "=" * 90)
        L.append("## NODE `%s` — %s" % (st.get("qid", rel), st.get("question", "")))
        L.append("state=%s depth=%s budget=%s rounds=%s n_read=%s"
                 % (st.get("state"), st.get("depth"), st.get("budget"),
                    st.get("rounds"), st.get("n_read")))
        L.append("")
        findings = _read(os.path.join(node, "findings.md"))
        if findings.strip():
            L.append("### findings.md")
            L.append(findings)
        evidence = _read(os.path.join(node, "evidence.md"))
        if evidence.strip():
            L.append("### evidence.md")
            L.append(evidence)
        telemetry = _read(os.path.join(node, "telemetry.jsonl"))
        if telemetry.strip():
            L.append("### telemetry.jsonl")
            L.append(telemetry)
        srcs = [l for l in _read(os.path.join(node, "sources.jsonl")).splitlines() if l.strip()]
        if srcs:
            L.append("### sources.jsonl (%d)" % len(srcs))
            for s in srcs:
                try:
                    r = json.loads(s)
                    if not isinstance(r, dict):        # a valid-JSON non-object line -> skip, don't crash
                        continue
                    L.append("- [%s] %s — %s" % (r.get("_class") or r.get("channel_class") or "?",
                                                 (r.get("title") or "")[:110], r.get("url", "")))
                except ValueError:
                    pass
        if reads:
            notes_dir = os.path.join(node, "notes")
            for rel, path in _note_files(notes_dir):
                body = _read(path)
                if max_chars and len(body) > max_chars:
                    body = body[:max_chars] + "\n…[truncated]"
                L.append("#### read primary — notes/%s" % rel)
                L.append(body)
    brief = _read(os.path.join(run, "brief.md"))
    if brief.strip():
        L.append("\n" + "=" * 90)
        L.append("## brief.md (the synthesized answer)")
        L.append(brief)
    return "\n".join(L) + "\n"


def outline(run: str) -> str:
    """Tree + artifact inventory, so the orchestrator's multi-page summary is grounded and complete."""
    cfg = _cfg(run)
    L = ["# Run outline — %s (%s)" % (cfg.get("topic", ""), cfg.get("thoroughness")), ""]
    L.append(treestate.tree_view(run))
    L.append("")
    L.append("## Artifacts per node")
    for node in _nodes_depth_first(run):
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        rel = os.path.relpath(node, run)
        arts = [a for a in ("findings.md", "evidence.md", "sources.jsonl")
                if os.path.exists(os.path.join(node, a))]
        notes_dir = os.path.join(node, "notes")
        n_notes = len(_note_files(notes_dir))
        L.append("- `%s` [%s] — %s | %d read primaries" % (rel, st.get("qid", ""), ", ".join(arts), n_notes))
    return "\n".join(L) + "\n"


def _independent_origins(records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
    if _pg is not None:
        try:
            uf, by = _pg.build_clusters([dict(r) for r in records])
            return len({uf.find(s) for s in by})
        except Exception:  # noqa: BLE001
            pass
    if _dedupe is not None:
        return len({_dedupe.voice_key(r) for r in records})
    return len(records)


def _claim_source_records(verdicts: List[Dict[str, Any]], index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return unique finally judged citation records, enriched from the retrieval index.

    Independence over every search hit rewards irrelevant breadth. The epistemic question is whether
    the sources actually carrying final claims are independent. Keep contradicted/unsupported
    citations in the audit (they were still used), but exclude unreadable/off-topic and unfinished
    rows. Cross-domain copies retain their separate records so structural clustering can collapse them.
    """
    final = {"supported", "contradicted", "unsupported"}
    by_key: Dict[str, Dict[str, Any]] = {}

    def keys(row: Dict[str, Any]) -> List[str]:
        url = str(row.get("url") or "")
        canon = _dedupe.canonical_url(url) if _dedupe is not None else url.rstrip("/").lower()
        out = ["url:" + canon] if canon else []
        if _pg is not None:
            try:
                out += ["%s:%s" % item for item in _pg._work_identity(row).items()]
            except Exception:  # noqa: BLE001 - URL identity remains available
                pass
        return out

    for row in index:
        if not isinstance(row, dict):
            continue
        for key in keys(row):
            by_key.setdefault(key, row)
    out, seen = [], set()
    for verdict in verdicts:
        if verdict.get("verdict") not in final:
            continue
        url = str(verdict.get("url") or "")
        if not url:
            continue
        probe = {"url": url}
        probe_keys = keys(probe)
        if not probe_keys or any(key in seen for key in probe_keys):
            continue
        matched = next((by_key[key] for key in probe_keys if key in by_key), None)
        source = dict(matched or probe)
        source.setdefault("url", url)
        source_keys = set(probe_keys + keys(source))
        if source_keys & seen:
            continue
        seen.update(source_keys)
        out.append(source)
    return out


def score(run: str) -> Dict[str, Any]:
    """Self-contained scorer (ships WITH the skill — no repo/eval or deep-aletheia dependency). The
    headline `citation_accuracy` is precision, reported ONLY when the verification pass is complete
    (every on-topic claim has a final verdict); off_topic counts in the denominator so a dropped
    citation can't vanish; an independent, content-hashed scope audit prevents the writer from omitting
    inconvenient claims from the denominator; independence uses shared-origin clustering."""
    ver = _jsonl_dicts(os.path.join(run, "verify.jsonl"))
    vc = Counter(r.get("verdict") for r in ver)
    supported, contradicted, unsupported = vc["supported"], vc["contradicted"], vc["unsupported"]
    awaiting = vc["relevant"] + vc["borderline"]
    off_topic, broken = vc["off_topic"], vc["broken"]
    judged = supported + contradicted + unsupported + off_topic
    precision = round(supported / judged, 3) if judged else None
    blocking = awaiting + broken
    coverage = round(judged / (judged + blocking), 3) if (judged + blocking) else None
    row_complete = bool(judged and blocking == 0)
    claim_scope = _claim_scope_state(run)
    complete = row_complete and claim_scope["valid"]
    runtime = _runtime_telemetry(run)
    observability = _observability(run, runtime)
    reconciliation = _claim_reconciliation(run)
    try:
        ledger_audit = ledger.audit(run)
    except (ValueError, OSError) as exc:
        ledger_audit = {"epistemically_complete": False, "ready_for_synthesis": False,
                        "errors": [str(exc)]}
    strict = _strict_accuracy_run(run)
    completion_blockers = []
    if not complete:
        completion_blockers.append("final citation/claim-scope verification is incomplete")
    if strict and ledger_audit.get("epistemically_complete") is not True:
        completion_blockers.append("atomic claim ledger is not epistemically complete")
    if strict and reconciliation.get("valid") is not True:
        completion_blockers.append("final claims are not reconciled to the atomic ledger")
    if strict and observability.get("valid") is not True:
        completion_blockers.append("run observability/accounting is incomplete")
    claim_count = int(claim_scope.get("claim_count") or 0)
    added_claims = int(claim_scope.get("added_claims") or 0)
    idx = _jsonl_dicts(os.path.join(run, "index", "sources.jsonl"))
    cited = _claim_source_records(ver, idx)
    origins = _independent_origins(cited)
    retrieved_origins = _independent_origins(idx)
    cfg = _cfg(run)
    return {
        "topic": cfg.get("topic"), "version": cfg.get("version"),
        "implementation": cfg.get("implementation") or {},
        "citation_accuracy": precision if complete else None,
        "citation_precision": precision, "citation_coverage": coverage,
        "citation_denominator": judged, "citation_complete": complete,
        "row_verification_complete": row_complete,
        "claim_scope_audit": claim_scope,
        "claim_recall": {"added_claims": added_claims, "final_claims": claim_count,
                         "added_claim_rate": round(added_claims / claim_count, 3)
                                             if claim_count else None},
        "claim_ledger_audit": ledger_audit,
        "final_claim_reconciliation": reconciliation,
        "observability": observability,
        "completion": {"ready": not completion_blockers,
                       "blockers": completion_blockers},
        "verdicts": {"supported": supported, "contradicted": contradicted, "unsupported": unsupported,
                     "off_topic": off_topic, "broken": broken, "awaiting_llm_check": awaiting},
        # Headline independence is claim-level. Retrieval breadth remains observable but cannot
        # masquerade as corroboration.
        "sources": len(cited), "claim_sources": len(cited), "independent_origins": origins,
        "origin_echo_ratio": round(1 - origins / len(cited), 3) if cited else 0,
        "retrieved_sources": len(idx), "retrieved_independent_origins": retrieved_origins,
        "retrieved_origin_echo_ratio": round(1 - retrieved_origins / len(idx), 3) if idx else 0,
        # Behavioral activation evidence: proves which selector ran and separates retrieval,
        # selection, attempted reads, and successful reads for matched-budget evaluations.
        "runtime": runtime,
    }


def write_brief(run: str, text: str) -> str:
    """Write the user-facing brief.md into the run dir. Exists as a SCRIPT so a guarded harness that
    blocks writing report `.md` files can still emit the deliverable (the audited cold-caller gap)."""
    treestate.runtime_checkpoint(run, "before final brief write", fail_if_expired=False)
    path = os.path.join(run, "brief.md")
    payload = text if text.endswith("\n") else text + "\n"
    treestate._write_text(path, payload)
    treestate.log_run_event(run, "artifact_written", actor="orchestrator", component="report",
                            data={"artifact": "brief.md", "sha256": _file_sha256(path),
                                  "bytes": len(payload.encode("utf-8"))})
    treestate.set_run_state(run, "briefed", actor="orchestrator",
                            reason="brief exists; verification/completion gates remain")
    treestate.runtime_checkpoint(run, "after final brief write", fail_if_expired=False)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia Research output assembler (verbosity dial).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bundle"); b.add_argument("--run", required=True)
    b.add_argument("--reads", action="store_true", help="inline the primaries read in full (notes/*.md)")
    b.add_argument("--max-chars", type=int, default=0, help="truncate each read to N chars (0 = no cap)")
    b.add_argument("--output", default="", help="write the bundle to FILE instead of stdout")
    o = sub.add_parser("outline"); o.add_argument("--run", required=True)
    s = sub.add_parser("score"); s.add_argument("--run", required=True)
    s.add_argument("--output", default="", help="also persist the score JSON to FILE")
    w = sub.add_parser("write-brief"); w.add_argument("--run", required=True)
    w.add_argument("--file", default="", help="read brief text from this file")
    w.add_argument("--text", default="", help="inline brief text (use --file for anything long)")
    a = sub.add_parser("audit-claims"); a.add_argument("--run", required=True)
    a.add_argument("--auditor", required=True, help="fresh-context verifier identity/role")
    a.add_argument("--added-claims", type=int, default=0)
    a.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    if args.cmd == "bundle":
        text = bundle(args.run, args.reads, args.max_chars)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(os.path.abspath(args.output))
        else:
            print(text)
    elif args.cmd == "outline":
        print(outline(args.run))
    elif args.cmd == "score":
        payload = json.dumps(score(args.run), indent=2)
        if args.output:
            treestate._write_text(args.output, payload + "\n")
            treestate.log_run_event(args.run, "score_written", actor="runtime", component="report",
                                    data={"artifact": os.path.relpath(args.output, args.run),
                                          "sha256": _file_sha256(args.output)})
        print(payload)
    elif args.cmd == "write-brief":
        txt = _read(args.file) if args.file else args.text
        if not txt.strip():
            sys.stderr.write("write-brief: need --file or --text\n"); return 2
        print(write_brief(args.run, txt))
    elif args.cmd == "audit-claims":
        try:
            payload = audit_claim_scope(args.run, args.auditor, args.added_claims, args.notes)
        except ValueError as exc:
            sys.stderr.write("audit-claims: %s\n" % exc); return 2
        scored = score(args.run)
        if scored.get("completion", {}).get("ready"):
            final_state = "complete"
        elif _strict_accuracy_run(args.run) and os.path.isfile(os.path.join(args.run, "brief.md")):
            final_state = "delivered_with_gaps"
        else:
            final_state = "briefed"
        treestate.set_run_state(args.run, final_state, actor=args.auditor,
                                reason="; ".join(scored.get("completion", {}).get("blockers", [])))
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
