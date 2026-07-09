#!/usr/bin/env python3
"""Deep Aletheia — synthesis helper (bottom-up merge + independence).

Synthesis PROSE is authored by the single-threaded orchestrator (Cognition: one context sees
all). This helper does the deterministic prep so that authoring is grounded:
  - gathers direct children's questions + findings.md (what bubbles up),
  - computes INDEPENDENCE over the node's whole subtree of sources (echo ratio via voice_key,
    unique voices/domains/index-groups, class mix, concentration) — the "40 blogs, 1 origin"
    check, done over the tree instead of by eye,
  - flags children that returned thin/no findings (candidates for a top-down clarification).
Writes <node>/synthesis_input.md for the orchestrator to turn into <node>/findings.md.

Usage:  synthesize.py --node NODE_DIR
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
sys.path.insert(0, PROV)
import dedupe  # noqa: E402


def _read_json(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


def _load_jsonl(p) -> List[Dict[str, Any]]:
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def _answered(child: str) -> bool:
    """A child is 'resolved' once it has recorded at least one answer to a parent's question."""
    ap = os.path.join(child, "answers.jsonl")
    return os.path.exists(ap) and any(l.strip() for l in open(ap, encoding="utf-8"))


def children(node: str) -> List[str]:
    cdir = os.path.join(node, "children")
    if not os.path.isdir(cdir):
        return []
    return [os.path.join(cdir, c) for c in sorted(os.listdir(cdir))
            if os.path.isdir(os.path.join(cdir, c))]


def subtree_sources(node: str) -> List[Dict[str, Any]]:
    recs = _load_jsonl(os.path.join(node, "sources.jsonl"))
    for c in children(node):
        recs += subtree_sources(c)
    return recs


def independence(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"n": 0, "voices": 0, "echo_ratio": 0, "domains": 0, "index_groups": 0,
                "top_domain_share": 0, "class_breakdown": {}}
    voices = {dedupe.voice_key(r) for r in records}
    domains = Counter(dedupe.registrable_domain(r.get("url", "")) for r in records if r.get("url"))
    groups = Counter(r.get("_index_group") or r.get("index_of_origin") for r in records)
    classes = Counter(r.get("_class") or r.get("channel_class") or "?" for r in records)
    return {
        "n": len(records), "voices": len(voices),
        "echo_ratio": round(1 - len(voices) / len(records), 3),
        "domains": len(domains),
        "top_domain_share": round(domains.most_common(1)[0][1] / sum(domains.values()), 3) if domains else 0,
        "index_groups": len(groups), "class_breakdown": dict(classes),
    }


def synthesis_input(node: str) -> Dict[str, Any]:
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    kids = children(node)
    child_blocks, thin, unresolved = [], [], []
    for c in kids:
        cst = _read_json(os.path.join(c, "status.json"), {}) or {}
        qid = cst.get("qid", os.path.basename(c))
        fpath = os.path.join(c, "findings.md")
        ftext = open(fpath, encoding="utf-8").read().strip() if os.path.exists(fpath) else ""
        child_blocks.append((qid, cst.get("question", ""), ftext))
        if len(ftext) < 120:
            thin.append(qid)
            if not _answered(c):                 # thin AND never asked/answered -> gate blocks
                unresolved.append(qid)
    indep = independence(subtree_sources(node))

    lines = ["# Synthesis input — %s" % st.get("qid", "node"), "",
             "**Question:** %s" % st.get("question", ""), "",
             "## Independence (subtree)", "```", json.dumps(indep, indent=2), "```"]
    if indep["echo_ratio"] >= 0.4 or indep["top_domain_share"] >= 0.4:
        lines.append("> ⚠ high echo / concentration — treat convergence with suspicion; "
                     "trace to independent origins before calling it Agreement.")
    if unresolved:
        lines += ["", "## BLOCKED — ask before authoring (back-and-forth, not assumption)",
                  "These children are thin AND unanswered. Do NOT write findings.md yet — ask each "
                  "(`treestate ask --node <child> --from %s --q \"...\"`) and let it answer from its "
                  "already-gathered sources (`treestate answer`):" % st.get("qid", "parent"),
                  ", ".join(unresolved), ""]
    lines += ["", "## Children findings (bubble up)", ""]
    for qid, q, ftext in child_blocks:
        lines += ["### %s — %s" % (qid, q), ftext or "_(no findings yet)_", ""]
    if thin:
        lines += ["## Thin children (consider a top-down clarification via treestate ask)",
                  ", ".join(thin), ""]
    with open(os.path.join(node, "synthesis_input.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"node": node, "children": len(kids), "thin": thin, "unresolved": unresolved,
            "independence": indep}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia synthesis helper.")
    ap.add_argument("--node", required=True)
    ap.add_argument("--gate", action="store_true",
                    help="exit 3 if any child is thin AND unanswered (enforce ask-before-authoring)")
    args = ap.parse_args(argv)
    res = synthesis_input(args.node)
    print(json.dumps(res, indent=2))
    if args.gate and res.get("unresolved"):
        sys.stderr.write("BLOCKED: thin+unanswered children: %s — ask them before authoring findings.\n"
                         % ", ".join(res["unresolved"]))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
