#!/usr/bin/env python3
"""Read-only evaluation receipt validation; never runs or judges a medical model.

Python 3.10+, standard library only. See tests/evaluation-protocol.md.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


STATUSES = {"pass", "fail", "blocked", "not_run"}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ReceiptError(ValueError):
    """A receipt or its evidence violates the evaluation contract."""


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    """Stable JSON for source-map and structured-input fingerprints."""
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False)


def prompt_for(case):
    """Only input is sent; expected/prohibited answers never enter the prompt."""
    value = case["input"]
    return value if isinstance(value, str) else canonical(value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"),
                           object_pairs_hook=unique_object,
                           parse_constant=lambda v: reject_constant(v))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReceiptError(f"{path.name}: {exc}") from exc
    require(isinstance(value, dict), f"{path.name}: expected JSON object")
    return value


def reject_constant(value):
    raise ReceiptError(f"non-finite JSON value: {value}")


def local_path(base, value):
    require(text(value), "path must be a nonempty relative string")
    parts = PurePosixPath(value)
    require(not parts.is_absolute() and ":" not in value and "\\" not in value
            and all(part not in {"", ".", ".."} for part in value.split("/")),
            f"unsafe relative path: {value}")
    path = (base / value).resolve()
    require(path.is_relative_to(base.resolve()), f"path escapes root: {value}")
    return path


def read_bytes(path):
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ReceiptError(f"{path.name}: {exc}") from exc


def evidence(base, ref):
    require(isinstance(ref, dict), "evidence reference must be an object")
    path = local_path(base, ref.get("path"))
    data = read_bytes(path)
    require(bool(data.strip()), f"empty evidence: {ref.get('path')}")
    require(ref.get("sha256") == digest(data),
            f"evidence hash mismatch: {ref.get('path')}")
    return path, data


def validate_manifest(manifest, root, check_current_source):
    require(type(manifest.get("schema_version")) is int
            and manifest["schema_version"] == 1, "manifest schema_version must be 1")
    require(manifest.get("algorithm") == "sha256", "manifest algorithm must be sha256")
    require(text(manifest.get("captured_at")), "manifest captured_at is required")
    sources, inputs = manifest.get("sources"), manifest.get("inputs")
    for label, mapping in (("sources", sources), ("inputs", inputs)):
        require(isinstance(mapping, dict) and mapping, f"manifest {label} required")
        for name, checksum in mapping.items():
            local_path(root, name)
            require(isinstance(checksum, str) and SHA256.fullmatch(checksum),
                    f"invalid SHA256: {name}")
    skills = {name.split("/")[0] for name in sources}
    require(all(name.startswith("dyz-med-") and "/" in name for name in sources),
            "sources must be files under dyz-med-* directories")
    require(manifest.get("skill_count") == len(skills)
            and manifest.get("source_file_count") == len(sources),
            "manifest source counts mismatch")
    require(manifest.get("source_sha256") == digest(canonical(sources).encode()),
            "manifest source fingerprint mismatch")
    for name, checksum in inputs.items():
        require(digest(read_bytes(local_path(root, name))) == checksum,
                f"frozen input changed: {name}")
    if check_current_source:
        current = {p.relative_to(root).as_posix(): digest(read_bytes(p))
                   for directory in root.glob("dyz-med-*") if directory.is_dir()
                   for p in directory.rglob("*") if p.is_file()}
        require(current == sources, "current sources differ from frozen manifest")
    return skills


def load_cases(result, manifest, root):
    fixtures = result.get("fixtures")
    require(isinstance(fixtures, list) and fixtures, "fixtures must be a nonempty list")
    require(all(text(p) for p in fixtures) and len(set(fixtures)) == len(fixtures),
            "duplicate or invalid fixture paths")
    cases = {}
    for name in fixtures:
        require(name in manifest["inputs"], f"fixture not frozen: {name}")
        fixture = read_json(local_path(root, name))
        require(fixture.get("verification_status") == "not_run",
                f"fixture must remain a specification: {name}")
        entries = fixture.get("cases")
        require(isinstance(entries, list) and entries, f"fixture cases missing: {name}")
        for case in entries:
            require(isinstance(case, dict) and text(case.get("id"))
                    and "/" not in case["id"] and "input" in case,
                    f"invalid fixture case: {name}")
            identity = f"{PurePosixPath(name).stem}/{case['id']}"
            require(identity not in cases, f"duplicate fixture identity: {identity}")
            cases[identity] = case
    return cases


def validate_execution(result, record, case, base, skills):
    for section, field in (("host", "name"), ("host", "version"), ("model", "id")):
        require(text(result[section].get(field)), f"executed record needs {section}.{field}")
    env = result["environment"]
    require(env.get("verified") is True and env.get("id") in {"library_only", "daily_full"},
            "executed record needs verified skill environment")
    actual = env.get("actual_skill_set")
    require(isinstance(actual, list) and all(text(s) for s in actual)
            and len(actual) == len(set(actual)), "actual skill set must be a unique list")
    require(skills.issubset(set(actual)), "evaluated source skills missing from environment")
    if env["id"] == "library_only":
        require(set(actual) == skills, "library_only contains other skills")
    _, catalog = evidence(base, env.get("evidence"))
    require(result["source_sha256"].encode() in catalog
            and all(s.encode() in catalog for s in actual),
            "environment evidence must bind actual catalog and source fingerprint")
    output_path, output = evidence(base, record.get("raw_output"))
    invocation_path, _ = evidence(base, record.get("invocation_evidence"))
    require(invocation_path != output_path, "output cannot replace invocation evidence")
    invocation = read_json(invocation_path)
    require(invocation.get("kind") == "host_execution", "not actual host execution evidence")
    require(invocation.get("origin") in {"host_export", "human_transcription"}
            and text(invocation.get("source_locator")), "execution provenance is required")
    prompt = prompt_for(case)
    bindings = {"run_id": result["run_id"], "case_id": record["id"],
                "source_sha256": result["source_sha256"],
                "input_sha256": digest(prompt.encode("utf-8")),
                "raw_output_sha256": digest(output),
                "host": result["host"], "model": result["model"],
                "environment_id": env["id"], "submitted_prompt": prompt}
    for field, expected in bindings.items():
        require(invocation.get(field) == expected, f"invocation binding mismatch: {field}")
    require(invocation.get("trace_complete") is True, "complete invocation trace required")
    require(text(invocation.get("session_id")) and text(invocation.get("executed_at")),
            "execution session and time are required")
    _, trace = evidence(base, invocation.get("trace"))
    require(prompt.encode("utf-8") in trace and output.strip() in trace,
            "raw host trace must contain the submitted input and actual output")
    invoked = invocation.get("actual_invoked_skills")
    require(isinstance(invoked, list) and all(text(s) for s in invoked),
            "actual_invoked_skills must be an observed list (empty is allowed)")
    require(all(s in actual and s.encode() in trace for s in invoked),
            "invoked skills absent from environment or host trace")
    if record["routing_status"] == "pass":
        require("expected_skills" in case, "no routing rubric in this fixture")
        require(set(case["expected_skills"]).issubset(set(invoked))
                and not set(case["excluded_skills"]).intersection(invoked),
                "routing PASS conflicts with observed skill invocations")
    if any(record[key] in {"pass", "fail"}
           for key in ("routing_status", "behavior_status")):
        reviewer = record.get("reviewer")
        require(isinstance(reviewer, dict) and text(reviewer.get("id"))
                and reviewer.get("kind") == "human"
                and reviewer.get("evidence_reviewed") is True,
                "human evidence reviewer required; model self-review is insufficient")


def validate(result_path: Path, root: Path, check_current_source: bool = False) -> dict:
    """Validate one immutable run; raise ReceiptError, never alter any input.

    A valid receipt can contain failures or no executions. It is not certification.
    Source checking is opt-in so later source edits do not rewrite history.
    """
    result_path, root = result_path.resolve(), root.resolve()
    base = result_path.parent
    result = read_json(result_path)
    require(type(result.get("schema_version")) is int
            and result["schema_version"] == 1, "schema_version must be 1")
    require(text(result.get("run_id")) and text(result.get("recorded_on")),
            "run identity and date are required")
    manifest = read_json(local_path(base, result.get("source_manifest")))
    skills = validate_manifest(manifest, root, check_current_source)
    require(result.get("source_sha256") == manifest["source_sha256"],
            "run source fingerprint mismatch")
    for name in ("host", "model", "environment"):
        require(isinstance(result.get(name), dict), f"{name} metadata required")
    require("name" in result["host"] and "version" in result["host"]
            and "id" in result["model"], "unknown host/model fields must be explicit null")
    env = result["environment"]
    require(env.get("id") in {"unverified", "library_only", "daily_full"}
            and type(env.get("verified")) is bool and "actual_skill_set" in env,
            "invalid environment metadata")
    fixtures = load_cases(result, manifest, root)
    records = result.get("cases")
    require(isinstance(records, list) and records, "cases must be a nonempty list")
    blockers = result.get("blockers", {})
    require(isinstance(blockers, dict), "blockers must be an object")
    for key, blocker in blockers.items():
        require(isinstance(blocker, dict) and text(blocker.get("reason")),
                f"blocker reason missing: {key}")
        path, _ = evidence(base, blocker.get("evidence"))
        probe = read_json(path)
        require(probe.get("kind") == "host_capability_probe"
                and probe.get("run_id") == result["run_id"],
                "blocker evidence is unrelated to this run")
    counts = {"cases": len(records), "attempted": 0, "submitted": 0, "executed": 0,
              "routing": dict.fromkeys(sorted(STATUSES), 0),
              "behavior": dict.fromkeys(sorted(STATUSES), 0)}
    seen = set()
    all_pass = True
    for record in records:
        require(isinstance(record, dict) and text(record.get("id")), "invalid case record")
        identity = record["id"]
        require(identity in fixtures, f"unknown namespaced case: {identity}")
        require(identity not in seen, f"duplicate case identity: {identity}")
        seen.add(identity)
        require(text(record.get("reason")), f"reason required: {identity}")
        require(all(key in record for key in ("raw_output", "invocation_evidence", "reviewer")),
                f"evidence and reviewer fields must be explicit: {identity}")
        for key in ("attempted", "submitted", "executed"):
            require(type(record.get(key)) is bool, f"{identity}: {key} must be boolean")
            counts[key] += int(record[key])
        require(not record["executed"] or record["submitted"], "execution needs submission")
        require(not record["submitted"] or record["attempted"], "submission needs an attempt")
        states = []
        for dimension in ("routing", "behavior"):
            state = record.get(f"{dimension}_status")
            require(isinstance(state, str) and state in STATUSES, f"unknown {dimension} status")
            counts[dimension][state] += 1
            states.append(state)
        require(record["executed"] or not {"pass", "fail"}.intersection(states),
                f"PASS/FAIL requires actual execution: {identity}")
        refs = record.get("blocker_ids", [])
        require(isinstance(refs, list) and all(text(r) and r in blockers for r in refs),
                f"unknown blocker: {identity}")
        require("blocked" not in states or refs, f"blocked case needs evidence: {identity}")
        if record["executed"]:
            validate_execution(result, record, fixtures[identity], base, skills)
        else:
            require(record["raw_output"] is None and record["invocation_evidence"] is None,
                    f"unexecuted case cannot claim model evidence: {identity}")
        required = "routing_status" if "expected_skills" in fixtures[identity] else "behavior_status"
        all_pass = all_pass and record[required] == "pass"
    require(seen == set(fixtures), "receipt must include every declared fixture case")
    if "summary" in result:
        require(result["summary"] == counts, "claimed summary differs from case records")
    return {"receipt_valid": True, "counts": counts, "required_dimensions_all_pass": all_pass,
            "limit": "Evidence consistency only; not clinical truth or proof of provenance."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check-current-source", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate(args.results, args.root, args.check_current_source)
    except (ReceiptError, OSError, UnicodeError) as exc:
        print(json.dumps({"receipt_valid": False, "errors": [str(exc)]}, ensure_ascii=True))
        return 1
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 3 if args.require_pass and not report["required_dimensions_all_pass"] else 0


if __name__ == "__main__":
    sys.exit(main())
