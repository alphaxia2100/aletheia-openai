#!/usr/bin/env python3
"""Aletheia channel doctor — health-probe + ordered failover.

Adopts the one genuinely good idea from agent-reach: for every channel, probe
the real backend(s) in priority order and report which is live, so a dead source
degrades gracefully instead of failing a survey. No-key channels are live-probed;
key-gated channels are reported as configured/not-configured.

Usage: doctor.py [--timeout S] [--json] [--all]
Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import _config

UA = "aletheia-doctor/0.1"


def load_env() -> None:
    """Use the shared user-scoped connector configuration loader."""
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    import _http
    _http.load_env()


def live(url: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    try:
        # Do not route a connector key (for example Brave's header) through an ambient proxy set
        # by the agent host. The normal retrieval client uses the same no-proxy/public-redirect
        # policy; doctor is a real request too, not an exempt diagnostic side channel.
        import _http
        _http.validate_public_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _http._PublicOnlyRedirect())
        with opener.open(req, timeout=timeout) as resp:
            return (resp.status < 400, "HTTP %s" % resp.status)
    except urllib.error.HTTPError as e:
        # Reachable is not the same as usable. Authentication/quota failures must not false-green a
        # configured channel; individual probes can downgrade known transient 429s to `warn`.
        return (False, "HTTP %s" % e.code)
    except Exception as e:  # noqa: BLE001
        return (False, type(e).__name__)


def key(var: str) -> bool:
    return bool(os.environ.get(var))


# Each probe returns (channel, index_group, status, active_backend, note).
# status: ok | warn | down | unconfigured

def p_brave(t: float) -> Tuple[str, ...]:
    if key("BRAVE_API_KEY"):
        ok, note = live("https://api.search.brave.com/res/v1/web/search?q=test&count=1", t,
                        {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"})
        if ok:
            return ("brave", "brave", "ok", "brave", "independent web index (live)")
        return ("brave", "brave", "warn", "brave", "key set but probe failed: " + note)
    return ("brave", "brave", "warn", "fetch/jina", "no BRAVE_API_KEY -> losing your independent web index; add free key")


def p_openalex(t: float) -> Tuple[str, ...]:
    url = "https://api.openalex.org/works?per_page=1"
    if key("OPENALEX_API_KEY"):
        url += "&api_key=" + os.environ["OPENALEX_API_KEY"]
    ok, note = live(url, t)
    if ok and key("OPENALEX_API_KEY"):
        return ("openalex", "openalex", "ok", "openalex", note)
    if ok:
        return ("openalex", "openalex", "warn", "openalex", "up but add OPENALEX_API_KEY (2026 free key; low quota without)")
    if key("OPENALEX_API_KEY"):
        return ("openalex", "openalex", "warn", "-", "configured key rejected/unusable: " + note)
    return ("openalex", "openalex", "down", "-", note)


def _simple(name: str, group: str, url: str, t: float, headers=None, warn_note="") -> Tuple[str, ...]:
    ok, note = live(url, t, headers)
    return (name, group, "ok" if ok else "down", name if ok else "-", note if ok else (warn_note or note))


def p_search(name: str, group: str, modname: str, t: float, q: str = "climate change effects") -> Tuple[str, ...]:
    """FUNCTIONAL probe: actually call the client's search() and count results, so a channel that is
    HTTP-200 but returns NOTHING (e.g. a dead scrape endpoint or an API change) shows as `warn`,
    not a false `ok`. This is what lets Aletheia surface silently-broken channels."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        m = __import__(modname)
        fn = getattr(m, "search", None) or getattr(m, "yt_search", None)
        out = fn(q, 3, t) or []
        n = len(out)
        return (name, group, "ok" if n else "warn", name,
                ("%d results" % n) if n else "live but 0 results — DEGRADED (check client/endpoint)")
    except Exception as e:  # noqa: BLE001
        return (name, group, "down", "-", "%s: %s" % (type(e).__name__, str(e)[:55]))


def p_arxiv(t: float) -> Tuple[str, ...]:
    ok, note = live("https://export.arxiv.org/api/query?search_query=all:test&max_results=1", t)
    if "429" in note:
        return ("arxiv", "arxiv", "warn", "arxiv", "rate-limited (429); circuit-breaker active — use openalex/semanticscholar")
    return ("arxiv", "arxiv", "ok" if ok else "down", "arxiv" if ok else "-", note)
def p_hn(t): return p_search("hackernews", "hackernews", "hn", t)
def p_wikipedia(t): return _simple("wikipedia", "wikipedia", "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=test&format=json&srlimit=1", t)
def p_duckduckgo(t): return p_search("duckduckgo", "duckduckgo", "web_ddg", t)
def p_marginalia(t): return p_search("marginalia", "marginalia", "web_marginalia", t)
def p_jina(t): return _simple("read (jina)", "jina", "https://r.jina.ai/https://example.com", t)


def p_x(t: float) -> Tuple[str, ...]:
    import _agentreach
    # A health check is real subprocess/network activity. Do not ask a browser-backed adapter for
    # session status unless the host granted the same capability needed for a real X query.
    if not _config.browser_authorized("x.com"):
        if key("GETXAPI_KEY") or key("TWITTERAPI_IO_KEY"):
            return ("x", "x", "warn", "-", "paid API key is set, but this runtime has no paid X adapter; browser capability not granted")
        return ("x", "x", "warn", "-", "browser/session capability is not authorized for x.com")
    tw = _agentreach.find_cli("twitter") or next(
        (p for p in (os.path.expanduser("~/.aletheia-agentreach/bin/twitter"),) if os.path.exists(p)), None)
    if tw:
        try:
            out = _agentreach._run([tw, "status"], t).lower()
            if "ok: true" in out or "authenticated: true" in out:
                return ("x", "x", "ok", "agent-reach", "logged-in session (color-only)")
            return ("x", "x", "warn", "twitter-cli", "installed; log into x.com then `agent-reach configure --from-browser chrome`")
        except Exception:  # noqa: BLE001
            pass
    if key("GETXAPI_KEY") or key("TWITTERAPI_IO_KEY"):
        return ("x", "x", "ok", "paid-api", "key set (color-only)")
    return ("x", "x", "warn", "agent-reach", "install agent-reach + twitter, or set GETXAPI/TWITTERAPI_IO_KEY")


def p_youtube(t: float) -> Tuple[str, ...]:
    import importlib.util
    has_lib = importlib.util.find_spec("youtube_transcript_api") is not None
    ok, note = live("https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=aircAruvnKk", t)
    if ok and has_lib:
        return ("youtube (transcripts)", "youtube", "ok", "youtube-transcript-api", "no-key captions")
    if ok:
        return ("youtube (transcripts)", "youtube", "warn", "-", "reachable; pip install --user youtube-transcript-api yt-dlp")
    return ("youtube (transcripts)", "youtube", "down", "-", note)
def p_se(t): return p_search("stackexchange", "stackexchange", "stackexchange", t, q="python asyncio")
def _has_cli(name: str) -> bool:
    if shutil.which(name):
        return True
    return any(os.path.exists(os.path.join(os.path.expanduser(d), name))
               for d in ("~/.local/bin", "~/.npm-global/bin"))


def p_reddit(t: float) -> Tuple[str, ...]:
    if _config.browser_authorized("reddit.com") and (_has_cli("opencli") or _has_cli("rdt")):
        return ("reddit", "reddit", "ok", "agent-reach", "live/authed via opencli (browser session)")
    ok, note = live("https://api.pullpush.io/reddit/search/submission/?q=test&size=1", t)
    if ok:
        return ("reddit", "reddit", "ok", "pullpush", "no-key archive (agent-reach reddit backend not installed)")
    return ("reddit", "reddit", "down", "-", note)
def p_gutendex(t): return _simple("gutenberg", "gutenberg", "https://gutendex.com/books?search=test", t)
def p_openlibrary(t): return _simple("openlibrary", "internet_archive", "https://openlibrary.org/search.json?q=test&limit=1", t)
def p_europepmc(t): return _simple("europepmc", "europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1", t)
def p_crossref(t): return _simple("crossref", "crossref", "https://api.crossref.org/works?rows=1", t)


def p_github(t: float) -> Tuple[str, ...]:
    name, group, status, active, note = p_search("github", "github", "github", t, q="deep learning")
    return (name, group, status, active, note + ("" if key("GITHUB_TOKEN") else " (60/hr unauth; add GITHUB_TOKEN)"))


def p_s2(t: float) -> Tuple[str, ...]:
    ok, note = live("https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1", t)
    throttled = "429" in note
    status = "ok" if (ok and not throttled) else "warn"
    detail = note if (ok and not throttled) else "shared anon pool throttles (429); add SEMANTIC_SCHOLAR_API_KEY"
    return ("semantic_scholar", "semantic_scholar", status, "semantic_scholar" if status == "ok" else "semantic_scholar", detail)


def p_googlebooks(t: float) -> Tuple[str, ...]:
    url = "https://www.googleapis.com/books/v1/volumes?q=test&maxResults=1"
    if key("GOOGLE_BOOKS_API_KEY"):
        url += "&key=" + os.environ["GOOGLE_BOOKS_API_KEY"]
    ok, note = live(url, t)
    throttled = "429" in note
    status = "ok" if (ok and not throttled) else "warn"
    detail = note if (ok and not throttled) else "keyless throttled (429); add GOOGLE_BOOKS_API_KEY"
    return ("google_books", "google_books", status, "google_books", detail)


def p_keyonly(name: str, group: str, var: str) -> Tuple[str, ...]:
    if key(var):
        return (name, group, "ok", name, "%s set" % var)
    return (name, group, "unconfigured", "-", "set %s to enable" % var)


LIVE_PROBES = [
    ("brave", p_brave), ("openalex", p_openalex), ("arxiv", p_arxiv),
    ("hackernews", p_hn), ("stackexchange", p_se), ("reddit", p_reddit),
    ("gutenberg", p_gutendex), ("openlibrary", p_openlibrary),
    ("europepmc", p_europepmc), ("crossref", p_crossref), ("github", p_github),
    ("semantic_scholar", p_s2), ("google_books", p_googlebooks),
    ("wikipedia", p_wikipedia), ("duckduckgo", p_duckduckgo),
    ("marginalia", p_marginalia), ("read", p_jina), ("youtube", p_youtube), ("x", p_x),
]

# Map a probe's display name to its channels.json index id (for core filtering).
_CID = {
    "serper (one Google window)": "google_serper",
    "supadata (youtube)": "supadata",
    "taddy (podcasts)": "taddy",
    "reddit-oauth (PRAW live)": "reddit-oauth",
    "youtube (transcripts)": "youtube",
    "read (jina)": "read",
}


def _cid(display: str) -> str:
    return _CID.get(display, display)


def _enabled_set() -> set:
    try:
        d = _config.load_channels()
        return set(d.get("enabled", [])) | set(d.get("utilities_always_on", []))
    except Exception:  # noqa: BLE001
        return set()

KEYONLY = [
    ("exa", "exa_neural", "EXA_API_KEY"),
    ("perplexity", "perplexity", "PERPLEXITY_API_KEY"),
    ("linkup", "linkup", "LINKUP_API_KEY"),
    ("firecrawl", "firecrawl", "FIRECRAWL_API_KEY"),
    ("serper (one Google window)", "google", "SERPER_API_KEY"),
    ("supadata (youtube)", "youtube", "SUPADATA_API_KEY"),
    ("taddy (podcasts)", "podcast", "TADDY_API_KEY"),
    ("scite", "scite", "SCITE_API_TOKEN"),
    ("reddit-oauth (PRAW live)", "reddit", "REDDIT_CLIENT_ID"),
]

_ORDER = {"ok": 0, "warn": 1, "down": 2, "unconfigured": 3}


def run(timeout: float, enabled: Optional[set] = None, include_all: bool = False) -> List[Tuple[str, ...]]:
    """Probe only enabled channels unless ``include_all`` is explicitly requested.

    Health checks are real network/subprocess activity, not a passive listing.  Keep
    disabled connectors dormant so the channel configuration is a genuine capability
    boundary rather than merely a display filter.
    """
    if enabled is None:
        enabled = _enabled_set()
    probes = LIVE_PROBES if include_all else [item for item in LIVE_PROBES if item[0] in enabled]
    rows: List[Tuple[str, ...]] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fn, timeout) for _channel, fn in probes]
        for f in futs:
            try:
                rows.append(f.result())
            except Exception as e:  # noqa: BLE001
                rows.append(("?", "?", "down", "-", type(e).__name__))
    for name, group, var in KEYONLY:
        if include_all or _cid(name) in enabled:
            rows.append(p_keyonly(name, group, var))
    rows.sort(key=lambda r: (_ORDER.get(r[2], 9), r[0]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Aletheia channel doctor")
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="actively probe every disabled channel too; this deliberately bypasses the normal channel filter")
    args = ap.parse_args()

    load_env()
    enabled = _enabled_set()
    rows = run(args.timeout, enabled=enabled, include_all=args.all)
    hidden = 0 if args.all else max(0, len(LIVE_PROBES) + len(KEYONLY) - len(rows))
    if args.json:
        keys = ("channel", "index_group", "status", "active_backend", "note")
        json.dump([dict(zip(keys, r)) for r in rows], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if not rows:
        print("No enabled Aletheia channels to probe. Check channels.json or pass --all.")
        return 1
    w = max(len(r[0]) for r in rows) + 2
    print("Aletheia channels  (ok=live, warn=degraded/keyless, down=unreachable, unconfigured=needs key)\n")
    print("%-*s %-13s %-16s %s" % (w, "CHANNEL", "STATUS", "ACTIVE", "NOTE"))
    print("-" * 96)
    for name, group, status, active, note in rows:
        print("%-*s %-13s %-16s %s" % (w, name, status, active, note))
    live_ok = sum(1 for r in rows if r[2] == "ok")
    scope = "all" if args.all else "core"
    print("\n%d/%d %s channels live." % (live_ok, len(rows), scope))
    if hidden:
        print("%d channels hidden (disabled). Run with --all to see them, or `channels.py enable <name>`." % hidden)
    # One functional request per channel runs concurrently, but this is not a same-backend load test.
    print("\nNote: one functional request per channel — 'ok' means usable now, not load-proof. "
          "Under repeated parallel fan-out (deep/exhaustive) the keyless academic pools (arXiv/OpenAlex/"
          "Semantic Scholar) may still rate-limit; check per-channel errors in the run's evidence.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
