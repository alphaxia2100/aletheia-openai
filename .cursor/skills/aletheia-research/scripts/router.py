#!/usr/bin/env python3
"""Aletheia Research — SCOPE-AWARE channel router.

Each run should fire only the channels the QUESTION needs — not all of them. Given a topic (+ optional
framing/angle), this classifies the question into one or two DOMAINS and returns a SMALL set that
covers the three roles (independent web / a domain-appropriate primary / an un-laundered community)
and EXCLUDES off-topic indexes (no arXiv on a nutrition question, no PubMed on a camera question, no
GitHub on a history question). The worker may override with --category or --channels.

Usage:  router.py "topic" [--framing "..."] [--category NAME] [--max N] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

# channels with a runnable search client (keep in sync with investigate.py DISPATCH)
AVAILABLE = {"brave", "duckduckgo", "marginalia", "openalex", "arxiv", "hackernews", "stackexchange",
             "github", "reddit", "youtube", "europepmc", "wikipedia", "crossref", "semanticscholar",
             "googlebooks", "gutenberg"}
WEB = ["brave", "duckduckgo", "marginalia"]          # independent-web role (always ≥1)

# Domain taxonomy: signals -> the domain-appropriate primary/community/color channels, and channels
# to keep OUT. Only channels that exist as clients are listed. 'general' is the fallback.
DOMAINS: Dict[str, Dict[str, List[str]]] = {
    "biomed": dict(
        signals=["clinical", "health", "disease", "drug", "dose", "patient", "trial", "rct", "cohort",
                 "diet", "dietary", "nutrition", "fasting", "caloric", "calorie", "metabolic", "insulin",
                 "glucose", "obesity", "cancer", "cardiovascular", "cholesterol", "vaccine", "gene",
                 "protein", "biomarker", "supplement", "cognition", "therapy", "efficacy", "medicine", "medical"],
        primary=["europepmc", "openalex"], community=["reddit"], color=[],
        exclude=["arxiv", "github", "stackexchange", "gutenberg"]),
    "cs_software": dict(
        signals=["code", "coding", "api", "programming", "library", "framework", "python", "javascript",
                 "typescript", "rust", "golang", "compiler", "algorithm", "software", "docker", "kubernetes",
                 "database", "sql", "backend", "frontend", "devops", "sdk", "cli", "server", "latency",
                 "machine learning", "deep learning", "neural", "transformer", "llm", "model", "embedding", "agent"],
        primary=["arxiv", "semanticscholar", "openalex"], community=["stackexchange", "github", "hackernews"],
        color=[], exclude=["europepmc", "googlebooks", "gutenberg"]),
    "science_physical": dict(
        signals=["physics", "chemistry", "chemical", "math", "mathematics", "quantum", "astronomy",
                 "astrophysics", "materials", "geology", "climate model", "particle", "theorem", "equation"],
        primary=["arxiv", "openalex"], community=["stackexchange"], color=[],
        exclude=["europepmc", "github", "gutenberg"]),
    "humanities_history": dict(
        signals=["history", "historical", "philosophy", "philosoph", "literature", "literary", "ancient",
                 "medieval", "century", "empire", "revolution", "war", "religion", "religious", "art",
                 "culture", "rhetoric", "classic", "poetry", "novel", "dynasty", "renaissance"],
        primary=["wikipedia", "googlebooks", "openalex"], community=["reddit"], color=[],
        exclude=["arxiv", "github", "stackexchange", "europepmc"]),
    "products_consumer": dict(
        signals=["best", "buy", "buying", "review", "camera", "laptop", "phone", "headphone", "monitor",
                 "keyboard", "recommend", "worth it", "budget", "cheap", "price", " vs ", "versus", "gear",
                 "which", "beginner", "gaming", "car", "mattress", "brand", "durable", "reliable"],
        primary=[], community=["reddit", "hackernews"], color=["youtube"],
        exclude=["arxiv", "openalex", "europepmc", "github", "gutenberg", "crossref", "semanticscholar"]),
    "finance_business": dict(
        signals=["stock", "shares", "earnings", "revenue", "valuation", "market cap", "ipo", "acquisition",
                 "10-k", "10-q", "sec filing", "balance sheet", "profit", "investor", "hedge fund", "startup funding"],
        primary=["openalex"], community=["reddit", "hackernews"], color=[],
        exclude=["arxiv", "europepmc", "github", "gutenberg"]),  # SEC EDGAR client: see docs/channel-proposals.md
    "legal": dict(
        signals=["court", "lawsuit", "ruling", "statute", "plaintiff", "defendant", "liability", "copyright",
                 "patent case", "supreme court", "appeal", "jurisdiction", "precedent", "litigation"],
        primary=["openalex"], community=["reddit"], color=[],
        exclude=["arxiv", "github", "europepmc", "gutenberg"]),  # CourtListener client: see channel-proposals
    "policy_econ": dict(
        signals=["policy", "economic", "economy", "gdp", "inflation", "unemployment", "regulation", "tax",
                 "labor", "welfare", "subsidy", "trade", "productivity", "carbon", "emissions", "governance"],
        primary=["openalex", "crossref"], community=["reddit", "hackernews"], color=[],
        exclude=["github", "gutenberg", "europepmc"]),
    "current_events": dict(
        signals=["latest", "2026", "2025", "news", "trend", "who is", "launch", "released", "announced",
                 "recent", "today", "ceo", "layoff", "controversy", "just released", "roadmap"],
        primary=[], community=["reddit", "hackernews"], color=["youtube"],
        exclude=["arxiv", "europepmc", "gutenberg", "googlebooks"]),
    "general": dict(signals=[], primary=["openalex", "wikipedia"], community=["reddit"], color=[], exclude=[]),
}
# a practitioner/field-report/adversary framing pulls in an extra un-laundered community voice
_COMMUNITY_FRAMING = ["practitioner", "field report", "lived", "hands-on", "forum", "review", "complaint",
                      "anecdot", "people who", "disconfirm", "criticism", "adversary", "real-world"]


def _domains_for(text: str) -> List[str]:
    scores = {d: sum(1 for kw in cfg["signals"] if kw in text) for d, cfg in DOMAINS.items() if cfg["signals"]}
    ranked = sorted((d for d, s in scores.items() if s > 0), key=lambda d: -scores[d])
    if not ranked:
        return ["general"]
    picks = [ranked[0]]
    if len(ranked) > 1 and scores[ranked[1]] >= 2:      # a second domain only if clearly present
        picks.append(ranked[1])
    return picks


def classify(topic: str, framing: str = "") -> str:
    return _domains_for((topic + " " + framing).lower())[0]


def route(topic: str, framing: str = "", category: str = "", enabled_only: bool = True,
          max_channels: int = 6) -> dict:
    text = (topic + " " + framing).lower()
    doms = [category] if category in DOMAINS else _domains_for(text)
    exclude = set().union(*[set(DOMAINS[d]["exclude"]) for d in doms])

    picks: List[str] = ["brave"]                                    # web role (always)
    if max_channels >= 5:
        picks.append("duckduckgo")                                 # a 2nd independent web index for breadth
    for d in doms:                                                  # domain primary + community + color
        picks += DOMAINS[d]["primary"] + DOMAINS[d]["community"] + DOMAINS[d]["color"]
    if any(b in text for b in _COMMUNITY_FRAMING) and "reddit" not in picks:
        picks.append("reddit")                                     # framing wants an un-laundered voice

    seen, channels = set(), []
    for c in picks:
        if c in AVAILABLE and c not in seen:
            seen.add(c); channels.append(c)
    # role guarantees (in case a domain left one empty)
    if not any(c in WEB for c in channels):
        channels.insert(0, "brave")
    if not any(c in ("reddit", "hackernews", "stackexchange") for c in channels):
        channels.append("reddit")
    if doms[0] not in ("products_consumer", "current_events") and \
       not any(c in ("openalex", "europepmc", "arxiv", "semanticscholar", "crossref", "wikipedia", "googlebooks") for c in channels):
        channels.append("openalex")
    channels = channels[:max_channels]
    excluded = sorted(c for c in AVAILABLE if c in exclude and c not in channels)
    return {"topic": topic, "framing": framing, "domains": doms, "category": doms[0],
            "channels": channels, "excluded": excluded}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia Research scope-aware channel router.")
    ap.add_argument("topic")
    ap.add_argument("--framing", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--max", type=int, default=6)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = route(args.topic, args.framing, args.category, max_channels=args.max)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        for c in r["channels"]:
            print(c)
        sys.stderr.write("domains=%s  excluded=%s\n" % (r["domains"], r["excluded"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
