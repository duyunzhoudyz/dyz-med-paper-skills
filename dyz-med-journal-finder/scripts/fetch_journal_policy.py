#!/usr/bin/env python3
"""Fetch or offline-replay target journal author-guideline signals before writing/submission.

Security & provenance contract:
  - Defaults to OFFLINE mode (--snapshot local HTML/text file); zero network calls unless --online.
  - --online requires BOTH --url (https public host) AND --authorization (confirmed R2 human approval JSON
    explicitly allowlisting the URL and purpose `journal_policy_lookup`).
  - Online fetch disables environment proxies, refuses all HTTP 3xx redirects, resolves DNS and blocks
    non-global IPs (loopback, private, link-local, cloud metadata 169.254.169.254), requires HTTP 200 and
    text/HTML Content-Type, and caps body size at 2 MB.
  - Decodes via HTTP charset / <meta charset> / UTF-8 / GB18030 fallback so Chinese journals extract cleanly.
  - Refuses symlinks and silent overwrites unless --force is passed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_BYTES = 2_000_000
PURPOSE = "journal_policy_lookup"
ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/xhtml+xml")

TAG_RE = re.compile(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", re.IGNORECASE)
BLOCK_BREAK_RE = re.compile(r"</?(?:p|div|li|tr|h[1-6]|br|section|article)\b[^>]*>", re.IGNORECASE)
META_CHARSET_RE = re.compile(rb"charset\s*=\s*['\"]?([A-Za-z0-9._-]+)", re.IGNORECASE)

# ASCII-safe reporting guideline detector (works next to Chinese characters like "遵循STROBE或CONSORT").
GUIDELINE_RE = re.compile(
    r"(?<![A-Za-z])(CONSORT(?:\s*2025|\s*2010)?|STROBE|PRISMA(?:\s*2020|-ScR|-P)?|STARD(?:\s*2015|-AI)?|"
    r"CARE|TRIPOD(?:\+AI)?|SPIRIT(?:\s*2025)?|ARRIVE|COREQ|RECORD|SQUIRE|CHEERS|MOOSE)(?![A-Za-z])"
)

# Sentence-level patterns for English and Chinese journal author instructions.
ARTICLE_TYPE_RE = re.compile(
    r"\b(Original\s+(?:Article|Investigation|Research)|Research\s+Article|Brief\s+Report|Short\s+Communication|"
    r"Letter|Case\s+Report|Review|Systematic\s+Review|Clinical\s+Trial)\b|"
    r"(论著|临床研究|短篇论著|病例报告|综述|系统评价|述评)",
    re.IGNORECASE,
)

EN_WORD_LIMIT_RES = (
    re.compile(r"(?:word\s+limit(?:\s+of)?|maximum(?:\s+of)?|up\s+to|no\s+(?:more|longer)\s+than|<=|≤)\s*[:：]?\s*(\d{1,2},?\d{3}|\d{3,4})\s*words?", re.IGNORECASE),
    re.compile(r"(\d{1,2},?\d{3}|\d{3,4})\s*words?\s*(?:of\s+text|maximum|max|limit|or\s+(?:fewer|less))", re.IGNORECASE),
)
ZH_WORD_LIMIT_RES = (
    re.compile(r"(?:正文|全文|论著|稿件|字数)[^。；\n]{0,20}?(?:不超过|不大于|限|控制在|<=|≤|最多)\s*(\d{1,2},?\d{3}|\d{3,5})\s*[字词]"),
    re.compile(r"(?:不超过|限)\s*(\d{1,2},?\d{3}|\d{3,5})\s*[字词]"),
    re.compile(r"(\d{1,2},?\d{3}|\d{3,5})\s*[字词]以内"),
)
ABSTRACT_LIMIT_RES = (
    re.compile(r"abstract[^.;\n]{0,60}?(?:no\s+(?:more|longer)\s+than|maximum(?:\s+of)?|up\s+to|limit(?:\s+of)?|<=|≤)?\s*(\d{2,4})\s*words?", re.IGNORECASE),
    re.compile(r"摘要[^。；\n]{0,25}?(?:不超过|限|控制在|<=|≤)?\s*(\d{2,4})\s*[字词](?:以内|左右)?"),
)
REF_LIMIT_RES = (
    re.compile(r"(?:references?|citations?)[^.;\n]{0,30}?(?:up\s+to|maximum(?:\s+of)?|no\s+more\s+than|limit(?:\s+of)?|<=|≤)\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"(?:up\s+to|maximum(?:\s+of)?|no\s+more\s+than|with|<=|≤)?\s*(\d{1,3})\s*(?:references?|citations?)\b", re.IGNORECASE),
    re.compile(r"参考文献[^。；\n]{0,20}?(?:不超过|限|<=|≤|最多)?\s*(\d{1,3})\s*[篇条](?:以内)?"),
)
AI_POLICY_RE = re.compile(
    r"(?:artificial\s+intelligence|generative\s+AI|large\s+language\s+model|\bLLM\b|ChatGPT|AI[- ]assisted|AI\s+tools?|"
    r"ICMJE[^.;\n]{0,50}AI|人工智能|生成式\s*AI|大语言模型)",
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


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect_blocked", headers, fp)


def decode_bytes(raw: bytes, header_charset: str | None = None) -> tuple[str, str]:
    candidates: list[str] = []
    if header_charset:
        candidates.append(header_charset.strip().strip("\"'"))
    m = META_CHARSET_RE.search(raw[:4096])
    if m:
        candidates.append(m.group(1).decode("ascii", errors="ignore"))
    candidates.extend(["utf-8-sig", "utf-8", "gb18030", "latin-1"])
    seen = set()
    for enc in candidates:
        low = enc.lower()
        if not low or low in seen:
            continue
        seen.add(low)
        try:
            return raw.decode(low), low
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def split_blocks(raw_text: str) -> list[str]:
    marked = BLOCK_BREAK_RE.sub("\n", raw_text)
    stripped = TAG_RE.sub(" ", marked)
    unescaped = html.unescape(stripped)
    chunks: list[str] = []
    for line in unescaped.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean:
            continue
        # Further split long blocks into sentence-like clauses (preserving abbreviations like e.g. / Fig.).
        for seg in re.split(r"(?<=[。！？；])\s*|(?<=[.!?])\s+(?=[A-Z0-9])", clean):
            s = seg.strip()
            if s:
                chunks.append(s)
    return chunks


def extract_policy(raw_bytes: bytes, source_url: str, journal_name: str, mode: str, header_charset: str | None = None) -> dict:
    decoded, used_encoding = decode_bytes(raw_bytes, header_charset)
    sentences = split_blocks(decoded)
    full_text = "\n".join(sentences)

    word_mentions: list[dict] = []
    abstract_mentions: list[dict] = []
    ref_mentions: list[dict] = []
    ai_excerpts: list[str] = []
    seen_w, seen_a, seen_r = set(), set(), set()

    for sent in sentences:
        at_match = ARTICLE_TYPE_RE.search(sent)
        atype = at_match.group(0) if at_match else None
        is_abstract_only_clause = bool(re.search(r"\babstract\b|摘要", sent, re.IGNORECASE))

        # 1. Abstract limits
        for pat in ABSTRACT_LIMIT_RES:
            for m in pat.finditer(sent):
                val = m.group(1)
                key = (val, sent[:60])
                if key not in seen_a:
                    seen_a.add(key)
                    abstract_mentions.append({"value": val, "article_type_hint": atype, "evidence_snippet": sent[:220]})

        # 2. Body word limits (exclude matches that sit right inside an abstract phrase)
        for pat in EN_WORD_LIMIT_RES + ZH_WORD_LIMIT_RES:
            for m in pat.finditer(sent):
                val = m.group(1)
                prefix = sent[max(0, m.start() - 35):m.start()]
                if is_abstract_only_clause and re.search(r"abstract|摘要", prefix, re.IGNORECASE):
                    continue
                if val in {x["value"] for x in abstract_mentions if x["evidence_snippet"] == sent[:220]}:
                    continue
                key = (val, sent[:60])
                if key not in seen_w:
                    seen_w.add(key)
                    word_mentions.append({"value": val, "article_type_hint": atype, "evidence_snippet": sent[:220]})

        # 3. Reference limits
        for pat in REF_LIMIT_RES:
            for m in pat.finditer(sent):
                val = m.group(1)
                key = (val, sent[:60])
                if key not in seen_r:
                    seen_r.add(key)
                    ref_mentions.append({"value": val, "article_type_hint": atype, "evidence_snippet": sent[:220]})

        # 4. AI / LLM disclosure policy
        if AI_POLICY_RE.search(sent) and len(ai_excerpts) < 8:
            ai_excerpts.append(sent[:280])

    guidelines = sorted({re.sub(r"\s+", " ", m.group(1)).strip() for m in GUIDELINE_RE.finditer(full_text)})

    return {
        "tool": "fetch_journal_policy/2.0",
        "mode": mode,
        "journal_name": journal_name,
        "source_url": source_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "detected_encoding": used_encoding,
        "snapshot_sha256": sha_bytes(raw_bytes),
        "extracted_signals": {
            "word_limit_mentions": word_mentions[:10],
            "abstract_limit_mentions": abstract_mentions[:6],
            "reference_limit_mentions": ref_mentions[:6],
            "reporting_guidelines_mentioned": guidelines,
            "ai_policy_excerpts": ai_excerpts,
        },
        "verification_note": (
            "以上为从页面文本按句提取的候选线索（附原句证据）；不同文章类型限额可能不同，"
            "投稿前必须人工核对官方作者须知原文。"
        ),
    }


def validate_public_url(url: str) -> tuple[str, list[str]]:
    """Validate https URL and ensure every resolved DNS IP is strictly global (anti-SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("在线抓取仅允许有效的 https:// 官方期刊链接")
    host = parsed.hostname
    if host.lower() in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError(f"拒绝本地或内网主机: {host}")
    # Check literal IPv4/IPv6 before any DNS lookup so private/loopback/metadata IPs are rejected offline.
    try:
        lit_ip = ipaddress.ip_address(host)
    except ValueError:
        lit_ip = None
    if lit_ip is not None:
        if not lit_ip.is_global or lit_ip.is_private or lit_ip.is_loopback or lit_ip.is_link_local or lit_ip.is_multicast:
            raise ValueError(f"SSRF 防护拦截非公网目标地址: {host}")
        return url, [str(lit_ip)]
    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"无法解析主机 {host}: {exc}") from exc
    resolved_ips: list[str] = []
    for info in infos:
        ip_str = info[4][0]
        ip_obj = ipaddress.ip_address(ip_str)
        if not ip_obj.is_global or ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
            raise ValueError(f"SSRF 防护拦截非公网目标地址: {host} -> {ip_str}")
        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)
    if not resolved_ips:
        raise ValueError(f"主机未解析到任何公网地址: {host}")
    return url, resolved_ips


def validate_online_authorization(auth_path: Path, target_url: str) -> dict:
    """Validate explicit human authorization JSON before any online fetch."""
    ap = ensure_plain_path(auth_path)
    if not ap.is_file():
        raise ValueError(f"授权文件不存在: {ap}")
    raw = ap.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(doc, dict) or doc.get("purpose") != PURPOSE:
        raise ValueError(f"授权 purpose 必须为 {PURPOSE!r}")
    allowed = doc.get("allowed_urls")
    if not isinstance(allowed, list) or target_url not in allowed:
        raise ValueError("目标 URL 未列入授权文件的 allowed_urls 明确白名单")
    approval = doc.get("approval")
    if not isinstance(approval, dict) or approval.get("state") != "confirmed":
        raise ValueError("授权缺少 approval.state == 'confirmed'")
    source = approval.get("source")
    if not isinstance(source, dict) or source.get("kind") != "human" or not str(source.get("actor_id") or "").strip():
        raise ValueError("授权缺少有效人类来源（source.kind == 'human' 与 actor_id）")
    return {"path": ap.name, "sha256": sha_bytes(raw), "status": "recorded_not_authenticated"}


def fetch_online(url: str, timeout: float = 15.0) -> tuple[bytes, str | None, dict]:
    validate_public_url(url)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    req = Request(url, headers={"User-Agent": "dyz-med-journal-policy-checker/2.0", "Accept": "text/html,text/plain;q=0.9"})
    with opener.open(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        if status != 200:
            raise ValueError(f"非 200 响应状态: HTTP {status}")
        ctype = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype and ctype not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"不支持的 Content-Type: {ctype}（例如 PDF 请下载后用专用工具阅读）")
        charset = resp.headers.get_content_charset()
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("页面超过 2MB 上限")
        meta = {"http_status": status, "content_type": ctype or "unknown", "final_url": resp.geturl()}
        return data, charset, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract dated journal guideline & AI-policy signals (offline snapshot or authorized --online).")
    parser.add_argument("--journal", required=True, help="Target journal name.")
    parser.add_argument("--snapshot", help="Local saved HTML/text file for offline extraction (read-only).")
    parser.add_argument("--url", default="", help="Official https author-guidelines URL (required for --online).")
    parser.add_argument("--online", action="store_true", help="Explicitly allow live HTTPS fetch (requires --url and --authorization).")
    parser.add_argument("--authorization", help="Path to confirmed human authorization JSON (required for --online).")
    parser.add_argument("--output", required=True, help="Output journal-policy.json path.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting an existing --output file.")
    args = parser.parse_args(argv)

    try:
        out_p = ensure_plain_path(Path(args.output))
        if out_p.exists() and not args.force:
            raise ValueError(f"拒绝静默覆盖已有输出（如需覆盖请传 --force）: {out_p}")

        auth_meta = {"status": "not_used"}
        http_meta = None
        if args.online:
            if not args.url or not args.authorization:
                print("ERROR: --online 必须同时提供 --url 与 --authorization 人类授权文件", file=sys.stderr)
                return 3
            auth_meta = validate_online_authorization(Path(args.authorization), args.url)
            raw, header_charset, http_meta = fetch_online(args.url)
            mode = "online"
            source = args.url
        else:
            if not args.snapshot:
                print("ERROR: 离线模式需要 --snapshot（联网抓取请显式传 --online --url --authorization）", file=sys.stderr)
                return 2
            snap = ensure_plain_path(Path(args.snapshot))
            if snap == out_p:
                raise ValueError("--output 不能与 --snapshot 路径相同")
            raw = snap.read_bytes()
            header_charset = None
            mode = "offline_snapshot"
            source = args.url or snap.name

        policy = extract_policy(raw, source, args.journal, mode, header_charset=header_charset)
        policy["authorization"] = auth_meta
        if http_meta:
            policy["http"] = http_meta

        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "status": "ok",
            "mode": mode,
            "output": out_p.name,
            "guidelines": policy["extracted_signals"]["reporting_guidelines_mentioned"],
            "word_limits": len(policy["extracted_signals"]["word_limit_mentions"]),
        }, ensure_ascii=False))
        return 0
    except (ValueError, HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, (ValueError, json.JSONDecodeError)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
