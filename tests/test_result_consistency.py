"""合成只读对账测试；所有输出均在临时目录，不运行模型。"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dyz-med-results/scripts/check_result_consistency.py"
FIXTURE = ROOT / "tests/fixtures/result-consistency.json"
SPEC = importlib.util.spec_from_file_location("result_checker", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ResultConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture_bytes = FIXTURE.read_bytes()
        fixture = json.loads(self.fixture_bytes)
        self.results = fixture["results"]
        self.reported = fixture["reported"]
        self.source = fixture["source_text"]
        self.manuscript = fixture["manuscript_text"]
        self.row = self.results["results"][0]
        self.claim = self.reported["reported_values"][0]
        self.artifacts = {key: {"_nonempty": True} for key in
                          ("analysis-results", "reported-values", "external-output", "manuscript")}

    def tearDown(self):
        self.assertEqual(FIXTURE.read_bytes(), self.fixture_bytes)

    def compare(self):
        before = copy.deepcopy((self.results, self.reported, self.artifacts))
        report = checker.reconcile(self.results, self.reported, self.artifacts)
        self.assertEqual(before, (self.results, self.reported, self.artifacts))
        return report

    def stage(self, root, name="analysis-results.json"):
        payloads = {"analysis-results": (name, json.dumps(self.results)),
                    "reported-values": ("reported-values.json", json.dumps(self.reported)),
                    "external-output": ("output.txt", self.source),
                    "manuscript": ("manuscript.txt", self.manuscript)}
        entries = []
        for key, (path, content) in payloads.items():
            data = content.encode("utf-8")
            (root / path).write_bytes(data)
            entries.append({"id": key, "path": path, "version": "v1", "sha256": sha(data)})
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"artifacts": entries}), encoding="utf-8")
        return manifest

    def cli(self, root, manifest, check_id="synthetic-run-001"):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(manifest), "--root", str(root),
             "--report", "reports/consistency.json", "--record", "reports/check.json",
             "--check-id", check_id], capture_output=True, text=True, encoding="utf-8")

    def test_external_results_and_valid_rounding(self):
        report = self.compare()
        self.assertEqual(report["conclusion"], "consistent")
        self.assertEqual(len(report["matched_values"]), 6)
        self.assertEqual(report["unverified"], [])

    def test_adjusted_p_and_unadjusted_ci_are_legitimate(self):
        self.assertLess(float(self.row["ci"]["upper"]), 1)
        self.assertGreater(float(self.row["p"]["value"]), .05)
        self.assertEqual(self.compare()["conclusion"], "consistent")

    def test_236_vs_235_is_discrepant(self):
        self.claim["values"]["denominator.value"]["value"] = 235
        report = self.compare()
        self.assertEqual(report["conclusion"], "discrepant")
        self.assertIn("denominator.value", report["differences"][0]["location"])
        self.assertIn("Table 2", report["reported_items"][0]["locator"]["location"])

    def test_integer_rounding_is_not_accepted(self):
        self.claim["values"]["denominator.value"]["precision"] = {"places": 0, "mode": "half_up"}
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_counts_require_json_integer(self):
        for value in (236.0, "236", True):
            with self.subTest(value=value):
                self.claim["values"]["denominator.value"]["value"] = value
                self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_reference_group_reversal(self):
        self.claim["context"]["groups"] = {"comparison": "control", "reference": "treatment"}
        self.assertEqual(self.compare()["conclusion"], "discrepant")

    def test_units_population_timepoint_outcome_and_scale(self):
        for field, value in (("unit", "percent"), ("population", "PP"),
                             ("timepoint", "12 months"), ("outcome", "OS"),
                             ("effect_scale", "OR"), ("effect_scale", "RR")):
            with self.subTest(field=field, value=value):
                original = self.claim["context"][field]
                self.claim["context"][field] = value
                self.assertEqual(self.compare()["conclusion"], "discrepant")
                self.claim["context"][field] = original

    def test_denominator_unit_mismatch(self):
        self.claim["context"]["denominator"]["unit"] = "person-years"
        self.assertEqual(self.compare()["conclusion"], "discrepant")

    def test_p_adjustment_mismatch(self):
        self.claim["context"]["p"]["adjustment"] = "unadjusted"
        self.assertEqual(self.compare()["conclusion"], "discrepant")

    def test_rounding_requires_explicit_precision(self):
        del self.claim["values"]["estimate"]["precision"]
        self.assertEqual(self.compare()["conclusion"], "discrepant")

    def test_rounding_does_not_hide_difference(self):
        self.claim["values"]["estimate"]["value"] = "0.83"
        self.assertEqual(self.compare()["conclusion"], "discrepant")

    def test_decimal_ties_and_precision(self):
        self.assertTrue(checker.compare_value("0.825", {"value": "0.83", "precision":
                                                     {"places": 2, "mode": "half_up"}}, False))
        self.assertTrue(checker.compare_value("0.825", {"value": "0.82", "precision":
                                                     {"places": 2, "mode": "half_even"}}, False))
        self.assertFalse(checker.compare_value("0.824999", {"value": "0.83", "precision":
                                                         {"places": 2, "mode": "half_up"}}, False))
        with self.assertRaises(ValueError):
            checker.compare_value("0.8246", {"value": "0.824", "precision":
                                            {"places": 2, "mode": "half_up"}}, False)

    def test_arbitrary_tolerance_is_rejected(self):
        self.claim["values"]["estimate"]["tolerance"] = 100
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_missing_provenance_and_empty_source(self):
        original = self.row.pop("source")
        self.assertEqual(self.compare()["conclusion"], "unverified")
        self.row["source"] = original
        self.artifacts["external-output"]["_nonempty"] = False
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_unexecuted_and_unknown_execution(self):
        for state in ("not_run", "blocked", "failed", "unknown", None):
            with self.subTest(state=state):
                self.row["execution_status"] = state
                self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_missing_locator_or_context(self):
        self.claim.pop("locator")
        self.assertEqual(self.compare()["conclusion"], "unverified")
        self.claim.pop("context")
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_unknown_fields_and_empty_checklist(self):
        self.claim["values"]["unknown_statistic"] = {"value": 1}
        self.assertEqual(self.compare()["conclusion"], "unverified")
        self.reported["reported_values"] = []
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_unknown_analysis_id(self):
        self.claim["analysis_id"] = "other-model"
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_duplicate_ids_and_unknown_schema_are_rejected(self):
        self.results["results"].append(copy.deepcopy(self.row))
        with self.assertRaises(ValueError):
            self.compare()
        self.results["results"].pop()
        self.reported["reported_values"].append(copy.deepcopy(self.claim))
        with self.assertRaises(ValueError):
            self.compare()
        self.reported["reported_values"].pop()
        self.results["schema_version"] = "9"
        with self.assertRaises(ValueError):
            self.compare()

    def test_applicability_allows_descriptive_count(self):
        self.row.update({"effect_scale": "count", "estimate": 236, "unit": "participants",
                         "groups": None, "ci": None, "denominator": None,
                         "not_applicable": {"groups": "single cohort", "ci": "descriptive count",
                                            "denominator": "cohort total"}})
        self.row.pop("p")
        self.claim["context"].update({key: self.row[key] for key in checker.CONTEXT})
        self.claim["values"] = {"estimate": {"value": 236}}
        self.assertEqual(self.compare()["conclusion"], "consistent")
        self.row["not_applicable"] = {}
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_continuous_denominator(self):
        self.row["denominator"] = {"value": "125.726", "kind": "continuous", "unit": "person-years"}
        self.claim["context"]["denominator"] = {"kind": "continuous", "unit": "person-years"}
        self.claim["values"]["denominator.value"] = {"value": "125.73", "precision":
                                                    {"places": 2, "mode": "half_up"}}
        self.assertEqual(self.compare()["conclusion"], "consistent")

    def test_nonfinite_bool_and_invalid_ci_are_unverified(self):
        for value in ("NaN", "Infinity", True, "1e9999"):
            with self.subTest(value=value):
                self.row["estimate"] = value
                self.assertEqual(self.compare()["conclusion"], "unverified")
        self.row["estimate"] = "0.8246"
        self.row["ci"]["lower"] = "2"
        self.assertTrue(self.compare()["unverified"])

    def test_difference_and_unverified_are_both_preserved(self):
        self.claim["values"]["events"]["value"] = 50
        self.row.pop("source")
        report = self.compare()
        self.assertEqual(report["conclusion"], "discrepant")
        self.assertTrue(report["unverified"])

    def test_unreported_analysis_coverage_is_not_full_validation(self):
        other = copy.deepcopy(self.row)
        other["analysis_id"] = "not-reported"
        other["execution_status"] = "not_run"
        self.results["results"].append(other)
        report = self.compare()
        self.assertEqual(report["conclusion"], "consistent")
        self.assertEqual(report["coverage"]["unreported_analyses"], ["not-reported"])

    def test_cli_alias_bindings_outputs_and_immutable_inputs(self):
        for name in ("analysis-results.json", "structured_results.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = self.stage(root, name)
                before = {path: path.read_bytes() for path in root.iterdir()}
                process = self.cli(root, manifest)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertEqual(before, {path: path.read_bytes() for path in before})
                report_path = root / "reports/consistency.json"
                report = json.loads(report_path.read_bytes())
                record = json.loads((root / "reports/check.json").read_bytes())
                check = record["checks"][0]
                self.assertEqual(check["report"]["sha256"], sha(report_path.read_bytes()))
                self.assertEqual(check["execution_status"], "completed")
                self.assertEqual(check["domain_result"]["value"], "consistent")
                self.assertEqual(check["inputs"], report["inputs"])
                self.assertEqual(len(check["inputs"]), 4)
                self.assertEqual(record["artifacts"][0]["path"], name)
                self.assertEqual(report["manifest_sha256"], sha(before[manifest]))

    def test_cli_exit_codes_discrepant_unverified_and_error(self):
        for expected in (1, 3, 2):
            with self.subTest(code=expected), tempfile.TemporaryDirectory() as temp:
                if expected == 1:
                    self.claim["values"]["denominator.value"]["value"] = 235
                else:
                    self.claim["values"]["denominator.value"]["value"] = 236
                    self.row["execution_status"] = "not_run"
                root = Path(temp)
                manifest = self.stage(root)
                if expected == 2:
                    (root / "output.txt").write_text("changed", encoding="utf-8")
                process = self.cli(root, manifest)
                self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
                if expected != 2:
                    record = json.loads((root / "reports/check.json").read_bytes())
                    self.assertEqual(record["checks"][0]["execution_status"], "completed")
                else:
                    self.assertFalse((root / "reports/check.json").exists())

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            self.assertEqual(self.cli(root, manifest).returncode, 0)
            report = root / "reports/consistency.json"
            before = report.read_bytes()
            self.assertEqual(self.cli(root, manifest).returncode, 2)
            self.assertEqual(report.read_bytes(), before)

    def test_cli_rejects_bad_json_and_duplicate_manifest_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            data = json.loads(manifest.read_bytes())
            data["artifacts"].append(data["artifacts"][0])
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(self.cli(root, manifest).returncode, 2)
            manifest.write_text('{"artifacts": [], "artifacts": []}', encoding="utf-8")
            self.assertEqual(self.cli(root, manifest).returncode, 2)

    def test_yaml_is_not_silently_parsed_or_renamed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root, "structured_results.yaml")
            before = (root / "structured_results.yaml").read_bytes()
            self.assertEqual(self.cli(root, manifest).returncode, 2)
            self.assertEqual((root / "structured_results.yaml").read_bytes(), before)

    def test_root_restrictions_and_output_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("../out.json", "/out.json", "C:/out.json", "a\\b", "a//b", "./x", "a/../x"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    checker.resolve_path(root, name)
            manifest = self.stage(root)
            with self.assertRaises(ValueError):
                checker.run(manifest, root, "manifest.json", "new.json", "run")
            with self.assertRaises(ValueError):
                checker.run(manifest, root, "new.json", "new.json", "run")

    def test_inflight_input_change_cannot_generate_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            original = checker.reconcile

            def mutate(*args):
                report = original(*args)
                (root / "output.txt").write_text("changed mid-run", encoding="utf-8")
                return report

            with patch.object(checker, "reconcile", side_effect=mutate):
                with self.assertRaisesRegex(ValueError, "运行中输入改变"):
                    checker.run(manifest, root, "report.json", "check.json", "run")
            self.assertFalse((root / "check.json").exists())

    def test_explicit_normalized_role_keeps_original_yaml_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root, "normalized.json")
            data = json.loads(manifest.read_bytes())
            data["artifacts"][0]["id"] = "analysis-results-json"
            original = b"results: synthetic external YAML export\n"
            (root / "structured_results.yaml").write_bytes(original)
            data["artifacts"].append({"id": "analysis-results", "version": "v1",
                                      "path": "structured_results.yaml", "sha256": sha(original)})
            data["roles"] = {"results": "analysis-results-json", "reported": "reported-values"}
            manifest.write_text(json.dumps(data), encoding="utf-8")
            process = self.cli(root, manifest)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            record = json.loads((root / "reports/check.json").read_bytes())
            self.assertEqual(len(record["checks"][0]["inputs"]), 5)
            self.assertEqual((root / "structured_results.yaml").read_bytes(), original)

    def test_json_decimal_text_is_not_rounded_by_binary_float(self):
        result = checker.load_json(b'{"value": 0.824999999999999999999999999}')
        self.assertEqual(result["value"], "0.824999999999999999999999999")
        self.assertTrue(checker.compare_value(result["value"], {"value": "0.82", "precision":
                                                              {"places": 2, "mode": "half_up"}}, False))

    def test_malformed_core_values_are_unverified_not_crashes(self):
        self.row["source"]["artifact_id"] = []
        self.claim["locator"]["artifact_id"] = {}
        self.claim["values"]["estimate"]["precision"]["mode"] = []
        report = self.compare()
        self.assertEqual(report["conclusion"], "unverified")
        self.assertGreaterEqual(len(report["unverified"]), 3)

    def test_missing_optional_ci_and_p_are_valid(self):
        self.row.pop("p")
        self.row["ci"] = None
        self.row["not_applicable"] = {"ci": "descriptive point estimate only"}
        for field in ("ci.lower", "ci.upper", "p.value"):
            self.claim["values"].pop(field)
        self.assertEqual(self.compare()["conclusion"], "consistent")
        self.row.pop("denominator")
        self.assertEqual(self.compare()["conclusion"], "unverified")

    def test_cli_argument_error(self):
        process = subprocess.run([sys.executable, "-B", str(SCRIPT)], capture_output=True)
        self.assertEqual(process.returncode, 2)


if __name__ == "__main__":
    unittest.main()
