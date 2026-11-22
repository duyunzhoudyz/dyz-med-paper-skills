#!/usr/bin/env python3
"""Exact Kaplan-Meier survival estimator, Greenwood 95% CI, Number-at-Risk table, and 2-group Log-rank test.

Pure Python stdlib; strictly read-only on input CSV. Directly emits both a structured results JSON
and a plot_clinical_svg.py-compatible `km` figure spec so survival plots are 100% computed from data.
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


def km_curve(records: list[tuple[float, int]]) -> list[dict]:
    """Compute exact product-limit S(t) and Greenwood 95% CI."""
    if not records:
        return []
    times = sorted({t for t, _ in records})
    n_total = len(records)
    surv = 1.0
    greenwood_sum = 0.0
    points = [{"t": 0.0, "s": 1.0, "ci_low": 1.0, "ci_high": 1.0, "at_risk": n_total, "events": 0, "censored": 0}]

    for t in times:
        n_risk = sum(1 for ti, _ in records if ti >= t)
        d = sum(1 for ti, ev in records if ti == t and ev == 1)
        c = sum(1 for ti, ev in records if ti == t and ev == 0)
        if d > 0 and n_risk > 0:
            surv *= (1.0 - d / n_risk)
            if n_risk > d:
                greenwood_sum += d / (n_risk * (n_risk - d))
        se = surv * math.sqrt(greenwood_sum) if surv > 0 else 0.0
        lo = max(0.0, surv - 1.959963984540054 * se)
        hi = min(1.0, surv + 1.959963984540054 * se)
        points.append({
            "t": round(t, 4),
            "s": round(surv, 6),
            "ci_low": round(lo, 6),
            "ci_high": round(hi, 6),
            "at_risk": n_risk,
            "events": d,
            "censored": c,
        })
    return points


def survival_at(points: list[dict], t_query: float) -> float:
    val = 1.0
    for p in points:
        if p["t"] <= t_query:
            val = p["s"]
        else:
            break
    return val


def log_rank_two_group(rec_a: list[tuple[float, int]], rec_b: list[tuple[float, int]]) -> dict | None:
    """Mantel-Haenszel two-sample log-rank test (exact 1-df chi-square via erfc)."""
    if not rec_a or not rec_b:
        return None
    event_times = sorted({t for t, ev in rec_a + rec_b if ev == 1})
    obs_a, exp_a, var_a = 0.0, 0.0, 0.0
    for t in event_times:
        n1 = sum(1 for ti, _ in rec_a if ti >= t)
        n2 = sum(1 for ti, _ in rec_b if ti >= t)
        d1 = sum(1 for ti, ev in rec_a if ti == t and ev == 1)
        d2 = sum(1 for ti, ev in rec_b if ti == t and ev == 1)
        n = n1 + n2
        d = d1 + d2
        if n <= 1 or d == 0:
            continue
        e1 = d * (n1 / n)
        v1 = (n1 * n2 * d * (n - d)) / (n * n * (n - 1))
        obs_a += d1
        exp_a += e1
        var_a += v1
    if var_a <= 0:
        return None
    chi2 = ((obs_a - exp_a) ** 2) / var_a
    # For 1 df chi-square, P(X >= chi2) = erfc(sqrt(chi2 / 2))
    p_val = math.erfc(math.sqrt(chi2 / 2.0))
    return {"chi2": round(chi2, 4), "df": 1, "p_value": round(p_val, 6), "observed_group0": int(obs_a), "expected_group0": round(exp_a, 3)}


def analyze_survival(
    input_path: Path,
    group_col: str,
    time_col: str,
    event_col: str,
    risk_ticks: list[float] | None = None,
    title: str = "Kaplan-Meier Survival Curve",
    xlabel: str = "Follow-up Time",
    ylabel: str = "Survival Probability",
    timestamp: str | None = None,
) -> tuple[dict, dict]:
    raw = input_path.read_bytes()
    delimiter = "\t" if input_path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter=delimiter)
    for req in (group_col, time_col, event_col):
        if not reader.fieldnames or req not in reader.fieldnames:
            raise ValueError(f"缺少必要列: {req!r}")

    by_group: dict[str, list[tuple[float, int]]] = {}
    excluded = 0
    for row in reader:
        g = (row.get(group_col) or "").strip()
        try:
            t = float((row.get(time_col) or "").strip())
            ev = int(float((row.get(event_col) or "").strip()))
        except ValueError:
            excluded += 1
            continue
        if not g or not math.isfinite(t) or t < 0 or ev not in (0, 1):
            excluded += 1
            continue
        by_group.setdefault(g, []).append((t, ev))

    groups = sorted(by_group.keys())
    if not groups:
        raise ValueError("无有效生存分析记录")

    max_t = max(t for recs in by_group.values() for t, _ in recs)
    if not risk_ticks:
        step = max(1.0, round(max_t / 4.0))
        risk_ticks = [round(step * i, 2) for i in range(5) if step * i <= max_t + 1e-6]
        if risk_ticks[-1] < max_t:
            risk_ticks.append(round(max_t, 2))

    curves_spec = []
    group_summary = {}
    for g in groups:
        recs = by_group[g]
        pts = km_curve(recs)
        n_risk_table = [sum(1 for t, _ in recs if t >= tick) for tick in risk_ticks]
        events_total = sum(ev for _, ev in recs)
        # Median survival (first time S(t) <= 0.5)
        med = next((p["t"] for p in pts if p["s"] <= 0.5), None)
        group_summary[g] = {
            "n": len(recs),
            "events": events_total,
            "censored": len(recs) - events_total,
            "median_survival": med,
            "survival_at_ticks": {str(tick): round(survival_at(pts, tick), 4) for tick in risk_ticks},
            "number_at_risk": {str(tick): cnt for tick, cnt in zip(risk_ticks, n_risk_table)},
        }
        curves_spec.append({
            "label": f"{g} (n={len(recs)}, events={events_total})",
            "short_label": g,
            "points": pts,
            "at_risk": n_risk_table,
        })

    lr = log_rank_two_group(by_group[groups[0]], by_group[groups[1]]) if len(groups) == 2 else None
    p_annot = f"Log-rank P = {lr['p_value']:.4f}" if lr and lr["p_value"] >= 0.0001 else ("Log-rank P < 0.0001" if lr else "")

    results = {
        "tool": "km_survival/1.0",
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "input": {"path": input_path.name, "sha256": sha_bytes(raw), "excluded_invalid_rows": excluded},
        "columns": {"group": group_col, "time": time_col, "event": event_col},
        "risk_ticks": risk_ticks,
        "groups": group_summary,
        "log_rank_test": lr,
    }
    km_spec = {
        "kind": "km",
        "title": title,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "risk_ticks": risk_ticks,
        "annotation": p_annot,
        "curves": curves_spec,
        "computed_by": "km_survival/1.0",
        "source_sha256": sha_bytes(raw),
    }
    return results, km_spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute exact Kaplan-Meier estimates, risk table, Log-rank test, and SVG figure spec.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--time", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--ticks", help="Comma-separated risk table time points (e.g. 0,12,24,36).")
    parser.add_argument("--title", default="Kaplan-Meier Survival Curve")
    parser.add_argument("--xlabel", default="Follow-up Time")
    parser.add_argument("--out-results", required=True)
    parser.add_argument("--out-spec", required=True)
    parser.add_argument("--timestamp")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        inp = ensure_plain_path(Path(args.input))
        out_r = ensure_plain_path(Path(args.out_results))
        out_s = ensure_plain_path(Path(args.out_spec))
        if not inp.is_file():
            raise ValueError(f"输入文件不存在: {inp}")
        if inp in (out_r, out_s) or out_r == out_s:
            raise ValueError("输出路径冲突")
        for p in (out_r, out_s):
            if p.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {p}")

        ticks = [float(x) for x in args.ticks.split(",") if x.strip()] if args.ticks else None
        results, spec = analyze_survival(inp, args.group, args.time, args.event, ticks, args.title, args.xlabel, timestamp=args.timestamp)
        out_r.parent.mkdir(parents=True, exist_ok=True)
        out_s.parent.mkdir(parents=True, exist_ok=True)
        out_r.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        out_s.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": "ok", "groups": list(results["groups"].keys()), "log_rank_p": (results["log_rank_test"] or {}).get("p_value")}, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
