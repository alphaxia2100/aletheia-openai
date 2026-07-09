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
  report.py bundle  --run RUN_DIR [--reads] [--max-chars N]
  report.py outline --run RUN_DIR
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import treestate  # noqa: E402


def _read(p: str, default: str = "") -> str:
    # errors="replace": the bundle must robustly hand back EVERY artifact — a single stray non-UTF-8
    # byte (corrupt/hand-edited/cross-system file) must not abort the whole pack into an empty result.
    try:
        return open(p, encoding="utf-8", errors="replace").read()
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
    L.append("")
    L.append("This is the COMPLETE research artifact set — not a summary. Every node's findings and "
             "evidence are included verbatim so no nuance is lost. Read it in full; cite the primaries.")
    L.append("")
    L.append("## Portfolio (competing framings)")
    L.append(_read(os.path.join(run, "portfolio.md"), "_(none)_"))
    L.append("")
    L.append(treestate.tree_view(run))
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
            if os.path.isdir(notes_dir):
                for fn in sorted(os.listdir(notes_dir)):
                    if not fn.endswith(".md"):
                        continue
                    body = _read(os.path.join(notes_dir, fn))
                    if max_chars and len(body) > max_chars:
                        body = body[:max_chars] + "\n…[truncated]"
                    L.append("#### read primary — notes/%s" % fn)
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
        n_notes = (len([f for f in os.listdir(notes_dir) if f.endswith(".md")])  # match bundle --reads
                   if os.path.isdir(notes_dir) else 0)
        L.append("- `%s` [%s] — %s | %d read primaries" % (rel, st.get("qid", ""), ", ".join(arts), n_notes))
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia Research output assembler (verbosity dial).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bundle"); b.add_argument("--run", required=True)
    b.add_argument("--reads", action="store_true", help="inline the primaries read in full (notes/*.md)")
    b.add_argument("--max-chars", type=int, default=0, help="truncate each read to N chars (0 = no cap)")
    o = sub.add_parser("outline"); o.add_argument("--run", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "bundle":
        print(bundle(args.run, args.reads, args.max_chars))
    elif args.cmd == "outline":
        print(outline(args.run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
