#!/usr/bin/env python3
"""Deterministic diagnostic accuracy analyzer: 2x2 table, Wilson 95% CI, PPV/NPV, LR+/LR-, ROC curve & DeLong 95% CI.

Pure Python stdlib; strictly read-only on input CSV. Directly emits results JSON, 2x2 Markdown table,
and a plot_clinical_svg.py-compatible `roc` figure spec.
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


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    if n <= 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def delong_auc_ci(pos_scores: list[float], neg_scores: list[float]) -> tuple[float, list[float]]:
    """Exact empirical AUC and DeLong (1988) structural-components 95% CI."""
    m, n = len(pos_scores), len(neg_scores)
    if m < 2 or n < 2:
        raise ValueError("计算 AUC 与 DeLong 95% CI 需要至少 2 例阳性与 2 例阴性")
    v10 = [sum(1.0 if ps > ns else (0.5 if ps == ns else 0.0) for ns in neg_scores) / n for ps in pos_scores]
    v01 = [sum(1.0 if ps > ns else (0.5 if ps == ns else 0.0) for ps in pos_scores) / m for ns in neg_scores]
    auc = sum(v10) / m
    s10 = sum((x - auc) ** 2 for x in v10) / (m - 1)
    s01 = sum((y - auc) ** 2 for y in v01) / (n - 1)
    var = s10 / m + s01 / n
    se = math.sqrt(max(0.0, var))
    z = 1.959963984540054
    return round(auc, 4), [round(max(0.0, auc - z * se), 4), round(min(1.0, auc + z * se), 4)]


def compute_roc_points(records: list[tuple[int, float]]) -> list[dict]:
    pos_total = sum(1 for r, _ in records if r == 1)
    neg_total = len(records) - pos_total
    thresholds = sorted({s for _, s in records}, reverse=True)
    pts = [{"fpr": 0.0, "tpr": 0.0}]
    for th in thresholds:
        tp = sum(1 for r, s in records if r == 1 and s >= th)
        fp = sum(1 for r, s in records if r == 0 and s >= th)
        pts.append({"fpr": round(fp / neg_total, 4), "tpr": round(tp / pos_total, 4)})
    if pts[-1] != {"fpr": 1.0, "tpr": 1.0}:
        pts.append({"fpr": 1.0, "tpr": 1.0})
    return pts


def analyze_diagnostic(
    input_path: Path,
    ref_col: str,
    score_col: str,
    threshold: float = 0.50,
    title: str = "Receiver Operating Characteristic (ROC) Curve",
    timestamp: str | None = None,
) -> tuple[dict, dict, str]:
    raw = input_path.read_bytes()
    delimiter = "\t" if input_path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=delimiter)
    for req in (ref_col, score_col):
        if not reader.fieldnames or req not in reader.fieldnames:
            raise ValueError(f"缺少必要列: {req!r}")

    records: list[tuple[int, float]] = []
    excluded = 0
    for row in reader:
        try:
            ref = int(float((row.get(ref_col) or "").strip()))
            sc = float((row.get(score_col) or "").strip())
        except ValueError:
            excluded += 1
            continue
        if ref not in (0, 1) or not math.isfinite(sc):
            excluded += 1
            continue
        records.append((ref, sc))

    tp = sum(1 for r, s in records if r == 1 and s >= threshold)
    fn = sum(1 for r, s in records if r == 1 and s < threshold)
    fp = sum(1 for r, s in records if r == 0 and s >= threshold)
    tn = sum(1 for r, s in records if r == 0 and s < threshold)

    pos_n, neg_n = tp + fn, tn + fp
    sens = tp / pos_n if pos_n else 0.0
    spec = tn / neg_n if neg_n else 0.0
    ppv = tp / (tp + fp) if (tp + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    lr_pos = round(sens / (1.0 - spec), 3) if spec < 1.0 else None
    lr_neg = round((1.0 - sens) / spec, 3) if spec > 0.0 else None

    pos_scores = [s for r, s in records if r == 1]
    neg_scores = [s for r, s in records if r == 0]
    auc, auc_ci = delong_auc_ci(pos_scores, neg_scores)
    roc_pts = compute_roc_points(records)

    results = {
        "tool": "diagnostic_accuracy/1.0",
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "input": {"path": input_path.name, "sha256": sha_bytes(raw), "n": len(records), "excluded_invalid_rows": excluded},
        "prespecified_threshold": threshold,
        "prevalence": round(pos_n / len(records), 4) if records else 0.0,
        "confusion_matrix": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "sensitivity": round(sens, 4),
        "sensitivity_wilson_95ci": wilson_ci(tp, pos_n),
        "specificity": round(spec, 4),
        "specificity_wilson_95ci": wilson_ci(tn, neg_n),
        "ppv": round(ppv, 4),
        "ppv_wilson_95ci": wilson_ci(tp, tp + fp),
        "npv": round(npv, 4),
        "npv_wilson_95ci": wilson_ci(tn, tn + fn),
        "lr_positive": lr_pos,
        "lr_negative": lr_neg,
        "roc_auc": auc,
        "roc_auc_delong_95ci": auc_ci,
    }
    roc_spec = {
        "kind": "roc",
        "title": title,
        "auc": auc,
        "auc_ci": auc_ci,
        "operating_point": {"fpr": round(1.0 - spec, 4), "tpr": round(sens, 4), "label": f"Cut-off ≥ {threshold:.2f} (Sens {sens*100:.1f}%, Spec {spec*100:.1f}%)"},
        "points": roc_pts,
        "computed_by": "diagnostic_accuracy/1.0",
        "source_sha256": sha_bytes(raw),
    }

    md = (
        "| Index Test (Cut-off ≥ " + f"{threshold:.2f}" + ") | Reference Positive | Reference Negative | Total |\n"
        "| --- | --- | --- | --- |\n"
        f"| Positive | {tp} (TP) | {fp} (FP) | {tp + fp} |\n"
        f"| Negative | {fn} (FN) | {tn} (TN) | {fn + tn} |\n"
        f"| **Total** | **{pos_n}** | **{neg_n}** | **{len(records)}** |\n\n"
        "| Metric | Estimate (95% CI) |\n"
        "| --- | --- |\n"
        f"| Sensitivity | {sens*100:.1f}% ({results['sensitivity_wilson_95ci'][0]*100:.1f}%–{results['sensitivity_wilson_95ci'][1]*100:.1f}%) |\n"
        f"| Specificity | {spec*100:.1f}% ({results['specificity_wilson_95ci'][0]*100:.1f}%–{results['specificity_wilson_95ci'][1]*100:.1f}%) |\n"
        f"| PPV | {ppv*100:.1f}% ({results['ppv_wilson_95ci'][0]*100:.1f}%–{results['ppv_wilson_95ci'][1]*100:.1f}%) |\n"
        f"| NPV | {npv*100:.1f}% ({results['npv_wilson_95ci'][0]*100:.1f}%–{results['npv_wilson_95ci'][1]*100:.1f}%) |\n"
        f"| LR+ / LR- | {lr_pos} / {lr_neg} |\n"
        f"| ROC-AUC (DeLong) | {auc:.3f} ({auc_ci[0]:.3f}–{auc_ci[1]:.3f}) |\n"
    )
    return results, roc_spec, md


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute diagnostic accuracy 2x2 metrics, Wilson/DeLong 95% CIs, and ROC spec.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--ref-col", required=True)
    parser.add_argument("--score-col", required=True)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--title", default="ROC Curve")
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

        results, spec, md = analyze_diagnostic(inp, args.ref_col, args.score_col, args.threshold, args.title, args.timestamp)
        out_r.parent.mkdir(parents=True, exist_ok=True)
        out_s.parent.mkdir(parents=True, exist_ok=True)
        out_r.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        out_s.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if out_t is not None:
            out_t.parent.mkdir(parents=True, exist_ok=True)
            out_t.write_text(md, encoding="utf-8", newline="\n")
        print(json.dumps({"status": "ok", "n": results["input"]["n"], "auc": results["roc_auc"]}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
