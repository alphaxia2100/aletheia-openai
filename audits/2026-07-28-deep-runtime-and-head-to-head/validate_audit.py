#!/usr/bin/env python3
"""Validate immutable evidence records for this audit without touching product code.

Run from any directory:
    python3 audits/2026-07-28-deep-runtime-and-head-to-head/validate_audit.py

This checks the claims that can be checked mechanically: JSON syntax, contiguous
line-review accounting, frozen-source hashes, comparison packet hashes, and
anonymous-output hashes. It intentionally does not claim to re-prove qualitative
judgments or live-network behavior.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


AUDIT = Path(__file__).resolve().parent
REPO = AUDIT.parent.parent
ERRORS: list[str] = []


def fail(message: str) -> None:
    ERRORS.append(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(commit: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        fail(f"cannot read frozen blob {commit}:{path}: {result.stderr.decode().strip()}")
        return None
    return result.stdout


def line_count(blob: bytes) -> int:
    if not blob:
        return 0
    return len(blob.splitlines())


def coverage_ranges(record: dict[str, Any]) -> list[tuple[int, int]]:
    accounting = record.get("accounting", {})
    raw = accounting.get("inspected_ranges") or record.get("ranges_reviewed") or record.get("reviewed_ranges")
    if not raw:
        fail(f"no review ranges for {record.get('path')}")
        return []
    output: list[tuple[int, int]] = []
    for item in raw:
        if isinstance(item, dict):
            start, end = item.get("start"), item.get("end")
        else:
            start, end = item
        if not isinstance(start, int) or not isinstance(end, int):
            fail(f"bad review range for {record.get('path')}: {item!r}")
            continue
        output.append((start, end))
    return output


def assert_full_coverage(path: str, count: int, ranges: Iterable[tuple[int, int]]) -> None:
    covered: set[int] = set()
    for start, end in ranges:
        if start < 1 or end < start or end > count:
            fail(f"out-of-bounds review range for {path}: {start}-{end} of {count}")
            continue
        covered.update(range(start, end + 1))
    expected = set(range(1, count + 1))
    if covered != expected:
        missing = sorted(expected - covered)
        extra = sorted(covered - expected)
        fail(f"non-contiguous coverage for {path}: missing={missing[:8]} extra={extra[:8]}")


def frozen_commit(manifest: dict[str, Any]) -> str | None:
    audit = manifest.get("audit", {})
    return (
        audit.get("audited_code_commit")
        or manifest.get("frozen_candidate_commit")
        or manifest.get("frozen_commit")
    )


def check_coverage_manifest(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    commit = frozen_commit(data)
    if not commit:
        fail(f"no frozen commit in {path.name}")
        return 0
    checked = 0
    # The first two manifests use `files`; the control-plane record predates
    # that compact schema and calls the same collection `source_files`.
    for record in data.get("files", data.get("source_files", [])):
        source_path = record["path"]
        blob = git_blob(commit, source_path)
        if blob is None:
            continue
        expected_lines = record.get("line_count")
        observed_lines = line_count(blob)
        if expected_lines != observed_lines:
            fail(f"line count drift for {source_path}: manifest={expected_lines} frozen={observed_lines}")
        assert_full_coverage(source_path, observed_lines, coverage_ranges(record))
        expected_hash = record.get("sha256")
        if expected_hash and sha256(blob) != expected_hash:
            fail(f"frozen SHA-256 mismatch for {source_path}")
        checked += 1
    print(f"OK coverage: {path.name} ({checked} files at {commit[:12]})")
    return checked


def check_json_files() -> int:
    checked = 0
    for path in sorted(AUDIT.rglob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))
        checked += 1
    print(f"OK JSON syntax: {checked} files")
    return checked


def check_source_packet() -> None:
    data = json.loads((AUDIT / "comparison" / "source-fingerprints.json").read_text(encoding="utf-8"))
    commit = data["source_commit"]
    for source_path, expected_hash in data["files"].items():
        blob = git_blob(commit, source_path)
        if blob is not None and sha256(blob) != expected_hash:
            fail(f"comparison source hash mismatch for {source_path}")
    print(f"OK frozen comparison packet: {len(data['files'])} files at {commit[:12]}")


def check_blind_outputs() -> None:
    data = json.loads((AUDIT / "comparison" / "blind-map.json").read_text(encoding="utf-8"))
    for filename, record in data["outputs"].items():
        observed = sha256((AUDIT / "comparison" / filename).read_bytes())
        if observed != record["sha256"]:
            fail(f"blind output hash mismatch for {filename}")
    print(f"OK blind output hashes: {len(data['outputs'])} files")


def check_whitespace() -> None:
    result = subprocess.run(
        ["git", "diff", "--check", "--", str(AUDIT.relative_to(REPO))],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode:
        fail("git diff --check failed: " + result.stdout.strip())
    else:
        print("OK git diff --check")


def main() -> int:
    try:
        check_json_files()
        manifests = sorted((AUDIT / "line-review").glob("*-coverage.json"))
        for manifest in manifests:
            check_coverage_manifest(manifest)
        check_source_packet()
        check_blind_outputs()
        check_whitespace()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        fail(f"validator exception: {type(exc).__name__}: {exc}")
    if ERRORS:
        print("FAIL audit validation:", file=sys.stderr)
        for error in ERRORS:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("PASS audit evidence validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
