#!/usr/bin/env python3
"""Deep Aletheia — authority/class-aware ranking + class-budgeted read selection.

v1's TF-IDF rerank put Medium listicles above arXiv papers and blew the whole read budget on
content farms (measured; independently confirmed by Anthropic's "SEO farms over academic PDFs").
This ranker keeps lexical relevance but combines it with:
  - domain AUTHORITY (arxiv/doi/.edu/.gov/github high; medium/geeksforgeeks/etc. demoted),
  - citation count (log-scaled, for academic records),
  - channel CLASS (evidence > lead_gen > color).
Then select_reads() spends the read budget with CLASS QUOTAS so primaries are always read, not
crowded out by high-lexical-score blogs.

Usage:
  rank.py "query" --sources sources.jsonl [--select K]   # ranked JSONL to stdout
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "channel-retrieval", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "provenance-audit", "scripts"))
import rerank  # noqa: E402
import dedupe  # noqa: E402

# Relevance GATES quality (multiplicative): authority/class/citations reorder among
# reasonably-relevant items but can't rescue a near-zero-relevance source. This is the fix
# for authority promoting authoritative-but-off-topic papers when lexical relevance is noisy.
REL_FLOOR = 0.2  # authority still matters a little even at rel=0
CLASS_W = {"evidence": 1.0, "lead_gen": 0.6, "color": 0.3, "?": 0.5}

AUTH_HIGH = {  # primary / near-primary
    "arxiv.org", "doi.org", "openalex.org", "semanticscholar.org", "nature.com",
    "science.org", "acm.org", "ieee.org", "ncbi.nlm.nih.gov", "nih.gov", "pnas.org",
    "cell.com", "plos.org", "biorxiv.org", "medrxiv.org", "jstor.org", "springer.com",
    "sciencedirect.com", "europepmc.org", "aclanthology.org", "openreview.net"}
AUTH_MED = {  # reputable orgs / official docs / code
    "github.com", "gitlab.com", "python.org", "mozilla.org", "w3.org", "ietf.org",
    "kernel.org", "postgresql.org", "anthropic.com", "openai.com", "deepmind.com",
    "cognition.ai", "stanford.edu", "mit.edu", "berkeley.edu"}
FARM = {  # low-authority aggregators / SEO-prone
    "medium.com", "dev.to", "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com",
    "javatpoint.com", "simplilearn.com", "guru99.com", "baeldung.com", "toptal.com",
    "analyticsvidhya.com", "kdnuggets.com", "towardsdatascience.com", "hackernoon.com",
    "quora.com", "linkedin.com"}


def authority(url: str) -> float:
    dom = dedupe.registrable_domain(url or "")
    if not dom:
        return 0.5
    if dom in AUTH_HIGH or dom.endswith(".edu") or dom.endswith(".gov") or dom.endswith(".ac.uk"):
        return 1.0
    if dom in AUTH_MED:
        return 0.8
    if dom in FARM:
        return 0.2
    return 0.5


def _class_of(r: Dict[str, Any]) -> str:
    return r.get("channel_class") or r.get("_class") or "?"


def rank(query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = rerank.rerank(query, records)  # sets r["relevance"]; TF-IDF cosine
    maxrel = max((r.get("relevance", 0) for r in ranked), default=0) or 1.0
    out = []
    for r in ranked:
        rel = r.get("relevance", 0) / maxrel
        auth = authority(r.get("url", ""))
        cite = min(math.log1p(r.get("cited_by_count", 0) or 0) / math.log1p(1000), 1.0)
        cls = _class_of(r)
        rel_base = REL_FLOOR + (1 - REL_FLOOR) * rel           # relevance gate
        quality = 0.5 + 0.5 * auth + 0.2 * cite + 0.2 * CLASS_W.get(cls, 0.5)
        score = rel_base * quality * (1.05 if r.get("primary") else 1.0)
        rr = dict(r)
        rr["_relnorm"] = round(rel, 3); rr["_authority"] = auth
        rr["score"] = round(score, 4)
        out.append(rr)
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def select_reads(ranked: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """Spend the read budget with class quotas so primaries are read, not crowded out.
    >=60% evidence, >=1 un-laundered (lead_gen/color), color capped at ~25%."""
    if k <= 0:
        return []
    ev = [r for r in ranked if _class_of(r) == "evidence"]
    lg = [r for r in ranked if _class_of(r) == "lead_gen"]
    co = [r for r in ranked if _class_of(r) == "color"]
    want_ev = max(1, math.ceil(0.6 * k))
    want_co = max(0, int(0.25 * k))
    pick: List[Dict[str, Any]] = []
    seen = set()

    def take(pool, n):
        for r in pool:
            if n <= 0:
                break
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u); pick.append(r); n -= 1

    take(ev, want_ev)
    take(lg, max(1, k // 4))          # ensure some un-laundered lead-gen
    take(co, want_co)
    # fill the rest by pure score
    for r in ranked:
        if len(pick) >= k:
            break
        u = r.get("url", "")
        if u and u not in seen:
            seen.add(u); pick.append(r)
    pick.sort(key=lambda r: r["score"], reverse=True)
    return pick[:k]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Authority/class-aware ranking.")
    ap.add_argument("query")
    ap.add_argument("--sources", help="JSONL (default stdin)")
    ap.add_argument("--select", type=int, default=0, help="also emit read-selection of size K")
    args = ap.parse_args(argv)
    if args.sources:
        with open(args.sources, encoding="utf-8") as raw:
            records = [json.loads(l) for l in raw if l.strip()]
    else:
        records = [json.loads(l) for l in sys.stdin if l.strip()]
    ranked = rank(args.query, records)
    if args.select:
        sel = set(id(r) for r in select_reads(ranked, args.select))
        for r in ranked:
            r["_read"] = id(r) in sel
    for r in ranked:
        print(json.dumps(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
