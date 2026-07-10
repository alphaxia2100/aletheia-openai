#!/usr/bin/env python3
"""Deep Aletheia — synthesis helper (bottom-up merge + independence).

Synthesis PROSE is authored by the single-threaded orchestrator (Cognition: one context sees
all). This helper does the deterministic prep so that authoring is grounded:
  - gathers direct children's questions + findings.md (what bubbles up),
  - computes INDEPENDENCE over the node's whole subtree of sources — the "40 blogs, 1 origin"
    check done over the tree instead of by eye. Two signals: identity echo (voice_key) AND the
    stronger structural origin_echo (provenance_graph.build_clusters: collapses canonical-url dups,
    derives_from echoes, and near-duplicate syndication into shared-origin clusters, which voice_key
    misses), plus unique domains/index-groups, class mix, and concentration,
  - flags children that returned thin/no findings (candidates for a top-down clarification).
Writes <node>/synthesis_input.md for the orchestrator to turn into <node>/findings.md.

Usage:  synthesize.py --node NODE_DIR
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
sys.path.insert(0, PROV)
import dedupe  # noqa: E402
import provenance_graph as pg  # noqa: E402  (structural shared-origin clustering)


def _read_json(p, d=None):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return d


def _load_jsonl(p) -> List[Dict[str, Any]]:
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _answered(child: str) -> bool:
    """A child is 'resolved' once it has recorded at least one answer to a parent's question."""
    ap = os.path.join(child, "answers.jsonl")
    if not os.path.exists(ap):
        return False
    with open(ap, encoding="utf-8") as fh:
        return any(l.strip() for l in fh)


def children(node: str) -> List[str]:
    cdir = os.path.join(node, "children")
    if not os.path.isdir(cdir):
        return []
    return [os.path.join(cdir, c) for c in sorted(os.listdir(cdir))
            if os.path.isdir(os.path.join(cdir, c))]


def subtree_sources(node: str) -> List[Dict[str, Any]]:
    recs = _load_jsonl(os.path.join(node, "sources.jsonl"))
    for c in children(node):
        recs += subtree_sources(c)
    return recs


def _origin_clusters(records: List[Dict[str, Any]]) -> int:
    """Distinct SHARED-ORIGIN clusters via provenance_graph.build_clusters. Where voice_key merges
    only source *identity* (same author/domain/DOI), build_clusters also collapses canonical-url
    duplicates, explicit `derives_from` echoes, AND un-annotated near-duplicate text (a wire story /
    press release reprinted across N domains). This is the fix for the audited failure: 40 distinct
    domains echoing one origin score echo≈0 under voice_key but collapse to ~1 origin here."""
    if not records:
        return 0
    try:
        uf, by_id = pg.build_clusters([dict(r) for r in records])  # copy: build_clusters mutates
        return len({uf.find(sid) for sid in by_id})
    except Exception:  # noqa: BLE001 — never let independence math crash synthesis
        return len({dedupe.voice_key(r) for r in records})


def _unique_source_instances(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Count a source once when the same retrieved record appears in multiple tree branches."""
    out, seen = [], set()
    for record in records:
        canon = dedupe.canonical_url(str(record.get("url") or ""))
        sid = str(record.get("id") or "")
        key = ("url", canon) if canon else (("id", sid) if sid else None)
        if key is not None and key in seen:
            continue
        if key is not None:
            seen.add(key)
        out.append(record)
    return out


def independence(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    records = _unique_source_instances(records)
    if not records:
        return {"n": 0, "voices": 0, "echo_ratio": 0, "independent_origins": 0,
                "origin_echo_ratio": 0, "domains": 0, "index_groups": 0,
                "top_domain_share": 0, "class_breakdown": {}}
    n = len(records)
    voices = {dedupe.voice_key(r) for r in records}
    origins = _origin_clusters(records)          # structural: the REAL independence signal
    domains = Counter(dedupe.registrable_domain(r.get("url", "")) for r in records if r.get("url"))
    groups = Counter(r.get("_index_group") or r.get("index_of_origin") for r in records)
    classes = Counter(r.get("_class") or r.get("channel_class") or "?" for r in records)
    return {
        "n": n, "voices": len(voices),
        "echo_ratio": round(1 - len(voices) / n, 3),          # identity echo (voice_key) — kept for continuity
        "independent_origins": origins,                        # shared-origin clusters (structural)
        "origin_echo_ratio": round(1 - origins / n, 3),        # the headline: many sources, few origins?
        "domains": len(domains),
        "top_domain_share": round(domains.most_common(1)[0][1] / sum(domains.values()), 3) if domains else 0,
        "index_groups": len(groups), "class_breakdown": dict(classes),
    }


def synthesis_input(node: str) -> Dict[str, Any]:
    st = _read_json(os.path.join(node, "status.json"), {}) or {}
    kids = children(node)
    child_blocks, thin, unresolved = [], [], []
    for c in kids:
        cst = _read_json(os.path.join(c, "status.json"), {}) or {}
        qid = cst.get("qid", os.path.basename(c))
        fpath = os.path.join(c, "findings.md")
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as fh:
                ftext = fh.read().strip()
        else:
            ftext = ""
        child_blocks.append((qid, cst.get("question", ""), ftext))
        if len(ftext) < 120:
            thin.append(qid)
            if not _answered(c):                 # thin AND never asked/answered -> gate blocks
                unresolved.append(qid)
    all_sources = subtree_sources(node)
    read_sources = [r for r in all_sources if r.get("_read_ok")]
    # Search hits are leads, not corroborating evidence. Base synthesis independence on what was
    # actually read; retain retrieved_n for observability. Legacy/imported packs without read flags
    # fall back to all records rather than reporting an empty evidence set.
    basis = read_sources if read_sources else all_sources
    indep = independence(basis)
    indep["retrieved_n"] = len(all_sources)
    indep["retrieved_unique_n"] = len(_unique_source_instances(all_sources))
    indep["basis"] = "read_sources" if read_sources else "all_sources_no_read_flags"

    lines = ["# Synthesis input — %s" % st.get("qid", "node"), "",
             "**Question:** %s" % st.get("question", ""), "",
             "## Independence (subtree)", "```", json.dumps(indep, indent=2), "```"]
    if indep["origin_echo_ratio"] >= 0.4 or indep["echo_ratio"] >= 0.4 or indep["top_domain_share"] >= 0.4:
        lines.append("> ⚠ high echo / concentration — %d sources but only %d independent ORIGINS "
                     "(origin_echo=%.2f). Treat convergence with suspicion; trace to independent "
                     "origins before calling it Agreement." % (
                         indep["n"], indep["independent_origins"], indep["origin_echo_ratio"]))
    if unresolved:
        lines += ["", "## BLOCKED — ask before authoring (back-and-forth, not assumption)",
                  "These children are thin AND unanswered. Do NOT write findings.md yet — ask each "
                  "(`treestate ask --node <child> --from %s --q \"...\"`) and let it answer from its "
                  "already-gathered sources (`treestate answer`):" % st.get("qid", "parent"),
                  ", ".join(unresolved), ""]
    lines += ["", "## Children findings (bubble up)", ""]
    for qid, q, ftext in child_blocks:
        lines += ["### %s — %s" % (qid, q), ftext or "_(no findings yet)_", ""]
    if thin:
        lines += ["## Thin children (consider a top-down clarification via treestate ask)",
                  ", ".join(thin), ""]
    with open(os.path.join(node, "synthesis_input.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"node": node, "children": len(kids), "thin": thin, "unresolved": unresolved,
            "independence": indep}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia synthesis helper.")
    ap.add_argument("--node", required=True)
    ap.add_argument("--gate", action="store_true",
                    help="exit 3 if any child is thin AND unanswered (enforce ask-before-authoring)")
    args = ap.parse_args(argv)
    res = synthesis_input(args.node)
    print(json.dumps(res, indent=2))
    if args.gate and res.get("unresolved"):
        sys.stderr.write("BLOCKED: thin+unanswered children: %s — ask them before authoring findings.\n"
                         % ", ".join(res["unresolved"]))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
