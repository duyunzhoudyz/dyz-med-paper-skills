#!/usr/bin/env python3
"""Publication-ready medical SVG figure generator with cryptographic provenance checking.

Pure Python stdlib (zero matplotlib/R requirement). Supports:
  - forest: Forest plot with weight-scaled squares, Events/Weight% columns, human-readable log/linear ticks,
            clipping arrows, favours labels, and heterogeneity footnote
  - km: Kaplan-Meier step survival curves with 95% CI bands, censoring ticks, top non-overlapping legend,
        Log-rank annotation, and vertically aligned Number-at-Risk table
  - rob2: Risk-of-bias traffic-light matrix with dynamic canvas sizing, explicit `no_information` (?) handling,
          and domain definitions footnote
  - roc: Receiver Operating Characteristic curve with diagonal reference, AUC (95% CI) box, and operating point

Colorblind-safe Okabe-Ito palette and CJK-safe font stack. Writes <output>.provenance.json binding spec SHA-256,
upstream source_data SHA-256, generator/computation metadata, and SVG SHA-256.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from xml.sax.saxutils import escape

FONT_STACK = "Arial, Helvetica, 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif"
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]
ROB_COLORS = {"low": "#009E73", "some_concerns": "#E69F00", "high": "#D55E00", "no_information": "#9CA3AF"}
ROB_SYMBOL = {"low": "+", "some_concerns": "!", "high": "-", "no_information": "?"}
LOG_NICE_TICKS = (0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 4.0, 5.0, 10.0, 20.0)


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


def _text_width_est(text: str, font_px: float = 12.0) -> float:
    wide = sum(1 for ch in text if ord(ch) > 127)
    narrow = len(text) - wide
    return wide * font_px * 1.02 + narrow * font_px * 0.58


def render_forest_svg(spec: dict) -> str:
    items = spec.get("items", [])
    if not items:
        raise ValueError("forest spec 需要非空 items 列表")
    scale = spec.get("scale", "log")
    null_val = float(spec.get("null_value", 1.0 if scale == "log" else 0.0))
    title = str(spec.get("title", "Forest Plot"))
    xlabel = str(spec.get("xlabel", "Effect Estimate (95% CI)"))
    footnote = str(spec.get("footnote", ""))
    fav_l = str(spec.get("favours_left", ""))
    fav_r = str(spec.get("favours_right", ""))

    has_events = any(it.get("events_t") or it.get("events_c") for it in items)
    has_weight = any(it.get("weight") is not None for it in items)

    def xf(v: float) -> float:
        return math.log(v) if scale == "log" else v

    all_vals = [null_val]
    for it in items:
        est, lo, hi = float(it["estimate"]), float(it["ci_low"]), float(it["ci_high"])
        all_vals.extend([est, lo, hi])
    if scale == "log" and min(all_vals) <= 0:
        raise ValueError("对数坐标下效应量与置信区间必须 > 0")

    # Determine nice tick bounds
    if scale == "log":
        min_v, max_v = min(all_vals), max(all_vals)
        # Keep display range readable; clip extreme CI tails with arrows
        disp_lo = max(0.05, min(t for t in LOG_NICE_TICKS if t <= min_v) if any(t <= min_v for t in LOG_NICE_TICKS) else 0.05)
        disp_hi = min(10.0, max(t for t in LOG_NICE_TICKS if t >= max_v) if any(t >= max_v for t in LOG_NICE_TICKS) else 10.0)
        # Ensure sensible bracket around null_val
        disp_lo = min(disp_lo, 0.25 if null_val == 1.0 else null_val / 2.0)
        disp_hi = max(disp_hi, 2.0 if null_val == 1.0 else null_val * 2.0)
        ticks = [t for t in LOG_NICE_TICKS if disp_lo - 1e-9 <= t <= disp_hi + 1e-9]
        if null_val not in ticks:
            ticks = sorted(set(ticks + [null_val]))
        lo_t, hi_t = math.log(disp_lo), math.log(disp_hi)
    else:
        lo_raw, hi_raw = min(all_vals), max(all_vals)
        span = max(hi_raw - lo_raw, 1.0)
        lo_t, hi_t = lo_raw - span * 0.15, hi_raw + span * 0.15
        ticks = sorted(set([round(lo_t + i * (hi_t - lo_t) / 4.0, 2) for i in range(5)] + [null_val]))

    label_col_w = max(210, min(320, int(max(_text_width_est(str(it["label"]), 12) for it in items) + 30)))
    ev_t_x = 20 + label_col_w
    ev_c_x = ev_t_x + (85 if has_events else 0)
    plot_l = ev_c_x + (95 if has_events else 15)
    plot_r = plot_l + 300
    weight_x = plot_r + 22
    est_x = weight_x + (72 if has_weight else 0)
    width = max(int(est_x + 165), int(_text_width_est(title, 16) + 50), int(_text_width_est(footnote, 11) + 50))

    row_h = 30
    top_margin = 76
    bottom_margin = 92 if (footnote or fav_l or fav_r) else 65
    height = top_margin + row_h * len(items) + bottom_margin

    def map_x(v: float) -> float:
        return plot_l + (xf(v) - lo_t) / (hi_t - lo_t) * (plot_r - plot_l)

    null_x = map_x(null_val)
    max_w = max((float(it.get("weight") or 1.0) for it in items if not it.get("pooled")), default=1.0)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{escape(FONT_STACK)}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="20" y="30" font-size="16" font-weight="bold" fill="#111827">{escape(title)}</text>',
        '<text x="20" y="58" font-size="12" font-weight="bold" fill="#374151">Study / Subgroup</text>',
    ]
    if has_events:
        lines.append(f'<text x="{ev_t_x}" y="58" font-size="11" font-weight="bold" fill="#374151">Treat n/N</text>')
        lines.append(f'<text x="{ev_c_x}" y="58" font-size="11" font-weight="bold" fill="#374151">Ctrl n/N</text>')
    if has_weight:
        lines.append(f'<text x="{weight_x}" y="58" font-size="11" font-weight="bold" fill="#374151">Weight</text>')
    lines.append(f'<text x="{est_x}" y="58" font-size="12" font-weight="bold" fill="#374151">Estimate (95% CI)</text>')
    lines.append(f'<line x1="20" y1="66" x2="{width - 20}" y2="66" stroke="#111827" stroke-width="1.2"/>')
    axis_y = height - bottom_margin
    lines.append(f'<line x1="{null_x:.1f}" y1="66" x2="{null_x:.1f}" y2="{axis_y}" stroke="#6B7280" stroke-dasharray="4,4" stroke-width="1.2"/>')

    for idx, it in enumerate(items):
        y = top_margin + idx * row_h + row_h / 2
        est, lo, hi = float(it["estimate"]), float(it["ci_low"]), float(it["ci_high"])
        is_pooled = bool(it.get("pooled", False))
        weight = "bold" if is_pooled else "normal"
        if is_pooled:
            lines.append(f'<line x1="20" y1="{y - row_h / 2:.1f}" x2="{width - 20}" y2="{y - row_h / 2:.1f}" stroke="#E5E7EB" stroke-width="1"/>')
        lines.append(f'<text x="20" y="{y + 4:.1f}" font-size="11.5" font-weight="{weight}" fill="#111827">{escape(str(it["label"]))}</text>')
        if has_events:
            lines.append(f'<text x="{ev_t_x}" y="{y + 4:.1f}" font-size="11" font-weight="{weight}" fill="#374151">{escape(str(it.get("events_t", "")))}</text>')
            lines.append(f'<text x="{ev_c_x}" y="{y + 4:.1f}" font-size="11" font-weight="{weight}" fill="#374151">{escape(str(it.get("events_c", "")))}</text>')

        raw_x_lo, raw_x_est, raw_x_hi = map_x(lo), map_x(est), map_x(hi)
        x_lo = max(plot_l, min(plot_r, raw_x_lo))
        x_hi = max(plot_l, min(plot_r, raw_x_hi))
        x_est = max(plot_l, min(plot_r, raw_x_est))

        if is_pooled:
            pts = f"{x_lo:.1f},{y:.1f} {x_est:.1f},{y - 7:.1f} {x_hi:.1f},{y:.1f} {x_est:.1f},{y + 7:.1f}"
            lines.append(f'<polygon points="{pts}" fill="#D55E00" stroke="#111827" stroke-width="1"/>')
        else:
            lines.append(f'<line x1="{x_lo:.1f}" y1="{y:.1f}" x2="{x_hi:.1f}" y2="{y:.1f}" stroke="#0072B2" stroke-width="1.8"/>')
            # Clipping arrows when CI exceeds axis bounds
            if raw_x_lo < plot_l:
                lines.append(f'<polygon points="{plot_l},{y:.1f} {plot_l + 6},{y - 3.5:.1f} {plot_l + 6},{y + 3.5:.1f}" fill="#0072B2"/>')
            if raw_x_hi > plot_r:
                lines.append(f'<polygon points="{plot_r},{y:.1f} {plot_r - 6},{y - 3.5:.1f} {plot_r - 6},{y + 3.5:.1f}" fill="#0072B2"/>')
            w_ratio = float(it.get("weight") or 1.0) / max(max_w, 1e-6)
            sq = max(5.0, min(13.0, 5.0 + 8.0 * math.sqrt(max(0.0, w_ratio))))
            lines.append(f'<rect x="{x_est - sq / 2:.1f}" y="{y - sq / 2:.1f}" width="{sq:.1f}" height="{sq:.1f}" fill="#0072B2"/>')

        if has_weight:
            w_val = it.get("weight")
            w_str = f"{float(w_val):.1f}%" if w_val is not None else ""
            lines.append(f'<text x="{weight_x}" y="{y + 4:.1f}" font-size="11" font-weight="{weight}" fill="#374151">{escape(w_str)}</text>')
        stat_txt = f"{est:.2f} ({lo:.2f}–{hi:.2f})"
        lines.append(f'<text x="{est_x}" y="{y + 4:.1f}" font-size="11.5" font-weight="{weight}" fill="#111827">{escape(stat_txt)}</text>')

    lines.append(f'<line x1="{plot_l}" y1="{axis_y}" x2="{plot_r}" y2="{axis_y}" stroke="#111827" stroke-width="1.2"/>')
    for tv in ticks:
        tx = map_x(tv)
        if tx < plot_l - 2 or tx > plot_r + 2:
            continue
        lines.append(f'<line x1="{tx:.1f}" y1="{axis_y}" x2="{tx:.1f}" y2="{axis_y + 5}" stroke="#111827" stroke-width="1"/>')
        lbl = f"{tv:g}"
        lines.append(f'<text x="{tx:.1f}" y="{axis_y + 19}" font-size="10.5" text-anchor="middle" fill="#374151">{lbl}</text>')
    lines.append(f'<text x="{(plot_l + plot_r) / 2:.1f}" y="{axis_y + 38}" font-size="11.5" font-weight="bold" text-anchor="middle" fill="#111827">{escape(xlabel)}</text>')
    if fav_l:
        lines.append(f'<text x="{plot_l}" y="{axis_y + 54}" font-size="10.5" fill="#4B5563">← {escape(fav_l)}</text>')
    if fav_r:
        lines.append(f'<text x="{plot_r}" y="{axis_y + 54}" font-size="10.5" text-anchor="end" fill="#4B5563">{escape(fav_r)} →</text>')
    if footnote:
        lines.append(f'<text x="20" y="{height - 14}" font-size="10.5" fill="#374151">{escape(footnote)}</text>')
    lines.append("</svg>\n")
    return "\n".join(lines)


def render_km_svg(spec: dict) -> str:
    curves = spec.get("curves", [])
    if not curves:
        raise ValueError("km spec 需要非空 curves 列表")
    title = str(spec.get("title", "Kaplan-Meier Survival Curve"))
    xlabel = str(spec.get("xlabel", "Follow-up Time"))
    ylabel = str(spec.get("ylabel", "Survival Probability"))
    annotation = str(spec.get("annotation", ""))
    max_t = max(float(p["t"]) for c in curves for p in c["points"])
    max_t = max(max_t, 1.0)
    risk_ticks = [float(x) for x in (spec.get("risk_ticks") or [])]
    if not risk_ticks:
        step = max(1.0, round(max_t / 4.0))
        risk_ticks = [round(step * i, 2) for i in range(5) if step * i <= max_t + 1e-6]
        if risk_ticks[-1] < max_t:
            risk_ticks.append(round(max_t, 2))
    has_risk_table = any(c.get("at_risk") for c in curves)

    width = 800
    pl, pr = 115, 750
    pt = 88  # Leave clean top strip for title + non-overlapping horizontal legend
    pb = 370
    risk_h = (32 + 22 * len(curves)) if has_risk_table else 0
    height = pb + 60 + risk_h

    def mx(t: float) -> float:
        return pl + (t / max_t) * (pr - pl)

    def my(s: float) -> float:
        return pb - max(0.0, min(1.0, s)) * (pb - pt)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{escape(FONT_STACK)}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="20" y="30" font-size="16" font-weight="bold" fill="#111827">{escape(title)}</text>',
    ]

    # Top horizontal legend (outside plot area so it NEVER overlaps survival curves)
    leg_x = pl
    for c_idx, curve in enumerate(curves):
        color = PALETTE[c_idx % len(PALETTE)]
        lbl = str(curve["label"])
        lines.append(f'<line x1="{leg_x:.1f}" y1="58" x2="{leg_x + 22:.1f}" y2="58" stroke="{color}" stroke-width="2.6"/>')
        lines.append(f'<text x="{leg_x + 28:.1f}" y="62" font-size="11.5" fill="#111827">{escape(lbl)}</text>')
        leg_x += _text_width_est(lbl, 11.5) + 52

    # Gridlines & axes
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        yy = my(tick)
        if tick > 0:
            lines.append(f'<line x1="{pl}" y1="{yy:.1f}" x2="{pr}" y2="{yy:.1f}" stroke="#F3F4F6" stroke-width="1"/>')
        lines.append(f'<line x1="{pl - 5}" y1="{yy:.1f}" x2="{pl}" y2="{yy:.1f}" stroke="#111827"/>')
        lines.append(f'<text x="{pl - 10}" y="{yy + 4:.1f}" font-size="11" text-anchor="end" fill="#374151">{tick:.2f}</text>')

    lines.append(f'<line x1="{pl}" y1="{pt}" x2="{pl}" y2="{pb}" stroke="#111827" stroke-width="1.3"/>')
    lines.append(f'<line x1="{pl}" y1="{pb}" x2="{pr}" y2="{pb}" stroke="#111827" stroke-width="1.3"/>')

    for tv in risk_ticks:
        xx = mx(tv)
        lines.append(f'<line x1="{xx:.1f}" y1="{pb}" x2="{xx:.1f}" y2="{pb + 5}" stroke="#111827"/>')
        lines.append(f'<text x="{xx:.1f}" y="{pb + 20}" font-size="11" text-anchor="middle" fill="#374151">{tv:g}</text>')

    # Optional 95% CI bands first, then step curves + censoring ticks
    for c_idx, curve in enumerate(curves):
        color = PALETTE[c_idx % len(PALETTE)]
        pts = sorted(curve["points"], key=lambda p: float(p["t"]))
        if all("ci_low" in p and "ci_high" in p for p in pts) and len(pts) >= 2:
            upper_cmds = [f"{mx(float(pts[0]['t'])):.1f},{my(float(pts[0]['ci_high'])):.1f}"]
            for prev, curr in zip(pts, pts[1:]):
                upper_cmds.append(f"{mx(float(curr['t'])):.1f},{my(float(prev['ci_high'])):.1f}")
                upper_cmds.append(f"{mx(float(curr['t'])):.1f},{my(float(curr['ci_high'])):.1f}")
            lower_cmds = []
            for prev, curr in reversed(list(zip(pts, pts[1:]))):
                lower_cmds.append(f"{mx(float(curr['t'])):.1f},{my(float(curr['ci_low'])):.1f}")
                lower_cmds.append(f"{mx(float(curr['t'])):.1f},{my(float(prev['ci_low'])):.1f}")
            lower_cmds.append(f"{mx(float(pts[0]['t'])):.1f},{my(float(pts[0]['ci_low'])):.1f}")
            poly_pts = " ".join(upper_cmds + lower_cmds)
            lines.append(f'<polygon points="{poly_pts}" fill="{color}" fill-opacity="0.12"/>')

    for c_idx, curve in enumerate(curves):
        color = PALETTE[c_idx % len(PALETTE)]
        pts = sorted(curve["points"], key=lambda p: float(p["t"]))
        path_cmds = [f'M {mx(float(pts[0]["t"])):.1f} {my(float(pts[0]["s"])):.1f}']
        for prev, curr in zip(pts, pts[1:]):
            path_cmds.append(f'L {mx(float(curr["t"])):.1f} {my(float(prev["s"])):.1f}')
            path_cmds.append(f'L {mx(float(curr["t"])):.1f} {my(float(curr["s"])):.1f}')
        lines.append(f'<path d="{" ".join(path_cmds)}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        for p in pts:
            if p.get("censored"):
                cx, cy = mx(float(p["t"])), my(float(p["s"]))
                lines.append(f'<line x1="{cx:.1f}" y1="{cy - 4:.1f}" x2="{cx:.1f}" y2="{cy + 4:.1f}" stroke="{color}" stroke-width="1.5"/>')

    if annotation:
        lines.append(f'<text x="{pl + 12}" y="{pb - 14}" font-size="11.5" font-weight="bold" fill="#111827">{escape(annotation)}</text>')

    lines.append(f'<text x="{(pl + pr) / 2:.1f}" y="{pb + 42}" font-size="12" font-weight="bold" text-anchor="middle" fill="#111827">{escape(xlabel)}</text>')
    lines.append(f'<text x="24" y="{(pt + pb) / 2:.1f}" font-size="12" font-weight="bold" text-anchor="middle" fill="#111827" transform="rotate(-90 24 {(pt + pb) / 2:.1f})">{escape(ylabel)}</text>')

    # Vertically aligned Number-at-Risk table
    if has_risk_table:
        rt_top = pb + 64
        lines.append(f'<text x="20" y="{rt_top}" font-size="11.5" font-weight="bold" fill="#111827">Number at risk</text>')
        for c_idx, curve in enumerate(curves):
            ry = rt_top + 22 * (c_idx + 1)
            color = PALETTE[c_idx % len(PALETTE)]
            sname = str(curve.get("short_label") or curve["label"])[:14]
            lines.append(f'<text x="20" y="{ry}" font-size="11" font-weight="bold" fill="{color}">{escape(sname)}</text>')
            counts = curve.get("at_risk") or []
            for tv, cnt in zip(risk_ticks, counts):
                lines.append(f'<text x="{mx(tv):.1f}" y="{ry}" font-size="11" text-anchor="middle" fill="#374151">{cnt}</text>')

    lines.append("</svg>\n")
    return "\n".join(lines)


def render_rob2_svg(spec: dict) -> str:
    studies = spec.get("studies", [])
    domains = spec.get("domains", ["D1", "D2", "D3", "D4", "D5", "Overall"])
    if not studies:
        raise ValueError("rob2 spec 需要非空 studies 列表")
    title = str(spec.get("title", "Risk of Bias (RoB 2) Traffic-Light Plot"))
    domain_footnote = str(spec.get("footnote", "Domains: D1 Randomization; D2 Deviations; D3 Missing data; D4 Measurement; D5 Selection."))

    left = max(200, int(max(_text_width_est(str(st["label"]), 12) for st in studies) + 34))
    cell = 46
    top = 78
    min_w = left + len(domains) * cell + 36
    width = max(min_w, int(_text_width_est(title, 15) + 48), int(_text_width_est(domain_footnote, 10.5) + 48))
    height = top + len(studies) * cell + 78

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{escape(FONT_STACK)}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="20" y="30" font-size="15" font-weight="bold" fill="#111827">{escape(title)}</text>',
    ]
    for d_idx, dom in enumerate(domains):
        cx = left + d_idx * cell + cell / 2
        lines.append(f'<text x="{cx:.1f}" y="{top - 12}" font-size="11.5" font-weight="bold" text-anchor="middle" fill="#374151">{escape(dom)}</text>')
    for s_idx, st in enumerate(studies):
        cy = top + s_idx * cell + cell / 2
        lines.append(f'<text x="20" y="{cy + 4:.1f}" font-size="11.5" fill="#111827">{escape(str(st["label"]))}</text>')
        judgments = st.get("judgments") or {}
        for d_idx, dom in enumerate(domains):
            cx = left + d_idx * cell + cell / 2
            # Never fabricate "some_concerns" for missing domain judgments: explicitly mark no_information (?).
            val = str(judgments.get(dom, "no_information")).lower()
            color = ROB_COLORS.get(val, "#9CA3AF")
            sym = ROB_SYMBOL.get(val, "?")
            lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="{color}"/>')
            lines.append(f'<text x="{cx:.1f}" y="{cy + 5:.1f}" font-size="13.5" font-weight="bold" text-anchor="middle" fill="#FFFFFF">{sym}</text>')
    lines.append(f'<text x="20" y="{height - 36}" font-size="11" fill="#374151">Legend: (+) Low risk   (!) Some concerns   (-) High risk   (?) No information / not assessed</text>')
    lines.append(f'<text x="20" y="{height - 16}" font-size="10.5" fill="#4B5563">{escape(domain_footnote)}</text>')
    lines.append("</svg>\n")
    return "\n".join(lines)


def render_roc_svg(spec: dict) -> str:
    points = spec.get("points", [])
    if len(points) < 2:
        raise ValueError("roc spec 需要至少 2 个 (fpr, tpr) 坐标点")
    title = str(spec.get("title", "ROC Curve"))
    auc = spec.get("auc")
    auc_ci = spec.get("auc_ci")
    op = spec.get("operating_point")

    width, height = 620, 560
    pl, pr, pt, pb = 82, 562, 62, 482

    def mx(v: float) -> float:
        return pl + max(0.0, min(1.0, v)) * (pr - pl)

    def my(v: float) -> float:
        return pb - max(0.0, min(1.0, v)) * (pb - pt)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{escape(FONT_STACK)}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="20" y="30" font-size="15.5" font-weight="bold" fill="#111827">{escape(title)}</text>',
    ]
    for tick in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        xx, yy = mx(tick), my(tick)
        lines.append(f'<line x1="{pl}" y1="{yy:.1f}" x2="{pr}" y2="{yy:.1f}" stroke="#F3F4F6"/>')
        lines.append(f'<line x1="{xx:.1f}" y1="{pt}" x2="{xx:.1f}" y2="{pb}" stroke="#F3F4F6"/>')
        lines.append(f'<text x="{pl - 10}" y="{yy + 4:.1f}" font-size="11" text-anchor="end" fill="#374151">{tick:.1f}</text>')
        lines.append(f'<text x="{xx:.1f}" y="{pb + 20}" font-size="11" text-anchor="middle" fill="#374151">{tick:.1f}</text>')

    lines.append(f'<rect x="{pl}" y="{pt}" width="{pr - pl}" height="{pb - pt}" fill="none" stroke="#111827" stroke-width="1.3"/>')
    lines.append(f'<line x1="{pl}" y1="{pb}" x2="{pr}" y2="{pt}" stroke="#9CA3AF" stroke-dasharray="5,5" stroke-width="1.2"/>')

    pts_sorted = sorted(points, key=lambda p: (float(p["fpr"]), float(p["tpr"])))
    path_d = " ".join(
        f'{"M" if i == 0 else "L"} {mx(float(p["fpr"])):.1f} {my(float(p["tpr"])):.1f}'
        for i, p in enumerate(pts_sorted)
    )
    lines.append(f'<path d="{path_d}" fill="none" stroke="#0072B2" stroke-width="2.4"/>')

    if isinstance(op, dict) and "fpr" in op and "tpr" in op:
        ox, oy = mx(float(op["fpr"])), my(float(op["tpr"]))
        lines.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="5.5" fill="#D55E00" stroke="#FFFFFF" stroke-width="1.5"/>')
        if op.get("label"):
            lines.append(f'<text x="{min(ox + 10, pr - 210):.1f}" y="{max(oy + 18, pt + 22):.1f}" font-size="11" fill="#D55E00" font-weight="bold">{escape(str(op["label"]))}</text>')

    if auc is not None:
        auc_txt = f"AUC = {float(auc):.3f}" + (f" (95% CI {float(auc_ci[0]):.3f}–{float(auc_ci[1]):.3f})" if auc_ci else "")
        lines.append(f'<rect x="{pr - 255}" y="{pb - 48}" width="242" height="34" rx="4" fill="#F9FAFB" stroke="#D1D5DB"/>')
        lines.append(f'<text x="{pr - 134}" y="{pb - 27}" font-size="11.5" font-weight="bold" text-anchor="middle" fill="#111827">{escape(auc_txt)}</text>')

    lines.append(f'<text x="{(pl + pr) / 2:.1f}" y="{pb + 48}" font-size="12" font-weight="bold" text-anchor="middle" fill="#111827">1 − Specificity (False Positive Rate)</text>')
    lines.append(f'<text x="24" y="{(pt + pb) / 2:.1f}" font-size="12" font-weight="bold" text-anchor="middle" fill="#111827" transform="rotate(-90 24 {(pt + pb) / 2:.1f})">Sensitivity (True Positive Rate)</text>')
    lines.append("</svg>\n")
    return "\n".join(lines)


def generate_with_provenance(spec_path: Path, output_path: Path, source_data_path: Path | None = None, timestamp: str | None = None) -> dict:
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8-sig"))
    kind = spec.get("kind")
    if kind == "forest":
        svg = render_forest_svg(spec)
    elif kind == "km":
        svg = render_km_svg(spec)
    elif kind == "rob2":
        svg = render_rob2_svg(spec)
    elif kind == "roc":
        svg = render_roc_svg(spec)
    else:
        raise ValueError(f"不支持的图形类型: {kind!r}（仅支持 forest / km / rob2 / roc）")

    svg_bytes = svg.encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(svg_bytes)

    src_hash = sha_bytes(source_data_path.read_bytes()) if source_data_path and source_data_path.is_file() else None
    spec_src_hash = spec.get("source_sha256")
    if src_hash and spec_src_hash and src_hash != spec_src_hash:
        raise ValueError("spec 中声明的 source_sha256 与传入 --source-data 不一致，拒绝生成伪溯源图形")

    prov = {
        "tool": "plot_clinical_svg/2.0",
        "generated_at": timestamp or datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "computed_by": spec.get("computed_by", "unverified_manual_spec"),
        "spec": {"path": spec_path.name, "sha256": sha_bytes(spec_bytes)},
        "source_data": {"path": source_data_path.name, "sha256": src_hash} if src_hash and source_data_path else None,
        "output": {"path": output_path.name, "sha256": sha_bytes(svg_bytes)},
        "provenance_scope": (
            "hash_and_computation_bound" if (spec.get("computed_by") and src_hash and spec_src_hash == src_hash)
            else "file_hash_only_not_formula_verified"
        ),
    }
    prov_path = output_path.with_suffix(output_path.suffix + ".provenance.json")
    prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return prov


def check_provenance(spec_path: Path, output_path: Path, source_data_path: Path | None = None) -> dict:
    prov_path = output_path.with_suffix(output_path.suffix + ".provenance.json")
    issues: list[str] = []
    if not prov_path.is_file() or not output_path.is_file():
        return {"status": "failed", "issues": ["MISSING_OUTPUT_OR_PROVENANCE"]}
    prov = json.loads(prov_path.read_text(encoding="utf-8-sig"))
    if sha_bytes(spec_path.read_bytes()) != prov.get("spec", {}).get("sha256"):
        issues.append("SPEC_HASH_MISMATCH")
    if sha_bytes(output_path.read_bytes()) != prov.get("output", {}).get("sha256"):
        issues.append("OUTPUT_SVG_HASH_MISMATCH")
    if prov.get("source_data"):
        if not source_data_path or not source_data_path.is_file():
            issues.append("SOURCE_DATA_MISSING")
        elif sha_bytes(source_data_path.read_bytes()) != prov["source_data"].get("sha256"):
            issues.append("SOURCE_DATA_HASH_MISMATCH")
    return {"status": "consistent" if not issues else "stale", "provenance_scope": prov.get("provenance_scope"), "issues": issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify provenance-bound publication clinical SVG plots.")
    parser.add_argument("--spec", required=True, help="JSON figure spec (kind: forest | km | rob2 | roc).")
    parser.add_argument("--output", required=True, help="Output .svg file path.")
    parser.add_argument("--source-data", help="Optional upstream results CSV/JSON to bind in provenance.")
    parser.add_argument("--check", action="store_true", help="Verify existing SVG against spec/source provenance.")
    parser.add_argument("--timestamp", help="Optional fixed ISO-8601 timestamp.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing --output.")
    args = parser.parse_args(argv)

    try:
        spec_p = ensure_plain_path(Path(args.spec))
        out_p = ensure_plain_path(Path(args.output))
        src_p = ensure_plain_path(Path(args.source_data)) if args.source_data else None
        if args.check:
            res = check_provenance(spec_p, out_p, src_p)
            print(json.dumps(res, ensure_ascii=False))
            return 0 if res["status"] == "consistent" else 1
        if not spec_p.is_file():
            raise ValueError(f"spec 文件不存在: {spec_p}")
        if out_p in (spec_p, src_p):
            raise ValueError("--output 不能覆盖输入文件")
        if out_p.exists() and not args.force:
            raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {out_p}")
        prov = generate_with_provenance(spec_p, out_p, src_p, timestamp=args.timestamp)
        print(json.dumps(prov, ensure_ascii=False))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
