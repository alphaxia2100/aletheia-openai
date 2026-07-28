#!/usr/bin/env python3
"""Read FULL content of a URL -> clean markdown. The depth step, with an opt-in browser.

Default order of attack:
  1. Jina Reader (r.jina.ai, no key) for pages/PDFs, including Reddit URLs.
  2. Flag a short/blocked result honestly; do not touch a browser session.

Only an explicit ``--browser`` opts into opencli's authenticated Browser Bridge.  For a
Reddit thread that first tries opencli's full-thread reader, then the generic browser
reader.  This separates ordinary research reads from a user's authenticated browser
state and makes browser/session access visible in the command invocation.

Usage:
  read.py URL [URL2 ...] [--outdir DIR] [--max-chars N] [--browser]
  read.py --from-sources sources.jsonl --top-k 8 [--outdir DIR]
Prints: "<chars>\t<method>\t<file>\t<url>". Full text saved to --outdir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Tuple

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402
import _agentreach  # noqa: E402
import _config  # noqa: E402

_STUB = 1500  # bytes below this = likely blocked / JS-gated / stub
# Content markers of a block/captcha/interstitial page that can EXCEED _STUB bytes and thus
# masquerade as a successful read (e.g. ScienceDirect "Are you a robot?" ~1.6 KB).
_BLOCK_MARKERS = ("are you a robot", "just a moment", "enable javascript", "captcha",
                  "verify you are human", "please confirm you are a human", "access denied",
                  "cf-browser-verification", "checking your browser", "request unsuccessful",
                  "please enable cookies", "attention required")


def _blocked(text: str) -> bool:
    tl = text[:2000].lower()
    return any(m in tl for m in _BLOCK_MARKERS)


def _is_reddit_thread(url: str) -> bool:
    return "reddit.com" in url and "/comments/" in url


def _jina(url: str, timeout: float, max_chars: int) -> str:
    _http.validate_public_url(url)
    headers = {"X-Return-Format": "markdown"}
    if os.environ.get("JINA_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["JINA_API_KEY"]
    body = _http.get_bytes("https://r.jina.ai/" + url, timeout, headers).decode("utf-8", "replace")
    return body[:max_chars] if max_chars > 0 else body


def read_url(url: str, timeout: float, max_chars: int, browser: bool = False) -> Tuple[str, str]:
    _http.validate_public_url(url)
    # An authenticated browser is an explicit capability.  In particular, do not let a
    # short Jina result turn an arbitrary retrieved URL into a browser/session request.
    if browser and not _config.browser_authorized(url):
        return "", "browser-not-authorized"
    if browser and _is_reddit_thread(url):
        txt, _err = _agentreach.reddit_read(url, max(timeout, 90))
        if txt:
            return (txt[:max_chars] if max_chars > 0 else txt), "reddit-read"
    # 2. Jina Reader (fast, no key)
    text = ""
    method = "jina"
    if not browser:
        try:
            text = _jina(url, timeout, max_chars)
        except Exception:  # noqa: BLE001
            text = ""
    blocked = _blocked(text)
    # 3. Explicit opt-in only: render in real logged-in Chrome.  A short/blocked Jina
    # response is evidence of an unreadable page, not permission to use browser cookies.
    if browser:
        if not _agentreach.browser_available():
            return "", "browser-unavailable"
        btxt, _berr = _agentreach.browser_extract(url, max(timeout, 60), max_chars or 40000)
        if not btxt:
            return "", "browser-empty"
        if _blocked(btxt):
            return "", "blocked"
        text, method, blocked = btxt, "opencli-browser", False
    if blocked:  # unrecoverable block -> honest failure, not a fake success
        return "", "blocked"
    return text, method


def _save(url: str, text: str, outdir: str, method: str) -> str:
    _config.ensure_private_dir(outdir)
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    path = os.path.join(outdir, h + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<!-- source: %s (via %s) -->\n\n" % (url, method) + text)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read full URL content (Jina by default; browser only with --browser).")
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--from-sources", help="sources JSONL; read the top URLs")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--outdir", default="runs/reads")
    ap.add_argument("--max-chars", type=int, default=40000)
    ap.add_argument("--timeout", type=float, default=40.0)
    ap.add_argument("--browser", action="store_true",
                    help="request the authenticated browser; requires a matching harness browser capability")
    args = ap.parse_args(argv)

    urls = list(args.urls)
    if args.from_sources:
        with open(args.from_sources, "r", encoding="utf-8") as fh:
            recs = [json.loads(l) for l in fh if l.strip()]
        urls += [r.get("url", "") for r in recs[: args.top_k] if r.get("url")]
    if not urls:
        ap.error("provide URLs or --from-sources")

    rc = 0
    for url in urls:
        if not url.lower().startswith(("http://", "https://")):
            sys.stderr.write("SKIP non-http url: %s\n" % url)
            rc = 1
            continue
        try:
            text, method = read_url(url, args.timeout, args.max_chars, args.browser)
            path = _save(url, text, args.outdir, method)
            n = len(text)
            flag = "  [!] likely blocked/stub" if (n < _STUB and method == "jina") else ""
            sys.stdout.write("%d\t%s\t%s\t%s%s\n" % (n, method, path, url, flag))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("FAIL %s: %s\n" % (url, type(e).__name__))
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
