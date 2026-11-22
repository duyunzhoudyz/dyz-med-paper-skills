#!/usr/bin/env python3
"""Deterministic binary-outcome random-effects meta-analysis (DerSimonian-Laird log Risk Ratio).

Pure Python stdlib; strictly read-only on input CSV (columns: study, tpos, tneg, cpos, cneg; optional subgroup).
Features:
  - Automatic 0.5 continuity correction for studies with zero cells (recorded transparently).
  - Exact DerSimonian-Laird pooled RR, 95% CI, Cochran's Q, tau^2, I^2, and 95% Prediction Interval (k >= 3).
  - Leave-one-out sensitivity analysis for every study.
  - Optional subgroup stratification (e.g., latitude band for Colditz 1994 BCG dataset).
  - Emits results JSON, individual-study Markdown table, and a plot_clinical_svg.py-compatible `forest` spec.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import sys

# Two-sided t critical values (alpha=0.05) for df = k - 2 in 95% Prediction Interval.
T_CRIT_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
    9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    20: 2.086, 25: 2.060, 30: 2.042,
}


def t_crit_95(df: int) -> float:
    if df <= 0:
        return 1.959963984540054
    if df in T_CRIT_95:
        return T_CRIT_95[df]
    if df > 30:
        return 1.959963984540054 + 2.4 / df
    keys = sorted(T_CRIT_95.keys())
    for lo, hi in zip(keys, keys[1:]):
        if lo < df < hi:
            return T_CRIT_95[lo] + (T_CRIT_95[hi] - T_CRIT_95[lo]) * (df - lo) / (hi - lo)
    return 1.959963984540054


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ensure_plain_path(path: Path) -> Path:
    abs_p = Path(os.path.abspath(path.expanduser()))
    for part in (abs_p, *abs_p.parents):
        try:
            attrs = getattr(part.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            attrs = 0
        if part.is_symlink() or (attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
            raise ValueError(f"拒绝符号链接或重定向路径: {part}")
    return abs_p.resolve()


def pool_dl(studies: list[dict]) -> dict:
    k = len(studies)
    if k == 0:
        raise ValueError("研究列表为空")
    yi = [s["log_rr"] for s in studies]
    vi = [s["var_log_rr"] for s in studies]
    w_fe = [1.0 / v for v in vi]
    sum_w = sum(w_fe)
    mu_fe = sum(w * y for w, y in zip(w_fe, yi)) / sum_w
    q = sum(w * (y - mu_fe) ** 2 for w, y in zip(w_fe, yi))
    df = k - 1
    if df > 0:
        c_denom = sum_w - sum(w ** 2 for w in w_fe) / sum_w
        tau2 = max(0.0, (q - df) / c_denom) if c_denom > 0 else 0.0
        i2 = max(0.0, (q - df) / q * 100.0) if q > 0 else 0.0
    else:
        tau2, i2 = 0.0, 0.0

    w_re = [1.0 / (v + tau2) for v in vi]
    sum_wre = sum(w_re)
    mu_re = sum(w * y for w, y in zip(w_re, yi)) / sum_wre
    se_re = math.sqrt(1.0 / sum_wre)
    weights_pct = [round(100.0 * w / sum_wre, 2) for w in w_re]

    pi_95 = None
    if k >= 3:
        t_val = t_crit_95(k - 2)
        pi_se = math.sqrt(tau2 + se_re ** 2)
        pi_95 = [round(math.exp(mu_re - t_val * pi_se), 3), round(math.exp(mu_re + t_val * pi_se), 3)]

    return {
        "k": k,
        "pooled_rr": round(math.exp(mu_re), 4),
        "ci_95": [round(math.exp(mu_re - 1.959963984540054 * se_re), 4), round(math.exp(mu_re + 1.959963984540054 * se_re), 4)],
        "prediction_interval_95": pi_95,
        "q_stat": round(q, 2),
        "df": df,
        "tau2": round(tau2, 4),
        "i2_pct": round(i2, 1),
        "weights_pct": weights_pct,
    }


def analyze_meta(
    input_path: Path,
    subgroup_col: str | None = None,
    title: str = "Random-Effects Meta-Analysis (Risk Ratio)",
    timestamp: str | None = None,
) -> tuple[dict, dict, str]:
    raw = input_path.read_bytes()
    delimiter = "\t" if input_path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=delimiter)
    for req in ("study", "tpos", "tneg", "cpos", "cneg"):
        if not reader.fieldnames or req not in reader.fieldnames:
            raise ValueError(f"缺少必要列: {req!r}")

    studies: list[dict] = []
    for row in reader:
        label = (row["study"] or "").strip()
        tp, tn, cp, cn = int(row["tpos"]), int(row["tneg"]), int(row["cpos"]), int(row["cneg"])
        corr = 0.5 if min(tp, tn, cp, cn) == 0 else 0.0
        tp_c, tn_c, cp_c, cn_c = tp + corr, tn + corr, cp + corr, cn + corr
        nt_c, nc_c = tp_c + tn_c, cp_c + cn_c
        rr = (tp_c / nt_c) / (cp_c / nc_c)
        lrr = math.log(rr)
        var = (1.0 / tp_c - 1.0 / nt_c) + (1.0 / cp_c - 1.0 / nc_c)
        se = math.sqrt(var)
        entry = {
            "study": label,
            "tpos": tp,
            "ttotal": tp + tn,
            "cpos": cp,
            "ctotal": cp + cn,
            "continuity_corrected": bool(corr),
            "rr": round(rr, 4),
            "ci_low": round(math.exp(lrr - 1.959963984540054 * se), 4),
            "ci_high": round(math.exp(lrr + 1.959963984540054 * se), 4),
            "log_rr": lrr,
            "var_log_rr": var,
        }
        if subgroup_col and subgroup_col in reader.fieldnames:
            entry["subgroup"] = (row.get(subgroup_col) or "").strip()
        studies.append(entry)

    overall = pool_dl(studies)
    for st, wp in zip(studies, overall["weights_pct"]):
        st["weight_pct"] = wp

    # Leave-one-out sensitivity analysis
    loo = []
    if len(studies) >= 3:
        for idx, omitted in enumerate(studies):
            sub = [s for j, s in enumerate(studies) if j != idx]
            p = pool_dl(sub)
            loo.append({
                "omitted_study": omitted["study"],
                "pooled_rr": p["pooled_rr"],
                "ci_95": p["ci_95"],
                "i2_pct": p["i2_pct"],
            })

    # Optional subgroup analysis
    subgroups = {}
    if subgroup_col and any(s.get("subgroup") for s in studies):
        groups = sorted({s["subgroup"] for s in studies if s.get("subgroup")})
        for g in groups:
            sub_studies = [s for s in studies if s.get("subgroup") == g]
            subgroups[g] = pool_dl(sub_studies)

    clean_studies = [
        {k: v for k, v in s.items() if k not in ("log_rr", "var_log_rr")}
        for s in studies
    ]
    results = {
        "tool": "meta_analysis/1.0",
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "input": {"path": input_path.name, "sha256": sha_bytes(raw), "k": len(studies)},
        "model": "DerSimonian-Laird random-effects (log Risk Ratio)",
        "overall": {k: v for k, v in overall.items() if k != "weights_pct"},
        "studies": clean_studies,
        "subgroups": subgroups,
        "leave_one_out": loo,
    }

    forest_items = [
        {
            "label": s["study"],
            "events_t": f"{s['tpos']}/{s['ttotal']}",
            "events_c": f"{s['cpos']}/{s['ctotal']}",
            "weight": s["weight_pct"],
            "estimate": s["rr"],
            "ci_low": s["ci_low"],
            "ci_high": s["ci_high"],
        }
        for s in clean_studies
    ]
    forest_items.append({
        "label": "Random-Effects Pooled (DL)",
        "events_t": f"{sum(s['tpos'] for s in clean_studies)}/{sum(s['ttotal'] for s in clean_studies)}",
        "events_c": f"{sum(s['cpos'] for s in clean_studies)}/{sum(s['ctotal'] for s in clean_studies)}",
        "weight": 100.0,
        "estimate": overall["pooled_rr"],
        "ci_low": overall["ci_95"][0],
        "ci_high": overall["ci_95"][1],
        "pooled": True,
    })
    pi_txt = f"; 95% PI {overall['prediction_interval_95'][0]:.2f}–{overall['prediction_interval_95'][1]:.2f}" if overall["prediction_interval_95"] else ""
    forest_spec = {
        "kind": "forest",
        "scale": "log",
        "null_value": 1.0,
        "title": title,
        "xlabel": "Risk Ratio (95% CI, log scale)",
        "favours_left": "Favours Treatment",
        "favours_right": "Favours Control",
        "footnote": f"Heterogeneity: Q = {overall['q_stat']:.2f} (df = {overall['df']}), tau² = {overall['tau2']:.4f}, I² = {overall['i2_pct']:.1f}%{pi_txt}",
        "items": forest_items,
        "computed_by": "meta_analysis/1.0",
        "source_sha256": sha_bytes(raw),
    }

    md_lines = [
        "| Study | Treatment (n/N) | Control (n/N) | Weight (%) | Risk Ratio (95% CI) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in clean_studies:
        md_lines.append(f"| {s['study']} | {s['tpos']}/{s['ttotal']} | {s['cpos']}/{s['ctotal']} | {s['weight_pct']:.1f}% | {s['rr']:.2f} ({s['ci_low']:.2f}–{s['ci_high']:.2f}) |")
    md_lines.append(
        f"| **Random-Effects Pooled (DL)** | **{sum(s['tpos'] for s in clean_studies)}/{sum(s['ttotal'] for s in clean_studies)}** | "
        f"**{sum(s['cpos'] for s in clean_studies)}/{sum(s['ctotal'] for s in clean_studies)}** | **100.0%** | "
        f"**{overall['pooled_rr']:.2f} ({overall['ci_95'][0]:.2f}–{overall['ci_95'][1]:.2f})** |"
    )
    return results, forest_spec, "\n".join(md_lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DerSimonian-Laird binary meta-analysis with subgroups, leave-one-out, and forest spec.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--subgroup-col")
    parser.add_argument("--title", default="Random-Effects Meta-Analysis (Risk Ratio)")
    parser.add_argument("--out-results", required=True)
    parser.add_argument("--out-spec", required=True)
    parser.add_argument("--out-table")
    parser.add_argument("--timestamp")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        inp = ensure_plain_path(Path(args.input))
        out_r = ensure_plain_path(Path(args.out_results))
        out_s = ensure_plain_path(Path(args.out_spec))
        out_t = ensure_plain_path(Path(args.out_table)) if args.out_table else None
        if not inp.is_file():
            raise ValueError(f"输入文件不存在: {inp}")
        outputs = [p for p in (out_r, out_s, out_t) if p is not None]
        if inp in outputs or len(set(outputs)) != len(outputs):
            raise ValueError("输出路径冲突")
        for p in outputs:
            if p.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {p}")

        results, spec, md = analyze_meta(inp, args.subgroup_col, args.title, args.timestamp)
        out_r.parent.mkdir(parents=True, exist_ok=True)
        out_s.parent.mkdir(parents=True, exist_ok=True)
        out_r.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        out_s.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if out_t is not None:
            out_t.parent.mkdir(parents=True, exist_ok=True)
            out_t.write_text(md, encoding="utf-8", newline="\n")
        print(json.dumps({"status": "ok", "k": results["input"]["k"], "pooled_rr": results["overall"]["pooled_rr"], "i2_pct": results["overall"]["i2_pct"]}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
