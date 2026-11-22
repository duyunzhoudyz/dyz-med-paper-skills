#!/usr/bin/env python3
"""Deterministic safety and workflow hook for DYZ MedPaper (Claude Code / CLI).

Runs locally with Python stdlib only. Never uploads data or modifies user files.
Output formats (--format):
  - claude (default): emits Claude Code official hook JSON schema (`systemMessage` + `hookSpecificOutput`).
    In `advisory` mode, passes warnings via `additionalContext` (exit 0).
    In `strict` mode on PreToolUse blocking findings, emits `permissionDecision: "deny"` with reason (exit 0).
  - raw: emits raw diagnostic JSON (exits 2 on strict block) for CLI checks and non-Claude hosts.

Guards:
  1. PHI pre-flight guard: flags CN 18-digit IDs (checksum verified), separator-aware CN mobile numbers
     (excluding Grant/PMID/NCT/barcode contexts), MRN/ward/bed tags, Chinese patient-name clinical strings,
     US SSN, and direct-identifier CSV headers across Write/Edit/MultiEdit/Bash/PowerShell payloads.
  2. Plan-first workflow gate: aligned with SKILL.md paths (`paper/sections/`, `paper/manuscript/`,
     `paper/analysis/analysis-plan.md`, `paper/writing/manuscript_argument_map.yaml`, etc.) and
     target-specific `paper/project-passport.yaml` approvals (never bypassed by unrelated `confirmed`).
  3. External transmission guard: blocks unauthorized `--online` calls (verify_references.py /
     fetch_journal_policy.py) and warns/blocks curl/wget/Invoke-WebRequest/git push referencing data/patient files.
  4. Post-edit statistical audit reminder: flags orphan `[evidence:...]` tags and unbound statistical paragraphs.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECK = "10X98765432"

CN_ID_RE = re.compile(
    r"(?<![0-9A-Za-z])([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?![0-9A-Za-z])"
)
CN_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d[\s-]?\d{4}[\s-]?\d{4})(?!\d)")
NON_PHONE_CTX_RE = re.compile(
    r"(?:grant(?:\s*(?:no\.?|number|#))?|fund(?:ing)?(?:\s*(?:no\.?|number|#))?|基金(?:编号|号)?|资助(?:编号|号)?|"
    r"pmid|nct|doi|issn|isbn|barcode|条码|标本(?:号|编号)?|样本(?:号|编号)?|timestamp|时间戳|project\s*(?:no\.?|id)|编号)\s*[:：#.\-]?\s*$",
    re.IGNORECASE,
)
MRN_TAG_RE = re.compile(
    r"(?:住院号|门诊号|病案号|就诊卡号|医保号|病历号|住院流水号|登记号|患者\s*ID|病人\s*ID|MRN|Patient\s*ID)\s*[:：=#]\s*[A-Za-z0-9_-]{3,}",
    re.IGNORECASE,
)
CN_PATIENT_NAME_RE = re.compile(r"(?:患者|病人)\s*[:：]?\s*[\u4e00-\u9fff]{2,4}(?:[，,、\s]|(?:男|女|\d{1,3}岁))")
WARD_BED_RE = re.compile(r"(?:\d+病区\s*\d+床|\d+床[^。\n]{0,12}(?:医院|科|病区)|(?:医院|科)[^。\n]{0,12}\d+病区\s*\d+床)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
SENSITIVE_COL_RE = re.compile(
    r"(?:^|[,;\t|]\s*)(?:姓名(?:\([^)]*\))?|患者姓名|病人姓名|身份证号?|手机号?|联系电话\d*|家庭住址|家庭地址|居住地址|住院号|门诊号|病案号(?:\([^)]*\))?|患者ID|patient_name|full_name|id_card|national_id|phone_number|home_address|mrn|ssn)(?:\s*[,;\t|]|$)",
    re.IGNORECASE | re.MULTILINE,
)

CLAIM_RE = re.compile(r"\[claim:([A-Za-z][A-Za-z0-9_-]*)\]")
EVIDENCE_RE = re.compile(r"\[evidence:([^\]\n]+)\]")
# Narrowed to statistical expressions rather than ordinary years or section numbering.
STAT_EXPR_RE = re.compile(
    r"(?:\b(?:HR|OR|RR|aHR|aOR|SMD|AUC|AUROC|IQR|SD|CI)\b|\b[Pp]\s*[=<>≤≥]\s*0?\.\d+|\bn\s*=\s*\d+|\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*±\s*\d+)"
)

MANUSCRIPT_DIR_HINTS = ("paper/sections/", "paper/manuscript/", "paper/drafts/", "manuscript/", "drafts/")
PLAN_FILE_STEM_RE = re.compile(r"(?:^|[_/-])(plan|outline|notes|blueprint|map)(?:$|[_/-])", re.IGNORECASE)
SHELL_TOOLS = {"Bash", "PowerShell"}
ANALYSIS_EXEC_RE = re.compile(r"\b(?:rscript|python3?|py\s+-3|stata|spss)\b", re.IGNORECASE)
ANALYSIS_TARGET_RE = re.compile(r"(?:paper/analysis/|analysis[._/-]|run_model|statistical)", re.IGNORECASE)
EXFIL_CMD_RE = re.compile(r"\b(?:curl(?:\.exe)?|wget(?:\.exe)?|invoke-webrequest|iwr|irm|git\s+push|gh\s+pr\s+create)\b", re.IGNORECASE)
DATA_FILE_HINT_RE = re.compile(r"(?:\.(?:csv|tsv|xlsx?|sav|dta|rds)\b|raw[_-]|patient|cohort|paper/data/)", re.IGNORECASE)


def valid_cn_id(code: str) -> bool:
    code = code.upper()
    if len(code) != 18 or not code[:17].isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(code[:17], _ID_WEIGHTS))
    return _ID_CHECK[total % 11] == code[17]


def scan_text_for_phi(text: str) -> list[dict]:
    """Return redacted PHI findings; never echo raw identifier values."""
    if not text:
        return []
    findings: list[dict] = []
    cn_ids = [m.group(1) for m in CN_ID_RE.finditer(text) if valid_cn_id(m.group(1))]
    if cn_ids:
        findings.append({"code": "PHI_CN_ID", "count": len(cn_ids), "detail": "检测到符合校验码的中国大陆18位身份证号"})

    phones = []
    for m in CN_PHONE_RE.finditer(text):
        prefix = text[max(0, m.start() - 28):m.start()]
        if NON_PHONE_CTX_RE.search(prefix):
            continue
        phones.append(m.group(1))
    if phones:
        findings.append({"code": "PHI_CN_PHONE", "count": len(phones), "detail": "检测到疑似中国大陆11位手机号"})

    mrns = MRN_TAG_RE.findall(text)
    if mrns:
        findings.append({"code": "PHI_MRN", "count": len(mrns), "detail": "检测到住院号/门诊号/病案号/住院流水号/患者ID标识"})

    cn_names = CN_PATIENT_NAME_RE.findall(text)
    if cn_names:
        findings.append({"code": "PHI_CN_PATIENT_NAME", "count": len(cn_names), "detail": "检测到疑似含中文患者姓名的临床描述"})

    ward_beds = WARD_BED_RE.findall(text)
    if ward_beds:
        findings.append({"code": "PHI_WARD_BED", "count": len(ward_beds), "detail": "检测到疑似具体病区/床号定位信息"})

    ssns = SSN_RE.findall(text)
    if ssns:
        findings.append({"code": "PHI_SSN", "count": len(ssns), "detail": "检测到疑似SSN格式编号"})

    cols = SENSITIVE_COL_RE.findall(text)
    if cols:
        findings.append({"code": "PHI_COLUMN_HEADER", "count": len(cols), "detail": "检测到疑似含患者直接标识符的表头字段"})
    return findings


def normalize_rel(path_str: str, project_root: Path) -> str:
    if not path_str:
        return ""
    try:
        p = Path(path_str)
        if p.is_absolute():
            p = p.resolve().relative_to(project_root.resolve())
        return p.as_posix().lstrip("./")
    except ValueError:
        return path_str.replace("\\", "/")


def extract_written_content(tool_input: dict) -> str:
    parts: list[str] = []
    for k in ("content", "new_string", "new_str", "command"):
        val = tool_input.get(k)
        if val:
            parts.append(str(val))
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for item in edits:
            if isinstance(item, dict) and item.get("new_string"):
                parts.append(str(item["new_string"]))
    return "\n".join(parts)


def has_approved_marker(project_root: Path, candidates: tuple[str, ...], passport_target_keywords: tuple[str, ...]) -> bool:
    approve_re = re.compile(
        r"(?:status|state|approval|审批状态|计划状态|状态)\s*[:=：]\s*['\"]?(?:approved|confirmed|已批准|已确认)['\"]?",
        re.IGNORECASE,
    )
    for rel in candidates:
        p = project_root / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        if approve_re.search(text):
            return True

    # Inspect passport approvals strictly scoped to the target artifact type (not any random `state: confirmed`).
    passport = project_root / "paper/project-passport.yaml"
    if passport.is_file():
        try:
            text = passport.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return False
        # Split human_approvals blocks or scan nearby lines around target keywords.
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            low = line.lower()
            if any(kw in low for kw in passport_target_keywords):
                window = "\n".join(lines[max(0, idx - 6):min(len(lines), idx + 8)])
                if re.search(r"state\s*:\s*['\"]?confirmed['\"]?", window, re.IGNORECASE):
                    return True
    return False


def evaluate_pre_tool(payload: dict, project_root: Path, mode: str) -> dict:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    file_path = str(tool_input.get("file_path") or tool_input.get("path") or tool_input.get("uri") or "")
    rel_path = normalize_rel(file_path, project_root)
    content = extract_written_content(tool_input)
    findings: list[dict] = []

    # 1. PHI check across Write / Edit / MultiEdit / Bash / PowerShell.
    for item in scan_text_for_phi(content):
        findings.append({"severity": "high", "rule": "PHI_GUARD", **item})

    # 2. Plan-first gate for manuscript drafting (aligned with paper/sections/ & paper/manuscript/).
    if tool_name in ("Write", "Edit", "MultiEdit") and any(h in rel_path for h in MANUSCRIPT_DIR_HINTS):
        stem = Path(rel_path).stem
        if rel_path.endswith(".md") and not PLAN_FILE_STEM_RE.search(stem):
            approved = has_approved_marker(
                project_root,
                (
                    "paper/writing/manuscript_argument_map.yaml",
                    "paper/writing-plan/writing-plan.md",
                    "paper/writing-plan/approved-plan.yaml",
                    "paper/draft_plan.md",
                ),
                passport_target_keywords=("writing-plan", "writing_plan", "argument_map", "draft_plan"),
            )
            if not approved:
                findings.append({
                    "severity": "medium",
                    "rule": "PLAN_FIRST_MANUSCRIPT",
                    "code": "MISSING_APPROVED_WRITING_PLAN",
                    "detail": (
                        f"写入 {rel_path} 前未检测到已确认的写作计划（paper/writing/manuscript_argument_map.yaml、"
                        "paper/writing-plan/writing-plan.md 或 passport 对应 confirmed 批准）。请先用 dyz-med-writing-plan 确认蓝图。"
                    ),
                })

    # 3. Plan-first gate & external transmission checks for Bash / PowerShell commands.
    command = str(tool_input.get("command") or "")
    cmd_norm = command.replace("\\", "/")
    if tool_name in SHELL_TOOLS and command:
        if ANALYSIS_EXEC_RE.search(command) and ANALYSIS_TARGET_RE.search(cmd_norm):
            approved = has_approved_marker(
                project_root,
                (
                    "paper/analysis/analysis-plan.md",
                    "paper/analysis/statistical-analysis-plan.md",
                    "paper/analysis/approved-sap.yaml",
                ),
                passport_target_keywords=("analysis-plan", "analysis_plan", "statistical-analysis-plan", "sap"),
            )
            if not approved:
                findings.append({
                    "severity": "high",
                    "rule": "PLAN_FIRST_ANALYSIS",
                    "code": "MISSING_APPROVED_SAP",
                    "detail": (
                        "执行统计分析脚本前未检测到已批准的统计分析计划（paper/analysis/analysis-plan.md "
                        "或 passport 对应 confirmed 批准）。请先通过 dyz-med-analyze 拟定计划并取得用户批准。"
                    ),
                })

        if "--online" in command and "--authorization" not in command:
            if "verify_references.py" in command or "fetch_journal_policy.py" in command:
                findings.append({
                    "severity": "high",
                    "rule": "EXTERNAL_AUTH_REQUIRED",
                    "code": "MISSING_ONLINE_AUTHORIZATION",
                    "detail": "在线核验/抓取脚本使用 --online 时必须显式传入 --authorization 人类授权文件。",
                })

        if EXFIL_CMD_RE.search(command) and DATA_FILE_HINT_RE.search(cmd_norm):
            findings.append({
                "severity": "high",
                "rule": "EXTERNAL_DATA_EXFIL_GUARD",
                "code": "POTENTIAL_EXTERNAL_DATA_SEND",
                "detail": "检测到外部网络/推送命令引用了数据或患者相关文件，严禁未经脱敏与人类明确授权外传。",
            })

    has_blocking = any(f["severity"] == "high" or f["rule"].startswith("PLAN_FIRST") for f in findings)
    decision = "block" if (mode == "strict" and has_blocking) else ("warn" if findings else "allow")
    return {
        "hook": "dyz-med-guard",
        "event": "PreToolUse",
        "mode": mode,
        "decision": decision,
        "findings": findings,
    }


def evaluate_post_edit(payload: dict, project_root: Path, mode: str) -> dict:
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or tool_input.get("uri") or "")
    rel_path = normalize_rel(file_path, project_root)
    findings: list[dict] = []

    if file_path and rel_path.endswith(".md") and any(h in rel_path for h in MANUSCRIPT_DIR_HINTS):
        target = Path(file_path) if Path(file_path).is_absolute() else (project_root / rel_path)
        if target.is_file():
            try:
                text = target.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                try:
                    text = target.read_text(encoding="gb18030", errors="replace")
                except OSError:
                    text = ""
            for item in scan_text_for_phi(text):
                findings.append({"severity": "high", "rule": "PHI_GUARD", **item})
            untagged_stat = 0
            orphan_ev = 0
            for para in re.split(r"\n\s*\n", text):
                stripped = para.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("|"):
                    continue
                has_claim = bool(CLAIM_RE.search(stripped))
                has_ev = bool(EVIDENCE_RE.search(stripped))
                if has_ev and not has_claim:
                    orphan_ev += 1
                if STAT_EXPR_RE.search(stripped) and not (has_claim or has_ev):
                    untagged_stat += 1
            if orphan_ev:
                findings.append({
                    "severity": "medium",
                    "rule": "POST_EDIT_AUDIT",
                    "code": "EVIDENCE_WITHOUT_CLAIM",
                    "detail": f"{rel_path} 中有 {orphan_ev} 个段落含 [evidence:...] 但缺少 [claim:...] 标记，建议运行 audit_manuscript.py 复核。",
                })
            if untagged_stat:
                findings.append({
                    "severity": "info",
                    "rule": "POST_EDIT_AUDIT",
                    "code": "STATISTICAL_PARAGRAPHS_UNBOUND",
                    "detail": f"{rel_path} 中有 {untagged_stat} 个含统计量（HR/OR/P/CI/%/n=）的段落未绑定 claim/evidence 标记，提交前建议运行 dyz-med-evidence-audit。",
                })

    return {
        "hook": "dyz-med-guard",
        "event": "PostToolUse",
        "mode": mode,
        "decision": "warn" if findings else "allow",
        "findings": findings,
    }


def format_claude_output(report: dict) -> dict | None:
    """Map internal report to Claude Code official Hooks JSON schema."""
    findings = report.get("findings") or []
    if not findings:
        return None
    summary_lines = [f"[{f['code']}] {f['detail']}" for f in findings]
    summary = "DYZ MedPaper Guard: " + " | ".join(summary_lines)
    event_name = report["event"]

    if event_name == "PreToolUse":
        if report["decision"] == "block":
            return {
                "systemMessage": summary,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": summary,
                },
            }
        return {
            "systemMessage": summary,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": summary,
            },
        }
    return {
        "systemMessage": summary,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": summary,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DYZ MedPaper deterministic safety and workflow hook.")
    parser.add_argument("event", choices=("pre-tool", "post-edit"))
    parser.add_argument("--mode", choices=("advisory", "strict"), default=os.environ.get("DYZ_MED_HOOK_MODE", "advisory"))
    parser.add_argument("--format", choices=("claude", "raw"), default=os.environ.get("DYZ_MED_HOOK_FORMAT", "claude"))
    parser.add_argument("--project-root", help="Override project root (default: payload.cwd else os.getcwd()).")
    parser.add_argument("--payload-file", help="Optional JSON file instead of reading stdin.")
    args = parser.parse_args(argv)

    raw = ""
    if args.payload_file:
        raw = Path(args.payload_file).read_text(encoding="utf-8-sig")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    cwd_from_payload = payload.get("cwd") if isinstance(payload, dict) else None
    root = Path(args.project_root or cwd_from_payload or os.getcwd()).resolve()
    report = evaluate_pre_tool(payload, root, args.mode) if args.event == "pre-tool" else evaluate_post_edit(payload, root, args.mode)

    if args.format == "raw":
        out_str = json.dumps(report, ensure_ascii=False)
        if report["decision"] == "block":
            print(out_str, file=sys.stderr)
            return 2
        if report["findings"]:
            print(out_str)
        return 0

    claude_obj = format_claude_output(report)
    if claude_obj is not None:
        print(json.dumps(claude_obj, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
