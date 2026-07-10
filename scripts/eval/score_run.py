#!/usr/bin/env python3
"""Compatibility scorer for completed Aletheia runs.

Tree/process diagnostics remain here for historical comparisons.  Citation headlines are delegated
to :mod:`evaluator_v2`, which in turn calls the scorer shipped with the current skill and requires a
valid final-brief claim-scope attestation.  This prevents the three repository scorers from silently
using different citation denominators.

Metrics:
  citation_precision  supported / finally-judged   (of the claims Fact-Checked, the fraction that hold)
  citation_coverage   finally-judged / on-topic    (how much of the checkable set was actually checked)
  citation_accuracy   the headline — = precision, but ONLY once coverage is complete (else None)
  citation_denominator  # load-bearing claims that received a final verdict (the stated denominator)
                        Precision-only is gameable (SAFE/VeriScore/FactScore pair it with a denominator
                        and coverage); true recall of UNSTATED claims isn't machine-measurable here.
  source_quality      share of sources that are evidence-class AND high-authority
  independence        1 - echo_ratio (voice_key identity) AND origin_independence (structural,
                      shared-origin clusters — the "40 domains, 1 origin" catch voice_key misses)
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
import provenance_graph as pg  # noqa: E402  (structural shared-origin independence)
import evaluator_v2  # noqa: E402  (canonical, fail-closed citation scorer)


def _jsonl(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def score(run: str, require_scope: bool = True) -> dict:
    with open(os.path.join(run, "run.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    idx = _jsonl(os.path.join(run, "index", "sources.jsonl"))

    # independence + source quality over the global index
    voices = {dedupe.voice_key(r) for r in idx} if idx else set()
    echo = round(1 - len(voices) / len(idx), 3) if idx else 0
    # structural independence: distinct shared-origin clusters (catches many domains echoing one
    # origin, which identity-based voice_key scores as independent) — see synthesize.independence
    try:
        _uf, _by = pg.build_clusters([dict(r) for r in idx]) if idx else (None, {})
        origins = len({_uf.find(s) for s in _by}) if idx else 0
    except Exception:  # noqa: BLE001
        origins = len(voices)
    origin_indep = round(origins / len(idx), 3) if idx else 0
    origin_echo = round(1 - origins / len(idx), 3) if idx else 0
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
        with open(os.path.join(d, "status.json"), encoding="utf-8") as fh:
            st = json.load(fh)
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
    # lexical layer emits relevant/borderline/off_topic/broken; the LLM verifier upgrades each
    # 'relevant' AND 'borderline' to a final supported/contradicted/unsupported (SKILL.md step 6).
    vc = Counter(r.get("verdict") for r in ver)
    supported, contradicted, unsupported = vc["supported"], vc["contradicted"], vc["unsupported"]
    awaiting = vc["relevant"] + vc["borderline"]   # on-topic, still awaiting the LLM Fact-Check
    off_topic, broken = vc["off_topic"], vc["broken"]
    # off_topic is a READABLE source the lexical layer judged unrelated -> a FAILED citation, NOT a
    # non-event. It MUST stay in the precision denominator or a wrongly-dropped true claim vanishes
    # and biases precision up (the audited bug). broken = unreadable link (access failure), reported
    # separately since support can't be judged without reading. A broken citation BLOCKS completion
    # until it is replaced or the claim is removed. (coverage != answer recall.)
    judged = supported + contradicted + unsupported + off_topic   # the stated denominator
    precision = round(supported / judged, 3) if judged else None  # of judged citations, fraction that hold
    blocking = awaiting + broken
    coverage = round(judged / (judged + blocking), 3) if (judged + blocking) else None
    complete = bool(judged and blocking == 0)      # every claim is readable and has a final verdict
    # headline accuracy is only real once the pass is COMPLETE; None while claims still await checking
    cit_acc = precision if complete else None
    bad = off_topic + broken
    on_topic = round((len(ver) - bad) / len(ver), 3) if ver else None

    brief = os.path.join(run, "brief.md")
    if os.path.exists(brief):
        with open(brief, encoding="utf-8") as fh:
            btext = fh.read().lower()
    else:
        btext = ""
    sections = {s: (s in btext) for s in ("agreement", "disagreement", "unverified")}

    out = {
        "topic": cfg.get("topic"), "version": cfg.get("version"),
        "citation_accuracy": cit_acc, "citation_precision": precision,
        "citation_coverage": coverage, "citation_denominator": judged,
        "citation_complete": complete, "on_topic_rate": on_topic,
        "verified_claims": len(ver), "off_topic_or_broken_citations": bad,
        "verdicts": {"supported": supported, "contradicted": contradicted,
                     "unsupported": unsupported, "off_topic": off_topic, "broken": broken,
                     "awaiting_llm_check": awaiting},
        # Kept only as an explicitly legacy diagnostic.  The old authority-domain proxy reversed
        # both promoted forward-test source-choice judgments and must never be a release metric.
        "source_quality": None, "legacy_source_quality_proxy": quality, "sources": len(idx),
        "independence": round(1 - echo, 3), "echo_ratio": echo, "unique_voices": len(voices),
        "origin_independence": origin_indep, "origin_echo_ratio": origin_echo,
        "independent_origins": origins,
        "framing_coverage": {"root_framings": len(root_framings), "leaves": leaves,
                             "leaves_with_findings": with_find},
        "disconfirmation": {"adversary_branch": adversary, "produced_findings": adversary_find},
        "depth": depth_metrics,
        "tree": {"nodes": nodes, "max_depth": maxdepth, "leaves": leaves, "reads": reads},
        "brief_sections": sections,
        "evidence_sources": ev, "high_authority_sources": hi,
    }
    canonical = evaluator_v2.score_run(run, require_scope=require_scope)
    for key in (
        "citation_accuracy", "citation_precision", "citation_entailment_precision",
        "citation_coverage", "citation_denominator", "citation_complete",
        "row_verification_complete", "claim_scope_audit", "scope_gate_passed",
        "verdicts", "factual_accuracy", "answer_recall", "probabilistic_calibration",
        "temporal_correctness", "contradiction_recall", "unmeasured_dimensions",
        "metric_semantics", "evaluator", "eval_schema_version", "brief_word_count",
        "extracted_claim_rows",
    ):
        if key in canonical:
            out[key] = canonical[key]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score a Deep Aletheia run.")
    ap.add_argument("run")
    args = ap.parse_args(argv)
    print(json.dumps(score(args.run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
