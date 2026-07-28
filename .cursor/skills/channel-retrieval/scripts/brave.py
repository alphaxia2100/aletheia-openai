#!/usr/bin/env python3
"""Brave Search client -> normalized records (JSONL).

Core web #1: the only at-scale INDEPENDENT Western index with a public API.
Needs BRAVE_API_KEY (free tier ~2000/mo), loaded only from user-scoped configuration by _http.
No MCP required. Usage: brave.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
import urllib.error
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    key = os.environ.get("BRAVE_API_KEY")
    if not key:
        sys.stderr.write("BRAVE_API_KEY not set (add it to the user-scoped Aletheia config). Falling back: use marginalia.py / web_ddg.py.\n")
        return []
    def fetch(q: str):
        url = ("https://api.search.brave.com/res/v1/web/search?q=%s&count=%d"
               % (_http.quote(q), min(limit, 20)))
        return url, _http.get_json(url, timeout, headers={
            "X-Subscription-Token": key, "Accept": "application/json"})

    try:
        url, data = fetch(query)
    except urllib.error.HTTPError as exc:
        # Brave rejects some long/compound queries with 422. Retry once with the same salience-aware
        # compaction used by the other keyword APIs instead of silently losing the web channel.
        compact = _http.keywordize(query, 12)
        if exc.code != 422 or compact == query:
            raise
        url, data = fetch(compact)
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
