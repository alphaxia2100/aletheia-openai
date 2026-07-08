#!/usr/bin/env python3
"""Brave Search client -> normalized records (JSONL).

Core web #1: the only at-scale INDEPENDENT Western index with a public API.
Needs BRAVE_API_KEY (free tier ~2000/mo), auto-loaded from .env by _http.
No MCP required. Usage: brave.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        sys.stderr.write("BRAVE_API_KEY not set (add to .env). Falling back: use marginalia.py / web_ddg.py.\n")
        return []
    url = ("https://api.search.brave.com/res/v1/web/search?q=%s&count=%d"
           % (_http.quote(query), min(limit, 20)))
    data = _http.get_json(url, timeout, headers={
        "X-Subscription-Token": key, "Accept": "application/json"})
    out: List[Dict[str, Any]] = []
    for r in ((data.get("web") or {}).get("results") or []):
        out.append(_http.rec(
            "brave", url=r.get("url", ""), title=r.get("title", ""),
            primary=False,
            snippet=(r.get("description", "") or "")[:220],
            published=(r.get("age", "") or ""),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Brave Search -> normalized records"))
