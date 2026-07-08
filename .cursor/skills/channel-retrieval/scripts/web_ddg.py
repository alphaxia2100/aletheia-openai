#!/usr/bin/env python3
"""DuckDuckGo (no-key) web search -> normalized records (JSONL).

Class = lead_gen. IMPORTANT: DDG is Bing-derived, so index_group = 'bing' — it is
NOT independent of Bing/other Bing resellers. Use it as a no-key web-search
fallback when BRAVE_API_KEY is absent, but for real index diversity prefer Brave
(independent) or Marginalia (independent, no key: web_marginalia.py).

HTML-scraped (no official API), so it is brittle and may get rate-limited/blocked.
Usage: web_ddg.py "query" [--limit N].
"""
from __future__ import annotations

import html
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def _strip(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", s)).strip())


def _real_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if "duckduckgo.com/l/" in href or "uddg=" in href:
        q = urllib.parse.urlparse(href).query
        u = urllib.parse.parse_qs(q).get("uddg")
        if u:
            return u[0]
    return href


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    # POST the query (more reliable than GET for the html endpoint)
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(
        "https://html.duckduckgo.com/html/", data=data,
        headers={"User-Agent": _http.UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")

    results = re.findall(r'result__a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)
    snippets = re.findall(r'result__snippet[^>]*>(.*?)</a>', html, re.S)
    out: List[Dict[str, Any]] = []
    for i, (href, title) in enumerate(results[:limit]):
        snip = _strip(snippets[i]) if i < len(snippets) else ""
        out.append(_http.rec(
            "duckduckgo", url=_real_url(href), title=_strip(title),
            primary=False, snippet=snip[:220]))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "DuckDuckGo (no-key) -> normalized records"))
