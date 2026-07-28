#!/usr/bin/env python3
"""Regression tests for the portable runtime's local capability boundaries.

These are deliberately hermetic: no test depends on a real connector, browser session,
or the machine's Aletheia preferences.  They lock in the properties that make a copied
runtime safe to invoke from another agent harness.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNEL_SCRIPTS = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts")
RESEARCH_SCRIPTS = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")
for _path in (RESEARCH_SCRIPTS, CHANNEL_SCRIPTS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import _agentreach  # noqa: E402
import _config  # noqa: E402
import _http  # noqa: E402
import arxiv  # noqa: E402
import read as channel_read  # noqa: E402
import youtube  # noqa: E402


def _write_overlay(directory: str, enabled, raw: str = "") -> str:
    """Write an owner-private test-only capability overlay."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "channels.json")
    with open(path, "w", encoding="utf-8") as fh:
        if raw:
            fh.write(raw)
        else:
            json.dump({"schema_version": 1, "enabled": list(enabled)}, fh)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return path


class TestFailClosedCapabilities(unittest.TestCase):
    def test_malformed_channel_overlay_disables_every_connector(self):
        with tempfile.TemporaryDirectory() as config:
            _write_overlay(config, [], raw="{not valid JSON")
            with mock.patch.dict(os.environ, {"ALETHEIA_CONFIG_DIR": config}, clear=False):
                effective, source = _config.active_channels()
                self.assertEqual(source, "invalid")
                self.assertEqual(effective["enabled"], [])
                with self.assertRaises(PermissionError):
                    _config.require_enabled("arxiv")

    def test_generic_direct_client_refuses_disabled_channel_before_calling_connector(self):
        with tempfile.TemporaryDirectory() as config:
            _write_overlay(config, [])
            called = []

            def connector(*_args):
                called.append(True)
                raise AssertionError("disabled client must not start its connector")

            with mock.patch.dict(os.environ, {"ALETHEIA_CONFIG_DIR": config}, clear=False), \
                    mock.patch.object(sys, "argv", ["arxiv.py", "a query"]):
                self.assertEqual(_http.run_client(connector, "test client"), 2)
            self.assertEqual(called, [])

    def test_custom_direct_client_refuses_disabled_youtube_before_search(self):
        with tempfile.TemporaryDirectory() as config:
            _write_overlay(config, [])
            with mock.patch.dict(os.environ, {"ALETHEIA_CONFIG_DIR": config}, clear=False), \
                    mock.patch.object(sys, "argv", ["youtube.py", "--search", "a query"]), \
                    mock.patch.object(youtube, "yt_search",
                                      side_effect=AssertionError("disabled client must not search")):
                self.assertEqual(youtube.main(), 2)

    def test_explicit_investigate_channels_cannot_revive_disabled_connector(self):
        """A CLI --channels override is a narrowing choice, never a capability escalation."""
        with tempfile.TemporaryDirectory() as tmp:
            config = os.path.join(tmp, "config")
            _write_overlay(config, [])
            env = dict(os.environ, ALETHEIA_CONFIG_DIR=config, HOME=os.path.join(tmp, "home"),
                       PYTHONNOUSERSITE="1")
            treestate = os.path.join(RESEARCH_SCRIPTS, "treestate.py")
            investigate = os.path.join(RESEARCH_SCRIPTS, "investigate.py")
            run = subprocess.check_output(
                [sys.executable, treestate, "init", "capability test", "--thoroughness", "quick",
                 "--base", os.path.join(tmp, "runs")],
                env=env, text=True).strip()
            node = os.path.join(run, "tree", "root")
            proc = subprocess.run(
                [sys.executable, investigate, "--node", node, "--channels", "youtube"],
                env=env, text=True, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("refusing disabled Aletheia channel", proc.stderr)
            self.assertFalse(os.path.exists(os.path.join(node, "telemetry.jsonl")))


class TestBrowserCapabilityBoundary(unittest.TestCase):
    def test_denied_browser_read_never_probes_browser_or_jina(self):
        url = "https://example.com/research"
        with mock.patch.dict(os.environ, {"ALETHEIA_BROWSER_CAPABILITY": ""}, clear=False), \
                mock.patch.object(channel_read._http, "validate_public_url") as validate, \
                mock.patch.object(channel_read, "_jina",
                                  side_effect=AssertionError("browser denial must precede Jina")) as jina, \
                mock.patch.object(channel_read._agentreach, "reddit_read",
                                  side_effect=AssertionError("browser denial must precede Reddit")) as reddit, \
                mock.patch.object(channel_read._agentreach, "browser_available",
                                  side_effect=AssertionError("browser denial must precede probe")) as available, \
                mock.patch.object(channel_read._agentreach, "browser_extract",
                                  side_effect=AssertionError("browser denial must precede extraction")) as extract:
            text, method = channel_read.read_url(url, 1, 4000, browser=True)
        self.assertEqual((text, method), ("", "browser-not-authorized"))
        validate.assert_called_once_with(url)
        jina.assert_not_called()
        reddit.assert_not_called()
        available.assert_not_called()
        extract.assert_not_called()

    def test_agentreach_browser_adapter_is_denied_before_cli_lookup(self):
        url = "https://example.com/research"
        with mock.patch.dict(os.environ, {"ALETHEIA_BROWSER_CAPABILITY": ""}, clear=False), \
                mock.patch.object(_agentreach._config, "browser_authorized", return_value=False), \
                mock.patch.object(_agentreach, "find_cli",
                                  side_effect=AssertionError("must not inspect browser CLI")) as find_cli, \
                mock.patch.object(_http, "validate_public_url"):
            text, error = _agentreach.browser_extract(url, 1)
        self.assertEqual(text, "")
        self.assertIn("not authorized", error)
        find_cli.assert_not_called()


class TestPrivateLocalState(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX file-mode enforcement")
    def test_rejects_group_or_world_readable_connector_env_file(self):
        with tempfile.TemporaryDirectory() as config:
            env_file = os.path.join(config, ".env")
            with open(env_file, "w", encoding="utf-8") as fh:
                fh.write("BRAVE_API_KEY=must-not-load\n")
            os.chmod(env_file, 0o644)
            with mock.patch.dict(os.environ, {"ALETHEIA_CONFIG_DIR": config}, clear=True):
                _http.load_env()
                self.assertNotIn("BRAVE_API_KEY", os.environ)

    @unittest.skipUnless(os.name == "posix", "POSIX file-mode enforcement")
    def test_rejects_symlinked_connector_env_file(self):
        """A capability file must be a private regular file, not an attacker-swappable link."""
        with tempfile.TemporaryDirectory() as config:
            target = os.path.join(config, "private-target")
            with open(target, "w", encoding="utf-8") as fh:
                fh.write("BRAVE_API_KEY=must-not-load\n")
            os.chmod(target, 0o600)
            os.symlink(target, os.path.join(config, ".env"))
            with mock.patch.dict(os.environ, {"ALETHEIA_CONFIG_DIR": config}, clear=True):
                _http.load_env()
                self.assertNotIn("BRAVE_API_KEY", os.environ)

    @unittest.skipUnless(os.name == "posix", "POSIX file-mode enforcement")
    def test_runtime_import_makes_new_raw_read_artifacts_private_under_umask_022(self):
        """A copied runtime must not inherit a permissive host umask for raw research text."""
        with tempfile.TemporaryDirectory() as tmp:
            code = r'''
import json
import os
import stat
import sys

os.umask(0o022)
sys.path.insert(0, sys.argv[1])
import read

outdir = os.path.join(sys.argv[2], "raw-reads")
path = read._save("https://example.com/a", "sensitive raw evidence", outdir, "jina")
print(json.dumps({"dir": stat.S_IMODE(os.stat(outdir).st_mode),
                  "file": stat.S_IMODE(os.stat(path).st_mode)}))
'''
            env = dict(os.environ, HOME=os.path.join(tmp, "home"),
                       ALETHEIA_CONFIG_DIR=os.path.join(tmp, "config"), PYTHONNOUSERSITE="1")
            result = subprocess.run([sys.executable, "-c", code, CHANNEL_SCRIPTS, tmp],
                                    env=env, text=True, capture_output=True, check=True)
            modes = json.loads(result.stdout)
        self.assertEqual(modes, {"dir": 0o700, "file": 0o600})

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"),
                         "requires POSIX no-follow semantics")
    def test_arxiv_cooldown_ignores_and_replaces_a_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = os.path.join(tmp, "cache")
            target = os.path.join(tmp, "target")
            original = str(time.time() + 300)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(original)
            os.chmod(target, 0o600)
            with mock.patch.dict(os.environ, {"ALETHEIA_CACHE_DIR": cache}, clear=False):
                path = arxiv._cooldown_path()
                os.symlink(target, path)
                self.assertEqual(arxiv._cooling_down(), 0.0)
                arxiv._set_cooldown(60)
                self.assertFalse(os.path.islink(path))
                with open(target, encoding="utf-8") as fh:
                    self.assertEqual(fh.read(), original)
                self.assertGreater(arxiv._cooling_down(), 0.0)
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
