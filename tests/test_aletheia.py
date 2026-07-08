#!/usr/bin/env python3
"""Aletheia correctness tests (stdlib unittest, no deps).

Run: python3 -m unittest discover -s tests   (or: python3 tests/test_aletheia.py)

These lock in the fixes for the independence-math bugs found in review — the
differentiator must never silently return wrong numbers again.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "provenance-audit", "scripts"))
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "defensibility-judge", "scripts"))
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "deep-aletheia", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import provenance_graph as pg  # noqa: E402
import dedupe  # noqa: E402
import rubric  # noqa: E402
import verify  # noqa: E402  (deep-aletheia citation gate)
import score_run  # noqa: E402  (deep-aletheia run scorer)


def audit_one(sources, support):
    return pg.audit(sources, [{"id": "c", "text": "t", "support": support}])["claims"][0]


class TestIndependence(unittest.TestCase):
    def test_echo_via_derives_from_collapses_to_one(self):
        srcs = [
            {"id": "s1", "url": "https://a.com/x", "authors": [{"name": "A"}], "derives_from": ["s5"], "primary": False},
            {"id": "s5", "url": "https://anthropic.com/p", "authors": [{"name": "Anthropic"}], "primary": True},
        ]
        r = audit_one(srcs, ["s1", "s5"])
        self.assertEqual(r["independent_sources"], 1)
        self.assertIn("single_primary_origin", r["flags"])

    def test_distinct_publisher_papers_stay_independent(self):
        # P0: two different PLOS papers (different DOIs) must NOT collapse to 1
        srcs = [
            {"id": "p1", "url": "https://journals.plos.org/plosone/article?id=1",
             "doi": "10.1371/journal.pone.0000001", "authors": [{"name": "Team A"}], "primary": True},
            {"id": "p2", "url": "https://journals.plos.org/plosone/article?id=2",
             "doi": "10.1371/journal.pone.0000002", "authors": [{"name": "Team B"}], "primary": True},
        ]
        r = audit_one(srcs, ["p1", "p2"])
        self.assertEqual(r["independent_sources"], 2)

    def test_same_author_same_domain_merges(self):
        srcs = [
            {"id": "a", "url": "https://blog.example/1", "authors": [{"name": "Sam"}], "primary": False},
            {"id": "b", "url": "https://blog.example/2", "authors": [{"name": "Sam"}], "primary": False},
        ]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)

    def test_near_duplicate_syndication_merges_without_annotation(self):
        # P1: same wire story on two domains, NO derives_from -> 1 independent
        text = ("the central bank raised interest rates by fifty basis points citing persistent "
                "inflation across the economy and signaled further tightening ahead next quarter")
        srcs = [
            {"id": "w1", "url": "https://site1.example/a", "title": "Bank raises rates",
             "snippet": text, "authors": [{"name": "AP"}], "primary": False},
            {"id": "w2", "url": "https://site2.example/b", "title": "Bank raises rates",
             "snippet": text, "authors": [{"name": "Wire desk"}], "primary": False},
        ]
        self.assertEqual(audit_one(srcs, ["w1", "w2"])["independent_sources"], 1)

    def test_id_collision_kept_distinct(self):
        # P0: two sources lacking id+url must remain 2 nodes, not overwrite
        srcs = [{"authors": [{"name": "X"}], "snippet": "alpha"},
                {"authors": [{"name": "Y"}], "snippet": "beta"}]
        self.assertEqual(pg.audit(srcs, [])["summary"]["sources"], 2)

    def test_discovery_monoculture_not_fired_on_single_source(self):
        srcs = [{"id": "a", "url": "https://x.example/1", "index_of_origin": "brave", "primary": True}]
        self.assertNotIn("discovery_monoculture", audit_one(srcs, ["a"])["flags"])


class TestCitations(unittest.TestCase):
    def test_shared_institution_is_not_echo(self):
        # P0: 4 distinct authors all at "MIT" -> 4 independent groups (not an echo)
        payload = {"target": {"authors": [{"name": "T"}]},
                   "citers": [{"authors": [{"name": n, "affiliation": "MIT"}]} for n in "ABCD"]}
        res = pg.citation_independence(payload)
        self.assertEqual(res["independent_citer_groups"], 4)
        self.assertNotIn("NOT independent", res["verdict"])

    def test_shared_author_collapses(self):
        payload = {"target": {"authors": [{"name": "T"}]},
                   "citers": [{"authors": [{"name": "Alice"}]}, {"authors": [{"name": "Alice"}]}]}
        self.assertEqual(pg.citation_independence(payload)["independent_citer_groups"], 1)

    def test_self_citation_counted(self):
        payload = {"target": {"authors": [{"name": "Alice"}]},
                   "citers": [{"authors": [{"name": "Alice"}]}, {"authors": [{"name": "Bob"}]}]}
        self.assertEqual(pg.citation_independence(payload)["self_citations"], 1)


class TestCycles(unittest.TestCase):
    def test_doi_cycle_detected(self):
        srcs = [
            {"id": "x", "doi": "10.1/x", "url": "https://doi.org/10.1/x", "refs": ["10.1/y"], "primary": True},
            {"id": "y", "doi": "10.1/y", "url": "https://doi.org/10.1/y", "refs": ["10.1/x"], "primary": True},
        ]
        rep = pg.audit(srcs, [{"id": "c", "support": ["x", "y"]}])
        self.assertTrue(rep["summary"]["global_cycles"])

    def test_large_chain_no_recursion_error(self):
        # P1: iterative DFS must handle 5000 nodes without RecursionError
        edges = {str(i): {str(i + 1)} for i in range(5000)}
        edges["5000"] = set()
        self.assertEqual(pg._find_cycles(edges), [])


class TestDedupe(unittest.TestCase):
    def test_canonical_url_strips_tracking(self):
        self.assertEqual(dedupe.canonical_url("https://www.Ex.com/a/?utm_source=x&id=5#f"),
                         "https://ex.com/a?id=5")

    def test_registrable_domain_multilabel(self):
        self.assertEqual(dedupe.registrable_domain("https://www.example.co.uk/x"), "example.co.uk")

    def test_voice_key_doi_distinguishes_works(self):
        a = dedupe.voice_key({"doi": "10.1/a", "url": "https://p.org/1"})
        b = dedupe.voice_key({"doi": "10.1/b", "url": "https://p.org/2"})
        self.assertNotEqual(a, b)


class TestRubric(unittest.TestCase):
    def test_bare_claim_not_defensible(self):
        r = rubric.judge({"claim": "X is best", "falsifier": ""})
        self.assertEqual(r["verdict"], "not yet defensible")

    def test_full_belief_defensible(self):
        belief = {
            "claim": "c",
            "falsifier": "a controlled same-budget comparison showing no difference would sink it",
            "falsifier_search": {"performed": True, "found": "searched, found dissent of a different task type"},
            "evidence": {"independent_sources": 3, "primary": True},
            "steelman": {"opposing_view": "the opposite camp says Y", "why_unconvinced": "their case is a different regime"},
        }
        self.assertTrue(rubric.judge(belief)["verdict"].startswith("defensible"))


class TestVerifyGate(unittest.TestCase):
    """Deep Aletheia's deterministic verify layer certifies RELEVANCE only, never SUPPORT —
    lexical overlap can't see polarity/magnitude, so entailment is the LLM verifier's job.
    Regression for the dogfooded bug: a false "IF doubles fat loss" claim was scored 'supported'
    by lexical overlap alone; the fix is that this layer can NEVER emit 'supported'."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # kill the live-read fallback so tests are hermetic (broken == no readable source)
        self._orig = verify.readmod.read_url
        verify.readmod.read_url = lambda *a, **k: ("", None)

    def tearDown(self):
        verify.readmod.read_url = self._orig

    def _note(self, url, text):
        import hashlib
        h = hashlib.sha1(url.encode()).hexdigest()[:10]
        with open(os.path.join(self.tmp, h + ".md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _verdict(self, claim, url):
        return verify.verify_claim(claim, [url], None, self.tmp, 1.0)

    def test_never_emits_supported_even_when_source_says_the_opposite(self):
        claim = "Intermittent fasting is dramatically superior and doubles fat loss."
        # on-topic + heavy word overlap, but the OPPOSITE polarity — lexical can't tell
        self._note("u://a", "Intermittent fasting is not superior; it does not double fat loss. " * 8)
        r = self._verdict(claim, "u://a")
        self.assertEqual(r["verdict"], "relevant")        # relevant, NOT supported
        self.assertNotEqual(r["verdict"], "supported")
        self.assertTrue(r["needs_llm_check"])             # entailment always deferred to the LLM

    def test_off_topic_when_no_overlap(self):
        self._note("u://b", "The migratory patterns of arctic terns span pole to pole. " * 8)
        r = self._verdict("Intermittent fasting beats caloric restriction for fat loss", "u://b")
        self.assertEqual(r["verdict"], "off_topic")

    def test_broken_when_source_unreadable(self):
        r = self._verdict("anything at all here", "u://missing")  # no note + no live read
        self.assertEqual(r["verdict"], "broken")
        self.assertFalse(r["link_works"])

    def test_run_summary_has_no_supported_bucket(self):
        self._note("u://c", "matched calorie intermittent fasting weight loss advantage comparison " * 8)
        out = verify.run([{"claim": "matched calorie intermittent fasting weight loss advantage",
                           "url": "u://c"}], None, self.tmp, 1.0)
        self.assertIn("on_topic_rate", out)
        self.assertEqual(set(out["counts"]), {"relevant", "off_topic", "broken"})


class TestScoreRunVerdicts(unittest.TestCase):
    """score_run turns the LLM verdicts into citation_accuracy = supported/total, and exposes the
    full breakdown so a caught false claim (contradicted/unsupported) is visible in the score."""

    def _run_with_verify(self, verdicts, cfg=None):
        run = tempfile.mkdtemp()
        with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg or {"topic": "t", "version": "test"}, fh)
        os.makedirs(os.path.join(run, "tree"))
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for v in verdicts:
                fh.write(json.dumps({"claim": "c", "verdict": v}) + "\n")
        return run

    def test_citation_accuracy_and_breakdown(self):
        run = self._run_with_verify(["supported", "supported", "contradicted", "unsupported"])
        s = score_run.score(run)
        self.assertEqual(s["citation_accuracy"], 0.5)
        self.assertEqual(s["verdicts"], {"supported": 2, "contradicted": 1,
                                         "unsupported": 1, "awaiting_llm_check": 0})

    def test_citation_accuracy_is_none_before_llm_pass(self):
        run = self._run_with_verify(["relevant", "relevant", "relevant"])
        s = score_run.score(run)
        self.assertIsNone(s["citation_accuracy"])          # not yet Fact-Checked
        self.assertEqual(s["verdicts"]["awaiting_llm_check"], 3)
        self.assertEqual(s["on_topic_rate"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
