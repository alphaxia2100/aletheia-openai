#!/usr/bin/env python3
"""Regression and control suite for the experimental semantic read-identity gate."""
import json
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")
CH = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts")
PROV = os.path.join(ROOT, ".cursor", "skills", "provenance-audit", "scripts")
for path in (PROV, CH, AR):
    sys.path.insert(0, path)

import read_identity  # noqa: E402


def load_ar(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(AR, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


treestate = load_ar("read_identity_ar_treestate", "treestate.py")
investigate = load_ar("read_identity_ar_investigate", "investigate.py")
investigate.treestate = treestate
investigate.read_identity = read_identity
report = load_ar("read_identity_ar_report", "report.py")
report.treestate = treestate


FIXTURE = os.path.join(HERE, "fixtures", "read_identity_cases.json")
PAD = (" This portable fixture retains the observed identity front matter while adding neutral "
       "article prose so it crosses the production length-only success threshold. Evidence methods "
       "results limitations and discussion are represented without adding another title or identifier.")


def fixture_cases():
    with open(FIXTURE, encoding="utf-8") as fh:
        cases = json.load(fh)
    for case in cases:
        case = dict(case)
        case["body"] = case["front"] + (PAD * 12 if case.get("pad") else "")
        yield case


class TestReadIdentityGate(unittest.TestCase):
    def test_portable_reproductions_and_false_positive_controls(self):
        for case in fixture_cases():
            with self.subTest(case=case["id"]):
                result = read_identity.assess_read(
                    case["record"], case["body"], case.get("resolved_url", ""),
                    case.get("method", "jina"), False)
                self.assertEqual(result["identity_state"], case["expected_identity"])
                self.assertEqual(result["read_ok"], case["expected_read_ok"])
                if case.get("expected_content"):
                    self.assertEqual(result["content_state"], case["expected_content"])

    def test_observed_wrong_bodies_passed_the_production_length_predicate(self):
        cases = list(fixture_cases())[:2]
        for case in cases:
            self.assertGreaterEqual(len(case["body"].strip()), 1500)
            self.assertFalse(read_identity.assess_read(case["record"], case["body"])["read_ok"])

    def test_expected_identifier_in_reference_list_does_not_override_wrong_front_identity(self):
        record = {"url": "https://doi.org/10.5555/12345678", "doi": "10.5555/12345678",
                  "title": "Expected Controlled Study of Retrieval Quality"}
        body = ("Title: Unrelated Clinical Guidance on Heterogeneity\n"
                "DOI: 10.5555/99990000\n" + PAD * 12 +
                "\n## References\nPrior work https://doi.org/10.5555/12345678")
        result = read_identity.assess_read(record, body)
        self.assertEqual(result["identity_state"], "mismatch")
        self.assertFalse(result["read_ok"])

    def test_truncation_is_orthogonal_to_verified_identity(self):
        record = {"url": "https://doi.org/10.5555/12345678", "doi": "10.5555/12345678",
                  "title": "Adaptive Evidence Retrieval for Complex Research Questions"}
        body = "Title: Adaptive Evidence Retrieval for Complex Research Questions\nDOI: 10.5555/12345678\n" + PAD * 12
        result = read_identity.assess_read(record, body, truncated=True)
        self.assertEqual(result["identity_state"], "verified_identifier")
        self.assertEqual(result["content_state"], "truncated")
        self.assertTrue(result["read_ok"])

    def test_mismatch_is_persisted_but_not_counted_as_success(self):
        run = treestate.init_run("identity integration", base=tempfile.mkdtemp(),
                                 budget=8, unit=4, max_depth=1, max_children=2, max_nodes=4,
                                 verbosity="agent")
        node = os.path.join(run, "tree", "root")
        case = next(fixture_cases())
        record = dict(case["record"], _class="evidence", _relnorm=1.0, _authority=1.0,
                      score=1.0)
        ctx = {"query": "identity", "chans": ["stub"], "per": {"stub": {"n": 1}},
               "round_no": 1, "reads": 1, "recs": [record], "uniq": [record],
               "ranked": [record], "read_pool": [record], "prev_read": 0}
        with mock.patch.object(investigate, "_read_source",
                               return_value=(case["body"], "opencli-browser", record["url"])):
            result = investigate._execute_reads(node, ctx, [record], timeout=1,
                                                selection_mode="agent")
        self.assertEqual(result["reads_ok"], 0)
        self.assertEqual(result["telemetry"]["identity_mismatches"], 1)
        self.assertTrue(os.path.isfile(os.path.join(node, record["_read_file"])))
        self.assertFalse(record["_read_ok"])
        self.assertTrue(record["_content_ok"])
        self.assertEqual(record["_identity_state"], "mismatch")
        with open(os.path.join(node, "telemetry.jsonl"), encoding="utf-8") as fh:
            events = [json.loads(line) for line in fh if line.strip()]
        attempt = next(event for event in events if event.get("event") == "read_attempt")
        self.assertEqual(attempt["identity_state"], "mismatch")
        self.assertEqual(attempt["content_sha256"], record["_read_sha256"])

    def test_retry_preserves_the_first_wrong_body(self):
        node = tempfile.mkdtemp()
        url = "https://doi.org/10.5555/12345678"
        first = investigate._save_read(node, url, "wrong body", "browser", False, url,
                                       "mismatch", "complete")
        second = investigate._save_read(node, url, "correct body", "jina", False, url,
                                        "verified_identifier", "complete")
        self.assertNotEqual(first, second)
        with open(first, encoding="utf-8") as fh:
            self.assertIn("wrong body", fh.read())
        with open(second, encoding="utf-8") as fh:
            self.assertIn("correct body", fh.read())

    def test_failed_identity_artifact_does_not_block_retry(self):
        node = tempfile.mkdtemp()
        os.makedirs(os.path.join(node, "notes"))
        record = {"url": "https://doi.org/10.5555/12345678",
                  "doi": "10.5555/12345678", "title": "Target Study"}
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(record, _read_ok=False, _identity_state="mismatch")) + "\n")
        self.assertFalse(investigate._successful_read_exists(node, record))
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(record, _read_ok=True,
                                     _identity_state="verified_identifier")) + "\n")
        self.assertTrue(investigate._successful_read_exists(node, record))

    def test_report_aggregates_typed_read_states(self):
        run = treestate.init_run("typed telemetry", base=tempfile.mkdtemp(), budget=8, unit=4)
        node = os.path.join(run, "tree", "root")
        event = {"event": "investigation_round", "selection_mode": "agent", "round": 1,
                 "read_attempts": 3, "reads_ok": 1, "content_reads_ok": 2,
                 "read_failures": 2, "identity_mismatches": 1, "identity_unverified": 1,
                 "identity_states": {"verified_title": 1, "mismatch": 1,
                                     "unverified_identity": 1},
                 "content_states": {"complete": 2, "blocked": 1}}
        with open(os.path.join(node, "telemetry.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
        runtime = report._runtime_telemetry(run)
        self.assertEqual(runtime["identity_mismatches"], 1)
        self.assertEqual(runtime["identity_unverified"], 1)
        self.assertEqual(runtime["content_reads_ok"], 2)
        self.assertEqual(runtime["identity_states"]["verified_title"], 1)
        self.assertEqual(runtime["content_states"]["blocked"], 1)


if __name__ == "__main__":
    unittest.main()
