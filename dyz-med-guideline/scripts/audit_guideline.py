#!/usr/bin/env python3
"""Deterministic reporting-guideline audit calculator and contract verifier.

Validates an authored item-by-item audit JSON against structured-checklists.json (full official subitems):
  - Enforces valid statuses: COVERED, PARTIAL, MISSING, NOT_APPLICABLE
  - Rejects omitted, duplicated, or unknown item IDs
  - Requires non-empty evidence locator for COVERED items
  - Requires non-empty gap explanation (comment) for PARTIAL items
  - Requires non-empty rationale (comment) for NOT_APPLICABLE items
  - Computes total distribution and applicable coverage percentage (excluding NOT_APPLICABLE)
  - Binds manuscript SHA-256 and guideline version metadata; refuses silent overwrites without --force

Does NOT auto-certify compliance; human/expert review of evidence adequacy remains required.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

VALID_STATUSES = {"COVERED", "PARTIAL", "MISSING", "NOT_APPLICABLE"}
DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "structured-checklists.json"


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


def write_safe_json(path: Path, payload: dict, force: bool, protected: tuple[Path, ...] = ()) -> None:
    target = ensure_plain_path(path)
    if target in protected:
        raise ValueError(f"输出路径不能与输入路径相同: {target}")
    if target.exists() and not force:
        raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_checklists(data_path: Path = DEFAULT_DATA) -> dict:
    return json.loads(data_path.read_text(encoding="utf-8-sig"))


def resolve_guideline(db: dict, guideline_id: str) -> tuple[str, dict, str | None]:
    aliases = db.get("aliases") or {}
    warning = None
    resolved_id = guideline_id
    if guideline_id in aliases:
        resolved_id = aliases[guideline_id]
        warning = (
            f"别名 {guideline_id!r} 已解析为 {resolved_id!r}；"
            "请按研究设计显式选择 STROBE-Cohort / STROBE-CaseControl / STROBE-CrossSectional。"
        )
    spec = db["guidelines"].get(resolved_id)
    if not spec:
        raise ValueError(f"未知规范: {guideline_id}；可用: {sorted(db['guidelines'])}")
    return resolved_id, spec, warning


def init_skeleton(guideline_id: str, manuscript_path: Path, data_path: Path = DEFAULT_DATA) -> dict:
    db = load_checklists(data_path)
    resolved_id, spec, warning = resolve_guideline(db, guideline_id)
    ms_p = ensure_plain_path(manuscript_path)
    ms_bytes = ms_p.read_bytes()
    doc = {
        "schema_version": "2.0",
        "guideline_id": resolved_id,
        "guideline_version": spec["version"],
        "official_main_items": spec.get("official_main_items"),
        "official_subitems": spec.get("official_subitems", len(spec["items"])),
        "granularity": spec.get("granularity", "full_subitems"),
        "official_url": spec["official_url"],
        "manuscript": {"path": ms_p.name, "sha256": sha_bytes(ms_bytes)},
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "id": it["id"],
                "section": it["section"],
                "topic": it["topic"],
                **({"applicability": it["applicability"]} if "applicability" in it else {}),
                "status": "MISSING",
                "evidence": "",
                "comment": "",
                "suggested_fix": "",
            }
            for it in spec["items"]
        ],
    }
    if warning:
        doc["alias_warning"] = warning
    return doc


def evaluate_audit(audit_doc: dict, manuscript_path: Path | None = None, data_path: Path = DEFAULT_DATA) -> dict:
    db = load_checklists(data_path)
    gid_raw = str(audit_doc.get("guideline_id") or "")
    gid, spec, alias_warning = resolve_guideline(db, gid_raw)

    expected_ids = [it["id"] for it in spec["items"]]
    expected_set = set(expected_ids)
    provided_items = audit_doc.get("items") or []
    by_id = {}
    issues: list[dict] = []

    for row in provided_items:
        if not isinstance(row, dict):
            issues.append({"code": "INVALID_ROW", "item_id": "*", "detail": "条目必须是对象"})
            continue
        iid = str(row.get("id", "")).strip()
        if iid not in expected_set:
            issues.append({"code": "UNKNOWN_ITEM_ID", "item_id": iid or "(empty)", "detail": f"不属于 {gid} 官方条目编号"})
            continue
        if iid in by_id:
            issues.append({"code": "DUPLICATE_ITEM", "item_id": iid, "detail": "重复条目 ID"})
        by_id[iid] = row

    counts = {s: 0 for s in VALID_STATUSES}
    for iid in expected_ids:
        row = by_id.get(iid)
        if not row:
            issues.append({"code": "ITEM_OMITTED", "item_id": iid, "detail": "清单条目缺失"})
            continue
        status = row.get("status")
        if status not in VALID_STATUSES:
            issues.append({"code": "INVALID_STATUS", "item_id": iid, "detail": f"非法状态: {status}"})
            continue
        counts[status] += 1
        if status == "COVERED" and not str(row.get("evidence") or "").strip():
            issues.append({"code": "COVERED_WITHOUT_EVIDENCE", "item_id": iid, "detail": "COVERED 条目必须提供可定位的稿件位置"})
        if status == "PARTIAL" and not str(row.get("comment") or "").strip():
            issues.append({"code": "PARTIAL_WITHOUT_GAP_COMMENT", "item_id": iid, "detail": "PARTIAL 条目必须写明缺失的具体组成"})
        if status == "NOT_APPLICABLE" and not str(row.get("comment") or "").strip():
            issues.append({"code": "NA_WITHOUT_REASON", "item_id": iid, "detail": "NOT_APPLICABLE 条目必须写明不适用理由"})

    ms_freshness = "unverified"
    warnings: list[str] = []
    if alias_warning:
        warnings.append(alias_warning)
    if manuscript_path is not None:
        ms_p = ensure_plain_path(manuscript_path)
        if not ms_p.is_file():
            issues.append({"code": "MANUSCRIPT_MISSING", "item_id": "*", "detail": f"指定稿件不存在: {ms_p}"})
        else:
            actual_sha = sha_bytes(ms_p.read_bytes())
            expected_sha = (audit_doc.get("manuscript") or {}).get("sha256")
            if expected_sha and actual_sha == expected_sha:
                ms_freshness = "current"
            else:
                ms_freshness = "stale"
                issues.append({"code": "MANUSCRIPT_CHANGED", "item_id": "*", "detail": "稿件内容哈希已变化，需重新核对清单"})
    else:
        warnings.append("未传入 --manuscript，未能核验当前稿件哈希新鲜度（manuscript_freshness=unverified）。")

    applicable_total = counts["COVERED"] + counts["PARTIAL"] + counts["MISSING"]
    applicable_coverage = round(100.0 * counts["COVERED"] / applicable_total, 1) if applicable_total else 0.0

    return {
        "tool": "audit_guideline/2.0",
        "guideline_id": gid,
        "guideline_version": spec["version"],
        "official_main_items": spec.get("official_main_items"),
        "official_subitems": len(expected_ids),
        "granularity": spec.get("granularity", "full_subitems"),
        "official_url": spec["official_url"],
        "manuscript_freshness": ms_freshness,
        "total_items": len(expected_ids),
        "applicable_items": applicable_total,
        "counts": counts,
        "applicable_coverage_pct": applicable_coverage,
        "contract_status": "valid" if not issues else "invalid",
        "issues": issues,
        "warnings": warnings,
        "certification": "not_certified_requires_human_review",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize or validate a full-subitem reporting-guideline audit.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create an item-by-item audit skeleton bound to a manuscript.")
    p_init.add_argument(
        "--guideline",
        required=True,
        help="Guideline ID (STROBE-Cohort, STROBE-CaseControl, STROBE-CrossSectional, PRISMA-2020, CONSORT-2025, STARD-2015, CARE, TRIPOD+AI).",
    )
    p_init.add_argument("--manuscript", required=True, help="Path to manuscript file (read-only).")
    p_init.add_argument("--output", required=True, help="Output skeleton JSON path.")
    p_init.add_argument("--force", action="store_true", help="Allow overwriting an existing --output file.")

    p_check = sub.add_parser("check", help="Validate audit JSON and compute coverage.")
    p_check.add_argument("--audit", required=True, help="Populated audit JSON file (read-only).")
    p_check.add_argument("--manuscript", help="Manuscript file to verify SHA-256 freshness.")
    p_check.add_argument("--report", help="Optional output summary JSON path.")
    p_check.add_argument("--force", action="store_true", help="Allow overwriting an existing --report file.")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            ms_p = ensure_plain_path(Path(args.manuscript))
            if not ms_p.is_file():
                raise ValueError(f"稿件不存在: {ms_p}")
            doc = init_skeleton(args.guideline, ms_p)
            out = Path(args.output)
            write_safe_json(out, doc, force=args.force, protected=(ms_p,))
            print(json.dumps({"status": "initialized", "guideline": doc["guideline_id"], "items": len(doc["items"]), "output": out.name}, ensure_ascii=False))
            return 0

        audit_p = ensure_plain_path(Path(args.audit))
        if not audit_p.is_file():
            raise ValueError(f"审计文件不存在: {audit_p}")
        audit_doc = json.loads(audit_p.read_text(encoding="utf-8-sig"))
        ms_p = ensure_plain_path(Path(args.manuscript)) if args.manuscript else None
        summary = evaluate_audit(audit_doc, ms_p)
        if args.report:
            protected = tuple(p for p in (audit_p, ms_p) if p is not None)
            write_safe_json(Path(args.report), summary, force=args.force, protected=protected)
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if summary["contract_status"] == "valid" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
