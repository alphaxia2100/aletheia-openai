#!/usr/bin/env python3
"""Score a completed Deep Aletheia run — the deterministic half of the Anthropic-style rubric
plus Aletheia-specific epistemic metrics. (Factual accuracy & completeness are LLM-judge
dimensions added by a judging subagent; this covers what can be computed.)

Metrics:
  citation_accuracy   supported / total          (from verify.jsonl)
  source_quality      share of sources that are evidence-class AND high-authority
  independence        1 - echo_ratio             (voice_key over the global source index)
  framing_coverage    # root framings explored, # leaves with findings
  disconfirmation     an adversary branch exists AND produced findings
  tree                nodes / depth / leaves / reads

Usage:  score_run.py RUN_DIR
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from collections import Counter

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, ".cursor", "skills", "provenance-audit", "scripts"))
sys.path.insert(0, os.path.join(REPO, ".cursor", "skills", "deep-aletheia", "scripts"))
import dedupe  # noqa: E402
import rank as rankmod  # noqa: E402


def _jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def score(run: str) -> dict:
    cfg = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
    idx = _jsonl(os.path.join(run, "index", "sources.jsonl"))

    # independence + source quality over the global index
    voices = {dedupe.voice_key(r) for r in idx} if idx else set()
    echo = round(1 - len(voices) / len(idx), 3) if idx else 0
    ev = sum(1 for r in idx if (r.get("_class") or r.get("channel_class")) == "evidence")
    hi = sum(1 for r in idx if rankmod.authority(r.get("url", "")) >= 0.8)
    quality = round(sum(1 for r in idx if (r.get("_class") or r.get("channel_class")) == "evidence"
                        and rankmod.authority(r.get("url", "")) >= 0.8) / len(idx), 3) if idx else 0

    # tree walk (+ depth metrics: is 0.2 actually deeper than 0.1's single-pass leaves?)
    nodes = leaves = with_find = maxdepth = reads = 0
    adversary = adversary_find = False
    root_framings = []
    leaf_rounds, leaf_reads, reads_by_depth = [], [], {}
    ev_children = apriori_children = 0            # evidence-driven vs a-priori decompositions
    q_asked = q_answered = thin_children = thin_unresolved = 0
    for d, _s, fs in os.walk(os.path.join(run, "tree")):
        if "status.json" not in fs:
            continue
        st = json.load(open(os.path.join(d, "status.json"), encoding="utf-8"))
        depth = int(st.get("depth", 0))
        nodes += 1
        maxdepth = max(maxdepth, depth)
        has_children = os.path.isdir(os.path.join(d, "children")) and any(
            os.path.isdir(os.path.join(d, "children", c)) for c in os.listdir(os.path.join(d, "children")))
        fpath = os.path.join(d, "findings.md")
        find_bytes = os.path.getsize(fpath) if os.path.exists(fpath) else 0
        has_find = find_bytes > 0
        n_read = int(st.get("n_read", 0) or 0)
        reads += n_read
        reads_by_depth[depth] = reads_by_depth.get(depth, 0) + n_read
        q_asked += len(_jsonl(os.path.join(d, "questions.jsonl")))
        n_ans = len(_jsonl(os.path.join(d, "answers.jsonl")))
        q_answered += n_ans
        if not has_children:
            leaves += 1
            leaf_rounds.append(int(st.get("rounds", 0) or 0))
            leaf_reads.append(n_read)
            if has_find:
                with_find += 1
        elif depth >= 1:  # internal, non-root: evidence-driven if it proposed after a scout look
            ev_children += 1 if os.path.exists(os.path.join(d, "proposal.json")) else 0
            apriori_children += 0 if os.path.exists(os.path.join(d, "proposal.json")) else 1
        if depth >= 1 and find_bytes < 120:       # thin child; resolved iff it answered a question
            thin_children += 1
            thin_unresolved += 1 if n_ans == 0 else 0
        if depth == 1:
            root_framings.append(st.get("qid", ""))
        qid = (st.get("qid") or "").lower()
        if any(k in qid for k in ("advers", "disconfirm", "skeptic")):  # the disconfirming framing
            adversary = True
            adversary_find = adversary_find or has_find

    def _stats(xs):
        return {"mean": round(statistics.mean(xs), 2), "median": statistics.median(xs),
                "min": min(xs), "max": max(xs)} if xs else {}
    _mean_reads = statistics.mean(leaf_reads) if leaf_reads else 0
    depth_metrics = {
        "rounds_per_leaf": _stats(leaf_rounds),               # 0.1 == 1.0 everywhere; 0.2 should be > 1
        "reads_per_leaf": {**_stats(leaf_reads),
                           # coefficient of variation: lower = more uniform scrutiny per leaf
                           "cv": round(statistics.pstdev(leaf_reads) / _mean_reads, 3) if _mean_reads else None},
        "reads_by_depth": {str(k): reads_by_depth[k] for k in sorted(reads_by_depth)},  # equal time/level
        "evidence_driven_children": ev_children, "a_priori_children": apriori_children,
        "clarification": {"asked": q_asked, "answered": q_answered,
                          "thin_children": thin_children, "thin_unresolved": thin_unresolved,
                          "coverage": round((thin_children - thin_unresolved) / thin_children, 3)
                          if thin_children else None},
    }

    ver = _jsonl(os.path.join(run, "verify.jsonl"))
    # lexical layer emits relevant/off_topic/broken; the LLM verifier upgrades each 'relevant'
    # to a final verdict supported/contradicted/unsupported (see deep-aletheia/SKILL.md step 6).
    vc = Counter(r.get("verdict") for r in ver)
    supported, contradicted, unsupported = vc["supported"], vc["contradicted"], vc["unsupported"]
    relevant = vc["relevant"]  # on-topic but still awaiting the LLM Fact-Check
    bad = vc["off_topic"] + vc["broken"]
    llm_done = supported + contradicted + unsupported
    # citation accuracy is only meaningful once the LLM pass has run; None = not yet Fact-Checked
    cit_acc = round(supported / len(ver), 3) if (ver and llm_done) else None
    on_topic = round((len(ver) - bad) / len(ver), 3) if ver else None

    brief = os.path.join(run, "brief.md")
    btext = open(brief, encoding="utf-8").read().lower() if os.path.exists(brief) else ""
    sections = {s: (s in btext) for s in ("agreement", "disagreement", "unverified")}

    return {
        "topic": cfg.get("topic"), "version": cfg.get("version"),
        "citation_accuracy": cit_acc, "on_topic_rate": on_topic,
        "verified_claims": len(ver), "off_topic_or_broken_citations": bad,
        "verdicts": {"supported": supported, "contradicted": contradicted,
                     "unsupported": unsupported, "awaiting_llm_check": relevant},
        "source_quality": quality, "sources": len(idx),
        "independence": round(1 - echo, 3), "echo_ratio": echo, "unique_voices": len(voices),
        "framing_coverage": {"root_framings": len(root_framings), "leaves": leaves,
                             "leaves_with_findings": with_find},
        "disconfirmation": {"adversary_branch": adversary, "produced_findings": adversary_find},
        "depth": depth_metrics,
        "tree": {"nodes": nodes, "max_depth": maxdepth, "leaves": leaves, "reads": reads},
        "brief_sections": sections,
        "evidence_sources": ev, "high_authority_sources": hi,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score a Deep Aletheia run.")
    ap.add_argument("run")
    args = ap.parse_args(argv)
    print(json.dumps(score(args.run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
