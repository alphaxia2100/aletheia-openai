#!/usr/bin/env python3
"""Objective static checks for the field-dossier handoff experiment.

This does not judge research quality. It proves artifact coverage, hashes, links, branch-synthesis
coverage, raw-read non-injection, and answer position against an optional production flat bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from urllib.parse import unquote, urlparse


def read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_files(run: str, excluded: set[str]) -> dict[str, str]:
    out = {}
    for directory, subdirs, files in os.walk(run):
        subdirs[:] = sorted(d for d in subdirs if d != "__pycache__")
        for filename in sorted(files):
            path = os.path.abspath(os.path.join(directory, filename))
            if path in excluded or os.path.islink(path):
                continue
            out[os.path.relpath(path, run).replace(os.sep, "/")] = path
    return out


def node_findings(run: str) -> list[str]:
    out = []
    for directory, _subdirs, files in os.walk(os.path.join(run, "tree")):
        if "status.json" in files and "findings.md" in files:
            path = os.path.join(directory, "findings.md")
            if os.path.getsize(path):
                out.append(path)
    return sorted(out)


def local_links(markdown_path: str) -> tuple[int, list[str]]:
    text = read(markdown_path)
    base = os.path.dirname(os.path.abspath(markdown_path))
    targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    checked, broken = 0, []
    for raw in targets:
        target = raw.strip().split("#", 1)[0]
        if not target:
            continue
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https", "mailto", "data"}:
            continue
        checked += 1
        path = os.path.abspath(os.path.join(base, unquote(target)))
        if not os.path.exists(path):
            broken.append(raw)
    return checked, broken


def answer_offset(container: str, brief: str) -> dict[str, object]:
    pos = container.find(brief.strip()) if brief.strip() else -1
    return {"found": pos >= 0, "byte_offset": pos,
            "relative_offset": round(pos / max(1, len(container)), 4) if pos >= 0 else None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check an Aletheia field dossier against its run.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--dossier", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--baseline-bundle", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    run = os.path.abspath(args.run)
    dossier_path = os.path.abspath(args.dossier)
    manifest_path = os.path.abspath(args.manifest)
    manifest = json.loads(read(manifest_path))
    dossier_text = read(dossier_path)
    brief_text = read(os.path.join(run, "brief.md")) if os.path.isfile(os.path.join(run, "brief.md")) else ""
    excluded = {dossier_path, manifest_path}
    actual = run_files(run, excluded)
    declared = {row["path"]: row for row in manifest.get("artifacts", [])}
    missing_rows = sorted(set(actual) - set(declared))
    stale_rows = sorted(set(declared) - set(actual))
    hash_mismatches = sorted(rel for rel in set(actual) & set(declared)
                             if sha256(actual[rel]) != declared[rel].get("sha256"))

    findings = node_findings(run)
    missing_findings = []
    for path in findings:
        body = read(path).strip()
        # Identical root brief is deliberately linked instead of repeated.
        if body and body not in dossier_text and body != brief_text.strip():
            missing_findings.append(os.path.relpath(path, run).replace(os.sep, "/"))

    notes = [path for rel, path in actual.items() if "/notes/" in "/" + rel and rel.endswith(".md")]
    inlined_raw = []
    for path in notes:
        body = read(path).strip()
        if len(body) >= 200 and body in dossier_text:
            inlined_raw.append(os.path.relpath(path, run).replace(os.sep, "/"))

    checked_links, broken_links = local_links(dossier_path)
    result = {
        "schema": "aletheia.handoff-static-check.v1",
        "run": run,
        "candidate": {
            "dossier_bytes": os.path.getsize(dossier_path),
            "manifest_bytes": os.path.getsize(manifest_path),
            "answer": answer_offset(dossier_text, brief_text),
            "nodes_with_findings": len(findings),
            "missing_branch_syntheses": missing_findings,
            "raw_read_artifacts": len(notes),
            "inlined_raw_reads": inlined_raw,
            "local_links_checked": checked_links,
            "broken_local_links": broken_links,
            "manifest_rows": len(declared),
            "missing_manifest_rows": missing_rows,
            "stale_manifest_rows": stale_rows,
            "hash_mismatches": hash_mismatches,
        },
    }
    if args.baseline_bundle:
        baseline = read(args.baseline_bundle)
        result["baseline"] = {
            "bundle_bytes": os.path.getsize(args.baseline_bundle),
            "answer": answer_offset(baseline, brief_text),
            "mentions_decision_trace": "decisions.jsonl" in baseline,
        }
        result["candidate"]["entrypoint_byte_reduction_vs_bundle"] = round(
            1 - os.path.getsize(dossier_path) / max(1, os.path.getsize(args.baseline_bundle)), 4)
    candidate = result["candidate"]
    result["static_pass"] = not any((candidate["missing_branch_syntheses"],
                                      candidate["inlined_raw_reads"],
                                      candidate["broken_local_links"],
                                      candidate["missing_manifest_rows"],
                                      candidate["stale_manifest_rows"],
                                      candidate["hash_mismatches"])) and candidate["answer"]["found"]
    payload = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
    print(payload)
    return 0 if result["static_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

