#!/usr/bin/env python3
"""Aletheia run-metrics harness — measure ONE retrieval pass across channels.

Purpose: ground the "Deep Aletheia" redesign in numbers, not vibes. Runs the
enabled channel clients in parallel for a query and reports the metrics that
actually predict survey quality:

  yield/latency/errors per channel   -> which channels pull weight vs. stall
  unique_domains / index_groups      -> REAL diversity (not fake same-index dup)
  echo_ratio (voice_key collapse)    -> "40 blogs, 1 origin" detection
  dup_rate / top_domain_share        -> redundancy + concentration
  relevance_median / noise_frac      -> on-topic-ness of the raw pull
  read_probe success_rate            -> can we actually READ the top hits?

Usage:
  run_metrics.py "query" [--channels a,b] [--limit N] [--read-k K] [--out f.json]
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCR = os.path.join(REPO, ".cursor", "skills", "channel-retrieval", "scripts")
PROV = os.path.join(REPO, ".cursor", "skills", "provenance-audit", "scripts")
for p in (SCR, PROV):
    if p not in sys.path:
        sys.path.insert(0, p)

import dedupe  # noqa: E402
import rerank  # noqa: E402


def _search(mod: str, q: str, n: int, t: float):
    return getattr(importlib.import_module(mod), "search")(q, n, t)


def _yt(q: str, n: int, t: float):
    yt = importlib.import_module("youtube")
    return [{"index_of_origin": "youtube", "url": u, "title": "", "snippet": ""}
            for u in yt.yt_search(q, n, t)]


# channel name -> adapter(query, limit, timeout) -> list[record]
DISPATCH = {
    "brave": lambda q, n, t: _search("brave", q, n, t),
    "marginalia": lambda q, n, t: _search("web_marginalia", q, n, t),
    "duckduckgo": lambda q, n, t: _search("web_ddg", q, n, t),
    "openalex": lambda q, n, t: _search("openalex", q, n, t),
    "arxiv": lambda q, n, t: _search("arxiv", q, n, t),
    "hackernews": lambda q, n, t: _search("hn", q, n, t),
    "stackexchange": lambda q, n, t: _search("stackexchange", q, n, t),
    "github": lambda q, n, t: _search("github", q, n, t),
    "reddit": lambda q, n, t: importlib.import_module("reddit").search(q, n, t),
    "youtube": _yt,
}


def _load_cfg() -> dict:
    with open(os.path.join(os.path.dirname(SCR), "channels.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _run_channel(name: str, q: str, n: int, t: float):
    start = time.time()
    try:
        recs = DISPATCH[name](q, n, t) or []
        for r in recs:
            r.setdefault("_channel", name)
        return name, recs, time.time() - start, None
    except Exception as e:  # noqa: BLE001
        return name, [], time.time() - start, "%s: %s" % (type(e).__name__, str(e)[:120])


def measure(query: str, channels, limit: int, timeout: float, read_k: int) -> dict:
    cfg = _load_cfg()
    idx = cfg["indexes"]
    per: dict = {}
    all_recs: list = []
    with ThreadPoolExecutor(max_workers=max(len(channels), 1)) as ex:
        futs = [ex.submit(_run_channel, c, query, limit, timeout) for c in channels]
        for f in as_completed(futs):
            name, recs, dt, err = f.result()
            per[name] = {"n": len(recs), "latency_s": round(dt, 2), "error": err}
            all_recs += recs

    for r in all_recs:
        origin = r.get("index_of_origin") or r.get("_channel")
        meta = idx.get(origin, {})
        r["_index_group"] = meta.get("index_group", origin)
        r["_class"] = meta.get("class", "?")

    urls = [r.get("url", "") for r in all_recs if r.get("url")]
    canon = [dedupe.canonical_url(u) for u in urls]
    domains = Counter(dedupe.registrable_domain(u) for u in urls if u)
    groups = Counter(r["_index_group"] for r in all_recs)
    classes = Counter(r["_class"] for r in all_recs)
    voices = set(dedupe.voice_key(r) for r in all_recs)

    ranked = rerank.rerank(query, all_recs)
    scores = [r.get("relevance", 0) for r in ranked]
    nonzero = [s for s in scores if s > 0]

    m = {
        "query": query,
        "channels": channels,
        "limit": limit,
        "total_records": len(all_recs),
        "unique_urls": len(set(canon)),
        "dup_rate": round(1 - len(set(canon)) / max(len(canon), 1), 3),
        "unique_domains": len(domains),
        "top_domain_share": round(domains.most_common(1)[0][1] / max(sum(domains.values()), 1), 3) if domains else 0,
        "unique_index_groups": len(groups),
        "independent_voices": len(voices),
        "echo_ratio": round(1 - len(voices) / max(len(all_recs), 1), 3),
        "class_breakdown": dict(classes),
        "relevance_max": round(max(scores), 3) if scores else 0,
        "relevance_median": round(statistics.median(scores), 3) if scores else 0,
        "noise_frac": round(1 - len(nonzero) / max(len(scores), 1), 3),
        "per_channel": per,
    }

    if read_k > 0:
        read = importlib.import_module("read")
        rr = []
        for r in ranked[:read_k]:
            u = r.get("url", "")
            if not u.lower().startswith(("http://", "https://")):
                continue
            st = time.time()
            try:
                txt, method = read.read_url(u, timeout, 40000, False)
                rr.append({"url": u, "chars": len(txt), "method": method,
                           "ok": len(txt.strip()) >= 1500, "t": round(time.time() - st, 1)})
            except Exception as e:  # noqa: BLE001
                rr.append({"url": u, "chars": 0, "method": "FAIL",
                           "ok": False, "err": type(e).__name__})
        ok = sum(1 for x in rr if x["ok"])
        m["read_probe"] = {"attempted": len(rr), "success": ok,
                           "success_rate": round(ok / max(len(rr), 1), 3), "detail": rr}
    return m


def _summary(m: dict) -> str:
    lines = ["", "=" * 78, "QUERY: %s" % m["query"], "-" * 78,
             "%-14s %5s %9s  %s" % ("CHANNEL", "N", "LATENCY", "ERROR")]
    for name, s in sorted(m["per_channel"].items(), key=lambda kv: -kv[1]["n"]):
        lines.append("%-14s %5d %8.2fs  %s" % (name, s["n"], s["latency_s"], s["error"] or ""))
    lines += ["-" * 78,
              "total=%d  unique_urls=%d  dup_rate=%.0f%%  domains=%d  index_groups=%d" % (
                  m["total_records"], m["unique_urls"], m["dup_rate"] * 100,
                  m["unique_domains"], m["unique_index_groups"]),
              "independent_voices=%d  echo_ratio=%.0f%%  top_domain_share=%.0f%%" % (
                  m["independent_voices"], m["echo_ratio"] * 100, m["top_domain_share"] * 100),
              "relevance median=%.3f max=%.3f  noise_frac=%.0f%%  classes=%s" % (
                  m["relevance_median"], m["relevance_max"], m["noise_frac"] * 100, m["class_breakdown"])]
    if "read_probe" in m:
        rp = m["read_probe"]
        lines.append("read_probe: %d/%d ok (%.0f%%)" % (rp["success"], rp["attempted"], rp["success_rate"] * 100))
        for d in rp["detail"]:
            lines.append("   %-5s %6d ch  %-16s %s" % ("ok" if d["ok"] else "MISS", d["chars"],
                                                       d.get("method", ""), d["url"][:60]))
    lines.append("=" * 78)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia retrieval metrics harness.")
    ap.add_argument("query")
    ap.add_argument("--channels", default="", help="comma list; default = enabled channels")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--read-k", type=int, default=0, help="probe read success on top-K reranked")
    ap.add_argument("--out", default="", help="write metrics JSON here")
    args = ap.parse_args(argv)

    cfg = _load_cfg()
    channels = [c.strip() for c in args.channels.split(",") if c.strip()] or \
               [c for c in cfg["enabled"] if c in DISPATCH]
    m = measure(args.query, channels, args.limit, args.timeout, args.read_k)
    sys.stderr.write(_summary(m) + "\n")
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=2)
        sys.stderr.write("wrote %s\n" % args.out)
    print(json.dumps(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
