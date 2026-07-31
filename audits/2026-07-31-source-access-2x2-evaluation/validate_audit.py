#!/usr/bin/env python3
"""Offline integrity checks for the checked-in source-access audit bundle."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ERRORS: list[str] = []


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should collect all failures
        ERRORS.append(f"cannot parse {relative}: {type(exc).__name__}: {exc}")
        return {}
    require(isinstance(value, dict), f"{relative}: expected JSON object")
    return value if isinstance(value, dict) else {}


def check_text_files() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or "raw" in path.parts or path.suffix not in {".md", ".py", ".json", ".gitignore"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            ERRORS.append(f"{path.relative_to(ROOT)}: not UTF-8")
            continue
        for number, line in enumerate(lines, start=1):
            if line.rstrip(" \t") != line:
                ERRORS.append(f"{path.relative_to(ROOT)}:{number}: trailing whitespace")


def check_relative_markdown_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        if "raw" in path.parts:
            continue
        for target in pattern.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            clean = target.split("#", 1)[0].strip("<>")
            if not clean:
                continue
            candidate = (path.parent / clean).resolve()
            require(candidate.exists(), f"{path.relative_to(ROOT)}: broken relative link {target}")


def check_python_syntax() -> None:
    for relative in ("run_access_probe.py", "posthoc_adapter_diagnostics.py", "derive_results.py", "validate_audit.py"):
        path = ROOT / relative
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            ERRORS.append(f"{relative}: syntax error: {exc}")


def main() -> int:
    required = {
        "README.md",
        "protocol.md",
        "tasks.json",
        "run_access_probe.py",
        "posthoc_adapter_diagnostics.py",
        "derive_results.py",
        "results.json",
        "results.md",
        "analysis.md",
        "decision-log.md",
        "audit-manifest.json",
        "research/adversarial-review.md",
        "research/protocol-review.md",
        "research/runtime-review.md",
        "research/result-integrity-review.md",
        "research/final-claims-review.md",
    }
    for relative in sorted(required):
        require((ROOT / relative).is_file(), f"missing required artifact: {relative}")

    tasks = read_json("tasks.json")
    results = read_json("results.json")
    manifest = read_json("audit-manifest.json")
    require(results.get("audit_id") == "2026-07-31-source-access-2x2-evaluation", "wrong result audit_id")
    require(manifest.get("audit_id") == "2026-07-31-source-access-2x2-evaluation", "wrong manifest audit_id")

    result_hash = results.get("result_sha256")
    calculated_result_hash = digest({key: value for key, value in results.items() if key != "result_sha256"})
    require(result_hash == calculated_result_hash, "results.json result_sha256 does not verify")
    tasks_hash = digest(tasks)
    contract = results.get("claimed_primary_contract") or {}
    require(contract.get("tasks_sha256") == tasks_hash, "results.json tasks hash does not match tasks.json")
    primary = contract.get("primary_observation") or {}
    lanes = primary.get("lanes") or {}
    generic, specialist = lanes.get("generic_web") or {}, lanes.get("specialist") or {}
    require(generic.get("raw_hit_count") == 1 and generic.get("replay_top_8_count") == 1,
            "unexpected primary generic literal result")
    require(specialist.get("raw_hit_count") == 0 and specialist.get("replay_top_8_count") == 0,
            "unexpected primary specialist literal result")
    replication = results.get("post_hoc_replication") or {}
    replicated_lanes = replication.get("lanes") or {}
    require((replicated_lanes.get("generic_web") or {}).get("raw_hit_count") == 0,
            "unexpected post-hoc generic replication result")
    require((replicated_lanes.get("specialist") or {}).get("raw_hit_count") == 0,
            "unexpected post-hoc specialist replication result")
    diagnostics = results.get("post_hoc_adapter_diagnostic") or {}
    cases = {item.get("id"): item for item in diagnostics.get("cases") or [] if isinstance(item, dict)}
    require((cases.get("europepmc-exact-pmid") or {}).get("first_title_match_rank") == 1,
            "Europe PMC exact-ID diagnostic missing expected title match")
    require((cases.get("europepmc-exact-pmid") or {}).get("first_url_match_rank") is None,
            "Europe PMC exact-ID diagnostic unexpectedly passes URL-only PMID matcher")
    require((cases.get("arxiv-exact-id") or {}).get("first_url_match_rank") == 1,
            "arXiv exact-ID diagnostic missing expected match")
    require((cases.get("github-natural-question") or {}).get("returned") == 0,
            "GitHub natural-question diagnostic no longer records zero results")
    require((cases.get("github-exact-slug") or {}).get("first_url_match_rank") == 1,
            "GitHub exact-slug diagnostic missing expected match")
    require((cases.get("openalex-natural-question-error") or {}).get("provider_http_status") == 400,
            "OpenAlex punctuation diagnostic no longer records HTTP 400")
    validity = results.get("validity_findings") or {}
    require("two adapter invocations per task x access lane" in str(validity.get("execution_units")),
            "results.json omits corrected adapter-invocation unit")
    require("sequential" in str(validity.get("network_snapshot")),
            "results.json omits sequential snapshot limitation")

    for relative in manifest.get("key_artifacts") or []:
        require((ROOT / relative).is_file(), f"manifest points to missing artifact: {relative}")

    check_text_files()
    check_relative_markdown_links()
    check_python_syntax()
    if ERRORS:
        print("audit validation failed:")
        for error in ERRORS:
            print("- " + error)
        return 1
    print("audit validation passed")
    print("results_sha256=" + str(result_hash))
    print("tasks_sha256=" + tasks_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
