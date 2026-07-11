#!/usr/bin/env python3
"""Append-only claim/evidence/span ledger for accuracy-first Aletheia runs.

Discovery links are deliberately absent from the support calculation. A claim becomes supported only
through a verified edge to an exact source span with the required facet checks. The hash-chained event
log preserves every revision and invalidates stale stop probes when new evidence arrives.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import treestate  # noqa: E402

_LOCAL_RUNTIME_TREESTATE = None


def _runtime_ts():
    global _LOCAL_RUNTIME_TREESTATE
    if all(hasattr(treestate, name) for name in ("runtime_checkpoint", "log_run_event")):
        return treestate
    if _LOCAL_RUNTIME_TREESTATE is None:
        spec = importlib.util.spec_from_file_location(
            "aletheia_accuracy_ledger_treestate",
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "treestate.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOCAL_RUNTIME_TREESTATE = module
    return _LOCAL_RUNTIME_TREESTATE

try:  # POSIX Codex/Claude/Cursor hosts
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback is best-effort, surfaced by audit
    fcntl = None

SCHEMA_VERSION = 1
EVENTS = "claim-ledger.jsonl"
LOCK = ".claim-ledger.lock"
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,79}$")
RELATIONS = {"supports", "contradicts", "qualifies", "background"}
IMPORTANCE = {"load_bearing", "supporting"}
RESULTS = {"verified", "rejected"}
CHECKS = {"polarity", "scope", "numeric", "temporal"}
CLAIM_KINDS = {"empirical", "inferential", "normative", "forecast"}
INFERENCE_RESULTS = {"verified", "rejected", "underdetermined"}


def _canonical(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _event_hash(row: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical({k: v for k, v in row.items() if k != "event_sha256"})).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(run: str) -> str:
    return os.path.join(os.path.abspath(run), EVENTS)


def _read_rows(run: str) -> List[Dict[str, Any]]:
    path = _path(run)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("%s line %d is invalid JSON: %s" % (EVENTS, n, exc.msg)) from exc
            if not isinstance(row, dict):
                raise ValueError("%s line %d is not an object" % (EVENTS, n))
            rows.append(row)
    return rows


def verify_chain(rows: List[Dict[str, Any]]) -> List[str]:
    errors, previous = [], "0" * 64
    for i, row in enumerate(rows, 1):
        if row.get("seq") != i:
            errors.append("line %d has seq %r" % (i, row.get("seq")))
        if row.get("prev_sha256") != previous:
            errors.append("line %d breaks the previous-hash link" % i)
        actual = _event_hash(row)
        if row.get("event_sha256") != actual:
            errors.append("line %d event hash mismatch" % i)
        previous = str(row.get("event_sha256") or "")
    return errors


@contextmanager
def _locked(run: str):
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, LOCK), "a+", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def append_event(run: str, event: Dict[str, Any]) -> Dict[str, Any]:
    run = os.path.abspath(run)
    if not os.path.exists(os.path.join(run, "run.json")):
        raise ValueError("run.json not found in %s" % run)
    cfg = _runtime_ts()._read_json(os.path.join(run, "run.json"), {}) or {}
    observed = bool(cfg.get("run_id"))
    if observed and event.get("event") != "termination":
        _runtime_ts().runtime_checkpoint(run, "before claim-ledger %s" % event.get("event"),
                                         fail_if_expired=True)
    with _locked(run):
        rows = _read_rows(run)
        chain_errors = verify_chain(rows)
        if chain_errors:
            raise ValueError("refusing to append to corrupt ledger: " + "; ".join(chain_errors))
        row = {"schema_version": SCHEMA_VERSION, "seq": len(rows) + 1,
               "timestamp": _now(), "prev_sha256": rows[-1]["event_sha256"] if rows else "0" * 64}
        row.update(event)
        row["event_sha256"] = _event_hash(row)
        with open(_path(run), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    if observed:
        _runtime_ts().log_run_event(run, "claim_ledger_event", actor=str(
            event.get("verifier") or event.get("actor") or "orchestrator"), component="claim-ledger",
            data={"ledger_event": row.get("event"), "ledger_seq": row.get("seq"),
                  "ledger_event_sha256": row.get("event_sha256"),
                  "claim_id": row.get("claim_id"), "evidence_id": row.get("evidence_id"),
                  "result": row.get("result"), "reason": row.get("reason")})
    return row


def _ids(value: str) -> List[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def _checks(value: str) -> List[str]:
    values = sorted(set(_ids(value)))
    unknown = set(values) - CHECKS
    if unknown:
        raise ValueError("unknown checks: %s" % ", ".join(sorted(unknown)))
    return values


def _valid_id(value: str, label: str) -> str:
    if not ID_RE.match(value or ""):
        raise ValueError("invalid %s ID %r" % (label, value))
    return value


def reduce_state(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    claims: Dict[str, Dict[str, Any]] = {}
    evidence: Dict[str, Dict[str, Any]] = {}
    verdicts: Dict[str, Dict[str, Any]] = {}
    inference_verdicts: Dict[str, Dict[str, Any]] = {}
    probes, termination = [], None
    errors = list(verify_chain(rows))
    last_substantive_seq = 0
    for row in rows:
        kind = row.get("event")
        if kind == "claim_declared":
            cid = row.get("claim_id")
            if cid in claims:
                errors.append("duplicate claim ID %s" % cid)
            else:
                claims[cid] = row
            last_substantive_seq = row["seq"]
        elif kind == "evidence_linked":
            eid = row.get("evidence_id")
            if eid in evidence:
                errors.append("duplicate evidence ID %s" % eid)
            elif row.get("claim_id") not in claims:
                errors.append("evidence %s references unknown claim %s" % (eid, row.get("claim_id")))
            else:
                evidence[eid] = row
            last_substantive_seq = row["seq"]
        elif kind == "evidence_verified":
            eid = row.get("evidence_id")
            if eid not in evidence:
                errors.append("verdict references unknown evidence %s" % eid)
            verdicts[eid] = row
            last_substantive_seq = row["seq"]
        elif kind == "inference_verified":
            cid = row.get("claim_id")
            if cid not in claims:
                errors.append("inference verdict references unknown claim %s" % cid)
            inference_verdicts[cid] = row
            last_substantive_seq = row["seq"]
        elif kind == "stop_probe":
            probes.append(row)
        elif kind == "termination":
            termination = row
        else:
            errors.append("unknown ledger event %r" % kind)
    for cid, claim in claims.items():
        for dependency in claim.get("depends_on_claim_ids") or []:
            if dependency not in claims:
                errors.append("claim %s depends on unknown claim %s" % (cid, dependency))
    return {"claims": claims, "evidence": evidence, "verdicts": verdicts,
            "inference_verdicts": inference_verdicts,
            "probes": probes, "termination": termination, "errors": errors,
            "last_substantive_seq": last_substantive_seq}


def _edge_passes(claim: Dict[str, Any], ev: Dict[str, Any], verdict: Optional[Dict[str, Any]]) -> bool:
    if not verdict or verdict.get("result") != "verified":
        return False
    completed = set(verdict.get("checks_completed") or [])
    required = set(claim.get("check_requirements") or ["polarity", "scope"])
    return (required <= completed and bool(ev.get("verbatim_span")) and
            bool(ev.get("content_hash")) and bool(ev.get("artifact_valid")))


def _norm_ws(value: str) -> str:
    return " ".join((value or "").split())


def _validate_artifact(run: str, ev: Dict[str, Any]) -> List[str]:
    eid = ev.get("evidence_id", "?")
    artifact = ev.get("content_artifact")
    if not artifact:
        return ["evidence %s has no bound content artifact" % eid]
    path = artifact if os.path.isabs(artifact) else os.path.join(run, artifact)
    try:
        with open(path, "rb") as fh:
            body = fh.read()
    except OSError:
        return ["evidence %s content artifact is unreadable" % eid]
    errors = []
    if hashlib.sha256(body).hexdigest() != ev.get("content_hash"):
        errors.append("evidence %s content artifact hash changed" % eid)
    text = body.decode("utf-8", "replace")
    if _norm_ws(ev.get("verbatim_span", "")) not in _norm_ws(text):
        errors.append("evidence %s verbatim span is absent from its content artifact" % eid)
    return errors


def materialize(run: str) -> Dict[str, Any]:
    run = os.path.abspath(run)
    rows = _read_rows(run)
    state = reduce_state(rows)
    evidence = {eid: dict(ev) for eid, ev in state["evidence"].items()}
    artifact_errors = []
    for ev in evidence.values():
        errs = _validate_artifact(run, ev)
        ev["artifact_valid"] = not errs
        artifact_errors.extend(errs)
    rendered = {}
    for cid, claim in state["claims"].items():
        linked = [e for e in evidence.values() if e.get("claim_id") == cid]
        passing = [e for e in linked if _edge_passes(claim, e, state["verdicts"].get(e["evidence_id"]))]
        supports = [e for e in passing if e.get("relation_to_claim") == "supports"]
        contradicts = [e for e in passing if e.get("relation_to_claim") == "contradicts"]
        kind = claim.get("claim_kind") or "empirical"
        if kind != "empirical":
            status = "unresolved"
        elif supports and contradicts:
            status = "disputed"
        elif supports:
            status = "supported"
        elif contradicts:
            status = "contradicted"
        else:
            status = "unresolved"
        origins = sorted({str(e.get("origin_key")) for e in supports if e.get("origin_key")})
        rendered[cid] = dict(claim, status=status,
                             support_evidence_ids=[e["evidence_id"] for e in supports],
                             contradict_evidence_ids=[e["evidence_id"] for e in contradicts],
                             independent_origin_keys=origins,
                             linked_evidence_ids=[e["evidence_id"] for e in linked])
    # Conclusions are arguments over verified premises. A source span cannot directly certify
    # "probably helped overall" or another synthesis judgment, so those claims need an independent
    # inference verdict and every declared premise must itself remain supported.
    for _ in range(max(1, len(rendered))):
        changed = False
        for cid, claim in rendered.items():
            if (claim.get("claim_kind") or "empirical") == "empirical":
                continue
            inference = state["inference_verdicts"].get(cid) or {}
            dependencies = list(claim.get("depends_on_claim_ids") or [])
            dep_states = [rendered.get(dep, {}).get("status") for dep in dependencies]
            if inference.get("result") == "rejected":
                status = "contradicted"
            elif (inference.get("result") == "verified" and dependencies
                  and all(value == "supported" for value in dep_states)):
                status = "supported"
            else:
                status = "unresolved"
            origins = sorted({origin for dep in dependencies
                              for origin in rendered.get(dep, {}).get("independent_origin_keys", [])})
            if claim.get("status") != status or claim.get("independent_origin_keys") != origins:
                claim["status"] = status
                claim["independent_origin_keys"] = origins
                changed = True
            claim["inference_verdict"] = inference or None
            claim["premise_statuses"] = dict(zip(dependencies, dep_states))
        if not changed:
            break
    return {"schema_version": SCHEMA_VERSION, "chain_valid": not verify_chain(rows),
            "claims": rendered, "evidence": evidence, "verdicts": state["verdicts"],
            "inference_verdicts": state["inference_verdicts"],
            "probes": state["probes"], "termination": state["termination"],
            "errors": state["errors"] + artifact_errors,
            "last_substantive_seq": state["last_substantive_seq"],
            "portable_locking": fcntl is not None}


def audit(run: str) -> Dict[str, Any]:
    state = materialize(run)
    blockers = list(state["errors"])
    if not state["claims"]:
        blockers.append("claim ledger is empty")
    elif not any(c.get("importance") == "load_bearing" for c in state["claims"].values()):
        blockers.append("claim ledger has no load-bearing claims")
    for cid, claim in state["claims"].items():
        if claim.get("importance") != "load_bearing":
            continue
        if claim["status"] != "supported":
            blockers.append("%s is %s" % (cid, claim["status"]))
        required = int(claim.get("required_origins", 1) or 0)
        if ((claim.get("claim_kind") or "empirical") == "empirical"
                and len(claim["independent_origin_keys"]) < required):
            blockers.append("%s has %d/%d required independent supporting origins" %
                            (cid, len(claim["independent_origin_keys"]), required))
    last = state["last_substantive_seq"]
    challenger = next((p for p in reversed(state["probes"])
                       if p.get("probe_kind") == "challenger" and p.get("seq", 0) > last), None)
    confirmation = next((p for p in reversed(state["probes"])
                         if p.get("probe_kind") == "confirmation" and challenger
                         and p.get("seq", 0) > challenger.get("seq", 0)), None)
    probe_blockers = []
    if not challenger or challenger.get("outcome") != "no_material_novelty":
        probe_blockers.append("fresh independent challenger probe missing or found a gap")
    if not confirmation or confirmation.get("outcome") != "no_material_novelty":
        probe_blockers.append("soft-stop confirmation missing or found a gap")
    ready = not blockers
    epistemically_complete = ready and not probe_blockers
    termination_reason = (state.get("termination") or {}).get("reason")
    return {"schema_version": SCHEMA_VERSION, "chain_valid": state["chain_valid"],
            "claims": len(state["claims"]), "ready_for_synthesis": ready,
            "epistemically_complete": epistemically_complete, "blockers": blockers,
            "stop_blockers": probe_blockers, "termination_reason": termination_reason,
            "budget_exhausted": termination_reason in {"wall_clock_limit", "run_read_limit",
                                                        "budget_exhausted"},
            "portable_locking": state["portable_locking"]}


def next_actions(run: str) -> List[Dict[str, Any]]:
    state = materialize(run)
    out = []
    for cid, claim in state["claims"].items():
        importance = 100 if claim.get("importance") == "load_bearing" else 10
        status_score = {"disputed": 90, "contradicted": 80, "unresolved": 70,
                        "supported": 0}[claim["status"]]
        deficit = max(0, int(claim.get("required_origins", 1)) -
                      len(claim["independent_origin_keys"]))
        score = importance + status_score + 20 * deficit
        if score:
            action = "adjudicate contradiction" if claim["status"] == "disputed" else (
                "find supporting primary" if claim["status"] != "supported" else
                "find independent corroboration")
            out.append({"claim_id": cid, "priority": score, "action": action,
                        "status": claim["status"], "origin_deficit": deficit})
    return sorted(out, key=lambda x: (-x["priority"], x["claim_id"]))


def context_markdown(run: str) -> str:
    state = materialize(run)
    lines = ["# Verified claim/evidence context", "",
             "Only verified support edges are included; bibliographic discovery links confer no support.", ""]
    for cid, claim in sorted(state["claims"].items()):
        lines += ["## %s — %s" % (cid, claim["status"]), "", claim.get("canonical_text", ""), ""]
        for eid in claim["support_evidence_ids"] + claim["contradict_evidence_ids"]:
            ev = state["evidence"][eid]
            lines += ["- `%s` %s: “%s” — %s (%s)" %
                      (eid, ev["relation_to_claim"], ev["verbatim_span"], ev["source_url"],
                       ev.get("locator") or "locator not supplied")]
        lines.append("")
    return "\n".join(lines)


def _existing_ids(run: str) -> Tuple[set, set]:
    state = reduce_state(_read_rows(run))
    return set(state["claims"]), set(state["evidence"])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add-claim"); p.add_argument("--run", required=True)
    p.add_argument("--id", required=True); p.add_argument("--text", required=True)
    p.add_argument("--scope", required=True); p.add_argument("--importance", choices=sorted(IMPORTANCE), required=True)
    p.add_argument("--kind", choices=sorted(CLAIM_KINDS), default="empirical")
    p.add_argument("--required-origins", type=int, default=1); p.add_argument("--valid-time", default="")
    p.add_argument("--freshness", default="none"); p.add_argument("--depends-on", default="")
    p.add_argument("--checks", default="polarity,scope")

    p = sub.add_parser("add-evidence"); p.add_argument("--run", required=True)
    p.add_argument("--id", required=True); p.add_argument("--claim", required=True)
    p.add_argument("--url", required=True); p.add_argument("--source-class", required=True)
    p.add_argument("--origin-key", required=True); p.add_argument("--version-url", default="")
    p.add_argument("--publication-date", default=""); p.add_argument("--event-date", default="")
    p.add_argument("--accessed-at", default=""); p.add_argument("--span", required=True)
    p.add_argument("--locator", required=True); p.add_argument("--content-file", required=True)
    p.add_argument("--relation", choices=sorted(RELATIONS), required=True)

    p = sub.add_parser("verify-evidence"); p.add_argument("--run", required=True)
    p.add_argument("--id", required=True); p.add_argument("--result", choices=sorted(RESULTS), required=True)
    p.add_argument("--verifier", required=True); p.add_argument("--checks", default="polarity,scope")
    p.add_argument("--why", required=True)

    p = sub.add_parser("verify-inference"); p.add_argument("--run", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--result", choices=sorted(INFERENCE_RESULTS), required=True)
    p.add_argument("--verifier", required=True); p.add_argument("--premises", required=True)
    p.add_argument("--assumptions", required=True); p.add_argument("--counterarguments", required=True)
    p.add_argument("--why", required=True)

    p = sub.add_parser("probe"); p.add_argument("--run", required=True)
    p.add_argument("--kind", dest="probe_kind", choices=["challenger", "confirmation"], required=True)
    p.add_argument("--outcome", choices=["no_material_novelty", "found_gap"], required=True)
    p.add_argument("--actor", required=True); p.add_argument("--method", required=True)

    p = sub.add_parser("terminate"); p.add_argument("--run", required=True)
    p.add_argument("--reason", choices=["budget_exhausted", "wall_clock_limit", "run_read_limit",
                                         "evidence_exhausted", "user_stopped", "runtime_failure"],
                   required=True)

    for name in ("show", "audit", "next", "context"):
        p = sub.add_parser(name); p.add_argument("--run", required=True)
        if name == "context": p.add_argument("--output", default="")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "add-claim":
            claims, _ = _existing_ids(args.run); cid = _valid_id(args.id, "claim")
            if cid in claims: raise ValueError("claim ID already exists: %s" % cid)
            if not args.text.strip() or not args.scope.strip(): raise ValueError("claim text/scope must not be empty")
            if args.required_origins < 0: raise ValueError("required_origins must be >= 0")
            if args.kind == "empirical" and args.required_origins < 1:
                raise ValueError("empirical claims require at least one independent origin")
            dependencies = _ids(args.depends_on)
            if args.kind != "empirical" and not dependencies:
                raise ValueError("non-empirical claims require --depends-on premises")
            missing_dependencies = sorted(set(dependencies) - claims)
            if missing_dependencies:
                raise ValueError("unknown dependency claim IDs: %s" %
                                 ", ".join(missing_dependencies))
            row = append_event(args.run, {"event": "claim_declared", "claim_id": cid,
                "canonical_text": args.text.strip(), "scope": args.scope.strip(),
                "claim_kind": args.kind,
                "importance": args.importance, "required_origins": args.required_origins,
                "valid_time": args.valid_time, "freshness_requirement": args.freshness,
                "depends_on_claim_ids": dependencies,
                "check_requirements": _checks(args.checks)})
        elif args.cmd == "add-evidence":
            claims, evidence = _existing_ids(args.run); eid = _valid_id(args.id, "evidence")
            if eid in evidence: raise ValueError("evidence ID already exists: %s" % eid)
            if args.claim not in claims: raise ValueError("unknown claim ID: %s" % args.claim)
            if not args.url.lower().startswith(("http://", "https://")): raise ValueError("evidence URL must be HTTP(S)")
            if len(args.span.strip()) < 8: raise ValueError("verbatim span is too short")
            content_path = os.path.abspath(args.content_file)
            with open(content_path, "rb") as fh: content = fh.read()
            if _norm_ws(args.span.strip()) not in _norm_ws(content.decode("utf-8", "replace")):
                raise ValueError("verbatim span is absent from --content-file")
            try: content_artifact = os.path.relpath(content_path, os.path.abspath(args.run))
            except ValueError: content_artifact = content_path
            row = append_event(args.run, {"event": "evidence_linked", "evidence_id": eid,
                "claim_id": args.claim, "source_url": args.url, "source_class": args.source_class,
                "origin_key": args.origin_key, "version_url": args.version_url,
                "publication_date": args.publication_date, "event_date": args.event_date,
                "accessed_at": args.accessed_at or _now(), "verbatim_span": args.span.strip(),
                "locator": args.locator, "content_artifact": content_artifact,
                "content_hash": hashlib.sha256(content).hexdigest(),
                "relation_to_claim": args.relation})
        elif args.cmd == "verify-evidence":
            _, evidence = _existing_ids(args.run)
            if args.id not in evidence: raise ValueError("unknown evidence ID: %s" % args.id)
            row = append_event(args.run, {"event": "evidence_verified", "evidence_id": args.id,
                "result": args.result, "verifier": args.verifier,
                "checks_completed": _checks(args.checks), "why": args.why})
        elif args.cmd == "verify-inference":
            state = reduce_state(_read_rows(args.run))
            claim = state["claims"].get(args.claim)
            if not claim: raise ValueError("unknown claim ID: %s" % args.claim)
            if (claim.get("claim_kind") or "empirical") == "empirical":
                raise ValueError("empirical claims use exact-span evidence, not inference verdicts")
            premises = _ids(args.premises)
            declared = list(claim.get("depends_on_claim_ids") or [])
            if set(premises) != set(declared) or len(premises) != len(declared):
                raise ValueError("--premises must exactly match the claim's declared dependencies")
            row = append_event(args.run, {"event": "inference_verified", "claim_id": args.claim,
                "result": args.result, "verifier": args.verifier, "premise_claim_ids": premises,
                "assumptions": args.assumptions, "counterarguments": args.counterarguments,
                "why": args.why})
        elif args.cmd == "probe":
            row = append_event(args.run, {"event": "stop_probe", "probe_kind": args.probe_kind,
                "outcome": args.outcome, "actor": args.actor, "method": args.method})
        elif args.cmd == "terminate":
            row = append_event(args.run, {"event": "termination", "reason": args.reason})
        elif args.cmd == "show":
            print(json.dumps(materialize(args.run), indent=2, sort_keys=True)); return 0
        elif args.cmd == "audit":
            print(json.dumps(audit(args.run), indent=2, sort_keys=True)); return 0
        elif args.cmd == "next":
            print(json.dumps(next_actions(args.run), indent=2, sort_keys=True)); return 0
        elif args.cmd == "context":
            text = context_markdown(args.run)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as fh: fh.write(text + "\n")
                print(os.path.abspath(args.output))
            else: print(text)
            return 0
        print(json.dumps(row, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        sys.stderr.write("ledger: %s\n" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
