#!/usr/bin/env python3
"""Response-withheld blind re-review packet builder and reconciliation verifier for dyz-med-revision.

Solves the bias where a persuasive response letter masks unimplemented manuscript edits:
  1. `pack`: Combines original reviewer comments JSON + revised manuscript (explicitly EXCLUDING any response letter)
     into a SHA-256-bound blind re-review packet + blank verdict template.
  2. `reconcile`: Cross-checks blind verdicts against the author's response-table JSON, blocking `verified_closed`
     whenever a comment claimed `ACCEPT` in the letter but blind review found `not_found_in_text` or `partially_addressed`.
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

VALID_BLIND = {"resolved_in_text", "partially_addressed", "not_found_in_text", "not_applicable_disagree"}


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


def build_blind_packet(comments_path: Path, manuscript_path: Path, out_dir: Path, force: bool = False) -> dict:
    c_p = ensure_plain_path(comments_path)
    m_p = ensure_plain_path(manuscript_path)
    o_dir = ensure_plain_path(out_dir)
    if not c_p.is_file() or not m_p.is_file():
        raise ValueError("--comments 与 --manuscript 必须存在")
    pkt_p = o_dir / "blind-rereview-packet.json"
    verdict_p = o_dir / "blind-verdicts-template.json"
    for target in (pkt_p, verdict_p):
        if target in (c_p, m_p):
            raise ValueError("输出路径不能覆盖输入文件")
        if target.exists() and not force:
            raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请传 --force）: {target}")

    c_raw = c_p.read_bytes()
    m_raw = m_p.read_bytes()
    comments_doc = json.loads(c_raw.decode("utf-8-sig"))
    comments = comments_doc.get("comments") if isinstance(comments_doc, dict) else comments_doc
    if not isinstance(comments, list) or not comments:
        raise ValueError("comments JSON 需要非空 comments 数组")

    # Strip any author response fields if accidentally present in input comments JSON.
    sanitized_comments = []
    for item in comments:
        if not isinstance(item, dict) or not item.get("id") or not item.get("original_text"):
            raise ValueError("每条审稿意见必须包含 id 与 original_text")
        sanitized_comments.append({
            "id": str(item["id"]),
            "reviewer": str(item.get("reviewer", "Reviewer")),
            "severity": str(item.get("severity", "major")),
            "original_text": str(item["original_text"]),
        })

    packet = {
        "tool": "blind_rereview_pack/1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "response_letter_withheld": True,
        "inputs": {
            "comments": {"path": c_p.name, "sha256": sha_bytes(c_raw)},
            "revised_manuscript": {"path": m_p.name, "sha256": sha_bytes(m_raw)},
        },
        "instructions": (
            "盲审自检：请仅阅读 revised_manuscript_text 与 sanitized_comments，不要读取作者回复信。"
            "在 blind-verdicts-template.json 中逐条填写 blind_check_status 与稿件实际定位后再运行 reconcile。"
        ),
        "sanitized_comments": sanitized_comments,
        "revised_manuscript_text": m_raw.decode("utf-8-sig"),
    }
    verdict_template = {
        "schema_version": "1.0",
        "manuscript_sha256": sha_bytes(m_raw),
        "verdicts": [
            {
                "id": c["id"],
                "blind_check_status": "not_found_in_text",
                "blind_check_locator": "",
                "notes": "",
            }
            for c in sanitized_comments
        ],
    }

    o_dir.mkdir(parents=True, exist_ok=True)
    pkt_p.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    verdict_p.write_text(json.dumps(verdict_template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"status": "packed", "comments": len(sanitized_comments), "packet": pkt_p.name, "template": verdict_p.name}


def reconcile_verdicts(verdicts_doc: dict, responses_doc: dict, manuscript_path: Path | None = None) -> dict:
    verdicts = {str(v["id"]): v for v in verdicts_doc.get("verdicts", [])}
    responses = responses_doc.get("responses") if isinstance(responses_doc, dict) else responses_doc
    if not isinstance(responses, list):
        raise ValueError("responses JSON 需要 responses 数组")

    conflicts: list[dict] = []
    ready_to_close = 0
    freshness = "unverified"
    if manuscript_path is not None:
        m_p = ensure_plain_path(manuscript_path)
        actual_sha = sha_bytes(m_p.read_bytes())
        if actual_sha == verdicts_doc.get("manuscript_sha256"):
            freshness = "current"
        else:
            freshness = "stale"
            conflicts.append({"id": "*", "code": "MANUSCRIPT_STALE", "detail": "修改稿哈希已变更，盲审记录已过期"})

    for resp in responses:
        cid = str(resp.get("id", ""))
        stance = str(resp.get("response_stance", "")).upper()
        claimed_status = str(resp.get("status", "open"))
        v = verdicts.get(cid)
        if not v:
            conflicts.append({"id": cid, "code": "MISSING_BLIND_VERDICT", "detail": "该审稿意见缺少盲审自检结论"})
            continue
        bstat = str(v.get("blind_check_status", ""))
        if bstat not in VALID_BLIND:
            conflicts.append({"id": cid, "code": "INVALID_BLIND_STATUS", "detail": f"非法盲检状态: {bstat}"})
            continue
        if bstat == "resolved_in_text" and not str(v.get("blind_check_locator") or "").strip():
            conflicts.append({"id": cid, "code": "RESOLVED_WITHOUT_LOCATOR", "detail": "resolved_in_text 必须提供正文实际定位"})
        if stance == "ACCEPT" and bstat != "resolved_in_text":
            conflicts.append({
                "id": cid,
                "code": "LETTER_ACCEPT_NOT_IN_MANUSCRIPT",
                "detail": f"回复信声称 ACCEPT，但盲审仅见 {bstat}，禁止进入 verified_closed",
            })
        elif claimed_status == "verified_closed" and bstat != "resolved_in_text":
            conflicts.append({
                "id": cid,
                "code": "PREMATURE_VERIFIED_CLOSED",
                "detail": f"问题标为 verified_closed，但盲审状态为 {bstat}",
            })
        elif bstat == "resolved_in_text" and freshness != "stale":
            ready_to_close += 1

    return {
        "tool": "blind_rereview_pack/1.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "manuscript_freshness": freshness,
        "total_items": len(responses),
        "blind_resolved_count": ready_to_close,
        "status": "reconciled" if not conflicts else "conflicts_found",
        "conflicts": conflicts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Response-withheld blind re-review packager and conflict reconciler.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="Build a blind re-review packet excluding the response letter.")
    p_pack.add_argument("--comments", required=True)
    p_pack.add_argument("--manuscript", required=True)
    p_pack.add_argument("--out-dir", required=True)
    p_pack.add_argument("--force", action="store_true")

    p_rec = sub.add_parser("reconcile", help="Cross-check blind verdicts against response-table stances.")
    p_rec.add_argument("--verdicts", required=True)
    p_rec.add_argument("--responses", required=True)
    p_rec.add_argument("--manuscript", help="Optional revised manuscript to verify SHA-256 freshness.")
    p_rec.add_argument("--report", help="Optional JSON report path.")
    p_rec.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "pack":
            res = build_blind_packet(Path(args.comments), Path(args.manuscript), Path(args.out_dir), force=args.force)
            print(json.dumps(res, ensure_ascii=False))
            return 0

        v_p = ensure_plain_path(Path(args.verdicts))
        r_p = ensure_plain_path(Path(args.responses))
        m_p = ensure_plain_path(Path(args.manuscript)) if args.manuscript else None
        res = reconcile_verdicts(
            json.loads(v_p.read_text(encoding="utf-8-sig")),
            json.loads(r_p.read_text(encoding="utf-8-sig")),
            m_p,
        )
        if args.report:
            rp = ensure_plain_path(Path(args.report))
            if rp in (v_p, r_p, m_p):
                raise ValueError("--report 不能覆盖输入文件")
            if rp.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请传 --force）: {rp}")
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["status"] == "reconciled" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
