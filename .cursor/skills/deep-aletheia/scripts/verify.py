#!/usr/bin/env python3
"""Deep Aletheia — claim -> source verification gate.

From "Cited but Not Verified" (arXiv 2605.06635): surface-level citations mask factual
failures, and MORE search can LOWER accuracy — so a draft's claims must be checked against the
sources they cite, not just counted. This automates the deterministic layers:

  Link-Works    : the cited URL was actually read (note on disk) or is fetchable now.
  Relevant      : lexical overlap between the claim and the source text.
  support_signal: overlap strength + best-matching sentence (a proxy for entailment).

verify.py computes these and assigns a verdict (supported / weak / unsupported / broken) plus a
best-matching snippet. The verifier SUBAGENT then makes the final entailment call on the ones
flagged weak/unsupported (true Fact-Check is LLM judgment). Citation accuracy = supported/total.

Input JSONL (one per line):  {"claim": "...", "url": "..."}  or  {"claim":"...","urls":[...]}
Usage:
  verify.py --claims claims.jsonl [--node NODE_DIR | --reads-dir DIR] [--out verify.jsonl]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.realpath(__file__))
CH = os.path.join(HERE, "..", "..", "channel-retrieval", "scripts")
sys.path.insert(0, CH)
import rerank  # noqa: E402  (tokenize)
import read as readmod  # noqa: E402

SUPPORTED, WEAK = 0.55, 0.30


def _note_path(url: str, node: Optional[str], reads_dir: Optional[str]) -> Optional[str]:
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    for base in (os.path.join(node, "notes") if node else None, reads_dir):
        if base:
            p = os.path.join(base, h + ".md")
            if os.path.exists(p):
                return p
    return None


def _source_text(url: str, node, reads_dir, timeout: float) -> str:
    p = _note_path(url, node, reads_dir)
    if p:
        try:
            return open(p, encoding="utf-8").read()
        except OSError:
            pass
    try:  # fall back to a live read
        txt, _ = readmod.read_url(url, timeout, 40000, False)
        return txt
    except Exception:  # noqa: BLE001
        return ""


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.strip()) > 20]


def verify_claim(claim: str, urls: List[str], node, reads_dir, timeout: float) -> Dict[str, Any]:
    ctoks = set(rerank.tokenize(claim))
    best = {"overlap": 0.0, "url": "", "link_works": False, "snippet": ""}
    for url in urls:
        text = _source_text(url, node, reads_dir, timeout)
        link_works = len(text.strip()) >= 200
        if not link_works:
            if not best["url"]:
                best["url"] = url
            continue
        stoks = set(rerank.tokenize(text))
        overlap = len(ctoks & stoks) / max(len(ctoks), 1)
        # best matching sentence (proxy for the supporting passage)
        snip, snip_score = "", 0.0
        for s in _sentences(text):
            sc = len(ctoks & set(rerank.tokenize(s))) / max(len(ctoks), 1)
            if sc > snip_score:
                snip, snip_score = s, sc
        if overlap > best["overlap"]:
            best = {"overlap": round(overlap, 3), "url": url, "link_works": True,
                    "snippet": snip[:300], "snippet_score": round(snip_score, 3)}
    verdict = ("broken" if not best["link_works"] else
               "supported" if best["overlap"] >= SUPPORTED else
               "weak" if best["overlap"] >= WEAK else "unsupported")
    return {"claim": claim, "verdict": verdict, "overlap": best["overlap"],
            "url": best["url"], "link_works": best["link_works"],
            "snippet": best.get("snippet", ""),
            "needs_llm_check": verdict in ("weak", "unsupported")}


def run(claims: List[Dict[str, Any]], node, reads_dir, timeout: float) -> Dict[str, Any]:
    results = []
    for c in claims:
        urls = c.get("urls") or ([c["url"]] if c.get("url") else [])
        results.append(verify_claim(c.get("claim", ""), urls, node, reads_dir, timeout))
    n = len(results) or 1
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("supported", "weak", "unsupported", "broken")}
    return {"n_claims": len(results), "counts": counts,
            "citation_accuracy": round(counts["supported"] / n, 3),
            "needs_llm_check": sum(1 for r in results if r["needs_llm_check"]),
            "results": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia claim->source verification.")
    ap.add_argument("--claims", required=True, help="JSONL: {claim, url|urls}")
    ap.add_argument("--node", default="")
    ap.add_argument("--reads-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    claims = [json.loads(l) for l in open(args.claims, encoding="utf-8") if l.strip()]
    summary = run(claims, args.node or None, args.reads_dir or None, args.timeout)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for r in summary["results"]:
                fh.write(json.dumps(r) + "\n")
    sys.stderr.write(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
