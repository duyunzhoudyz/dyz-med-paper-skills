#!/usr/bin/env python3
"""Read-only structure checks, not a host routing or token-budget evaluation.

Run: python scripts/validate_skills.py [--root PATH]
Uses the standard library and an existing PyYAML installation; installs nothing.
Checks Markdown local file/directory targets, not heading anchors or remote URLs.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:
    yaml = None


EXPECTED_SKILL_COUNT = 32
INLINE_LINK = re.compile(
    r"!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|(?:\\.|[^\s()]|\([^()\n]*\))+)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?\s*\)"
)
REFERENCE_DEFINITION = re.compile(r"(?m)^ {0,3}\[([^\]\n]+)\]:\s*(<[^>\n]+>|\S+)")


def markdown_prose(text):
    """Ignore examples inside fenced/inline code and HTML comments."""
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                if not marker[2].strip():
                    fence = None
            lines.append("\n")
        elif marker:
            fence = marker[1]
            lines.append("\n")
        else:
            lines.append(line)
    text = re.sub(r"<!--[\s\S]*?-->", "", "".join(lines))
    return re.sub(r"(`+)(.*?)\1", "", text, flags=re.DOTALL)


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def validate(root):
    errors = []
    counts = {"skills": 0, "frontmatters": 0, "agents": 0, "yaml_json": 0,
              "markdown_files": 0, "local_links": 0, "routing_cases": 0}

    def fail(path, message):
        errors.append(f"{path.relative_to(root)}: {message}")

    def read_text(path):
        try:
            return path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            fail(path, str(exc))
            return None

    skills = sorted(path for path in root.glob("dyz-med-*") if path.is_dir())
    counts["skills"] = len(skills)
    if len(skills) != EXPECTED_SKILL_COUNT:
        errors.append(f"Expected {EXPECTED_SKILL_COUNT} dyz-med-* skill directories, found {len(skills)}")

    structured = set(root.glob("tests/fixtures/**/*.json"))
    for directory in skills:
        structured.update(path for path in directory.rglob("*")
                          if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"})
    documents = {}
    for path in sorted(structured):
        text = read_text(path)
        if text is None:
            continue
        try:
            documents[path] = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
            counts["yaml_json"] += 1
        except (ValueError, yaml.YAMLError) as exc:
            fail(path, f"Invalid YAML/JSON: {exc}")

    for directory in skills:
        skill_path = directory / "SKILL.md"
        text = read_text(skill_path)
        if text is not None:
            lines = text.splitlines()
            if not lines or lines[0] != "---" or "---" not in lines[1:]:
                fail(skill_path, "Missing delimited YAML frontmatter")
            else:
                closing = lines.index("---", 1)
                try:
                    metadata = yaml.safe_load("\n".join(lines[1:closing]))
                    if not isinstance(metadata, dict):
                        fail(skill_path, "Frontmatter must be a mapping")
                    else:
                        counts["frontmatters"] += 1
                        if metadata.get("name") != directory.name:
                            fail(skill_path, "Frontmatter name must equal the skill directory name")
                        if not nonempty_string(metadata.get("description")):
                            fail(skill_path, "Description must be a nonempty string")
                        if metadata.get("disable-model-invocation") is True:
                            fail(skill_path, "Implicit invocation is disabled in frontmatter")
                except yaml.YAMLError as exc:
                    fail(skill_path, f"Invalid frontmatter YAML: {exc}")
                body_lines = len(lines[closing + 1:])
                if body_lines > 500:
                    fail(skill_path, f"Body has {body_lines} lines; maximum is 500")

        agent_path = directory / "agents" / "openai.yaml"
        agent = documents.get(agent_path)
        if not isinstance(agent, dict):
            fail(agent_path, "Agent config is missing or is not a YAML mapping")
            continue
        counts["agents"] += 1
        policy = agent.get("policy")
        if not isinstance(policy, dict) or policy.get("allow_implicit_invocation") is not True:
            fail(agent_path, "Top-level policy.allow_implicit_invocation must be true")
        interface = agent.get("interface")
        if not isinstance(interface, dict):
            fail(agent_path, "Interface must be a mapping")
            continue
        for field in ("display_name", "short_description", "default_prompt"):
            if not nonempty_string(interface.get(field)):
                fail(agent_path, f"interface.{field} must be a nonempty string")
        prompt = interface.get("default_prompt")
        if isinstance(prompt, str):
            identities = set(re.findall(r"\$(dyz-med-[a-z0-9-]+)", prompt))
            if identities != {directory.name}:
                fail(agent_path, "Default prompt must reference only its own $dyz-med-* identity")

    def check_target(path, raw):
        target = re.sub(r"\\([\\()\[\]<> ])", r"\1", raw.strip("<>"))
        try:
            parts = urlsplit(target)
        except ValueError as exc:
            fail(path, f"Invalid link target {raw!r}: {exc}")
            return
        if parts.scheme or parts.netloc or not parts.path:
            return
        # Resolve against the containing Markdown file, never the skill root.
        local_path = path.parent / unquote(parts.path)
        counts["local_links"] += 1
        if not local_path.exists():
            fail(path, f"Missing local Markdown link target: {raw}")

    for directory in skills:
        for path in sorted(directory.rglob("*.md")):
            text = read_text(path)
            if text is None:
                continue
            counts["markdown_files"] += 1
            if path.name == "SKILL.md" and text.startswith("---\n"):
                parts = text.split("\n---", 1)
                if len(parts) == 2:
                    text = parts[1]
            prose = markdown_prose(text)
            # Undefined [text][label] is literal Markdown, not a broken link.
            for match in REFERENCE_DEFINITION.finditer(prose):
                check_target(path, match[2])
            for match in INLINE_LINK.finditer(prose):
                check_target(path, match[1])

    fixture_path = root / "tests" / "fixtures" / "intent-routing.json"
    fixture = documents.get(fixture_path)
    if not isinstance(fixture, dict):
        fail(fixture_path, "Routing fixture is missing or is not a JSON object")
    else:
        if type(fixture.get("schema_version")) is not int or fixture["schema_version"] != 1:
            fail(fixture_path, "schema_version must be 1")
        if fixture.get("verification_status") != "not_run":
            fail(fixture_path, "Semantic scenarios must remain marked not_run until host execution")
        cases = fixture.get("cases")
        if not isinstance(cases, list) or len(cases) < 12:
            fail(fixture_path, "At least 12 routing cases are required")
        else:
            known_skills = {path.name for path in skills}
            seen = set()
            for index, case in enumerate(cases):
                if not isinstance(case, dict):
                    fail(fixture_path, f"Case {index} must be an object")
                    continue
                counts["routing_cases"] += 1
                case_id = case.get("id")
                if not nonempty_string(case_id) or case_id in seen:
                    fail(fixture_path, f"Case {index} must have a unique nonempty id")
                else:
                    seen.add(case_id)
                if not nonempty_string(case.get("input")):
                    fail(fixture_path, f"Case {index} input must be a nonempty string")
                for field in ("expected_skills", "excluded_skills", "required_behavior", "prohibited_behavior"):
                    values = case.get(field)
                    if not isinstance(values, list) or not all(nonempty_string(item) for item in values):
                        fail(fixture_path, f"Case {index} {field} must be a string array")
                    elif field.endswith("_skills"):
                        if any(item not in known_skills for item in values):
                            fail(fixture_path, f"Case {index} {field} contains unknown skill identities")
                    elif not values:
                        fail(fixture_path, f"Case {index} {field} must not be empty")
                expected = case.get("expected_skills")
                excluded = case.get("excluded_skills")
                if (isinstance(expected, list) and isinstance(excluded, list)
                        and any(item in excluded for item in expected)):
                    fail(fixture_path, f"Case {index} expected/excluded skills overlap")
    return errors, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    print("TOKEN_BUDGET: NOT_MEASURED (no tokenizer configured)")
    print("HOST_INTENT_EXECUTION: NOT_RUN (fixtures are semantic specifications only)")
    if yaml is None:
        print("BLOCKED: PyYAML is unavailable; YAML was not validated. No dependencies installed.", file=sys.stderr)
        return 2
    root = args.root.resolve()
    errors, counts = validate(root)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print("COUNTS: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    print(f"STRUCTURE: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
