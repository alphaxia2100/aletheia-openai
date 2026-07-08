#!/usr/bin/env python3
"""Rerank/compress retrieved records by relevance BEFORE reading them.

Cuts noise and tokens: score each record against the query with TF-IDF cosine
(pure stdlib, no embeddings, no deps), sort desc, add a `relevance` field, and
optionally keep only the top-k or above a min score. This is the free version of
the embeddings-rerank step in gpt-researcher's ContextCompressor; swap in an
embeddings model later for semantic (not just lexical) matching.

Usage:
  rerank.py "query" --sources sources.jsonl [--top-k 20] [--min-score 0.05]
  cat sources.jsonl | rerank.py "query" --top-k 20

Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from typing import Any, Dict, List

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "with", "as", "by", "at", "it", "this", "that", "how",
    "what", "why", "do", "does", "vs", "via", "from", "into",
}


def tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) > 1 and w not in _STOP]


def _doc_text(rec: Dict[str, Any]) -> str:
    authors = " ".join(a.get("name", "") if isinstance(a, dict) else str(a)
                       for a in (rec.get("authors") or []))
    return " ".join([rec.get("title", ""), rec.get("snippet", ""), authors])


def rerank(query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = [tokenize(_doc_text(r)) for r in records]
    n = len(docs)
    if n == 0:
        return []
    df: Counter = Counter()
    for toks in docs:
        for term in set(toks):
            df[term] += 1
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    def vec(tokens: List[str]) -> Dict[str, float]:
        tf = Counter(tokens)
        v = {t: cnt * idf.get(t, math.log((n + 1) / 1) + 1.0) for t, cnt in tf.items()}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        return {t: w / norm for t, w in v.items()}

    qv = vec(tokenize(query))
    out = []
    for rec, toks in zip(records, docs):
        dv = vec(toks)
        score = sum(qv.get(t, 0.0) * w for t, w in dv.items())
        r = dict(rec)
        r["relevance"] = round(score, 4)
        out.append(r)
    out.sort(key=lambda r: r["relevance"], reverse=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TF-IDF cosine rerank of source records.")
    ap.add_argument("query")
    ap.add_argument("--sources", help="JSONL file (default: stdin)")
    ap.add_argument("--top-k", type=int, default=0, help="keep only top K (0 = all)")
    ap.add_argument("--min-score", type=float, default=0.0, help="drop below this relevance")
    args = ap.parse_args(argv)

    raw = open(args.sources, "r", encoding="utf-8") if args.sources else sys.stdin
    records = [json.loads(line) for line in raw if line.strip()]
    if args.sources:
        raw.close()

    ranked = rerank(args.query, records)
    if args.min_score > 0:
        ranked = [r for r in ranked if r["relevance"] >= args.min_score]
    if args.top_k > 0:
        ranked = ranked[: args.top_k]
    for r in ranked:
        sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
