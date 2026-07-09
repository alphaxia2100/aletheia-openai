#!/usr/bin/env python3
"""Deep Aletheia — filesystem-as-blackboard tree state.

Every agent node in a Deep Aletheia run is a DIRECTORY. All coordination is files, so
nothing depends on a single context window: state survives on disk (resumable, auditable),
findings flow UP (findings.md), clarifications flow DOWN (questions.jsonl/answers.jsonl),
and each agent keeps a reasoning log (decisions.jsonl).

Budget model ("equal time per level" + "equal scrutiny per leaf"):
  A node holds a numeric BUDGET. Splitting into K children gives each budget/K — budget is
  CONSERVED across a split. Recurse while budget/K >= U (the scrutiny unit); otherwise the
  node is a LEAF that spends its budget investigating. For a balanced tree this makes every
  level sum to ~budget_root (equal effort/level) and every leaf get ~U (equal scrutiny).
  Hard caps (max_depth/max_children/max_nodes) bound fan-out.

Layout:
  runs/deep/<ts>-<slug>/
    run.json  portfolio.md  brief.md  verify.jsonl
    index/sources.jsonl                      (global dedup / independence)
    tree/root/{spec.md,status.json,decisions.jsonl,questions.jsonl,answers.jsonl,
               sources.jsonl,notes/,findings.md,children/<qid>/...}

CLI (used by the orchestrator skill + subagents):
  treestate.py init "<topic>" [--slug s] [--budget 32] [--unit 4] [--max-depth 3]
               [--max-children 5] [--max-nodes 40]
  treestate.py split  --node DIR --children '[["q1","question one"],["q2","..."]]'
  treestate.py decide --node DIR --actor NAME --why "..." "<decision>"
  treestate.py status --node DIR [--set state] [--field k=v ...]
  treestate.py ask    --node CHILD_DIR --from PARENT --q "specific question"
  treestate.py answer --node DIR --qid QID --a "answer text"
  treestate.py findings --node DIR --text "..."   (or --file f)
  treestate.py frontier --run RUNDIR [--state pending]
  treestate.py tree   --run RUNDIR
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

NODE_FILES = ("decisions.jsonl", "questions.jsonl", "answers.jsonl", "sources.jsonl")


def _now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").lower()).strip("-")
    return (s[:n].strip("-") or "run")


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


def log_decision(node: str, actor: str, decision: str, why: str = "") -> None:
    _append_jsonl(os.path.join(node, "decisions.jsonl"),
                  {"t": _now(), "actor": actor, "decision": decision, "why": why})


# ---------------------------------------------------------------- run + tree
# Thoroughness dial (callable/scaled from any session; scales effort to the question). It sets the
# tree's budget/caps — deeper tiers spend more and split wider. `auto` = the agent picks it in SCOPE.
THOROUGHNESS = {
    "quick":      dict(budget=8.0,  unit=4.0, max_depth=1, max_children=3, max_nodes=8),
    "standard":   dict(budget=16.0, unit=4.0, max_depth=2, max_children=3, max_nodes=16),
    "deep":       dict(budget=32.0, unit=4.0, max_depth=3, max_children=4, max_nodes=40),
    "exhaustive": dict(budget=64.0, unit=4.0, max_depth=3, max_children=5, max_nodes=64),
}


def init_run(topic: str, slug: str = "", budget: float = 32.0, unit: float = 4.0,
             max_depth: int = 3, max_children: int = 5, max_nodes: int = 40,
             base: str = "runs/aletheia-research", thoroughness: str = "") -> str:
    tier = thoroughness if thoroughness in THOROUGHNESS else ""
    if tier:  # tier overrides the budget/caps
        t = THOROUGHNESS[tier]
        budget, unit = t["budget"], t["unit"]
        max_depth, max_children, max_nodes = t["max_depth"], t["max_children"], t["max_nodes"]
    ts = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    run = os.path.join(base, "%s-%s" % (ts, _slugify(slug or topic)))
    os.makedirs(os.path.join(run, "index"), exist_ok=True)
    _write_json(os.path.join(run, "run.json"), {
        "topic": topic, "created": _now(), "version": "aletheia-research 0.3.0",
        "thoroughness": tier or (thoroughness or "custom"),
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
    d = os.path.abspath(node)
    while d != "/" and not os.path.exists(os.path.join(d, "run.json")):
        d = os.path.dirname(d)
    return _read_json(os.path.join(d, "run.json"), {}) or {}


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
    if run and count_nodes(run) >= int(cfg.get("max_nodes", 40)):
        reasons.append("at max_nodes")
    kmax = int(budget // U) if U > 0 else 0
    kmax = min(kmax, int(cfg.get("max_children", 5)))
    return {"can_split": not reasons, "max_k": max(kmax, 0), "reasons": reasons,
            "budget": budget, "unit": U, "depth": depth}


def _find_run(node: str) -> str:
    d = os.path.abspath(node)
    while d != "/" and not os.path.exists(os.path.join(d, "run.json")):
        d = os.path.dirname(d)
    return d if os.path.exists(os.path.join(d, "run.json")) else ""


def split_node(node: str, children: List[List[str]], actor: str = "orchestrator") -> List[str]:
    """children = [[qid, question], ...]. Budget is CONSERVED: each child gets budget/K."""
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    chk = can_split(node)
    k = len(children)
    if k < 1:
        raise SystemExit("split needs >=1 child")
    if not chk["can_split"]:
        raise SystemExit("cannot split (%s); make this a leaf and investigate" % ", ".join(chk["reasons"]))
    if k > chk["max_k"]:
        raise SystemExit("K=%d exceeds max viable %d (would starve children below the scrutiny "
                         "unit). Propose fewer, broader children." % (k, chk["max_k"]))
    child_budget = float(st.get("budget", 0)) / k
    depth = int(st.get("depth", 0)) + 1
    made = []
    for qid, q in children:
        cdir = os.path.join(node, "children", _slugify(qid, 24))
        _init_node_dir(cdir, qid, q, child_budget, depth, "worker", st.get("qid"))
        made.append(cdir)
    set_status(node, state="split", children=[c[0] for c in children])
    log_decision(node, actor, "split into %d children" % k,
                 "budget %.2f -> %.2f each (conserved); depth %d" % (st.get("budget", 0), child_budget, depth))
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
        for line in open(idx_path, encoding="utf-8"):
            try:
                seen.add(_canon(json.loads(line).get("url", "")))
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
    set_status(node, state="investigated")


def ask(child_node: str, from_node: str, question: str) -> str:
    qid = "q%d" % (sum(1 for _ in open(os.path.join(child_node, "questions.jsonl"),
                                       encoding="utf-8")) + 1)
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
        rows = [json.loads(l) for l in open(qpath, encoding="utf-8") if l.strip()]
        for row in rows:
            if row.get("qid") == qid:
                row["answered"] = True
        with open(qpath, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
    set_status(node, state="answered")


def frontier(run: str, state: str = "pending", depth: Optional[int] = None) -> List[str]:
    """Nodes in a given state; with --depth D, only that level (for level-by-level processing =
    'equal time per level')."""
    out = []
    for d, _s, fs in os.walk(os.path.join(run, "tree")):
        if "status.json" in fs:
            st = _read_json(os.path.join(d, "status.json"), {}) or {}
            if st.get("state") == state and (depth is None or int(st.get("depth", 0)) == depth):
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
    p.add_argument("--slug", default=""); p.add_argument("--budget", type=float, default=32.0)
    p.add_argument("--unit", type=float, default=4.0); p.add_argument("--max-depth", type=int, default=3)
    p.add_argument("--max-children", type=int, default=5); p.add_argument("--max-nodes", type=int, default=40)
    p.add_argument("--base", default="runs/aletheia-research")
    p.add_argument("--thoroughness", default="", help="quick|standard|deep|exhaustive (overrides budget/caps)")

    p = sub.add_parser("split"); p.add_argument("--node", required=True)
    p.add_argument("--children", required=True, help='JSON: [["qid","question"],...]')
    p.add_argument("--actor", default="orchestrator")

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

    p = sub.add_parser("tree"); p.add_argument("--run", required=True)

    args = ap.parse_args(argv)

    if args.cmd == "init":
        run = init_run(args.topic, args.slug, args.budget, args.unit, args.max_depth,
                       args.max_children, args.max_nodes, args.base, args.thoroughness)
        print(run)
    elif args.cmd == "cansplit":
        print(json.dumps(can_split(args.node), indent=2))
    elif args.cmd == "split":
        for d in split_node(args.node, json.loads(args.children), args.actor):
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
        txt = open(args.file, encoding="utf-8").read() if args.file else args.text
        write_findings(args.node, txt)
    elif args.cmd == "frontier":
        for d in frontier(args.run, args.state, args.depth):
            print(d)
    elif args.cmd == "tree":
        print(tree_view(args.run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
