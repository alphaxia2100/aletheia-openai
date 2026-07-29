#!/usr/bin/env python3
"""Small, dependency-free integrity check for this committed audit dossier.

It deliberately does not fetch external URLs: external availability is volatile
and is recorded in the research artifacts. It validates the machine-readable
manifest, required files, and local Markdown links before a future audit is
committed or amended.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "README.md",
    "audit-manifest.json",
    "v2-design.md",
    "acceptance-contract.md",
    "decision-log.md",
    "research/control-plane.md",
    "research/workflows-and-alternatives.md",
    "research/adversary-and-evaluation.md",
    "research/channel-health-2026-07-29.md",
)
LINK = re.compile(r"(?<!!)(?<!\\\\)\[[^\]]*\]\(([^)]+)\)")
IGNORED_PREFIXES = ("#", "http://", "https://", "mailto:", "data:", "javascript:")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            fail(errors, f"required file missing: {name}")

    manifest_path = ROOT / "audit-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, f"invalid audit-manifest.json: {exc}")
        manifest = {}

    for field in ("schema_version", "audit_id", "status", "question", "conclusion", "deliverables", "limitations"):
        if field not in manifest:
            fail(errors, f"manifest field missing: {field}")
    if manifest.get("audit_id") != "2026-07-29-v2-ground-up-design":
        fail(errors, "manifest audit_id does not identify this dossier")
    for name in manifest.get("deliverables", []):
        if not (ROOT / name).is_file():
            fail(errors, f"manifest deliverable missing: {name}")

    checked = 0
    for path in ROOT.rglob("*.md"):
        # Local raw run state is intentionally ignored and can contain retrieved
        # webpage markup. It is not part of the committed dossier contract.
        if "research-runs" in path.parts or "raw" in path.parts or "fixtures" in path.parts:
            continue
        checked += 1
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for raw_target in LINK.findall(line):
                target = raw_target.strip().strip("<>")
                if not target or target.startswith(IGNORED_PREFIXES):
                    continue
                file_target = target.split("#", 1)[0]
                if file_target and not (path.parent / file_target).resolve().exists():
                    fail(errors, f"broken local link: {path.relative_to(ROOT)}:{line_number}: {target}")

    if errors:
        print("Dossier validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Dossier validation passed: {checked} Markdown files and {len(REQUIRED)} required files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
