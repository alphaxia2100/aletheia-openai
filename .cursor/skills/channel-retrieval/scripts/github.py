#!/usr/bin/env python3
"""GitHub repo search -> normalized records (JSONL).

Class = evidence: repos/tooling as a primary channel for technical claims. Works
unauth (60 req/hr); set GITHUB_TOKEN for 5000/hr. Usage: github.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    url = ("https://api.github.com/search/repositories?q=%s&sort=stars&order=desc&per_page=%d"
           % (_http.quote(_http.keywordize(query, 4)), min(limit, 50)))  # GitHub ANDs terms -> long q = 0
    data = _http.get_json(url, timeout, headers)
    out: List[Dict[str, Any]] = []
    for r in (data.get("items") or []):
        owner = (r.get("owner") or {}).get("login", "")
        out.append(_http.rec(
            "github", url=r.get("html_url", ""), title=r.get("full_name", ""),
            authors=[{"name": owner}] if owner else [],
            published=(r.get("pushed_at") or "")[:10], primary=True,
            cited_by_count=r.get("stargazers_count") or 0,
            snippet="stars=%s lang=%s :: %s" % (
                r.get("stargazers_count"), r.get("language"), (r.get("description") or "")[:160]),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "GitHub repos -> normalized records"))
