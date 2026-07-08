#!/usr/bin/env python3
"""Iterative-deepening loop controller (breadth x depth + reflection).

The mechanism behind real deep-research (dzhng/deep-research): search the current
frontier, extract LEARNINGS and FOLLOW-UP questions, then recurse into the gaps
with a decaying breadth. This script owns the STATE — query dedup, visited
tracking, breadth decay, and the stop decision — so the agent only does the LLM
parts (generating queries, extracting learnings). It does not call any network.

Flow:
  deepen.py init  STATE --query "..." [--breadth 4] [--depth 2]
  # agent searches state.frontier, then:
  deepen.py record STATE --learning "..." [--learning ...] --followup "..." [--followup ...]
  deepen.py next   STATE     # prints next frontier (deduped, breadth-decayed); exit 3 = STOP
  deepen.py status STATE

Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from typing import Any, Dict, List


def _norm(q: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()


def _load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)


def allowed_for_level(breadth: int, level: int) -> int:
    # level 1 uses full breadth; each deeper level halves it (dzhng-style decay)
    return max(1, math.ceil(breadth / (2 ** max(0, level - 1))))


def cmd_init(args: argparse.Namespace) -> int:
    state = {
        "query": args.query,
        "breadth": args.breadth,
        "depth": args.depth,
        "level": 0,
        "frontier": [args.query],
        "visited": [_norm(args.query)],
        "pending": [],
        "learnings": [],
    }
    _save(args.state, state)
    sys.stdout.write("initialized level 0, frontier: %s\n" % args.query)
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    state = _load(args.state)
    stored = 0
    for l in (args.learning or []):
        if l.strip():
            state["learnings"].append({"level": state["level"], "text": l.strip()})
            stored += 1
    added = 0
    for f in (args.followup or []):
        n = _norm(f)
        if n and n not in state["visited"] and n not in [_norm(p) for p in state["pending"]]:
            state["pending"].append(f.strip())
            added += 1
    _save(args.state, state)
    sys.stdout.write("recorded %d learnings, %d novel follow-ups (pending=%d)\n"
                     % (stored, added, len(state["pending"])))
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    state = _load(args.state)
    if state["level"] >= state["depth"]:
        sys.stderr.write("STOP: reached max depth %d\n" % state["depth"])
        return 3
    if not state["pending"]:
        sys.stderr.write("STOP: no novel follow-up queries remain (converged)\n")
        return 3
    new_level = state["level"] + 1
    budget = allowed_for_level(state["breadth"], new_level)
    frontier = state["pending"][:budget]
    state["pending"] = state["pending"][budget:]
    for q in frontier:
        state["visited"].append(_norm(q))
    state["frontier"] = frontier
    state["level"] = new_level
    _save(args.state, state)
    for q in frontier:
        sys.stdout.write(q + "\n")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = _load(args.state)
    sys.stdout.write(
        "level %d/%d | frontier=%d | pending=%d | visited=%d | learnings=%d\n" % (
            state["level"], state["depth"], len(state["frontier"]),
            len(state["pending"]), len(state["visited"]), len(state["learnings"])))
    for q in state["frontier"]:
        sys.stdout.write("  frontier: " + q + "\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Iterative-deepening loop controller.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init")
    i.add_argument("state")
    i.add_argument("--query", required=True)
    i.add_argument("--breadth", type=int, default=4)
    i.add_argument("--depth", type=int, default=2)
    i.set_defaults(fn=cmd_init)

    r = sub.add_parser("record")
    r.add_argument("state")
    r.add_argument("--learning", action="append")
    r.add_argument("--followup", action="append")
    r.set_defaults(fn=cmd_record)

    n = sub.add_parser("next")
    n.add_argument("state")
    n.set_defaults(fn=cmd_next)

    s = sub.add_parser("status")
    s.add_argument("state")
    s.set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
