#!/usr/bin/env python3
"""Hermetic release checks for the portable installer."""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTALL = os.path.join(ROOT, "scripts", "install.sh")
SANDBOX = os.path.join(ROOT, "containers", "run-sandbox.sh")


class TestPortableRelease(unittest.TestCase):
    def _env(self, root: str) -> dict:
        env = dict(os.environ)
        env["ALETHEIA_CODEX_SKILLS"] = os.path.join(root, "codex-skills")
        env["ALETHEIA_CONFIG_DIR"] = os.path.join(root, "config")
        return env

    def test_copy_install_is_self_contained_and_runnable(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(tmp)
            # This test exercises the candidate currently in the working tree.  Normal transfer
            # installs intentionally use committed HEAD bytes; --allow-dirty is the explicit
            # developer opt-in for smoke-testing uncommitted release work.
            subprocess.check_call(["bash", INSTALL, "--allow-dirty"], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL)
            skills = env["ALETHEIA_CODEX_SKILLS"]
            entry = os.path.join(skills, "aletheia-research")
            runtime = os.path.join(skills, ".aletheia-runtime")
            self.assertTrue(os.path.islink(entry))
            self.assertTrue(os.path.isfile(os.path.join(runtime, "skills", "channel-retrieval",
                                                        "scripts", "_http.py")))
            self.assertFalse(os.path.realpath(entry).startswith(os.path.realpath(ROOT) + os.sep))
            subprocess.check_call(
                [sys.executable, os.path.join(runtime, "tools", "preflight.py"),
                 "--runtime", runtime],
                cwd=tmp, env=env, stdout=subprocess.DEVNULL)
            out = subprocess.check_output(
                [sys.executable, os.path.join(entry, "scripts", "treestate.py"), "init",
                 "portable install smoke", "--thoroughness", "quick",
                 "--base", os.path.join(tmp, "runs", "aletheia-research")],
                cwd=tmp, env=env, text=True).strip()
            self.assertTrue(os.path.isfile(os.path.join(out, "run.json")))

    def test_preflight_rejects_unexpected_and_modified_runtime_files(self):
        """The copied-runtime manifest must catch both additions and byte-level drift."""
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(tmp)
            subprocess.check_call(["bash", INSTALL, "--allow-dirty"], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL)
            runtime = os.path.join(env["ALETHEIA_CODEX_SKILLS"], ".aletheia-runtime")
            preflight = os.path.join(runtime, "tools", "preflight.py")

            extra = os.path.join(runtime, "unexpected-runtime-file.txt")
            with open(extra, "w", encoding="utf-8") as fh:
                fh.write("must be detected")
            proc = subprocess.run([sys.executable, preflight, "--runtime", runtime, "--json"],
                                  text=True, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            report = json.loads(proc.stdout)
            self.assertIn("unexpected runtime file not in manifest: unexpected-runtime-file.txt",
                          report["errors"])

            os.unlink(extra)
            listed = os.path.join(runtime, "skills", "channel-retrieval", "scripts", "_http.py")
            with open(listed, "a", encoding="utf-8") as fh:
                fh.write("\n# test-only manifest mutation\n")
            proc = subprocess.run([sys.executable, preflight, "--runtime", runtime, "--json"],
                                  text=True, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            report = json.loads(proc.stdout)
            self.assertIn("manifest digest mismatch: skills/channel-retrieval/scripts/_http.py",
                          report["errors"])

    @unittest.skipUnless(shutil.which("git"), "requires Git to isolate a controlled dirty checkout")
    def test_copy_mode_uses_head_by_default_and_worktree_only_with_allow_dirty(self):
        """The transfer default is reproducible; an uncommitted runtime needs explicit consent."""
        with tempfile.TemporaryDirectory() as tmp:
            clone = os.path.join(tmp, "isolated-source")
            subprocess.check_call(["git", "clone", "--quiet", "--no-local", ROOT, clone])

            # Put the candidate installer (which has the HEAD/archive behavior) into an otherwise
            # clean clone, then make one tracked runtime file differ only in that clone.
            shutil.copy2(INSTALL, os.path.join(clone, "scripts", "install.sh"))
            source_file = os.path.join(clone, ".cursor", "skills", "channel-retrieval", "channels.json")
            with open(source_file, "rb") as fh:
                committed = fh.read()
            dirty = committed + b"\n"
            with open(source_file, "wb") as fh:
                fh.write(dirty)

            def install_to(destination: str, *args: str) -> bytes:
                env = dict(os.environ, HOME=os.path.join(tmp, "home"),
                           ALETHEIA_CURSOR_SKILLS=destination, PYTHONNOUSERSITE="1")
                subprocess.check_call(["bash", os.path.join(clone, "scripts", "install.sh"), "--cursor", *args],
                                      cwd=clone, env=env, stdout=subprocess.DEVNULL)
                path = os.path.join(destination, "channel-retrieval", "channels.json")
                with open(path, "rb") as fh:
                    return fh.read()

            self.assertEqual(install_to(os.path.join(tmp, "head-copy")), committed)
            self.assertEqual(install_to(os.path.join(tmp, "dirty-copy"), "--allow-dirty"), dirty)

    def test_installer_refuses_unmanaged_destination_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(tmp)
            target = os.path.join(env["ALETHEIA_CODEX_SKILLS"], "aletheia-research")
            os.makedirs(target)
            sentinel = os.path.join(target, "KEEP")
            with open(sentinel, "w", encoding="utf-8") as fh:
                fh.write("keep")
            proc = subprocess.run(["bash", INSTALL, "--allow-dirty"], cwd=ROOT, env=env,
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)
            with open(sentinel, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "keep")

    def test_dry_run_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(tmp)
            subprocess.check_call(["bash", INSTALL, "--dry-run"], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL)
            self.assertFalse(os.path.exists(env["ALETHEIA_CODEX_SKILLS"]))

    @unittest.skipUnless(os.name == "posix", "POSIX file-mode enforcement")
    def test_copy_install_remains_private_under_a_permissive_host_umask(self):
        """The installer must not turn its runtime/metadata directories into shared state."""
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(tmp)
            # Run through a hostile caller shell. The installer resets its own umask before it
            # creates the portable runtime, rather than assuming the harness did the right thing.
            subprocess.check_call(
                ["bash", "-c", 'umask 022; exec bash "$@"', "bash", INSTALL, "--allow-dirty"],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL)
            runtime = os.path.join(env["ALETHEIA_CODEX_SKILLS"], ".aletheia-runtime")
            marker = os.path.join(runtime, ".aletheia-install.json")
            manifest = os.path.join(runtime, "MANIFEST.sha256")
            self.assertEqual(stat.S_IMODE(os.stat(runtime).st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(os.stat(marker).st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(os.stat(manifest).st_mode), 0o600)

    @unittest.skipUnless(os.name == "posix" and os.geteuid() != 0 and shutil.which("true"),
                         "requires a non-root POSIX host and a harmless fake container engine")
    def test_sandbox_wrapper_makes_workdir_private_under_a_permissive_host_umask(self):
        """Validate the wrapper's host-side directory boundary without invoking Docker."""
        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "raw-runs")
            env = dict(os.environ, ALETHEIA_CONTAINER_ENGINE=shutil.which("true"))
            subprocess.check_call(
                ["bash", "-c", 'umask 022; exec bash "$@"', "bash", SANDBOX, "--work", work],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL)
            self.assertEqual(stat.S_IMODE(os.stat(work).st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()
