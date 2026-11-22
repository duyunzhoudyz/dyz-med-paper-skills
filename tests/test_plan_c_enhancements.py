"""Hard offline unit & CLI subprocess tests for Plan C (reworked v2):
covers marketplace/catalog alignment, Claude Code Hooks official schema & bypass fixes,
hospital GB18030/XLSX PHI check, native Word tracked changes (<w:trackRevisions/> + DP alignment),
Crossref updated-by vs update-to retraction alerts, 6 complete official reporting-guideline subitem tables,
multicategory Yang & Dalton SMD, exact KM survival verification, publication SVG provenance,
quantitative style check + protected bridge, blind re-review packager, --pack installer,
overwrite/path guards, and reproducible demo build idempotency."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load_mod(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(rel_script: str, args: list[str], stdin_text: str | None = None, env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / rel_script), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


deid = load_mod("dyz-med-data-adequacy/scripts/deidentify_check.py", "deid_v2")
tracked = load_mod("dyz-med-export/scripts/export_tracked_docx.py", "tracked_v2")
verify_refs = load_mod("dyz-med-cnki/scripts/verify_references.py", "vrefs_v2")
table1 = load_mod("dyz-med-analyze/scripts/table1_summary.py", "table1_v2")
km_mod = load_mod("dyz-med-analyze/scripts/km_survival.py", "km_v2")
plotter = load_mod("dyz-med-figures-tables/scripts/plot_clinical_svg.py", "plot_v2")
guideline = load_mod("dyz-med-guideline/scripts/audit_guideline.py", "guide_v2")
jpolicy = load_mod("dyz-med-journal-finder/scripts/fetch_journal_policy.py", "jpol_v2")
installer = load_mod("scripts/install_codex.py", "inst_v2")
demos_mod = load_mod("scripts/build_demos.py", "demos_v2")


class PlanCEnhancementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_marketplace_matches_catalog_and_has_no_conflicting_root_plugin_json(self):
        self.assertFalse((ROOT / ".claude-plugin/plugin.json").exists())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        catalog = json.loads((ROOT / "docs/catalog.json").read_text(encoding="utf-8"))
        cat_groups: dict[str, list[str]] = {}
        for item in catalog:
            cat_groups.setdefault(item["group"], []).append(f"./{item['id']}")

        by_name = {p["name"]: p for p in market["plugins"]}
        self.assertEqual(len(by_name["dyz-med-all"]["skills"]), 32)
        for group_name, expected_skills in cat_groups.items():
            entry = by_name[f"dyz-med-{group_name}"]
            self.assertIs(entry.get("strict"), False)
            self.assertIsInstance(entry.get("hooks"), dict)  # inline hooks object, never file path
            self.assertEqual(sorted(entry["skills"]), sorted(expected_skills))

    def test_hooks_claude_official_schema_and_bypass_fixes_cli(self):
        pp = self.root / "paper/project-passport.yaml"
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.write_text("approvals:\n  - target: research-question\n    state: confirmed\n", encoding="utf-8")

        # MultiEdit with PHI + transplant filename in paper/sections/ (must NOT bypass writing plan gate!)
        payload = {
            "cwd": str(self.root),
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(self.root / "paper/sections/transplant_results.md"),
                "edits": [{"old_string": "a", "new_string": "患者张伟，男，11010519491231002X，138-0013-8000，住院流水号=ZY2026001"}],
            },
        }
        r_adv = run_cli("hooks/med_guard.py", ["pre-tool", "--mode", "advisory"], stdin_text=json.dumps(payload))
        self.assertEqual(r_adv.returncode, 0)
        adv = json.loads(r_adv.stdout)
        self.assertEqual(adv["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertIn("additionalContext", adv["hookSpecificOutput"])
        self.assertIn("PHI_CN_ID", adv["systemMessage"])
        self.assertIn("MISSING_APPROVED_WRITING_PLAN", adv["systemMessage"])
        self.assertNotIn("11010519491231002X", r_adv.stdout)
        self.assertNotIn("138-0013-8000", r_adv.stdout)

        r_strict = run_cli("hooks/med_guard.py", ["pre-tool", "--mode", "strict"], stdin_text=json.dumps(payload))
        self.assertEqual(r_strict.returncode, 0)
        strict = json.loads(r_strict.stdout)
        self.assertEqual(strict["hookSpecificOutput"]["permissionDecision"], "deny")

        r_raw = run_cli("hooks/med_guard.py", ["pre-tool", "--mode", "strict", "--format", "raw"], stdin_text=json.dumps(payload))
        self.assertEqual(r_raw.returncode, 2)

        # Grant No. must NOT false-positive as mobile phone; approved analysis-plan.md allows PowerShell py -3 run
        grant_p = {"cwd": str(self.root), "tool_name": "Write", "tool_input": {"file_path": str(self.root / "ack.md"), "content": "Grant No. 13800123456"}}
        self.assertEqual(run_cli("hooks/med_guard.py", ["pre-tool", "--mode", "strict"], stdin_text=json.dumps(grant_p)).stdout.strip(), "")

        ap = self.root / "paper/analysis/analysis-plan.md"
        ap.parent.mkdir(parents=True, exist_ok=True)
        ap.write_text("审批状态：已确认\n", encoding="utf-8")
        ps_ok = {"cwd": str(self.root), "tool_name": "PowerShell", "tool_input": {"command": "py -3 paper/analysis/run.py"}}
        self.assertEqual(run_cli("hooks/med_guard.py", ["pre-tool", "--mode", "strict"], stdin_text=json.dumps(ps_ok)).stdout.strip(), "")

        # Post-edit ignores plain years, flags statistical paragraphs & orphan evidence
        ms = self.root / "paper/sections/03-results.md"
        ms.parent.mkdir(parents=True, exist_ok=True)
        ms.write_text("# Results\n\nIn 2024 the study enrolled patients.\n\nHR was 0.72 (P = 0.01).\n\nOrphan [evidence:E1]\n", encoding="utf-8")
        r_post = run_cli("hooks/med_guard.py", ["post-edit"], stdin_text=json.dumps({"cwd": str(self.root), "tool_input": {"file_path": str(ms)}}))
        self.assertEqual(r_post.returncode, 0)
        post_obj = json.loads(r_post.stdout)
        self.assertIn("STATISTICAL_PARAGRAPHS_UNBOUND", post_obj["systemMessage"])
        self.assertIn("EVIDENCE_WITHOUT_CLAIM", post_obj["systemMessage"])

    def test_deidentify_gb18030_xlsx_cli_and_overwrite_guard(self):
        gbk = self.root / "hospital_gbk.csv"
        gbk.write_bytes(
            (
                "患者ID,姓名(中文),联系电话1,入院时间,年龄(岁),家庭地址,样本条码,结局\n"
                "P001,张三,138-0013-8000,2026-01-15,91,北京市朝阳区1号,13912345678,1,EXTRA\n"
            ).encode("gb18030")
        )
        rep_p = self.root / "phi.json"
        out_p = self.root / "clean.csv"
        r1 = run_cli("dyz-med-data-adequacy/scripts/deidentify_check.py",
                     ["--input", str(gbk), "--report", str(rep_p), "--output", str(out_p)])
        self.assertEqual(r1.returncode, 0, r1.stderr)
        rep = json.loads(rep_p.read_text(encoding="utf-8"))
        self.assertEqual(rep["input"]["detected_encoding"], "gb18030")
        self.assertEqual(rep["age_over_89_count"], 1)
        cleaned = out_p.read_text(encoding="utf-8")
        self.assertNotIn("张三", cleaned)
        self.assertNotIn("138-0013-8000", cleaned)
        self.assertIn(">89", cleaned)
        self.assertIn("13912345678", cleaned)  # barcode preserved!

        # Silent overwrite refused without --force
        r_dup = run_cli("dyz-med-data-adequacy/scripts/deidentify_check.py",
                        ["--input", str(gbk), "--report", str(rep_p)])
        self.assertEqual(r_dup.returncode, 2)

        # XLSX scan works with stdlib only
        xlsx = self.root / "clin.xlsx"
        with ZipFile(xlsx, "w") as zf:
            zf.writestr("xl/sharedStrings.xml",
                        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>姓名</t></si><si><t>王五</t></si></sst>')
            zf.writestr("xl/worksheets/sheet1.xml",
                        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                        '<row r="1"><c r="A1" t="s"><v>0</v></c></row><row r="2"><c r="A2" t="s"><v>1</v></c></row>'
                        '</sheetData></worksheet>')
        r_x = run_cli("dyz-med-data-adequacy/scripts/deidentify_check.py",
                      ["--input", str(xlsx), "--report", str(self.root / "x.json"), "--fail-on-phi"])
        self.assertEqual(r_x.returncode, 1)

    def test_native_word_tracked_docx_settings_markers_alignment_cli(self):
        old_p = self.root / "old.md"
        new_p = self.root / "new.md"
        out_p = self.root / "tracked.docx"
        rep_p = self.root / "report.json"
        old_p.write_text("# Results\n### Sub\nPara A baseline 240.\x0c [claim:C1]\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
        new_p.write_text("# Results\n### Sub\nInserted para.\n\nPara A baseline 240 revised. [claim:C1]\n\n| A | B |\n|---|---|\n| 1 | 3 |\n", encoding="utf-8")

        r = run_cli("dyz-med-export/scripts/export_tracked_docx.py",
                    ["--old", str(old_p), "--new", str(new_p), "--output", str(out_p), "--report", str(rep_p), "--author", "Dr. Z"])
        self.assertEqual(r.returncode, 0, r.stderr)
        with ZipFile(out_p) as zf:
            self.assertIn("word/settings.xml", zf.namelist())
            self.assertIn("docProps/core.xml", zf.namelist())
            self.assertIn("trackRevisions", zf.read("word/settings.xml").decode("utf-8"))
            doc_xml = zf.read("word/document.xml").decode("utf-8")
            self.assertNotIn("[claim:", doc_xml)
            root = ET.fromstring(doc_xml.encode("utf-8"))
            ns = {"w": tracked.W_NS}
            self.assertTrue(root.findall(".//w:tbl", ns))
            self.assertTrue(root.findall(".//w:ins", ns))
        # Overwrite refused without --force
        r2 = run_cli("dyz-med-export/scripts/export_tracked_docx.py",
                     ["--old", str(old_p), "--new", str(new_p), "--output", str(out_p)])
        self.assertEqual(r2.returncode, 2)

    def test_verify_references_crossref_updated_by_vs_update_to_and_exit_code_4(self):
        rows = [
            {"id": "orig-retracted", "doi": "10.1016/S0140-6736(97)11096-0", "title": "Wakefield original"},
            {"id": "notice-itself", "doi": "10.1016/S0140-6736(20)31324-6", "title": "Retraction notice"},
            {"id": "pm-retracted", "pmid": "32450107", "title": "Mehra NEJM"},
        ]
        offline_doc = {
            "schema_version": "1.0",
            "responses": [
                {
                    "provider": "crossref",
                    "identifier": "10.1016/s0140-6736(97)11096-0",
                    "attempts": [{"status": 200, "body": {"message": {
                        "DOI": "10.1016/S0140-6736(97)11096-0", "title": ["Wakefield original"],
                        "updated-by": [{"type": "retraction", "label": "Retraction", "source": "retraction-watch"}],
                    }}}],
                },
                {
                    "provider": "crossref",
                    "identifier": "10.1016/s0140-6736(20)31324-6",
                    "attempts": [{"status": 200, "body": {"message": {
                        "DOI": "10.1016/S0140-6736(20)31324-6", "title": ["Retraction notice"],
                        "update-to": [{"type": "retraction", "label": "Retraction"}],
                    }}}],
                },
                {
                    "provider": "pubmed",
                    "identifier": "32450107",
                    "attempts": [{"status": 200, "body": {"result": {"32450107": {
                        "uid": "32450107", "title": "Mehra NEJM",
                        "pubtype": ["Journal Article", "Retracted Publication"],
                        "references": [{"reftype": "Retraction in", "refsource": "NEJM 2020"}],
                    }}}}],
                },
            ],
        }
        result = verify_refs.verify(rows, verify_refs.OfflineTransport(offline_doc))
        by_id = {r["id"]: r for r in result["records"]}
        self.assertEqual(by_id["orig-retracted"]["retraction_status"], "retracted")
        self.assertEqual(by_id["notice-itself"]["retraction_status"], "is_update_notice_itself")
        self.assertEqual(by_id["pm-retracted"]["retraction_status"], "retracted")
        self.assertEqual(result["integrity_status"], "retraction_alert")

        # Full run() returns exit code 4 when retracted reference is matched!
        ref_b = json.dumps({"schema_version": "1.0", "references": rows}).encode("utf-8")
        resp_b = json.dumps(offline_doc).encode("utf-8")
        (self.root / "refs.json").write_bytes(ref_b)
        (self.root / "resp.json").write_bytes(resp_b)
        man = self.root / "manifest.json"
        man.write_text(json.dumps({
            "artifacts": [
                {"id": "references", "path": "refs.json", "version": "v1", "sha256": hashlib.sha256(ref_b).hexdigest()},
                {"id": "responses", "path": "resp.json", "version": "v1", "sha256": hashlib.sha256(resp_b).hexdigest()},
            ],
            "roles": {"references": "references", "responses": "responses"},
        }), encoding="utf-8")
        summary, code = verify_refs.run(man, self.root, "rep.json", "rec.json", "chk-ret")
        self.assertEqual(code, 4)
        self.assertEqual(summary["integrity_status"], "retraction_alert")
        self.assertEqual(summary["retraction_alert_count"], 3)

    def test_structured_checklists_official_subitem_counts_and_strict_audit_cli(self):
        db = guideline.load_checklists()
        expected = {
            "STROBE-Cohort": 34, "STROBE-CaseControl": 33, "STROBE-CrossSectional": 32,
            "PRISMA-2020": 42, "CONSORT-2025": 42, "STARD-2015": 34, "CARE": 30, "TRIPOD+AI": 52,
        }
        for name, cnt in expected.items():
            self.assertEqual(len(db["guidelines"][name]["items"]), cnt, name)

        ms = self.root / "ms.md"
        ms.write_text("# Case Report\nBody.\n", encoding="utf-8")
        skel_p = self.root / "care.json"
        r_init = run_cli("dyz-med-guideline/scripts/audit_guideline.py",
                         ["init", "--guideline", "CARE", "--manuscript", str(ms), "--output", str(skel_p)])
        self.assertEqual(r_init.returncode, 0, r_init.stderr)
        doc = json.loads(skel_p.read_text(encoding="utf-8"))
        doc["items"][0]["status"] = "PARTIAL"
        doc["items"][0]["comment"] = ""  # invalid: PARTIAL without gap comment
        doc["items"].append({"id": "99z", "status": "MISSING"})  # invalid: unknown item ID
        skel_p.write_text(json.dumps(doc), encoding="utf-8")
        r_chk = run_cli("dyz-med-guideline/scripts/audit_guideline.py",
                        ["check", "--audit", str(skel_p), "--manuscript", str(ms)])
        self.assertEqual(r_chk.returncode, 1)
        out = json.loads(r_chk.stdout)
        codes = {i["code"] for i in out["issues"]}
        self.assertTrue({"PARTIAL_WITHOUT_GAP_COMMENT", "UNKNOWN_ITEM_ID"} <= codes)

    def test_table1_km_meta_diagnostic_and_svg_provenance_cli(self):
        csv_p = self.root / "cohort.csv"
        csv_p.write_text(
            "grp,age,stage,time,ev\n"
            "A,60,I,12,1\nA,62,II,24,0\nA,64,III,36,0\nA,66,NA,36,0\n"
            "B,70,I,10,1\nB,72,III,20,1\nB,74,III,36,0\nB,76,III,36,0\n"
            ",80,I,12,1\n",
            encoding="utf-8",
        )
        r_t1 = run_cli("dyz-med-analyze/scripts/table1_summary.py",
                       ["--input", str(csv_p), "--group", "grp", "--continuous", "age", "--categorical", "stage", "--out-dir", str(self.root / "t1")])
        self.assertEqual(r_t1.returncode, 0, r_t1.stderr)
        t1 = json.loads((self.root / "t1/table1.json").read_text(encoding="utf-8"))
        self.assertEqual(t1["input"]["analyzed_rows"], 8)
        self.assertEqual(t1["input"]["excluded_missing_group_rows"], 1)

        r_km = run_cli("dyz-med-analyze/scripts/km_survival.py",
                       ["--input", str(csv_p), "--group", "grp", "--time", "time", "--event", "ev",
                        "--out-results", str(self.root / "km.json"), "--out-spec", str(self.root / "km-spec.json")])
        self.assertEqual(r_km.returncode, 0, r_km.stderr)
        r_svg = run_cli("dyz-med-figures-tables/scripts/plot_clinical_svg.py",
                        ["--spec", str(self.root / "km-spec.json"), "--output", str(self.root / "km.svg"), "--source-data", str(csv_p)])
        self.assertEqual(r_svg.returncode, 0, r_svg.stderr)
        r_chk = run_cli("dyz-med-figures-tables/scripts/plot_clinical_svg.py",
                        ["--spec", str(self.root / "km-spec.json"), "--output", str(self.root / "km.svg"), "--source-data", str(csv_p), "--check"])
        self.assertEqual(r_chk.returncode, 0)
        # Tampering source CSV invalidates provenance
        csv_p.write_text(csv_p.read_text(encoding="utf-8") + "B,78,III,36,0\n", encoding="utf-8")
        r_stale = run_cli("dyz-med-figures-tables/scripts/plot_clinical_svg.py",
                          ["--spec", str(self.root / "km-spec.json"), "--output", str(self.root / "km.svg"), "--source-data", str(csv_p), "--check"])
        self.assertEqual(r_stale.returncode, 1)

    def test_journal_policy_ssrf_auth_and_zh_gb18030_cli(self):
        # Online without authorization must exit 3
        r_unauth = run_cli("dyz-med-journal-finder/scripts/fetch_journal_policy.py",
                           ["--journal", "JAMA", "--online", "--url", "https://example.org", "--output", str(self.root / "p.json")])
        self.assertEqual(r_unauth.returncode, 3)
        for bad in ("https://127.0.0.1/x", "https://169.254.169.254/latest", "http://example.org/x"):
            with self.assertRaises(ValueError):
                jpolicy.validate_public_url(bad)

        snap = self.root / "zh_gbk.html"
        snap.write_bytes("<html><meta charset='gbk'><body><p>论著正文不超过5000字，摘要400字以内，参考文献不超过40篇，遵循STROBE规范，使用大语言模型需披露。</p></body></html>".encode("gb18030"))
        out = self.root / "pol.json"
        r_off = run_cli("dyz-med-journal-finder/scripts/fetch_journal_policy.py",
                        ["--journal", "中华测试", "--snapshot", str(snap), "--output", str(out)])
        self.assertEqual(r_off.returncode, 0, r_off.stderr)
        pol = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("STROBE", pol["extracted_signals"]["reporting_guidelines_mentioned"])
        self.assertTrue(pol["extracted_signals"]["word_limit_mentions"])

    def test_style_check_and_blind_rereview_pack_cli(self):
        b, a = self.root / "b.md", self.root / "a.md"
        b.write_text("Dr. Smith et al. found HR 0.72 in 240 patients (e.g., Fig. 1). Furthermore, moreover, additionally, we utilized a robust methodology.\n", encoding="utf-8")
        a.write_text("Dr. Smith et al. found HR 0.72 in 240 patients (e.g., Fig. 1). We used a matched cohort design.\n", encoding="utf-8")
        r_st = run_cli("dyz-med-deai/scripts/style_check.py", ["--before", str(b), "--after", str(a)])
        self.assertEqual(r_st.returncode, 0, r_st.stderr)
        st = json.loads(r_st.stdout)
        self.assertEqual(st["protected_content_check"]["status"], "consistent")
        self.assertGreater(st["before_finding_count"], st["after_finding_count"])

        c, m, resp = self.root / "c.json", self.root / "m.md", self.root / "r.json"
        c.write_text(json.dumps({"comments": [{"id": "C1", "original_text": "Clarify blinding", "author_reply": "SECRET"}]}), encoding="utf-8")
        m.write_text("# Draft\nBlinding clarified.\n", encoding="utf-8")
        self.assertEqual(run_cli("dyz-med-revision/scripts/blind_rereview_pack.py",
                                 ["pack", "--comments", str(c), "--manuscript", str(m), "--out-dir", str(self.root / "blind")]).returncode, 0)
        self.assertNotIn("SECRET", (self.root / "blind/blind-rereview-packet.json").read_text(encoding="utf-8"))
        resp.write_text(json.dumps({"responses": [{"id": "C1", "response_stance": "ACCEPT", "status": "verified_closed"}]}), encoding="utf-8")
        r_rec = run_cli("dyz-med-revision/scripts/blind_rereview_pack.py",
                        ["reconcile", "--verdicts", str(self.root / "blind/blind-verdicts-template.json"), "--responses", str(resp), "--manuscript", str(m)])
        self.assertEqual(r_rec.returncode, 1)

    def test_installer_pack_mode_and_demos_idempotent_with_exact_km(self):
        target = self.root / "pack_install"
        rep = installer.synchronize(ROOT, target, pack="analysis")
        self.assertEqual(rep["status"], "pass")
        self.assertEqual(rep["skill_count"], 5)
        self.assertTrue((target / "dyz-med-analyze/scripts/km_survival.py").is_file())
        self.assertTrue((target / "dyz-med-figures-tables/scripts/plot_clinical_svg.py").is_file())

        # Rebuilding demos into two temp folders with identical timestamp produces identical summary & consistent audits
        d1, d2 = self.root / "d1", self.root / "d2"
        self.assertEqual(demos_mod.main(["--out-dir", str(d1), "--timestamp", "2026-11-22T00:00:00+00:00"]), 0)
        self.assertEqual(demos_mod.main(["--out-dir", str(d2), "--timestamp", "2026-11-22T00:00:00+00:00"]), 0)
        self.assertEqual((d1 / "summary.json").read_bytes(), (d2 / "summary.json").read_bytes())

        # Verify Demo 01 committed artifacts: protected==consistent, audit==consistent, KM matches CSV recomputation
        summary = json.loads((ROOT / "demos/summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["demos"][0]["protected"], "consistent")
        self.assertEqual(summary["demos"][0]["audit"], "consistent")
        self.assertEqual(summary["demos"][2]["audit"], "consistent")
        re_km, _ = km_mod.analyze_survival(ROOT / "demos/01_cohort_strobe/cohort_deidentified.csv", "exposure", "followup_months", "event", [0.0, 12.0, 24.0, 36.0])
        committed_km = json.loads((ROOT / "demos/01_cohort_strobe/results/km-results.json").read_text(encoding="utf-8"))
        self.assertEqual(re_km["groups"]["Exposed"]["survival_at_ticks"], committed_km["groups"]["Exposed"]["survival_at_ticks"])
        self.assertEqual(re_km["groups"]["Unexposed"]["survival_at_ticks"], committed_km["groups"]["Unexposed"]["survival_at_ticks"])


if __name__ == "__main__":
    unittest.main()
