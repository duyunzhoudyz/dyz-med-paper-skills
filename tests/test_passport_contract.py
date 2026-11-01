"""Synthetic local contract tests; no scientific decisions or real human approvals."""

import builtins
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dyz-med-passport/scripts/validate_passport.py"
SPEC = importlib.util.spec_from_file_location("passport_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
FIXTURE = ROOT / "tests/fixtures/project-state.json"


class PassportContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for name, content in fixture["files"].items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
        encoded = json.dumps(fixture["passport"])
        for name in fixture["files"]:
            encoded = encoded.replace("__SHA256__:" + name, self.hash(name))
        self.document = json.loads(encoded)
        self.path = self.root / "passport.json"

    def hash(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def check(self, expected_code=0):
        self.path.write_text(json.dumps(self.document), encoding="utf-8")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = validator.validate(self.path)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "Validator must not write or rewrite any input")
        self.assertEqual(validator.exit_code(report), expected_code, report)
        return report

    def assert_error(self, report, code):
        self.assertIn(code, [entry["code"] for entry in report["errors"]])

    def test_valid_and_unchanged_inputs(self):
        first = self.check()
        second = self.check()
        self.assertEqual(first, second)
        self.assertEqual(first["checks"][0]["freshness"], "current")
        self.assertEqual(first["approvals"][0]["provenance"], "recorded_not_authenticated")

    def test_result_bytes_change_invalidates_check_and_approval(self):
        (self.root / "paper/results.txt").write_bytes(b"synthetic N=235\n")
        report = self.check(1)
        self.assert_error(report, "HASH_MISMATCH")
        self.assertEqual(report["checks"][0]["freshness"], "stale")
        self.assertEqual(report["approvals"][0]["freshness"], "stale")
        self.assertEqual(report["checks"][0]["domain_result"]["value"], "consistent")

    def test_registered_new_version_leaves_old_check_stale(self):
        (self.root / "paper/results.txt").write_bytes(b"synthetic N=235\n")
        artifact = self.document["artifacts"][0]
        artifact.update(version="v2", sha256=self.hash("paper/results.txt"))
        self.assertEqual(self.check(3)["checks"][0]["freshness"], "stale")

    def test_version_label_change_alone_is_conservatively_stale(self):
        self.document["artifacts"][0]["version"] = "v2"
        self.assertEqual(self.check(3)["checks"][0]["freshness"], "stale")

    def test_formatting_change_has_no_automatic_semantic_exception(self):
        (self.root / "paper/results.txt").write_bytes(b"synthetic N = 236\n")
        self.document["checks"][0]["formatting_only"] = True
        self.assertEqual(self.check(1)["checks"][0]["freshness"], "stale")

    def test_unrelated_unregistered_file_change_does_not_invalidate(self):
        before = self.check()
        (self.root / "paper/unrelated.txt").write_bytes(b"new unrelated notes\n")
        self.assertEqual(self.check(), before)

    def test_unrelated_registered_input_does_not_invalidate_other_check(self):
        self.document["artifacts"].append({
            "id": "notes", "path": "paper/unrelated.txt", "version": "v1",
            "sha256": self.hash("paper/unrelated.txt"),
        })
        (self.root / "paper/unrelated.txt").write_bytes(b"new unrelated notes\n")
        report = self.check(1)
        self.assertEqual(report["checks"][0]["freshness"], "current")
        self.assertEqual(report["approvals"][0]["freshness"], "current")

    def test_each_member_of_multi_input_set_is_bound(self):
        self.document["artifacts"].append({
            "id": "report-values", "path": "paper/unrelated.txt", "version": "v1",
            "sha256": self.hash("paper/unrelated.txt"),
        })
        self.document["checks"][0]["inputs"].append({
            "artifact_id": "report-values", "version": "v1",
            "sha256": self.hash("paper/unrelated.txt"),
        })
        self.check()
        (self.root / "paper/unrelated.txt").write_bytes(b"changed report values\n")
        report = self.check(1)
        self.assertEqual(report["checks"][0]["freshness"], "stale")
        self.assertEqual(report["approvals"][0]["freshness"], "current")

    def test_legacy_records_are_not_upgraded_and_extensions_preserved(self):
        self.document["schema_version"] = "1.0"
        del self.document["artifacts"][0]["sha256"]
        self.document["checks"] = [{"id": "old-audit", "status": "pass"}]
        self.document["human_approvals"] = {"local_review": "confirmed"}
        expected = copy.deepcopy(self.document)
        report = self.check(3)
        self.assertEqual(report["checks"][0]["freshness"], "unverified")
        self.assertEqual(report["approvals"][0]["freshness"], "unverified")
        self.assertEqual(self.document, expected)
        self.assertEqual(json.loads(self.path.read_text()), expected)
        self.document["schema_version"] = "1.1"
        self.assertEqual(self.check(3)["checks"][0]["freshness"], "unverified")

    def test_missing_input_or_report_is_located(self):
        for name in ("paper/results.txt", "paper/check.json"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.unlink()
                report = self.check(1)
                self.assert_error(report, "FILE_UNREADABLE")
                self.assertEqual(report["checks"][0]["freshness"], "unverified")
                path.write_bytes(original)

    def test_report_content_change_is_stale(self):
        (self.root / "paper/check.json").write_bytes(b"changed check\n")
        self.assertEqual(self.check(1)["checks"][0]["freshness"], "stale")

    def test_duplicate_ids_rejected(self):
        for name in ("artifacts", "checks"):
            with self.subTest(collection=name):
                self.document[name].append(copy.deepcopy(self.document[name][0]))
                self.assert_error(self.check(1), "DUPLICATE_ID")
                self.document[name].pop()

    def test_duplicate_or_missing_inputs_rejected(self):
        inputs = self.document["checks"][0]["inputs"]
        inputs.append(copy.deepcopy(inputs[0]))
        self.assert_error(self.check(1), "DUPLICATE_INPUT")
        inputs.clear()
        self.assert_error(self.check(1), "MISSING_BINDING")

    def test_unknown_core_states_including_wrong_types_are_rejected(self):
        for key, invalid in (("execution_status", "pass"), ("execution_status", []),
                             ("applicability", "yes"), ("applicability", {})):
            with self.subTest(key=key, value=invalid):
                original = self.document["checks"][0][key]
                self.document["checks"][0][key] = invalid
                self.assert_error(self.check(1), "UNKNOWN_STATE")
                self.document["checks"][0][key] = original
        self.document["schema_version"] = "99.0"
        self.assert_error(self.check(1), "UNKNOWN_SCHEMA")

    def test_scientific_rejection_does_not_equal_execution_failure(self):
        self.document["checks"][0]["domain_result"] = {
            "namespace": "mock_review", "value": "REJECT",
        }
        report = self.check()
        self.assertEqual(report["checks"][0]["execution_status"], "completed")
        self.assertEqual(report["checks"][0]["domain_result"]["value"], "REJECT")

    def test_not_applicable_is_separate_from_freshness(self):
        record = self.document["checks"][0]
        record.update(applicability="not_applicable", applicability_reason="Synthetic scope")
        self.assertEqual(self.check()["checks"][0]["applicability"], "not_applicable")
        del record["applicability_reason"]
        self.assert_error(self.check(1), "MISSING_REASON")

    def test_unexecuted_failed_and_blocked_checks_are_not_current(self):
        record = self.document["checks"][0]
        for state in ("not_run", "blocked", "failed"):
            with self.subTest(state=state):
                record.update(execution_status=state, domain_result=None,
                              reason="Synthetic inability to execute")
                self.assertEqual(self.check(3)["checks"][0]["freshness"], "unverified")
        record["domain_result"] = {"namespace": "test", "value": "pass"}
        self.assert_error(self.check(1), "UNEXECUTED_RESULT")

    def test_human_approval_cannot_be_boolean_or_sourceless(self):
        original = copy.deepcopy(self.document["human_approvals"]["local_review"])
        for invalid in (True, {"state": "confirmed"}):
            self.document["human_approvals"]["local_review"] = invalid
            report = self.check(1)
            self.assertEqual(report["approvals"][0]["freshness"], "unverified")
        self.document["human_approvals"]["local_review"] = original
        original["source"]["kind"] = "model"
        self.assert_error(self.check(1), "MISSING_PROVENANCE")

    def test_approval_evidence_and_time_must_be_traceable(self):
        approval = self.document["human_approvals"]["local_review"]
        for field in ("actor_id", "statement", "locator"):
            saved = approval["source"].pop(field)
            self.assert_error(self.check(1), "MISSING_PROVENANCE")
            approval["source"][field] = saved
        approval["confirmed_at"] = "2026-10-31"
        self.assert_error(self.check(1), "INVALID_DATE")
        approval["confirmed_at"] = "2026-10-31T12:10:00+00:00"
        (self.root / "paper/approval.txt").write_bytes(b"different synthetic approval")
        self.assertEqual(self.check(1)["approvals"][0]["freshness"], "stale")

    def test_unconfirmed_approval_never_becomes_current(self):
        self.document["human_approvals"]["local_review"] = {
            "state": "not_confirmed", "targets": [],
        }
        self.assertEqual(self.check(3)["approvals"][0]["freshness"], "unverified")

    def test_issue_closure_requires_current_check_and_evidence(self):
        self.document["open_items"] = [{
            "id": "OPEN-001", "severity": "major", "status": "verified_closed",
            "verification_check_id": "result-check-001",
            "evidence": {"path": "paper/check.json", "sha256": self.hash("paper/check.json")},
        }]
        self.check()
        self.document["checks"][0]["applicability"] = "not_applicable"
        self.document["checks"][0]["applicability_reason"] = "Synthetic reason"
        self.assert_error(self.check(1), "UNVERIFIED_CLOSURE")
        self.document["open_items"][0]["status"] = "replied"
        self.assert_error(self.check(1), "UNKNOWN_STATE")

    def test_root_resolution_and_rejected_paths(self):
        self.check()
        nested = self.root / "paper/passport.json"
        nested.write_bytes(self.path.read_bytes())
        self.assertEqual(validator.exit_code(validator.validate(nested, self.root)), 0)
        self.assertEqual(validator.exit_code(validator.validate(nested)), 1)
        for invalid in ("../outside.txt", "/tmp/x", "C:/x", "paper\\results.txt",
                        "paper//results.txt", "./paper/results.txt", "https://example.org/x"):
            with self.subTest(path=invalid):
                self.document["artifacts"][0]["path"] = invalid
                self.assert_error(self.check(1), "INVALID_PATH")

    def test_duplicate_mapping_keys_and_malformed_document(self):
        for content in ('{"schema_version":"1.1","schema_version":"1.0"}', '[]', '{'):
            self.path.write_text(content, encoding="utf-8")
            self.assertEqual(validator.exit_code(validator.validate(self.path)), 1)

    def test_yaml_dependency_missing_is_explicit_blocker(self):
        path = self.root / "passport.yaml"
        path.write_text("schema_version: '1.1'\n", encoding="utf-8")
        real_import = builtins.__import__

        def without_yaml(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("synthetic missing dependency")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=without_yaml):
            report = validator.validate(path)
        self.assertEqual(validator.exit_code(report), 4)
        self.assertEqual(report["status"], "blocked")

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML not installed")
    def test_yaml_parity_and_template_examples_parse(self):
        import yaml

        self.check()
        path = self.root / "passport.yaml"
        path.write_text(yaml.safe_dump(self.document), encoding="utf-8")
        self.assertEqual(validator.exit_code(validator.validate(path)), 0)
        for name in ("templates/project-passport.template.yaml",
                     "examples/虚构项目状态文件样例.yaml"):
            data = validator.load_document(ROOT / "dyz-med-passport" / name)
            self.assertIsInstance(data, dict)
        path.write_text("schema_version: '1.1'\nschema_version: '1.0'\n", encoding="utf-8")
        self.assertEqual(validator.exit_code(validator.validate(path)), 1)

    def test_cli_codes_and_json_output(self):
        self.check()
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(validator.main([str(self.path)]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "valid")
        self.document["human_approvals"]["pending"] = {"state": "not_confirmed"}
        self.check(3)
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["freshness"], "unverified")
        invalid = subprocess.run([sys.executable, "-B", str(SCRIPT)],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(invalid.returncode, 2)

    def test_python_syntax_compiles_only_in_temporary_directory(self):
        for index, path in enumerate((SCRIPT, Path(__file__))):
            py_compile.compile(str(path), cfile=str(self.root / f"{index}.pyc"), doraise=True)


if __name__ == "__main__":
    unittest.main()
