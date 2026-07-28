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
import stat
import sys
import tempfile
import time
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402
import _config  # noqa: E402

_NS = {"a": "http://www.w3.org/2005/Atom"}
_HOSTS = ["https://export.arxiv.org/api/query"]
_FALLBACK_MSG = ("arXiv rate-limited (429). Skipping; use openalex.py / semanticscholar.py "
                 "which also index arXiv papers.\n")


def _cooldown_path() -> str:
    """Return an owner-private cache path, never a predictable shared /tmp file."""
    try:
        directory = _config.ensure_private_dir(_config.cache_dir())
    except OSError:
        return ""
    return os.path.join(directory, "arxiv-cooldown")


def _read_private_text(path: str) -> str:
    """Read one regular owner-private file without following a symlink."""
    if not path:
        return ""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return ""
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return ""
        if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            return ""
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            fd = -1
            return fh.read()
    except OSError:
        return ""
    finally:
        if fd >= 0:
            os.close(fd)


def _cooling_down() -> float:
    try:
        remaining = float(_read_private_text(_cooldown_path()).strip()) - time.time()
        return max(0.0, remaining)
    except Exception:  # noqa: BLE001
        return 0.0


def _set_cooldown(seconds: float) -> None:
    path = _cooldown_path()
    if not path:
        return
    fd, temporary = -1, ""
    try:
        fd, temporary = tempfile.mkstemp(prefix=".arxiv-cooldown-", dir=os.path.dirname(path))
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            fh.write(str(time.time() + min(seconds, 300.0)))
            fh.flush()
            os.fsync(fh.fileno())
        # os.replace changes a malicious symlink itself rather than following it.
        os.replace(temporary, path)
    except OSError:
        pass
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
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
