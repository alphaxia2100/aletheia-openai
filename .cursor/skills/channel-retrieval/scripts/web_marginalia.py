#!/usr/bin/env python3
"""Marginalia (no-key) web search -> normalized records (JSONL).

Class = evidence-ish (lead_gen by default). Marginalia is a GENUINELY INDEPENDENT
index that favors the non-commercial "small web" — the best no-key way to add real
index diversity alongside Brave, and it surfaces primary/personal sources the big
engines bury. HTML-scraped (its JSON API needs a free key), so brittle.
Usage: web_marginalia.py "query" [--limit N].
"""
from __future__ import annotations

import html
import os
import re
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402

# Marginalia site chrome / nav that must never be emitted as "sources".
_NAV_TITLES = {"about", "donate", "faq", "login", "api", "source code", "contact",
               "help", "privacy", "terms", "blog", "settings", "search", "home",
               "marginalia search", "old marginalia search"}
_NAV_HOSTS = ("marginalia", "github.com/marginaliasearch")


def _strip(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", s)).strip())


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = "https://old-search.marginalia.nu/search?query=" + _http.quote(query)
    html = _http.get_bytes(url, timeout).decode("utf-8", "replace")
    anchors = re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', html, re.S)
    seen: Dict[str, str] = {}
    order: List[str] = []
    for href, text in anchors:
        if any(h in href for h in _NAV_HOSTS):  # marginalia.nu / marginalia-search.com / about.* nav
            continue
        t = _strip(text)
        if not t or t.lower() in _NAV_TITLES:
            continue
        if href not in seen:
            order.append(href)
            seen[href] = ""
        # prefer a human title over the raw-URL anchor text
        if not t.startswith("http") and not seen[href]:
            seen[href] = t
    out: List[Dict[str, Any]] = []
    for href in order[:limit]:
        out.append(_http.rec(
            "marginalia", url=href, title=seen[href] or href, primary=False,
            snippet="independent small-web index result"))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Marginalia (no-key, independent) -> normalized records"))
