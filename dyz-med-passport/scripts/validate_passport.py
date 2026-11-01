#!/usr/bin/env python3
"""Read-only artifact binding checks; no scientific or human-consent certification."""

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re


HASH = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*\Z")
EXECUTION = {"not_run", "blocked", "failed", "completed"}
APPLICABILITY = {"applicable", "not_applicable", "unknown"}
APPROVAL = {"not_confirmed", "confirmed", "declined"}
ITEM_STATUS = {"open", "in_progress", "awaiting_verification", "verified_closed"}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def timestamp(value, require_time=False):
    if isinstance(value, datetime):
        return value.tzinfo is not None
    if isinstance(value, date):
        return not require_time
    if not text(value):
        return False
    try:
        if len(value) == 10 and not require_time:
            date.fromisoformat(value)
            return True
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def unique_mapping(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate mapping key: {key}")
        result[key] = value
    return result


def load_document(path):
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(raw, object_pairs_hook=unique_mapping)
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("Passport must be .json, .yaml or .yml")
    try:
        import yaml
    except ImportError as exc:
        raise ModuleNotFoundError("YAML requires existing PyYAML; nothing installed") from exc

    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        return unique_mapping(
            (loader.construct_object(key, deep=deep),
             loader.construct_object(value, deep=deep))
            for key, value in node.value
        )

    UniqueLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping
    )
    try:
        return yaml.load(raw, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValueError(str(exc)) from exc


class Validator:
    def __init__(self, root):
        self.root = root.resolve()
        self.report = {
            "validator": "passport-contract/1.1",
            "status": "valid", "freshness": "unverified",
            "errors": [], "warnings": [],
            "artifacts": [], "checks": [], "approvals": [],
        }
        self.artifacts = {}
        self.checks = {}
        self.states = []

    def issue(self, code, location, message, warning=False):
        bucket = "warnings" if warning else "errors"
        self.report[bucket].append(
            {"code": code, "location": location, "message": message}
        )

    def legacy(self, location):
        self.issue("LEGACY_UNBOUND", location,
                   "Record retained without verified current binding", warning=True)
        self.states.append("unverified")

    def file_hash(self, value, location, nonempty=False):
        if (not text(value) or "\\" in value or ":" in value
                or any(part in {"", ".", ".."} for part in value.split("/"))):
            self.issue("INVALID_PATH", location, "Use a root-relative POSIX file path")
            return None
        try:
            path = (self.root / value).resolve()
            if not path.is_relative_to(self.root):
                self.issue("PATH_ESCAPE", location, "Resolved path escapes root")
                return None
            data = path.read_bytes()
        except (OSError, ValueError, RuntimeError):
            self.issue("FILE_UNREADABLE", location, "Referenced file is missing or unreadable")
            return None
        if nonempty and not data:
            self.issue("EMPTY_EVIDENCE", location, "Evidence file must not be empty")
            return None
        return hashlib.sha256(data).hexdigest()

    def reference(self, value, location):
        if not isinstance(value, dict) or not digest(value.get("sha256")):
            self.issue("INVALID_REFERENCE", location, "Expected path and lowercase sha256")
            return "unverified"
        actual = self.file_hash(value.get("path"), location + ".path", nonempty=True)
        if actual is None:
            return "unverified"
        if actual != value["sha256"]:
            self.issue("HASH_MISMATCH", location, "Evidence bytes differ from recorded hash")
            return "stale"
        return "current"

    def records(self, document, name):
        values = document.get(name, [])
        if not isinstance(values, list):
            self.issue("INVALID_COLLECTION", name, "Expected a list")
            return []
        seen = set()
        result = []
        for index, value in enumerate(values):
            loc = f"{name}[{index}]"
            if not isinstance(value, dict):
                self.issue("INVALID_RECORD", loc, "Expected an object")
                continue
            identifier = value.get("id")
            if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
                self.issue("INVALID_ID", loc + ".id", "Expected a stable nonempty identifier")
                continue
            if identifier in seen:
                self.issue("DUPLICATE_ID", loc + ".id", f"Duplicate ID: {identifier}")
                continue
            seen.add(identifier)
            result.append((value, loc))
        return result

    def bindings(self, values, location):
        if not isinstance(values, list) or not values:
            self.issue("MISSING_BINDING", location, "Expected a nonempty input/target set")
            return "unverified"
        states = []
        seen = set()
        for index, binding in enumerate(values):
            loc = f"{location}[{index}]"
            if (not isinstance(binding, dict) or not text(binding.get("artifact_id"))
                    or not text(binding.get("version")) or not digest(binding.get("sha256"))):
                self.issue("INVALID_BINDING", loc, "Expected artifact_id/version/sha256")
                states.append("unverified")
                continue
            identifier = binding["artifact_id"]
            if identifier in seen:
                self.issue("DUPLICATE_INPUT", loc, "An artifact may occur only once per set")
                states.append("unverified")
            seen.add(identifier)
            artifact = self.artifacts.get(identifier)
            if artifact is None:
                self.issue("UNKNOWN_ARTIFACT", loc, f"Unknown artifact: {identifier}")
                states.append("unverified")
            elif artifact["actual"] is None or artifact["freshness"] == "unverified":
                states.append("unverified")
            elif (binding["sha256"] != artifact["actual"]
                  or binding["sha256"] != artifact["sha256"]
                  or binding["version"] != artifact["version"]):
                self.issue("STALE_BINDING", loc, "Input version or bytes changed", warning=True)
                states.append("stale")
            else:
                states.append("current")
        return freshness(states)

    def artifact(self, record, loc):
        actual = self.file_hash(record.get("path"), loc + ".path")
        bound = text(record.get("version")) and digest(record.get("sha256"))
        state = "current" if bound and actual is not None else "unverified"
        if not bound:
            self.legacy(loc)
            if record.get("sha256") not in (None, ""):
                self.issue("INVALID_HASH", loc + ".sha256", "Expected lowercase SHA256")
        elif actual is not None and actual != record["sha256"]:
            self.issue("HASH_MISMATCH", loc + ".sha256", "Artifact bytes changed")
            state = "stale"
        if "status" in record and record["status"] not in (
                "draft", "in_progress", "complete", "unknown"):
            self.issue("UNKNOWN_STATE", loc + ".status", "Unknown artifact status")
            state = "unverified"
        self.artifacts[record["id"]] = {
            "actual": actual, "version": record.get("version"),
            "sha256": record.get("sha256"), "freshness": state,
        }
        self.report["artifacts"].append({"id": record["id"], "freshness": state})
        self.states.append(state)

    def check(self, record, loc):
        before = len(self.report["errors"])
        execution = record.get("execution_status")
        applicability = record.get("applicability")
        result = {
            "id": record["id"], "execution_status": execution,
            "applicability": applicability, "domain_result": record.get("domain_result"),
        }
        if "execution_status" not in record:
            self.legacy(loc)
            state = "unverified"
        else:
            # Lists or mappings are invalid states too, not uncaught TypeErrors.
            if not isinstance(execution, str) or execution not in EXECUTION:
                self.issue("UNKNOWN_STATE", loc + ".execution_status", "Unknown execution state")
            if not isinstance(applicability, str) or applicability not in APPLICABILITY:
                self.issue("UNKNOWN_STATE", loc + ".applicability", "Unknown applicability")
            if applicability != "applicable" and not text(record.get("applicability_reason")):
                self.issue("MISSING_REASON", loc, "Non-applicable/unknown requires a reason")
            scope = record.get("scope")
            if (not isinstance(scope, dict) or not text(scope.get("domain"))
                    or not text(scope.get("description"))):
                self.issue("INVALID_SCOPE", loc + ".scope", "Expected domain and description")
            states = [self.bindings(record.get("inputs"), loc + ".inputs")]
            if execution == "completed":
                verdict = record.get("domain_result")
                if (not isinstance(verdict, dict) or not text(verdict.get("namespace"))
                        or not text(verdict.get("value"))):
                    self.issue("INVALID_RESULT", loc + ".domain_result", "Expected namespace/value")
            elif record.get("domain_result") is not None:
                self.issue("UNEXECUTED_RESULT", loc + ".domain_result", "Only completed has a result")
            if execution in ("blocked", "failed") and not text(record.get("reason")):
                self.issue("MISSING_REASON", loc + ".reason", "Blocked/failed requires a reason")
            if execution in ("completed", "failed") or record.get("report") is not None:
                states.append(self.reference(record.get("report"), loc + ".report"))
            if (execution in ("completed", "failed") or record.get("checked_at") is not None):
                if not timestamp(record.get("checked_at")):
                    self.issue("INVALID_DATE", loc + ".checked_at", "Expected ISO date/zoned time")
            if execution != "completed" or applicability == "unknown":
                states.append("unverified")
            if len(self.report["errors"]) != before:
                states.append("unverified")
            state = freshness(states)
        result["freshness"] = state
        self.checks[record["id"]] = result
        self.report["checks"].append(result)
        self.states.append(state)

    def approval(self, identifier, record):
        loc = f"human_approvals.{identifier}"
        if isinstance(record, str) and record in APPROVAL:
            self.legacy(loc)
            state = "unverified"
            decision = record
            provenance = "unverified"
        elif not isinstance(record, dict):
            self.issue("INVALID_APPROVAL", loc, "Approval requires an object, not a flag")
            state, decision, provenance = "unverified", None, "unverified"
        else:
            before = len(self.report["errors"])
            decision = record.get("state")
            provenance = "unverified"
            states = []
            if not isinstance(decision, str) or decision not in APPROVAL:
                self.issue("UNKNOWN_STATE", loc + ".state", "Unknown approval state")
                states.append("unverified")
            if decision in ("confirmed", "declined"):
                states.append(self.bindings(record.get("targets"), loc + ".targets"))
                if not text(record.get("role")):
                    self.issue("MISSING_PROVENANCE", loc + ".role", "Human role required")
                if not timestamp(record.get("confirmed_at"), require_time=True):
                    self.issue("INVALID_DATE", loc + ".confirmed_at", "Zoned confirmation time required")
                source = record.get("source")
                if (not isinstance(source, dict) or source.get("kind") != "human"
                        or not all(text(source.get(key)) for key in
                                   ("actor_id", "statement", "locator"))):
                    self.issue("MISSING_PROVENANCE", loc + ".source", "Explicit human source required")
                else:
                    states.append(self.reference(source.get("reference"), loc + ".source.reference"))
                if len(self.report["errors"]) == before:
                    provenance = "recorded_not_authenticated"
            else:
                states.append("unverified")
                if record.get("targets"):
                    states.append(self.bindings(record["targets"], loc + ".targets"))
            if len(self.report["errors"]) != before:
                states.append("unverified")
            state = freshness(states)
        self.report["approvals"].append({
            "id": identifier, "state": decision, "freshness": state,
            "provenance": provenance,
        })
        self.states.append(state)

    def open_item(self, record, loc):
        for field, allowed in (("severity", ("critical", "major", "minor")),
                               ("status", tuple(ITEM_STATUS))):
            if field not in record:
                self.legacy(loc + "." + field)
            elif record[field] not in allowed:
                self.issue("UNKNOWN_STATE", loc + "." + field, "Unknown issue state/severity")
        if record.get("status") == "verified_closed":
            reference = record.get("verification_check_id")
            check = self.checks.get(reference) if isinstance(reference, str) else None
            if (check is None or check["freshness"] != "current"
                    or check["execution_status"] != "completed"
                    or check["applicability"] != "applicable"):
                self.issue("UNVERIFIED_CLOSURE", loc, "Closure requires a current applicable check")
            self.states.append(self.reference(record.get("evidence"), loc + ".evidence"))

    def run(self, document):
        if not isinstance(document, dict):
            self.issue("INVALID_DOCUMENT", "$", "Passport must be an object")
            return self.finish()
        version = document.get("schema_version")
        if version in (None, "1.0"):
            self.legacy("schema_version")
        elif version != "1.1":
            self.issue("UNKNOWN_SCHEMA", "schema_version", "Supported: legacy 1.0 or 1.1")
        for record, loc in self.records(document, "artifacts"):
            self.artifact(record, loc)
        for record, loc in self.records(document, "checks"):
            self.check(record, loc)
        approvals = document.get("human_approvals", {})
        if not isinstance(approvals, dict):
            self.issue("INVALID_COLLECTION", "human_approvals", "Expected a mapping")
        else:
            for identifier, record in approvals.items():
                if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
                    self.issue("INVALID_ID", "human_approvals", "Invalid approval key")
                    continue
                self.approval(identifier, record)
        for record, loc in self.records(document, "open_items"):
            self.open_item(record, loc)
        if "history" in document and not isinstance(document["history"], list):
            self.issue("INVALID_COLLECTION", "history", "Expected an append-only history list")
        return self.finish()

    def finish(self):
        if self.report["errors"]:
            self.report["status"] = "invalid"
            self.states.append("unverified")
        self.report["freshness"] = freshness(self.states)
        return self.report


def freshness(states):
    if "stale" in states:
        return "stale"
    if not states or "unverified" in states:
        return "unverified"
    return "current"


def validate(passport_path: Path, root: Path | None = None) -> dict:
    """Validate declared local bindings without modifying files or approving claims."""
    path = Path(passport_path).resolve()
    validator = Validator(Path(root) if root is not None else path.parent)
    try:
        document = load_document(path)
    except ModuleNotFoundError as exc:
        validator.issue("DEPENDENCY_MISSING", "$", str(exc))
        validator.report["status"] = "blocked"
        return validator.report
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        validator.issue("READ_ERROR", "$", str(exc))
        return validator.finish()
    return validator.run(document)


def exit_code(report: dict) -> int:
    """Return the documented CLI code; zero never means scientific approval."""
    if report["status"] == "blocked":
        return 4
    if report["errors"]:
        return 1
    return 0 if report["freshness"] == "current" else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("passport", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    report = validate(args.passport, args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
