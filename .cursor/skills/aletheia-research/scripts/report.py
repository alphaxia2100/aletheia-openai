#!/usr/bin/env python3
"""Aletheia Research — output assembler (the VERBOSITY dial).

Two audiences need very different outputs (0.4.0):
  - `bundle` (verbosity=agent): the FULL research pack — every node's findings.md and evidence.md
    verbatim, the source index, and with --reads the actual primaries read in full (notes/*.md). A
    calling AGENT wants everything, not a summary; nuance lives in the raw files. This is what the
    skill hands back when another session invoked it.
  - the user-facing MULTI-PAGE summary is authored by the orchestrator (brief.md); `outline` here just
    prints the tree + where every artifact is, so that synthesis is grounded and complete.

Usage:
  report.py bundle  --run RUN_DIR [--reads] [--max-chars N] [--output FILE]
  report.py outline --run RUN_DIR
  report.py score   --run RUN_DIR [--output FILE]
  report.py audit-claims --run RUN_DIR --auditor "fresh-context verifier" [--added-claims N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
# sibling skills resolve via realpath (works through ~/.cursor, ~/.claude, or ~/.codex symlinks),
# so `score` is self-contained WITH the skill — no dependency on the repo's scripts/eval or deep-aletheia.
_PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
for _p in (HERE, _PROV):
    sys.path.insert(0, _p)
import treestate  # noqa: E402
try:
    import provenance_graph as _pg  # noqa: E402  (structural independence)
    import dedupe as _dedupe  # noqa: E402
except Exception:  # noqa: BLE001 — score still runs (independence degrades to identity voices)
    _pg = _dedupe = None
from collections import Counter  # noqa: E402


def _read(p: str, default: str = "") -> str:
    # errors="replace": the bundle must robustly hand back EVERY artifact — a single stray non-UTF-8
    # byte (corrupt/hand-edited/cross-system file) must not abort the whole pack into an empty result.
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return default


def _nodes_depth_first(run: str) -> List[str]:
    out = []
    for d, _s, fs in os.walk(os.path.join(run, "tree")):
        if "status.json" in fs:
            out.append(d)
    out.sort(key=lambda p: (int((treestate._read_json(os.path.join(p, "status.json"), {}) or {}).get("depth", 0)), p))
    return out


def _cfg(run: str) -> Dict[str, Any]:
    return treestate._read_json(os.path.join(run, "run.json"), {}) or {}


def _jsonl_dicts(path: str) -> List[Dict[str, Any]]:
    rows = []
    for line in _read(path).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _file_sha256(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def _claim_scope_state(run: str) -> Dict[str, Any]:
    """Validate the claim-coverage attestation against the exact final artifacts."""
    audit = treestate._read_json(os.path.join(run, "claim_audit.json"), {}) or {}
    reasons = []
    if audit.get("status") != "complete":
        reasons.append("missing_complete_attestation")
    if not str(audit.get("auditor") or "").strip():
        reasons.append("missing_auditor")
    brief_hash = _file_sha256(os.path.join(run, "brief.md"))
    claims_hash = _file_sha256(os.path.join(run, "claims.jsonl"))
    if not brief_hash:
        reasons.append("missing_brief")
    elif audit.get("brief_sha256") != brief_hash:
        reasons.append("brief_changed_after_audit")
    if not claims_hash:
        reasons.append("missing_claims")
    elif audit.get("claims_sha256") != claims_hash:
        reasons.append("claims_changed_after_audit")
    claims = _jsonl_dicts(os.path.join(run, "claims.jsonl"))
    if int(audit.get("claim_count", -1) or -1) != len(claims):
        reasons.append("claim_count_mismatch")
    return {
        "required": True,
        "valid": not reasons,
        "auditor": audit.get("auditor"),
        "claim_count": len(claims),
        "added_claims": int(audit.get("added_claims", 0) or 0),
        "reasons": reasons,
    }


def audit_claim_scope(run: str, auditor: str, added_claims: int = 0,
                      notes: str = "") -> Dict[str, Any]:
    """Attest that a verifier compared the final brief with the complete claim set.

    Code enforces artifact identity and completed row verification. The auditor supplies the semantic
    judgment that every load-bearing factual assertion was extracted; hashes make any later edit
    invalidate the attestation.
    """
    auditor = str(auditor or "").strip()
    if not auditor:
        raise ValueError("auditor must identify the fresh-context verification pass")
    if added_claims < 0:
        raise ValueError("added_claims must be non-negative")
    brief_path = os.path.join(run, "brief.md")
    claims_path = os.path.join(run, "claims.jsonl")
    claims = _jsonl_dicts(claims_path)
    verdicts = _jsonl_dicts(os.path.join(run, "verify.jsonl"))
    if not _file_sha256(brief_path):
        raise ValueError("write the final brief before attesting claim coverage")
    if not claims:
        raise ValueError("claims.jsonl is empty")
    final = {"supported", "contradicted", "unsupported", "off_topic"}
    if len(verdicts) != len(claims) or any(v.get("verdict") not in final for v in verdicts):
        raise ValueError("every extracted claim must have a final readable verdict before attestation")
    claim_keys = sorted((str(c.get("claim") or ""), str(c.get("url") or "")) for c in claims)
    verdict_keys = sorted((str(v.get("claim") or ""), str(v.get("url") or "")) for v in verdicts)
    if claim_keys != verdict_keys:
        raise ValueError("claims.jsonl and verify.jsonl do not describe the same claim/url set")
    payload = {
        "status": "complete",
        "auditor": auditor,
        "attestation": ("Auditor read the final brief, added every omitted load-bearing factual claim, "
                        "and checked the final claim/url set against verify.jsonl."),
        "claim_count": len(claims),
        "added_claims": added_claims,
        "brief_sha256": _file_sha256(brief_path),
        "claims_sha256": _file_sha256(claims_path),
        "notes": notes,
        "created": treestate._now(),
    }
    treestate._write_json(os.path.join(run, "claim_audit.json"), payload)
    return payload


def _runtime_telemetry(run: str) -> Dict[str, Any]:
    """Aggregate selection-path activation and cost counters emitted by investigate.py."""
    events = []
    for node in _nodes_depth_first(run):
        events.extend(_jsonl_dicts(os.path.join(node, "telemetry.jsonl")))
    rounds = [e for e in events if e.get("event") == "investigation_round"]
    modes = Counter(str(e.get("selection_mode") or "unknown") for e in rounds)

    def total(field: str) -> int:
        return sum(int(e.get(field, 0) or 0) for e in rounds)

    return {
        "rounds": len(rounds),
        "rounds_by_selection_mode": dict(sorted(modes.items())),
        "retrieved": total("retrieved"),
        "unique": total("unique"),
        "eligible": total("eligible"),
        "selected": total("selected"),
        "read_attempts": total("read_attempts"),
        "reads_ok": total("reads_ok"),
        "read_failures": total("read_failures"),
        "zero_selection_rounds": sum(1 for e in rounds if int(e.get("selected", 0) or 0) == 0),
        "zero_success_rounds": sum(1 for e in rounds if int(e.get("reads_ok", 0) or 0) == 0),
        "floor_engagements": sum(1 for e in rounds if e.get("floor_engaged") is True),
        "triage_requeries": sum(1 for e in events if e.get("event") == "triage_requery"),
        "read_seconds": round(sum(float(e.get("read_seconds", 0) or 0) for e in rounds), 1),
    }


def _note_files(notes_dir: str):
    """Yield nested read artifacts deterministically (workers may store full/decisive rereads)."""
    if not os.path.isdir(notes_dir):
        return []
    out = []
    for directory, _subdirs, files in os.walk(notes_dir):
        for filename in files:
            if filename.endswith(".md"):
                path = os.path.join(directory, filename)
                out.append((os.path.relpath(path, notes_dir), path))
    return sorted(out)


def bundle(run: str, reads: bool = False, max_chars: int = 0) -> str:
    """The FULL pack for an agent caller — every artifact, verbatim. `reads` also inlines the primaries
    read in full (notes/*.md). `max_chars` optionally truncates each read (0 = no truncation)."""
    cfg = _cfg(run)
    L: List[str] = []
    L.append("# Aletheia Research — FULL BUNDLE (agent verbosity)")
    L.append("")
    L.append("**Topic:** %s" % cfg.get("topic", ""))
    L.append("**Thoroughness:** %s · **Verbosity:** %s · **Version:** %s"
             % (cfg.get("thoroughness"), cfg.get("verbosity"), cfg.get("version")))
    L.append("")
    L.append("This is the COMPLETE research artifact set — not a summary. Every node's findings and "
             "evidence are included verbatim so no nuance is lost. Read it in full; cite the primaries.")
    L.append("")
    L.append("## Portfolio (competing framings)")
    L.append(_read(os.path.join(run, "portfolio.md"), "_(none)_"))
    L.append("")
    L.append(treestate.tree_view(run))
    L.append("")
    for artifact in ("claims.jsonl", "verify.jsonl", "claim_audit.json", "score.json"):
        content = _read(os.path.join(run, artifact))
        if content.strip():
            L.append("## %s" % artifact)
            L.append(content)
            L.append("")
    for node in _nodes_depth_first(run):
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        rel = os.path.relpath(node, run)
        L.append("\n" + "=" * 90)
        L.append("## NODE `%s` — %s" % (st.get("qid", rel), st.get("question", "")))
        L.append("state=%s depth=%s budget=%s rounds=%s n_read=%s"
                 % (st.get("state"), st.get("depth"), st.get("budget"),
                    st.get("rounds"), st.get("n_read")))
        L.append("")
        findings = _read(os.path.join(node, "findings.md"))
        if findings.strip():
            L.append("### findings.md")
            L.append(findings)
        evidence = _read(os.path.join(node, "evidence.md"))
        if evidence.strip():
            L.append("### evidence.md")
            L.append(evidence)
        telemetry = _read(os.path.join(node, "telemetry.jsonl"))
        if telemetry.strip():
            L.append("### telemetry.jsonl")
            L.append(telemetry)
        srcs = [l for l in _read(os.path.join(node, "sources.jsonl")).splitlines() if l.strip()]
        if srcs:
            L.append("### sources.jsonl (%d)" % len(srcs))
            for s in srcs:
                try:
                    r = json.loads(s)
                    if not isinstance(r, dict):        # a valid-JSON non-object line -> skip, don't crash
                        continue
                    L.append("- [%s] %s — %s" % (r.get("_class") or r.get("channel_class") or "?",
                                                 (r.get("title") or "")[:110], r.get("url", "")))
                except ValueError:
                    pass
        if reads:
            notes_dir = os.path.join(node, "notes")
            for rel, path in _note_files(notes_dir):
                body = _read(path)
                if max_chars and len(body) > max_chars:
                    body = body[:max_chars] + "\n…[truncated]"
                L.append("#### read primary — notes/%s" % rel)
                L.append(body)
    brief = _read(os.path.join(run, "brief.md"))
    if brief.strip():
        L.append("\n" + "=" * 90)
        L.append("## brief.md (the synthesized answer)")
        L.append(brief)
    return "\n".join(L) + "\n"


def outline(run: str) -> str:
    """Tree + artifact inventory, so the orchestrator's multi-page summary is grounded and complete."""
    cfg = _cfg(run)
    L = ["# Run outline — %s (%s)" % (cfg.get("topic", ""), cfg.get("thoroughness")), ""]
    L.append(treestate.tree_view(run))
    L.append("")
    L.append("## Artifacts per node")
    for node in _nodes_depth_first(run):
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        rel = os.path.relpath(node, run)
        arts = [a for a in ("findings.md", "evidence.md", "sources.jsonl")
                if os.path.exists(os.path.join(node, a))]
        notes_dir = os.path.join(node, "notes")
        n_notes = len(_note_files(notes_dir))
        L.append("- `%s` [%s] — %s | %d read primaries" % (rel, st.get("qid", ""), ", ".join(arts), n_notes))
    return "\n".join(L) + "\n"


def _independent_origins(records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
    if _pg is not None:
        try:
            uf, by = _pg.build_clusters([dict(r) for r in records])
            return len({uf.find(s) for s in by})
        except Exception:  # noqa: BLE001
            pass
    if _dedupe is not None:
        return len({_dedupe.voice_key(r) for r in records})
    return len(records)


def _claim_source_records(verdicts: List[Dict[str, Any]], index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return unique finally judged citation records, enriched from the retrieval index.

    Independence over every search hit rewards irrelevant breadth. The epistemic question is whether
    the sources actually carrying final claims are independent. Keep contradicted/unsupported
    citations in the audit (they were still used), but exclude unreadable/off-topic and unfinished
    rows. Cross-domain copies retain their separate records so structural clustering can collapse them.
    """
    final = {"supported", "contradicted", "unsupported"}
    by_key: Dict[str, Dict[str, Any]] = {}

    def keys(row: Dict[str, Any]) -> List[str]:
        url = str(row.get("url") or "")
        canon = _dedupe.canonical_url(url) if _dedupe is not None else url.rstrip("/").lower()
        out = ["url:" + canon] if canon else []
        if _pg is not None:
            try:
                out += ["%s:%s" % item for item in _pg._work_identity(row).items()]
            except Exception:  # noqa: BLE001 - URL identity remains available
                pass
        return out

    for row in index:
        if not isinstance(row, dict):
            continue
        for key in keys(row):
            by_key.setdefault(key, row)
    out, seen = [], set()
    for verdict in verdicts:
        if verdict.get("verdict") not in final:
            continue
        url = str(verdict.get("url") or "")
        if not url:
            continue
        probe = {"url": url}
        probe_keys = keys(probe)
        if not probe_keys or any(key in seen for key in probe_keys):
            continue
        matched = next((by_key[key] for key in probe_keys if key in by_key), None)
        source = dict(matched or probe)
        source.setdefault("url", url)
        source_keys = set(probe_keys + keys(source))
        if source_keys & seen:
            continue
        seen.update(source_keys)
        out.append(source)
    return out


def score(run: str) -> Dict[str, Any]:
    """Self-contained scorer (ships WITH the skill — no repo/eval or deep-aletheia dependency). The
    headline `citation_accuracy` is precision, reported ONLY when the verification pass is complete
    (every on-topic claim has a final verdict); off_topic counts in the denominator so a dropped
    citation can't vanish; an independent, content-hashed scope audit prevents the writer from omitting
    inconvenient claims from the denominator; independence uses shared-origin clustering."""
    ver = _jsonl_dicts(os.path.join(run, "verify.jsonl"))
    vc = Counter(r.get("verdict") for r in ver)
    supported, contradicted, unsupported = vc["supported"], vc["contradicted"], vc["unsupported"]
    awaiting = vc["relevant"] + vc["borderline"]
    off_topic, broken = vc["off_topic"], vc["broken"]
    judged = supported + contradicted + unsupported + off_topic
    precision = round(supported / judged, 3) if judged else None
    blocking = awaiting + broken
    coverage = round(judged / (judged + blocking), 3) if (judged + blocking) else None
    row_complete = bool(judged and blocking == 0)
    claim_scope = _claim_scope_state(run)
    complete = row_complete and claim_scope["valid"]
    idx = _jsonl_dicts(os.path.join(run, "index", "sources.jsonl"))
    cited = _claim_source_records(ver, idx)
    origins = _independent_origins(cited)
    retrieved_origins = _independent_origins(idx)
    return {
        "topic": _cfg(run).get("topic"), "version": _cfg(run).get("version"),
        "citation_accuracy": precision if complete else None,
        "citation_precision": precision, "citation_coverage": coverage,
        "citation_denominator": judged, "citation_complete": complete,
        "row_verification_complete": row_complete,
        "claim_scope_audit": claim_scope,
        "verdicts": {"supported": supported, "contradicted": contradicted, "unsupported": unsupported,
                     "off_topic": off_topic, "broken": broken, "awaiting_llm_check": awaiting},
        # Headline independence is claim-level. Retrieval breadth remains observable but cannot
        # masquerade as corroboration.
        "sources": len(cited), "claim_sources": len(cited), "independent_origins": origins,
        "origin_echo_ratio": round(1 - origins / len(cited), 3) if cited else 0,
        "retrieved_sources": len(idx), "retrieved_independent_origins": retrieved_origins,
        "retrieved_origin_echo_ratio": round(1 - retrieved_origins / len(idx), 3) if idx else 0,
        # Behavioral activation evidence: proves which selector ran and separates retrieval,
        # selection, attempted reads, and successful reads for matched-budget evaluations.
        "runtime": _runtime_telemetry(run),
    }


def write_brief(run: str, text: str) -> str:
    """Write the user-facing brief.md into the run dir. Exists as a SCRIPT so a guarded harness that
    blocks writing report `.md` files can still emit the deliverable (the audited cold-caller gap)."""
    path = os.path.join(run, "brief.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    treestate.set_run_state(run, "complete" if score(run).get("citation_complete") else "briefed")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia Research output assembler (verbosity dial).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bundle"); b.add_argument("--run", required=True)
    b.add_argument("--reads", action="store_true", help="inline the primaries read in full (notes/*.md)")
    b.add_argument("--max-chars", type=int, default=0, help="truncate each read to N chars (0 = no cap)")
    b.add_argument("--output", default="", help="write the bundle to FILE instead of stdout")
    o = sub.add_parser("outline"); o.add_argument("--run", required=True)
    s = sub.add_parser("score"); s.add_argument("--run", required=True)
    s.add_argument("--output", default="", help="also persist the score JSON to FILE")
    w = sub.add_parser("write-brief"); w.add_argument("--run", required=True)
    w.add_argument("--file", default="", help="read brief text from this file")
    w.add_argument("--text", default="", help="inline brief text (use --file for anything long)")
    a = sub.add_parser("audit-claims"); a.add_argument("--run", required=True)
    a.add_argument("--auditor", required=True, help="fresh-context verifier identity/role")
    a.add_argument("--added-claims", type=int, default=0)
    a.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    if args.cmd == "bundle":
        text = bundle(args.run, args.reads, args.max_chars)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(os.path.abspath(args.output))
        else:
            print(text)
    elif args.cmd == "outline":
        print(outline(args.run))
    elif args.cmd == "score":
        payload = json.dumps(score(args.run), indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
        print(payload)
    elif args.cmd == "write-brief":
        txt = _read(args.file) if args.file else args.text
        if not txt.strip():
            sys.stderr.write("write-brief: need --file or --text\n"); return 2
        print(write_brief(args.run, txt))
    elif args.cmd == "audit-claims":
        try:
            payload = audit_claim_scope(args.run, args.auditor, args.added_claims, args.notes)
        except ValueError as exc:
            sys.stderr.write("audit-claims: %s\n" % exc); return 2
        treestate.set_run_state(args.run, "complete" if score(args.run).get("citation_complete")
                                else "briefed")
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
