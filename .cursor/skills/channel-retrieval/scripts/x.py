#!/usr/bin/env python3
"""X / Twitter client (no paid API) -> normalized records (JSONL).

Thin adapter: routes to the agent-reach `twitter` CLI (browser-session auth) via
_agentreach. When that backend breaks, swap it in _agentreach.x_search rather than
here. Class = color: what people react to, never evidence.

Setup (one-time, no key): log into x.com in Chrome, then
  agent-reach configure --from-browser chrome
  twitter status                                  # -> ok: true

Usage: x.py "query" [--limit N] [--top] [--from USER] [--since YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402
import _agentreach  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="X/Twitter via agent-reach (no paid API) -> records")
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--top", action="store_true", help="Top tab (default: Latest)")
    ap.add_argument("--from", dest="frm", default="", help="only tweets from this user")
    ap.add_argument("--since", default="", help="YYYY-MM-DD")
    ap.add_argument("--timeout", type=float, default=45.0)
    args = ap.parse_args()

    records, err = _agentreach.x_search(args.query, args.limit, args.top, args.frm, args.since, args.timeout)
    if err:
        sys.stderr.write(
            "x unavailable: %s\n"
            "  -> log into x.com in Chrome, then `agent-reach configure --from-browser chrome`.\n"
            "  -> or use a paid backend (GetXAPI/twitterapi.io); see .cursor/mcp.reference.md.\n" % err)
    _http.emit(records)
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
