#!/usr/bin/env python3
"""Persist every pairwise judge result and separate blind anchors from mapping keys."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _safe(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "unknown")).strip("-")
    return text[:80] or "unknown"


def _order_signature(order: Any) -> str:
    if not isinstance(order, dict) or set(order) != {"A", "B"}:
        return "invalid"
    if order.get("A") == "candidate" and order.get("B") == "baseline":
        return "candidate_first"
    if order.get("A") == "baseline" and order.get("B") == "candidate":
        return "baseline_first"
    return "invalid"


def _neutral_blind_path(path: Any) -> bool:
    """Require judge-visible files below a neutral ``blind-inputs`` directory."""
    text = os.path.normpath(str(path or ""))
    parts = text.split(os.sep)
    try:
        tail = parts[parts.index("blind-inputs") + 1:]
    except ValueError:
        return False
    visible = "/".join(tail).lower()
    return bool(visible) and not re.search(r"(?:^|[-_/])(candidate|baseline)(?:[-_/\.]|$)", visible)


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _atomic_write(path: str, data: bytes, mode: int = 0o644) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".judge-", dir=os.path.dirname(path))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
        os.chmod(path, mode)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json(path: str, value: Any, mode: int = 0o644) -> None:
    _atomic_write(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n", mode)


def _write_jsonl(path: str, rows: List[Dict[str, Any]], mode: int = 0o644) -> None:
    data = b"".join(_canonical(row) + b"\n" for row in rows)
    _atomic_write(path, data, mode)


def _expected_matrix(path: Optional[str], trusted_sha256: str
                     ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any], List[str]]:
    """Load an externally pinned topic/version/canonical-brief matrix."""
    reasons: List[str] = []
    mapping: Dict[str, Dict[str, Any]] = {}
    meta: Dict[str, Any] = {"path": "", "sha256": "", "trusted": False}
    pin = str(trusted_sha256 or "").strip().lower()
    if not path or not re.fullmatch(r"[0-9a-f]{64}", pin):
        return mapping, meta, ["expected_matrix_not_trusted"]
    real = os.path.realpath(path)
    try:
        actual = _sha_file(real)
        with open(real, encoding="utf-8") as fh:
            value = json.load(fh)
    except (OSError, ValueError, json.JSONDecodeError):
        return mapping, meta, ["expected_matrix_unreadable"]
    meta.update({"path": real, "sha256": actual})
    if actual != pin:
        return mapping, meta, ["expected_matrix_sha256_mismatch"]
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return mapping, meta, ["expected_matrix_schema_invalid"]
    topics = value.get("topics")
    if not isinstance(topics, list) or not topics:
        return mapping, meta, ["expected_matrix_schema_invalid"]
    for raw in topics:
        if not isinstance(raw, dict):
            reasons.append("expected_matrix_schema_invalid")
            continue
        topic = str(raw.get("topic") or "").strip()
        if not topic or topic in mapping:
            reasons.append("expected_matrix_topic_missing_or_duplicate")
            continue
        systems: Dict[str, Any] = {}
        for system in ("candidate", "baseline"):
            spec = raw.get(system)
            if not isinstance(spec, dict):
                reasons.append("expected_matrix_schema_invalid")
                continue
            version = str(spec.get("version") or "").strip()
            brief_path = os.path.realpath(str(spec.get("brief_path") or ""))
            declared = str(spec.get("brief_sha256") or "").strip().lower()
            try:
                actual_brief = _sha_file(brief_path)
            except OSError:
                actual_brief = ""
            if (not version or not re.fullmatch(r"[0-9a-f]{64}", declared)
                    or not actual_brief or actual_brief != declared):
                reasons.append("canonical_brief_identity_invalid")
                continue
            systems[system] = {"version": version, "brief_path": brief_path,
                               "brief_sha256": declared}
        if set(systems) == {"candidate", "baseline"}:
            mapping[topic] = systems
    reasons = list(dict.fromkeys(reasons))
    if len(mapping) != len(topics):
        reasons.append("expected_matrix_incomplete")
    meta["trusted"] = not reasons
    return mapping, meta, reasons


def persist(payload: Dict[str, Any], out: str, release_mode: bool = True,
            expected_matrix: Optional[str] = None,
            expected_matrix_sha256: str = "") -> Dict[str, Any]:
    out = os.path.realpath(out)
    os.makedirs(out, exist_ok=True)
    expected, matrix_meta, matrix_reasons = _expected_matrix(
        expected_matrix, expected_matrix_sha256)
    if matrix_meta.get("trusted"):
        _atomic_write(os.path.join(out, "expected-matrix.json"),
                      _read_bytes(str(matrix_meta["path"])))
    artifacts = payload.get("judge_artifacts")
    if not isinstance(artifacts, list):
        artifacts = payload.get("pairwise") or []
    if not isinstance(artifacts, list):
        raise ValueError("judge_artifacts/pairwise must be a list")

    manifest_rows = []
    seen_names: Dict[str, int] = {}
    seen_judges = set()
    pair_groups: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    rows_valid = True
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, dict):
            raise ValueError("judge artifact %d is not an object" % index)
        artifact = dict(raw)
        artifact.setdefault("artifact_index", index)
        artifact.setdefault("schema_version", 2)
        topic = str(artifact.get("topic") or "").strip()
        pair_id_raw = str(artifact.get("pair_id") or "").strip()
        judge_id = str(artifact.get("judge_id") or "").strip()
        judge_unique = bool(judge_id) and judge_id not in seen_judges
        if judge_id:
            seen_judges.add(judge_id)
        order = artifact.get("order") or artifact.get("shown_order") or {}
        signature = _order_signature(order)
        shown = str(artifact.get("winner_shown") or "").strip()
        order_map = order if isinstance(order, dict) else {}
        winner = ("tie" if shown.lower() == "tie" else
                  order_map.get(shown) if shown in ("A", "B") else None)
        declared = str(artifact.get("winner") or "").strip().lower()
        winner_consistent = not declared or declared == winner
        a_path, b_path = str(artifact.get("A_path") or ""), str(artifact.get("B_path") or "")
        input_hashes = {}
        inputs_readable = bool(a_path and b_path and os.path.isfile(a_path) and os.path.isfile(b_path))
        if inputs_readable:
            input_hashes = {"A": _sha_file(a_path), "B": _sha_file(b_path)}
            artifact["input_sha256"] = input_hashes
        expected_topic = expected.get(topic) or {}
        expected_inputs = {}
        if signature != "invalid" and expected_topic:
            expected_inputs = {
                side: expected_topic.get(str(order_map.get(side)) or "", {}).get("brief_sha256")
                for side in ("A", "B")
            }
        canonical_binding_valid = bool(
            expected_inputs and input_hashes
            and all(expected_inputs.get(side) == input_hashes.get(side) for side in ("A", "B"))
        )
        blind_paths_valid = _neutral_blind_path(a_path) and _neutral_blind_path(b_path)
        prompt = str(artifact.get("prompt") or "")
        prompt_inputs_match = bool(a_path and b_path and a_path in prompt and b_path in prompt)
        required = bool(
            topic and pair_id_raw and judge_unique and signature != "invalid"
            and shown in ("A", "B", "tie") and winner_consistent
            and str(artifact.get("judge_model") or "").strip()
            and prompt.strip() and prompt_inputs_match
            and inputs_readable and blind_paths_valid
        )
        rows_valid = rows_valid and required
        semantic_hash = _sha_value(artifact)
        artifact["artifact_sha256"] = semantic_hash
        topic_safe = _safe(topic)
        pair_id = _safe(pair_id_raw or artifact.get("trial") or index)
        base = "%s--%s--%s.json" % (topic_safe, pair_id, signature.replace("_", "-"))
        suffix = seen_names.get(base, 0)
        seen_names[base] = suffix + 1
        filename = base if suffix == 0 else base[:-5] + "--%d.json" % suffix
        path = os.path.join(out, "judges", filename)
        _write_json(path, artifact)
        if topic and pair_id_raw:
            pair_groups.setdefault((topic, pair_id_raw), []).append({
                "signature": signature,
                "input_sha256": input_hashes,
                "row_valid": required,
                "canonical_binding_valid": canonical_binding_valid,
            })
        manifest_rows.append({"index": index, "path": os.path.relpath(path, out),
                              "file_sha256": _sha_file(path), "artifact_sha256": semantic_hash,
                              "paired_schema_valid": required,
                              "judge_id_unique": judge_unique,
                              "blind_input_paths_valid": blind_paths_valid,
                              "prompt_inputs_match": prompt_inputs_match,
                              "input_sha256": input_hashes,
                              "expected_canonical_input_sha256": expected_inputs,
                              "canonical_binding_valid": canonical_binding_valid})

    pair_manifest = []
    exact_pairs_valid = bool(pair_groups)
    for (topic, pair_id), group in sorted(pair_groups.items()):
        by_order = {row["signature"]: row for row in group if row["signature"] != "invalid"}
        exact_two = (len(group) == 2 and len(by_order) == 2
                     and set(by_order) == {"candidate_first", "baseline_first"})
        content_swap_valid = False
        if exact_two:
            cf, bf = by_order["candidate_first"], by_order["baseline_first"]
            content_swap_valid = bool(
                cf["input_sha256"] and bf["input_sha256"]
                and cf["input_sha256"].get("A") == bf["input_sha256"].get("B")
                and cf["input_sha256"].get("B") == bf["input_sha256"].get("A")
            )
        bindings_valid = all(row["canonical_binding_valid"] for row in group)
        valid = exact_two and content_swap_valid and all(row["row_valid"] for row in group)
        exact_pairs_valid = exact_pairs_valid and valid
        pair_manifest.append({"topic": topic, "pair_id": pair_id, "artifact_count": len(group),
                              "exact_two_orders": exact_two,
                              "content_swap_valid": content_swap_valid,
                              "canonical_bindings_valid": bindings_valid, "valid": valid})
    paired_schema_valid = (bool(artifacts) and rows_valid and exact_pairs_valid
                           and sum(len(group) for group in pair_groups.values()) == len(artifacts))

    anchors = payload.get("anchor_public")
    if not isinstance(anchors, list):
        anchors = payload.get("anchor") or []
    if not isinstance(anchors, list):
        raise ValueError("anchor/anchor_public must be a list")
    public_rows, key_rows, anchor_artifacts = [], [], []
    secret_keys = {"_cand_is", "candidate_is", "mapping", "generator_mapping"}
    seen_topics = set()
    for index, raw in enumerate(anchors):
        if not isinstance(raw, dict):
            raise ValueError("anchor is not an object")
        topic = str(raw.get("topic") or "").strip()
        if not topic or topic in seen_topics:
            raise ValueError("anchor topic is missing or duplicated: %s" % topic)
        seen_topics.add(topic)
        a_source, b_source = str(raw.get("A") or ""), str(raw.get("B") or "")
        if not os.path.isfile(a_source) or not os.path.isfile(b_source):
            raise ValueError("anchor %s inputs are missing" % topic)
        anchor_dir = os.path.join(out, "anchors", "%03d-%s" % (index, _safe(topic)))
        a_blind, b_blind = os.path.join(anchor_dir, "A.md"), os.path.join(anchor_dir, "B.md")
        _atomic_write(a_blind, _read_bytes(a_source))
        _atomic_write(b_blind, _read_bytes(b_source))
        public = {"topic": topic}
        if raw.get("question") is not None:
            public["question"] = raw.get("question")
        public.update({"A": os.path.relpath(a_blind, out), "B": os.path.relpath(b_blind, out)})
        key = {"topic": topic}
        if raw.get("_cand_is") is not None:
            key["candidate_is"] = raw.get("_cand_is")
        elif raw.get("candidate_is") is not None:
            key["candidate_is"] = raw.get("candidate_is")
        public_rows.append(public)
        key_rows.append(key)
        anchor_artifacts.append({"topic": topic, "A": public["A"], "B": public["B"],
                                 "A_sha256": _sha_file(a_blind), "B_sha256": _sha_file(b_blind)})
    separate_key = payload.get("anchor_key")
    if isinstance(separate_key, list):
        key_rows = [dict(row) for row in separate_key if isinstance(row, dict)]

    key_by_topic = {}
    key_valid = True
    for row in key_rows:
        topic = str(row.get("topic") or "").strip()
        candidate_is = str(row.get("candidate_is") or "").strip()
        if not topic or topic in key_by_topic or candidate_is not in ("A", "B"):
            key_valid = False
            continue
        key_by_topic[topic] = {"topic": topic, "candidate_is": candidate_is}
    key_valid = key_valid and set(key_by_topic) == {row["topic"] for row in public_rows}
    key_rows = [key_by_topic[row["topic"]] for row in public_rows if row["topic"] in key_by_topic]

    public_path, key_path = os.path.join(out, "anchor-public.jsonl"), os.path.join(out, "anchor-key.jsonl")
    _write_jsonl(public_path, public_rows)
    _write_jsonl(key_path, key_rows, mode=0o600)
    leaked = any(any(k in row for k in secret_keys) for row in public_rows)
    anchor_schema_valid = bool(public_rows) and len(public_rows) == len(anchors)
    observed_topics = {topic for topic, _pair_id in pair_groups}
    expected_topics = set(expected)
    expected_topic_matrix_complete = bool(expected) and observed_topics == expected_topics
    canonical_brief_bindings_valid = bool(manifest_rows) and all(
        row["canonical_binding_valid"] for row in manifest_rows)
    expected_versions = {
        topic: {system: spec[system]["version"] for system in ("candidate", "baseline")}
        for topic, spec in sorted(expected.items())
    }
    release_reasons = list(matrix_reasons)
    if matrix_meta.get("trusted") and not expected_topic_matrix_complete:
        release_reasons.append("observed_topics_do_not_match_expected_matrix")
    if matrix_meta.get("trusted") and not canonical_brief_bindings_valid:
        release_reasons.append("blind_inputs_do_not_match_canonical_briefs")
    if not paired_schema_valid:
        release_reasons.append("paired_schema_invalid")
    if not anchor_schema_valid or not key_valid or leaked:
        release_reasons.append("anchor_schema_or_separation_invalid")
    if not release_mode:
        release_reasons.append("diagnostic_mode_not_release")
    release_reasons = list(dict.fromkeys(release_reasons))
    manifest = {
        "schema_version": 2,
        "release_mode": release_mode,
        "release_gate_passed": bool(release_mode and not release_reasons),
        "release_invalid_reasons": release_reasons,
        "persistence_code_sha256": _sha_file(os.path.realpath(__file__)),
        "aggregation_code_sha256": _sha_file(os.path.join(os.path.dirname(__file__),
                                                           "judge_score.py")),
        "input_sha256": _sha_value(payload),
        "expected_matrix_trusted": bool(matrix_meta.get("trusted")),
        "expected_matrix_sha256": matrix_meta.get("sha256") or None,
        "expected_matrix_artifact": ("expected-matrix.json" if matrix_meta.get("trusted") else None),
        "expected_topic_count": len(expected),
        "expected_topics": sorted(expected),
        "expected_versions": expected_versions,
        "expected_topic_matrix_complete": expected_topic_matrix_complete,
        "canonical_brief_bindings_valid": canonical_brief_bindings_valid,
        "judge_artifact_count": len(artifacts),
        "persisted_judge_artifact_count": len(manifest_rows),
        "every_judge_artifact_persisted": len(artifacts) == len(manifest_rows),
        "paired_schema_valid": paired_schema_valid,
        "pairs": pair_manifest,
        "public_anchor_count": len(public_rows),
        "anchor_schema_valid": anchor_schema_valid,
        "anchor_mapping_separated": not leaked and key_valid,
        "anchor_key_complete": key_valid,
        "anchor_public_sha256": _sha_file(public_path),
        "anchor_key_sha256": _sha_file(key_path),
        "anchor_artifacts": anchor_artifacts,
        "artifacts": manifest_rows,
    }
    _write_json(os.path.join(out, "manifest.json"), manifest)
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Persist all judge artifacts with a hashed manifest")
    ap.add_argument("results")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-matrix", default="")
    ap.add_argument("--expected-matrix-sha256", default="")
    ap.add_argument("--legacy-diagnostic", action="store_true",
                    help="preserve unhashed legacy diagnostics; never release-valid")
    args = ap.parse_args(argv)
    try:
        with open(args.results, encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, dict):
            raise ValueError("results must be a JSON object")
        manifest = persist(payload, args.out, release_mode=not args.legacy_diagnostic,
                           expected_matrix=args.expected_matrix or None,
                           expected_matrix_sha256=args.expected_matrix_sha256)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("persist-judges: %s\n" % exc)
        return 2
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if args.legacy_diagnostic:
        return 0 if (manifest["every_judge_artifact_persisted"]
                     and manifest["paired_schema_valid"]
                     and manifest["anchor_schema_valid"]
                     and manifest["anchor_mapping_separated"]) else 1
    return 0 if manifest["release_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
