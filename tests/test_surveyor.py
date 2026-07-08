#!/usr/bin/env python3
"""Surveyor driver tests (stdlib unittest, hermetic — no network).

Locks in the deterministic behavior of the thoroughness-scaled surveyor: tier->params, channel-role
selection (incl. the biomed arXiv drop), work-level dedup, authority ranking, class-budgeted reads,
deepen convergence, independence math, and the verify layer's relevance-only contract.

Run: python3 -m unittest discover -s tests
"""
import argparse
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "surveyor", "scripts"))
import surveyor  # noqa: E402


def _ns(**kw):
    return argparse.Namespace(**kw)


def _make_run(tmp, tier="standard", topic="t"):
    run = os.path.join(tmp, "run")
    os.makedirs(os.path.join(run, "notes"))
    with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
        json.dump({"topic": topic, "params": surveyor.resolve_tier(tier),
                   "resolved_tier": tier, "channels": ["stub"]}, fh)
    return run


class TestTiersAndChannels(unittest.TestCase):
    def test_tier_resolution(self):
        self.assertEqual(surveyor.resolve_tier("deep")["fanout"], True)
        self.assertEqual(surveyor.resolve_tier("quick")["rounds"], 0)
        self.assertEqual(surveyor.resolve_tier("auto"), surveyor.resolve_tier("standard"))  # auto->standard
        self.assertEqual(surveyor.resolve_tier("bogus"), surveyor.resolve_tier("standard"))

    def test_biomed_drops_arxiv_and_covers_roles(self):
        chans = surveyor.pick_channels("intermittent fasting caloric restriction insulin metabolic", 4)
        self.assertNotIn("arxiv", chans)                      # off-domain for biomed
        self.assertIn("openalex", chans)                      # a primary survives
        self.assertTrue(any(c in surveyor.WEB for c in chans))

    def test_nonbiomed_keeps_arxiv_and_caps(self):
        chans = surveyor.pick_channels("multi-agent LLM systems architecture", 3)
        self.assertEqual(len(chans), 3)

    def test_authority(self):
        self.assertEqual(surveyor.authority("https://arxiv.org/abs/1"), 1.0)
        self.assertEqual(surveyor.authority("https://medium.com/x"), 0.2)


class TestRankDedup(unittest.TestCase):
    def test_work_key_collapses_variants(self):
        self.assertEqual(surveyor.work_key({"url": "https://arxiv.org/pdf/2509.13312"}),
                         surveyor.work_key({"url": "https://arxiv.org/abs/2509.13312v3"}))

    def test_select_reads_prioritizes_evidence(self):
        recs = ([{"url": "https://arxiv.org/abs/%d.00000" % i, "title": "paper %d" % i,
                  "_class": "evidence", "score": 0.5} for i in range(3)] +
                [{"url": "https://medium.com/%d" % i, "title": "blog %d" % i,
                  "_class": "lead_gen", "score": 0.9} for i in range(5)])
        sel = surveyor.select_reads(recs, 4)
        self.assertGreaterEqual(sum(1 for r in sel if r["_class"] == "evidence"), 2)  # >=60% of 4


class TestDeepen(unittest.TestCase):
    def test_convergence_and_cap(self):
        tmp = tempfile.mkdtemp(); run = _make_run(tmp, "standard")
        # no follow-ups -> STOP (exit 3)
        self.assertEqual(surveyor.cmd_deepen(_ns(run=run, angle="", learning=["l1"], followup=[])), 3)
        # a novel follow-up -> continue (exit 0)
        self.assertEqual(surveyor.cmd_deepen(_ns(run=run, angle="", learning=[], followup=["new gap q"])), 0)

    def test_round_cap_stops(self):
        tmp = tempfile.mkdtemp(); run = _make_run(tmp, "quick")  # rounds cap = 0
        self.assertEqual(surveyor.cmd_deepen(_ns(run=run, angle="", learning=[], followup=["q"])), 3)


class TestIndependence(unittest.TestCase):
    def test_echo_ratio(self):
        recs = [{"url": "https://a.com/1", "authors": [{"name": "A"}]},
                {"url": "https://a.com/1", "authors": [{"name": "A"}]},  # same voice -> echo
                {"url": "https://b.org/2", "authors": [{"name": "B"}]}]
        rep = surveyor.independence(recs)
        self.assertEqual(rep["n"], 3)
        self.assertGreater(rep["echo_ratio"], 0)


class TestVerify(unittest.TestCase):
    """verify layer certifies RELEVANCE only, never SUPPORT (can't see polarity/magnitude)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.run = _make_run(self.tmp)
        self._orig = surveyor.readmod.read_url
        surveyor.readmod.read_url = lambda *a, **k: ("", None)  # hermetic: no live fallback

    def tearDown(self):
        surveyor.readmod.read_url = self._orig

    def _note(self, url, text):
        with open(surveyor._note_path(self.run, url), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _run_verify(self, claim, url):
        cp = os.path.join(self.tmp, "claims.jsonl")
        with open(cp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"claim": claim, "url": url}) + "\n")
        surveyor.cmd_verify(_ns(run=self.run, claims=cp, out="", timeout=1))
        return json.loads(open(os.path.join(self.run, "verify.jsonl"), encoding="utf-8").read())

    def test_relevant_never_supported(self):
        self._note("u://a", "intermittent fasting is not superior; it does not double fat loss. " * 8)
        r = self._run_verify("intermittent fasting dramatically superior doubles fat loss", "u://a")
        self.assertEqual(r["verdict"], "relevant")
        self.assertTrue(r["needs_llm_check"])

    def test_off_topic_and_broken(self):
        self._note("u://b", "arctic terns migrate pole to pole across the globe each year. " * 8)
        self.assertEqual(self._run_verify("intermittent fasting fat loss caloric restriction", "u://b")["verdict"], "off_topic")
        self.assertEqual(self._run_verify("anything", "u://missing")["verdict"], "broken")


class TestScore(unittest.TestCase):
    def test_citation_accuracy_from_llm_verdicts(self):
        tmp = tempfile.mkdtemp(); run = _make_run(tmp, "standard")
        with open(os.path.join(run, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": "https://arxiv.org/abs/1", "_class": "evidence"}) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for v in ("supported", "supported", "contradicted", "unsupported"):
                fh.write(json.dumps({"claim": "c", "verdict": v}) + "\n")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            surveyor.cmd_score(_ns(run=run))
        d = json.loads(buf.getvalue())
        self.assertEqual(d["citation_accuracy"], 0.5)
        self.assertEqual(d["verdicts"]["contradicted"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
