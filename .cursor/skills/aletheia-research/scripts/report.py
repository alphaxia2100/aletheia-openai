#!/usr/bin/env python3
"""Aletheia Research — output assembler and agent handoff builder.

The default agent contract is a lossless-by-reference field dossier: a shallow map embeds the final
answer and every branch synthesis, then links to claims, evidence, decisions, and full reads. Raw
artifacts stay available without being injected into the caller's context. `bundle` remains the
fully-inline transport fallback for callers that cannot share a filesystem.

Usage:
  report.py handoff --run RUN_DIR [--output FILE] [--manifest FILE]
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
import re
import sys
import tempfile
from collections import Counter
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

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
            digest = hashlib.sha256()
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    except OSError:
        return ""


def _strict_jsonl_dicts(path: str, label: str) -> List[Dict[str, Any]]:
    """Read gate-critical JSONL without the bundle reader's corruption-tolerant skipping."""
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = list(fh)
    except OSError as exc:
        raise ValueError("%s is missing or unreadable" % label) from exc
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError("%s line %d is invalid JSON" % (label, lineno)) from exc
        if not isinstance(row, dict):
            raise ValueError("%s line %d must be a JSON object" % (label, lineno))
        rows.append(row)
    return rows


def _claim_urls(row: Dict[str, Any]) -> List[str]:
    raw = row.get("urls")
    if not isinstance(raw, list):
        raw = [row.get("url")]
    return [str(url).strip() for url in raw if str(url or "").strip()]


def _claim_verdict_sets_match(claims: List[Dict[str, Any]],
                              verdicts: List[Dict[str, Any]]) -> bool:
    """Match each claim to one verdict; a multi-source claim may resolve to any declared URL."""
    remaining = list(verdicts)
    for claim in claims:
        text = str(claim.get("claim") or "").strip()
        allowed = set(_claim_urls(claim))
        if not text or not allowed:
            return False
        found = next((i for i, verdict in enumerate(remaining)
                      if str(verdict.get("claim") or "").strip() == text
                      and str(verdict.get("url") or "").strip() in allowed), None)
        if found is None:
            return False
        remaining.pop(found)
    return not remaining


def _claim_scope_required(run: str) -> bool:
    """New 0.5 runs require the gate; preserve read-only scoring compatibility for older runs."""
    version = str(_cfg(run).get("version") or "")
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)(?:\.|\b)", version)
    return True if match is None else (int(match.group(1)), int(match.group(2))) >= (0, 5)


def _claim_scope_state(run: str) -> Dict[str, Any]:
    """Validate the claim-coverage attestation against the exact final artifacts."""
    audit = treestate._read_json(os.path.join(run, "claim_audit.json"), {}) or {}
    required = _claim_scope_required(run)
    if not required and not audit:
        return {"required": False, "valid": True, "auditor": None, "claim_count": None,
                "added_claims": 0, "reasons": []}
    reasons = []
    if audit.get("status") != "complete":
        reasons.append("missing_complete_attestation")
    if not str(audit.get("auditor") or "").strip():
        reasons.append("missing_auditor")
    brief_hash = _file_sha256(os.path.join(run, "brief.md"))
    claims_hash = _file_sha256(os.path.join(run, "claims.jsonl"))
    verify_hash = _file_sha256(os.path.join(run, "verify.jsonl"))
    if not brief_hash:
        reasons.append("missing_brief")
    elif audit.get("brief_sha256") != brief_hash:
        reasons.append("brief_changed_after_audit")
    if not claims_hash:
        reasons.append("missing_claims")
    elif audit.get("claims_sha256") != claims_hash:
        reasons.append("claims_changed_after_audit")
    if not verify_hash:
        reasons.append("missing_verify")
    elif audit.get("verify_sha256") != verify_hash:
        reasons.append("verify_changed_after_audit")
    try:
        claims = _strict_jsonl_dicts(os.path.join(run, "claims.jsonl"), "claims.jsonl")
        _strict_jsonl_dicts(os.path.join(run, "verify.jsonl"), "verify.jsonl")
    except ValueError:
        claims = []
        reasons.append("invalid_claim_or_verify_jsonl")
    if int(audit.get("claim_count", -1) or -1) != len(claims):
        reasons.append("claim_count_mismatch")
    return {
        "required": required,
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
    claims = _strict_jsonl_dicts(claims_path, "claims.jsonl")
    verdicts = _strict_jsonl_dicts(os.path.join(run, "verify.jsonl"), "verify.jsonl")
    if not _file_sha256(brief_path):
        raise ValueError("write the final brief before attesting claim coverage")
    if not claims:
        raise ValueError("claims.jsonl is empty")
    final = {"supported", "contradicted", "unsupported", "off_topic"}
    if len(verdicts) != len(claims) or any(v.get("verdict") not in final for v in verdicts):
        raise ValueError("every extracted claim must have a final readable verdict before attestation")
    if not _claim_verdict_sets_match(claims, verdicts):
        raise ValueError("claims.jsonl and verify.jsonl do not describe the same claim/source set")
    payload = {
        "status": "complete",
        "auditor": auditor,
        "attestation": ("Auditor read the final brief, added every omitted load-bearing factual claim, "
                        "and checked the final claim/url set against verify.jsonl."),
        "claim_count": len(claims),
        "added_claims": added_claims,
        "brief_sha256": _file_sha256(brief_path),
        "claims_sha256": _file_sha256(claims_path),
        "verify_sha256": _file_sha256(os.path.join(run, "verify.jsonl")),
        "notes": notes,
        "created": treestate._now(),
    }
    treestate._write_json(os.path.join(run, "claim_audit.json"), payload)
    return payload


def _runtime_telemetry(run: str) -> Dict[str, Any]:
    """Aggregate selection-path activation and cost counters emitted by investigate.py."""
    events = []
    read_artifacts = set()
    engine_artifacts = set()
    for node in _nodes_depth_first(run):
        notes = os.path.join(node, "notes")
        for _rel, path in _note_files(notes):
            read_artifacts.add(os.path.realpath(path))
        for source in _jsonl_dicts(os.path.join(node, "sources.jsonl")):
            rel = str(source.get("_read_file") or "").strip()
            if rel:
                path = os.path.realpath(os.path.join(node, rel))
                if os.path.isfile(path):
                    engine_artifacts.add(path)
        for event in _jsonl_dicts(os.path.join(node, "telemetry.jsonl")):
            tagged = dict(event)
            tagged["_node"] = node       # disambiguate equal round numbers across different leaves
            events.append(tagged)
    rounds = [e for e in events if e.get("event") == "investigation_round"]
    gathers = [e for e in events if e.get("event") == "candidate_gather"]
    # Agent rounds repeat the final gather's retrieval counts, so use gather events for agent search
    # cost and completed-round events only for deterministic search. Match per node+round so a run
    # resumed across an upgrade still counts its older agent rounds that lack candidate_gather events.
    deterministic_search = [e for e in rounds if e.get("selection_mode") != "agent"]
    gather_rounds = {(e.get("_node"), e.get("round")) for e in gathers}
    legacy_agent_search = [e for e in rounds if e.get("selection_mode") == "agent"
                           and (e.get("_node"), e.get("round")) not in gather_rounds]
    searches = gathers + deterministic_search + legacy_agent_search
    modes = Counter(str(e.get("selection_mode") or "unknown") for e in rounds)

    def total(field: str, rows=rounds) -> int:
        return sum(int(e.get(field, 0) or 0) for e in rows)

    return {
        "rounds": len(rounds),
        "rounds_by_selection_mode": dict(sorted(modes.items())),
        "retrieval_passes": len(searches),
        "candidate_gathers": len(gathers),
        "retrieved": total("retrieved", searches),
        "unique": total("unique", searches),
        "eligible": total("eligible", searches),
        "completed_round_retrieved": total("retrieved"),
        "selected": total("selected"),
        "read_attempts": total("read_attempts"),
        "reads_ok": total("reads_ok"),
        "read_failures": total("read_failures"),
        "zero_selection_rounds": sum(1 for e in rounds if int(e.get("selected", 0) or 0) == 0),
        "zero_success_rounds": sum(1 for e in rounds if int(e.get("reads_ok", 0) or 0) == 0),
        "floor_engagements": sum(1 for e in rounds if e.get("floor_engaged") is True),
        "abstained_rounds": sum(1 for e in rounds if e.get("abstained") is True),
        "triage_requeries": sum(1 for e in events if e.get("event") == "triage_requery"),
        "read_seconds": round(sum(float(e.get("read_seconds", 0) or 0) for e in rounds), 1),
        # Workers may chase a linked primary or make an uncapped reread outside investigate.py. Those
        # files are valid evidence, but they are additional cost and must not disappear from an A/B.
        "read_artifacts": len(read_artifacts),
        "engine_read_artifacts": len(read_artifacts & engine_artifacts),
        "direct_or_manual_read_artifacts": len(read_artifacts - engine_artifacts),
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


def _atomic_write(path: str, text: str) -> None:
    """Persist a handoff artifact without exposing a half-written file to another agent."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".aletheia-report-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _portable_rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _md_link(label: str, path: str, output_dir: str) -> str:
    rel = _portable_rel(path, output_dir)
    return "[%s](%s)" % (label, quote(rel, safe="/._-~"))


def _md_cell(value: Any, limit: int = 260) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def _preview(markdown: str, limit: int = 420) -> str:
    """Return the first substantive prose paragraph, not a heading or metadata stub."""
    for block in re.split(r"\n\s*\n", markdown or ""):
        lines = []
        in_fence = False
        for raw in block.splitlines():
            stripped = raw.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or not stripped or stripped.startswith(("#", "<!--")):
                continue
            lines.append(re.sub(r"^[>*+-]\s*", "", stripped))
        text = " ".join(lines).strip()
        if len(text) >= 40:
            return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return ""


def _artifact_role(rel: str) -> str:
    base = os.path.basename(rel)
    if "/notes/" in "/" + rel or rel.startswith("notes/"):
        return "primary_read"
    roles = {
        "brief.md": "final_synthesis",
        "portfolio.md": "framing_portfolio",
        "run.json": "run_identity",
        "findings.md": "branch_synthesis",
        "evidence.md": "evidence_pack",
        "sources.jsonl": "source_index",
        "claims.jsonl": "claim_set",
        "verify.jsonl": "claim_verdicts",
        "claim_audit.json": "claim_scope_audit",
        "score.json": "run_score",
        "decisions.jsonl": "decision_trace",
        "questions.jsonl": "clarification_questions",
        "answers.jsonl": "clarification_answers",
        "telemetry.jsonl": "runtime_telemetry",
        "status.json": "node_status",
        "spec.md": "node_specification",
        "proposal.json": "decomposition_proposal",
        "bundle.md": "inline_bundle",
        "channel-health.json": "channel_health",
    }
    return roles.get(base, "artifact")


def _artifact_files(run: str, exclude: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    root = os.path.abspath(run)
    excluded = {os.path.abspath(p) for p in (exclude or set())}
    artifacts: List[Dict[str, Any]] = []
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if d != "__pycache__")
        for filename in sorted(files):
            path = os.path.abspath(os.path.join(directory, filename))
            if path in excluded or os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            rel = _portable_rel(path, root)
            artifacts.append({
                "path": rel,
                "role": _artifact_role(rel),
                "bytes": size,
                "sha256": _file_sha256(path),
            })
    return artifacts


def _node_manifest(run: str, node: str, artifact_by_path: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    status = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
    node_rel = _portable_rel(node, run)
    prefix = node_rel.rstrip("/") + "/"
    node_artifacts = [row for path, row in artifact_by_path.items() if path.startswith(prefix)]
    direct = [row for row in node_artifacts
              if not row["path"][len(prefix):].startswith("children/")]
    sources = _jsonl_dicts(os.path.join(node, "sources.jsonl"))
    notes = [row for row in direct if row["role"] == "primary_read"]
    decisions = _jsonl_dicts(os.path.join(node, "decisions.jsonl"))
    questions = _jsonl_dicts(os.path.join(node, "questions.jsonl"))
    answers = _jsonl_dicts(os.path.join(node, "answers.jsonl"))
    files: Dict[str, str] = {}
    for row in direct:
        if row["bytes"] or row["role"] in {"node_status", "node_specification"}:
            files.setdefault(row["role"], row["path"])
    return {
        "qid": status.get("qid") or os.path.basename(node),
        "path": node_rel,
        "parent": status.get("parent"),
        "depth": int(status.get("depth", 0) or 0),
        "state": status.get("state"),
        "question": status.get("question", ""),
        "preview": _preview(_read(os.path.join(node, "findings.md"))),
        "budget": status.get("budget"),
        "counts": {
            "sources": len(sources),
            "read_sources": sum(1 for row in sources if row.get("_read_ok") is True),
            "failed_reads": sum(1 for row in sources if row.get("_read_ok") is False),
            "truncated_reads": sum(1 for row in sources if row.get("_truncated") is True),
            "read_artifacts": len(notes),
            "unique_read_bodies": len({row["sha256"] for row in notes if row.get("sha256")}),
            "decisions": len(decisions),
            "questions": len(questions),
            "answers": len(answers),
        },
        "files": files,
    }


def artifact_manifest(run: str, exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Build a machine-readable, content-addressed map of the complete durable run."""
    run = os.path.abspath(run)
    artifacts = _artifact_files(run, exclude)
    by_path = {row["path"]: row for row in artifacts}
    nodes = [_node_manifest(run, node, by_path) for node in _nodes_depth_first(run)]
    by_hash: Dict[str, List[str]] = {}
    for row in artifacts:
        if row["bytes"] and row["sha256"]:
            by_hash.setdefault(row["sha256"], []).append(row["path"])
    aliases = [{"sha256": digest, "paths": paths, "bytes_each": by_path[paths[0]]["bytes"]}
               for digest, paths in sorted(by_hash.items()) if len(paths) > 1]
    role_counts = Counter(row["role"] for row in artifacts)
    reads = [row for row in artifacts if row["role"] == "primary_read"]
    unique_read_bytes = sum(next(row["bytes"] for row in reads if row["sha256"] == digest)
                            for digest in sorted({row["sha256"] for row in reads if row["sha256"]}))
    cfg = _cfg(run)
    entrypoints = {name: name for name in ("brief.md", "portfolio.md", "claims.jsonl",
                                            "verify.jsonl", "claim_audit.json", "score.json")
                   if os.path.isfile(os.path.join(run, name))}
    return {
        "schema": "aletheia.agent-handoff.v1",
        "generated_at": treestate._now(),
        "topic": cfg.get("topic"),
        "version": cfg.get("version"),
        "thoroughness": cfg.get("thoroughness"),
        "implementation": cfg.get("implementation") or {},
        "entrypoints": entrypoints,
        "tree": nodes,
        "artifacts": artifacts,
        "content_aliases": aliases,
        "summary": {
            "nodes": len(nodes),
            "artifacts": len(artifacts),
            "artifact_roles": dict(sorted(role_counts.items())),
            "raw_read_artifacts": len(reads),
            "raw_read_bytes": sum(row["bytes"] for row in reads),
            "unique_raw_read_bytes": unique_read_bytes,
            "duplicate_content_groups": len(aliases),
        },
    }


def _artifact_link(label: str, rel: str, run: str, output_dir: str) -> str:
    return _md_link(label, os.path.join(run, rel), output_dir)


def _node_links(node: Dict[str, Any], run: str, output_dir: str, compact: bool = False) -> str:
    labels = {
        "branch_synthesis": "findings",
        "evidence_pack": "evidence",
        "source_index": "sources",
        "decision_trace": "decisions",
        "clarification_questions": "questions",
        "clarification_answers": "answers",
        "runtime_telemetry": "telemetry",
        "node_status": "status",
        "node_specification": "spec",
    }
    wanted = ("branch_synthesis", "evidence_pack", "decision_trace", "node_status") if compact \
        else tuple(labels)
    links = [_artifact_link(labels[role], node["files"][role], run, output_dir)
             for role in wanted if role in node.get("files", {})]
    return " · ".join(links) if links else "_(no node artifacts)_"


def _key_decisions(node_dir: str, limit: int = 4) -> List[Dict[str, Any]]:
    rows = _jsonl_dicts(os.path.join(node_dir, "decisions.jsonl"))
    if not rows:
        return []
    terms = re.compile(r"\b(stop|saturat|reject|split|merge|override|reopen|defer|downgrade|adversar)", re.I)
    material = [row for row in rows if terms.search(str(row.get("decision", "")) + " " +
                                                    str(row.get("why", "")))
                or str(row.get("actor", "")) not in {"investigate", "agent-triage"}]
    chosen: List[Dict[str, Any]] = []
    for row in material:
        if row not in chosen:
            chosen.append(row)
    if len(chosen) > limit:
        chosen = chosen[:1] + chosen[-(limit - 1):]
    return chosen


def _claim_index(run: str) -> List[Dict[str, Any]]:
    claims = _jsonl_dicts(os.path.join(run, "claims.jsonl"))
    verdicts = _jsonl_dicts(os.path.join(run, "verify.jsonl"))
    unused = list(verdicts)
    out = []
    for i, claim in enumerate(claims, 1):
        text = str(claim.get("claim") or "").strip()
        urls = set(_claim_urls(claim))
        pos = next((j for j, row in enumerate(unused)
                    if str(row.get("claim") or "").strip() == text
                    and str(row.get("url") or "").strip() in urls), None)
        verdict = unused.pop(pos) if pos is not None else {}
        out.append({"id": "C%03d" % i, "claim": text, "urls": sorted(urls),
                    "verdict": verdict.get("verdict", "missing"),
                    "fact_check": verdict.get("fact_check") or verdict.get("notes") or ""})
    return out


def dossier(run: str, manifest: Dict[str, Any], output_path: str,
            manifest_path: str) -> str:
    """Render the shallow, navigable agent entry point. Raw evidence is linked, never inlined."""
    run = os.path.abspath(run)
    output_dir = os.path.dirname(os.path.abspath(output_path))
    cfg = _cfg(run)
    brief = _read(os.path.join(run, "brief.md"))
    portfolio = _read(os.path.join(run, "portfolio.md"))
    root_findings = _read(os.path.join(run, "tree", "root", "findings.md"))
    nodes = manifest.get("tree", [])
    summary = manifest.get("summary", {})
    manifest_sha = _file_sha256(manifest_path)
    impl = cfg.get("implementation") or {}
    lines: List[str] = [
        "# Aletheia field dossier — agent handoff",
        "",
        "**Topic:** %s" % cfg.get("topic", ""),
        "**Thoroughness:** %s · **Version:** %s" % (cfg.get("thoroughness"), cfg.get("version")),
    ]
    if impl:
        lines.append("**Implementation:** commit=`%s` · dirty=`%s` · runtime=`%s`" % (
            impl.get("git_commit"), impl.get("git_dirty"), impl.get("runtime_sha256")))
    lines.append("**Manifest:** %s · `sha256:%s`" %
                 (_md_link("artifact-manifest.json", manifest_path, output_dir), manifest_sha))
    score_path = os.path.join(run, "score.json")
    if os.path.isfile(score_path):
        lines.append("**Score:** " + _md_link("score.json", score_path, output_dir))
    lines += [
        "",
        "> Start at L0. Descend only when the downstream task needs a branch, claim, decision, or",
        "> primary. This dossier is lossless **by reference**: it embeds every branch synthesis and",
        "> content-addresses every durable artifact, but it does not inject full reads or transcripts.",
        "",
        "## Navigation contract",
        "",
        "- **L0 — answer:** the verified `brief.md`, immediately below.",
        "- **L1 — survey map and branch syntheses:** what each branch contributes, disputes, and leaves open.",
        "- **L2 — claims, evidence, and decisions:** exact verdicts and links to full node traces.",
        "- **L3 — raw artifacts:** evidence packs, source indexes, full reads, telemetry, and execution state.",
        "- Follow links downward or sideways; do not treat worker agreement as independent evidence.",
        "",
        "## L0 — synthesized answer",
        "",
    ]
    if brief.strip():
        lines += [brief.rstrip(), "", "Source artifact: " +
                  _md_link("brief.md", os.path.join(run, "brief.md"), output_dir), ""]
    elif root_findings.strip():
        lines += ["> **Warning:** `brief.md` is missing; showing root findings as an incomplete fallback.",
                  "", root_findings.rstrip(), ""]
    else:
        lines += ["> **Warning:** neither `brief.md` nor root findings exists. This handoff is incomplete.", ""]

    lines += ["## L1 — survey map", "",
              "| Branch | State | Question | Branch signal | Evidence footprint | Open |",
              "|---|---|---|---|---:|---|"]
    for node in nodes:
        counts = node.get("counts", {})
        footprint = "%s reads / %s sources / %s decisions" % (
            counts.get("read_artifacts", 0), counts.get("sources", 0), counts.get("decisions", 0))
        lines.append("| `%s` | %s | %s | %s | %s | %s |" % (
            _md_cell(node.get("qid"), 60), _md_cell(node.get("state"), 40),
            _md_cell(node.get("question")), _md_cell(node.get("preview")), footprint,
            _node_links(node, run, output_dir, compact=True)))
    lines.append("")
    if portfolio.strip():
        lines += ["### Competing framing portfolio", "", portfolio.rstrip(), "",
                  "Source artifact: " + _md_link("portfolio.md", os.path.join(run, "portfolio.md"),
                                                 output_dir), ""]

    lines += ["## L1 — self-contained branch syntheses", "",
              "These are the intermediate research products. Open L2/L3 links only when a claim needs",
              "audit, a disagreement needs resolution, or a new synthesis needs more context.", ""]
    brief_norm = brief.strip()
    for node in nodes:
        node_dir = os.path.join(run, node["path"])
        findings = _read(os.path.join(node_dir, "findings.md"))
        lines += ["### `%s` — %s" % (node.get("qid"), node.get("question", "")), "",
                  _node_links(node, run, output_dir), ""]
        if not findings.strip():
            lines += ["> **Missing branch synthesis.** Inspect evidence/status before relying on this branch.", ""]
        elif brief_norm and findings.strip() == brief_norm:
            lines += ["_(This root synthesis is identical to L0; it is linked rather than repeated.)_", ""]
        else:
            lines += [findings.rstrip(), ""]

    claims = _claim_index(run)
    lines += ["## L2 — verified claim index", ""]
    if not claims:
        lines += ["> No structured claim set is available. Treat factual assertions as unaudited.", ""]
    else:
        for claim in claims:
            lines += ["### %s — `%s`" % (claim["id"], claim["verdict"]), "", claim["claim"] or "_(empty claim)_"]
            if claim["urls"]:
                lines.append("- Sources: " + ", ".join("[%d](%s)" % (i + 1, url)
                                                       for i, url in enumerate(claim["urls"])))
            if claim["fact_check"]:
                lines.append("- Fact-check: %s" % claim["fact_check"])
            lines.append("")
        lines += ["Structured artifacts: " + " · ".join(
            link for link in [
                _md_link("claims.jsonl", os.path.join(run, "claims.jsonl"), output_dir)
                if os.path.isfile(os.path.join(run, "claims.jsonl")) else "",
                _md_link("verify.jsonl", os.path.join(run, "verify.jsonl"), output_dir)
                if os.path.isfile(os.path.join(run, "verify.jsonl")) else "",
                _md_link("claim_audit.json", os.path.join(run, "claim_audit.json"), output_dir)
                if os.path.isfile(os.path.join(run, "claim_audit.json")) else "",
            ] if link), ""]

    lines += ["## L2 — key epistemic decisions and rejected paths", "",
              "Only material decisions are previewed here. Each node link exposes the complete trace.", ""]
    any_decision = False
    for node in nodes:
        selected = _key_decisions(os.path.join(run, node["path"]))
        if not selected:
            continue
        any_decision = True
        lines += ["### `%s`" % node.get("qid"), ""]
        for row in selected:
            lines.append("- **%s:** %s — %s" % (row.get("actor", "?"), row.get("decision", ""),
                                                row.get("why", "")))
        decision_path = node.get("files", {}).get("decision_trace")
        if decision_path:
            lines += ["", "Full trace: " + _artifact_link("decisions.jsonl", decision_path, run,
                                                            output_dir), ""]
    if not any_decision:
        lines += ["> No material decision records were found. This is a provenance gap.", ""]

    failed = sum(int(n.get("counts", {}).get("failed_reads", 0) or 0) for n in nodes)
    truncated = sum(int(n.get("counts", {}).get("truncated_reads", 0) or 0) for n in nodes)
    incomplete = [n for n in nodes if n.get("state") in {"pending", "active", "needs_answer",
                                                          "proposes_split"}]
    non_supported = [c for c in claims if c["verdict"] != "supported"]
    lines += ["## Warnings and unresolved state", ""]
    warnings = []
    if incomplete:
        warnings.append("%d node(s) are still nonterminal: %s" %
                        (len(incomplete), ", ".join(str(n.get("qid")) for n in incomplete)))
    if failed:
        warnings.append("%d source record(s) carry an explicit failed-read state" % failed)
    if truncated:
        warnings.append("%d source record(s) are marked truncated" % truncated)
    if non_supported:
        warnings.append("%d claim verdict(s) are not `supported`" % len(non_supported))
    if summary.get("duplicate_content_groups"):
        warnings.append("%d duplicate-content group(s) are identified in the manifest" %
                        summary.get("duplicate_content_groups"))
    if not warnings:
        lines += ["- No structural warning was detected. This is not a semantic truth guarantee.", ""]
    else:
        lines += ["- " + item for item in warnings] + [""]

    lines += ["## L3 — complete artifact inventory", "",
              "- Nodes: **%s**" % summary.get("nodes", 0),
              "- Addressed artifacts: **%s**" % summary.get("artifacts", 0),
              "- Full-read artifacts: **%s** (%s bytes; %s unique-content bytes)" % (
                  summary.get("raw_read_artifacts", 0), summary.get("raw_read_bytes", 0),
                  summary.get("unique_raw_read_bytes", 0)),
              "- Duplicate-content groups: **%s**" % summary.get("duplicate_content_groups", 0),
              "- Machine map: " + _md_link("artifact-manifest.json", manifest_path, output_dir),
              "",
              "The manifest records every artifact path, role, byte count, and SHA-256 digest, plus",
              "per-node counts and content aliases. Raw reads and execution traces remain outside this",
              "default context but are reachable without relying on worker transcripts.", ""]
    bundle_path = os.path.join(run, "bundle.md")
    if os.path.isfile(bundle_path):
        lines += ["Inline transport fallback: " + _md_link("bundle.md", bundle_path, output_dir), ""]
    return "\n".join(lines).rstrip() + "\n"


def write_handoff(run: str, output: str = "", manifest_path: str = "") -> Dict[str, Any]:
    """Persist the manifest first, then the dossier; return hashes for a durable handoff."""
    run = os.path.abspath(run)
    output = os.path.abspath(output or os.path.join(run, "dossier.md"))
    manifest_path = os.path.abspath(manifest_path or os.path.join(run, "artifact-manifest.json"))
    excluded = {output, manifest_path}
    manifest = artifact_manifest(run, excluded)
    _atomic_write(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    text = dossier(run, manifest, output, manifest_path)
    _atomic_write(output, text)
    return {
        "dossier": output,
        "manifest": manifest_path,
        "dossier_sha256": _file_sha256(output),
        "manifest_sha256": _file_sha256(manifest_path),
        "dossier_bytes": os.path.getsize(output),
        "referenced_artifacts": manifest["summary"]["artifacts"],
        "raw_read_artifacts": manifest["summary"]["raw_read_artifacts"],
        "raw_read_bytes": manifest["summary"]["raw_read_bytes"],
    }


def bundle(run: str, reads: bool = False, max_chars: int = 0) -> str:
    """Fully-inline transport fallback for callers without shared artifact access.

    Unlike the old pseudo-complete bundle, this includes node decisions, questions, answers, specs,
    status, and proposals. `reads` inlines primaries; `max_chars` can cap each read.
    """
    cfg = _cfg(run)
    L: List[str] = []
    L.append("# Aletheia Research — FULL BUNDLE (inline transport fallback)")
    L.append("")
    L.append("**Topic:** %s" % cfg.get("topic", ""))
    L.append("**Thoroughness:** %s · **Verbosity:** %s · **Version:** %s"
             % (cfg.get("thoroughness"), cfg.get("verbosity"), cfg.get("version")))
    impl = cfg.get("implementation") or {}
    if impl:
        L.append("**Implementation:** commit=%s · dirty=%s · runtime_sha256=%s"
                 % (impl.get("git_commit"), impl.get("git_dirty"), impl.get("runtime_sha256")))
    L.append("")
    L.append("This is the fully-inline fallback for a caller that cannot open the run directory. "
             "Prefer `report.py handoff` when artifacts are shared: it preserves the same record by "
             "reference without forcing raw reads into context.")
    L.append("")
    brief = _read(os.path.join(run, "brief.md"))
    if brief.strip():
        L.append("## START HERE — brief.md (the synthesized answer)")
        L.append(brief)
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
        for artifact in ("spec.md", "status.json", "proposal.json", "decisions.jsonl",
                         "questions.jsonl", "answers.jsonl"):
            content = _read(os.path.join(node, artifact))
            if content.strip():
                L.append("### %s" % artifact)
                L.append(content)
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
    cfg = _cfg(run)
    return {
        "topic": cfg.get("topic"), "version": cfg.get("version"),
        "implementation": cfg.get("implementation") or {},
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
    ap = argparse.ArgumentParser(description="Aletheia Research output assembler and agent handoff builder.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("handoff"); h.add_argument("--run", required=True)
    h.add_argument("--output", default="",
                   help="dossier path (default: RUN/dossier.md)")
    h.add_argument("--manifest", default="",
                   help="artifact map path (default: RUN/artifact-manifest.json)")
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
    if args.cmd == "handoff":
        payload = write_handoff(args.run, args.output, args.manifest)
        print(json.dumps(payload, indent=2))
    elif args.cmd == "bundle":
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
