#!/usr/bin/env python3
"""Read immutable bundled channel metadata plus a user-scoped preference overlay.

The repository's ``channels.json`` is part of the executable research runtime and must stay
read-only while a skill is installed through a symlink.  Mutable channel selection instead
lives in ``$ALETHEIA_CONFIG_DIR/channels.json`` when explicitly configured, otherwise in
``${XDG_CONFIG_HOME:-~/.config}/aletheia/channels.json``.  The user file deliberately stores
only ``enabled``; all channel metadata continues to come from the versioned bundle.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import tempfile
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional, Tuple


_SCHEMA_VERSION = 1


def _private_umask() -> None:
    """Keep newly-created research artifacts private on POSIX hosts.

    Raw reads and run traces can contain browser-derived or otherwise sensitive material.
    Every bundled runtime client imports this module, so this is the narrowest common place to
    choose private defaults without affecting the host's already-created files.
    """
    if os.name == "posix":
        os.umask(0o077)


_private_umask()


def bundled_channels_path() -> str:
    """Return the immutable channel metadata shipped with this skill bundle."""
    return os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "channels.json"))


def config_dir() -> str:
    """Return the directory for mutable, user-scoped Aletheia preferences."""
    override = os.environ.get("ALETHEIA_CONFIG_DIR", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))
    root = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if root:
        root = os.path.expanduser(root)
    else:
        root = os.path.expanduser("~/.config")
    return os.path.abspath(os.path.join(root, "aletheia"))


def cache_dir() -> str:
    """Return the private, user-scoped cache directory for disposable runtime state."""
    override = os.environ.get("ALETHEIA_CACHE_DIR", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))
    root = os.environ.get("XDG_CACHE_HOME", "").strip()
    if root:
        root = os.path.expanduser(root)
    else:
        root = os.path.expanduser("~/.cache")
    return os.path.abspath(os.path.join(root, "aletheia"))


def ensure_private_dir(path: str) -> str:
    """Create (or repair) a user-owned directory with private POSIX permissions."""
    os.makedirs(path, mode=0o700, exist_ok=True)
    if os.name == "posix":
        try:
            info = os.stat(path)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
                raise OSError("not an owner-controlled directory")
            os.chmod(path, 0o700)
        except (AttributeError, OSError):
            raise OSError("cannot secure private Aletheia directory: %s" % path)
    return path


def user_channels_path() -> str:
    return os.path.join(config_dir(), "channels.json")


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def bundled_channels() -> Dict[str, Any]:
    data = _read_json(bundled_channels_path())
    if not data or not isinstance(data.get("indexes"), dict):
        raise RuntimeError("bundled Aletheia channels.json is missing or invalid")
    return data


def _validated_enabled(raw: Any, indexes: Dict[str, Any]) -> Optional[List[str]]:
    if not isinstance(raw, list):
        return None
    out: List[str] = []
    for name in raw:
        if not isinstance(name, str) or name not in indexes or name in out:
            return None
        out.append(name)
    return out


def _safe_user_overlay(path: str) -> bool:
    """Accept only a regular, private, current-user capability overlay."""
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode):
            return False
        if os.name == "posix":
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                return False
        return True
    except OSError:
        return False


def active_channels() -> Tuple[Dict[str, Any], str]:
    """Return effective metadata and whether preferences came from ``user`` or ``bundled``.

    A missing overlay uses the bundled safe core.  An invalid, unsafe, or stale existing overlay
    fails closed to *no enabled channels* rather than silently restoring network capability.  An
    overlay never replaces channel metadata, so it cannot invent an executable channel or alter its
    class.
    """
    bundled = bundled_channels()
    path = user_channels_path()
    if not os.path.lexists(path):
        return bundled, "bundled"
    overlay = _read_json(path) if _safe_user_overlay(path) else None
    enabled = _validated_enabled((overlay or {}).get("enabled"), bundled["indexes"])
    if (overlay is not None and overlay.get("schema_version") == _SCHEMA_VERSION
            and enabled is not None):
        effective = copy.deepcopy(bundled)
        effective["enabled"] = enabled
        return effective, "user"
    effective = copy.deepcopy(bundled)
    effective["enabled"] = []
    return effective, "invalid"


def load_channels() -> Dict[str, Any]:
    """Return a fresh effective channel configuration for the current process environment."""
    return active_channels()[0]


def active_metadata() -> Dict[str, Any]:
    """Return a reproducible, non-secret summary suitable for run provenance."""
    channels, source = active_channels()
    encoded = json.dumps(channels, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return {
        "source": source,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "enabled": list(channels.get("enabled", [])),
    }


_CHANNEL_ALIASES = {
    "semanticscholar": "semantic_scholar",
    "googlebooks": "google_books",
    "web_ddg": "duckduckgo",
    "web_marginalia": "marginalia",
    "gutendex": "gutenberg",
    "hn": "hackernews",
}


def canonical_channel(name: str) -> str:
    """Translate a client-module name to its bundled channel identifier."""
    return _CHANNEL_ALIASES.get(str(name or "").strip(), str(name or "").strip())


def require_enabled(name: str) -> str:
    """Return a known enabled channel or raise before any connector activity occurs."""
    canonical = canonical_channel(name)
    channels = load_channels()
    if canonical not in channels.get("indexes", {}):
        raise PermissionError("unknown Aletheia channel: %s" % canonical)
    if canonical not in channels.get("enabled", []):
        raise PermissionError(
            "Aletheia channel %r is disabled; enable it in the user-owned capability config before use"
            % canonical)
    return canonical


def _browser_host(resource: str) -> str:
    raw = str(resource or "").strip()
    if not raw:
        return ""
    parsed = urllib.parse.urlsplit(raw if "://" in raw else "https://" + raw)
    return (parsed.hostname or "").rstrip(".").lower()


def browser_authorized(resource: str) -> bool:
    """Check the harness-owned, host-scoped browser capability grant.

    A caller must set ``ALETHEIA_BROWSER_CAPABILITY`` to a comma-separated allowlist such as
    ``reddit.com,x.com`` (or ``*`` in a deliberately broad harness).  This is a policy gate that
    prevents accidental browser/session use; a hostile agent with shell authority can still set its
    own environment, so robust consent requires a host-level broker or sandbox policy.
    """
    host = _browser_host(resource)
    if not host:
        return False
    grants = [item.strip().lower().rstrip(".")
              for item in os.environ.get("ALETHEIA_BROWSER_CAPABILITY", "").split(",")]
    for grant in grants:
        if grant == "*":
            return True
        grant_host = _browser_host(grant)
        if grant_host and (host == grant_host or host.endswith("." + grant_host)):
            return True
    return False


def require_browser_authorization(resource: str) -> None:
    if not browser_authorized(resource):
        raise PermissionError(
            "browser/session access is not authorized for %s; the harness must grant a matching "
            "ALETHEIA_BROWSER_CAPABILITY host" % (_browser_host(resource) or "this target"))


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    directory = os.path.dirname(path)
    ensure_private_dir(directory)
    fd, tmp = tempfile.mkstemp(prefix=".channels-", suffix=".tmp", dir=directory)
    try:
        if os.name == "posix":
            try:
                os.fchmod(fd, 0o600)
            except (AttributeError, OSError):
                pass
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        if os.name == "posix":
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def write_enabled(names: Iterable[str]) -> str:
    """Atomically persist a validated enabled-channel preference overlay."""
    bundled = bundled_channels()
    enabled = _validated_enabled(list(names), bundled["indexes"])
    if enabled is None:
        raise ValueError("enabled channels must be unique known channel names")
    path = user_channels_path()
    _atomic_write(path, {"schema_version": _SCHEMA_VERSION, "enabled": enabled})
    return path


def reset_enabled() -> str:
    """Persist the bundled core defaults as an explicit user preference."""
    bundled = bundled_channels()
    return write_enabled(bundled.get("core_default", []))
