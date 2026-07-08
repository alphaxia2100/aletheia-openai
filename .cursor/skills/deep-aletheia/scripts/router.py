#!/usr/bin/env python3
"""Deep Aletheia — channel router. Executes channels.json:selection_guidance instead of
leaving it a comment. Given a topic (+ optional framing), pick a SMALL, well-matched channel
set that always covers the three roles (independent web / a primary source / an un-laundered
community channel) and excludes off-topic indexes (the fix for "10 arXiv papers on a camera
topic"). The agent can override with --category or --channels.

Usage:
  router.py "topic" [--framing "..."] [--category NAME] [--json]
Prints the chosen channels (one per line), or full JSON with --json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

# channels that actually have a runnable search client (keep in sync with investigate.py)
AVAILABLE = {"brave", "marginalia", "duckduckgo", "openalex", "arxiv",
             "hackernews", "stackexchange", "github", "reddit", "youtube"}

KEYWORDS: Dict[str, List[str]] = {
    "software_technical_howto": [
        "code", "coding", "api", "programming", "program", "library", "framework", "python",
        "javascript", "typescript", "rust", "golang", " go ", "java", "c++", "docker",
        "kubernetes", "bug", "error", "exception", "install", "compiler", "algorithm",
        "software", "git", "database", "sql", "backend", "frontend", "devops", "linux",
        "regex", "runtime", "package", "sdk", "cli", "server", "latency"],
    "science_medicine_quantitative": [
        "study", "studies", "trial", "clinical", "drug", "dose", "gene", "protein", "gwas",
        "disease", "physics", "chemistry", "biology", "quantum", "statistical", "statistics",
        "dataset", "medicine", "medical", "health", "cancer", "neuron", "neural network",
        "experiment", "molecule", "enzyme", "vaccine", "epidemi", "meta-analysis", "rct",
        "biomarker", "cohort", "peer-reviewed", "efficacy"],
    "humanities_history_theory": [
        "history", "historical", "philosophy", "philosoph", "theory", "literature", "literary",
        "art", "culture", "cultural", "war", "ancient", "medieval", "century", "ethics",
        "moral", "religion", "religious", "political theory", "sociolog", "anthropolog",
        "rhetoric", "classic", "poetry", "novel", "empire", "revolution"],
    "products_consumer_lived_experience": [
        "best", "buy", "buying", "review", "camera", "laptop", "phone", "headphone", "monitor",
        "keyboard", "recommend", "worth it", "budget", "cheap", "price", "vs ", "versus",
        "product", "gear", "which", "beginner", "setup", "gaming", "car", "mattress", "brand",
        "quality", "durable", "reliable"],
    "current_trends_people": [
        "latest", "2026", "2025", "news", "trend", "who is", "startup", "launch", "release",
        "funding", "ceo", "recent", "today", "announced", "acquisition", "ipo", "layoff",
        "roadmap", "just released", "controversy", "drama"],
}
FRAMING_BOOST = {
    "an_un_laundered_channel": ["practitioner", "field report", "lived", "community",
                                "people who", "hands-on", "anecdot", "forum", "reddit",
                                "disconfirm", "criticism", "complaint", "failure"],
    "a_primary_source": ["primary", "paper", "papers", "academic", "peer", "study",
                         "evidence", "original", "dataset", "source code", "spec"],
}
# arXiv is CS/physics/math preprints — it has ~no biomedical/clinical/nutrition content, so on
# clearly-biomed topics it returns keyword-matched CS papers (e.g. "Head Gesture" for a nutrition
# query). Drop it there; openalex + web (which surfaces PubMed/Nature) carry the primaries.
BIOMED = ["clinical", "fasting", "diet", "dietary", "caloric", "calorie", "metabolic",
          "insulin", "glucose", "obesity", "weight loss", "patient", "disease", "drug",
          "dose", "nutrition", "cardiovascular", "cholesterol", "lipid", "cancer", "therapy",
          "trial", "medicine", "medical", "health", "blood", "hormone", "vitamin", "gut"]


def _cfg() -> dict:
    here = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(here, "..", "..", "channel-retrieval", "channels.json")
    with open(os.path.abspath(path), encoding="utf-8") as fh:
        return json.load(fh)


def classify(topic: str, framing: str = "") -> str:
    text = (topic + " " + framing).lower()
    # clinical/nutrition topics ("best diet for fat loss") hit product words (best/which/vs) and
    # were misfiled as consumer-trends -> firing off-domain channels. BIOMED signal wins outright.
    if sum(1 for kw in BIOMED if kw in text) >= 2:
        return "science_medicine_quantitative"
    scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in KEYWORDS.items()}
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else "current_trends_people"


def route(topic: str, framing: str = "", category: str = "",
          enabled_only: bool = True) -> dict:
    cfg = _cfg()
    guide = cfg["selection_guidance"]
    enabled = set(cfg.get("enabled", [])) if enabled_only else set(cfg["indexes"])
    usable = AVAILABLE & (enabled | {"duckduckgo", "marginalia"})  # keyless web always usable
    cat = category or classify(topic, framing)
    base = [c for c in guide["by_topic"].get(cat, []) if c in usable]

    roles = guide["always"]
    text = (topic + " " + framing).lower()
    chosen_roles: Dict[str, str] = {}
    for role, members in roles.items():
        present = [c for c in members if c in base]
        if present:
            chosen_roles[role] = present[0]
            continue
        # add the best available member of this role (respect framing boosts)
        boost = any(b in text for b in FRAMING_BOOST.get(role, []))
        pool = [c for c in members if c in usable]
        if pool:
            pick = pool[0]
            base.append(pick)
            chosen_roles[role] = pick
        if boost and pool and len(pool) > 1 and pool[1] not in base:
            base.append(pool[1])  # framing asked for extra depth in this role

    # dedupe, keep order
    seen, channels = set(), []
    for c in base:
        if c in usable and c not in seen:
            seen.add(c); channels.append(c)
    # biomed topics: arXiv is off-domain noise -> drop it (keep openalex + web)
    biomed = sum(1 for kw in BIOMED if kw in text) >= 2
    if biomed and "arxiv" in channels:
        channels = [c for c in channels if c != "arxiv"]
    return {"topic": topic, "framing": framing, "category": cat, "biomed": biomed,
            "channels": channels, "roles": chosen_roles}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia channel router.")
    ap.add_argument("topic")
    ap.add_argument("--framing", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--all", action="store_true", help="consider all channels, not just enabled")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = route(args.topic, args.framing, args.category, enabled_only=not args.all)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        for c in r["channels"]:
            print(c)
        sys.stderr.write("category=%s roles=%s\n" % (r["category"], r["roles"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
