import hashlib
import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import evaluator_v2  # noqa: E402
import persist_judges  # noqa: E402


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class ScopeIdentityGateTests(unittest.TestCase):
    def _run(self, verdicts):
        run = tempfile.mkdtemp()
        os.makedirs(os.path.join(run, "tree"))
        files = {
            "run.json": {"topic": "scope-test", "version": "aletheia-research 0.5.0"},
            "claims.jsonl": [
                {"claim": "A", "url": "https://example.test/a"},
                {"claim": "B", "url": "https://example.test/b"},
            ],
            "verify.jsonl": verdicts,
        }
        with open(os.path.join(run, "brief.md"), "w", encoding="utf-8") as fh:
            fh.write("Claim A. Claim B.\n")
        for name, value in files.items():
            path = os.path.join(run, name)
            with open(path, "w", encoding="utf-8") as fh:
                if isinstance(value, list):
                    for row in value:
                        fh.write(json.dumps(row) + "\n")
                else:
                    json.dump(value, fh)
        audit = {
            "status": "complete",
            "auditor": "external-scope-auditor",
            "claim_count": 2,
            "brief_sha256": _sha(os.path.join(run, "brief.md")),
            "claims_sha256": _sha(os.path.join(run, "claims.jsonl")),
            "verify_sha256": _sha(os.path.join(run, "verify.jsonl")),
        }
        with open(os.path.join(run, "claim_audit.json"), "w", encoding="utf-8") as fh:
            json.dump(audit, fh)
        return run

    def test_release_rejects_hash_correct_claim_verdict_cardinality_mismatch(self):
        run = self._run([
            {"claim": "A", "url": "https://example.test/a", "verdict": "supported"},
        ])
        score = evaluator_v2.score_run(run)
        self.assertFalse(score["scope_gate_passed"])
        self.assertIsNone(score["citation_accuracy"])
        self.assertIn("claim_verdict_cardinality_mismatch", score["claim_scope_audit"]["reasons"])

    def test_release_rejects_equal_cardinality_but_wrong_claim_identity(self):
        run = self._run([
            {"claim": "A", "url": "https://example.test/a", "verdict": "supported"},
            {"claim": "C", "url": "https://example.test/c", "verdict": "supported"},
        ])
        score = evaluator_v2.score_run(run)
        self.assertFalse(score["scope_gate_passed"])
        self.assertIn("claim_verdict_identity_mismatch", score["claim_scope_audit"]["reasons"])


class JudgeProvenanceGateTests(unittest.TestCase):
    def _fixture(self, alter_candidate=False):
        tmp = tempfile.mkdtemp()
        canonical = os.path.join(tmp, "canonical")
        blind = os.path.join(tmp, "blind-inputs", "topic-1")
        os.makedirs(canonical)
        os.makedirs(blind)
        paths = {}
        for system, content in (("candidate", "candidate canonical"),
                                ("baseline", "baseline canonical")):
            paths[system] = os.path.join(canonical, system + ".md")
            with open(paths[system], "w", encoding="utf-8") as fh:
                fh.write(content)
        candidate_blind = os.path.join(blind, "input-1.md")
        baseline_blind = os.path.join(blind, "input-2.md")
        with open(candidate_blind, "w", encoding="utf-8") as fh:
            fh.write("altered" if alter_candidate else "candidate canonical")
        with open(baseline_blind, "w", encoding="utf-8") as fh:
            fh.write("baseline canonical")
        matrix = {
            "schema_version": 1,
            "topics": [{
                "topic": "topic-1",
                "candidate": {"version": "candidate-v2", "brief_path": paths["candidate"],
                              "brief_sha256": _sha(paths["candidate"])},
                "baseline": {"version": "baseline-v1", "brief_path": paths["baseline"],
                             "brief_sha256": _sha(paths["baseline"])},
            }],
        }
        matrix_path = os.path.join(tmp, "expected-matrix.json")
        with open(matrix_path, "w", encoding="utf-8") as fh:
            json.dump(matrix, fh, sort_keys=True)
        rows = [
            {"topic": "topic-1", "pair_id": "p", "judge_id": "j1", "judge_model": "m",
             "order": {"A": "candidate", "B": "baseline"}, "winner_shown": "A",
             "A_path": candidate_blind, "B_path": baseline_blind,
             "prompt": "Read %s and %s" % (candidate_blind, baseline_blind)},
            {"topic": "topic-1", "pair_id": "p", "judge_id": "j2", "judge_model": "m",
             "order": {"A": "baseline", "B": "candidate"}, "winner_shown": "B",
             "A_path": baseline_blind, "B_path": candidate_blind,
             "prompt": "Read %s and %s" % (baseline_blind, candidate_blind)},
        ]
        payload = {"judge_artifacts": rows,
                   "anchor": [{"topic": "topic-1", "A": candidate_blind,
                               "B": baseline_blind, "_cand_is": "A"}]}
        return tmp, payload, matrix_path

    def test_release_fails_closed_without_pinned_expected_matrix(self):
        tmp, payload, _ = self._fixture()
        manifest = persist_judges.persist(payload, os.path.join(tmp, "out"), release_mode=True)
        self.assertFalse(manifest["release_gate_passed"])
        self.assertIn("expected_matrix_not_trusted", manifest["release_invalid_reasons"])

    def test_release_binds_every_blind_input_to_canonical_brief_hash(self):
        tmp, payload, matrix = self._fixture(alter_candidate=True)
        manifest = persist_judges.persist(
            payload, os.path.join(tmp, "out"), release_mode=True,
            expected_matrix=matrix, expected_matrix_sha256=_sha(matrix))
        self.assertFalse(manifest["release_gate_passed"])
        self.assertFalse(manifest["canonical_brief_bindings_valid"])
        self.assertEqual(manifest["expected_topic_count"], 1)

    def test_release_accepts_exact_topic_version_and_canonical_hash_matrix(self):
        tmp, payload, matrix = self._fixture()
        manifest = persist_judges.persist(
            payload, os.path.join(tmp, "out"), release_mode=True,
            expected_matrix=matrix, expected_matrix_sha256=_sha(matrix))
        self.assertTrue(manifest["release_gate_passed"])
        self.assertTrue(manifest["canonical_brief_bindings_valid"])
        self.assertTrue(manifest["expected_topic_matrix_complete"])
        self.assertEqual(manifest["expected_versions"], {
            "topic-1": {"candidate": "candidate-v2", "baseline": "baseline-v1"}})


if __name__ == "__main__":
    unittest.main()
