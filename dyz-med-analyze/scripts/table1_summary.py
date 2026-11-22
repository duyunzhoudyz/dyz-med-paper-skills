#!/usr/bin/env python3
"""Deterministic, stdlib-only Table 1 baseline summary generator (with Yang & Dalton multicategory SMD).

Designed for clinical cohort / RCT baseline reporting in dyz-med-analyze.
- Original data file is strictly read-only; refuses silent overwrites without --force.
- Unifies missing-value tokens across continuous and categorical variables.
- Excludes rows with missing group assignment from the analytical Overall column (reporting excluded count explicitly)
  so Overall N == sum(group n) always reconciles.
- Computes |SMD| (absolute Standardized Mean Difference) for two-group balance assessment:
    * Continuous: |mean1 - mean2| / sqrt((sd1^2 + sd2^2) / 2)
    * Binary categorical: |p1 - p2| / sqrt((p1(1-p1) + p2(1-p2)) / 2)
    * Multi-category (>=3 levels): Yang & Dalton (2012) multivariate Mahalanobis distance sqrt((T-C)' S^-1 (T-C))
      with Tikhonov ridge protection for near-singular cells.
- Emits Markdown table, CSV table, and machine-readable results JSON with input SHA-256 provenance.
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

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", ".", "-", "missing"}


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


def is_missing(val: str | None) -> bool:
    return (val or "").strip().lower() in MISSING_TOKENS


def clean_cat(val: str | None) -> str | None:
    if is_missing(val):
        return None
    return (val or "").strip()


def parse_float(val: str | None) -> float | None:
    if is_missing(val):
        return None
    try:
        v = float((val or "").strip())
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return math.nan
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def mean_sd(vals: list[float]) -> tuple[float, float]:
    n = len(vals)
    if n == 0:
        return math.nan, math.nan
    m = sum(vals) / n
    if n < 2:
        return m, 0.0
    var = sum((x - m) ** 2 for x in vals) / (n - 1)
    return m, math.sqrt(var)


def smd_continuous(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, sda = mean_sd(a)
    mb, sdb = mean_sd(b)
    pooled = math.sqrt((sda ** 2 + sdb ** 2) / 2.0)
    if pooled == 0:
        return 0.0
    return abs(ma - mb) / pooled


def smd_binary(p1: float, p2: float) -> float | None:
    denom = math.sqrt((p1 * (1.0 - p1) + p2 * (1.0 - p2)) / 2.0)
    if denom == 0:
        return 0.0
    return abs(p1 - p2) / denom


def _solve_linear(matrix: list[list[float]], rhs: list[float]) -> list[float] | None:
    """Gaussian elimination with partial pivoting for small k x k covariance matrices."""
    k = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv_val = aug[col][col]
        for j in range(col, k + 1):
            aug[col][j] /= piv_val
        for r in range(k):
            if r != col:
                factor = aug[r][col]
                for j in range(col, k + 1):
                    aug[r][j] -= factor * aug[col][j]
    return [aug[i][k] for i in range(k)]


def smd_multicategory(p1_vec: list[float], p2_vec: list[float]) -> float | None:
    """Yang & Dalton (2012) multivariate Mahalanobis SMD for >=3-level nominal categorical variables."""
    if len(p1_vec) <= 1:
        return 0.0
    # Drop the reference category (last element) to keep k-1 linearly independent proportions.
    t = p1_vec[:-1]
    c = p2_vec[:-1]
    k = len(t)
    diff = [t[i] - c[i] for i in range(k)]
    if all(abs(d) < 1e-12 for d in diff):
        return 0.0
    # Pooled covariance matrix S = 0.5 * (Cov(T) + Cov(C))
    s_mat = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            if i == j:
                s_mat[i][j] = 0.5 * (t[i] * (1.0 - t[i]) + c[i] * (1.0 - c[i]))
            else:
                s_mat[i][j] = -0.5 * (t[i] * t[j] + c[i] * c[j])
    sol = _solve_linear(s_mat, diff)
    if sol is None:
        # Small ridge regularization if any category is empty in both arms
        reg = [[s_mat[i][j] + (1e-9 if i == j else 0.0) for j in range(k)] for i in range(k)]
        sol = _solve_linear(reg, diff)
    if sol is None:
        return None
    quad = sum(diff[i] * sol[i] for i in range(k))
    return math.sqrt(max(0.0, quad))


def summarize_table1(
    input_path: Path,
    group_col: str,
    continuous_cols: list[str],
    categorical_cols: list[str],
    decimals: int = 2,
    continuous_style: str = "both",
    timestamp: str | None = None,
) -> dict:
    raw = input_path.read_bytes()
    delimiter = "\t" if input_path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=delimiter)
    if not reader.fieldnames or group_col not in reader.fieldnames:
        raise ValueError(f"分组列 {group_col!r} 不在输入表头中")
    for col in continuous_cols + categorical_cols:
        if col not in reader.fieldnames:
            raise ValueError(f"变量列 {col!r} 不在输入表头中")

    all_rows = list(reader)
    by_group: dict[str, list[dict]] = {}
    missing_group_rows = 0
    for row in all_rows:
        g = clean_cat(row.get(group_col))
        if g is None:
            missing_group_rows += 1
            continue
        by_group.setdefault(g, []).append(row)

    # Sort groups deterministically so SMD/columns do not depend on input row order.
    groups = sorted(by_group.keys())
    valid_rows = [r for g in groups for r in by_group[g]]
    fmt = f"{{:.{decimals}f}}"
    summary_rows: list[dict] = []

    def numeric_stats(vals: list[float]) -> dict:
        if not vals:
            return {"n": 0, "mean": None, "sd": None, "median": None, "q1": None, "q3": None}
        m, sd = mean_sd(vals)
        sv = sorted(vals)
        return {
            "n": len(vals),
            "mean": round(m, decimals + 2),
            "sd": round(sd, decimals + 2),
            "median": round(percentile(sv, 0.5), decimals + 2),
            "q1": round(percentile(sv, 0.25), decimals + 2),
            "q3": round(percentile(sv, 0.75), decimals + 2),
        }

    def fmt_cont(vals: list[float]) -> str:
        if not vals:
            return "NA"
        m, sd = mean_sd(vals)
        sv = sorted(vals)
        med, q1, q3 = percentile(sv, 0.5), percentile(sv, 0.25), percentile(sv, 0.75)
        if continuous_style == "mean_sd":
            return f"{fmt.format(m)} ± {fmt.format(sd)}"
        if continuous_style == "median_iqr":
            return f"{fmt.format(med)} [{fmt.format(q1)}, {fmt.format(q3)}]"
        return f"{fmt.format(m)} ± {fmt.format(sd)} / {fmt.format(med)} [{fmt.format(q1)}, {fmt.format(q3)}]"

    metric_label = {
        "mean_sd": "Mean ± SD",
        "median_iqr": "Median [IQR]",
        "both": "Mean ± SD / Median [IQR]",
    }.get(continuous_style, "Mean ± SD / Median [IQR]")

    for col in continuous_cols:
        all_vals = [v for r in valid_rows if (v := parse_float(r.get(col))) is not None]
        miss_all = len(valid_rows) - len(all_vals)
        grp_vals = {g: [v for r in by_group[g] if (v := parse_float(r.get(col))) is not None] for g in groups}
        miss_by_grp = {g: len(by_group[g]) - len(grp_vals[g]) for g in groups}
        smd = smd_continuous(grp_vals[groups[0]], grp_vals[groups[1]]) if len(groups) == 2 else None

        summary_rows.append({
            "variable": col,
            "type": "continuous",
            "level": metric_label,
            "missing_total": miss_all,
            "missing_by_group": miss_by_grp,
            "overall": fmt_cont(all_vals),
            "groups": {g: fmt_cont(grp_vals[g]) for g in groups},
            "numeric": {
                "overall": numeric_stats(all_vals),
                "groups": {g: numeric_stats(grp_vals[g]) for g in groups},
            },
            "smd": round(smd, 3) if smd is not None else None,
        })

    for col in categorical_cols:
        levels = sorted({v for r in valid_rows if (v := clean_cat(r.get(col))) is not None})
        miss_all = sum(1 for r in valid_rows if clean_cat(r.get(col)) is None)
        miss_by_grp = {g: sum(1 for r in by_group[g] if clean_cat(r.get(col)) is None) for g in groups}
        valid_total = len(valid_rows) - miss_all

        # Compute per-group proportion vector across all levels first.
        grp_valid_counts = {g: len(by_group[g]) - miss_by_grp[g] for g in groups}
        props_by_grp: dict[str, list[float]] = {g: [] for g in groups}
        for lvl in levels:
            for g in groups:
                cnt_g = sum(1 for r in by_group[g] if clean_cat(r.get(col)) == lvl)
                denom_g = grp_valid_counts[g]
                props_by_grp[g].append((cnt_g / denom_g) if denom_g else 0.0)

        var_smd: float | None = None
        if len(groups) == 2 and len(levels) >= 2:
            if len(levels) == 2:
                var_smd = smd_binary(props_by_grp[groups[0]][0], props_by_grp[groups[1]][0])
            else:
                var_smd = smd_multicategory(props_by_grp[groups[0]], props_by_grp[groups[1]])

        for l_idx, lvl in enumerate(levels):
            cnt_all = sum(1 for r in valid_rows if clean_cat(r.get(col)) == lvl)
            pct_all = (100.0 * cnt_all / valid_total) if valid_total else 0.0
            grp_cells = {}
            for g in groups:
                cnt_g = sum(1 for r in by_group[g] if clean_cat(r.get(col)) == lvl)
                grp_cells[g] = f"{cnt_g} ({100.0 * props_by_grp[g][l_idx]:.1f}%)"
            # Report the variable-level |SMD| once on the first level row to avoid duplicate/sign-flipped SMDs.
            summary_rows.append({
                "variable": col,
                "type": "categorical",
                "level": lvl,
                "missing_total": miss_all if l_idx == 0 else 0,
                "missing_by_group": miss_by_grp if l_idx == 0 else {},
                "overall": f"{cnt_all} ({pct_all:.1f}%)",
                "groups": grp_cells,
                "smd": (round(var_smd, 3) if var_smd is not None else None) if l_idx == 0 else None,
            })

    return {
        "tool": "table1_summary/2.0",
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": input_path.name,
            "sha256": sha_bytes(raw),
            "raw_rows": len(all_rows),
            "analyzed_rows": len(valid_rows),
            "excluded_missing_group_rows": missing_group_rows,
        },
        "group_column": group_col,
        "group_order": groups,
        "group_counts": {g: len(by_group[g]) for g in groups},
        "continuous_style": continuous_style,
        "rows": summary_rows,
        "method_note": (
            "两组基线比较默认报告绝对标准化均数差 |SMD|（多分类变量采用 Yang & Dalton 2012 多元马氏距离公式），"
            "不以基线假设检验 P 值替代研究设计或协变量选择；缺失分组行已从 Overall 排除并单列计数。"
        ),
    }


def render_markdown(report: dict) -> str:
    groups = list(report["group_counts"].keys())
    headers = ["Variable", "Level / Metric", f"Overall (N={report['input']['analyzed_rows']})", "Missing"]
    headers += [f"{g} (n={report['group_counts'][g]})" for g in groups]
    if len(groups) == 2:
        headers.append("|SMD|")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in report["rows"]:
        miss_txt = str(r["missing_total"]) if r["missing_by_group"] or r["type"] == "continuous" else ""
        cells = [r["variable"], r["level"], r["overall"], miss_txt]
        cells += [r["groups"].get(g, "") for g in groups]
        if len(groups) == 2:
            cells.append("" if r["smd"] is None else f"{r['smd']:.3f}")
        lines.append("| " + " | ".join(cells) + " |")
    if report["input"]["excluded_missing_group_rows"]:
        lines.append(f"\n*Note: {report['input']['excluded_missing_group_rows']} row(s) with missing `{report['group_column']}` were excluded from Overall and group summaries.*")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate reproducible Table 1 (Markdown + CSV + JSON provenance).")
    parser.add_argument("--input", required=True, help="De-identified CSV/TSV dataset (read-only).")
    parser.add_argument("--group", required=True, help="Grouping column name.")
    parser.add_argument("--continuous", default="", help="Comma-separated continuous variable names.")
    parser.add_argument("--categorical", default="", help="Comma-separated categorical variable names.")
    parser.add_argument("--continuous-style", choices=("both", "mean_sd", "median_iqr"), default="both")
    parser.add_argument("--out-dir", required=True, help="Output directory for table1.md, table1.csv, table1.json.")
    parser.add_argument("--timestamp", help="Optional fixed ISO-8601 timestamp for reproducible builds.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing files in --out-dir.")
    args = parser.parse_args(argv)

    try:
        inp = ensure_plain_path(Path(args.input))
        if not inp.is_file():
            raise ValueError(f"输入文件不存在: {inp}")
        out_dir = ensure_plain_path(Path(args.out_dir))
        targets = [out_dir / name for name in ("table1.md", "table1.json", "table1.csv")]
        if inp in targets:
            raise ValueError("输出文件不能覆盖输入文件")
        for t in targets:
            if t.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {t}")

        cont = [c.strip() for c in args.continuous.split(",") if c.strip()]
        cat = [c.strip() for c in args.categorical.split(",") if c.strip()]
        report = summarize_table1(inp, args.group, cont, cat, continuous_style=args.continuous_style, timestamp=args.timestamp)

        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "table1.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
        (out_dir / "table1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

        groups = list(report["group_counts"].keys())
        fieldnames = ["variable", "level", "overall", "missing_total"] + groups + (["abs_smd"] if len(groups) == 2 else [])
        with (out_dir / "table1.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in report["rows"]:
                row_dict = {"variable": r["variable"], "level": r["level"], "overall": r["overall"], "missing_total": r["missing_total"]}
                for g in groups:
                    row_dict[g] = r["groups"].get(g, "")
                if len(groups) == 2:
                    row_dict["abs_smd"] = "" if r["smd"] is None else f"{r['smd']:.3f}"
                w.writerow(row_dict)

        print(json.dumps({"status": "ok", "out_dir": out_dir.name, "rows": len(report["rows"])}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
