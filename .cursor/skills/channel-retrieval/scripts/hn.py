#!/usr/bin/env python3
"""Hacker News (Algolia) client -> normalized records (JSONL). No key.
Class = lead_gen: HN comments/stories point to primary sources; cite the linked
primary, use HN itself for expert contrarian color. Usage: hn.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = ("https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=%d&query=%s"
           % (limit, _http.quote(query)))
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for h in data.get("hits", []):
        oid = str(h.get("objectID"))
        hn_url = "https://news.ycombinator.com/item?id=" + oid
        target = h.get("url") or hn_url
        out.append(_http.rec(
            "hackernews", url=target,
            title=h.get("title") or h.get("story_title") or "",
            authors=[{"name": h.get("author", "")}] if h.get("author") else [],
            published=(h.get("created_at") or "")[:10],
            primary=False,
            snippet="points=%s comments=%s discussion=%s" % (
                h.get("points"), h.get("num_comments"), hn_url),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Hacker News -> normalized records"))
