#!/usr/bin/env python3
"""Reddit client -> normalized records (JSONL). NO KEY, NO LOGIN.

Closes the "agents can't reach Reddit" gap. DISCOVERY is relevance-first: a web index
scoped to reddit.com (the `site:reddit.com` trick, via Brave/DDG) ranks by relevance,
whereas Reddit's own search ranks by recency/engagement and returns viral noise. Order:
web-relevance -> PullPush -> Arctic Shift -> opencli (live/authed, demoted for search
but primary for READING threads via --thread). Whatever wins is relevance-filtered.
Ordered-backend failover: try each, use the first that returns.

Class = lead_gen: Reddit is lived-experience + lead discovery, gameable/noisy.
Cite specific technical threads, never aggregate sentiment as fact.

Usage: reddit.py "query" [--limit N] [--kind submission|comment] [--subreddit NAME]
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402
import _agentreach  # noqa: E402


def _iso(epoch: Any) -> str:
    try:
        return dt.datetime.utcfromtimestamp(int(epoch)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def _permalink_url(d: Dict[str, Any]) -> str:
    if d.get("full_link"):
        return d["full_link"]
    pl = d.get("permalink") or ""
    if pl.startswith("http"):
        return pl
    return "https://www.reddit.com" + pl if pl else (d.get("url") or "")


def _to_record(d: Dict[str, Any], kind: str) -> Dict[str, Any]:
    title = d.get("title") or (("comment in r/%s" % d.get("subreddit", "")) if kind == "comment" else "")
    body = (d.get("selftext") or d.get("body") or "").strip()
    return _http.rec(
        "reddit", url=_permalink_url(d), title=title,
        authors=[{"name": d.get("author", "")}] if d.get("author") else [],
        published=_iso(d.get("created_utc")),
        primary=False,
        snippet="r/%s score=%s comments=%s :: %s" % (
            d.get("subreddit", ""), d.get("score"), d.get("num_comments", ""), body[:200]),
    )


def _pullpush(query: str, limit: int, kind: str, subreddit: Optional[str], timeout: float) -> List[Dict[str, Any]]:
    endpoint = "submission" if kind == "submission" else "comment"
    url = "https://api.pullpush.io/reddit/search/%s/?q=%s&size=%d&sort=desc" % (
        endpoint, _http.quote(query), min(limit, 100))
    if subreddit:
        url += "&subreddit=" + _http.quote(subreddit)
    data = _http.get_json(url, timeout)
    return [_to_record(d, kind) for d in (data.get("data") or [])]


def _arctic_shift(query: str, limit: int, kind: str, subreddit: Optional[str], timeout: float) -> List[Dict[str, Any]]:
    endpoint = "posts" if kind == "submission" else "comments"
    url = "https://arctic-shift.photon-reddit.com/api/%s/search?query=%s&limit=%d" % (
        endpoint, _http.quote(query), min(limit, 100))
    if subreddit:
        url += "&subreddit=" + _http.quote(subreddit)
    data = _http.get_json(url, timeout)
    rows = data.get("data") if isinstance(data, dict) else data
    return [_to_record(d, kind) for d in (rows or [])]


def _agentreach_backend(query: str, limit: int, kind: str, subreddit: Optional[str],
                        timeout: float) -> List[Dict[str, Any]]:
    recs, _err = _agentreach.reddit_search(query, limit, subreddit or "", timeout)
    return recs


def _web_reddit(query: str, limit: int, kind: str, subreddit: Optional[str],
                timeout: float) -> List[Dict[str, Any]]:
    """Reddit DISCOVERY via a web index restricted to reddit.com (the `site:reddit.com`
    trick). Reddit's own search ranks by recency/engagement -> viral noise; a real web
    index (Brave) ranks by relevance, so this returns on-topic threads. Prefer this for
    search; use opencli `--thread` to READ the threads it finds.
    """
    q = "site:reddit.com " + (("r/%s " % subreddit) if subreddit else "") + query
    recs: List[Dict[str, Any]] = []
    try:  # Brave first (independent index, keyed); else DuckDuckGo (no key)
        if os.environ.get("BRAVE_API_KEY"):
            import brave
            recs = brave.search(q, max(limit * 3, 10), timeout)
    except Exception:  # noqa: BLE001
        recs = []
    if not recs:
        try:
            import web_ddg
            recs = web_ddg.search(q, max(limit * 3, 10), timeout)
        except Exception:  # noqa: BLE001
            recs = []
    out: List[Dict[str, Any]] = []
    seen = set()
    for r in recs:
        u = r.get("url", "")
        if "reddit.com" not in u or "/comments/" not in u or u in seen:
            continue
        seen.add(u)
        title = r.get("title", "")
        t = title.split(" on Reddit:", 1)[-1].strip() if " on Reddit:" in title else title
        m = re.search(r"reddit\.com/(r/[A-Za-z0-9_]+)/comments", u)
        sub = m.group(1) if m else ""
        out.append(_http.rec("reddit", url=u, title=(t or title), primary=False,
                             snippet="%s (web-relevance) :: %s" % (sub, (r.get("snippet", "") or "")[:180])))
        if len(out) >= limit:
            break
    return out


def _rerank_filter(query: str, recs: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Relevance-sort a backend's results and drop obvious off-topic noise."""
    try:
        import rerank
        ranked = rerank.rerank(query, recs)
        nonzero = [r for r in ranked if r.get("relevance", 0) > 0]
        return (nonzero or ranked)[:limit]
    except Exception:  # noqa: BLE001
        return recs[:limit]


def search(query: str, limit: int, timeout: float, kind: str = "submission",
           subreddit: Optional[str] = None) -> List[Dict[str, Any]]:
    # Ordered, SWAPPABLE backends. RELEVANCE-FIRST for discovery: a web index scoped to
    # reddit.com beats Reddit's own (recency/engagement) ranking, which returns viral
    # noise. opencli is demoted to last for SEARCH (it's great for READING via --thread).
    # Whatever wins is relevance-filtered to drop off-topic junk.
    backends = [("web", _web_reddit), ("pullpush", _pullpush), ("arctic_shift", _arctic_shift)]
    if _agentreach.reddit_backend():
        backends.append(("agent-reach", _agentreach_backend))
    errors = []
    for name, fn in backends:
        try:
            recs = fn(query, limit, kind, subreddit, timeout)
            if recs:
                return _rerank_filter(query, recs, limit)
            errors.append("%s: empty" % name)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (name, type(e).__name__))
    sys.stderr.write("all reddit backends failed/empty: " + "; ".join(errors) + "\n")
    return []


def _thread_pullpush(pid: str, limit: int, timeout: float) -> str:
    """Archive fallback: OP + comments by link_id (PullPush). May lag for very recent posts."""
    try:
        sub = (_http.get_json("https://api.pullpush.io/reddit/search/submission/?ids=%s" % pid, timeout)
               .get("data") or [])
        coms = (_http.get_json(
            "https://api.pullpush.io/reddit/search/comment/?link_id=%s&size=%d&sort=desc"
            % (pid, min(max(limit * 10, 50), 100)), timeout).get("data") or [])
    except Exception:  # noqa: BLE001
        return ""
    if not sub and not coms:
        return ""
    s = sub[0] if sub else {}
    lines = ["# Reddit thread (r/%s)" % s.get("subreddit", ""),
             "**OP** u/%s (score %s):\n%s\n" % (
                 s.get("author", ""), s.get("score", ""), (s.get("selftext") or s.get("title") or "").strip()),
             "## Comments (%d)" % len(coms)]
    for c in coms:
        b = (c.get("body") or "").strip()
        if b:
            lines.append("- u/%s (%s): %s" % (c.get("author", ""), c.get("score", ""), b))
    return "\n".join(lines).strip()


def read_thread(post: str, limit: int, timeout: float, outdir: str) -> Optional[Dict[str, Any]]:
    """Read a full thread (OP + comments). opencli (live/authed) -> PullPush archive."""
    pid = _agentreach.reddit_post_id(post)
    text, _err = _agentreach.reddit_read(post, max(timeout, 90))
    method = "opencli"
    if not text:
        text = _thread_pullpush(pid, limit, timeout)
        method = "pullpush"
    if not text:
        sys.stderr.write("could not read thread %s (opencli not logged in? archive lag?)\n" % pid)
        return None
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "reddit-" + re.sub(r"[^A-Za-z0-9_-]", "_", pid)[:32] + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    url = post if post.startswith("http") else ("https://www.reddit.com/comments/%s" % pid)
    return _http.rec("reddit", url=url, title=text.split("\n", 1)[0].lstrip("# ")[:80],
                     primary=False, snippet="[thread via %s, %d chars, full=%s] %s"
                     % (method, len(text), path, text[:200]))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Reddit (no key) -> normalized records")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--thread", help="read a full thread (OP + comments) by URL or post id")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--kind", choices=["submission", "comment"], default="submission")
    ap.add_argument("--subreddit")
    ap.add_argument("--outdir", default="runs/reddit")
    args = ap.parse_args()
    if args.thread:
        rec = read_thread(args.thread, args.limit, args.timeout, args.outdir)
        if rec:
            _http.emit([rec])
            return 0
        return 1
    if not args.query:
        ap.error("provide a query, or --thread <url|id>")
    recs = search(args.query, args.limit, args.timeout, args.kind, args.subreddit)
    _http.emit(recs)
    return 0 if recs else 1


if __name__ == "__main__":
    raise SystemExit(main())
