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
  runs/aletheia-research/<ts>-<slug>/
    run.json  portfolio.md  brief.md  verify.jsonl
    index/sources.jsonl                      (global dedup / independence)
    tree/root/{spec.md,status.json,decisions.jsonl,questions.jsonl,answers.jsonl,
               sources.jsonl,notes/,findings.md,children/<qid>/...}

CLI (used by the orchestrator skill + subagents):
  treestate.py init "<topic>" [--slug s] [--thoroughness quick|standard|deep|exhaustive|unlimited|max]
               [--verbosity user|agent] [--budget N (explicit = custom bounded run)]
               # default (no tier, no budget) = `unlimited`: unbounded depth/budget, stop on saturation
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
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

NODE_FILES = ("decisions.jsonl", "questions.jsonl", "answers.jsonl", "sources.jsonl")


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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj) + "\n")


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


def set_status(node: str, state: Optional[str] = None, **fields: Any) -> Dict[str, Any]:
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    if state:
        st["state"] = state
    for k, v in fields.items():
        st[k] = v
    st["updated"] = _now()
    _write_json(os.path.join(node, "status.json"), st)
    return st


def set_run_state(run: str, state: str) -> Dict[str, Any]:
    """Persist the run lifecycle; node status alone is not enough for resume/observability."""
    path = os.path.join(run, "run.json")
    cfg = _read_json(path, {}) or {}
    cfg["state"] = state
    cfg["updated"] = _now()
    _write_json(path, cfg)
    return cfg


def log_decision(node: str, actor: str, decision: str, why: str = "") -> None:
    _append_jsonl(os.path.join(node, "decisions.jsonl"),
                  {"t": _now(), "actor": actor, "decision": decision, "why": why})


# ---------------------------------------------------------------- run + tree
# Thoroughness dial (callable/scaled from any session; scales effort to the question). It sets the
# tree's budget/caps — deeper tiers spend more and split wider. `auto` = the agent picks it in SCOPE.
#: Tiers. `unlimited` is the DEFAULT: budget/depth are effectively unbounded so the stop is no longer
#: budget-exhaustion but AGENT-PACED CONVERGENCE — the orchestrator keeps splitting/deepening until a
#: branch is saturated (no new distinct origins/claims). A high `max_nodes` remains as the one safety
#: backstop (Anthropic's 50-subagent failure) — raise it, don't rely on it. The bounded tiers stay for
#: when speed matters. `max` is the "proper flag": the same unbounded caps but run maximally (more
#: framings, more redundancy, deeper verification) — the ~week-of-searching target vs unlimited's ~day.
_BIG = 1_000_000.0
THOROUGHNESS = {
    "quick":      dict(budget=8.0,  unit=4.0, max_depth=1, max_children=3, max_nodes=8),
    "standard":   dict(budget=16.0, unit=4.0, max_depth=2, max_children=3, max_nodes=16),
    "deep":       dict(budget=32.0, unit=4.0, max_depth=3, max_children=4, max_nodes=40),
    "exhaustive": dict(budget=64.0, unit=4.0, max_depth=3, max_children=5, max_nodes=64),
    "unlimited":  dict(budget=_BIG, unit=4.0, max_depth=99, max_children=6, max_nodes=512),
    "max":        dict(budget=_BIG, unit=4.0, max_depth=99, max_children=8, max_nodes=2048),
}


def init_run(topic: str, slug: str = "", budget: Optional[float] = None, unit: float = 4.0,
             max_depth: int = 3, max_children: int = 5, max_nodes: int = 40,
             base: str = "runs/aletheia-research", thoroughness: str = "",
             verbosity: str = "user") -> str:
    if not str(topic).strip():
        raise ValueError("topic must not be empty")
    if thoroughness and thoroughness not in THOROUGHNESS:
        raise ValueError("unknown thoroughness %r" % thoroughness)
    if budget is not None and budget <= 0:
        raise ValueError("budget must be positive")
    if unit <= 0:
        raise ValueError("unit must be positive")
    # Resolution: a named tier wins; else an EXPLICIT budget means custom (honored, for bounded/
    # programmatic runs); else — nothing specified — default to `unlimited` (the new default).
    if thoroughness in THOROUGHNESS:
        tier = thoroughness
    elif budget is None:
        tier = "unlimited"
    else:
        tier = thoroughness or "custom"
    if tier in THOROUGHNESS:              # tier overrides budget/caps
        t = THOROUGHNESS[tier]
        budget, unit = t["budget"], t["unit"]
        max_depth, max_children, max_nodes = t["max_depth"], t["max_children"], t["max_nodes"]
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
    _write_json(os.path.join(run, "run.json"), {
        "topic": topic, "created": _now(), "version": "aletheia-research 0.5.0-dev2",
        "implementation": _implementation_metadata(),
        "thoroughness": tier, "verbosity": verbosity,
        "budget": budget, "unit": unit, "max_depth": max_depth,
        "max_children": max_children, "max_nodes": max_nodes, "state": "framing",
    })
    with open(os.path.join(run, "portfolio.md"), "w", encoding="utf-8") as fh:
        fh.write("# Hypothesis portfolio — %s\n\n_(orchestrator writes 4-6 competing "
                 "framings here before any search)_\n" % topic)
    open(os.path.join(run, "index", "sources.jsonl"), "a", encoding="utf-8").close()
    _init_node_dir(os.path.join(run, "tree", "root"), "root", topic, budget, 0, "root", None)
    return run


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
    run = _find_run(node)
    idx_path = os.path.join(run, "index", "sources.jsonl") if run else ""
    seen = set()
    if idx_path and os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        seen.add(_canon(row.get("url", "")))
                except ValueError:
                    pass
    added = 0
    for r in records:
        _append_jsonl(os.path.join(node, "sources.jsonl"), r)
        cu = _canon(r.get("url", ""))
        if idx_path and cu and cu not in seen:
            seen.add(cu)
            rec = dict(r); rec["_node"] = os.path.relpath(node, run)
            _append_jsonl(idx_path, rec)
            added += 1
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
    with open(os.path.join(node, "findings.md"), "w", encoding="utf-8") as fh:
        fh.write(text.rstrip() + "\n")
    run = _find_run(node)
    is_root = bool(run and os.path.abspath(node) == os.path.abspath(os.path.join(run, "tree", "root")))
    set_status(node, state="synthesized" if is_root else "investigated")
    if is_root:
        set_run_state(run, "synthesized")


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
                   help="explicit budget = a CUSTOM bounded run; omit for the `unlimited` default")
    p.add_argument("--unit", type=float, default=4.0); p.add_argument("--max-depth", type=int, default=3)
    p.add_argument("--max-children", type=int, default=5); p.add_argument("--max-nodes", type=int, default=40)
    p.add_argument("--base", default="runs/aletheia-research")
    p.add_argument("--thoroughness", default="",
                   choices=sorted(THOROUGHNESS),
                   help="quick|standard|deep|exhaustive|unlimited(default)|max (overrides budget/caps)")
    p.add_argument("--verbosity", default="user", choices=["user", "agent"],
                   help="agent = emit the FULL bundle for a calling agent; user = a multi-page summary")

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

    args = ap.parse_args(argv)

    if args.cmd == "init":
        run = init_run(args.topic, args.slug, args.budget, args.unit, args.max_depth,
                       args.max_children, args.max_nodes, args.base, args.thoroughness,
                       args.verbosity)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
