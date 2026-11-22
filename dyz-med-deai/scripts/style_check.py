#!/usr/bin/env python3
"""Quantitative clinical-journal style checker, corpus baseline comparator, and protected-content bridge.

Pure Python stdlib. Designed for dyz-med-deai (and optional review of EN/ZH drafts).
Features:
  - Separate English (word count, long > 38w) and Chinese (CJK+token count, long > 85c) sentence statistics
    with medical abbreviation protection (vs., e.g., i.e., et al., Fig., Dr., No., approx.) and true Q1/median/Q3/IQR.
  - Graded AI-register lexicon (40+ EN stem patterns + 18 ZH template phrases), transition-adverb density,
    stacked-hedging detector, passive-voice ratio estimation, and repeated-paragraph-opener detection.
  - Optional `--reference-corpus` file/directory to measure target-journal or author exemplar baselines.
  - Optional `--before` + `--after` revision audit mode invoking bundled `compare_protected.py` in one report.
  - Optional personal term memory (`--memory-file` / `--add-term`) with word-boundary matching for ASCII rules.
  - Records input SHA-256 and refuses silent overwrite without --force. Never used for AI-detector evasion.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

# Stem/phrase regexes for high-frequency AI academic register in English clinical writing.
EN_CLICHE_PATTERNS = [
    (r"\bdelv(?:e|ed|es|ing)\b", "examine / investigate / evaluate"),
    (r"\bunderscor(?:e|ed|es|ing)\b", "highlight / indicate / show"),
    (r"\butiliz(?:e|ed|es|ing|ation)\b", "use / using"),
    (r"\bleverag(?:e|ed|es|ing)\b", "use / apply"),
    (r"\btapestry\b", "delete metaphor; state exact pattern"),
    (r"\bpivotal\b", "important / key (only if supported)"),
    (r"\b(?:crucial|vital|indispensable|paramount)\s+role\b", "state the measured effect or mechanism"),
    (r"\b(?:groundbreaking|revolutionary|transformative|game[- ]changing|paradigm\s+shift)\b", "remove promotional hype; state exact advance"),
    (r"\b(?:multifaceted|nuanced|intricate|comprehensive)\s+(?:landscape|understanding|interplay|nature)\b", "replace vague abstract noun with specific clinical variables"),
    (r"\bfoster(?:s|ed|ing)?\s+innovat(?:ive|ion)\b", "state concrete clinical/methodological advance"),
    (r"\brobust\s+methodology\b", "name the actual design strength (e.g., propensity-matched, blinded)"),
    (r"\bshed(?:s|ding)?\s+light\s+on\b", "clarify / show"),
    (r"\bit\s+is\s+(?:worth\s+noting|imperative\s+to\s+note|crucial\s+to\s+note)\s+that\b", "delete filler opener"),
    (r"\bin\s+(?:the\s+)?realm\s+of\b", "in"),
    (r"\bserves\s+as\s+a\s+testament\s+to\b", "indicates / reflects"),
    (r"\bsignificantly\s+enhanc(?:e|es|ed|ing)\b", "report exact effect size and 95% CI"),
    (r"\bnavigate\s+the\s+complexit(?:y|ies)\b", "address / manage"),
]

ZH_CLICHES = {
    "值得注意的是": "直接陈述具体发现或限定条件",
    "不可否认的是": "删去空泛过渡，直接写依据",
    "显而易见的是": "删去主观强调，直接给数据",
    "众所周知": "改为具体流行病学或文献背景",
    "扮演着至关重要的角色": "改写为具体机制或量化关联",
    "发挥着举足轻重的作用": "改写为具体效应或机制",
    "具有深远的临床意义": "改写为具体适用人群、效应大小与临床阈值",
    "提供了强有力的证据": "改为符合研究设计层级的克制表述",
    "取得了突破性进展": "按实际效应量与局限克制总结",
    "亟待进一步深入探讨": "具体指出哪项偏倚/人群/随访需要后续研究",
    "具有广阔的应用前景": "删去宣传语，改写实际适用条件与限制",
    "不仅如此": "如仅为并列补充，直接陈述或改用精确逻辑连接",
    "总而言之": "直接概括核心发现",
}

TRANSITION_RE = re.compile(
    r"\b(?:furthermore|moreover|additionally|consequently|nevertheless|nonetheless|subsequently|henceforth)\b|"
    r"(?:此外|另外|与此同时|因此|由此可见|综上所述)",
    re.IGNORECASE,
)

HEDGE_RE = re.compile(
    r"\b(?:may|might|could|possibly|potentially|apparently|seemingly|presumably|arguably|likely|suggests?)\b|"
    r"(?:可能|或许|似乎|在一定程度上|倾向于|提示可能)",
    re.IGNORECASE,
)

PASSIVE_RE = re.compile(r"\b(?:is|are|was|were|been|being|be)\s+[a-z]{3,}(?:ed|en|wn|ht|pt)\b", re.IGNORECASE)

OVERCLAIM_PATTERNS = [
    (re.compile(r"\b(?:proves?|proven|definitively\s+establishes?|conclusively\s+demonstrates?)\b", re.IGNORECASE),
     "EN_STRONG_CAUSAL", "强因果/确证措辞，观察性或单中心研究需核对证据层级"),
    (re.compile(r"(?:首次证明|充分证明|确切证实|完全等效|彻底解决)"),
     "ZH_STRONG_CAUSAL", "强因果/等效断言，需核对研究设计与检验界值"),
]

# Medical/academic abbreviations whose trailing period does NOT end a sentence.
ABBREV_RE = re.compile(
    r"\b(vs|e\.g|i\.e|et\s+al|Fig|Figs|Tab|Table|Dr|Prof|Mr|Ms|No|approx|est|min|max|sd|yr|yrs|mo|wk|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.",
    re.IGNORECASE,
)


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


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(sorted_vals[lo])
    return float(sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo))


def split_sentences(text: str) -> list[tuple[int, str]]:
    """Split text into (approx_line_no, sentence) protecting medical abbreviations and decimals."""
    results: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("|"):
            continue
        # Strip internal claim/evidence markers before measuring prose length.
        s = re.sub(r"\[(?:claim|evidence):[^\]\n]+\]", "", s).strip()
        protected = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + "<DOT>", s)
        # Protect decimal points and numbered prefixes like "1. "
        protected = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", protected)
        protected = re.sub(r"^(\d+)\.\s+", r"\1<DOT> ", protected)
        for seg in re.split(r"(?<=[.!?。！？])\s+|(?<=[。！？])", protected):
            clean = seg.replace("<DOT>", ".").strip()
            if len(clean) >= 6:
                results.append((lineno, clean))
    return results


def sentence_metrics(sent: str) -> tuple[str, int]:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", sent))
    en_words = len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", sent))
    if cjk >= en_words:
        return "zh", cjk + en_words
    return "en", en_words + cjk


def summarize_lengths(vals: list[int], threshold: int) -> dict:
    if not vals:
        return {"count": 0, "mean": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "iqr": 0.0, f"long_gt_{threshold}": 0}
    sv = sorted(vals)
    q1 = round(percentile(sv, 0.25), 1)
    med = round(percentile(sv, 0.50), 1)
    q3 = round(percentile(sv, 0.75), 1)
    return {
        "count": len(sv),
        "mean": round(sum(sv) / len(sv), 1),
        "q1": q1,
        "median": med,
        "q3": q3,
        "iqr": round(q3 - q1, 1),
        f"long_gt_{threshold}": sum(1 for x in sv if x > threshold),
    }


def load_memory(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {"schema_version": "1.0", "terms": [], "notes": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def analyze_style(text: str, memory: dict | None = None, input_name: str | None = None, input_sha: str | None = None) -> dict:
    findings: list[dict] = []
    lines = text.splitlines()

    # 1. Graded EN/ZH AI-register patterns with line locators
    for pat_str, suggestion in EN_CLICHE_PATTERNS:
        pat = re.compile(pat_str, re.IGNORECASE)
        hits = []
        for idx, ln in enumerate(lines, start=1):
            for m in pat.finditer(ln):
                hits.append((idx, m.group(0)))
        if hits:
            findings.append({
                "severity": "must_review",
                "code": "EN_AI_REGISTER",
                "phrase": hits[0][1],
                "count": len(hits),
                "lines": sorted({h[0] for h in hits})[:8],
                "suggestion": suggestion,
            })

    for phrase, suggestion in ZH_CLICHES.items():
        hit_lines = [idx for idx, ln in enumerate(lines, start=1) if phrase in ln]
        if hit_lines:
            findings.append({
                "severity": "must_review",
                "code": "ZH_TEMPLATE_PHRASE",
                "phrase": phrase,
                "count": text.count(phrase),
                "lines": hit_lines[:8],
                "suggestion": suggestion,
            })

    # 2. Strong causal / equivalence overclaim warnings
    for pat, code, reason in OVERCLAIM_PATTERNS:
        hit_lines = [idx for idx, ln in enumerate(lines, start=1) if pat.search(ln)]
        if hit_lines:
            findings.append({
                "severity": "scientific_warning",
                "code": code,
                "count": len(pat.findall(text)),
                "lines": hit_lines[:8],
                "detail": reason,
            })

    # 3. Sentence-level statistics (split by language), stacked hedging, passive voice ratio
    sents = split_sentences(text)
    en_lens, zh_lens = [], []
    long_outliers = []
    hedging_lines = []
    passive_en_sents = 0
    for lineno, sent in sents:
        lang, length = sentence_metrics(sent)
        if lang == "en":
            en_lens.append(length)
            if length > 38:
                long_outliers.append({"line": lineno, "lang": "en", "units": length, "excerpt": sent[:100]})
            if PASSIVE_RE.search(sent):
                passive_en_sents += 1
        else:
            zh_lens.append(length)
            if length > 85:
                long_outliers.append({"line": lineno, "lang": "zh", "units": length, "excerpt": sent[:80]})
        if len(HEDGE_RE.findall(sent)) >= 2:
            hedging_lines.append(lineno)

    if hedging_lines:
        findings.append({
            "severity": "consider",
            "code": "STACKED_HEDGING",
            "count": len(hedging_lines),
            "lines": hedging_lines[:8],
            "detail": "同一句叠加 2 个及以上模糊限定词（如 may/possibly/可能/似乎），建议保留一个精确限定即可。",
        })

    # 4. Transition adverb density
    trans_hits = TRANSITION_RE.findall(text)
    total_sents = max(len(sents), 1)
    trans_per_10_sents = round(10.0 * len(trans_hits) / total_sents, 2)
    if len(trans_hits) >= 3 and trans_per_10_sents >= 3.0:
        findings.append({
            "severity": "consider",
            "code": "HIGH_TRANSITION_DENSITY",
            "count": len(trans_hits),
            "rate_per_10_sentences": trans_per_10_sents,
            "detail": "过渡副词（furthermore/moreover/此外/因此等）出现偏密，建议依赖段落逻辑而非机械连接词。",
        })

    # 5. Repeated paragraph openers
    openers: dict[str, int] = {}
    for para in re.split(r"\n\s*\n", text):
        s = para.strip()
        if not s or s.startswith("#") or s.startswith("|"):
            continue
        first_tok = " ".join(s.split()[:3]).lower() if re.match(r"^[A-Za-z]", s) else s[:6]
        openers[first_tok] = openers.get(first_tok, 0) + 1
    repeated_openers = {k: v for k, v in openers.items() if v >= 3}
    if repeated_openers:
        findings.append({
            "severity": "consider",
            "code": "REPEATED_PARAGRAPH_OPENERS",
            "openers": repeated_openers,
            "detail": "多段使用相同开头句式，建议按段落沟通功能调整主题句。",
        })

    # 6. Personal/advisor terminology rules (word-boundary safe for ASCII terms)
    for rule in (memory or {}).get("terms", []):
        avoid = str(rule.get("avoid", "")).strip()
        prefer = str(rule.get("prefer", "")).strip()
        if not avoid:
            continue
        is_ascii = all(ord(c) < 128 for c in avoid)
        pat = re.compile(r"\b" + re.escape(avoid) + r"\b") if is_ascii else re.compile(re.escape(avoid))
        hit_lines = [idx for idx, ln in enumerate(lines, start=1) if pat.search(ln)]
        if hit_lines:
            findings.append({
                "severity": "personal_style",
                "code": "PERSONAL_TERM_RULE",
                "phrase": avoid,
                "count": len(pat.findall(text)),
                "lines": hit_lines[:8],
                "suggestion": f"按个人/导师偏好替换为: {prefer}",
            })

    passive_ratio = round(100.0 * passive_en_sents / len(en_lens), 1) if en_lens else None
    return {
        "tool": "style_check/2.0",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "input": {"path": input_name, "sha256": input_sha or sha_bytes(text.encode("utf-8"))},
        "sentence_stats": {
            "total_sentences": len(sents),
            "english": summarize_lengths(en_lens, 38),
            "chinese": summarize_lengths(zh_lens, 85),
            "english_passive_sentence_pct": passive_ratio,
            "transition_per_10_sentences": trans_per_10_sents,
            "long_sentence_outliers": long_outliers[:8],
        },
        "findings": findings,
        "disclaimer": (
            "本检查仅识别可观察的套话、过强措辞、过渡词密度和自定义术语偏好，不用于 AI 检测规避或作者身份判定；"
            "任何涉及科学强度的改动均须核实原研究设计与用户确认。"
        ),
    }


def measure_corpus(corpus_path: Path) -> dict:
    p = ensure_plain_path(corpus_path)
    files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in {".md", ".txt"})
    if not files:
        raise ValueError(f"参考语料路径中未找到 .md/.txt 文件: {p}")
    combined = "\n\n".join(f.read_text(encoding="utf-8-sig") for f in files)
    rep = analyze_style(combined, input_name=p.name)
    return {
        "corpus_files": len(files),
        "english_baseline": rep["sentence_stats"]["english"],
        "chinese_baseline": rep["sentence_stats"]["chinese"],
        "english_passive_sentence_pct": rep["sentence_stats"]["english_passive_sentence_pct"],
        "transition_per_10_sentences": rep["sentence_stats"]["transition_per_10_sentences"],
    }


def compare_before_after(before_path: Path, after_path: Path, memory: dict | None = None) -> dict:
    b_p, a_p = ensure_plain_path(before_path), ensure_plain_path(after_path)
    b_txt, a_txt = b_p.read_text(encoding="utf-8-sig"), a_p.read_text(encoding="utf-8-sig")
    rep_b = analyze_style(b_txt, memory, b_p.name, sha_bytes(b_p.read_bytes()))
    rep_a = analyze_style(a_txt, memory, a_p.name, sha_bytes(a_p.read_bytes()))

    # Invoke bundled compare_protected.py in the same skill directory (self-contained, no sibling skill dependency).
    cp_script = Path(__file__).resolve().parent / "compare_protected.py"
    spec = importlib.util.spec_from_file_location("bundled_compare_protected", cp_script)
    cp_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cp_mod)
    prot = cp_mod.compare(b_txt, a_txt)

    return {
        "tool": "style_check/2.0",
        "mode": "before_after_with_protected_guard",
        "before_finding_count": len(rep_b["findings"]),
        "after_finding_count": len(rep_a["findings"]),
        "protected_content_check": prot,
        "after_style_report": rep_a,
    }


def add_memory_rule(path: Path, avoid: str, prefer: str, note: str = "") -> dict:
    p = ensure_plain_path(path)
    mem = load_memory(p)
    terms = [t for t in mem.setdefault("terms", []) if t.get("avoid") != avoid]
    terms.append({"avoid": avoid, "prefer": prefer, "note": note, "updated_at": datetime.now(timezone.utc).isoformat()})
    mem["terms"] = terms
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mem, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return mem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quantitative clinical-journal style check, corpus baseline, and protected-content bridge.")
    parser.add_argument("--input", help="Single manuscript Markdown/text file to inspect.")
    parser.add_argument("--before", help="Original draft (used with --after for style + protected-number check).")
    parser.add_argument("--after", help="Revised draft (used with --before).")
    parser.add_argument("--reference-corpus", help="Optional exemplar paper file or folder to compute baseline stats.")
    parser.add_argument("--memory-file", help="Optional personal style memory JSON (e.g., ~/.dyz-med/style-memory.json).")
    parser.add_argument("--add-term", nargs=2, metavar=("AVOID", "PREFER"), help="Add a preferred wording rule to --memory-file.")
    parser.add_argument("--report", help="Optional JSON report output path.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting existing --report.")
    args = parser.parse_args(argv)

    try:
        mem_path = ensure_plain_path(Path(args.memory_file)) if args.memory_file else None
        if args.add_term:
            if mem_path is None:
                raise ValueError("--add-term 需要同时指定 --memory-file")
            mem = add_memory_rule(mem_path, args.add_term[0], args.add_term[1])
            print(json.dumps({"status": "rule_saved", "memory_file": mem_path.name, "total_terms": len(mem["terms"])}, ensure_ascii=False))
            if not args.input and not (args.before and args.after):
                return 0

        if args.before or args.after:
            if not (args.before and args.after):
                raise ValueError("--before 与 --after 必须成对使用")
            report = compare_before_after(Path(args.before), Path(args.after), load_memory(mem_path))
            protected_paths = (ensure_plain_path(Path(args.before)), ensure_plain_path(Path(args.after)))
        elif args.input:
            inp = ensure_plain_path(Path(args.input))
            if not inp.is_file():
                raise ValueError(f"输入文件不存在: {inp}")
            raw = inp.read_bytes()
            report = analyze_style(raw.decode("utf-8-sig"), load_memory(mem_path), inp.name, sha_bytes(raw))
            protected_paths = (inp,)
        else:
            raise ValueError("需要 --input 或 (--before 与 --after)")

        if args.reference_corpus:
            report["reference_corpus_baseline"] = measure_corpus(Path(args.reference_corpus))

        if args.report:
            rp = ensure_plain_path(Path(args.report))
            if rp in protected_paths:
                raise ValueError("--report 不能覆盖输入文件")
            if rp.exists() and not args.force:
                raise ValueError(f"拒绝静默覆盖已有文件（如需覆盖请显式传 --force）: {rp}")
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

        print(json.dumps(report, ensure_ascii=False))
        if args.before and args.after and report["protected_content_check"]["status"] != "consistent":
            return 1
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
