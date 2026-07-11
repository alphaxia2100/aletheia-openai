#!/usr/bin/env python3
"""Deep Aletheia — filesystem-as-blackboard tree state.

Every agent node in a Deep Aletheia run is a DIRECTORY. All coordination is files, so
nothing depends on a single context window: state survives on disk (resumable, auditable),
findings flow UP (findings.md), clarifications flow DOWN (questions.jsonl/answers.jsonl),
and each agent keeps a reasoning log (decisions.jsonl).

Budget model (conserved split, contestedness-weighted):
  A node holds a numeric BUDGET. Splitting into K children CONSERVES budget (children sum to the
  parent). Allocation is uniform (budget/K) by default, or WEIGHTED by contestedness/uncertainty
  (split --weights): floor every child at U (the scrutiny unit, no starvation), then distribute the
  remainder by weight — contested children get deeper scrutiny (the audited fix for the old uniform
  "equal scrutiny per leaf"; scale-effort-to-complexity, Snell 2408.03314 / UAB 2605.26849). Recurse
  while budget/K >= U; else the node is a LEAF that spends its budget investigating. Hard caps
  (max_depth/max_children/max_nodes) bound fan-out.

Layout:
  runs/aletheia-research-accuracy/<ts>-<slug>/
    run.json  portfolio.md  brief.md  verify.jsonl
    index/sources.jsonl                      (global dedup / independence)
    tree/root/{spec.md,status.json,decisions.jsonl,questions.jsonl,answers.jsonl,
               sources.jsonl,notes/,findings.md,children/<qid>/...}

CLI (used by the orchestrator skill + subagents):
  treestate.py init "<topic>" [--slug s] [--thoroughness quick|standard|deep|exhaustive|unlimited|max]
               [--verbosity user|agent] [--budget N (explicit = custom bounded run)]
               # default (no tier, no budget) = `accuracy`: agent-paced within hard ceilings
  treestate.py split  --node DIR --children '[["q1","question one"],["q2","..."]]'
  treestate.py decide --node DIR --actor NAME --why "..." "<decision>"
  treestate.py status --node DIR [--set state] [--field k=v ...]
  treestate.py ask    --node CHILD_DIR --from PARENT --q "specific question"
  treestate.py answer --node DIR --qid QID --a "answer text"
  treestate.py findings --node DIR --text "..."   (or --file f)
  treestate.py split  --node DIR --children '[...]' [--weights "[3,1,2]"]
  treestate.py frontier --run RUNDIR [--state pending] [--resumable]
  treestate.py tree   --run RUNDIR
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any, Dict, List, Optional

NODE_FILES = ("decisions.jsonl", "questions.jsonl", "answers.jsonl", "sources.jsonl")
RUN_EVENTS = "run-events.jsonl"
RUN_EVENTS_LOCK = ".run-events.lock"
RUN_EVENT_SCHEMA = 1


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").lower()).strip("-")
    return (s[:n].strip("-") or "run")


def _sha256_files(root: str, paths: List[str]) -> Optional[str]:
    h = hashlib.sha256()
    found = False
    for path in sorted(paths):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        found = True
        h.update(os.path.relpath(path, root).encode("utf-8", "surrogateescape"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest() if found else None


def _implementation_metadata() -> Dict[str, Any]:
    """Fingerprint the executable skill, not just its manually maintained version label."""
    scripts = os.path.dirname(os.path.realpath(__file__))
    skill = os.path.dirname(scripts)
    skills_root = os.path.dirname(skill)
    files = [os.path.join(skill, "SKILL.md"), os.path.join(skill, "agents", "openai.yaml")]
    for directory, _subdirs, names in os.walk(scripts):
        files.extend(os.path.join(directory, name) for name in names
                     if name.endswith((".py", ".json", ".sh")))
    channel_cfg = os.path.realpath(os.path.join(skill, "..", "channel-retrieval", "channels.json"))
    runtime_files = list(files)
    for dependency in ("channel-retrieval", "provenance-audit"):
        dep_root = os.path.join(skills_root, dependency)
        for directory, _subdirs, names in os.walk(dep_root):
            runtime_files.extend(os.path.join(directory, name) for name in names
                                 if name.endswith((".py", ".json", ".sh")))
    meta: Dict[str, Any] = {
        "schema_version": 1,
        "skill_sha256": _sha256_files(skill, files),
        "channel_config_sha256": _sha256_files(os.path.dirname(channel_cfg), [channel_cfg]),
        "runtime_sha256": _sha256_files(skills_root, runtime_files),
        "git_commit": None,
        "git_dirty": None,
    }
    try:
        meta["git_commit"] = subprocess.check_output(
            ["git", "-C", skill, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
            text=True, timeout=3).strip() or None
        meta["git_dirty"] = bool(subprocess.check_output(
            ["git", "-C", skill, "status", "--porcelain", "--untracked-files=normal"],
            stderr=subprocess.DEVNULL, text=True, timeout=3).strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return meta


def _read_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path: str, obj: Any) -> None:
    """Atomically replace JSON state so a crash cannot leave a half-written run/status file."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".%s." % os.path.basename(path), dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _write_text(path: str, text: str) -> None:
    """Atomically replace a text artifact and fsync it before publication."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".%s." % os.path.basename(path), dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj) + "\n")


def _canonical_event(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _run_event_hash(row: Dict[str, Any]) -> str:
    material = {k: v for k, v in row.items() if k != "event_sha256"}
    return hashlib.sha256(_canonical_event(material)).hexdigest()


def _read_run_events(run: str) -> List[Dict[str, Any]]:
    path = os.path.join(run, RUN_EVENTS)
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError as exc:
                raise ValueError("%s line %d is invalid JSON" % (RUN_EVENTS, lineno)) from exc
            if not isinstance(row, dict):
                raise ValueError("%s line %d is not an object" % (RUN_EVENTS, lineno))
            rows.append(row)
    return rows


def verify_run_events(rows: List[Dict[str, Any]]) -> List[str]:
    """Verify sequence, run identity continuity, and the tamper-evident hash chain."""
    errors: List[str] = []
    previous = "0" * 64
    run_id = None
    for lineno, row in enumerate(rows, 1):
        if row.get("seq") != lineno:
            errors.append("line %d has seq %r" % (lineno, row.get("seq")))
        if row.get("prev_sha256") != previous:
            errors.append("line %d breaks the previous-hash link" % lineno)
        actual = _run_event_hash(row)
        if row.get("event_sha256") != actual:
            errors.append("line %d event hash mismatch" % lineno)
        if run_id is None:
            run_id = row.get("run_id")
        elif row.get("run_id") != run_id:
            errors.append("line %d changes run_id" % lineno)
        previous = str(row.get("event_sha256") or "")
    return errors


def audit_run_events(run: str) -> Dict[str, Any]:
    """Machine-readable integrity/coverage summary for the unified execution chronology."""
    run = os.path.abspath(run)
    cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
    try:
        rows = _read_run_events(run)
        errors = verify_run_events(rows)
    except ValueError as exc:
        rows, errors = [], [str(exc)]
    counts: Dict[str, int] = {}
    for row in rows:
        key = str(row.get("event") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    required = {"run_initialized", "node_created"}
    if cfg.get("state") in {"complete", "delivered_with_gaps", "terminated", "failed"}:
        required.add("run_state_changed")
    missing = sorted(required - set(counts))
    return {
        "schema_version": RUN_EVENT_SCHEMA,
        "run_id": cfg.get("run_id"),
        "events": len(rows),
        "chain_valid": bool(rows) and not errors,
        "errors": errors,
        "missing_required_events": missing,
        "event_counts": dict(sorted(counts.items())),
        "last_elapsed_seconds": max(
            [float(row.get("elapsed_seconds", 0) or 0) for row in rows] or [0.0]),
        "last_event_sha256": rows[-1].get("event_sha256") if rows else None,
    }


def log_run_event(run_or_node: str, event: str, actor: str = "runtime",
                  component: str = "treestate", data: Optional[Dict[str, Any]] = None,
                  node: str = "", correlation_id: str = "") -> Dict[str, Any]:
    """Append one canonical event to the run-wide locked, hash-chained audit spine.

    Specialized files (claim ledger, telemetry, human decisions) remain useful views. This stream is
    the ordered join key that makes the complete execution replayable without timestamp archaeology.
    """
    candidate = os.path.abspath(run_or_node)
    run = candidate if os.path.isfile(os.path.join(candidate, "run.json")) else _find_run(candidate)
    if not run:
        raise ValueError("run.json not found above %s" % run_or_node)
    cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
    run_id = str(cfg.get("run_id") or "")
    if not run_id:
        raise ValueError("run_id missing from run.json")
    target_node = os.path.abspath(node or candidate)
    node_rel = ""
    if target_node != os.path.abspath(run) and target_node.startswith(os.path.abspath(run) + os.sep):
        node_rel = os.path.relpath(target_node, run)
    lock_path = os.path.join(run, RUN_EVENTS_LOCK)
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows = _read_run_events(run)
        errors = verify_run_events(rows)
        if errors:
            raise ValueError("refusing to append to corrupt run log: " + "; ".join(errors))
        epoch = time.time()
        started = float(cfg.get("started_epoch") or epoch)
        row: Dict[str, Any] = {
            "schema_version": RUN_EVENT_SCHEMA,
            "seq": len(rows) + 1,
            "event_id": "%s:%06d" % (run_id, len(rows) + 1),
            "run_id": run_id,
            "timestamp": _now(),
            "timestamp_epoch": epoch,
            "elapsed_seconds": round(max(0.0, epoch - started), 3),
            "event": str(event),
            "component": str(component),
            "actor": str(actor),
            "node": node_rel,
            "correlation_id": str(correlation_id or ""),
            "data": data or {},
            "prev_sha256": rows[-1]["event_sha256"] if rows else "0" * 64,
        }
        row["event_sha256"] = _run_event_hash(row)
        with open(os.path.join(run, RUN_EVENTS), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return row


def record_artifact(run_or_node: str, path: str, actor: str = "orchestrator",
                    kind: str = "artifact") -> Dict[str, Any]:
    """Hash and register an agent-authored file that is not emitted by an instrumented script."""
    candidate = os.path.abspath(run_or_node)
    run = candidate if os.path.isfile(os.path.join(candidate, "run.json")) else _find_run(candidate)
    if not run:
        raise ValueError("run.json not found above %s" % run_or_node)
    target = os.path.abspath(path if os.path.isabs(path) else os.path.join(run, path))
    if not target.startswith(os.path.abspath(run) + os.sep) or not os.path.isfile(target):
        raise ValueError("artifact must be an existing file inside the run")
    with open(target, "rb") as fh:
        content = fh.read()
    return log_run_event(run_or_node, "artifact_registered", actor=actor, component="artifact",
                         data={"kind": kind, "artifact": os.path.relpath(target, run),
                               "bytes": len(content),
                               "sha256": hashlib.sha256(content).hexdigest()})


# ---------------------------------------------------------------- node primitives
def _init_node_dir(node: str, qid: str, question: str, budget: float, depth: int,
                   role: str, parent: Optional[str]) -> None:
    os.makedirs(os.path.join(node, "notes"), exist_ok=True)
    os.makedirs(os.path.join(node, "children"), exist_ok=True)
    for f in NODE_FILES:
        open(os.path.join(node, f), "a", encoding="utf-8").close()
    _write_json(os.path.join(node, "status.json"), {
        "qid": qid, "question": question, "budget": round(budget, 3), "depth": depth,
        "role": role, "parent": parent, "state": "pending", "updated": _now(),
    })
    with open(os.path.join(node, "spec.md"), "w", encoding="utf-8") as fh:
        fh.write("# %s\n\n**Question:** %s\n\n- role: %s\n- budget: %.3f\n- depth: %d\n"
                 "- parent: %s\n\n## Objective\n_(orchestrator fills: what to find, output "
                 "schema, channel hints, boundaries)_\n" %
                 (qid, question, role, budget, depth, parent or "(root)"))
    run = _find_run(node)
    if run:
        log_run_event(node, "node_created", actor="orchestrator", component="treestate",
                      data={"qid": qid, "question": question, "budget": round(budget, 3),
                            "depth": depth, "role": role, "parent": parent})


def set_status(node: str, state: Optional[str] = None, **fields: Any) -> Dict[str, Any]:
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    before = dict(st)
    if state:
        st["state"] = state
    for k, v in fields.items():
        st[k] = v
    st["updated"] = _now()
    _write_json(os.path.join(node, "status.json"), st)
    changed = {key: st.get(key) for key in st if before.get(key) != st.get(key) and key != "updated"}
    if changed and _find_run(node):
        log_run_event(node, "node_state_changed", actor="runtime", component="treestate",
                      data={"before_state": before.get("state"), "after_state": st.get("state"),
                            "changed": changed})
    return st


def set_run_state(run: str, state: str, actor: str = "runtime", reason: str = "") -> Dict[str, Any]:
    """Persist the run lifecycle; node status alone is not enough for resume/observability."""
    path = os.path.join(run, "run.json")
    cfg = _read_json(path, {}) or {}
    before = cfg.get("state")
    cfg["state"] = state
    cfg["updated"] = _now()
    if state in {"complete", "delivered_with_gaps", "terminated", "failed"}:
        finished = time.time()
        cfg["finished_epoch"] = finished
        cfg["elapsed_seconds"] = round(max(0.0, finished - float(cfg.get("started_epoch") or finished)), 3)
    _write_json(path, cfg)
    log_run_event(run, "run_state_changed", actor=actor, component="treestate",
                  data={"from": before, "to": state, "reason": reason,
                        "elapsed_seconds": cfg.get("elapsed_seconds")})
    return cfg


def log_decision(node: str, actor: str, decision: str, why: str = "") -> None:
    _append_jsonl(os.path.join(node, "decisions.jsonl"),
                  {"t": _now(), "actor": actor, "decision": decision, "why": why})
    if _find_run(node):
        log_run_event(node, "decision_recorded", actor=actor, component="orchestrator",
                      data={"decision": decision, "why": why})


# ---------------------------------------------------------------- run + tree
# Thoroughness dial (callable/scaled from any session; scales effort to the question). It sets the
# tree's budget/caps — deeper tiers spend more and split wider. `auto` = the agent picks it in SCOPE.
#: Tiers. `accuracy` is the DEFAULT: depth is agent-paced, while elapsed time and reads have hard
#: ceilings. `unlimited` remains an explicit compatibility tier but is still bounded by the same
#: absolute safety ceilings in this accuracy specialization.
#: budget-exhaustion but AGENT-PACED CONVERGENCE — the orchestrator keeps splitting/deepening until a
#: branch is saturated (no new distinct origins/claims). A high `max_nodes` remains as the one safety
#: backstop (Anthropic's 50-subagent failure) — raise it, don't rely on it. The bounded tiers stay for
#: when speed matters. `max` is the "proper flag": the same unbounded caps but run maximally (more
#: framings, more redundancy, deeper verification) — the ~week-of-searching target vs unlimited's ~day.
_BIG = 1_000_000.0
ABS_MAX_SECONDS = 3600.0
ABS_MAX_READS_PER_ROUND = 40
ABS_MAX_READ_ATTEMPTS = 640
THOROUGHNESS = {
    "quick":      dict(budget=8.0,  unit=4.0, max_depth=1, max_children=3, max_nodes=8),
    "standard":   dict(budget=16.0, unit=4.0, max_depth=2, max_children=3, max_nodes=16),
    "deep":       dict(budget=32.0, unit=4.0, max_depth=3, max_children=4, max_nodes=40),
    "exhaustive": dict(budget=64.0, unit=4.0, max_depth=3, max_children=5, max_nodes=64),
    "unlimited":  dict(budget=_BIG, unit=4.0, max_depth=99, max_children=6, max_nodes=512),
    "max":        dict(budget=_BIG, unit=4.0, max_depth=99, max_children=8, max_nodes=2048),
    "accuracy":   dict(budget=_BIG, unit=4.0, max_depth=99, max_children=8, max_nodes=2048,
                       reads_per_round=40, max_read_attempts=640, max_seconds=3600.0),
}


def init_run(topic: str, slug: str = "", budget: Optional[float] = None, unit: float = 4.0,
             max_depth: int = 3, max_children: int = 5, max_nodes: int = 40,
             base: str = "runs/aletheia-research-accuracy", thoroughness: str = "",
             verbosity: str = "user", reads_per_round: Optional[int] = None,
             max_read_attempts: Optional[int] = None,
             max_seconds: Optional[float] = None) -> str:
    if not str(topic).strip():
        raise ValueError("topic must not be empty")
    if thoroughness and thoroughness not in THOROUGHNESS:
        raise ValueError("unknown thoroughness %r" % thoroughness)
    if budget is not None and budget <= 0:
        raise ValueError("budget must be positive")
    if unit <= 0:
        raise ValueError("unit must be positive")
    if reads_per_round is not None and reads_per_round <= 0:
        raise ValueError("reads_per_round must be positive")
    if max_read_attempts is not None and max_read_attempts <= 0:
        raise ValueError("max_read_attempts must be positive")
    if max_seconds is not None and max_seconds <= 0:
        raise ValueError("max_seconds must be positive")
    if reads_per_round is not None and reads_per_round > ABS_MAX_READS_PER_ROUND:
        raise ValueError("reads_per_round exceeds accuracy hard ceiling (%d)" % ABS_MAX_READS_PER_ROUND)
    if max_read_attempts is not None and max_read_attempts > ABS_MAX_READ_ATTEMPTS:
        raise ValueError("max_read_attempts exceeds accuracy hard ceiling (%d)" % ABS_MAX_READ_ATTEMPTS)
    if max_seconds is not None and max_seconds > ABS_MAX_SECONDS:
        raise ValueError("max_seconds exceeds accuracy hard ceiling (%s)" % int(ABS_MAX_SECONDS))
    # Resolution: a named tier wins; else an EXPLICIT budget means custom (honored, for bounded/
    # programmatic runs); else — nothing specified — default to the bounded accuracy tier.
    if thoroughness in THOROUGHNESS:
        tier = thoroughness
    elif budget is None:
        tier = "accuracy"
    else:
        tier = thoroughness or "custom"
    if tier in THOROUGHNESS:              # tier overrides budget/caps
        t = THOROUGHNESS[tier]
        budget, unit = t["budget"], t["unit"]
        max_depth, max_children, max_nodes = t["max_depth"], t["max_children"], t["max_nodes"]
        reads_per_round = reads_per_round or t.get("reads_per_round")
        max_read_attempts = max_read_attempts or t.get("max_read_attempts")
        max_seconds = max_seconds or t.get("max_seconds")
    reads_per_round = int(reads_per_round or max(3, round(unit)))
    max_read_attempts = int(max_read_attempts or ABS_MAX_READ_ATTEMPTS)
    max_seconds = float(max_seconds or ABS_MAX_SECONDS)
    verbosity = verbosity if verbosity in ("user", "agent") else "user"
    ts = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    stem = os.path.join(base, "%s-%s" % (ts, _slugify(slug or topic)))
    suffix = 1
    while True:
        run = stem if suffix == 1 else "%s-%d" % (stem, suffix)
        try:
            os.makedirs(run)
            break
        except FileExistsError:
            suffix += 1
    os.makedirs(os.path.join(run, "index"))
    started_epoch = time.time()
    run_id = uuid.uuid4().hex
    request_text = str(topic).strip() + "\n"
    request_sha256 = hashlib.sha256(request_text.encode("utf-8")).hexdigest()
    _write_json(os.path.join(run, "run.json"), {
        "run_id": run_id, "topic": topic, "request_sha256": request_sha256,
        "created": _now(), "version": "aletheia-research-accuracy 0.6.0-accuracy.2",
        "implementation": _implementation_metadata(),
        "thoroughness": tier, "verbosity": verbosity,
        "budget": budget, "unit": unit, "max_depth": max_depth,
        "max_children": max_children, "max_nodes": max_nodes, "state": "framing",
        "started_epoch": started_epoch,
        "limits": {"max_seconds": max_seconds,
                   "max_reads_per_round": reads_per_round,
                   "max_read_attempts": max_read_attempts},
    })
    _write_json(os.path.join(run, "runtime-ledger.json"), {
        "schema_version": 1, "started_epoch": started_epoch,
        "search_attempts": 0, "read_attempts_reserved": 0,
    })
    _write_text(os.path.join(run, "request.md"), request_text)
    _write_text(os.path.join(run, "portfolio.md"),
                "# Hypothesis portfolio — %s\n\n_(orchestrator writes 4-6 competing "
                "framings here before any search)_\n" % topic)
    open(os.path.join(run, "index", "sources.jsonl"), "a", encoding="utf-8").close()
    log_run_event(run, "run_initialized", actor="orchestrator", component="treestate",
                  data={"topic": topic, "request_sha256": request_sha256,
                        "version": "aletheia-research-accuracy 0.6.0-accuracy.2",
                        "thoroughness": tier,
                        "limits": {"max_seconds": max_seconds,
                                   "max_reads_per_round": reads_per_round,
                                   "max_read_attempts": max_read_attempts}})
    _init_node_dir(os.path.join(run, "tree", "root"), "root", topic, budget, 0, "root", None)
    return run


def reserve_runtime(node: str, kind: str, amount: int = 1, detail: str = "") -> Dict[str, Any]:
    """Atomically reserve a network action before it runs.

    Reservations are never refunded: failures and crashed workers still consumed an attempt. A file
    lock makes parallel leaves fail closed instead of racing beyond a run-wide hard ceiling.
    """
    if kind not in ("search", "read") or amount < 0:
        raise ValueError("invalid runtime reservation")
    run = _find_run(node)
    if not run:
        return {"enforced": False}
    cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
    limits = cfg.get("limits") or {}
    lock_path = os.path.join(run, ".runtime-ledger.lock")
    ledger_path = os.path.join(run, "runtime-ledger.json")
    events_path = os.path.join(run, "runtime-events.jsonl")
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        ledger = _read_json(ledger_path, {}) or {}
        started = float(ledger.get("started_epoch") or cfg.get("started_epoch") or time.time())
        elapsed = max(0.0, time.time() - started)
        max_seconds = limits.get("max_seconds")
        current_reads = int(ledger.get("read_attempts_reserved", 0) or 0)
        max_reads = limits.get("max_read_attempts")
        reason = ""
        if max_seconds is not None and elapsed >= float(max_seconds):
            reason = "wall_clock_limit"
        elif kind == "read" and max_reads is not None and current_reads + amount > int(max_reads):
            reason = "run_read_limit"
        event = {"schema_version": 1, "timestamp": time.time(), "kind": kind,
                 "amount": amount, "detail": detail, "elapsed_seconds": round(elapsed, 3),
                 "allowed": not bool(reason), "reason": reason}
        _append_jsonl(events_path, event)
        if reason:
            ledger["termination_reason"] = reason
            ledger["terminated_epoch"] = time.time()
            _write_json(ledger_path, ledger)
            if cfg.get("run_id"):
                log_run_event(node, "runtime_reservation", actor="runtime", component="budget",
                              data=event)
            raise SystemExit("runtime hard cap reached (%s); stopped before network I/O" % reason)
        key = "search_attempts" if kind == "search" else "read_attempts_reserved"
        ledger[key] = int(ledger.get(key, 0) or 0) + amount
        ledger["last_event_epoch"] = time.time()
        _write_json(ledger_path, ledger)
        if cfg.get("run_id"):
            log_run_event(node, "runtime_reservation", actor="runtime", component="budget",
                          data=dict(event, reserved_total=ledger[key]))
        return {"enforced": True, "kind": kind, "reserved": ledger[key],
                "elapsed_seconds": round(elapsed, 3)}


def runtime_checkpoint(run_or_node: str, detail: str = "", fail_if_expired: bool = False) -> Dict[str, Any]:
    """Observe wall-clock use outside network I/O, including synthesis and verification.

    Final reporting remains possible after expiry so the user receives an honest partial result, but
    the run is marked terminated and can never be graded as epistemically complete.
    """
    candidate = os.path.abspath(run_or_node)
    run = candidate if os.path.isfile(os.path.join(candidate, "run.json")) else _find_run(candidate)
    if not run:
        return {"enforced": False}
    cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
    ledger_path = os.path.join(run, "runtime-ledger.json")
    lock_path = os.path.join(run, ".runtime-ledger.lock")
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        ledger = _read_json(ledger_path, {}) or {}
        now = time.time()
        started = float(ledger.get("started_epoch") or cfg.get("started_epoch") or now)
        elapsed = max(0.0, now - started)
        maximum = float((cfg.get("limits") or {}).get("max_seconds") or ABS_MAX_SECONDS)
        expired = elapsed >= maximum
        if expired:
            ledger["termination_reason"] = ledger.get("termination_reason") or "wall_clock_limit"
            ledger["terminated_epoch"] = ledger.get("terminated_epoch") or now
        ledger["last_checkpoint_epoch"] = now
        ledger["last_elapsed_seconds"] = round(elapsed, 3)
        _write_json(ledger_path, ledger)
    payload = {"detail": detail, "elapsed_seconds": round(elapsed, 3),
               "max_seconds": maximum, "allowed": not expired,
               "reason": "wall_clock_limit" if expired else ""}
    if cfg.get("run_id"):
        log_run_event(run_or_node, "runtime_checkpoint", actor="runtime", component="budget", data=payload)
    if expired and fail_if_expired:
        raise SystemExit("runtime hard cap reached (wall_clock_limit)")
    return {"enforced": True, **payload}


def _run_cfg(node: str) -> Dict[str, Any]:
    # walk up to find run.json (…/<run>/tree/<path>)
    run = _find_run(node)
    return _read_json(os.path.join(run, "run.json"), {}) or {} if run else {}


def count_nodes(run: str) -> int:
    root = os.path.join(run, "tree")
    return sum(1 for _d, _s, fs in os.walk(root) if "status.json" in fs)


def can_split(node: str) -> Dict[str, Any]:
    """Budget/cap check: may this node split, and into at most how many children?"""
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    cfg = _run_cfg(node)
    budget = float(st.get("budget", 0)); depth = int(st.get("depth", 0))
    U = float(cfg.get("unit", 4)); run = _find_run(node)
    reasons = []
    if depth >= int(cfg.get("max_depth", 3)):
        reasons.append("at max_depth")
    if budget < 2 * U:
        reasons.append("budget<2U (leaf: investigate)")
    remaining = int(cfg.get("max_nodes", 40)) - count_nodes(run) if run else 0
    if run and remaining < 2:
        reasons.append("max_nodes leaves fewer than 2 child slots")
    kmax = int(budget // U) if U > 0 else 0
    kmax = min(kmax, int(cfg.get("max_children", 5)), max(remaining, 0) if run else kmax)
    return {"can_split": not reasons, "max_k": max(kmax, 0), "reasons": reasons,
            "budget": budget, "unit": U, "depth": depth}


def _find_run(node: str) -> str:
    d = os.path.abspath(node)
    while True:
        if os.path.exists(os.path.join(d, "run.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return ""
        d = parent


def split_node(node: str, children: List[List[str]], actor: str = "orchestrator",
               weights: Optional[List[float]] = None) -> List[str]:
    """children = [[qid, question], ...]. Budget is CONSERVED (sum of children = parent budget).

    Allocation: uniform by default (child = budget/K). If `weights` is given (one per child), use a
    two-phase scheme — floor every child to the scrutiny `unit`, then distribute the REMAINDER by
    weight. This is the fix for the audited "equal scrutiny per leaf" flaw: uniform allocation is
    suboptimal (Snell arXiv:2408.03314; UAB arXiv:2605.26849; Anthropic "scale effort to complexity"),
    so contested/uncertain children (higher weight from the scout round) get more, none below the floor."""
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    chk = can_split(node)
    k = len(children)
    if k < 2:
        raise SystemExit("split needs >=2 children")
    if any(not isinstance(child, (list, tuple)) or len(child) != 2 for child in children):
        raise SystemExit("each child must be [qid, question]")
    slugs = [_slugify(str(child[0]), 24) for child in children]
    if len(set(slugs)) != len(slugs):
        raise SystemExit("child qids collide after filesystem slug normalization")
    if not chk["can_split"]:
        raise SystemExit("cannot split (%s); make this a leaf and investigate" % ", ".join(chk["reasons"]))
    if k > chk["max_k"]:
        raise SystemExit("K=%d exceeds max viable %d (would starve children below the scrutiny "
                         "unit). Propose fewer, broader children." % (k, chk["max_k"]))
    B = float(st.get("budget", 0))
    U = float(chk.get("unit", 4) or 4)
    if weights is not None and len(weights) != k:
        raise SystemExit("weights must contain exactly one value per child")
    if weights is not None and sum(w for w in weights if w > 0) <= 0:
        raise SystemExit("weights must include at least one positive value")
    if weights is not None:
        floor = min(U, B / k)                          # guarantee ≥ floor each (no starvation)
        rem = max(0.0, B - floor * k)                  # remainder distributed by contestedness
        tot = sum(max(0.0, w) for w in weights)
        budgets = [round(floor + rem * (max(0.0, w) / tot), 3) for w in weights]
        if rem < 1e-9:                                 # tight budget: the floor eats everything,
            how = ("weighted requested but NO EFFECT (budget %.2f only covers K=%d at the unit "
                   "floor %.2f)" % (B, k, floor))      # so weights cannot apply — say so loudly
            sys.stderr.write("treestate: %s; every child gets the scrutiny unit. Raise budget or "
                             "reduce K to let weights bite.\n" % how)
        else:
            how = "weighted (floor %.2f + remainder by contestedness)" % floor
    else:
        budgets = [round(B / k, 3)] * k
        how = "uniform"
    # Conserve EXACTLY: rounding leaves budgets summing to e.g. 32.001, not B. Fold the residual
    # into the most-scrutinized child — its budget is always strictly > floor when the residual is
    # nonzero, so absorbing ±0.001 can never push a child below the scrutiny-unit floor.
    drift = round(B - sum(budgets), 3)
    if abs(drift) >= 1e-9 and budgets:
        j = max(range(k), key=lambda i: budgets[i])
        budgets[j] = round(budgets[j] + drift, 3)
    depth = int(st.get("depth", 0)) + 1
    made = []
    for (qid, q), cb in zip(children, budgets):
        cdir = os.path.join(node, "children", _slugify(qid, 24))
        _init_node_dir(cdir, qid, q, cb, depth, "worker", st.get("qid"))
        made.append(cdir)
    set_status(node, state="split", children=[c[0] for c in children])
    run = _find_run(node)
    if run and os.path.abspath(node) == os.path.abspath(os.path.join(run, "tree", "root")):
        set_run_state(run, "investigating")
    log_decision(node, actor, "split into %d children (%s)" % (k, how),
                 "budget %.2f -> %s (conserved); depth %d" % (B, [b for b in budgets], depth))
    return made


def propose_split(node: str, children: List[List[str]], why: str = "") -> None:
    """Worker proposes an EVIDENCE-DRIVEN decomposition AFTER a scout round (the dynamic-outline
    model: look, then decide). The orchestrator reviews proposals across the level and materializes
    approved ones — so caps and cross-level balance stay in one place."""
    _write_json(os.path.join(node, "proposal.json"),
                {"t": _now(), "children": children, "why": why})
    set_status(node, state="proposes_split")
    log_decision(node, "worker", "propose split into %d children" % len(children),
                 why or "evidence-driven decomposition")


def materialize_proposal(node: str, actor: str = "orchestrator") -> List[str]:
    """Orchestrator turns an approved proposal.json into real child nodes (split_node enforces the
    budget/cap floor via can_split)."""
    prop = _read_json(os.path.join(node, "proposal.json"), {}) or {}
    children = prop.get("children") or []
    if not children:
        raise SystemExit("no proposal.json (or empty) at %s" % node)
    return split_node(node, children, actor)


def add_sources(node: str, records: List[Dict[str, Any]]) -> int:
    """Append records to this node's sources.jsonl and to the run's global dedup index."""
    for r in records:
        _append_jsonl(os.path.join(node, "sources.jsonl"), r)
    return sync_global_sources(node, records)


def sync_global_sources(node: str, records: List[Dict[str, Any]]) -> int:
    """Locked atomic upsert into the run-wide source index.

    Parallel leaves previously raced on read-then-append dedup, while a later successful read updated
    only the node copy. The global report could therefore disagree with the evidence actually read.
    """
    run = _find_run(node)
    if not run:
        return 0
    idx_path = os.path.join(run, "index", "sources.jsonl")
    lock_path = os.path.join(run, ".sources-index.lock")
    added = 0
    with open(lock_path, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows: List[Dict[str, Any]] = []
        if os.path.exists(idx_path):
            with open(idx_path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(row, dict):
                        rows.append(row)
        by_url = {_canon(row.get("url", "")): i for i, row in enumerate(rows)
                  if _canon(row.get("url", ""))}
        for source in records:
            cu = _canon(source.get("url", ""))
            if not cu:
                continue
            node_rel = os.path.relpath(node, run)
            incoming = dict(source)
            incoming["_node"] = node_rel
            incoming["_nodes"] = [node_rel]
            read_rel = str(source.get("_read_file") or "")
            if read_rel:
                incoming["_read_artifact"] = os.path.relpath(os.path.join(node, read_rel), run)
            if cu not in by_url:
                by_url[cu] = len(rows)
                rows.append(incoming)
                added += 1
                continue
            existing = rows[by_url[cu]]
            nodes = set(existing.get("_nodes") or [existing.get("_node")])
            nodes.discard(None); nodes.discard(""); nodes.add(node_rel)
            existing["_nodes"] = sorted(nodes)
            # Preserve discovery metadata, but promote later proof that this exact source was read.
            for key, value in incoming.items():
                if key.startswith("_read") or key in {"_truncated", "_resolved_url"}:
                    existing[key] = value
                elif key not in existing or existing.get(key) in (None, "", [], {}):
                    existing[key] = value
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        _write_text(idx_path, text)
    cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
    if cfg.get("run_id"):
        log_run_event(node, "source_index_updated", actor="runtime", component="provenance",
                      data={"records": len(records), "new_canonical_urls": added,
                            "index_rows": len(rows)})
    return added


def _canon(url: str) -> str:
    if not url:
        return ""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                        "provenance-audit", "scripts"))
        import dedupe  # type: ignore
        return dedupe.canonical_url(url)
    except Exception:  # noqa: BLE001
        return url.split("#")[0].rstrip("/").lower()


def write_findings(node: str, text: str) -> None:
    run = _find_run(node)
    is_root = bool(run and os.path.abspath(node) == os.path.abspath(os.path.join(run, "tree", "root")))
    ledger_gate: Dict[str, Any] = {"epistemically_complete": True}
    if is_root:
        cfg = _read_json(os.path.join(run, "run.json"), {}) or {}
        strict = (str(cfg.get("version") or "").startswith("aletheia-research-accuracy ")
                  and cfg.get("thoroughness") in {"accuracy", "unlimited", "max"})
        if strict:
            ledger_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ledger.py")
            try:
                ledger_gate = json.loads(subprocess.check_output(
                    [sys.executable, ledger_script, "audit", "--run", run], text=True))
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                raise SystemExit("cannot audit claim ledger before root synthesis: %s" %
                                 type(exc).__name__) from exc
            if (ledger_gate.get("epistemically_complete") is not True
                    and not ledger_gate.get("termination_reason")):
                raise SystemExit("root synthesis blocked: claim ledger is unresolved and has no "
                                 "explicit termination (%s)" %
                                 "; ".join(ledger_gate.get("blockers") or ["unknown blocker"]))
    path = os.path.join(node, "findings.md")
    payload = text.rstrip() + "\n"
    _write_text(path, payload)
    if run:
        log_run_event(node, "artifact_written", actor="worker", component="synthesis",
                      data={"artifact": os.path.relpath(path, run),
                            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                            "bytes": len(payload.encode("utf-8"))})
    root_state = ("synthesized" if ledger_gate.get("epistemically_complete") is True
                  else "synthesized_with_gaps")
    set_status(node, state=root_state if is_root else "investigated")
    if is_root:
        set_run_state(run, root_state, actor="orchestrator",
                      reason=ledger_gate.get("termination_reason") or "claim ledger complete")


def ask(child_node: str, from_node: str, question: str) -> str:
    with open(os.path.join(child_node, "questions.jsonl"), encoding="utf-8") as fh:
        qid = "q%d" % (sum(1 for _ in fh) + 1)
    _append_jsonl(os.path.join(child_node, "questions.jsonl"),
                  {"qid": qid, "t": _now(), "from": from_node, "question": question, "answered": False})
    set_status(child_node, state="needs_answer")
    log_decision(child_node, "parent:%s" % from_node, "asked: %s" % question[:80], "top-down clarification")
    return qid


def answer(node: str, qid: str, text: str) -> None:
    _append_jsonl(os.path.join(node, "answers.jsonl"),
                  {"qid": qid, "t": _now(), "answer": text})
    # mark the matching question answered
    qpath = os.path.join(node, "questions.jsonl")
    if os.path.exists(qpath):
        with open(qpath, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
        for row in rows:
            if row.get("qid") == qid:
                row["answered"] = True
        with open(qpath, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
    set_status(node, state="answered")


#: states that still have work — a resumable frontier re-picks all of these after a crash/interrupt.
#: `active` is the key one: a node that died mid-round is left `state=active`, and a plain
#: `--state pending` scan silently SKIPS it (the audited resumability bug — audit rec #6).
_RESUMABLE_STATES = ("pending", "active", "needs_answer", "proposes_split")


def frontier(run: str, state: str = "pending", depth: Optional[int] = None,
             resumable: bool = False) -> List[str]:
    """Nodes with work left; with --depth D, only that level (for level-by-level processing).
    `resumable=True` ignores `state` and returns every node still needing work — pending PLUS
    crashed-mid-round `active`, unanswered `needs_answer`, and un-materialized `proposes_split` —
    so re-running after an interrupt picks up exactly what didn't finish, with no silent skips."""
    want = set(_RESUMABLE_STATES) if resumable else {state}
    out = []
    for d, _s, fs in os.walk(os.path.join(run, "tree")):
        if "status.json" in fs:
            st = _read_json(os.path.join(d, "status.json"), {}) or {}
            if st.get("state") in want and (depth is None or int(st.get("depth", 0)) == depth):
                out.append(d)
    out.sort(key=lambda p: (_read_json(os.path.join(p, "status.json"), {}).get("depth", 0), p))
    return out


def tree_view(run: str) -> str:
    lines = []
    root = os.path.join(run, "tree", "root")

    def walk(node: str):
        st = _read_json(os.path.join(node, "status.json"), {}) or {}
        indent = "  " * int(st.get("depth", 0))
        fpath = os.path.join(node, "findings.md")
        has_find = "*" if os.path.exists(fpath) and os.path.getsize(fpath) > 0 else " "
        lines.append("%s- [%s]%s %s  (b=%.1f d=%d)  %s" % (
            indent, st.get("state", "?"), has_find, st.get("qid", "?"),
            st.get("budget", 0), st.get("depth", 0),
            (st.get("question", "") or "")[:60]))
        cdir = os.path.join(node, "children")
        if os.path.isdir(cdir):
            for c in sorted(os.listdir(cdir)):
                if os.path.isdir(os.path.join(cdir, c)):
                    walk(os.path.join(cdir, c))
    if os.path.isdir(root):
        walk(root)
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia filesystem tree state.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("topic")
    p.add_argument("--slug", default=""); p.add_argument("--budget", type=float, default=None,
                   help="explicit budget = a CUSTOM bounded run; omit for the `accuracy` default")
    p.add_argument("--unit", type=float, default=4.0); p.add_argument("--max-depth", type=int, default=3)
    p.add_argument("--max-children", type=int, default=5); p.add_argument("--max-nodes", type=int, default=40)
    p.add_argument("--base", default="runs/aletheia-research-accuracy")
    p.add_argument("--thoroughness", default="",
                   choices=sorted(THOROUGHNESS),
                   help="accuracy(default)|quick|standard|deep|exhaustive|unlimited|max")
    p.add_argument("--verbosity", default="user", choices=["user", "agent"],
                   help="agent = emit the FULL bundle for a calling agent; user = a multi-page summary")
    p.add_argument("--reads-per-round", type=int, default=None,
                   help="decoupled per-round read ceiling (default derives from the scrutiny unit)")
    p.add_argument("--max-read-attempts", type=int, default=None,
                   help="run-wide hard ceiling; failed/crashed reserved attempts still count")
    p.add_argument("--max-seconds", type=float, default=None,
                   help="wall-clock hard ceiling checked before every search/read")

    p = sub.add_parser("split"); p.add_argument("--node", required=True)
    p.add_argument("--children", required=True, help='JSON: [["qid","question"],...]')
    p.add_argument("--actor", default="orchestrator")
    p.add_argument("--weights", default="", help='JSON list of per-child contestedness weights, '
                   'e.g. "[3,1,2]" — higher = more scrutiny budget (floored at the scrutiny unit). '
                   "Omit for a uniform split.")

    p = sub.add_parser("cansplit"); p.add_argument("--node", required=True)

    p = sub.add_parser("propose"); p.add_argument("--node", required=True)
    p.add_argument("--children", required=True, help='JSON: [["qid","question"],...]')
    p.add_argument("--why", default="")

    p = sub.add_parser("materialize"); p.add_argument("--node", required=True)
    p.add_argument("--actor", default="orchestrator")

    p = sub.add_parser("decide"); p.add_argument("decision")
    p.add_argument("--node", required=True); p.add_argument("--actor", default="worker")
    p.add_argument("--why", default="")

    p = sub.add_parser("status"); p.add_argument("--node", required=True)
    p.add_argument("--set", default=""); p.add_argument("--field", action="append", default=[])

    p = sub.add_parser("ask"); p.add_argument("--node", required=True)
    p.add_argument("--from", dest="frm", required=True); p.add_argument("--q", required=True)

    p = sub.add_parser("answer"); p.add_argument("--node", required=True)
    p.add_argument("--qid", required=True); p.add_argument("--a", required=True)

    p = sub.add_parser("findings"); p.add_argument("--node", required=True)
    p.add_argument("--text", default=""); p.add_argument("--file", default="")

    p = sub.add_parser("frontier"); p.add_argument("--run", required=True)
    p.add_argument("--state", default="pending"); p.add_argument("--depth", type=int, default=None)
    p.add_argument("--resumable", action="store_true",
                   help="return ALL nodes still needing work (pending+active+needs_answer+"
                   "proposes_split) — use after a crash/interrupt so mid-round nodes aren't skipped")

    p = sub.add_parser("tree"); p.add_argument("--run", required=True)

    p = sub.add_parser("audit-log"); p.add_argument("--run", required=True)

    p = sub.add_parser("log"); p.add_argument("--run", required=True)
    p.add_argument("--event", required=True); p.add_argument("--actor", default="orchestrator")
    p.add_argument("--component", default="orchestrator"); p.add_argument("--node", default="")
    p.add_argument("--correlation-id", default="")
    p.add_argument("--data", default="{}", help="JSON object with event-specific fields")

    p = sub.add_parser("checkpoint"); p.add_argument("--run", required=True)
    p.add_argument("--detail", default=""); p.add_argument("--fail-if-expired", action="store_true")

    p = sub.add_parser("artifact"); p.add_argument("--run", required=True)
    p.add_argument("--path", required=True); p.add_argument("--actor", default="orchestrator")
    p.add_argument("--kind", default="artifact")

    args = ap.parse_args(argv)

    if args.cmd == "init":
        run = init_run(args.topic, args.slug, args.budget, args.unit, args.max_depth,
                       args.max_children, args.max_nodes, args.base, args.thoroughness,
                       args.verbosity, args.reads_per_round, args.max_read_attempts,
                       args.max_seconds)
        print(run)
    elif args.cmd == "cansplit":
        print(json.dumps(can_split(args.node), indent=2))
    elif args.cmd == "split":
        wts = json.loads(args.weights) if args.weights.strip() else None
        for d in split_node(args.node, json.loads(args.children), args.actor, wts):
            print(d)
    elif args.cmd == "propose":
        propose_split(args.node, json.loads(args.children), args.why)
    elif args.cmd == "materialize":
        for d in materialize_proposal(args.node, args.actor):
            print(d)
    elif args.cmd == "decide":
        log_decision(args.node, args.actor, args.decision, args.why)
    elif args.cmd == "status":
        fields = dict(kv.split("=", 1) for kv in args.field)
        print(json.dumps(set_status(args.node, args.set or None, **fields)))
    elif args.cmd == "ask":
        print(ask(args.node, args.frm, args.q))
    elif args.cmd == "answer":
        answer(args.node, args.qid, args.a)
    elif args.cmd == "findings":
        if args.file:
            with open(args.file, encoding="utf-8") as fh:
                txt = fh.read()
        else:
            txt = args.text
        write_findings(args.node, txt)
    elif args.cmd == "frontier":
        for d in frontier(args.run, args.state, args.depth, args.resumable):
            print(d)
    elif args.cmd == "tree":
        print(tree_view(args.run))
    elif args.cmd == "audit-log":
        print(json.dumps(audit_run_events(args.run), indent=2, sort_keys=True))
    elif args.cmd == "log":
        data = json.loads(args.data)
        if not isinstance(data, dict):
            raise SystemExit("--data must decode to a JSON object")
        print(json.dumps(log_run_event(args.run, args.event, args.actor, args.component, data,
                                       args.node, args.correlation_id), indent=2, sort_keys=True))
    elif args.cmd == "checkpoint":
        print(json.dumps(runtime_checkpoint(args.run, args.detail, args.fail_if_expired),
                         indent=2, sort_keys=True))
    elif args.cmd == "artifact":
        print(json.dumps(record_artifact(args.run, args.path, args.actor, args.kind),
                         indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
