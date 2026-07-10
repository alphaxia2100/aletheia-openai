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
from typing import Any, Dict, List, Optional

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
    "sciencedirect.com", "europepmc.org", "aclanthology.org", "openreview.net",
    # biomed/clinical journals + evidence synthesis (audit: AUTH list was CS-biased)
    "thelancet.com", "bmj.com", "jamanetwork.com", "nejm.org", "cochranelibrary.com",
    "cochrane.org", "annualreviews.org", "wiley.com", "onlinelibrary.wiley.com", "oup.com",
    "tandfonline.com", "ahajournals.org", "diabetesjournals.org", "physiology.org", "asm.org",
    # regulators / health agencies — the decisive/settling sources on biomed & safety questions
    # (europa.eu covers EFSA/EMA/ECDC subdomains; *.gov is already credited via the .gov suffix)
    "who.int", "europa.eu", "nice.org.uk"}
AUTH_MED = {  # reputable orgs / official docs / code / wire services
    "github.com", "gitlab.com", "python.org", "mozilla.org", "w3.org", "ietf.org",
    "kernel.org", "postgresql.org", "anthropic.com", "openai.com", "deepmind.com",
    "cognition.ai", "stanford.edu", "mit.edu", "berkeley.edu",
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk"}
FARM = {  # low-authority aggregators / SEO-prone / SECONDARY research-summarizers (never a primary)
    "medium.com", "dev.to", "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com",
    "javatpoint.com", "simplilearn.com", "guru99.com", "baeldung.com", "toptal.com",
    "analyticsvidhya.com", "kdnuggets.com", "towardsdatascience.com", "hackernoon.com",
    "quora.com", "linkedin.com",
    # secondary AI/research summarizers — they restate primaries; chase the primary, never cite these
    "consensus.app", "elicit.com", "elicit.org", "scholarcy.com", "scite.ai",
    "connectedpapers.com", "researchrabbit.ai", "semanticscholar.org.reader", "perplexity.ai"}


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


def _focus_stem(token: str) -> str:
    """Fold only common plurals for the hard subject gate; avoid broad semantic collisions."""
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 4:
        return token[:-1]
    return token


def _subject_hits(record: Dict[str, Any], subject_terms: List[str]) -> int:
    authors = " ".join(a.get("name", "") if isinstance(a, dict) else str(a)
                       for a in (record.get("authors") or []))
    text = " ".join([str(record.get("title") or ""), str(record.get("snippet") or ""), authors])
    doc = {_focus_stem(t) for t in rerank.tokenize(text)}
    hits = 0
    for term in subject_terms:
        parts = {_focus_stem(t) for t in rerank.tokenize(term)}
        if parts and parts <= doc:
            hits += 1
    return hits


def rank(query: str, records: List[Dict[str, Any]],
         subject_terms: Optional[List[str]] = None,
         required_subject_terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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
        if subject_terms:
            rr["_subject_hits"] = _subject_hits(rr, subject_terms)
            rr["_subject_term_count"] = len(subject_terms)
        if required_subject_terms:
            rr["_required_subject_hits"] = _subject_hits(rr, required_subject_terms)
            rr["_required_subject_term_count"] = len(required_subject_terms)
        rr["score"] = round(score, 4)
        out.append(rr)
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


#: hard relevance gate for READS: authority can reorder among on-topic hits but must NEVER buy a read
#: slot for an off-topic source. Fixes the audited failure where a high-authority but off-topic paper
#: (or a secondary aggregator) got read while the decisive on-topic primary sat unread.
REL_READ = 0.25


def select_reads(ranked: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """Spend the read budget with class quotas so primaries are read, not crowded out.
    >=60% evidence, >=1 un-laundered (lead_gen/color), color capped at ~25%. RELEVANCE-GATED:
    only sources at/above REL_READ (normalized relevance) are eligible, so authority can't pull an
    off-topic source into a read slot. A thin result set returns fewer than k reads rather than
    spending the remaining budget on noise."""
    if k <= 0:
        return []
    pool = [r for r in ranked if r.get("_relnorm", 0) >= REL_READ]
    # When the orchestrator supplied a root-topic signature, a source must match at least one of its
    # core terms. Returning fewer reads is preferable to spending a bounded budget on a paper that
    # merely shares generic words such as "password" or "threat model".
    if any("_subject_hits" in r for r in pool):
        # A multi-facet subject requires two matches. A lone generic overlap (e.g. "synced" in a
        # TOTP clock question) must not become eligible merely because every better hit was absent.
        # Thin pools intentionally return no reads; the worker can chase a known primary instead.
        focus_level = min(2, max((r.get("_subject_term_count", 0) for r in pool), default=0))
        pool = [r for r in pool if focus_level and r.get("_subject_hits", 0) >= focus_level]
    if any("_required_subject_hits" in r for r in pool):
        # Named-entity topics must actually mention their named subject. Otherwise a generic item
        # such as a UK public-library review can satisfy two broad facets of a Carnegie-US query.
        pool = [r for r in pool if r.get("_required_subject_hits", 0) >= 1]
    if not pool:
        return []
    ev = [r for r in pool if _class_of(r) == "evidence"]
    lg = [r for r in pool if _class_of(r) == "lead_gen"]
    want_ev = max(1, math.ceil(0.6 * k))
    color_cap = max(0, int(0.25 * k))
    pick: List[Dict[str, Any]] = []
    seen = set()

    def take(candidates, n):
        for r in candidates:
            if n <= 0 or len(pick) >= k:
                break
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u); pick.append(r); n -= 1

    take(ev, want_ev)
    if len(pick) < k:
        take(lg, 1)                    # one un-laundered lead when the budget has room
    # Fill by score without violating the color cap. Quota picks stay selected; sorting before
    # slicing used to silently discard them again when a high-scoring color item was present.
    for r in pool:
        if len(pick) >= k:
            break
        u = r.get("url", "")
        if not u or u in seen:
            continue
        if _class_of(r) == "color" and sum(_class_of(x) == "color" for x in pick) >= color_cap:
            continue
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
