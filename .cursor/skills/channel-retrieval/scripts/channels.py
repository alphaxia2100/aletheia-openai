#!/usr/bin/env python3
"""Enable/disable channels for the Aletheia core.

Only channels in the active configuration's "enabled" list are visible to the agent (the CORE).
Every other index is disabled and hidden but ready. Bundled channel metadata is immutable; this
tool writes only a user-scoped preference overlay, atomically.

Usage:
  channels.py list            # show the enabled core
  channels.py list --all      # show every channel with [on]/[off]
  channels.py enable NAME...   # add channel(s) to the core
  channels.py disable NAME...  # remove channel(s)
  channels.py reset           # restore core_default
  channels.py core            # print core_default

Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import sys
from typing import List

import _config


def _load() -> dict:
    return _config.load_channels()


def _write_enabled(names: List[str]) -> str:
    return _config.write_enabled(names)


def main(argv: List[str]) -> int:
    data = _load()
    indexes = data.get("indexes", {})
    enabled = list(data.get("enabled", []))
    core = list(data.get("core_default", []))

    cmd = argv[0] if argv else "list"
    args = argv[1:]

    if cmd == "core":
        print(" ".join(core))
        return 0

    if cmd == "list":
        if "--all" in args:
            for name in sorted(indexes):
                mark = "on " if name in enabled else "off"
                idx = indexes[name]
                print("[%s] %-18s %-10s %s" % (mark, name, idx.get("class", ""), idx.get("index_group", "")))
            print("\n%d enabled of %d channels." % (len(enabled), len(indexes)))
        else:
            for name in enabled:
                idx = indexes.get(name, {})
                print("%-18s %-10s %s" % (name, idx.get("class", ""), idx.get("index_group", "")))
            print("\n%d enabled (the core). `channels.py list --all` to see the rest." % len(enabled))
        return 0

    if cmd in ("enable", "disable"):
        if not args:
            sys.exit("%s needs at least one channel name" % cmd)
        unknown = [a for a in args if a not in indexes]
        if unknown:
            sys.exit("unknown channel(s): %s\nvalid: %s" % (", ".join(unknown), ", ".join(sorted(indexes))))
        s = list(enabled)
        for a in args:
            if cmd == "enable" and a not in s:
                s.append(a)
            if cmd == "disable" and a in s:
                s.remove(a)
        path = _write_enabled(s)
        print("%sd: %s\nenabled now: %s\npreferences: %s" %
              (cmd, ", ".join(args), ", ".join(s), path))
        return 0

    if cmd == "reset":
        path = _config.reset_enabled()
        print("reset to core: %s\npreferences: %s" % (", ".join(core), path))
        return 0

    sys.exit("unknown command %r (list|enable|disable|reset|core)" % cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
