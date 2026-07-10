#!/usr/bin/env python3
"""Read FULL content of a URL -> clean markdown. The depth step, with way-arounds.

Order of attack:
  1. Reddit thread URL  -> opencli `reddit read` (OP + comments, authed browser).
  2. Otherwise          -> Jina Reader (r.jina.ai, no key) for pages/PDFs.
  3. If Jina stubs (< ~1.5 KB, i.e. JS-gated / login / soft-paywall) OR --browser
     -> render in your real logged-in Chrome via opencli Browser Bridge.
Stubs that still can't be beaten are FLAGGED, never silent.

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
    headers = {"X-Return-Format": "markdown"}
    if os.environ.get("JINA_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["JINA_API_KEY"]
    body = _http.get_bytes("https://r.jina.ai/" + url, timeout, headers).decode("utf-8", "replace")
    return body[:max_chars] if max_chars > 0 else body


def read_url(url: str, timeout: float, max_chars: int, browser: bool = False) -> Tuple[str, str]:
    # 1. Reddit threads -> full OP + comments via the authed browser
    if _is_reddit_thread(url):
        txt, _err = _agentreach.reddit_read(url, max(timeout, 90))
        if txt:
            return (txt[:max_chars] if max_chars > 0 else txt), "reddit-read"
    # 2. Jina Reader (fast, no key)
    text = ""
    if not browser:
        try:
            text = _jina(url, timeout, max_chars)
        except Exception:  # noqa: BLE001
            text = ""
    method = "jina"
    blocked = _blocked(text)
    # 3. Way-around: Jina stubbed/blocked (or forced) -> render in real logged-in Chrome
    if (browser or len(text.strip()) < _STUB or blocked) and _agentreach.browser_available():
        # Zero means unlimited on every backend. Do not silently turn an explicitly uncapped reread
        # back into the default 40k browser cap.
        btxt, _berr = _agentreach.browser_extract(url, max(timeout, 60), max_chars)
        if btxt and not _blocked(btxt) and len(btxt) > (0 if blocked else len(text)):
            text, method, blocked = btxt, "opencli-browser", False
    if blocked:  # unrecoverable block -> honest failure, not a fake success
        return "", "blocked"
    return text, method


def _save(url: str, text: str, outdir: str, method: str) -> str:
    os.makedirs(outdir, exist_ok=True)
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    path = os.path.join(outdir, h + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<!-- source: %s (via %s) -->\n\n" % (url, method) + text)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read full URL content (Jina -> real-browser fallback).")
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--from-sources", help="sources JSONL; read the top URLs")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--outdir", default="runs/reads")
    ap.add_argument("--max-chars", type=int, default=40000)
    ap.add_argument("--timeout", type=float, default=40.0)
    ap.add_argument("--browser", action="store_true", help="force real-browser render (opencli)")
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
