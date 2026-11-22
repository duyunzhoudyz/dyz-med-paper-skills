#!/usr/bin/env python3
"""Generate a real Word (.docx) file with native OOXML Tracked Changes (<w:ins>/<w:del>).

Pure Python stdlib; zero external dependencies. Never modifies source files.
Features:
  - Activates Word Track Changes mode via word/settings.xml (<w:trackRevisions/>) and includes docProps/core.xml.
  - Strips internal [claim:...] / [evidence:...] audit markers by default (--keep-internal-markers to retain).
  - Sanitizes illegal XML 1.0 control characters and validates every generated XML part with ET.fromstring before writing.
  - Supports H1-H4 headings (no blank line required), unordered/ordered lists, bold/italic inline runs, and pipe tables.
  - Uses similarity-driven dynamic-programming paragraph alignment to prevent misaligned redlines on inserts/edits,
    and coalesces fragmented adjacent edits into readable phrase-level <w:del>/<w:ins> blocks.
  - Records input SHA-256 provenance and refuses silent overwrite without --force.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
</Relationships>"""

SETTINGS_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="{W_NS}">
  <w:trackRevisions/>
  <w:defaultTabStop w:val="720"/>
</w:settings>"""

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/>
        <w:sz w:val="22"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading4">
    <w:name w:val="heading 4"/>
    <w:rPr><w:b/><w:i/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:pPr><w:ind w:left="420" w:hanging="210"/></w:pPr>
  </w:style>
</w:styles>"""

XML_ILLEGAL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
INTERNAL_MARKER_RE = re.compile(r"\s*\[(?:claim|evidence):[^\]\n]+\]")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$")
UL_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
OL_RE = re.compile(r"^\s*(\d+[.)])\s+(.+)$")
TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
INLINE_STYLE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\n]+\*)")
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*|\s+|[^\s\u4e00-\u9fffA-Za-z0-9]")


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


def clean_xml_text(text: str) -> tuple[str, int]:
    cleaned, count = XML_ILLEGAL_RE.subn("", text)
    return cleaned, count


def strip_internal_markers(text: str, keep: bool) -> tuple[str, int]:
    if keep:
        return text, 0
    cleaned, count = INTERNAL_MARKER_RE.subn("", text)
    return cleaned, count


def parse_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_markdown_blocks(text: str, keep_internal_markers: bool = False) -> tuple[list[dict], dict]:
    """Line-oriented Markdown parser producing typed blocks: heading/paragraph/list/table."""
    sanitized, ctrl_removed = clean_xml_text(text)
    stripped, markers_removed = strip_internal_markers(sanitized, keep_internal_markers)
    lines = stripped.splitlines()
    blocks: list[dict] = []
    unsupported: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue

        # Math block warning (preserved as text paragraph, explicitly flagged)
        if s.startswith("$$"):
            buf = [line]
            i += 1
            while i < n and not lines[i].strip().startswith("$$"):
                buf.append(lines[i])
                i += 1
            if i < n:
                buf.append(lines[i])
                i += 1
            unsupported.append({"kind": "math_block", "line": i, "detail": "数学公式块未转为 OMML，按纯文本保留并需人工校对"})
            blocks.append({"type": "paragraph", "style": None, "text": " ".join(x.strip() for x in buf)})
            continue

        # Headings H1-H4 (works even without blank lines between headings/paragraphs)
        hm = HEADING_RE.match(s)
        if hm:
            lvl = len(hm.group(1))
            blocks.append({"type": "heading", "style": f"Heading{lvl}", "text": hm.group(2).strip()})
            i += 1
            continue

        # Pipe table
        if "|" in s and (i + 1) < n and TABLE_SEP_RE.match(lines[i + 1]):
            header = parse_table_row(s)
            i += 2
            rows = [header]
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(parse_table_row(lines[i]))
                i += 1
            width = max(len(r) for r in rows)
            norm_rows = [r + [""] * (width - len(r)) for r in rows]
            flat = " | ".join(" ; ".join(r) for r in norm_rows)
            blocks.append({"type": "table", "style": None, "rows": norm_rows, "text": flat})
            continue

        # Unordered / ordered list items (each item is its own paragraph)
        um = UL_RE.match(line)
        if um:
            blocks.append({"type": "list", "style": "ListParagraph", "text": f"• {um.group(1).strip()}"})
            i += 1
            continue
        om = OL_RE.match(line)
        if om:
            blocks.append({"type": "list", "style": "ListParagraph", "text": f"{om.group(1)} {om.group(2).strip()}"})
            i += 1
            continue

        # Regular paragraph: consume until blank line or next structural block
        buf = [s]
        i += 1
        while i < n:
            nxt = lines[i]
            ns = nxt.strip()
            if not ns or HEADING_RE.match(ns) or UL_RE.match(nxt) or OL_RE.match(nxt) or ns.startswith("$$"):
                break
            if "|" in ns and (i + 1) < n and TABLE_SEP_RE.match(lines[i + 1]):
                break
            buf.append(ns)
            i += 1
        blocks.append({"type": "paragraph", "style": None, "text": " ".join(buf)})

    meta = {
        "control_chars_removed": ctrl_removed,
        "internal_markers_stripped": markers_removed,
        "unsupported_blocks": unsupported,
    }
    return blocks, meta


def runs_xml(text: str, deleted: bool = False) -> str:
    """Render inline **bold** and *italic* into OOXML runs."""
    tag = "w:delText" if deleted else "w:t"
    parts = INLINE_STYLE_RE.split(text)
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        rpr = ""
        body = part
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            rpr = "<w:rPr><w:b/></w:rPr>"
            body = part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            rpr = "<w:rPr><w:i/></w:rPr>"
            body = part[1:-1]
        out.append(f'<w:r>{rpr}<{tag} xml:space="preserve">{escape(body)}</{tag}></w:r>')
    return "".join(out)


def coalesce_opcodes(opcodes: list[tuple[str, int, int, int, int]], old_tokens: list[str], new_tokens: list[str]) -> list[tuple[str, int, int, int, int]]:
    """Merge fragmented adjacent changes separated only by whitespace or 1 short token for readability."""
    merged: list[tuple[str, int, int, int, int]] = []
    idx = 0
    while idx < len(opcodes):
        op = opcodes[idx]
        if op[0] != "equal" and (idx + 2) < len(opcodes) and opcodes[idx + 1][0] == "equal" and opcodes[idx + 2][0] != "equal":
            _, ei1, ei2, ej1, ej2 = opcodes[idx + 1]
            bridge = "".join(old_tokens[ei1:ei2])
            if len(bridge.strip()) <= 3:
                # Absorb short bridge + following non-equal op into one replace span
                cur_i1, cur_j1 = op[1], op[3]
                nxt = opcodes[idx + 2]
                cur_i2, cur_j2 = nxt[2], nxt[4]
                idx += 3
                while (idx + 1) < len(opcodes) and opcodes[idx][0] == "equal" and opcodes[idx + 1][0] != "equal":
                    _, bi1, bi2, _, _ = opcodes[idx]
                    if len("".join(old_tokens[bi1:bi2]).strip()) <= 3:
                        cur_i2, cur_j2 = opcodes[idx + 1][2], opcodes[idx + 1][4]
                        idx += 2
                    else:
                        break
                merged.append(("replace", cur_i1, cur_i2, cur_j1, cur_j2))
                continue
        merged.append(op)
        idx += 1
    return merged


def diff_inline_xml(old_text: str, new_text: str, author: str, date_iso: str, rev_counter: list[int], stats: dict) -> str:
    if old_text == new_text:
        return runs_xml(new_text, deleted=False)
    old_tokens = TOKEN_RE.findall(old_text)
    new_tokens = TOKEN_RE.findall(new_text)
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)
    opcodes = coalesce_opcodes(matcher.get_opcodes(), old_tokens, new_tokens)
    parts: list[str] = []
    auth_attr = escape(author)
    date_attr = escape(date_iso)
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            parts.append(runs_xml("".join(old_tokens[i1:i2]), deleted=False))
        else:
            del_chunk = "".join(old_tokens[i1:i2])
            ins_chunk = "".join(new_tokens[j1:j2])
            if del_chunk:
                rev_counter[0] += 1
                stats["deletions"] += 1
                parts.append(
                    f'<w:del w:id="{rev_counter[0]}" w:author="{auth_attr}" w:date="{date_attr}">'
                    f"{runs_xml(del_chunk, deleted=True)}</w:del>"
                )
            if ins_chunk:
                rev_counter[0] += 1
                stats["insertions"] += 1
                parts.append(
                    f'<w:ins w:id="{rev_counter[0]}" w:author="{auth_attr}" w:date="{date_attr}">'
                    f"{runs_xml(ins_chunk, deleted=False)}</w:ins>"
                )
    return "".join(parts)


def wrap_paragraph(inner_xml: str, style: str | None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{inner_xml}</w:p>"


def render_table_xml(old_rows: list[list[str]] | None, new_rows: list[list[str]] | None, author: str, date_iso: str, rev_counter: list[int], stats: dict) -> str:
    rows_a = old_rows or []
    rows_b = new_rows or []
    n_rows = max(len(rows_a), len(rows_b))
    n_cols = max((len(r) for r in rows_a + rows_b), default=1)
    tr_xml: list[str] = []
    for r in range(n_rows):
        tc_xml: list[str] = []
        for c in range(n_cols):
            ov = rows_a[r][c] if r < len(rows_a) and c < len(rows_a[r]) else ""
            nv = rows_b[r][c] if r < len(rows_b) and c < len(rows_b[r]) else ""
            inner = diff_inline_xml(ov, nv, author, date_iso, rev_counter, stats)
            tc_xml.append(f"<w:tc><w:p>{inner}</w:p></w:tc>")
        tr_xml.append("<w:tr>" + "".join(tc_xml) + "</w:tr>")
    tbl_pr = (
        '<w:tblPr><w:tblBorders>'
        '<w:top w:val="single" w:sz="6" w:space="0" w:color="111827"/>'
        '<w:bottom w:val="single" w:sz="6" w:space="0" w:color="111827"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D1D5DB"/>'
        '</w:tblBorders></w:tblPr>'
    )
    return f"<w:tbl>{tbl_pr}{''.join(tr_xml)}</w:tbl>"


def block_similarity(a: dict, b: dict) -> float:
    if a["type"] != b["type"]:
        return 0.0
    if a["text"] == b["text"]:
        return 1.0
    return difflib.SequenceMatcher(None, a["text"], b["text"], autojunk=False).ratio()


def align_replace_blocks(old_slice: list[dict], new_slice: list[dict], threshold: float = 0.45) -> list[tuple[str, dict | None, dict | None]]:
    """Similarity-driven DP alignment so inserting a paragraph before edited ones never misaligns the whole section."""
    m, n = len(old_slice), len(new_slice)
    dp = [[0.0] * (n + 1) for _ in range(m + 1)]
    back = [[""] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        back[i][0] = "del"
    for j in range(1, n + 1):
        back[0][j] = "ins"

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sim = block_similarity(old_slice[i - 1], new_slice[j - 1])
            best_score = dp[i - 1][j]
            best_op = "del"
            if dp[i][j - 1] > best_score:
                best_score = dp[i][j - 1]
                best_op = "ins"
            if sim >= threshold and (dp[i - 1][j - 1] + sim) > best_score:
                best_score = dp[i - 1][j - 1] + sim
                best_op = "pair"
            dp[i][j] = best_score
            back[i][j] = best_op

    aligned: list[tuple[str, dict | None, dict | None]] = []
    i, j = m, n
    while i > 0 or j > 0:
        op = back[i][j]
        if op == "pair":
            aligned.append(("pair", old_slice[i - 1], new_slice[j - 1]))
            i -= 1
            j -= 1
        elif op == "del":
            aligned.append(("del", old_slice[i - 1], None))
            i -= 1
        else:
            aligned.append(("ins", None, new_slice[j - 1]))
            j -= 1
    aligned.reverse()
    return aligned


def build_core_xml(author: str, date_iso: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<cp:coreProperties xmlns:cp="{CP_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCTERMS_NS}" xmlns:xsi="{XSI_NS}">'
        f"<dc:title>Tracked Changes Manuscript Draft</dc:title>"
        f"<dc:creator>{escape(author)}</dc:creator>"
        f"<cp:lastModifiedBy>{escape(author)}</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{escape(date_iso)}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{escape(date_iso)}</dcterms:modified>'
        f"</cp:coreProperties>"
    )


def build_tracked_docx(
    old_text: str,
    new_text: str,
    output_path: Path,
    author: str = "Author",
    date_iso: str | None = None,
    keep_internal_markers: bool = False,
    old_name: str = "old.md",
    new_name: str = "new.md",
) -> dict:
    date_iso = date_iso or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    old_blocks, old_meta = parse_markdown_blocks(old_text, keep_internal_markers=keep_internal_markers)
    new_blocks, new_meta = parse_markdown_blocks(new_text, keep_internal_markers=keep_internal_markers)

    old_keys = [(b["type"], b["text"]) for b in old_blocks]
    new_keys = [(b["type"], b["text"]) for b in new_blocks]
    matcher = difflib.SequenceMatcher(None, old_keys, new_keys, autojunk=False)

    rev_counter = [0]
    stats = {
        "insertions": 0,
        "deletions": 0,
        "paragraphs_unchanged": 0,
        "paragraphs_modified": 0,
        "paragraphs_added": 0,
        "paragraphs_deleted": 0,
        "tables_rendered": 0,
    }
    body_parts: list[str] = []
    auth_attr = escape(author)
    date_attr = escape(date_iso)

    def emit_deleted_block(blk: dict) -> None:
        if blk["type"] == "table":
            stats["tables_rendered"] += 1
            body_parts.append(render_table_xml(blk["rows"], None, author, date_iso, rev_counter, stats))
            return
        rev_counter[0] += 1
        stats["deletions"] += 1
        stats["paragraphs_deleted"] += 1
        inner = f'<w:del w:id="{rev_counter[0]}" w:author="{auth_attr}" w:date="{date_attr}">{runs_xml(blk["text"], deleted=True)}</w:del>'
        body_parts.append(wrap_paragraph(inner, blk["style"]))

    def emit_inserted_block(blk: dict) -> None:
        if blk["type"] == "table":
            stats["tables_rendered"] += 1
            body_parts.append(render_table_xml(None, blk["rows"], author, date_iso, rev_counter, stats))
            return
        rev_counter[0] += 1
        stats["insertions"] += 1
        stats["paragraphs_added"] += 1
        inner = f'<w:ins w:id="{rev_counter[0]}" w:author="{auth_attr}" w:date="{date_attr}">{runs_xml(blk["text"], deleted=False)}</w:ins>'
        body_parts.append(wrap_paragraph(inner, blk["style"]))

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(j1, j2):
                blk = new_blocks[idx]
                if blk["type"] == "table":
                    stats["tables_rendered"] += 1
                    body_parts.append(render_table_xml(blk["rows"], blk["rows"], author, date_iso, rev_counter, stats))
                else:
                    body_parts.append(wrap_paragraph(runs_xml(blk["text"]), blk["style"]))
                    stats["paragraphs_unchanged"] += 1
        elif tag == "delete":
            for idx in range(i1, i2):
                emit_deleted_block(old_blocks[idx])
        elif tag == "insert":
            for idx in range(j1, j2):
                emit_inserted_block(new_blocks[idx])
        elif tag == "replace":
            for op, ob, nb in align_replace_blocks(old_blocks[i1:i2], new_blocks[j1:j2]):
                if op == "del" and ob is not None:
                    emit_deleted_block(ob)
                elif op == "ins" and nb is not None:
                    emit_inserted_block(nb)
                elif op == "pair" and ob is not None and nb is not None:
                    if ob["type"] == "table" and nb["type"] == "table":
                        stats["tables_rendered"] += 1
                        body_parts.append(render_table_xml(ob["rows"], nb["rows"], author, date_iso, rev_counter, stats))
                    else:
                        inner = diff_inline_xml(ob["text"], nb["text"], author, date_iso, rev_counter, stats)
                        body_parts.append(wrap_paragraph(inner, nb["style"]))
                        stats["paragraphs_modified"] += 1

    doc_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>{"".join(body_parts)}'
        f'<w:sectPr>'
        f'<w:pgSz w:w="11906" w:h="16838"/>'
        f'<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        f'<w:lnNumType w:countBy="1" w:restart="continuous"/>'
        f"</w:sectPr></w:body></w:document>"
    )
    core_xml = build_core_xml(author, date_iso)

    xml_parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELS,
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES,
        "word/settings.xml": SETTINGS_XML,
        "docProps/core.xml": core_xml,
        "word/document.xml": doc_xml,
    }
    # Mandatory well-formedness check before writing anything to disk.
    for part_name, xml_str in xml_parts.items():
        try:
            ET.fromstring(xml_str.encode("utf-8"))
        except ET.ParseError as exc:
            raise ValueError(f"生成的 OOXML 部件 {part_name} 非良构 XML: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        for part_name, xml_str in xml_parts.items():
            zf.writestr(part_name, xml_str)

    return {
        "tool": "export_tracked_docx/2.0",
        "native_ooxml_tracked_changes": True,
        "track_revisions_enabled_in_settings": True,
        "author": author,
        "date": date_iso,
        "inputs": [
            {"role": "old", "path": old_name, "sha256": sha_bytes(old_text.encode("utf-8"))},
            {"role": "new", "path": new_name, "sha256": sha_bytes(new_text.encode("utf-8"))},
        ],
        "output": output_path.name,
        "output_sha256": sha_bytes(output_path.read_bytes()),
        "revision_nodes": rev_counter[0],
        "stats": stats,
        "sanitization": {
            "control_chars_removed": old_meta["control_chars_removed"] + new_meta["control_chars_removed"],
            "internal_markers_stripped": old_meta["internal_markers_stripped"] + new_meta["internal_markers_stripped"],
            "keep_internal_markers": keep_internal_markers,
        },
        "unsupported_blocks": old_meta["unsupported_blocks"] + new_meta["unsupported_blocks"],
        "visual_review": "not_run",
        "note": "已启用 Word 原生修订模式（<w:trackRevisions/>），支持 H1-H4、列表、粗斜体与基础管道表格；数学公式、复杂合并表与期刊模板仍需在 Word 中目视校对。",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export native Word Tracked Changes (.docx) between two Markdown drafts.")
    parser.add_argument("--old", required=True, help="Baseline Markdown draft (read-only).")
    parser.add_argument("--new", required=True, help="Revised Markdown draft (read-only).")
    parser.add_argument("--output", required=True, help="Target tracked-changes .docx file.")
    parser.add_argument("--author", default="Author", help="Reviewer/Author name stored in w:author.")
    parser.add_argument("--date", help="ISO-8601 UTC timestamp for w:date.")
    parser.add_argument("--report", help="Optional JSON report path.")
    parser.add_argument("--keep-internal-markers", action="store_true", help="Retain [claim:...]/[evidence:...] tags in output.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing --output or --report.")
    args = parser.parse_args(argv)

    try:
        old_p = ensure_plain_path(Path(args.old))
        new_p = ensure_plain_path(Path(args.new))
        out_p = ensure_plain_path(Path(args.output))
        rep_p = ensure_plain_path(Path(args.report)) if args.report else None

        if not old_p.is_file() or not new_p.is_file():
            raise ValueError("--old 与 --new 文件必须存在")
        if out_p in (old_p, new_p) or (rep_p is not None and rep_p in (old_p, new_p, out_p)):
            raise ValueError("输出路径不能与源稿路径冲突")
        for target in [p for p in (out_p, rep_p) if p is not None]:
            if target.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {target}")

        report = build_tracked_docx(
            old_p.read_text(encoding="utf-8-sig"),
            new_p.read_text(encoding="utf-8-sig"),
            out_p,
            author=args.author,
            date_iso=args.date,
            keep_internal_markers=args.keep_internal_markers,
            old_name=old_p.name,
            new_name=new_p.name,
        )
        if rep_p is not None:
            rep_p.parent.mkdir(parents=True, exist_ok=True)
            rep_p.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
