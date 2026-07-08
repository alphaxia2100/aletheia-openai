#!/usr/bin/env python3
"""Defensibility rubric — scores whether a belief is actually defensible.

A belief is defensible only when it (1) states its own falsifier, (2) was
searched against that falsifier with results reported, (3) traces to independent
primary evidence, and (4) steelmans the strongest opposing view and says why it
still holds. This is a lenient scaffold: it catches missing pillars; the final
call is yours.

Usage:
  rubric.py belief.json [--json]
  cat belief.json | rubric.py [--json]
  rubric.py belief.json --from-provenance provenance.json --claim-id c1

belief.json:
  {
    "claim": "...",
    "falsifier": "what would sink it",
    "falsifier_search": {"performed": true, "found": "...", "notes": "..."},
    "evidence": {"independent_sources": 3, "primary": true, "provenance_report": "..."},
    "steelman": {"opposing_view": "...", "why_unconvinced": "..."}
  }

Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

_VAGUE = {"", "it depends", "more research needed", "n/a", "na", "none", "unknown", "tbd"}


def _score_falsifier(belief: Dict[str, Any]) -> Tuple[float, str]:
    text = (belief.get("falsifier") or "").strip()
    if not text or text.lower() in _VAGUE:
        return 0.0, "No falsifier stated. This is a claim, not yet a belief — say what would sink it."
    if len(text) < 15:
        return 0.5, "Falsifier is vague. Make it specific and testable."
    return 1.0, "States a specific falsifier."


def _score_search(belief: Dict[str, Any]) -> Tuple[float, str]:
    fs = belief.get("falsifier_search") or {}
    performed = bool(fs.get("performed"))
    found = (fs.get("found") or "").strip()
    notes = (fs.get("notes") or "").strip()
    if not performed:
        return 0.0, "Did not go looking for the falsifier. Search the un-laundered channels for it."
    if not found and not notes:
        return 0.5, "Searched but reported nothing. Report what you found — even 'nothing after real search'."
    return 1.0, "Searched for the falsifier and reported the result."


def _score_evidence(belief: Dict[str, Any]) -> Tuple[float, str]:
    ev = belief.get("evidence") or {}
    indep = ev.get("independent_sources")
    primary = ev.get("primary")
    if indep is None:
        return 0.0, "Independence unknown. Run provenance-audit and record independent_sources."
    try:
        indep = int(indep)
    except (TypeError, ValueError):
        return 0.0, "independent_sources is not a number. Run provenance-audit."
    if indep <= 0:
        return 0.0, "No independent evidence."
    if indep == 1:
        return 0.5, "Single independent origin — a lead, not a finding. Corroborate independently."
    if not primary:
        return 0.5, "Independent but not traced to primary sources. Verify the primaries."
    return 1.0, "Traces to multiple independent primary sources."


def _score_steelman(belief: Dict[str, Any]) -> Tuple[float, str]:
    st = belief.get("steelman") or {}
    opp = (st.get("opposing_view") or "").strip()
    why = (st.get("why_unconvinced") or "").strip()
    if opp and why:
        return 1.0, "Steelmans the opposing view and says why the belief still holds."
    if opp or why:
        return 0.5, "Half a steelman. State BOTH the strongest opposing view and why you're unconvinced."
    return 0.0, "No steelman. State the strongest opposing view and why you still hold the belief."


def apply_provenance(belief: Dict[str, Any], provenance_path: str, claim_id: Optional[str]) -> None:
    with open(provenance_path, "r", encoding="utf-8") as fh:
        report = json.load(fh)
    claims = report.get("claims", []) if isinstance(report, dict) else []
    chosen = None
    for c in claims:
        if claim_id is None or c.get("id") == claim_id:
            chosen = c
            break
    if chosen is None:
        return
    ev = belief.setdefault("evidence", {})
    ev["independent_sources"] = chosen.get("independent_sources")
    ev["primary"] = (chosen.get("primary_origins", 0) or 0) >= 1
    ev["provenance_report"] = "auto: %s independent / %s mentions; flags=%s" % (
        chosen.get("independent_sources"), chosen.get("raw_mentions"), chosen.get("flags"))


CRITERIA = [
    ("falsifiability", "States its own falsifier", _score_falsifier),
    ("falsifier_search", "Went looking for the falsifier", _score_search),
    ("independent_evidence", "Traces to independent primary evidence", _score_evidence),
    ("steelman", "Steelmans the opposing view", _score_steelman),
]


def judge(belief: Dict[str, Any]) -> Dict[str, Any]:
    scored = []
    total = 0.0
    for key, label, fn in CRITERIA:
        score, note = fn(belief)
        total += score
        scored.append({"criterion": key, "label": label, "score": score, "note": note})

    min_score = min(s["score"] for s in scored)
    if all(s["score"] >= 1.0 for s in scored):
        verdict = "defensible"
    elif min_score >= 0.5 and total >= 3.0:
        verdict = "defensible (minor gaps)"
    else:
        verdict = "not yet defensible"

    gaps = [s for s in scored if s["score"] < 1.0]
    return {
        "claim": belief.get("claim", ""),
        "total": round(total, 2),
        "max": float(len(CRITERIA)),
        "verdict": verdict,
        "criteria": scored,
        "gaps": [{"criterion": g["criterion"], "fix": g["note"]} for g in gaps],
    }


def to_markdown(result: Dict[str, Any]) -> str:
    out = ["# Defensibility: %s" % (result["claim"] or "(unnamed belief)"), ""]
    out.append("Verdict: **%s**  (%.1f / %.0f)" % (result["verdict"], result["total"], result["max"]))
    out.append("")
    for c in result["criteria"]:
        mark = "PASS" if c["score"] >= 1.0 else ("PARTIAL" if c["score"] >= 0.5 else "FAIL")
        out.append("- [%s] %s (%.1f) — %s" % (mark, c["label"], c["score"], c["note"]))
    if result["gaps"]:
        out.append("")
        out.append("## To make it defensible")
        for g in result["gaps"]:
            out.append("- %s: %s" % (g["criterion"], g["fix"]))
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Score a belief against the 4-part defensibility rubric.")
    ap.add_argument("belief", nargs="?", help="belief JSON file (or stdin)")
    ap.add_argument("--from-provenance", help="provenance_graph audit --json output to auto-fill evidence")
    ap.add_argument("--claim-id", help="claim id to pull from the provenance report")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.belief:
        with open(args.belief, "r", encoding="utf-8") as fh:
            belief = json.load(fh)
    else:
        belief = json.load(sys.stdin)

    if args.from_provenance:
        apply_provenance(belief, args.from_provenance, args.claim_id)

    result = judge(belief)
    if args.json:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(to_markdown(result) + "\n")
    # exit non-zero if not defensible, so it can gate a pipeline
    return 0 if result["verdict"].startswith("defensible") else 3


if __name__ == "__main__":
    raise SystemExit(main())
