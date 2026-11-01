"""标准库题录工具的合成测试；不联网、不创建真实授权。"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "dyz-med-cnki/scripts/verify_references.py"
FIXTURE = ROOT / "tests/fixtures/reference-verification.json"
SPEC = importlib.util.spec_from_file_location("verify_references", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.raw_fixture = FIXTURE.read_bytes()
        self.fixture = json.loads(self.raw_fixture)
        self.references = self.fixture["references"]
        self.responses = self.fixture["responses"]

    def tearDown(self):
        self.assertEqual(FIXTURE.read_bytes(), self.raw_fixture)

    def verify(self, **kwargs):
        rows = self.references["references"]
        before = copy.deepcopy((rows, self.responses))
        result = checker.verify(rows, checker.OfflineTransport(self.responses), **kwargs)
        self.assertEqual(before, (rows, self.responses))
        return result

    def stage(self, root, authorized=False, csv=False):
        entries = []

        def add(identity, path, raw):
            if not isinstance(raw, bytes):
                raw = json.dumps(raw).encode("utf-8")
            (root / path).write_bytes(raw)
            entry = {"id": identity, "path": path, "version": "v1", "sha256": digest(raw)}
            entries.append(entry)
            return entry

        if csv:
            reference = add("references", "references.csv",
                            b'id,doi,title\nsynthetic-crossref,10.5555/synthetic.1,Synthetic cohort study: methods and results\n')
        else:
            reference = add("references", "references.json", self.references)
        add("responses", "responses.json", self.responses)
        if authorized:
            evidence = add("synthetic-consent", "consent.txt",
                           b'SYNTHETIC TEST ONLY: no real person or external transmission permission.\n')
            approval = {"state": "confirmed", "targets": [{"artifact_id": reference["id"],
                         "version": reference["version"], "sha256": reference["sha256"]}],
                        "role": "synthetic-test-role", "confirmed_at": "2026-10-31T00:00:00+00:00",
                        "source": {"kind": "human", "actor_id": "synthetic-actor",
                                   "statement": "Synthetic schema test only, not real permission.",
                                   "reference": {"path": evidence["path"], "sha256": evidence["sha256"]},
                                   "locator": "synthetic fixture line 1"}}
            auth = {"purpose": checker.PURPOSE, "content_category": checker.CATEGORY,
                    "destinations": list(checker.HOSTS.values()), "fields": ["doi", "pmid"],
                    "approval": approval}
            add("authorization", "authorization.json", auth)
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"artifacts": entries, "roles": {
            "references": "references", "responses": "responses"}}), encoding="utf-8")
        return manifest

    def alter_auth(self, root, mutate):
        path = root / "authorization.json"
        data = json.loads(path.read_bytes())
        mutate(data)
        raw = json.dumps(data).encode("utf-8")
        path.write_bytes(raw)
        manifest = root / "manifest.json"
        doc = json.loads(manifest.read_bytes())
        for item in doc["artifacts"]:
            if item["id"] == "authorization":
                item["sha256"] = digest(raw)
        manifest.write_text(json.dumps(doc), encoding="utf-8")

    def cli(self, root, manifest, *flags):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(manifest), "--root", str(root),
                               "--report", "report.json", "--record", "check.json", "--check-id", "synthetic-run",
                               *flags], capture_output=True, text=True, encoding="utf-8")

    def test_crossref_and_pubmed_positive(self):
        result = self.verify()
        self.assertEqual(result["conclusion"], "matched")
        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["network_requests"], 0)
        for item in result["records"]:
            self.assertEqual(item["access_scope"], "metadata_only")
            self.assertEqual(item["claim_support"]["status"], "not_assessed")
            self.assertEqual(item["evidence_mode"], "offline")

    def test_real_identifier_shape_wrong_title_is_mismatch(self):
        self.references["references"][0]["title"] = "Completely different cancer therapy"
        item = self.verify()["records"][0]
        self.assertEqual(item["identity_status"], "mismatch")
        self.assertEqual(item["differences"][0]["field"], "title")
        self.assertEqual(item["fields"][0]["status"], "matched")

    def test_identifier_mismatch(self):
        self.responses["responses"][0]["attempts"][0]["body"]["message"]["DOI"] = "10.5555/other"
        self.assertEqual(self.verify()["records"][0]["identity_status"], "mismatch")

    def test_missing_identifier_does_not_query_title(self):
        row = self.references["references"][0]
        row.pop("doi")
        transport = Mock()
        report = checker.verify([row], transport)
        transport.assert_not_called()
        self.assertEqual(report["conclusion"], "unverified")
        self.assertEqual(report["records"][0]["reason"], "identifier_missing")

    def test_missing_title_never_passes(self):
        self.references["references"][0].pop("title")
        self.assertEqual(self.verify()["records"][0]["identity_status"], "unverified")

    def test_url_and_query_injection_not_sent(self):
        for field, bad in (("doi", "https://attacker.test/10.1/test"),
                           ("doi", "10.5555/a?secret=1"), ("doi", "10.5555/a#fragment"),
                           ("pmid", "123&api_key=secret"), ("pmid", "https://attacker.test")):
            with self.subTest(field=field, bad=bad):
                row = {"id": "x", "title": "x", field: bad}
                transport = Mock()
                self.assertEqual(checker.verify([row], transport)["conclusion"], "unverified")
                transport.assert_not_called()

    def test_requests_use_fixed_hosts_and_identifiers_only(self):
        for row in self.references["references"]:
            query, error = checker.request_for(row)
            self.assertIsNone(error)
            self.assertTrue(query["url"].startswith(query["destination"] + "/"))
            self.assertNotIn(row["title"], query["url"])
            self.assertNotIn("api_key", query["url"])
            self.assertNotIn("mailto", query["url"])
        self.assertEqual(checker.request_for(self.references["references"][1])[0]["provider"], "pubmed")

    def test_failure_cases_are_unverified_and_retries_bounded(self):
        for case in self.fixture["failure_cases"]:
            with self.subTest(case=case["name"]):
                self.responses["responses"][0]["attempts"] = case["attempts"]
                report = self.verify(max_attempts=2)
                item = report["records"][0]
                self.assertEqual(item["identity_status"], "unverified")
                self.assertEqual(len(item["attempts"]), case["expected_attempts"])
                self.assertNotIn("fabricated", json.dumps(item))

    def test_timeout_then_success_retains_failed_attempt(self):
        attempts = self.responses["responses"][0]["attempts"]
        attempts.insert(0, {"status": None, "error": "timeout"})
        item = self.verify(max_attempts=2)["records"][0]
        self.assertEqual(item["identity_status"], "matched")
        self.assertEqual(item["attempts"][0]["error"], "timeout")
        self.assertEqual(len(item["attempts"]), 2)

    def test_pubmed_no_result_is_unverified(self):
        self.responses["responses"][1]["attempts"][0]["body"] = {"result": {"uids": []}}
        self.assertEqual(self.verify()["records"][1]["identity_status"], "unverified")

    def test_optional_fields_not_invented(self):
        self.responses["responses"][0]["attempts"][0]["body"]["message"].pop("published")
        item = self.verify()["records"][0]
        self.assertEqual(item["identity_status"], "unverified")
        self.assertIn("year", item["missing_fields"])

    def test_empty_batch_unverified(self):
        self.references["references"] = []
        self.assertEqual(self.verify()["conclusion"], "unverified")

    def test_title_normalization_does_not_fuzzy_match(self):
        self.assertEqual(checker.normalize("A &amp; B: <i>trial</i>."), "a b trial")
        self.references["references"][0]["title"] += " withdrawn"
        self.assertEqual(self.verify()["conclusion"], "mismatch")

    def test_bad_input_rejected_before_transport(self):
        for rows in ([{"id": "a", "title": "A", "abstract": "private"}],
                     [{"id": "a"}, {"id": "a"}], [{"id": "a", "year": 2020}],
                     [{"id": "a", "url": "https://attacker.test"}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                checker.read_references(json.dumps({"schema_version": "1.0", "references": rows}).encode(), ".json")
        with self.assertRaises(ValueError):
            checker.read_references(b"id,title,title\nx,a,a\n", ".csv")
        with self.assertRaises(ValueError):
            checker.read_references(b"@article{}", ".bib")

    def test_json_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            checker.load_json(b'{"a":1,"a":2}')

    def test_default_offline_ignores_injected_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            transport = Mock(side_effect=AssertionError("network used"))
            result, code = checker.run(manifest, root, "report.json", "check.json", "run", transport=transport)
            transport.assert_not_called()
            self.assertEqual(code, 0)
            self.assertEqual(result["network_requests"], 0)

    def test_online_without_authorization_zero_sends(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            transport = Mock(side_effect=AssertionError("network used"))
            result, code = checker.run(manifest, root, "report.json", "check.json", "run", True, transport=transport)
            transport.assert_not_called()
            self.assertEqual(code, 3)
            self.assertEqual(result["execution_status"], "blocked")
            record = json.loads((root / "check.json").read_bytes())
            self.assertIsNone(record["checks"][0]["domain_result"])

    def test_authorization_unknown_dimensions_each_send_zero(self):
        mutations = [lambda a: a.update(purpose="export"),
                     lambda a: a.update(content_category="manuscript"),
                     lambda a: a.update(destinations=["https://attacker.test"]),
                     lambda a: a.update(fields=["title"]),
                     lambda a: a.update(fields=["doi"]),
                     lambda a: a["approval"].update(state="not_confirmed"),
                     lambda a: a["approval"].update(targets=[]),
                     lambda a: a["approval"].update(role=""),
                     lambda a: a["approval"].update(confirmed_at="2026-01-01"),
                     lambda a: a["approval"]["source"].update(kind="model"),
                     lambda a: a["approval"]["source"].update(locator=""),
                     lambda a: a["approval"]["source"]["reference"].update(sha256="0" * 64),
                     lambda a: a["approval"]["source"]["reference"].update(path="../consent.txt")]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = self.stage(root, authorized=True)
                self.alter_auth(root, mutation)
                transport = Mock(side_effect=AssertionError("network used"))
                result, code = checker.run(manifest, root, "report.json", "check.json", "run", True,
                                           "authorization", transport=transport)
                self.assertEqual(code, 3)
                self.assertEqual(result["network_requests"], 0)
                transport.assert_not_called()

    def test_synthetic_approval_only_calls_mock_transport(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root, authorized=True)
            mock = Mock(side_effect=checker.OfflineTransport(self.responses))
            with patch.object(checker, "HttpTransport", side_effect=AssertionError("real network forbidden")):
                result, code = checker.run(manifest, root, "report.json", "check.json", "run", True,
                                           "authorization", transport=mock)
            self.assertEqual(code, 0)
            self.assertEqual(mock.call_count, 2)
            self.assertEqual(result["network_requests"], 2)

    def test_no_redirect_and_no_environment_proxy_credentials(self):
        with patch.object(checker, "ProxyHandler") as proxy, patch.object(checker, "build_opener"):
            checker.HttpTransport()
            proxy.assert_called_once_with({})
        handler = checker.NoRedirect()
        self.assertIsNone(handler.redirect_request(Request("https://api.crossref.org/works/x"), None,
                                                  302, "Found", {}, "https://attacker.test"))

    def test_http_transport_handles_redirect_rate_limit_timeout(self):
        for error, expected in ((HTTPError("https://api.crossref.org", 302, "redirect", {}, None), 302),
                                (HTTPError("https://api.crossref.org", 429, "limited", {}, None), 429),
                                (TimeoutError(), None), (URLError("unavailable"), None)):
            with self.subTest(error=type(error).__name__):
                transport = checker.HttpTransport()
                transport.opener = Mock()
                transport.opener.open.side_effect = error
                query, _ = checker.request_for(self.references["references"][0])
                response = transport(query, 1)
                self.assertEqual(response["status"], expected)
                self.assertEqual(transport.opener.open.call_count, 1)

    def test_cli_json_csv_immutable_and_report_hash(self):
        for use_csv in (False, True):
            with self.subTest(csv=use_csv), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = self.stage(root, csv=use_csv)
                before = {p: p.read_bytes() for p in root.iterdir()}
                process = self.cli(root, manifest)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                record = json.loads((root / "check.json").read_bytes())
                check = record["checks"][0]
                self.assertEqual(check["report"]["sha256"], digest((root / "report.json").read_bytes()))
                self.assertEqual(check["domain_result"], {"namespace": "reference_identity", "value": "matched"})
                self.assertIn("offline", check["scope"]["description"])

    def test_cli_mismatch_unverified_blocked_and_input_error_codes(self):
        for code in (1, 3, 2):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                if code == 1:
                    self.references["references"][0]["title"] = "Wrong title"
                elif code == 3:
                    self.references["references"][0]["title"] = ""
                manifest = self.stage(root)
                if code == 2:
                    (root / "references.json").write_text("changed", encoding="utf-8")
                process = self.cli(root, manifest)
                self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            self.assertEqual(self.cli(root, manifest, "--online").returncode, 3)

    def test_no_response_offline_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            data = json.loads(manifest.read_bytes())
            data["roles"].pop("responses")
            manifest.write_text(json.dumps(data), encoding="utf-8")
            process = self.cli(root, manifest)
            self.assertEqual(process.returncode, 3)
            self.assertEqual(json.loads(process.stdout)["network_requests"], 0)

    def test_output_overwrite_and_input_collision_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            self.assertEqual(self.cli(root, manifest).returncode, 0)
            before = (root / "report.json").read_bytes()
            self.assertEqual(self.cli(root, manifest).returncode, 2)
            self.assertEqual((root / "report.json").read_bytes(), before)
            with self.assertRaises(ValueError):
                checker.run(manifest, root, "references.json", "new.json", "run")

    def test_root_traversal_and_bad_retry_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for value in ("../x", "/x", "C:/x", "a\\b", "a//b", "./x"):
                with self.subTest(path=value), self.assertRaises(ValueError):
                    checker.path_at(root, value)
            for attempts in (0, 3, True):
                with self.subTest(attempts=attempts), self.assertRaises(ValueError):
                    checker.verify([], max_attempts=attempts)

    def test_changed_inputs_during_run_refuse_check_record(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.stage(root)
            original = checker.verify

            def mutate(*args):
                result = original(*args)
                (root / "responses.json").write_text("changed", encoding="utf-8")
                return result

            with patch.object(checker, "verify", side_effect=mutate):
                with self.assertRaisesRegex(ValueError, "运行中输入改变"):
                    checker.run(manifest, root, "report.json", "check.json", "run")
            self.assertFalse((root / "check.json").exists())

    def test_cli_argument_error(self):
        process = subprocess.run([sys.executable, "-B", str(SCRIPT)], capture_output=True)
        self.assertEqual(process.returncode, 2)


if __name__ == "__main__":
    unittest.main()
