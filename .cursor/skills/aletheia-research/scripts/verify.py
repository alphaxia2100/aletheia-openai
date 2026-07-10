#!/usr/bin/env python3
"""Deep Aletheia — claim -> source verification gate (deterministic layer).

From "Cited but Not Verified" (arXiv 2605.06635): surface-level citations mask factual
failures, and MORE search can LOWER accuracy — so a draft's claims must be checked against the
sources they cite, not just counted. Verification is TWO layers:

  Layer 1 — this script (deterministic, cheap, runs first):
    Link-Works : the cited URL was actually read (note on disk) or is fetchable now.
    Relevant   : lexical overlap between the claim and the source text is above threshold.
  It emits ONE of: broken (no readable source) / off_topic (readable but genuinely unrelated) /
  borderline (readable, low overlap — likely a paraphrase, so the LLM MUST still check it; never a
  silent drop) / relevant (on-topic). It returns the best-matching snippet as a lead for layer 2.
  Every result carries needs_llm_check=True.

  Layer 2 — the LLM verifier SUBAGENT (see deep-aletheia/SKILL.md step 6):
    Fact-Check : read the source and make the ENTAILMENT call, setting the final verdict
    supported / contradicted / unsupported. Citation accuracy = supported / total (LLM-set).

CRITICAL — why layer 1 NEVER emits "supported": lexical overlap proves a source is ON-TOPIC,
not that it SUPPORTS the claim. It cannot see polarity/negation or magnitude ("IF is superior"
vs "IF is NOT superior" share nearly all words; "doubles fat loss" vs a small effect look alike).
So support/entailment is exclusively layer 2's call — the deterministic pass must not certify it.

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

RELEVANT = 0.30    # at/above: clearly on-topic
BORDERLINE = 0.08  # readable but low overlap: could be a paraphrase — route to the LLM, do NOT drop
#: light suffix stemmer so morphological variants match (caloric~calorie, fasting~fast). This raises
#: layer-1 RECALL so a truly-supported paraphrase is not silently dropped as off_topic before the LLM
#: ever sees it (the audited false-negative). Not linguistically perfect — deliberately conservative.
#: deliberately excludes "al"/"ational" — they collide unrelated words (international↔internal,
#: national↔nation, rational↔ration) for little recall gain; the target folds survive via ic/ie/ing.
_SUFFIXES = ("ations", "ation", "izing", "ized", "izes", "ize", "ings", "ing",
             "ies", "ied", "ie", "ic", "es", "ly", "s", "e")


def _stem(w: str) -> str:
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def _stems(text: str) -> set:
    return {_stem(t) for t in rerank.tokenize(text)}


def _note_path(url: str, node: Optional[str], reads_dir: Optional[str]) -> Optional[str]:
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    filename = h + ".md"
    bases = [node, reads_dir]
    for base in bases:
        if not base:
            continue
        direct = os.path.join(base, "notes", filename) if base == node else os.path.join(base, filename)
        if os.path.exists(direct):
            return direct
        # The documented verify command points at the tree root while reads live under leaf
        # nodes. Search the subtree before doing a fragile/redundant live refetch.
        if os.path.isdir(base):
            for directory, _subdirs, files in os.walk(base):
                if filename in files:
                    return os.path.join(directory, filename)
    return None


def _source_text(url: str, node, reads_dir, timeout: float) -> str:
    p = _note_path(url, node, reads_dir)
    if p:
        try:
            with open(p, encoding="utf-8") as fh:
                return fh.read()
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
    ctoks = _stems(claim)                              # stemmed so paraphrase/inflection still matches
    best = {"overlap": 0.0, "url": "", "link_works": False, "snippet": ""}
    for url in urls:
        text = _source_text(url, node, reads_dir, timeout)
        link_works = len(text.strip()) >= 200
        if not link_works:
            if not best["url"]:
                best["url"] = url
            continue
        stoks = _stems(text)
        overlap = len(ctoks & stoks) / max(len(ctoks), 1)
        # best matching sentence (proxy for the supporting passage)
        snip, snip_score = "", 0.0
        for s in _sentences(text):
            sc = len(ctoks & _stems(s)) / max(len(ctoks), 1)
            if sc > snip_score:
                snip, snip_score = s, sc
        # record the first readable source even at overlap 0 (else a readable-but-off-topic
        # source is misreported as `broken`); later sources only replace it on higher overlap.
        if not best["link_works"] or overlap > best["overlap"]:
            best = {"overlap": round(overlap, 3), "url": url, "link_works": True,
                    "snippet": snip[:300], "snippet_score": round(snip_score, 3)}
    # broken -> no readable source; off_topic -> readable but genuinely unrelated;
    # borderline -> readable, low overlap (likely a paraphrase) so the LLM MUST check it, never drop;
    # relevant -> on-topic. SUPPORT/polarity is unconfirmed for all readable verdicts (LLM Fact-Check).
    if not best["link_works"]:
        verdict = "broken"
    elif best["overlap"] >= RELEVANT:
        verdict = "relevant"
    elif best["overlap"] >= BORDERLINE:
        verdict = "borderline"
    else:
        verdict = "off_topic"
    return {"claim": claim, "verdict": verdict, "overlap": best["overlap"],
            "url": best["url"], "link_works": best["link_works"],
            "snippet": best.get("snippet", ""),
            "needs_llm_check": True}  # entailment ALWAYS needs the LLM verifier


def run(claims: List[Dict[str, Any]], node, reads_dir, timeout: float) -> Dict[str, Any]:
    results = []
    for c in claims:
        urls = c.get("urls") or ([c["url"]] if c.get("url") else [])
        results.append(verify_claim(c.get("claim", ""), urls, node, reads_dir, timeout))
    n = len(results) or 1
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("relevant", "borderline", "off_topic", "broken")}
    return {"n_claims": len(results), "counts": counts,
            "on_topic_rate": round((counts["relevant"] + counts["borderline"]) / n, 3),
            "off_topic_or_broken": counts["off_topic"] + counts["broken"],
            "note": "Lexical pass: 'relevant'/'borderline' = on-topic (borderline = low overlap, "
                    "likely paraphrase). SUPPORT/polarity is NOT verified here — the LLM verifier "
                    "subagent must Fact-Check each 'relevant' AND 'borderline' claim.",
            "results": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia claim->source verification.")
    ap.add_argument("--claims", required=True, help="JSONL: {claim, url|urls}")
    ap.add_argument("--node", default="")
    ap.add_argument("--reads-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    with open(args.claims, encoding="utf-8") as fh:
        claims = [json.loads(l) for l in fh if l.strip()]
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
