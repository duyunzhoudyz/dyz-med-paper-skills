#!/usr/bin/env python3
"""Reproducibly build 3 end-to-end medical research workflow demos using stdlib tools only.

Every statistical number and plot coordinate is computed directly from each demo's CSV via the
bundled scripts (zero hard-coded plot coordinates, zero fabricated RoB 2 judgments).

Demos generated under --out-dir (default: demos/):
  1. 01_cohort_strobe/     — Observational cohort (exponential survival + administrative censoring at 36m ->
                             PHI check -> Baseline-only Table 1 with multicategory SMD -> Exact KM + Log-rank + Risk Table SVG ->
                             Evidence audit -> Protected-number preservation -> STROBE-Cohort full 34-subitem audit -> Native Tracked DOCX)
  2. 02_bcg_meta_prisma/   — Published BCG 13-trial dataset (Colditz et al., JAMA 1994; metafor::dat.bcg with real latitude & alloc ->
                             DerSimonian-Laird pooling + 95% PI + latitude subgroups + leave-one-out -> Publication Forest SVG ->
                             Honest allocation-method RoB matrix using `no_information` for unassessed domains -> PRISMA-2020 full 42-subitem audit)
  3. 03_diagnostic_stard/  — Diagnostic accuracy cohort (N=300 -> 2x2 table + Wilson 95% CI + PPV/NPV/LR+/LR- + DeLong AUC 95% CI ->
                             ROC curve SVG -> Evidence audit -> STARD-2015 full 34-subitem audit)

Run:
  python -B scripts/build_demos.py [--out-dir demos] [--timestamp 2026-11-22T00:00:00+00:00]
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TS = "2026-11-22T00:00:00+00:00"


def load_mod(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


deid = load_mod("dyz-med-data-adequacy/scripts/deidentify_check.py", "demo_deid")
table1 = load_mod("dyz-med-analyze/scripts/table1_summary.py", "demo_table1")
km_mod = load_mod("dyz-med-analyze/scripts/km_survival.py", "demo_km")
meta_mod = load_mod("dyz-med-analyze/scripts/meta_analysis.py", "demo_meta")
diag_mod = load_mod("dyz-med-analyze/scripts/diagnostic_accuracy.py", "demo_diag")
plotter = load_mod("dyz-med-figures-tables/scripts/plot_clinical_svg.py", "demo_plotter")
audit_ms = load_mod("dyz-med-evidence-audit/scripts/audit_manuscript.py", "demo_audit_ms")
guideline = load_mod("dyz-med-guideline/scripts/audit_guideline.py", "demo_guideline")
style_chk = load_mod("dyz-med-deai/scripts/style_check.py", "demo_style")
protect = load_mod("dyz-med-translate/scripts/compare_protected.py", "demo_protect")
tracked_docx = load_mod("dyz-med-export/scripts/export_tracked_docx.py", "demo_tracked")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def build_demo_01(base: Path, ts: str) -> dict:
    """Demo 01: Observational cohort (synthetic teaching cohort, realistic exponential survival) -> STROBE-Cohort."""
    d = base / "01_cohort_strobe"
    d.mkdir(parents=True, exist_ok=True)

    rng = random.Random(20261122)
    csv_path = d / "cohort_deidentified.csv"
    stages = ("Stage I", "Stage II", "Stage III")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["subject_id", "exposure", "age_years", "sex", "bmi", "hba1c_pct", "ckd_stage", "followup_months", "event"])
        for i in range(1, 241):
            exp = "Exposed" if i <= 120 else "Unexposed"
            age = round(rng.gauss(62.4 if exp == "Exposed" else 61.8, 8.5), 1)
            sex = "Male" if rng.random() < (0.56 if exp == "Exposed" else 0.54) else "Female"
            bmi = round(rng.gauss(26.1 if exp == "Exposed" else 25.9, 3.2), 1)
            hba1c = round(rng.gauss(7.6 if exp == "Exposed" else 7.5, 1.1), 2)
            ckd = rng.choices(stages, weights=[0.45, 0.35, 0.20] if exp == "Exposed" else [0.42, 0.36, 0.22])[0]
            # Realistic exponential event time + administrative censoring at 36 months + random dropout
            haz = 0.0055 if exp == "Exposed" else 0.0115
            t_event = -math.log(max(1e-6, rng.random())) / haz
            t_censor = 36.0 if rng.random() < 0.85 else rng.uniform(10.0, 35.5)
            event = 1 if t_event <= t_censor else 0
            fup = round(min(t_event, t_censor), 1)
            w.writerow([f"SUBJ_{i:04d}", exp, age, sex, bmi, hba1c, ckd, fup, event])

    # 1. Zero-network PHI check
    phi_rep, _ = deid.process_tabular(csv_path, None, ",")
    phi_rep["checked_at"] = ts
    write_json(d / "qc/phi-report.json", phi_rep)

    # 2. Baseline-only Table 1 (strictly excluding followup_months and event!)
    t1 = table1.summarize_table1(
        csv_path, "exposure", ["age_years", "bmi", "hba1c_pct"], ["sex", "ckd_stage"], timestamp=ts
    )
    write_json(d / "results/table1.json", t1)
    t1_md = table1.render_markdown(t1)
    (d / "results/table1.md").write_text(t1_md, encoding="utf-8", newline="\n")

    # 3. Exact Kaplan-Meier computation directly from cohort_deidentified.csv
    km_res, km_spec = km_mod.analyze_survival(
        csv_path,
        group_col="exposure",
        time_col="followup_months",
        event_col="event",
        risk_ticks=[0.0, 12.0, 24.0, 36.0],
        title="Demo 01: Kaplan-Meier Event-Free Survival (Synthetic Cohort, N=240)",
        xlabel="Follow-up (months)",
        ylabel="Event-Free Survival Probability",
        timestamp=ts,
    )
    km_res_p = write_json(d / "results/km-results.json", km_res)
    km_spec_p = write_json(d / "results/km-spec.json", km_spec)
    km_svg = d / "figures/figure1-km.svg"
    plotter.generate_with_provenance(km_spec_p, km_svg, csv_path, timestamp=ts)
    km_check = plotter.check_provenance(km_spec_p, km_svg, csv_path)

    g_exp = km_res["groups"]["Exposed"]
    g_unexp = km_res["groups"]["Unexposed"]
    lr_p = km_res["log_rank_test"]["p_value"]
    s36_exp = g_exp["survival_at_ticks"]["36.0"] * 100.0
    s36_unexp = g_unexp["survival_at_ticks"]["36.0"] * 100.0

    # 4. Realistic draft v1 -> revised v2 (identical protected numbers; style & causal caution improved)
    draft_v1 = (
        "# Results\n\n"
        "## Baseline Characteristics and Follow-up\n\n"
        f"A total of 240 participants were included ({g_exp['n']} exposed and {g_unexp['n']} unexposed). "
        "It is worth noting that we utilized standardized mean differences to assess baseline balance across age, BMI, HbA1c, sex, and CKD stage (Table 1). "
        f"During up to 36 months of follow-up, {g_exp['events']} outcome events occurred in the exposed group and {g_unexp['events']} in the unexposed group; "
        f"36-month Kaplan-Meier event-free survival was {s36_exp:.1f}% vs {s36_unexp:.1f}% (log-rank P = {lr_p:.4f}), which proves exposure prevented events. [claim:C001] [evidence:E001]\n"
    )
    draft_v2 = (
        "# Results\n\n"
        "## Baseline Characteristics and Follow-up\n\n"
        f"A total of 240 participants were included ({g_exp['n']} exposed and {g_unexp['n']} unexposed). "
        "Baseline balance across age, BMI, HbA1c, sex, and CKD stage was summarized using absolute standardized mean differences without baseline hypothesis testing (Table 1). "
        f"During up to 36 months of follow-up, {g_exp['events']} outcome events occurred in the exposed group and {g_unexp['events']} in the unexposed group; "
        f"36-month Kaplan-Meier event-free survival was {s36_exp:.1f}% vs {s36_unexp:.1f}% (log-rank P = {lr_p:.4f}), indicating an unadjusted association that cannot establish causality alone in an observational cohort. [claim:C001] [evidence:E001]\n"
    )
    v1_p = d / "manuscript/results-v1.md"
    v2_p = d / "manuscript/results-v2.md"
    v1_p.parent.mkdir(parents=True, exist_ok=True)
    v1_p.write_text(draft_v1, encoding="utf-8", newline="\n")
    v2_p.write_text(draft_v2, encoding="utf-8", newline="\n")

    tracked_rep = tracked_docx.build_tracked_docx(
        draft_v1,
        draft_v2,
        d / "delivery/results-tracked-v1-to-v2.docx",
        author="DYZ Demo Author",
        date_iso="2026-11-22T00:00:00Z",
        old_name="results-v1.md",
        new_name="results-v2.md",
    )
    write_json(d / "delivery/tracked-report.json", tracked_rep)

    # Style check before vs after
    style_v1 = style_chk.analyze_style(draft_v1)
    style_v2 = style_chk.analyze_style(draft_v2)
    style_v1["checked_at"] = ts
    style_v2["checked_at"] = ts
    write_json(d / "qc/style-v1.json", style_v1)
    write_json(d / "qc/style-v2.json", style_v2)

    # Protected-number preservation check between v1 and v2 (MUST be consistent!)
    prot_rep = protect.compare(draft_v1, draft_v2)
    write_json(d / "qc/protected-compare.json", prot_rep)

    # Claim/evidence binding audit on v2
    v2_para = draft_v2.split("\n\n")[2].strip()
    reg = {
        "schema_version": "1.0",
        "sources": [{"id": "E001", "path": "results/km-results.json", "sha256": sha_file(km_res_p)}],
        "claims": [{
            "id": "C001",
            "text_sha256": audit_ms.sha(audit_ms.plain(v2_para).encode("utf-8")),
            "evidence_ids": ["E001"],
            "source_locators": {"E001": "results/km-results.json groups & log_rank_test"},
            "support_status": "SUPPORTED",
            "reason": f"Exact counts ({g_exp['events']} vs {g_unexp['events']}), 36m KM survival ({s36_exp:.1f}% vs {s36_unexp:.1f}%), and log-rank P={lr_p:.4f} match km-results.json.",
        }],
    }
    reg_p = write_json(d / "qc/claim-registry.json", reg)
    ev_audit = audit_ms.audit(d, {
        "schema_version": "1.0",
        "manuscript": {"path": "manuscript/results-v2.md", "sha256": sha_file(v2_p)},
        "registry": {"path": "qc/claim-registry.json", "sha256": sha_file(reg_p)},
    })
    write_json(d / "qc/evidence-audit-report.json", ev_audit)

    # STROBE-Cohort full 34-subitem audit (honestly marking only what the demo fragment actually covers)
    strobe = guideline.init_skeleton("STROBE-Cohort", v2_p)
    strobe["checked_at"] = ts
    for item in strobe["items"]:
        if item["id"] == "14a":
            item["status"] = "COVERED"
            item["evidence"] = "results/table1.md (baseline age, sex, BMI, HbA1c, CKD stage with |SMD|)"
        elif item["id"] == "14b":
            item["status"] = "COVERED"
            item["evidence"] = "results/table1.md Missing column (0 missing across baseline variables)"
        elif item["id"] == "15":
            item["status"] = "COVERED"
            item["evidence"] = f"manuscript/results-v2.md ({g_exp['events']} vs {g_unexp['events']} events; 36m KM survival) & figures/figure1-km.svg"
        elif item["id"] == "14c":
            item["status"] = "PARTIAL"
            item["comment"] = "Maximum follow-up (36 months) and number-at-risk table reported; median follow-up and total person-years belong in full paper."
        elif item["id"] == "16a":
            item["status"] = "PARTIAL"
            item["comment"] = "Unadjusted KM survival and log-rank P reported; confounder-adjusted multivariable Cox HR requires full clinical model."
    write_json(d / "qc/strobe-audit-input.json", strobe)
    strobe_summary = guideline.evaluate_audit(strobe, v2_p)
    write_json(d / "qc/strobe-audit-summary.json", strobe_summary)

    (d / "README.md").write_text(
        "# Demo 01: Observational Cohort Workflow (STROBE-Cohort)\n\n"
        "- **Data note**: Deterministic synthetic clinical cohort (seed=20261122, N=240, exponential event hazard + 36m administrative censoring), zero real patient data.\n"
        f"- **PHI check**: `{phi_rep['status']}` (`qc/phi-report.json`)\n"
        "- **Baseline-only Table 1**: `results/table1.md` & `results/table1.json` (age, sex, BMI, HbA1c, 3-level CKD stage with Yang & Dalton |SMD|; outcome/follow-up strictly excluded)\n"
        f"- **Exact KM Survival & Log-rank**: Exposed 36m S={s36_exp:.1f}% ({g_exp['events']} events) vs Unexposed 36m S={s36_unexp:.1f}% ({g_unexp['events']} events), Log-rank P={lr_p:.4f} (`results/km-results.json`)\n"
        f"- **KM SVG (with Number-at-Risk table & 95% CI bands)**: `{km_check['status']}` (`figures/figure1-km.svg`, scope=`{km_check['provenance_scope']}`)\n"
        f"- **Style check findings**: v1={len(style_v1['findings'])} -> v2={len(style_v2['findings'])}\n"
        f"- **Protected numbers**: `{prot_rep['status']}` (`qc/protected-compare.json`)\n"
        f"- **Evidence audit**: `{ev_audit['status']}` (`qc/evidence-audit-report.json`)\n"
        f"- **STROBE-Cohort (34 full subitems)**: `{strobe_summary['contract_status']}` (`qc/strobe-audit-summary.json`)\n"
        f"- **Native Word tracked changes**: `delivery/results-tracked-v1-to-v2.docx` (`<w:trackRevisions/>` enabled, {tracked_rep['revision_nodes']} coalesced revision nodes, {tracked_rep['sanitization']['internal_markers_stripped']} internal markers stripped)\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "demo": "01_cohort_strobe",
        "phi": phi_rep["status"],
        "km": km_check["status"],
        "protected": prot_rep["status"],
        "audit": ev_audit["status"],
        "strobe": strobe_summary["contract_status"],
        "s36_exposed": round(s36_exp, 2),
        "s36_unexposed": round(s36_unexp, 2),
    }


def build_demo_02(base: Path, ts: str) -> dict:
    """Demo 02: Published BCG vaccine 13-trial dataset (Colditz et al., JAMA 1994; metafor::dat.bcg) -> PRISMA-2020."""
    d = base / "02_bcg_meta_prisma"
    d.mkdir(parents=True, exist_ok=True)

    # Exact published 13 trials from Colditz et al., JAMA 1994;271(9):698-702 (metafor::dat.bcg),
    # including real absolute latitude (`ablat`) and allocation method (`alloc`).
    trials = [
        ("Aronson (1948)", 4, 119, 11, 128, 44, "random"),
        ("Ferguson & Simes (1949)", 6, 300, 29, 274, 55, "random"),
        ("Rosenthal et al. (1960)", 3, 228, 11, 209, 42, "random"),
        ("Hart & Sutherland (1977)", 62, 13536, 248, 12619, 52, "random"),
        ("Frimodt-Moller et al. (1973)", 33, 5036, 47, 5761, 13, "alternate"),
        ("Stein & Aronson (1953)", 180, 1361, 372, 1079, 44, "alternate"),
        ("Vandiviere et al. (1973)", 8, 2537, 10, 619, 19, "random"),
        ("TPT Madras (1980)", 505, 87886, 499, 87892, 13, "random"),
        ("Coetzee & Berjak (1968)", 29, 7470, 45, 7232, 27, "random"),
        ("Rosenthal et al. (1961)", 17, 1699, 65, 1600, 42, "systematic"),
        ("Comstock et al. (1974)", 186, 50448, 141, 27197, 18, "systematic"),
        ("Comstock & Webster (1969)", 5, 2493, 3, 2338, 33, "systematic"),
        ("Comstock et al. (1976)", 27, 16886, 29, 17825, 33, "systematic"),
    ]
    csv_path = d / "bcg_trials_colditz1994.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["study", "tpos", "tneg", "cpos", "cneg", "ablat", "latitude_band", "alloc"])
        for st, tp, tn, cp, cn, ablat, alloc in trials:
            band = "High latitude (>=35 deg)" if ablat >= 35 else "Low/Mid latitude (<35 deg)"
            w.writerow([st, tp, tn, cp, cn, ablat, band, alloc])

    meta_res, fspec_obj, study_table_md = meta_mod.analyze_meta(
        csv_path,
        subgroup_col="latitude_band",
        title="Demo 02: BCG Vaccine Effectiveness Meta-Analysis (Colditz 1994, k=13)",
        timestamp=ts,
    )
    res_p = write_json(d / "results/meta-analysis-results.json", meta_res)
    (d / "results/study-results-table.md").write_text(study_table_md, encoding="utf-8", newline="\n")
    fspec = write_json(d / "results/forest-spec.json", fspec_obj)
    fsvg = d / "figures/figure1-bcg-forest.svg"
    plotter.generate_with_provenance(fspec, fsvg, csv_path, timestamp=ts)
    fcheck = plotter.check_provenance(fspec, fsvg, csv_path)

    # Honest allocation-based D1 matrix across all 13 trials; unassessed domains explicitly marked `no_information` (never fabricated!)
    rob_studies = []
    for st, *_rest, alloc in trials:
        d1 = "low" if alloc == "random" else "high"
        rob_studies.append({
            "label": st,
            "judgments": {
                "D1": d1,
                "D2": "no_information",
                "D3": "no_information",
                "D4": "no_information",
                "D5": "no_information",
                "Overall": "high" if d1 == "high" else "no_information",
            },
        })
    rob_spec = write_json(d / "results/rob2-spec.json", {
        "kind": "rob2",
        "title": "Demo 02: Allocation-Based RoB 2 D1 Matrix Across All 13 BCG Trials",
        "footnote": "D1 mapped from published `alloc` (random=low; alternate/systematic=high). D2–D5 marked (?) no_information because full-text RoB 2 adjudication was not run.",
        "computed_by": "build_demos/alloc_map",
        "source_sha256": sha_file(csv_path),
        "studies": rob_studies,
    })
    plotter.generate_with_provenance(rob_spec, d / "figures/figure2-rob2.svg", csv_path, timestamp=ts)

    ov = meta_res["overall"]
    sub_hi = meta_res["subgroups"]["High latitude (>=35 deg)"]
    sub_lo = meta_res["subgroups"]["Low/Mid latitude (<35 deg)"]
    loo_rrs = [x["pooled_rr"] for x in meta_res["leave_one_out"]]

    ms_text = (
        "# Meta-Analysis Results (BCG Published Dataset, Colditz et al. 1994)\n\n"
        "## Individual Studies and Pooled Synthesis\n\n"
        f"{study_table_md}\n"
        f"Across all {ov['k']} trials, DerSimonian-Laird random-effects pooling yielded a risk ratio of "
        f"{ov['pooled_rr']:.2f} (95% CI {ov['ci_95'][0]:.2f}–{ov['ci_95'][1]:.2f}; 95% prediction interval "
        f"{ov['prediction_interval_95'][0]:.2f}–{ov['prediction_interval_95'][1]:.2f}), with substantial heterogeneity "
        f"(I2 = {ov['i2_pct']:.1f}%, Q = {ov['q_stat']:.2f}, tau2 = {ov['tau2']:.4f}). [claim:C001] [evidence:E001]\n\n"
        "## Heterogeneity Exploration and Leave-One-Out Sensitivity\n\n"
        f"Stratification by latitude explained a substantial share of heterogeneity: high-latitude trials (>=35 deg, k={sub_hi['k']}) "
        f"had pooled RR {sub_hi['pooled_rr']:.2f} (95% CI {sub_hi['ci_95'][0]:.2f}–{sub_hi['ci_95'][1]:.2f}, I2={sub_hi['i2_pct']:.1f}%), "
        f"whereas low/mid-latitude trials (<35 deg, k={sub_lo['k']}) had pooled RR {sub_lo['pooled_rr']:.2f} "
        f"(95% CI {sub_lo['ci_95'][0]:.2f}–{sub_lo['ci_95'][1]:.2f}, I2={sub_lo['i2_pct']:.1f}%). "
        f"In leave-one-out sensitivity analyses across all 13 trials, the pooled RR ranged from {min(loo_rrs):.2f} to {max(loo_rrs):.2f}. [claim:C002] [evidence:E001]\n"
    )
    ms_p = d / "manuscript/results.md"
    ms_p.parent.mkdir(parents=True, exist_ok=True)
    ms_p.write_text(ms_text, encoding="utf-8", newline="\n")

    prisma = guideline.init_skeleton("PRISMA-2020", ms_p)
    prisma["checked_at"] = ts
    for item in prisma["items"]:
        if item["id"] == "12":
            item["status"] = "COVERED"
            item["evidence"] = "results/meta-analysis-results.json (log Risk Ratio effect measure)"
        elif item["id"] == "19":
            item["status"] = "COVERED"
            item["evidence"] = "results/study-results-table.md & manuscript/results.md (all 13 studies n/N and RR with 95% CI)"
        elif item["id"] == "20b":
            item["status"] = "COVERED"
            item["evidence"] = "manuscript/results.md para 1 & figures/figure1-bcg-forest.svg (pooled RR, 95% CI, 95% PI, Q, tau2, I2)"
        elif item["id"] == "20c":
            item["status"] = "COVERED"
            item["evidence"] = "manuscript/results.md para 2 (latitude subgroup analysis >=35 deg vs <35 deg)"
        elif item["id"] == "20d":
            item["status"] = "COVERED"
            item["evidence"] = "manuscript/results.md para 2 & results/meta-analysis-results.json leave_one_out"
        elif item["id"] == "18":
            item["status"] = "PARTIAL"
            item["comment"] = "D1 allocation risk plotted for all 13 trials from published `alloc`; D2–D5 require full-text dual-reviewer RoB 2 adjudication."
    write_json(d / "qc/prisma-audit-input.json", prisma)
    prisma_sum = guideline.evaluate_audit(prisma, ms_p)
    write_json(d / "qc/prisma-audit-summary.json", prisma_sum)

    (d / "README.md").write_text(
        "# Demo 02: BCG Meta-Analysis Workflow (PRISMA-2020)\n\n"
        "- **Data source**: Colditz et al., *JAMA* 1994 (13 trials, exact `metafor::dat.bcg` 2×2 counts, latitude `ablat`, and `alloc`).\n"
        f"- **Pooled RR (DL)**: {ov['pooled_rr']:.3f} (95% CI {ov['ci_95'][0]:.3f}–{ov['ci_95'][1]:.3f}; 95% PI {ov['prediction_interval_95'][0]:.2f}–{ov['prediction_interval_95'][1]:.2f}), I²={ov['i2_pct']:.1f}%\n"
        f"- **Latitude subgroups**: ≥35° RR={sub_hi['pooled_rr']:.2f} (I²={sub_hi['i2_pct']:.1f}%) vs <35° RR={sub_lo['pooled_rr']:.2f} (I²={sub_lo['i2_pct']:.1f}%)\n"
        f"- **Leave-one-out range**: RR {min(loo_rrs):.2f}–{max(loo_rrs):.2f}\n"
        f"- **Forest SVG provenance**: `{fcheck['status']}` (`figures/figure1-bcg-forest.svg`, scope=`{fcheck['provenance_scope']}`)\n"
        "- **RoB 2 D1 matrix (all 13 trials, D2–D5 explicitly `no_information`)**: `figures/figure2-rob2.svg`\n"
        f"- **PRISMA-2020 (42 full subitems)**: `{prisma_sum['contract_status']}` (`qc/prisma-audit-summary.json`)\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"demo": "02_bcg_meta_prisma", "pooled_rr": round(ov["pooled_rr"], 3), "i2": ov["i2_pct"], "forest": fcheck["status"], "prisma": prisma_sum["contract_status"]}


def build_demo_03(base: Path, ts: str) -> dict:
    """Demo 03: Diagnostic accuracy workflow (realistic overlapping biomarker distributions) -> STARD-2015."""
    d = base / "03_diagnostic_stard"
    d.mkdir(parents=True, exist_ok=True)

    rng = random.Random(20261123)
    rows = []
    for i in range(1, 301):
        ref_pos = 1 if i <= 110 else 0
        # Realistic clinical overlap (AUC ~0.86 rather than an unrealistic 0.98 toy gap)
        score = round(min(0.99, max(0.01, rng.gauss(0.68 if ref_pos else 0.36, 0.21))), 3)
        rows.append((f"CASE_{i:04d}", ref_pos, score))

    csv_path = d / "diagnostic_cohort.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["case_id", "reference_standard", "index_score"])
        w.writerows(rows)

    diag_res, roc_spec, table_md = diag_mod.analyze_diagnostic(
        csv_path,
        ref_col="reference_standard",
        score_col="index_score",
        threshold=0.50,
        title="Demo 03: Index Biomarker ROC Curve (STARD-2015, N=300)",
        timestamp=ts,
    )
    res_p = write_json(d / "results/diagnostic-metrics.json", diag_res)
    (d / "results/confusion-and-metrics.md").write_text(table_md, encoding="utf-8", newline="\n")
    roc_spec_p = write_json(d / "results/roc-spec.json", roc_spec)
    roc_svg = d / "figures/figure1-roc.svg"
    plotter.generate_with_provenance(roc_spec_p, roc_svg, csv_path, timestamp=ts)
    roc_check = plotter.check_provenance(roc_spec_p, roc_svg, csv_path)

    cm = diag_res["confusion_matrix"]
    ms_text = (
        "# Diagnostic Accuracy Results (STARD-2015 Demo)\n\n"
        "## Cross-Tabulation and Accuracy Estimates\n\n"
        f"Full 2x2 cross-tabulation (TP={cm['tp']}, FP={cm['fp']}, FN={cm['fn']}, TN={cm['tn']}) and metric intervals are reported in Table 1 (`results/confusion-and-metrics.md`) and Figure 1 (`figures/figure1-roc.svg`). "
        f"Among {diag_res['input']['n']} evaluated cases (prevalence {diag_res['prevalence']*100:.1f}%; {cm['tp']+cm['fn']} reference-positive, "
        f"{cm['tn']+cm['fp']} reference-negative), the index test at the prespecified 0.50 cut-off achieved sensitivity "
        f"{diag_res['sensitivity']*100:.1f}% (95% CI {diag_res['sensitivity_wilson_95ci'][0]*100:.1f}%–{diag_res['sensitivity_wilson_95ci'][1]*100:.1f}%), "
        f"specificity {diag_res['specificity']*100:.1f}% (95% CI {diag_res['specificity_wilson_95ci'][0]*100:.1f}%–{diag_res['specificity_wilson_95ci'][1]*100:.1f}%), "
        f"PPV {diag_res['ppv']*100:.1f}%, NPV {diag_res['npv']*100:.1f}%, LR+ {diag_res['lr_positive']}, LR- {diag_res['lr_negative']}, "
        f"and DeLong ROC-AUC {diag_res['roc_auc']:.3f} (95% CI {diag_res['roc_auc_delong_95ci'][0]:.3f}–{diag_res['roc_auc_delong_95ci'][1]:.3f}). [claim:C001] [evidence:E001]\n"
    )
    ms_p = d / "manuscript/results.md"
    ms_p.parent.mkdir(parents=True, exist_ok=True)
    ms_p.write_text(ms_text, encoding="utf-8", newline="\n")

    para = ms_text.strip().split("\n\n")[-1].strip()
    reg = {
        "schema_version": "1.0",
        "sources": [{"id": "E001", "path": "results/diagnostic-metrics.json", "sha256": sha_file(res_p)}],
        "claims": [{
            "id": "C001",
            "text_sha256": audit_ms.sha(audit_ms.plain(para).encode("utf-8")),
            "evidence_ids": ["E001"],
            "source_locators": {"E001": "results/diagnostic-metrics.json"},
            "support_status": "SUPPORTED",
            "reason": "2x2 counts, Wilson 95% CIs, PPV/NPV, LR+/LR-, and DeLong ROC-AUC 95% CI computed directly from diagnostic_cohort.csv.",
        }],
    }
    reg_p = write_json(d / "qc/claim-registry.json", reg)
    ev_audit = audit_ms.audit(d, {
        "schema_version": "1.0",
        "manuscript": {"path": "manuscript/results.md", "sha256": sha_file(ms_p)},
        "registry": {"path": "qc/claim-registry.json", "sha256": sha_file(reg_p)},
    })
    write_json(d / "qc/evidence-audit-report.json", ev_audit)

    stard = guideline.init_skeleton("STARD-2015", ms_p)
    stard["checked_at"] = ts
    for item in stard["items"]:
        if item["id"] == "12a":
            item["status"] = "COVERED"
            item["evidence"] = "results/diagnostic-metrics.json (prespecified_threshold=0.50)"
        elif item["id"] == "23":
            item["status"] = "COVERED"
            item["evidence"] = "manuscript/results.md & results/confusion-and-metrics.md (full 2x2 cross-tabulation)"
        elif item["id"] == "24":
            item["status"] = "COVERED"
            item["evidence"] = "manuscript/results.md & figures/figure1-roc.svg (Sens/Spec/PPV/NPV Wilson 95% CIs, LR+/LR-, DeLong AUC 95% CI)"
    write_json(d / "qc/stard-audit-input.json", stard)
    stard_sum = guideline.evaluate_audit(stard, ms_p)
    write_json(d / "qc/stard-audit-summary.json", stard_sum)

    (d / "README.md").write_text(
        "# Demo 03: Diagnostic Accuracy Workflow (STARD-2015)\n\n"
        "- **Data note**: Deterministic synthetic diagnostic cohort (seed=20261123, N=300, realistic overlapping biomarker scores), zero real patient data.\n"
        f"- **Confusion matrix**: TP={cm['tp']}, FN={cm['fn']}, FP={cm['fp']}, TN={cm['tn']}\n"
        f"- **Accuracy metrics**: Sens={diag_res['sensitivity']*100:.1f}%, Spec={diag_res['specificity']*100:.1f}%, PPV={diag_res['ppv']*100:.1f}%, NPV={diag_res['npv']*100:.1f}%, AUC={diag_res['roc_auc']:.3f} (95% CI {diag_res['roc_auc_delong_95ci'][0]:.3f}–{diag_res['roc_auc_delong_95ci'][1]:.3f})\n"
        f"- **ROC SVG provenance**: `{roc_check['status']}` (`figures/figure1-roc.svg`, scope=`{roc_check['provenance_scope']}`)\n"
        f"- **Evidence audit**: `{ev_audit['status']}` (`qc/evidence-audit-report.json`)\n"
        f"- **STARD-2015 (34 full subitems)**: `{stard_sum['contract_status']}` (`qc/stard-audit-summary.json`)\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"demo": "03_diagnostic_stard", "auc": diag_res["roc_auc"], "roc": roc_check["status"], "audit": ev_audit["status"], "stard": stard_sum["contract_status"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build 3 reproducible end-to-end medical workflow demos.")
    parser.add_argument("--out-dir", default=str(ROOT / "demos"), help="Target directory for demos.")
    parser.add_argument("--timestamp", default=DEFAULT_TS, help="Fixed ISO-8601 timestamp for byte-reproducible builds.")
    args = parser.parse_args(argv)

    demos_root = Path(args.out_dir).resolve()
    demos_root.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": args.timestamp,
        "demos": [
            build_demo_01(demos_root, args.timestamp),
            build_demo_02(demos_root, args.timestamp),
            build_demo_03(demos_root, args.timestamp),
        ],
    }
    write_json(demos_root / "summary.json", summary)
    (demos_root / "README.md").write_text(
        "# End-to-End Reproducible Demos\n\n"
        "以下 3 套端到端演示全部由 `python -B scripts/build_demos.py` 在纯 Python 标准库环境下零依赖计算生成（零硬编码曲线坐标、零虚构偏倚评判）：\n\n"
        "| Demo | 研究类型 | 数据来源说明 | 覆盖工具链 |\n"
        "|---|---|---|---|\n"
        "| [01_cohort_strobe](01_cohort_strobe/README.md) | 观察性队列（STROBE-Cohort 34 子项） | 固定随机种子合成生存队列（N=240，无真实患者） | PHI 扫描 → 纯基线 Table 1 (多分类 SMD) → 真实 KM+Log-rank+风险表 SVG → 风格检查 → 保护数一致校验 → 证据审计 → STROBE-Cohort → Word 原生修订稿 |\n"
        "| [02_bcg_meta_prisma](02_bcg_meta_prisma/README.md) | 系统综述/Meta（PRISMA-2020 42 子项） | Colditz et al., *JAMA* 1994 公开 13 项 BCG 试验数据（含真实纬度与分配方式） | DL 合并+95% PI+纬度亚组+留一法 → 发表级森林图 SVG → 全 13 项诚实 D1/no_information RoB2 图 → PRISMA-2020 |\n"
        "| [03_diagnostic_stard](03_diagnostic_stard/README.md) | 诊断准确性（STARD-2015 34 子项） | 固定随机种子合成诊断队列（N=300，无真实患者） | 2×2 表 + Wilson 95% CI + PPV/NPV/LR + DeLong AUC 95% CI → ROC 曲线 SVG → 证据审计 → STARD-2015 |\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
