"""Synthetic receipt-contract tests; these are NOT live skill evaluations."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import py_compile
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_eval_results.py"
SPEC = importlib.util.spec_from_file_location("check_eval_results", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class EvaluationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / "run"
        self.base.mkdir()
        self.source = self.root / "dyz-med-test" / "SKILL.md"
        self.source.parent.mkdir()
        self.source.write_text("Synthetic unit-test source.\n", encoding="utf-8")
        self.fixture_path = self.root / "tests" / "fixtures" / "routing.json"
        self.fixture_path.parent.mkdir(parents=True)
        self.fixture = {"verification_status": "not_run", "cases": [{
            "id": "shared-id", "input": "Synthetic unit-test prompt, not a medical run.",
            "expected_skills": ["dyz-med-test"], "excluded_skills": ["other-skill"]}]}
        self.write_json(self.fixture_path, self.fixture)
        self.manifest = {"schema_version": 1, "captured_at": "2026-10-31T00:00:00Z",
                         "algorithm": "sha256", "skill_count": 1, "source_file_count": 1,
                         "sources": {"dyz-med-test/SKILL.md": checker.digest(self.source.read_bytes())},
                         "inputs": {"tests/fixtures/routing.json": checker.digest(self.fixture_path.read_bytes())}}
        self.manifest["source_sha256"] = checker.digest(checker.canonical(self.manifest["sources"]).encode())
        self.write_json(self.base / "source-manifest.json", self.manifest)
        probe = {"kind": "host_capability_probe", "run_id": "synthetic-unit-test",
                 "observations": ["Synthetic test fixture, not a live probe."]}
        self.write_json(self.base / "probe.json", probe)
        self.record = {"id": "routing/shared-id", "attempted": False, "submitted": False,
                       "executed": False, "routing_status": "blocked", "behavior_status": "not_run",
                       "raw_output": None, "invocation_evidence": None, "reviewer": None,
                       "reason": "Synthetic precondition blocker.", "blocker_ids": ["host"]}
        self.result = {"schema_version": 1, "run_id": "synthetic-unit-test", "recorded_on": "2026-10-31",
                       "source_manifest": "source-manifest.json", "source_sha256": self.manifest["source_sha256"],
                       "host": {"name": "synthetic-host", "version": None}, "model": {"id": None},
                       "environment": {"id": "unverified", "verified": False, "actual_skill_set": None},
                       "fixtures": ["tests/fixtures/routing.json"],
                       "blockers": {"host": {"reason": "Synthetic blocker.", "evidence": self.ref("probe.json")}},
                       "cases": [self.record]}
        self.path = self.base / "results.json"

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def ref(self, name):
        return {"path": name, "sha256": checker.digest((self.base / name).read_bytes())}

    def check(self, current=False):
        self.write_json(self.path, self.result)
        return checker.validate(self.path, self.root, current)

    def invalid(self, message):
        with self.assertRaisesRegex(checker.ReceiptError, message):
            self.check()

    def executed(self):
        """Create explicitly synthetic evidence only inside the disposable test tree."""
        self.result["host"]["version"] = "unit-test-only"
        self.result["model"]["id"] = "synthetic-model"
        self.result["environment"] = {"id": "library_only", "verified": True,
                                      "actual_skill_set": ["dyz-med-test"]}
        (self.base / "catalog.txt").write_text("Synthetic catalog dyz-med-test " + self.result["source_sha256"], encoding="utf-8")
        self.result["environment"]["evidence"] = self.ref("catalog.txt")
        prompt = self.fixture["cases"][0]["input"]
        output = "Synthetic test output, NOT an evaluated model answer."
        (self.base / "output.txt").write_text(output, encoding="utf-8")
        (self.base / "trace.txt").write_text(prompt + "\nSynthetic invocation dyz-med-test\n" + output, encoding="utf-8")
        self.invocation = {"kind": "host_execution", "origin": "host_export",
                           "source_locator": "synthetic-unit-test-only", "run_id": self.result["run_id"],
                           "case_id": self.record["id"], "source_sha256": self.result["source_sha256"],
                           "input_sha256": checker.digest(prompt.encode()),
                           "raw_output_sha256": self.ref("output.txt")["sha256"],
                           "host": self.result["host"], "model": self.result["model"],
                           "environment_id": "library_only", "submitted_prompt": prompt,
                           "trace_complete": True, "session_id": "synthetic-session",
                           "executed_at": "2026-10-31T00:00:00Z", "trace": self.ref("trace.txt"),
                           "actual_invoked_skills": ["dyz-med-test"]}
        self.record.update(attempted=True, submitted=True, executed=True, routing_status="pass",
                           behavior_status="pass", raw_output=self.ref("output.txt"), blocker_ids=[],
                           reviewer={"id": "synthetic-reviewer", "kind": "human", "evidence_reviewed": True})
        self.refresh_invocation()

    def refresh_invocation(self):
        self.write_json(self.base / "invocation.json", self.invocation)
        self.record["invocation_evidence"] = self.ref("invocation.json")

    def test_honest_blocker_is_valid_not_a_pass(self):
        report = self.check(current=True)
        self.assertEqual(report["counts"]["executed"], 0)
        self.assertFalse(report["required_dimensions_all_pass"])

    def test_not_run_is_valid(self):
        self.record.update(routing_status="not_run", blocker_ids=[])
        self.assertTrue(self.check()["receipt_valid"])

    def test_complete_synthetic_execution_contract(self):
        self.executed()
        self.assertTrue(self.check()["required_dimensions_all_pass"])

    def test_failure_still_requires_execution_evidence(self):
        self.record["routing_status"] = "fail"
        self.invalid("requires actual execution")

    def test_pass_without_execution_rejected(self):
        self.record["routing_status"] = "pass"
        self.invalid("requires actual execution")

    def test_pass_missing_raw_output(self):
        self.executed()
        self.record["raw_output"] = None
        self.invalid("evidence reference")

    def test_missing_evidence_file(self):
        self.executed()
        (self.base / "output.txt").unlink()
        self.invalid("output.txt")

    def test_tampered_raw_output(self):
        self.executed()
        (self.base / "output.txt").write_text("changed", encoding="utf-8")
        self.invalid("evidence hash mismatch")

    def test_static_validation_cannot_prove_execution(self):
        self.executed()
        self.invocation["kind"] = "syntax_check"
        self.refresh_invocation()
        self.invalid("not actual host execution")

    def test_wrong_case_or_source_or_model_binding(self):
        self.executed()
        original = copy.deepcopy(self.invocation)
        for field in ("case_id", "source_sha256", "input_sha256", "model", "environment_id", "run_id"):
            with self.subTest(field=field):
                self.invocation = copy.deepcopy(original)
                self.invocation[field] = "wrong"
                self.refresh_invocation()
                self.invalid("invocation binding mismatch")

    def test_answer_key_leak_in_prompt_rejected(self):
        self.executed()
        self.invocation["submitted_prompt"] += " expected_behavior: pass"
        self.refresh_invocation()
        self.invalid("submitted_prompt")

    def test_unrelated_trace_rejected(self):
        self.executed()
        (self.base / "trace.txt").write_text("unrelated static PASS dyz-med-test", encoding="utf-8")
        self.invocation["trace"] = self.ref("trace.txt")
        self.refresh_invocation()
        self.invalid("raw host trace")

    def test_missing_actual_skill_invocation_rejected(self):
        self.executed()
        self.invocation["actual_invoked_skills"] = []
        self.refresh_invocation()
        self.invalid("routing PASS conflicts")

    def test_empty_invocations_valid_when_none_expected(self):
        self.fixture["cases"][0]["expected_skills"] = []
        self.write_json(self.fixture_path, self.fixture)
        self.manifest["inputs"]["tests/fixtures/routing.json"] = checker.digest(self.fixture_path.read_bytes())
        self.write_json(self.base / "source-manifest.json", self.manifest)
        self.executed()
        self.invocation["actual_invoked_skills"] = []
        self.refresh_invocation()
        self.assertTrue(self.check()["receipt_valid"])

    def test_no_model_self_review(self):
        self.executed()
        self.record["reviewer"]["kind"] = "model"
        self.invalid("human evidence reviewer")

    def test_unverified_environment_cannot_pass(self):
        self.executed()
        self.result["environment"]["verified"] = False
        self.invalid("verified skill environment")

    def test_duplicate_case_rejected(self):
        self.result["cases"].append(copy.deepcopy(self.record))
        self.invalid("duplicate case identity")

    def test_same_local_id_across_suites_is_valid(self):
        other = self.fixture_path.with_name("another.json")
        self.write_json(other, self.fixture)
        self.manifest["inputs"]["tests/fixtures/another.json"] = checker.digest(other.read_bytes())
        self.write_json(self.base / "source-manifest.json", self.manifest)
        self.result["fixtures"].append("tests/fixtures/another.json")
        record = copy.deepcopy(self.record)
        record["id"] = "another/shared-id"
        self.result["cases"].append(record)
        self.assertEqual(self.check()["counts"]["cases"], 2)

    def test_bare_case_id_rejected(self):
        self.record["id"] = "shared-id"
        self.invalid("unknown namespaced case")

    def test_unknown_status_rejected(self):
        self.record["behavior_status"] = "PASS"
        self.invalid("unknown behavior status")

    def test_wrong_boolean_type_rejected(self):
        self.record["attempted"] = "false"
        self.invalid("must be boolean")

    def test_blocked_needs_probe_evidence(self):
        self.record["blocker_ids"] = []
        self.invalid("blocked case needs evidence")

    def test_old_probe_cannot_explain_current_blocker(self):
        self.write_json(self.base / "probe.json", {"kind": "host_capability_probe", "run_id": "old-run"})
        self.result["blockers"]["host"]["evidence"] = self.ref("probe.json")
        self.invalid("unrelated to this run")

    def test_frozen_fixture_change_rejected(self):
        self.fixture_path.write_text("{}", encoding="utf-8")
        self.invalid("frozen input changed")

    def test_source_map_tampering_rejected(self):
        self.manifest["sources"]["dyz-med-test/SKILL.md"] = "0" * 64
        self.write_json(self.base / "source-manifest.json", self.manifest)
        self.invalid("manifest source fingerprint mismatch")

    def test_future_source_change_does_not_rewrite_history(self):
        self.source.write_text("new version", encoding="utf-8")
        self.assertTrue(self.check()["receipt_valid"])
        with self.assertRaisesRegex(checker.ReceiptError, "current sources differ"):
            self.check(current=True)

    def test_added_source_detected_by_current_check(self):
        (self.source.parent / "new.txt").write_text("added", encoding="utf-8")
        with self.assertRaisesRegex(checker.ReceiptError, "current sources differ"):
            self.check(current=True)

    def test_unsafe_paths_rejected(self):
        for path in ("../probe.json", "C:/secret", "/tmp/secret", "..\\secret", "./probe.json"):
            with self.subTest(path=path):
                self.result["blockers"]["host"]["evidence"]["path"] = path
                self.invalid("unsafe relative path")

    def test_summary_cannot_invent_passes(self):
        self.result["summary"] = {"executed": 60}
        self.invalid("claimed summary differs")

    def test_duplicate_json_keys_rejected(self):
        self.path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(checker.ReceiptError, "duplicate JSON key"):
            checker.validate(self.path, self.root)

    def test_invalid_json_and_nonobject_rejected(self):
        for value in ("{", "[]", '{"x":NaN}'):
            with self.subTest(value=value):
                self.path.write_text(value, encoding="utf-8")
                with self.assertRaises(checker.ReceiptError):
                    checker.validate(self.path, self.root)

    def test_cli_codes_and_read_only_inputs(self):
        self.write_json(self.path, self.result)
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([str(self.path), "--root", str(self.root)]), 0)
            self.assertEqual(checker.main([str(self.path), "--root", str(self.root), "--require-pass"]), 3)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.record["routing_status"] = "pass"
        self.write_json(self.path, self.result)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main([str(self.path), "--root", str(self.root)]), 1)

    def test_python_syntax_compiles_in_temporary_directory(self):
        for index, path in enumerate((SCRIPT, Path(__file__))):
            py_compile.compile(str(path), cfile=str(self.root / f"{index}.pyc"), doraise=True)


if __name__ == "__main__":
    unittest.main()
