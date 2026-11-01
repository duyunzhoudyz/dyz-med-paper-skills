"""核对规范化公开题录身份；默认离线，不证明全文已读或论断获支持。"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import socket
import sys
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


HOSTS = {"crossref": "https://api.crossref.org",
         "pubmed": "https://eutils.ncbi.nlm.nih.gov"}
FIELDS = {"id", "doi", "pmid", "title", "year", "first_author", "journal"}
PURPOSE = "reference_identity_verification"
CATEGORY = "public_bibliographic_identifiers"
MAX_BODY = 2_000_000


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def path_at(root: Path, value: str) -> Path:
    if (not text(value) or "\\" in value or ":" in value or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError("引用路径须为不含绝对路径、盘符、空段、.或..的正斜杠相对路径")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("路径逃出--root")
    return path


def load_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"重复JSON键: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError("JSON含非有限值")

    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique,
                      parse_constant=reject)


def read_references(data: bytes, suffix: str) -> list[dict]:
    """仅支持本合同JSON/CSV；不自动解析RIS、BibTeX或任意URL。"""
    if suffix.lower() == ".json":
        document = load_json(data)
        if not isinstance(document, dict) or document.get("schema_version") != "1.0":
            raise ValueError("题录JSON需要schema_version字符串1.0")
        rows = document.get("references")
    elif suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV需要唯一表头")
        if set(reader.fieldnames) - FIELDS or not {"id", "title"} <= set(reader.fieldnames):
            raise ValueError("CSV只允许规范字段且需要id/title表头")
        rows = list(reader)
    else:
        raise ValueError("仅支持规范化JSON/CSV，不支持RIS/BibTeX或其他格式")
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("references须为最多100条的数组")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - FIELDS:
            raise ValueError("题录有未知字段；不得包含稿件正文、摘要、任意URL或凭据")
        if not text(row.get("id")) or row["id"] in seen:
            raise ValueError("题录id须非空且唯一")
        seen.add(row["id"])
        for key, value in row.items():
            if not isinstance(value, str) or len(value) > 4000:
                raise ValueError(f"{row['id']}.{key}须为不超过4000字符的字符串")
    return rows


def normalize(value):
    plain = html.unescape(re.sub(r"<[^>]*>", "", value))
    plain = unicodedata.normalize("NFKC", plain).casefold()
    return " ".join("".join(char if char.isalnum() else " " for char in plain).split())


def request_for(row):
    """仅构造两个固定主机的标识符请求；题名和作者从不外发。"""
    pmid, doi = row.get("pmid", "").strip(), row.get("doi", "").strip()
    if pmid:
        if not re.fullmatch(r"[1-9][0-9]{0,9}", pmid):
            return None, "invalid_pmid"
        provider, field, value = "pubmed", "pmid", pmid
        url = HOSTS[provider] + "/entrez/eutils/esummary.fcgi?" + urlencode(
            {"db": "pubmed", "id": pmid, "retmode": "json"})
    elif doi:
        if not re.fullmatch(r"10\.[0-9]{4,9}/[-._;()/A-Za-z0-9:+]+", doi):
            return None, "invalid_doi"
        provider, field, value = "crossref", "doi", doi.lower()
        url = HOSTS[provider] + "/works/" + quote(value, safe="")
    else:
        return None, "identifier_missing"
    return {"provider": provider, "destination": HOSTS[provider], "url": url,
            "field": field, "value": value}, None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HttpTransport:
    """无代理、凭据或Cookie读取，不跟随重定向；输入URL不进入此接口。"""
    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.last_request = None

    def __call__(self, query, timeout):
        # PubMed无key的请求节流；重试和多条查询共用同一时钟。
        if self.last_request is not None:
            time.sleep(max(0, .4 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = Request(query["url"], headers={"Accept": "application/json",
                          "User-Agent": "dyz-med-cnki-reference-verifier/1.0"})
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(MAX_BODY + 1)
                if len(raw) > MAX_BODY:
                    return {"status": response.status, "error": "response_too_large"}
                try:
                    body = load_json(raw)
                except (ValueError, UnicodeError):
                    return {"status": response.status, "error": "invalid_json"}
                return {"status": response.status, "body": body,
                        "response_sha256": sha(raw)}
        except HTTPError as exc:
            # 3xx/429/404均只记状态，不访问Location或登录页，也不回显响应体。
            status = exc.code
            exc.close()
            return {"status": status, "error": "http_error"}
        except (TimeoutError, socket.timeout):
            return {"status": None, "error": "timeout"}
        except (URLError, OSError):
            return {"status": None, "error": "network_error"}


class OfflineTransport:
    """重放受版本绑定的固定响应；不是实时网络证据。"""
    def __init__(self, document):
        if (not isinstance(document, dict) or document.get("schema_version") != "1.0"
                or not isinstance(document.get("responses"), list)):
            raise ValueError("离线响应需要schema_version=1.0及responses数组")
        self.responses = {}
        self.counts = {}
        for item in document["responses"]:
            if (not isinstance(item, dict) or not text(item.get("provider"))
                    or item["provider"] not in HOSTS or not text(item.get("identifier"))
                    or not isinstance(item.get("attempts"), list) or not item["attempts"]):
                raise ValueError("离线响应须有provider/identifier/非空attempts")
            key = (item["provider"], item["identifier"])
            if key in self.responses:
                raise ValueError("重复离线响应身份")
            for attempt in item["attempts"]:
                if not isinstance(attempt, dict):
                    raise ValueError("离线attempt须为对象")
                status = attempt.get("status")
                if status is not None and (type(status) is not int or not 100 <= status <= 599):
                    raise ValueError("HTTP状态须为整数或null")
                if "error" in attempt and not text(attempt["error"]):
                    raise ValueError("离线error须为非空字符串")
            self.responses[key] = item["attempts"]

    def __call__(self, query, timeout):
        key = (query["provider"], query["value"])
        attempts = self.responses.get(key)
        if not attempts:
            return {"status": None, "error": "offline_response_missing"}
        index = self.counts.get(key, 0)
        self.counts[key] = index + 1
        return dict(attempts[min(index, len(attempts) - 1)])


def metadata(query, response):
    """按单条Crossref work/PubMed ESummary提取最小字段，缺字段保留为空。"""
    if not isinstance(response, dict):
        raise ValueError("response_not_object")
    if query["provider"] == "crossref":
        value = response.get("message")
        if not isinstance(value, dict):
            raise ValueError("crossref_record_missing")
        title = value.get("title", [])
        journal = value.get("container-title", [])
        authors = value.get("author", [])
        published = value.get("published", {})
        dates = published.get("date-parts", []) if isinstance(published, dict) else []
        year = str(dates[0][0]) if (isinstance(dates, list) and dates
                                   and isinstance(dates[0], list) and dates[0]) else ""
        first = authors[0] if isinstance(authors, list) and authors else {}
        return {"doi": value.get("DOI", ""), "pmid": "",
                "title": title[0] if isinstance(title, list) and title else "",
                "journal": journal[0] if isinstance(journal, list) and journal else "",
                "year": year, "first_author": first.get("family", "") if isinstance(first, dict) else ""}
    result = response.get("result", {})
    value = result.get(query["value"]) if isinstance(result, dict) else None
    if not isinstance(value, dict) or value.get("error"):
        raise ValueError("pubmed_record_missing")
    ids = value.get("articleids", [])
    doi = next((item.get("value", "") for item in ids
                if isinstance(item, dict) and item.get("idtype") == "doi"), "") if isinstance(ids, list) else ""
    authors = value.get("authors", [])
    first = authors[0] if isinstance(authors, list) and authors else {}
    date = value.get("pubdate", "")
    year = re.search(r"\b[12][0-9]{3}\b", date) if isinstance(date, str) else None
    return {"doi": doi, "pmid": value.get("uid", ""), "title": value.get("title", ""),
            "journal": value.get("fulljournalname", ""), "year": year.group() if year else "",
            "first_author": first.get("name", "") if isinstance(first, dict) else ""}


def compare(row, actual):
    checks = []
    for field in ("doi", "pmid", "title", "year", "first_author", "journal"):
        expected, observed = row.get(field, "").strip(), actual.get(field, "")
        if not expected and field != "title":
            continue
        if not text(observed) or not expected:
            state = "unverified"
        elif field == "doi":
            state = "matched" if expected.lower() == observed.strip().lower() else "mismatch"
        elif field in ("pmid", "year"):
            state = "matched" if expected == observed.strip() else "mismatch"
        else:
            left, right = normalize(expected), normalize(observed)
            state = "matched" if left and left == right else "mismatch" if left and right else "unverified"
        checks.append({"field": field, "expected": expected, "observed": observed,
                       "status": state})
    states = {item["status"] for item in checks}
    status = "mismatch" if "mismatch" in states else "unverified" if "unverified" in states else "matched"
    return status, checks


def verify(rows, transport=None, timeout=10.0, max_attempts=1, mode="offline", blocked_reason=None):
    """每次失败有留痕；最多2次，仅超时/网络/5xx重试，不将404/429判虚构。"""
    if not 0 < timeout <= 30 or type(max_attempts) is not int or not 1 <= max_attempts <= 2:
        raise ValueError("timeout须>0且≤30秒，max-attempts仅1或2")
    records, sent = [], 0
    for row in rows:
        query, invalid = request_for(row)
        item = {"id": row["id"], "identity_status": "unverified", "fields": [],
                "attempts": [], "source": query, "checked_at": now(),
                "evidence_mode": mode, "access_scope": "metadata_only",
                "claim_support": {"status": "not_assessed", "reason": "题录身份不裁定论断支持关系"}}
        if blocked_reason or invalid or transport is None:
            item["reason"] = blocked_reason or invalid or "offline_no_response"
            records.append(item)
            continue
        response = None
        for attempt in range(max_attempts):
            response = transport(query, timeout)
            if mode == "online":
                sent += 1
            status, error = response.get("status"), response.get("error")
            item["attempts"].append({"number": attempt + 1, "at": now(),
                                     "http_status": status, "error": error,
                                     "response_sha256": response.get("response_sha256")})
            retryable = error in ("timeout", "network_error") or (
                type(status) is int and 500 <= status <= 599)
            if not retryable:
                break
        if response.get("status") != 200 or response.get("error"):
            item["reason"] = response.get("error") or f"http_{response.get('status')}"
        else:
            try:
                actual = metadata(query, response.get("body"))
                item["identity_status"], item["fields"] = compare(row, actual)
                item["differences"] = [field for field in item["fields"] if field["status"] == "mismatch"]
                item["missing_fields"] = [field["field"] for field in item["fields"] if field["status"] == "unverified"]
            except (ValueError, TypeError, AttributeError):
                item["reason"] = "unrecognized_or_missing_metadata"
        records.append(item)
    states = {item["identity_status"] for item in records}
    conclusion = ("mismatch" if "mismatch" in states else "unverified"
                  if not records or "unverified" in states else "matched")
    return {"tool": "verify_references/1.0", "mode": mode, "conclusion": conclusion,
            "records": records, "network_requests": sent,
            "limitations": ["仅题录身份；不证明全文已读、研究质量或六类论断支持裁定",
                            "无结果、404、缺DOI、429或网络失败均不证明文献虚构",
                            "离线固定响应只证明重放比较，非本次实时API核验",
                            "年份/作者/期刊差异可能涉及版本或格式，须人工复核"]}


def authorization_reason(auth, reference, artifacts, snapshots, root, queries):
    """结构/字节预检不认证人类身份；任一授权维度未知，整批零发送。"""
    if not isinstance(auth, dict) or auth.get("purpose") != PURPOSE or auth.get("content_category") != CATEGORY:
        return "authorization_purpose_or_category_unknown"
    destinations, fields = auth.get("destinations"), auth.get("fields")
    if (not isinstance(destinations, list) or not destinations
            or any(not isinstance(v, str) or v not in HOSTS.values() for v in destinations)
            or not isinstance(fields, list) or not fields
            or any(not isinstance(v, str) or v not in ("doi", "pmid") for v in fields)):
        return "authorization_scope_unknown"
    if any(q["destination"] not in destinations or q["field"] not in fields for q in queries):
        return "authorization_scope_insufficient"
    approval = auth.get("approval")
    if not isinstance(approval, dict) or approval.get("state") != "confirmed":
        return "human_approval_missing"
    target = {"artifact_id": reference["id"], "version": reference["version"], "sha256": reference["sha256"]}
    if approval.get("targets") != [target] or not text(approval.get("role")):
        return "approval_input_binding_missing"
    try:
        date = datetime.fromisoformat(approval.get("confirmed_at", "").replace("Z", "+00:00"))
        if date.tzinfo is None:
            return "approval_time_missing"
    except (ValueError, AttributeError, TypeError):
        return "approval_time_missing"
    source = approval.get("source")
    if (not isinstance(source, dict) or source.get("kind") != "human"
            or not all(text(source.get(key)) for key in ("actor_id", "statement", "locator"))):
        return "human_source_missing"
    evidence = source.get("reference")
    if not isinstance(evidence, dict):
        return "human_source_reference_missing"
    try:
        path = path_at(root, evidence.get("path"))
    except ValueError:
        return "human_source_path_invalid"
    if (path not in snapshots or not snapshots[path]
            or sha(snapshots[path]) != evidence.get("sha256")):
        return "human_source_not_bound"
    return None


def run(manifest_path: Path, root: Path, report_name: str, record_name: str,
        check_id: str, online=False, authorization_id=None, timeout=10.0,
        max_attempts=1, transport=None):
    root = root.resolve()
    report_path, record_path = path_at(root, report_name), path_at(root, record_name)
    if report_path == record_path or report_path.exists() or record_path.exists():
        raise ValueError("报告/记录须为两个新路径，拒绝覆盖")
    if not text(check_id):
        raise ValueError("check-id不能为空")
    if not 0 < timeout <= 30 or type(max_attempts) is not int or not 1 <= max_attempts <= 2:
        raise ValueError("timeout须>0且≤30秒，max-attempts仅1或2")
    raw_manifest = manifest_path.read_bytes()
    manifest = load_json(raw_manifest)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), list):
        raise ValueError("manifest需要artifacts数组")
    artifacts, snapshots, inputs = {}, {}, []
    for item in manifest["artifacts"]:
        if (not isinstance(item, dict) or not text(item.get("id")) or item["id"] in artifacts
                or not text(item.get("version")) or not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise ValueError("工件需唯一id、version、真实小写SHA256")
        path = path_at(root, item.get("path"))
        if path in snapshots or path in (report_path, record_path):
            raise ValueError("输入路径重复或与输出冲突")
        raw = path.read_bytes()
        if sha(raw) != item["sha256"]:
            raise ValueError(f"工件{item['id']}字节与声明hash不一致")
        artifacts[item["id"]] = dict(item)
        snapshots[path] = raw
        inputs.append({"artifact_id": item["id"], "version": item["version"], "sha256": item["sha256"]})
    roles = manifest.get("roles", {"references": "references"})
    if (not isinstance(roles, dict) or set(roles) - {"references", "responses"}
            or not text(roles.get("references")) or roles["references"] not in artifacts):
        raise ValueError("roles.references须指向已登记工件；可选roles.responses")
    reference = artifacts[roles["references"]]
    path = path_at(root, reference["path"])
    rows = read_references(snapshots[path], path.suffix)
    queries = [q for row in rows for q, reason in [request_for(row)] if q]
    blocked = None
    if online:
        if not text(authorization_id) or authorization_id not in artifacts:
            blocked = "authorization_missing"
        else:
            auth_path = path_at(root, artifacts[authorization_id]["path"])
            auth = load_json(snapshots[auth_path])
            blocked = authorization_reason(auth, reference, artifacts, snapshots, root, queries)
        if blocked:
            transport = None
        elif transport is None:
            transport = HttpTransport()
    else:
        # 离线模式绝不使用调用者传入的网络transport，也不解释输入URL。
        transport = None
        response_id = roles.get("responses")
        if response_id is not None:
            if not text(response_id) or response_id not in artifacts:
                raise ValueError("roles.responses未登记")
            transport = OfflineTransport(load_json(snapshots[path_at(root, artifacts[response_id]["path"])]))
    report = verify(rows, transport, timeout, max_attempts,
                    "online" if online else "offline", blocked)
    if manifest_path.read_bytes() != raw_manifest or any(p.read_bytes() != raw for p, raw in snapshots.items()):
        raise ValueError("运行中输入改变，不能生成当前版本检查记录")
    execution = "blocked" if blocked else "completed"
    report.update({"inputs": inputs, "execution_status": execution,
                   "applicability": "applicable", "manifest_sha256": sha(raw_manifest),
                   "authorization": {"artifact_id": authorization_id,
                                     "status": "blocked" if blocked else "recorded_not_authenticated" if online else "not_used",
                                     "reason": blocked}, "checked_at": now()})
    raw_report = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    check = {"id": check_id, "scope": {"domain": "reference_identity",
             "description": f"{report['mode']}模式，仅核对规范化题录标识/题名及提供的元数据；不裁定全文或论断支持"},
             "inputs": inputs, "execution_status": execution, "applicability": "applicable",
             "domain_result": None if blocked else {"namespace": "reference_identity", "value": report["conclusion"]},
             "report": {"path": report_name, "sha256": sha(raw_report)}, "checked_at": report["checked_at"]}
    if blocked:
        check["reason"] = blocked
    record = {"schema_version": "1.1", "artifacts": list(artifacts.values()), "checks": [check]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("xb") as handle:
        handle.write(raw_report)
    with record_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    code = 3 if blocked else {"matched": 0, "mismatch": 1, "unverified": 3}[report["conclusion"]]
    return {"report": report_name, "record": record_name, "mode": report["mode"],
            "execution_status": execution, "conclusion": report["conclusion"],
            "network_requests": report["network_requests"]}, code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--report", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--authorization", help="已登记授权JSON的artifact ID，不是路径或布尔值")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-attempts", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        summary, code = run(args.manifest, args.root, args.report, args.record, args.check_id,
                            args.online, args.authorization, args.timeout, args.max_attempts)
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        summary = {"execution_status": "failed", "domain_result": None, "reason": str(exc),
                   "limitations": "未形成可登记完成检查；后段写失败可能留下领域报告"}
        code = 2
    print(json.dumps(summary, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
