#!/usr/bin/env python3
"""arXiv client -> normalized source records (JSONL). No key. Preprints (CS/physics/math).

The arXiv export API is aggressively shared-IP rate-limited (persistent HTTP 429).
So this does NOT hammer it: exponential backoff + Retry-After (in _http), a mirror
host, and a CROSS-INVOCATION circuit-breaker — once a 429 is seen, a short cooldown
file makes subsequent calls skip instantly (instead of burning dozens of attempts
across a fan-out) and tells you to use OpenAlex/Semantic Scholar, which also index arXiv.

Usage: arxiv.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402

_NS = {"a": "http://www.w3.org/2005/Atom"}
_HOSTS = ["https://export.arxiv.org/api/query", "http://export.arxiv.org/api/query"]
_COOLDOWN_FILE = os.path.join(tempfile.gettempdir(), "aletheia_arxiv_cooldown")
_FALLBACK_MSG = ("arXiv rate-limited (429). Skipping; use openalex.py / semanticscholar.py "
                 "which also index arXiv papers.\n")


def _cooling_down() -> float:
    try:
        with open(_COOLDOWN_FILE, "r", encoding="utf-8") as fh:
            remaining = float(fh.read().strip()) - time.time()
        return max(0.0, remaining)
    except Exception:  # noqa: BLE001
        return 0.0


def _set_cooldown(seconds: float) -> None:
    try:
        with open(_COOLDOWN_FILE, "w", encoding="utf-8") as fh:
            fh.write(str(time.time() + min(seconds, 300.0)))
    except OSError:
        pass


def _parse(raw: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(raw)
    out: List[Dict[str, Any]] = []
    for entry in root.findall("a:entry", _NS):
        title = (entry.findtext("a:title", default="", namespaces=_NS) or "").strip()
        link = (entry.findtext("a:id", default="", namespaces=_NS) or "").strip()
        summary = (entry.findtext("a:summary", default="", namespaces=_NS) or "").strip()
        published = (entry.findtext("a:published", default="", namespaces=_NS) or "").strip()
        authors = [{"name": (a.findtext("a:name", default="", namespaces=_NS) or "").strip()}
                   for a in entry.findall("a:author", _NS)]
        authors = [a for a in authors if a["name"]]
        out.append(_http.rec("arxiv", url=link, title=title, authors=authors,
                             published=published[:10], primary=True, snippet=summary[:280]))
    return out


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    cd = _cooling_down()
    if cd > 0:
        sys.stderr.write("arXiv on cooldown (%ds left after a recent 429). %s" % (int(cd), _FALLBACK_MSG))
        return []
    for host in _HOSTS:
        url = "%s?sortBy=relevance&max_results=%d&search_query=all:%s" % (host, limit, _http.quote(query))
        try:
            # retries=1 (2 attempts) with backoff/Retry-After in _http; don't over-try a throttled host
            return _parse(_http.get_bytes(url, timeout, retries=1))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = e.headers.get("Retry-After") if e.headers else None
                secs = float(ra) if (ra and str(ra).strip().isdigit()) else 60.0
                _set_cooldown(secs)  # circuit-breaker: stop the whole run from hammering
                sys.stderr.write(_FALLBACK_MSG)
                return []
            continue  # other HTTP error -> try the mirror host
        except Exception:  # noqa: BLE001 - network/parse error -> try mirror, else give up
            continue
    return []


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "arXiv -> normalized records"))
