#!/usr/bin/env python3
"""Resolve a research topic to concrete entities BEFORE searching.

Hits only free, no-auth endpoints (Wikipedia, HN Algolia, arXiv, GitHub, and
OpenAlex if a key is present). Every source is best-effort: failures are recorded
in `sources_status`, never fatal. Use --offline to skip the network entirely and
still emit a usable query-plan template.

Output: a JSON query-plan on stdout. Treat results as leads to verify, not truth.

Pure Python 3.9+ stdlib. No install required.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

UA = "aletheia-surveyor/0.1 (research surveyor; +https://github.com/)"

# Tokens that arXiv/OpenAlex metadata sometimes emits where an author name belongs.
_NAME_JUNK = {"keywords", "abstract", "introduction", "et al", "et al.", "anonymous", "unknown"}


def _clean_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = name.strip()
    if not n or n.lower() in _NAME_JUNK:
        return None
    return n


def _get(url: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _get_json(url: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> Any:
    return json.loads(_get(url, timeout, headers).decode("utf-8", "replace"))


def _q(s: str) -> str:
    return urllib.parse.quote(s)


# --- individual resolvers (each returns (payload, status_str)) ---

def resolve_wikipedia(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    url = ("https://en.wikipedia.org/w/api.php?action=opensearch&limit=6&format=json&search=" + _q(topic))
    data = _get_json(url, timeout)
    titles = data[1] if len(data) > 1 else []
    descs = data[2] if len(data) > 2 else []
    urls = data[3] if len(data) > 3 else []
    entries = [
        {"title": t, "description": (descs[i] if i < len(descs) else ""), "url": (urls[i] if i < len(urls) else "")}
        for i, t in enumerate(titles)
    ]
    return {"entries": entries}, "ok"


def resolve_hn(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    url = ("https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=12&query=" + _q(topic))
    data = _get_json(url, timeout)
    hits = []
    for h in data.get("hits", []):
        hits.append({
            "title": h.get("title") or h.get("story_title"),
            "url": h.get("url") or ("https://news.ycombinator.com/item?id=" + str(h.get("objectID"))),
            "author": h.get("author"),
            "points": h.get("points"),
            "hn_url": "https://news.ycombinator.com/item?id=" + str(h.get("objectID")),
        })
    return {"hits": hits}, "ok"


def resolve_arxiv(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    url = ("http://export.arxiv.org/api/query?max_results=8&sortBy=relevance&search_query=all:" + _q(topic))
    raw = _get(url, timeout)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(raw)
    papers: List[Dict[str, Any]] = []
    for entry in root.findall("a:entry", ns):
        title_el = entry.find("a:title", ns)
        id_el = entry.find("a:id", ns)
        authors = [a.findtext("a:name", default="", namespaces=ns).strip()
                   for a in entry.findall("a:author", ns)]
        authors = [a for a in authors if a]
        papers.append({
            "title": (title_el.text or "").strip() if title_el is not None else "",
            "url": (id_el.text or "").strip() if id_el is not None else "",
            "authors": authors,
        })
    return {"papers": papers}, "ok"


def resolve_github(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    url = ("https://api.github.com/search/repositories?per_page=8&sort=stars&order=desc&q=" + _q(topic))
    data = _get_json(url, timeout, headers)
    repos = []
    for r in data.get("items", []):
        repos.append({
            "full_name": r.get("full_name"),
            "url": r.get("html_url"),
            "stars": r.get("stargazers_count"),
            "description": r.get("description"),
            "owner": (r.get("owner") or {}).get("login"),
        })
    return {"repos": repos}, "ok"


def resolve_openalex(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    key = os.environ.get("OPENALEX_API_KEY")
    mailto = os.environ.get("OPENALEX_MAILTO")
    params = "per_page=6&search=" + _q(topic)
    if key:
        params += "&api_key=" + _q(key)
    if mailto:
        params += "&mailto=" + _q(mailto)
    url = "https://api.openalex.org/works?" + params
    data = _get_json(url, timeout)
    works = []
    for w in data.get("results", []):
        works.append({
            "title": w.get("display_name"),
            "doi": w.get("doi"),
            "id": w.get("id"),
            "cited_by_count": w.get("cited_by_count"),
            "authors": [(a.get("author") or {}).get("display_name") for a in (w.get("authorships") or [])],
        })
    status = "ok" if key else "ok_no_key_low_quota"
    return {"works": works}, status


def resolve_reddit(topic: str, timeout: float) -> Tuple[Dict[str, Any], str]:
    # Best-effort: Reddit frequently blocks non-OAuth traffic. Never fatal.
    sub_url = "https://www.reddit.com/subreddits/search.json?limit=6&q=" + _q(topic)
    data = _get_json(sub_url, timeout)
    subs = []
    for c in (data.get("data", {}) or {}).get("children", []):
        d = c.get("data", {})
        subs.append({
            "subreddit": d.get("display_name"),
            "subscribers": d.get("subscribers"),
            "description": (d.get("public_description") or "")[:200],
            "url": "https://www.reddit.com" + (d.get("url") or ""),
        })
    return {"subreddits": subs}, "ok"


# --- aggregation ---

def build_plan(topic: str, results: Dict[str, Any]) -> Dict[str, Any]:
    people = Counter()
    for p in results.get("arxiv", {}).get("papers", []):
        for a in p.get("authors", []):
            name = _clean_name(a)
            if name:
                people[name] += 2
    for w in results.get("openalex", {}).get("works", []):
        for a in (w.get("authors") or []):
            name = _clean_name(a)
            if name:
                people[name] += 2
    for h in results.get("hn", {}).get("hits", []):
        name = _clean_name(h.get("author"))
        if name:
            people[name] += 1

    canonical = [topic]
    for e in results.get("wikipedia", {}).get("entries", [])[:3]:
        if e.get("title") and e["title"] not in canonical:
            canonical.append(e["title"])

    repos = results.get("github", {}).get("repos", [])
    subs = results.get("reddit", {}).get("subreddits", [])
    top_people = [name for name, _ in people.most_common(8)]

    suggested = {
        "web_brave": [topic + " overview", topic + " limitations", topic + " criticism",
                      "how " + topic + " actually works"],
        "openalex": [topic] + ['author:"' + p + '"' for p in top_people[:3]],
        "arxiv": [topic] + ['au:"' + p + '"' for p in top_people[:3]],
        "hackernews": [topic],
        "stackexchange": [topic],
        "reddit": (["r/" + s["subreddit"] + " " + topic for s in subs[:3]] or [topic + " site:reddit.com"]),
        "github": [r["full_name"] for r in repos[:4]],
        "google_books": [topic],
    }

    framing_seeds = [
        {"id": "f_consensus", "kind": "mainstream", "seed": "The received/consensus view of " + topic + " is correct as usually stated.", "test_in": ["openalex", "web_brave"]},
        {"id": "f_minority", "kind": "heterodox", "seed": "The experts are wrong about " + topic + " in some load-bearing way.", "where_it_would_hide": ["reddit", "hackernews", "discourse", "retracted/dissenting papers"]},
        {"id": "f_practitioner", "kind": "field_report", "seed": "People who actually tried " + topic + " report something the summaries omit.", "where_it_would_hide": ["reddit", "stackexchange", "discourse", "youtube"]},
        {"id": "f_orthogonal", "kind": "reframe", "seed": topic + " is really a question about something else.", "test_in": ["openalex", "books"]},
    ]

    return {
        "topic": topic,
        "canonical_terms": canonical,
        "people": top_people,
        "github_repos": repos,
        "arxiv_papers": results.get("arxiv", {}).get("papers", []),
        "key_papers": results.get("openalex", {}).get("works", []),
        "hn_leads": results.get("hn", {}).get("hits", [])[:8],
        "subreddits": subs,
        "wikipedia": results.get("wikipedia", {}).get("entries", []),
        "suggested_queries": suggested,
        "framing_seeds": framing_seeds,
    }


def run_online(topic: str, timeout: float) -> Tuple[Dict[str, Any], Dict[str, str]]:
    resolvers = {
        "wikipedia": resolve_wikipedia,
        "hn": resolve_hn,
        "arxiv": resolve_arxiv,
        "github": resolve_github,
        "openalex": resolve_openalex,
        "reddit": resolve_reddit,
    }
    results: Dict[str, Any] = {}
    status: Dict[str, str] = {}
    for name, fn in resolvers.items():
        try:
            payload, st = fn(topic, timeout)
            results[name] = payload
            status[name] = st
        except Exception as e:  # noqa: BLE001 - best-effort by design
            results[name] = {}
            status[name] = "failed: " + type(e).__name__
    return results, status


def offline_plan(topic: str) -> Dict[str, Any]:
    plan = build_plan(topic, {})
    return plan


def load_env() -> None:
    """Populate os.environ from the nearest .env (walking up), without overriding real env."""
    d = os.path.dirname(os.path.realpath(__file__))
    for _ in range(8):
        p = os.path.join(d, ".env")
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, _, v = line.partition("=")
                        k = k.strip()
                        cut = v.find(" #")
                        if cut != -1:
                            v = v[:cut]
                        v = v.strip().strip('"').strip("'")
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            except OSError:
                pass
            return
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent


def main(argv: Optional[List[str]] = None) -> int:
    load_env()
    ap = argparse.ArgumentParser(description="Resolve a topic to concrete entities before searching.")
    ap.add_argument("topic", help="the research topic")
    ap.add_argument("--offline", action="store_true", help="skip all network calls; emit a template plan")
    ap.add_argument("--timeout", type=float, default=6.0, help="per-request timeout seconds (default 6)")
    args = ap.parse_args(argv)

    if args.offline:
        plan = offline_plan(args.topic)
        plan["sources_status"] = {k: "skipped_offline" for k in
                                  ["wikipedia", "hn", "arxiv", "github", "openalex", "reddit"]}
    else:
        results, status = run_online(args.topic, args.timeout)
        plan = build_plan(args.topic, results)
        plan["sources_status"] = status

    json.dump(plan, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
