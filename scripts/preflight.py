#!/usr/bin/env python3
"""Offline integrity check for an Aletheia checkout or copied runtime.

This intentionally makes no network requests, installs no packages, and writes no bytecode.
Run it before installing on a new machine or against a copied Codex runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from typing import List


REQUIRED = (
    ("aletheia-research", "SKILL.md"),
    ("aletheia-research", "agents/openai.yaml"),
    ("aletheia-research", "scripts/treestate.py"),
    ("aletheia-research", "scripts/investigate.py"),
    ("aletheia-research", "scripts/report.py"),
    ("channel-retrieval", "SKILL.md"),
    ("channel-retrieval", "channels.json"),
    ("channel-retrieval", "scripts/_config.py"),
    ("channel-retrieval", "scripts/_http.py"),
    ("channel-retrieval", "scripts/channels.py"),
    ("provenance-audit", "scripts/dedupe.py"),
    ("provenance-audit", "scripts/provenance_graph.py"),
)

# A copied runtime is intentionally independent of its source checkout, so it cannot use Git to
# answer the basic question "did every installed runtime file arrive intact?"  This manifest is an
# offline, accidental-corruption/tamper-evidence check.  It is not a signature and therefore does
# not authenticate a maliciously replaced runtime or release source.
MANIFEST_NAME = "MANIFEST.sha256"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _skills_root(root: str) -> str:
    candidates = (
        os.path.join(root, ".cursor", "skills"),
        os.path.join(root, "skills"),
    )
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return candidates[0]


def _python_files(root: str):
    for dirname, _dirs, names in os.walk(root):
        for name in names:
            if name.endswith(".py"):
                yield os.path.join(dirname, name)


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_rows(root: str):
    """Yield deterministic hashes for regular runtime files.

    Python bytecode caches are deliberately ignored: a normal skill run may create them after the
    first preflight and they are not part of the distributable runtime.  The install marker is
    written after the manifest and records local installation metadata rather than executable
    content.
    """
    root = os.path.abspath(root)
    ignored = {MANIFEST_NAME, ".aletheia-install.json"}
    for dirname, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            # ``write_manifest`` itself uses a sibling temporary file.  It exists while rows are
            # enumerated but is intentionally not part of the finished runtime.
            if (name in ignored or name.startswith(".%s-" % MANIFEST_NAME)
                    or name.endswith((".pyc", ".pyo"))):
                continue
            path = os.path.join(dirname, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            yield _hash_file(path), rel


def write_manifest(root: str) -> str:
    """Atomically write a SHA-256 manifest for a copied runtime."""
    root = os.path.abspath(root)
    target = os.path.join(root, MANIFEST_NAME)
    fd, temporary = tempfile.mkstemp(prefix=".%s-" % MANIFEST_NAME, dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fd = -1
            for digest, rel in _manifest_rows(root):
                fh.write("%s  %s\n" % (digest, rel))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporary, target)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return target


def _manifest_expected(root: str):
    """Read a manifest safely enough for offline validation, returning rows or an error."""
    path = os.path.join(root, MANIFEST_NAME)
    try:
        with open(path, encoding="utf-8") as fh:
            lines = list(fh)
    except OSError as exc:
        return None, "cannot read %s: %s" % (MANIFEST_NAME, exc)
    expected = {}
    for number, line in enumerate(lines, 1):
        digest, separator, rel = line.rstrip("\n").partition("  ")
        normalized = rel.replace("\\", "/")
        if (not separator or not _DIGEST.fullmatch(digest) or not normalized
                or normalized.startswith("/") or ".." in normalized.split("/")):
            return None, "invalid %s row %d" % (MANIFEST_NAME, number)
        if normalized in expected:
            return None, "duplicate %s path: %s" % (MANIFEST_NAME, normalized)
        expected[normalized] = digest
    if not expected:
        return None, "%s is empty" % MANIFEST_NAME
    return expected, ""


def verify_manifest(root: str):
    """Return ``(ok, errors)`` for the copied-runtime manifest."""
    expected, error = _manifest_expected(root)
    if expected is None:
        return False, [error]
    errors = []
    actual_rows = {rel: digest for digest, rel in _manifest_rows(root)}
    for rel, digest in expected.items():
        path = os.path.join(root, *rel.split("/"))
        if os.path.islink(path) or not os.path.isfile(path):
            errors.append("manifest file missing or not regular: %s" % rel)
            continue
        try:
            actual = _hash_file(path)
        except OSError as exc:
            errors.append("cannot hash manifest file %s: %s" % (rel, exc))
            continue
        if actual != digest:
            errors.append("manifest digest mismatch: %s" % rel)
    for rel in sorted(set(actual_rows) - set(expected)):
        errors.append("unexpected runtime file not in manifest: %s" % rel)
    return not errors, errors


def _portable_runtime(root: str) -> bool:
    """Whether this root is an installer-created runtime that must carry a manifest."""
    marker = os.path.join(root, ".aletheia-install.json")
    try:
        with open(marker, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("mode") in ("portable-copy", "container-runtime")


def _runtime_symlinks(root: str) -> List[str]:
    """Return every symlink below a copied runtime, including directory symlinks."""
    found: List[str] = []
    if os.path.islink(root):
        found.append(".")
    for dirname, dirs, names in os.walk(root, followlinks=False):
        for name in list(dirs) + list(names):
            path = os.path.join(dirname, name)
            if os.path.islink(path):
                found.append(os.path.relpath(path, root).replace(os.sep, "/"))
        # Do not descend into a symlink even if a platform's walk implementation changes.
        dirs[:] = [name for name in dirs if not os.path.islink(os.path.join(dirname, name))]
    return sorted(set(found))


def _runtime_env_files(root: str) -> List[str]:
    """Find secret-like dotenv files accidentally placed in a distributable runtime."""
    found: List[str] = []
    for dirname, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in names:
            if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
                found.append(os.path.relpath(os.path.join(dirname, name), root).replace(os.sep, "/"))
    return sorted(found)


def check(root: str) -> dict:
    root = os.path.abspath(root)
    skills = _skills_root(root)
    errors: List[str] = []
    warnings: List[str] = []
    if sys.version_info < (3, 9):
        errors.append("Python 3.9+ is required (found %s)" % sys.version.split()[0])
    for skill, rel in REQUIRED:
        path = os.path.join(skills, skill, rel)
        if not os.path.isfile(path):
            errors.append("missing required runtime file: %s" % os.path.relpath(path, root))
    if os.path.isdir(skills):
        for path in _python_files(skills):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    compile(fh.read(), path, "exec")
            except (OSError, SyntaxError) as exc:
                errors.append("cannot compile %s: %s" % (os.path.relpath(path, root), exc))
    else:
        errors.append("skills directory is missing: %s" % skills)
    portable = _portable_runtime(root)
    manifest = "not-applicable"
    if portable:
        for rel in _runtime_symlinks(root):
            errors.append("copied runtime contains a symlink: %s" % rel)
        for rel in _runtime_env_files(root):
            errors.append("copied runtime contains a secret-like dotenv file: %s" % rel)
        manifest = "verified"
        manifest_ok, manifest_errors = verify_manifest(root)
        if not manifest_ok:
            manifest = "failed"
            errors.extend(manifest_errors)
    elif os.path.lexists(os.path.join(root, ".env")):
        warnings.append("checkout contains a .env file; do not distribute it in a copied runtime")
    return {
        "ok": not errors,
        "python": sys.version.split()[0],
        "runtime_root": root,
        "skills_root": skills,
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="offline Aletheia portability preflight")
    parser.add_argument("--runtime", default="", help="checkout root or copied .aletheia-runtime directory")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-manifest", action="store_true",
                        help="write a runtime SHA-256 manifest (installer/container build use only)")
    args = parser.parse_args(argv)
    default_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    root = args.runtime or default_root
    result = check(root)
    if args.write_manifest:
        if result["errors"]:
            result["ok"] = False
        else:
            result["manifest"] = "written"
            result["manifest_path"] = write_manifest(root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Aletheia preflight: %s" % ("PASS" if result["ok"] else "FAIL"))
        print("  Python: %s" % result["python"])
        print("  Skills: %s" % result["skills_root"])
        print("  Manifest: %s" % result["manifest"])
        for warning in result["warnings"]:
            print("  warning: %s" % warning)
        for error in result["errors"]:
            print("  error: %s" % error)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
