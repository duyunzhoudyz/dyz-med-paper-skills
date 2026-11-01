"""Offline tests with synthetic normalized rows and temporary output files only."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dyz-med-screening-pipeline/scripts/compute_prisma_counts.py"
FIXTURE = ROOT / "tests/fixtures/prisma-records/cases.json"
SPEC = importlib.util.spec_from_file_location("prisma_counter", SCRIPT)
COUNTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COUNTER)
FIXTURES = json.loads(FIXTURE.read_text(encoding="utf-8"))


def case_data(case):
    data = copy.deepcopy(FIXTURES["base"])
    for change in case["changes"]:
        target = data
        for key in change["path"][:-1]:
            target = target[key]
        target[change["path"][-1]] = copy.deepcopy(change["value"])
    return data


class CountingTests(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(FIXTURES["base"])

    def compute(self):
        return COUNTER.compute(self.data, "screening-data")

    def test_fixture_cases(self):
        for case in FIXTURES["cases"]:
            with self.subTest(case=case["id"]):
                data = case_data(case)
                before = copy.deepcopy(data)
                result = COUNTER.compute(data, "screening-data")
                self.assertEqual(data, before)
                self.assertEqual(result["status"], case["status"])
                self.assertEqual(result["finalizable"], case["status"] == "reconciled")
                for key, count in case.get("counts", {}).items():
                    self.assertEqual(result["counts"][key]["count"], count)
                if "issue_code" in case:
                    self.assertIn(case["issue_code"], {i["code"] for i in result["errors"] + result["unresolved"]})
                if case["status"] == "invalid":
                    self.assertEqual(result["counts"], {})

    def test_one_study_two_reports_and_distinct_units(self):
        result = self.compute()
        self.assertEqual(result["counts"]["included.studies"]["member_ids"], ["s1"])
        self.assertEqual(result["counts"]["included.reports"]["member_ids"], ["p1", "p2"])
        self.assertEqual(result["counts"]["database_register.records_advanced"]["count"], 1)
        self.assertEqual(result["counts"]["database_register.reports_sought"]["count"], 2)
        for equation in result["equations"]:
            self.assertEqual(equation["difference"], 0)
            for key in equation["right"]:
                self.assertEqual(result["counts"][key]["unit"], equation["unit"])

    def test_many_records_to_one_report_preserves_edges(self):
        second = dict(self.data["records"][0], record_id="r2", source_record_id="raw2")
        self.data["records"].append(second)
        self.data["record_reports"].append({"record_id": "r2", "report_id": "p1", "basis": "synthetic-link"})
        self.data["reports"] = self.data["reports"][:1]
        self.data["record_reports"] = [r for r in self.data["record_reports"] if r["report_id"] == "p1"]
        self.data["report_studies"] = self.data["report_studies"][:1]
        result = self.compute()
        self.assertEqual(result["status"], "reconciled")
        self.assertEqual(result["counts"]["database_register.records_advanced"]["count"], 2)
        self.assertEqual(result["counts"]["database_register.reports_sought"]["count"], 1)
        self.assertEqual(len(result["associations"]["record_reports"]), 2)

    def test_one_report_can_describe_multiple_studies(self):
        self.data["studies"].append({"study_id": "s2", "basis": "synthetic-second-study"})
        self.data["report_studies"].append({"report_id": "p1", "study_id": "s2", "basis": "synthetic-two-studies-in-report"})
        result = self.compute()
        self.assertEqual(result["counts"]["included.studies"]["member_ids"], ["s1", "s2"])
        self.assertEqual(len(result["associations"]["report_studies"]), 3)

    def test_mixed_sources_share_study_without_double_counting(self):
        self.data["reports"][1]["branch"] = "other_direct"
        self.data["record_reports"] = self.data["record_reports"][:1]
        result = self.compute()
        self.assertEqual(result["status"], "reconciled")
        self.assertEqual(result["counts"]["included.studies"]["count"], 1)
        self.assertEqual(result["counts"]["other_direct.reports_sought"]["count"], 1)
        self.assertNotIn("other_direct.records_screened", result["counts"])

    def test_removed_records_are_not_automatically_decided(self):
        for pre in ("duplicate", "automation", "other"):
            row = dict(self.data["records"][0], record_id=f"r-{pre}", source_record_id=f"raw-{pre}", pre_screen_decision=pre, decision="not_applicable")
            if pre == "duplicate":
                row["duplicate_of"] = "r1"
            self.data["records"].append(row)
        result = self.compute()
        self.assertEqual(result["status"], "reconciled")
        self.assertEqual(result["counts"]["database_register.records_identified"]["count"], 4)
        self.assertEqual(result["counts"]["database_register.records_screened"]["count"], 1)
        self.assertTrue(all(e["difference"] == 0 for e in result["equations"]))

    def test_not_retrieved_never_enters_reason_groups(self):
        case = next(c for c in FIXTURES["cases"] if c["id"] == "not-retrieved-is-not-excluded")
        result = COUNTER.compute(case_data(case), "data")
        for reasons in result["exclusions_by_reason"].values():
            for entry in reasons.values():
                self.assertNotIn("p2", entry["member_ids"])

    def test_reason_totals_match_excluded_reports(self):
        case = next(c for c in FIXTURES["cases"] if c["id"] == "full-text-exclusion")
        result = COUNTER.compute(case_data(case), "data")
        for branch, reasons in result["exclusions_by_reason"].items():
            self.assertEqual(sum(x["count"] for x in reasons.values()), result["counts"][f"{branch}.reports_excluded"]["count"])

    def test_members_have_input_locators_and_filters(self):
        result = self.compute()
        tables = {"record": "records", "report": "reports", "study": "studies"}
        for entry in result["counts"].values():
            self.assertTrue(entry["filter"])
            self.assertEqual(entry["count"], len(entry["member_ids"]))
            for member in entry["member_ids"]:
                origin = result["source_rows"][tables[entry["unit"]]][member]
                self.assertEqual(origin["artifact_id"], "screening-data")
                self.assertTrue(origin["json_pointer"].startswith("/"))

    def test_duplicate_id_and_edge_rejected_for_all_tables(self):
        for table in COUNTER.TABLE_KEYS:
            with self.subTest(table=table):
                data = copy.deepcopy(self.data)
                data[table].append(copy.deepcopy(data[table][0]))
                result = COUNTER.compute(data, "data")
                self.assertEqual(result["status"], "invalid")
                self.assertIn("duplicate_id", {i["code"] for i in result["errors"]})

    def test_unknown_statuses_and_bad_reason_rejected(self):
        mutations = (("records", "pre_screen_decision", "auto"),
                     ("records", "source_type", "unknown"),
                     ("reports", "retrieval_status", "downloaded"),
                     ("reports", "branch", "unknown"),
                     ("reports", "decision", "maybe"),
                     ("reports", "primary_exclusion_reason", "wrong_design"))
        for table, field, value in mutations:
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[table][0][field] = value
                self.assertEqual(COUNTER.compute(data, "data")["status"], "invalid")

    def test_missing_schema_fields_are_not_synthesized(self):
        for field in ("records", "reports", "studies", "record_reports", "report_studies", "protocol_version", "exclusion_reasons"):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                del data[field]
                self.assertEqual(COUNTER.compute(data, "data")["status"], "invalid")

    def test_expected_counts_report_difference_not_repair(self):
        self.data["expected_counts"] = {"included.studies": 2}
        result = self.compute()
        self.assertEqual(result["differences"], [{"metric": "included.studies", "unit": "study", "expected": 2, "computed": 1, "difference": -1}])
        self.assertEqual(result["status"], "discrepancy")

    def test_unknown_expected_metric_is_error(self):
        self.data["expected_counts"] = {"fake_total": 0}
        self.assertEqual(self.compute()["status"], "invalid")

    def test_pending_screening_not_counted_as_screened(self):
        self.data["records"][0]["decision"] = "pending"
        result = self.compute()
        self.assertEqual(result["counts"]["database_register.records_screened"]["count"], 0)
        self.assertEqual(result["counts"]["database_register.records_awaiting_screening"]["count"], 1)
        self.assertEqual(result["count_scope"], "observed_only_not_final")

    def test_empty_explicit_dataset_is_zero_not_missing(self):
        for table in COUNTER.TABLE_KEYS:
            self.data[table] = []
        result = self.compute()
        self.assertEqual(result["status"], "reconciled")
        self.assertTrue(all(c["count"] == 0 for c in result["counts"].values()))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.script = self.root / "counter.py"
        shutil.copyfile(SCRIPT, self.script)
        self.data = copy.deepcopy(FIXTURES["base"])
        self.prepare()

    def prepare(self):
        (self.root / "rows.json").write_bytes(COUNTER.encoded(self.data))
        self.manifest = {
            "schema_version": "1.0", "id": "count-input-manifest", "version": "v1",
            "dataset_artifact_id": "normalized-screening", "tool_artifact_id": "prisma-tool",
            "artifacts": [
                {"id": "normalized-screening", "version": "v1", "path": "rows.json", "sha256": hashlib.sha256((self.root / "rows.json").read_bytes()).hexdigest()},
                {"id": "prisma-tool", "version": "v1", "path": "counter.py", "sha256": hashlib.sha256(self.script.read_bytes()).hexdigest()},
            ],
        }
        self.save_manifest()

    def save_manifest(self):
        (self.root / "manifest.json").write_bytes(COUNTER.encoded(self.manifest))

    def cli(self, suffix="1", extra=()):
        return subprocess.run(
            [sys.executable, "-B", str(self.script), "manifest.json", "--root", str(self.root),
             "--output", f"counts-{suffix}.json", "--check-output", f"check-{suffix}.json",
             "--run-id", f"prisma-run-{suffix}", *extra],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )

    def load(self, name):
        return json.loads((self.root / name).read_text(encoding="utf-8"))

    def test_repeatability_and_all_input_hashes_unchanged(self):
        names = ("counter.py", "rows.json", "manifest.json")
        before = {n: hashlib.sha256((self.root / n).read_bytes()).hexdigest() for n in names}
        first, second = self.cli("1"), self.cli("2")
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual((self.root / "counts-1.json").read_bytes(), (self.root / "counts-2.json").read_bytes())
        self.assertEqual(before, {n: hashlib.sha256((self.root / n).read_bytes()).hexdigest() for n in names})
        report = self.load("counts-1.json")
        self.assertEqual(report["counts"]["included.studies"]["count"], 1)
        self.assertEqual(report["counts"]["included.reports"]["count"], 2)

    def test_contract_receipt_binds_manifest_data_script_and_report(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stdout)
        receipt = self.load("check-1.json")
        check = receipt["checks"][0]
        self.assertEqual(check["scope"]["domain"], "prisma_counts")
        self.assertEqual(check["execution_status"], "completed")
        self.assertEqual(check["domain_result"], {"namespace": "prisma_counts", "value": "reconciled"})
        self.assertEqual({i["artifact_id"] for i in check["inputs"]}, {"normalized-screening", "prisma-tool", "count-input-manifest"})
        for artifact in receipt["artifacts"]:
            self.assertEqual(artifact["sha256"], hashlib.sha256((self.root / artifact["path"]).read_bytes()).hexdigest())
        self.assertEqual(check["report"]["sha256"], hashlib.sha256((self.root / "counts-1.json").read_bytes()).hexdigest())
        self.assertNotIn("prisma-counts", {i["artifact_id"] for i in check["inputs"]})
        self.assertEqual(check["applicability"], "applicable")
        self.assertTrue(check["checked_at"].endswith("+00:00"))

    def test_cli_unresolved_is_exit3_completed_unverified(self):
        self.data["report_studies"] = []
        self.prepare()
        self.assertEqual(self.cli().returncode, 3)
        check = self.load("check-1.json")["checks"][0]
        self.assertEqual(check["execution_status"], "completed")
        self.assertEqual(check["domain_result"]["value"], "unverified")

    def test_cli_difference_is_completed_not_execution_failure(self):
        self.data["expected_counts"] = {"included.studies": 2}
        self.prepare()
        self.assertEqual(self.cli().returncode, 1)
        check = self.load("check-1.json")["checks"][0]
        self.assertEqual(check["execution_status"], "completed")
        self.assertEqual(check["domain_result"]["value"], "discrepancy")

    def test_cli_invalid_decision_failed_with_report(self):
        self.data["reports"][0]["decision"] = "unknown"
        self.prepare()
        self.assertEqual(self.cli().returncode, 1)
        check = self.load("check-1.json")["checks"][0]
        self.assertEqual(check["execution_status"], "failed")
        self.assertIsNone(check["domain_result"])
        self.assertTrue(check["reason"])
        self.assertEqual(self.load("counts-1.json")["counts"], {})

    def test_hash_mismatch_refuses_counts_and_does_not_change_input(self):
        changed = (self.root / "rows.json").read_bytes() + b"\n"
        (self.root / "rows.json").write_bytes(changed)
        self.assertEqual(self.cli().returncode, 1)
        self.assertEqual(self.load("counts-1.json")["counts"], {})
        self.assertEqual((self.root / "rows.json").read_bytes(), changed)
        self.assertIn("hash mismatch", self.load("counts-1.json")["errors"][0]["message"])

    def test_changed_during_counting_detected(self):
        path = self.root / "rows.json"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with self.assertRaisesRegex(COUNTER.InputError, "changed during"):
            COUNTER.verify_unchanged({path: original})

    def test_inflight_change_suppresses_counts_and_success_binding(self):
        with patch.object(COUNTER, "__file__", str(self.script)):
            original = COUNTER.compute

            def mutate(data, artifact_id):
                result = original(data, artifact_id)
                with (self.root / "rows.json").open("ab") as stream:
                    stream.write(b"\n")
                return result

            with patch.object(COUNTER, "compute", side_effect=mutate):
                _, code = COUNTER.run(self.root, "manifest.json", "counts-x.json", "check-x.json", "run-x")
        self.assertEqual(code, 1)
        self.assertEqual(self.load("counts-x.json")["counts"], {})
        self.assertEqual(self.load("check-x.json")["checks"][0]["execution_status"], "failed")

    def test_outputs_cannot_overwrite_inputs_or_history(self):
        before = (self.root / "rows.json").read_bytes()
        result = self.cli(extra=("--output", "rows.json"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.root / "rows.json").read_bytes(), before)
        self.assertEqual(self.cli().returncode, 0)
        report = (self.root / "counts-1.json").read_bytes()
        self.assertEqual(self.cli().returncode, 1)
        self.assertEqual((self.root / "counts-1.json").read_bytes(), report)

    def test_missing_file_and_duplicate_artifact_id_fail(self):
        self.manifest["artifacts"][0]["path"] = "missing.json"
        self.save_manifest()
        self.assertEqual(self.cli("missing").returncode, 1)
        self.prepare()
        self.manifest["artifacts"].append(copy.deepcopy(self.manifest["artifacts"][0]))
        self.save_manifest()
        self.assertEqual(self.cli("duplicate").returncode, 1)

    def test_tool_binding_must_be_actual_script(self):
        shutil.copyfile(self.script, self.root / "lookalike.py")
        self.manifest["artifacts"][1]["path"] = "lookalike.py"
        self.save_manifest()
        self.assertEqual(self.cli().returncode, 1)
        self.assertIn("actual executing script", self.load("counts-1.json")["errors"][0]["message"])

    def test_duplicate_json_keys_fail(self):
        (self.root / "manifest.json").write_text('{"id":"a","id":"b"}', encoding="utf-8")
        self.assertEqual(self.cli().returncode, 1)
        self.assertIn("Duplicate JSON key", self.load("counts-1.json")["errors"][0]["message"])

    def test_malformed_json_fails_without_traceback(self):
        (self.root / "manifest.json").write_text("{", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)

    def test_unsafe_paths_and_same_output_rejected(self):
        for path in ("../escape.json", "a/../escape.json", "a//b", "./rows.json", "C:/absolute.json", "a\\b", "/absolute.json", "https://example.test/a"):
            with self.subTest(path=path):
                with self.assertRaises(COUNTER.InputError):
                    COUNTER.local_path(self.root, path)
        self.assertEqual(self.cli(extra=("--check-output", "counts-1.json")).returncode, 1)
        self.assertFalse((self.root / "counts-1.json").exists())

    def test_resolved_escape_is_rejected_without_needing_symlink_privilege(self):
        outside = self.root.parent / "outside-synthetic-file"
        with patch.object(Path, "resolve", return_value=outside):
            with self.assertRaisesRegex(COUNTER.InputError, "escapes"):
                COUNTER.local_path(self.root, "link/rows.json")

    def test_cli_requires_explicit_root_and_outputs(self):
        result = subprocess.run([sys.executable, "-B", str(self.script), "manifest.json"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
