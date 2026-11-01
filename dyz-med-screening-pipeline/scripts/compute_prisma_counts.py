#!/usr/bin/env python3
"""Recompute PRISMA sets from explicit normalized JSON; never decide eligibility."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


TOOL_VERSION = "1.0"
BRANCHES = ("database_register", "other_record", "other_direct")
SOURCE_BRANCH = {
    "database": "database_register",
    "register": "database_register",
    "other_record": "other_record",
}
TABLE_KEYS = {
    "records": ("record_id", "source_id", "source_record_id", "source_type",
                "pre_screen_decision", "decision", "decision_source"),
    "reports": ("report_id", "source_id", "source_report_id", "branch",
                "retrieval_status", "decision", "decision_source"),
    "studies": ("study_id", "basis"),
    "record_reports": ("record_id", "report_id", "basis"),
    "report_studies": ("report_id", "study_id", "basis"),
}
SCOPE = {
    "domain": "prisma_counts",
    "description": "Normalized row sets and declared mappings only; no search, "
                   "deduplication judgment, eligibility judgment or evidence appraisal.",
}


class InputError(ValueError):
    """An input cannot support a trustworthy counting run."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def local_path(root: Path, value: str) -> Path:
    """Resolve a contract path, rejecting lexical and symlink escapes."""
    if (not nonempty(value) or "\\" in value or ":" in value
            or PureWindowsPath(value).drive or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise InputError(f"Unsafe root-relative path: {value!r}")
    path = root.joinpath(*value.split("/")).resolve()
    if not path.is_relative_to(root):
        raise InputError(f"Path escapes --root: {value}")
    return path


def json_object(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise InputError(f"Non-finite JSON number: {value}")

    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                       parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise InputError("JSON top level must be an object")
    return value


def issue(code: str, location: str, message: str) -> dict:
    return {"code": code, "location": location, "message": message}


def validate_data(data: dict) -> tuple[list, list]:
    """Separate invalid input from known unresolved work; never repair either."""
    errors, unresolved = [], []

    def error(code, location, message):
        errors.append(issue(code, location, message))

    def pending(code, location, message):
        unresolved.append(issue(code, location, message))

    if data.get("schema_version") != "1.0":
        error("schema", "schema_version", "Expected normalized schema 1.0")
    if not nonempty(data.get("protocol_version")):
        error("protocol", "protocol_version", "Explicit protocol version required")
    reasons = data.get("exclusion_reasons")
    if (not isinstance(reasons, list) or any(not nonempty(x) for x in reasons)
            or len(reasons) != len(set(x for x in reasons if isinstance(x, str)))):
        error("reasons", "exclusion_reasons", "Unique predefined reason codes required")
    for table, fields in TABLE_KEYS.items():
        rows = data.get(table)
        if not isinstance(rows, list):
            error("table", table, "Required explicit array, including when empty")
            continue
        seen = set()
        key_fields = fields[:2] if table in ("record_reports", "report_studies") else fields[:1]
        for index, row in enumerate(rows):
            location = f"{table}[{index}]"
            if not isinstance(row, dict):
                error("row", location, "Expected object")
                continue
            if any(not nonempty(row.get(field)) for field in fields):
                error("field", location, f"Nonempty strings required: {', '.join(fields)}")
                continue
            key = tuple(row[field] for field in key_fields)
            if key in seen:
                error("duplicate_id", location, f"Duplicate identity: {key}")
            seen.add(key)
    if errors:
        return errors, unresolved

    records = {row["record_id"]: row for row in data["records"]}
    reports = {row["report_id"]: row for row in data["reports"]}
    studies = {row["study_id"]: row for row in data["studies"]}
    for rid, row in records.items():
        location = f"records/{rid}"
        pre, decision = row["pre_screen_decision"], row["decision"]
        if row["source_type"] not in SOURCE_BRANCH:
            error("unknown_source", location, "source_type must be database/register/other_record")
        if pre not in ("retain", "duplicate", "automation", "other"):
            error("unknown_decision", location, "Unknown pre_screen_decision")
        if decision not in ("include", "exclude", "uncertain", "pending", "conflict", "not_applicable"):
            error("unknown_decision", location, "Unknown title/abstract decision")
        if (pre == "retain") == (decision == "not_applicable"):
            error("conflicting_decision", location, "Only removed records use not_applicable")
        if pre == "duplicate":
            target = records.get(row.get("duplicate_of")) if isinstance(row.get("duplicate_of"), str) else None
            if target is None or target is row or target["pre_screen_decision"] != "retain":
                error("duplicate_target", location, "duplicate_of must name a retained record")
        elif row.get("duplicate_of") not in (None, ""):
            error("duplicate_target", location, "Only duplicate records may set duplicate_of")
        if decision in ("uncertain", "pending", "conflict"):
            pending("screening_unresolved", location, f"Recorded decision: {decision}")

    for pid, row in reports.items():
        location = f"reports/{pid}"
        retrieval, decision = row["retrieval_status"], row["decision"]
        if row["branch"] not in BRANCHES:
            error("unknown_branch", location, "Unknown report branch")
        if retrieval not in ("retrieved", "not_retrieved", "pending"):
            error("unknown_retrieval", location, "Unknown retrieval_status")
        if decision not in ("include", "exclude", "uncertain", "conflict", "pending", "not_applicable"):
            error("unknown_decision", location, "Unknown eligibility decision")
        if (retrieval == "retrieved") == (decision == "not_applicable"):
            error("conflicting_decision", location, "Only retrieved reports may have eligibility decisions")
        reason = row.get("primary_exclusion_reason", "")
        if decision == "exclude":
            if reason not in reasons:
                error("exclusion_reason", location, "One predefined primary reason required")
        elif reason not in (None, ""):
            error("exclusion_reason", location, "Non-excluded reports cannot carry an exclusion reason")
        if retrieval == "pending" or decision in ("pending", "uncertain", "conflict"):
            pending("eligibility_unresolved", location, "Retrieval or eligibility is unresolved")

    record_links, report_links, study_links = set(), set(), set()
    for row in data["record_reports"]:
        rid, pid = row["record_id"], row["report_id"]
        location = f"record_reports/{rid}/{pid}"
        if rid not in records or pid not in reports:
            error("unknown_mapping_id", location, "Mapping refers to an unknown record/report")
            continue
        record, report = records[rid], reports[pid]
        record_links.add(rid)
        report_links.add(pid)
        if report["branch"] != SOURCE_BRANCH.get(record["source_type"]):
            error("branch_conflict", location, "Cross-branch mapping needs explicit human reconciliation")
        if record["pre_screen_decision"] != "retain" or record["decision"] == "exclude":
            error("conflicting_mapping", location, "Removed/excluded record cannot advance to report retrieval")
        if record["decision"] != "include":
            pending("mapping_unresolved", location, "Record has not been explicitly advanced by human decision")
    for rid, row in records.items():
        if row["decision"] == "include" and rid not in record_links:
            pending("missing_report_mapping", f"records/{rid}", "Advanced record has no report mapping")
    for pid, row in reports.items():
        if row["branch"] != "other_direct" and pid not in report_links:
            pending("missing_record_mapping", f"reports/{pid}", "Record-derived report has no record mapping")
    for row in data["report_studies"]:
        pid, sid = row["report_id"], row["study_id"]
        if pid not in reports or sid not in studies:
            error("unknown_mapping_id", f"report_studies/{pid}/{sid}", "Unknown report/study")
        study_links.add(pid)
    for pid, row in reports.items():
        if row["decision"] == "include" and pid not in study_links:
            pending("missing_study_mapping", f"reports/{pid}", "Included report has no study mapping")
    expected = data.get("expected_counts", {})
    if not isinstance(expected, dict) or any(
            type(value) is not int or value < 0 for value in expected.values()):
        error("expected_counts", "expected_counts", "Expected nonnegative integer metric values")
    return errors, unresolved


def compute(data: dict, artifact_id: str) -> dict:
    """Produce deterministic members, filters and unit-preserving equations."""
    errors, unresolved = validate_data(data)
    report = {
        "schema_version": "1.0", "tool_version": TOOL_VERSION,
        "scope": SCOPE, "errors": errors, "unresolved": unresolved,
        "counts": {}, "exclusions_by_reason": {}, "equations": [],
        "differences": [], "finalizable": False,
    }
    if errors:
        report["status"] = "invalid"
        return report
    counts = report["counts"]

    def add(key, unit, members, query):
        members = sorted(set(members))
        counts[key] = {"unit": unit, "count": len(members), "member_ids": members,
                       "filter": query, "source_artifact_id": artifact_id}

    def equation(left, right):
        lhs = counts[left]["count"]
        rhs = sum(counts[key]["count"] for key in right)
        report["equations"].append({"left": left, "right": right,
                                    "unit": counts[left]["unit"],
                                    "left_count": lhs, "right_count": rhs,
                                    "difference": lhs - rhs})

    for branch in BRANCHES:
        if branch != "other_direct":
            rows = [r for r in data["records"] if SOURCE_BRANCH[r["source_type"]] == branch]
            selectors = {
                "records_identified": (lambda r: True, "all branch records"),
                "duplicates_removed": (lambda r: r["pre_screen_decision"] == "duplicate", "pre_screen_decision=duplicate"),
                "automation_removed": (lambda r: r["pre_screen_decision"] == "automation", "pre_screen_decision=automation"),
                "other_removed": (lambda r: r["pre_screen_decision"] == "other", "pre_screen_decision=other"),
                "records_awaiting_screening": (lambda r: r["decision"] == "pending", "decision=pending"),
                "records_screened": (lambda r: r["decision"] in ("include", "exclude", "uncertain", "conflict"), "decision in [include,exclude,uncertain,conflict]"),
                "records_excluded": (lambda r: r["decision"] == "exclude", "decision=exclude"),
                "records_advanced": (lambda r: r["decision"] == "include", "decision=include (human advance to retrieval)"),
                "records_unresolved": (lambda r: r["decision"] in ("uncertain", "conflict"), "decision in [uncertain,conflict]"),
            }
            for name, (select, query) in selectors.items():
                add(f"{branch}.{name}", "record", [r["record_id"] for r in rows if select(r)], f"branch={branch}; {query}")
            equation(f"{branch}.records_identified", [f"{branch}.{x}" for x in (
                "duplicates_removed", "automation_removed", "other_removed",
                "records_awaiting_screening", "records_screened")])
            equation(f"{branch}.records_screened", [f"{branch}.{x}" for x in (
                "records_excluded", "records_advanced", "records_unresolved")])
        rows = [r for r in data["reports"] if r["branch"] == branch]
        selectors = {
            "reports_sought": (lambda r: True, "all reports explicitly listed as sought"),
            "reports_not_retrieved": (lambda r: r["retrieval_status"] == "not_retrieved", "retrieval_status=not_retrieved"),
            "reports_retrieval_pending": (lambda r: r["retrieval_status"] == "pending", "retrieval_status=pending"),
            "reports_retrieved": (lambda r: r["retrieval_status"] == "retrieved", "retrieval_status=retrieved"),
            "reports_awaiting_assessment": (lambda r: r["decision"] == "pending", "decision=pending"),
            "reports_assessed": (lambda r: r["decision"] in ("include", "exclude", "uncertain", "conflict"), "decision in [include,exclude,uncertain,conflict]"),
            "reports_excluded": (lambda r: r["decision"] == "exclude", "decision=exclude"),
            "reports_included": (lambda r: r["decision"] == "include", "decision=include"),
            "reports_unresolved": (lambda r: r["decision"] in ("uncertain", "conflict"), "decision in [uncertain,conflict]"),
        }
        for name, (select, query) in selectors.items():
            add(f"{branch}.{name}", "report", [r["report_id"] for r in rows if select(r)], f"branch={branch}; {query}")
        equation(f"{branch}.reports_sought", [f"{branch}.{x}" for x in (
            "reports_not_retrieved", "reports_retrieval_pending", "reports_retrieved")])
        equation(f"{branch}.reports_retrieved", [f"{branch}.{x}" for x in (
            "reports_awaiting_assessment", "reports_assessed")])
        equation(f"{branch}.reports_assessed", [f"{branch}.{x}" for x in (
            "reports_excluded", "reports_included", "reports_unresolved")])
        report["exclusions_by_reason"][branch] = {}
        for reason in sorted(data["exclusion_reasons"]):
            members = sorted(r["report_id"] for r in rows if r["decision"] == "exclude" and r["primary_exclusion_reason"] == reason)
            report["exclusions_by_reason"][branch][reason] = {
                "unit": "report", "count": len(members), "member_ids": members,
                "source_artifact_id": artifact_id,
                "filter": {"branch": branch, "decision": "exclude", "primary_exclusion_reason": reason},
            }

    for source_type in sorted(SOURCE_BRANCH):
        add(f"identified.{source_type}", "record", [r["record_id"] for r in data["records"] if r["source_type"] == source_type], f"records.source_type={source_type}")
    included = {r["report_id"] for r in data["reports"] if r["decision"] == "include"}
    add("included.reports", "report", included, "reports.decision=include; union of all branches")
    add("included.studies", "study", [r["study_id"] for r in data["report_studies"] if r["report_id"] in included], "distinct report_studies.study_id where report_id in included.reports")
    report["source_rows"] = {
        table: {row[TABLE_KEYS[table][0]]: {
            "artifact_id": artifact_id, "json_pointer": f"/{table}/{i}",
            **{key: row[key] for key in TABLE_KEYS[table] if key.startswith("source_")},
        } for i, row in enumerate(data[table])}
        for table in ("records", "reports", "studies")
    }
    report["associations"] = {
        table: sorted(data[table], key=lambda r: tuple(r[k] for k in TABLE_KEYS[table][:2]))
        for table in ("record_reports", "report_studies")
    }
    for key, expected in sorted(data.get("expected_counts", {}).items()):
        if key not in counts:
            report["errors"].append(issue("unknown_metric", f"expected_counts/{key}", "Unknown metric, not silently ignored"))
        elif counts[key]["count"] != expected:
            report["differences"].append({"metric": key, "unit": counts[key]["unit"], "expected": expected, "computed": counts[key]["count"], "difference": counts[key]["count"] - expected})
    report["status"] = ("invalid" if report["errors"] else "unverified" if unresolved
                        else "discrepancy" if report["differences"] else "reconciled")
    report["finalizable"] = report["status"] == "reconciled"
    report["count_scope"] = "complete_declared_dataset" if not unresolved else "observed_only_not_final"
    return report


def load_inputs(root: Path, manifest_name: str) -> tuple[dict, list, dict]:
    manifest_path = local_path(root, manifest_name)
    raw = manifest_path.read_bytes()
    manifest = json_object(raw)
    if manifest.get("schema_version") != "1.0":
        raise InputError("Expected manifest schema_version 1.0")
    if not nonempty(manifest.get("id")) or not nonempty(manifest.get("version")):
        raise InputError("Manifest requires stable id and explicit version")
    declared = manifest.get("artifacts")
    if not isinstance(declared, list) or not declared:
        raise InputError("Manifest artifacts must be a nonempty array")
    artifacts = [{"id": manifest["id"], "version": manifest["version"],
                  "path": manifest_name, "sha256": digest(raw)}]
    snapshots = {manifest_path: raw}
    by_id = {}
    seen = {manifest["id"], "prisma-counts"}
    if manifest["id"] == "prisma-counts":
        raise InputError("prisma-counts is reserved for the output artifact")
    for item in declared:
        if not isinstance(item, dict) or any(not nonempty(item.get(k)) for k in ("id", "path", "version", "sha256")):
            raise InputError("Each artifact requires id/path/version/sha256")
        if item["id"] in seen:
            raise InputError(f"Duplicate/reserved artifact ID: {item['id']}")
        seen.add(item["id"])
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise InputError(f"Invalid SHA256: {item['id']}")
        path = local_path(root, item["path"])
        content = path.read_bytes()
        if digest(content) != item["sha256"]:
            raise InputError(f"Input hash mismatch: {item['id']}")
        snapshots[path] = content
        artifacts.append({k: item[k] for k in ("id", "path", "version", "sha256")})
        by_id[item["id"]] = (path, content)
    dataset_id, tool_id = manifest.get("dataset_artifact_id"), manifest.get("tool_artifact_id")
    if not isinstance(dataset_id, str) or not isinstance(tool_id, str) or dataset_id == tool_id:
        raise InputError("Distinct dataset_artifact_id and tool_artifact_id required")
    if dataset_id not in by_id or tool_id not in by_id:
        raise InputError("Dataset and tool IDs must refer to declared artifacts")
    if by_id[tool_id][0] != Path(__file__).resolve():
        raise InputError("tool_artifact_id must bind this actual executing script")
    return {"data": json_object(by_id[dataset_id][1]), "dataset_id": dataset_id}, artifacts, snapshots


def verify_unchanged(snapshots: dict) -> None:
    for path, raw in snapshots.items():
        if path.read_bytes() != raw:
            raise InputError(f"Input changed during counting: {path.name}")


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def run(root: Path, manifest_name: str, output_name: str, check_name: str,
        run_id: str) -> tuple[dict, int]:
    """Write new report/receipt only; existing files and inputs are never overwritten."""
    root = root.resolve()
    output, check_path = local_path(root, output_name), local_path(root, check_name)
    if output == check_path or output.exists() or check_path.exists():
        raise InputError("Output paths must be distinct new files; existing files are never overwritten")
    if not output.parent.is_dir() or not check_path.parent.is_dir():
        raise InputError("Output parent directories must already exist")
    if not nonempty(run_id):
        raise InputError("Nonempty run-id required")
    artifacts, snapshots = [], {}
    try:
        loaded, artifacts, snapshots = load_inputs(root, manifest_name)
        report = compute(loaded["data"], loaded["dataset_id"])
        verify_unchanged(snapshots)
    except (InputError, OSError, ValueError, TypeError, RecursionError) as exc:
        report = {"schema_version": "1.0", "tool_version": TOOL_VERSION,
                  "status": "invalid", "finalizable": False, "scope": SCOPE,
                  "counts": {}, "unresolved": [], "differences": [],
                  "errors": [issue("input_failure", "inputs", str(exc))]}
    inputs = [{"artifact_id": item["id"], "version": item["version"],
               "sha256": item["sha256"]} for item in artifacts]
    report["inputs"] = inputs
    raw = encoded(report)
    # The receipt hashes the completed report, never itself. Exclusive creation
    # prevents an existing source or historical result from being overwritten.
    with output.open("xb") as stream:
        stream.write(raw)
    failed = report["status"] == "invalid"
    check = {
        "id": run_id, "scope": SCOPE, "inputs": inputs,
        "execution_status": "failed" if failed else "completed",
        "applicability": "applicable",
        "domain_result": None if failed else {"namespace": "prisma_counts", "value": report["status"]},
        "report": {"path": output_name, "sha256": digest(raw)},
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if failed:
        check["reason"] = "Counting could not establish valid stable input; see report.errors"
    receipt = {"schema_version": "1.1", "artifacts": artifacts + [
        {"id": "prisma-counts", "version": run_id, "path": output_name, "sha256": digest(raw)}
    ], "checks": [check]}
    with check_path.open("xb") as stream:
        stream.write(encoded(receipt))
    code = {"reconciled": 0, "discrepancy": 1, "invalid": 1, "unverified": 3}[report["status"]]
    return {"status": report["status"], "exit_code": code, "report": output_name,
            "receipt": check_name, "errors": len(report["errors"]),
            "unresolved": len(report["unresolved"]), "differences": len(report["differences"])}, code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Root-relative binding manifest JSON")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", required=True, help="New root-relative count report JSON")
    parser.add_argument("--check-output", required=True, help="New root-relative contract receipt JSON")
    parser.add_argument("--run-id", required=True, help="Unique check ID and output version")
    args = parser.parse_args()
    try:
        summary, code = run(args.root, args.manifest, args.output, args.check_output, args.run_id)
    except (InputError, OSError, ValueError) as exc:
        summary, code = {"status": "invalid", "errors": [str(exc)]}, 1
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
