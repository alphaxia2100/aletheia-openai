import importlib.util
import json
import os
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(ROOT, "scripts", "eval", "grade_accuracy_run.py")
spec = importlib.util.spec_from_file_location("grade_accuracy_run_test", PATH)
grader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grader)


class TestAccuracyRunGrader(unittest.TestCase):
    def test_complete_mechanism_trace_scores_100_without_claiming_truth(self):
        run = tempfile.mkdtemp()
        files = {
            "run.json": {"version": "aletheia-research-accuracy 0.6.0-accuracy.1",
                         "thoroughness": "accuracy",
                         "limits": {"max_seconds": 3600, "max_reads_per_round": 40,
                                    "max_read_attempts": 640},
                         "implementation": {"runtime_sha256": "a" * 64, "git_dirty": False}},
            "runtime-ledger.json": {"search_attempts": 2, "read_attempts_reserved": 3},
            "score.json": {"persisted": True},
        }
        for name, value in files.items():
            with open(os.path.join(run, name), "w", encoding="utf-8") as fh:
                json.dump(value, fh)
        with open(os.path.join(run, "runtime-events.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"elapsed_seconds": 12.5}) + "\n")
        with open(os.path.join(run, "brief.md"), "w", encoding="utf-8") as fh:
            fh.write("verified brief")

        original = grader._tool_json
        def fake(script, command, _run):
            if script == grader.REPORT:
                return {"citation_complete": True, "citation_accuracy": 1.0,
                        "citation_coverage": 1.0, "citation_denominator": 2,
                        "claim_scope_audit": {"valid": True},
                        "runtime": {"retrieval_passes": 2, "read_artifacts": 3}}
            if command == "audit":
                return {"claims": 2, "ready_for_synthesis": True,
                        "epistemically_complete": True}
            return {"evidence": {"E1": {"artifact_valid": True}},
                    "verdicts": {"E1": {"result": "verified"}}}
        grader._tool_json = fake
        try:
            result = grader.grade(run)
        finally:
            grader._tool_json = original
        self.assertEqual((result["structural_score"], result["structural_grade"]), (100, "A"))
        self.assertIn("real_world_factual_truth", result["not_measured"])
        self.assertIn("not answer truth", result["note"])


if __name__ == "__main__":
    unittest.main()
