"""只读核对明确映射的JSON结果与有定位的报告数值；不执行统计分析。"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path
import re
import sys


CONTEXT = ("population", "outcome", "timepoint", "groups", "effect_scale", "unit")
NUMERIC = {"estimate", "ci.lower", "ci.upper", "ci.level", "denominator.value",
           "events", "p.value"}
ROUNDING = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_path(root: Path, name: str) -> Path:
    """按工件合同解析路径；不得借符号链接或Windows路径逃逸。"""
    if (not isinstance(name, str) or not name or "\\" in name
            or ":" in name or name.startswith("/")
            or any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError("需要不含盘符、空段、.或..的正斜杠相对路径")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("路径逃出--root")
    return target


def load_json(data: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"重复JSON键: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"非有限JSON数值: {value}")

    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique,
                      parse_float=str, parse_constant=reject)


def number(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("需要有限数值或十进制字符串，不接受布尔值")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("无效十进制数值") from exc
    if not result.is_finite() or len(result.as_tuple().digits) > 100:
        raise ValueError("需要不超过100位的有限数值")
    if result and abs(result.adjusted()) > 100:
        raise ValueError("数值指数超出本工具范围")
    return result


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def issue(items, code, location, message):
    items.append({"code": code, "location": location, "message": message})


def get_field(row, field):
    value = row
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"缺少字段 {field}")
        value = value[part]
    return value


def exact_context(expected, actual) -> bool:
    # 禁止Python把True当作1，或忽略参考组方向。
    return type(expected) is type(actual) and expected == actual


def validate_result(row, location, artifacts, unverified):
    """检查本次被引用的结果；未知/缺少口径不能成为已核实结果。"""
    for key in CONTEXT:
        value = row.get(key)
        if key == "groups":
            valid = (isinstance(value, dict)
                     and text(value.get("comparison")) and text(value.get("reference")))
            valid = valid or (key in row and value is None
                              and text(row.get("not_applicable", {}).get(key)))
        else:
            valid = text(value)
        if not valid:
            issue(unverified, "result_context", f"{location}.{key}", "缺少明确口径")
    if row.get("execution_status") != "completed":
        issue(unverified, "analysis_unexecuted", location,
              "统计分析未完成或执行状态未知；数值相等不能证明已执行")
    source = row.get("source")
    if (not isinstance(source, dict) or not text(source.get("artifact_id"))
            or source["artifact_id"] not in artifacts
            or not text(source.get("locator"))):
        issue(unverified, "source_missing", location, "来源须绑定工件并有输出定位")
    elif not artifacts[source["artifact_id"]].get("_nonempty"):
        issue(unverified, "source_empty", location, "来源文件为空")
    for field in ("estimate", "ci", "denominator"):
        if field not in row:
            issue(unverified, "result_field_missing", f"{location}.{field}", "缺少最小结果字段")
        elif row[field] is None:
            if not text(row.get("not_applicable", {}).get(field)):
                issue(unverified, "applicability_unknown", f"{location}.{field}",
                      "null须附not_applicable理由；缺失不是不适用")
    for section, fields in (("ci", ("lower", "upper", "level")),
                            ("denominator", ("value",)), ("p", ("value",))):
        value = row.get(section)
        if value is None:
            continue
        if not isinstance(value, dict):
            issue(unverified, "result_type", f"{location}.{section}", "需要对象或明确不适用")
            continue
        try:
            values = {key: number(value.get(key)) for key in fields}
            if section == "ci":
                if values["lower"] > values["upper"] or not 0 < values["level"] < 1:
                    raise ValueError("区间上下界或置信水平无效")
            elif section == "p" and not 0 <= values["value"] <= 1:
                raise ValueError("P值必须在0到1之间")
            elif section == "denominator":
                if value.get("kind") not in ("count", "continuous") or not text(value.get("unit")):
                    raise ValueError("分母需kind=count/continuous与unit")
                if values["value"] < 0:
                    raise ValueError("分母不能为负")
                if value["kind"] == "count" and type(value["value"]) is not int:
                    raise ValueError("计数分母必须为JSON整数")
            if section in ("ci", "p"):
                if not all(text(value.get(key)) for key in ("adjustment", "method")):
                    raise ValueError("需分别声明adjustment和method")
        except ValueError as exc:
            issue(unverified, "result_type", f"{location}.{section}", str(exc))
    if row.get("estimate") is not None:
        try:
            number(row["estimate"])
            if row.get("effect_scale") == "count" and (
                    type(row["estimate"]) is not int or row["estimate"] < 0):
                raise ValueError("count估计值必须为非负JSON整数")
        except ValueError as exc:
            issue(unverified, "result_type", f"{location}.estimate", str(exc))
    if "events" in row and (type(row["events"]) is not int or row["events"] < 0):
        issue(unverified, "result_type", f"{location}.events", "events必须为非负JSON整数")


def compare_value(expected, reported, integer):
    if not isinstance(reported, dict) or "value" not in reported:
        raise ValueError("报告值需要{value, precision?}对象")
    if set(reported) - {"value", "precision"}:
        raise ValueError("未知比较参数，不接受隐含或任意绝对/相对容差")
    if integer:
        if type(expected) is not int or type(reported["value"]) is not int:
            raise ValueError("计数必须是JSON整数")
        if "precision" in reported:
            raise ValueError("整数计数不允许舍入或容差")
        return expected == reported["value"]
    left, right = number(expected), number(reported["value"])
    if "precision" not in reported:
        return left == right
    precision = reported["precision"]
    if (not isinstance(precision, dict) or set(precision) != {"places", "mode"}
            or type(precision["places"]) is not int
            or not 0 <= precision["places"] <= 12
            or not isinstance(precision["mode"], str) or precision["mode"] not in ROUNDING):
        raise ValueError("precision需要places=0..12与mode=half_up/half_even")
    quantum = Decimal(1).scaleb(-precision["places"])
    with localcontext() as ctx:
        ctx.prec = 220
        rounded = left.quantize(quantum, rounding=ROUNDING[precision["mode"]])
        if right != right.quantize(quantum):
            raise ValueError("报告值与声明小数位数不符")
    return rounded == right


def reconcile(results, reported, artifacts):
    """纯函数：只对显式清单覆盖范围对账，不推断临床意义或P/CI关系。"""
    differences, unverified, matched = [], [], []
    if (not isinstance(results, dict) or results.get("schema_version") != "1.0"
            or not isinstance(reported, dict) or reported.get("schema_version") != "1.0"):
        raise ValueError("结果和报告清单均需schema_version=1.0")
    rows, claims = results.get("results"), reported.get("reported_values")
    if not isinstance(rows, list) or not isinstance(claims, list):
        raise ValueError("需要results和reported_values数组")
    by_id = {}
    for index, row in enumerate(rows):
        if (not isinstance(row, dict) or not text(row.get("analysis_id"))
                or row["analysis_id"] in by_id):
            raise ValueError(f"results[{index}]分析ID缺失或重复")
        if not isinstance(row.get("not_applicable", {}), dict):
            raise ValueError(f"results[{index}].not_applicable需要对象")
        by_id[row["analysis_id"]] = row
    seen, used = set(), set()
    for index, claim in enumerate(claims):
        loc = f"reported_values[{index}]"
        if not isinstance(claim, dict) or not text(claim.get("id")) or claim["id"] in seen:
            raise ValueError(f"{loc}报告值ID缺失或重复")
        seen.add(claim["id"])
        locator = claim.get("locator")
        if (not isinstance(locator, dict) or not text(locator.get("artifact_id"))
                or locator["artifact_id"] not in artifacts
                or not text(locator.get("location"))):
            issue(unverified, "locator_missing", loc, "需绑定稿件/表格工件与明确位置")
        elif not artifacts[locator["artifact_id"]].get("_nonempty"):
            issue(unverified, "locator_empty", loc, "被报告文件为空")
        analysis_id = claim.get("analysis_id")
        if not isinstance(analysis_id, str) or analysis_id not in by_id:
            issue(unverified, "analysis_unknown", loc, "找不到明确分析ID")
            continue
        row = by_id[analysis_id]
        used.add(analysis_id)
        validate_result(row, f"results[{analysis_id}]", artifacts, unverified)
        context = claim.get("context")
        if not isinstance(context, dict):
            context = {}
        for field in CONTEXT:
            if field not in context:
                issue(unverified, "context_missing", f"{loc}.context.{field}", "不能凭数值猜测口径")
            elif not exact_context(row.get(field), context[field]):
                issue(differences, "context_mismatch", f"{loc}.context.{field}",
                      f"分析{analysis_id}的{field}口径不一致")
        values = claim.get("values")
        if not isinstance(values, dict) or not values:
            issue(unverified, "values_missing", loc, "没有可核对的报告值")
            continue
        for section, keys in (("ci", ("level", "adjustment", "method")),
                              ("p", ("adjustment", "method")),
                              ("denominator", ("kind", "unit"))):
            if not any(field.startswith(section + ".") for field in values):
                continue
            for key in keys:
                field = f"{section}.{key}"
                try:
                    source = get_field(row, field)
                    target = get_field(context, field)
                    if not exact_context(source, target):
                        issue(differences, "context_mismatch", f"{loc}.context.{field}", "统计口径不一致")
                except ValueError as exc:
                    issue(unverified, "context_missing", f"{loc}.context.{field}", str(exc))
        for field, value in values.items():
            location = f"{loc}.values.{field}"
            if field not in NUMERIC:
                issue(unverified, "field_unsupported", location, "未知数值字段；需人工核对")
                continue
            integer = (field == "events" or (field == "estimate" and row.get("effect_scale") == "count")
                       or (field == "denominator.value" and isinstance(row.get("denominator"), dict)
                           and row["denominator"].get("kind") == "count"))
            try:
                same = compare_value(get_field(row, field), value, integer)
            except (ValueError, InvalidOperation) as exc:
                issue(unverified, "value_unverified", location, str(exc))
                continue
            if same:
                matched.append({"claim_id": claim["id"], "analysis_id": analysis_id,
                                "field": field, "locator": locator})
            else:
                issue(differences, "value_mismatch", location,
                      f"分析{analysis_id}的{field}与报告值不一致；定位见该报告项locator")
    if not claims:
        issue(unverified, "empty_scope", "reported_values", "空清单不构成一致性通过")
    conclusion = "discrepant" if differences else "unverified" if unverified else "consistent"
    return {"conclusion": conclusion, "differences": differences, "unverified": unverified,
            "matched_values": matched, "reported_items": claims,
            "coverage": {"reported_items": len(claims), "matched_values": len(matched),
                         "referenced_analyses": sorted(used),
                         "unreported_analyses": sorted(set(by_id) - used)},
            "limitations": ["仅核对显式结构化清单；不证明人工摘录完整或定位语义真实",
                            "不解析任意Word/PDF、不核验模型适用性、不推断无效或因果",
                            "不转换HR/OR/RR，不以P值与CI的算术关系否定合法不同口径"]}


def run(manifest_path: Path, root: Path, report_name: str, record_name: str,
        check_id: str) -> tuple[dict, int]:
    """写新报告和独立绑定记录，不覆盖文件；错误通过异常交CLI处理。"""
    root = root.resolve()
    report_path = resolve_path(root, report_name)
    record_path = resolve_path(root, record_name)
    if report_path == record_path or report_path.exists() or record_path.exists():
        raise ValueError("报告和记录须为不同的新文件；拒绝覆盖")
    if not text(check_id):
        raise ValueError("check-id不能为空")
    manifest_bytes = manifest_path.read_bytes()
    manifest = load_json(manifest_bytes)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("artifacts"), list):
        raise ValueError("工件清单需要artifacts数组")
    artifacts, snapshots, inputs, public_artifacts = {}, {}, [], []
    for entry in manifest["artifacts"]:
        if (not isinstance(entry, dict) or not text(entry.get("id"))
                or entry["id"] in artifacts or not text(entry.get("version"))
                or not isinstance(entry.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
            raise ValueError("工件需要唯一id、version与真实小写SHA256")
        path = resolve_path(root, entry.get("path"))
        if path in (report_path, record_path) or path in snapshots:
            raise ValueError("重复实际输入路径或输出与输入冲突")
        data = path.read_bytes()
        if digest(data) != entry["sha256"]:
            raise ValueError(f"工件{entry['id']}哈希不符；不能沿用旧绑定")
        snapshots[path] = data
        artifacts[entry["id"]] = dict(entry, _nonempty=bool(data))
        public_artifacts.append(dict(entry))
        inputs.append({"artifact_id": entry["id"], "version": entry["version"],
                       "sha256": entry["sha256"]})
    roles = manifest.get("roles", {"results": "analysis-results", "reported": "reported-values"})
    if not isinstance(roles, dict) or set(roles) != {"results", "reported"}:
        raise ValueError("roles需要results/reported两个稳定工件ID")
    documents = []
    for role in ("results", "reported"):
        identity = roles[role]
        if not isinstance(identity, str) or identity not in artifacts:
            raise ValueError(f"缺少{role}工件映射")
        entry = artifacts[identity]
        if not entry["path"].lower().endswith(".json"):
            raise ValueError("机器入口仅支持JSON；保留原文件，显式规范化并绑定原件，不自动改名")
        documents.append(load_json(snapshots[resolve_path(root, entry["path"])]))
    report = reconcile(*documents, artifacts)
    if manifest_path.read_bytes() != manifest_bytes or any(
            path.read_bytes() != data for path, data in snapshots.items()):
        raise ValueError("运行中输入改变，不能形成稳定版本绑定")
    report.update({"tool": "check_result_consistency", "execution_status": "completed",
                   "applicability": "applicable", "inputs": inputs,
                   "manifest_sha256": digest(manifest_bytes)})
    report_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    check = {"id": check_id,
             "scope": {"domain": "result_consistency",
                       "description": "仅核对结构化reported_values清单覆盖的数值和口径；不验证模型及全文"},
             "inputs": inputs, "execution_status": "completed", "applicability": "applicable",
             "domain_result": {"namespace": "result_consistency", "value": report["conclusion"]},
             "report": {"path": report_name, "sha256": digest(report_bytes)},
             "checked_at": datetime.now(timezone.utc).isoformat()}
    record = {"schema_version": "1.1", "artifacts": public_artifacts, "checks": [check]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("xb") as handle:
        handle.write(report_bytes)
    # 记录不能嵌进被其哈希的报告；写失败时保留报告并明确失败，绝不制造完成回执。
    with record_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    code = {"consistent": 0, "discrepant": 1, "unverified": 3}[report["conclusion"]]
    return {"report": report_name, "record": record_name,
            "conclusion": report["conclusion"], "execution_status": "completed"}, code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--check-id", required=True)
    args = parser.parse_args(argv)
    try:
        summary, code = run(args.manifest, args.root, args.report, args.record, args.check_id)
    except (OSError, ValueError, UnicodeError, InvalidOperation) as exc:
        summary = {"execution_status": "failed", "domain_result": None,
                   "reason": str(exc), "limitations": "没有生成可登记的完成检查；可能保留已写报告"}
        code = 2
    print(json.dumps(summary, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
