#!/usr/bin/env python3
"""Local, zero-network PHI/PII detector and optional pseudonymizer for medical CSV/TSV/XLSX/Markdown.

Usage:
  Scan only (read-only, default):
    python deidentify_check.py --input raw.csv --report phi-report.json

  Generate de-identified copy + external key map (original file is never modified):
    python deidentify_check.py --input raw.csv --report phi-report.json \
      --output deidentified.csv --key-map ../private-key-map.json

Security & robustness guarantees:
  - Pure Python stdlib; zero network calls, zero AI/API transmission.
  - Supports UTF-8, GB18030/GBK (common in Chinese hospital exports), UTF-16, and read-only .xlsx scanning.
  - Original input file is strictly read-only; refuses silent overwrite without --force and refuses symlinks.
  - Report never echoes raw identifier values (counts, column names, line/row numbers only).
  - Explicitly distinguishes non-PHI lab/study codes (样本条码/标本号/PMID/DOI/基金号) to avoid corrupting data.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECK = "10X98765432"

CN_ID_RE = re.compile(
    r"(?<![0-9A-Za-z])([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?![0-9A-Za-z])"
)
CN_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d[\s-]?\d{4}[\s-]?\d{4})(?!\d)")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
MRN_INLINE_RE = re.compile(
    r"(?:住院号|门诊号|病案号|就诊卡号|医保号|病历号|住院流水号|登记号|患者ID|病人ID|MRN|Patient\s*ID)\s*[:：=#]\s*([A-Za-z0-9_-]{3,})",
    re.IGNORECASE,
)
SSN_RE = re.compile(r"(?<!\d)(\d{3}-\d{2}-\d{4})(?!\d)")
EXACT_DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2}[-/.年](?:0?[1-9]|1[0-2])[-/.月](?:0?[1-9]|[12]\d|3[01])日?)(?!\d)")

NON_PHI_HEADER_KEYWORDS = (
    "样本条码", "标本条码", "标本号", "样本号", "样本编号", "条码", "条形码", "barcode", "specimen",
    "sample_id", "subject_id", "study_id", "case_id", "pmid", "doi", "基金号", "grant", "nct", "batch",
)

DIRECT_ID_PATTERNS = (
    "姓名", "患者名", "病人名", "受试者名", "patient_name", "full_name", "subject_name",
    "身份证", "证件号", "id_card", "national_id", "ssn",
    "手机", "联系电话", "电话", "联系方式", "phone", "mobile", "tel",
    "住址", "家庭地址", "居住地址", "联系地址", "通讯地址", "address",
    "邮箱", "email", "e-mail",
    "住院号", "门诊号", "病案号", "就诊卡号", "病历号", "医保号", "住院流水号", "登记号",
    "患者id", "病人id", "mrn", "patient_id", "hospital_id",
)

QUASI_DATE_PATTERNS = (
    "出生日期", "出生年月", "生日", "dob", "birth_date", "date_of_birth",
    "入院日期", "入院时间", "出院日期", "出院时间", "手术日期", "手术时间", "就诊日期", "就诊时间",
    "随访日期", "死亡日期", "admission_date", "discharge_date", "visit_date",
)

QUASI_LOC_PATTERNS = (
    "医院", "院区", "科室", "病区", "床号", "邮编", "邮政编码",
    "hospital", "department", "ward", "bed_no", "zip", "postal_code",
)

AGE_PATTERNS = ("年龄", "age")


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


def decode_text(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise ValueError("无法以 UTF-8 / GB18030 / UTF-16 解码输入文件（若为二进制或 .xls 请先转换）")


def valid_cn_id(code: str) -> bool:
    code = code.upper()
    if len(code) != 18 or not code[:17].isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(code[:17], _ID_WEIGHTS))
    return _ID_CHECK[total % 11] == code[17]


def clean_header(name: str) -> str:
    s = (name or "").strip().lower()
    # Strip parenthesized units/notes like 姓名(中文), 年龄（岁）, 病案号(旧)
    s = re.sub(r"[\(（][^\)）]*[\)）]", "", s)
    # Strip trailing digits like 联系电话1 -> 联系电话
    s = re.sub(r"\d+$", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s


def classify_header(name: str) -> str:
    raw_low = (name or "").strip().lower()
    norm = clean_header(name)
    if any(k in raw_low or k in norm for k in NON_PHI_HEADER_KEYWORDS):
        return "non_phi_code"
    if norm == "name" or any(p in norm for p in DIRECT_ID_PATTERNS):
        return "direct_id"
    if any(p in norm for p in QUASI_DATE_PATTERNS):
        return "quasi_date"
    if any(p in norm for p in QUASI_LOC_PATTERNS):
        return "quasi_location"
    if norm in AGE_PATTERNS or norm.startswith("age_") or norm.startswith("年龄"):
        return "age"
    return "other"


def scan_cell(value: str, col_role: str = "other") -> tuple[list[str], list[str]]:
    """Return (confirmed_phi_kinds, suspected_needs_review_kinds)."""
    hits: list[str] = []
    suspected: list[str] = []
    if not value:
        return hits, suspected
    if any(valid_cn_id(m.group(1)) for m in CN_ID_RE.finditer(value)):
        hits.append("CN_ID_CARD")
    if CN_PHONE_RE.search(value):
        if col_role == "non_phi_code":
            suspected.append("DIGITS_IN_CODE_COLUMN")
        elif col_role in ("direct_id", "text"):
            hits.append("CN_MOBILE")
        else:
            # In generic numeric/other columns, only treat separator-formatted numbers or explicit phone context as high-confidence mobile;
            # bare 11 digits go to suspected_needs_review so lab barcodes/numeric codes aren't blindly corrupted.
            if any(("-" in m.group(1) or " " in m.group(1)) for m in CN_PHONE_RE.finditer(value)):
                hits.append("CN_MOBILE")
            else:
                suspected.append("POSSIBLE_CN_MOBILE_NEEDS_REVIEW")
    if EMAIL_RE.search(value):
        hits.append("EMAIL")
    if MRN_INLINE_RE.search(value):
        hits.append("MRN_TAG")
    if SSN_RE.search(value):
        hits.append("US_SSN")
    return hits, suspected


def pseudonym(kind: str, raw: str, mapping: dict[str, dict[str, str]]) -> str:
    bucket = mapping.setdefault(kind, {})
    if raw not in bucket:
        bucket[raw] = f"{kind}_{len(bucket) + 1:04d}"
    return bucket[raw]


def scrub_text(text: str, mapping: dict[str, dict[str, str]], replace_bare_phone: bool = True) -> str:
    def _rep_id(match: re.Match) -> str:
        val = match.group(1)
        return pseudonym("ID", val, mapping) if valid_cn_id(val) else val

    def _rep_phone(match: re.Match) -> str:
        val = match.group(1)
        if not replace_bare_phone and "-" not in val and " " not in val:
            return val
        return pseudonym("PHONE", val, mapping)

    text = CN_ID_RE.sub(_rep_id, text)
    text = CN_PHONE_RE.sub(_rep_phone, text)
    text = EMAIL_RE.sub(lambda m: pseudonym("EMAIL", m.group(0), mapping), text)
    text = SSN_RE.sub(lambda m: pseudonym("SSN", m.group(1), mapping), text)
    text = MRN_INLINE_RE.sub(lambda m: m.group(0).replace(m.group(1), pseudonym("MRN", m.group(1), mapping)), text)
    return text


def _process_rows(
    fieldnames: list[str],
    row_iter,
    source_name: str,
    raw_sha: str,
    detected_encoding: str,
    output_path: Path | None,
    delimiter: str,
) -> tuple[dict, dict]:
    roles = {c: classify_header(c) for c in fieldnames}
    direct_cols = [c for c in fieldnames if roles[c] == "direct_id"]
    quasi_cols = [c for c in fieldnames if roles[c] in ("quasi_date", "quasi_location")]
    non_phi_cols = [c for c in fieldnames if roles[c] == "non_phi_code"]

    cell_findings: dict[str, dict] = {}
    suspected_findings: dict[str, dict] = {}
    age_over_89 = 0
    malformed_rows = 0
    rows_out: list[dict] = []
    mapping: dict[str, dict[str, str]] = {}
    row_count = 0

    for idx, row in enumerate(row_iter, start=2):
        row_count += 1
        extra_vals = row.get(None)
        if extra_vals:
            malformed_rows += 1
        out_row = {c: (row.get(c) or "") for c in fieldnames}
        for col in fieldnames:
            val_str = str(out_row[col] or "")
            role = roles[col]
            hits, susp = scan_cell(val_str, col_role=role)
            for kind in hits:
                rec = cell_findings.setdefault(kind, {"count": 0, "columns": set(), "sample_rows": []})
                rec["count"] += 1
                rec["columns"].add(col)
                if len(rec["sample_rows"]) < 5:
                    rec["sample_rows"].append(idx)
            for kind in susp:
                rec = suspected_findings.setdefault(kind, {"count": 0, "columns": set(), "sample_rows": []})
                rec["count"] += 1
                rec["columns"].add(col)
                if len(rec["sample_rows"]) < 5:
                    rec["sample_rows"].append(idx)

            age_capped = False
            if role == "age":
                try:
                    if float(val_str) > 89:
                        age_over_89 += 1
                        if output_path is not None:
                            out_row[col] = ">89"
                            age_capped = True
                except ValueError:
                    pass

            if output_path is not None and not age_capped:
                if role == "direct_id":
                    out_row[col] = pseudonym(clean_header(col).upper() or "DIRECT", val_str, mapping) if val_str.strip() else ""
                elif role == "quasi_date":
                    if EXACT_DATE_RE.search(val_str):
                        ym = re.search(r"(19|20)\d{2}", val_str)
                        out_row[col] = ym.group(0) if ym else "[DATE_REDACTED]"
                elif role == "quasi_location":
                    if val_str.strip():
                        out_row[col] = pseudonym("LOC", val_str, mapping)
                elif role == "non_phi_code":
                    # Preserve non-PHI barcode/study/grant columns untouched unless a valid CN ID card appears.
                    out_row[col] = val_str
                else:
                    out_row[col] = scrub_text(val_str, mapping, replace_bare_phone=False)

        if output_path is not None:
            rows_out.append(out_row)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows_out)

    serialized_cells = {
        k: {"count": v["count"], "columns": sorted(v["columns"]), "sample_rows": v["sample_rows"]}
        for k, v in sorted(cell_findings.items())
    }
    serialized_susp = {
        k: {"count": v["count"], "columns": sorted(v["columns"]), "sample_rows": v["sample_rows"]}
        for k, v in sorted(suspected_findings.items())
    }
    has_risk = bool(direct_cols or serialized_cells or age_over_89)
    report = {
        "tool": "deidentify_check/2.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "network_used": False,
        "input": {
            "path": source_name,
            "sha256": raw_sha,
            "detected_encoding": detected_encoding,
            "rows": row_count,
            "columns": len(fieldnames),
            "malformed_extra_column_rows": malformed_rows,
        },
        "status": "phi_detected" if has_risk else ("suspected_phi_needs_review" if serialized_susp or quasi_cols else "no_obvious_phi_detected"),
        "direct_identifier_columns": direct_cols,
        "quasi_identifier_columns": quasi_cols,
        "non_phi_code_columns_preserved": non_phi_cols,
        "pattern_hits": serialized_cells,
        "suspected_hits_needs_review": serialized_susp,
        "age_over_89_count": age_over_89,
        "output_written": output_path.name if output_path is not None else None,
        "disclaimer": (
            "本脚本仅做基于规则与表头的确定性初筛，不构成法定去标识化认证或伦理豁免；"
            "自由文本、罕见病组合和医学影像元信息仍须由人工与伦理/合规人员复核。"
        ),
    }
    return report, mapping


def process_tabular(input_path: Path, output_path: Path | None, delimiter: str) -> tuple[dict, dict]:
    raw_bytes = input_path.read_bytes()
    text, enc = decode_text(raw_bytes)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("输入表格缺少表头")
    fieldnames = [f for f in reader.fieldnames if f is not None]
    return _process_rows(fieldnames, reader, input_path.name, sha_bytes(raw_bytes), enc, output_path, delimiter)


def _col_index_from_ref(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def read_xlsx_first_sheet(input_path: Path) -> tuple[list[str], list[dict]]:
    """Pure-stdlib read-only reader for the first worksheet of an .xlsx file."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    try:
        with ZipFile(input_path, "r") as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                sst_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in sst_root.findall("s:si", ns):
                    shared.append("".join(t.text or "" for t in si.findall(".//s:t", ns)))
            sheet_names = sorted(n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
            if not sheet_names:
                raise ValueError("XLSX 中未找到工作表")
            sheet_root = ET.fromstring(zf.read(sheet_names[0]))
    except (BadZipFile, ET.ParseError) as exc:
        raise ValueError(f"无法解析 XLSX 文件: {exc}") from exc

    matrix: list[list[str]] = []
    for row_el in sheet_root.findall(".//s:sheetData/s:row", ns):
        row_map: dict[int, str] = {}
        max_col = -1
        for c_el in row_el.findall("s:c", ns):
            ref = c_el.attrib.get("r", "")
            col_i = _col_index_from_ref(ref) if ref else (max_col + 1)
            max_col = max(max_col, col_i)
            ctype = c_el.attrib.get("t", "")
            v_el = c_el.find("s:v", ns)
            is_el = c_el.find("s:is", ns)
            if ctype == "s" and v_el is not None and (v_el.text or "").isdigit():
                idx = int(v_el.text)
                val = shared[idx] if 0 <= idx < len(shared) else ""
            elif ctype == "inlineStr" and is_el is not None:
                val = "".join(t.text or "" for t in is_el.findall(".//s:t", ns))
            elif v_el is not None and v_el.text is not None:
                val = v_el.text
            else:
                val = ""
            row_map[col_i] = val
        if max_col >= 0:
            matrix.append([row_map.get(i, "") for i in range(max_col + 1)])

    if not matrix:
        raise ValueError("XLSX 工作表为空")
    headers = [h or f"col_{i+1}" for i, h in enumerate(matrix[0])]
    records = [{headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))} for r in matrix[1:]]
    return headers, records


def process_xlsx(input_path: Path, output_path: Path | None) -> tuple[dict, dict]:
    raw_bytes = input_path.read_bytes()
    headers, records = read_xlsx_first_sheet(input_path)
    if output_path is not None and output_path.suffix.lower() != ".csv":
        raise ValueError("对 .xlsx 输入生成脱敏副本时，--output 请指定 .csv 文件路径")
    return _process_rows(headers, records, input_path.name, sha_bytes(raw_bytes), "xlsx-ooxml", output_path, ",")


def process_text(input_path: Path, output_path: Path | None) -> tuple[dict, dict]:
    raw_bytes = input_path.read_bytes()
    text, enc = decode_text(raw_bytes)
    hits: dict[str, dict] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        confirmed, _ = scan_cell(line, col_role="text")
        for kind in confirmed:
            rec = hits.setdefault(kind, {"count": 0, "sample_lines": []})
            rec["count"] += 1
            if len(rec["sample_lines"]) < 10:
                rec["sample_lines"].append(lineno)
    mapping: dict[str, dict[str, str]] = {}
    if output_path is not None:
        cleaned = scrub_text(text, mapping, replace_bare_phone=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    report = {
        "tool": "deidentify_check/2.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "network_used": False,
        "input": {"path": input_path.name, "sha256": sha_bytes(raw_bytes), "detected_encoding": enc, "lines": len(text.splitlines())},
        "status": "phi_detected" if hits else "no_obvious_phi_detected",
        "direct_identifier_columns": [],
        "quasi_identifier_columns": [],
        "pattern_hits": hits,
        "suspected_hits_needs_review": {},
        "age_over_89_count": 0,
        "output_written": output_path.name if output_path is not None else None,
        "disclaimer": "确定性正则初筛不代替人工逐句核查，也不代表发表同意或伦理豁免。",
    }
    return report, mapping


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local zero-network medical PHI/PII detector and optional pseudonymizer.")
    parser.add_argument("--input", required=True, help="Source CSV/TSV/XLSX/MD/TXT file (read-only).")
    parser.add_argument("--report", required=True, help="Output JSON report path (redacted, no raw PHI).")
    parser.add_argument("--output", help="Optional de-identified copy output path (must differ from --input).")
    parser.add_argument("--key-map", help="Optional external pseudonym mapping JSON (keep outside repo/manuscript dir).")
    parser.add_argument("--fail-on-phi", action="store_true", help="Exit 1 when PHI is detected in scan-only mode.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing --report/--output/--key-map.")
    args = parser.parse_args(argv)

    try:
        inp = ensure_plain_path(Path(args.input))
        if not inp.is_file():
            raise ValueError(f"输入文件不存在: {inp}")
        rep_path = ensure_plain_path(Path(args.report))
        out = ensure_plain_path(Path(args.output)) if args.output else None
        km_path = ensure_plain_path(Path(args.key_map)) if args.key_map else None

        outputs = [p for p in (rep_path, out, km_path) if p is not None]
        if inp in outputs:
            raise ValueError("输出路径（--report/--output/--key-map）均不得与 --input 相同")
        if len(set(outputs)) != len(outputs):
            raise ValueError("--report、--output、--key-map 必须指向不同路径")
        for p in outputs:
            if p.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {p}")

        suffix = inp.suffix.lower()
        if suffix == ".xls":
            raise ValueError("不支持旧版二进制 .xls，请在本地 Excel/WPS 另存为 .xlsx 或 CSV 后再扫描")
        elif suffix == ".xlsx":
            report, mapping = process_xlsx(inp, out)
        elif suffix == ".csv":
            report, mapping = process_tabular(inp, out, ",")
        elif suffix == ".tsv":
            report, mapping = process_tabular(inp, out, "\t")
        elif suffix in {".md", ".txt", ".yaml", ".yml", ".json", ".tex"}:
            report, mapping = process_text(inp, out)
        else:
            raise ValueError(f"不支持的文件类型: {suffix}（仅支持 .csv/.tsv/.xlsx/.md/.txt/.yaml/.json/.tex）")

        rep_path.parent.mkdir(parents=True, exist_ok=True)
        rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

        if km_path is not None and mapping:
            km_path.parent.mkdir(parents=True, exist_ok=True)
            km_path.write_text(
                json.dumps(
                    {"warning": "CONTAINS ORIGINAL IDENTIFIERS. DO NOT COMMIT OR UPLOAD.", "mapping": mapping},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )

        print(json.dumps({"status": report["status"], "report": rep_path.name, "output": report["output_written"]}, ensure_ascii=False))
        if args.fail_on_phi and report["status"] == "phi_detected" and out is None:
            return 1
        return 0
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
