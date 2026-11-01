#!/usr/bin/env python3
"""离线路由声明合同检查；不实现自然语言分类器，不调用宿主或模型。"""

import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'tests/fixtures/routing-contract-v1.json'


def compact(text):
    return ''.join(text.split())


def load_catalog(root=ROOT):
    catalog = {}
    for path in sorted(root.glob('dyz-med-*/SKILL.md')):
        raw = path.read_text(encoding='utf-8-sig')
        lines = raw.splitlines()
        if lines[0] != '---':
            raise ValueError(f'{path}: missing frontmatter')
        end = lines.index('---', 1)
        catalog[path.parent.name] = {
            'metadata': yaml.safe_load('\n'.join(lines[1:end])),
            'agent': yaml.safe_load((path.parent / 'agents/openai.yaml').read_text(encoding='utf-8')),
            'body': '\n'.join(lines[end + 1:]),
        }
    return catalog


def declaration_errors(contract, declaration):
    errors = []
    metadata, agent = declaration['metadata'], declaration['agent']
    if metadata.get('name') != contract['skill']:
        errors.append('identity')
    description = compact(metadata.get('description', ''))
    for key in ('trigger', 'boundary'):
        if compact(contract[key]) not in description:
            errors.append(key)
    if metadata.get('disable-model-invocation') is True:
        errors.append('frontmatter_disabled')
    if agent.get('policy', {}).get('allow_implicit_invocation') is not True:
        errors.append('implicit_disabled')
    prompt = agent.get('interface', {}).get('default_prompt', '')
    if set(re.findall(r'\$(dyz-med-[a-z0-9-]+)', prompt)) != {contract['skill']}:
        errors.append('prompt_identity')
    return errors


def scenario_errors(documents, skills):
    errors, seen, covered = [], set(), set()
    for filename, document in documents.items():
        if type(document.get('schema_version')) is not int or document['schema_version'] != 1:
            errors.append(f'{filename}:schema')
        if document.get('verification_status') != 'not_run':
            errors.append(f'{filename}:unexecuted_claim')
        cases = document.get('cases')
        if not isinstance(cases, list) or not cases:
            errors.append(f'{filename}:cases')
            continue
        for case in cases:
            if not isinstance(case, dict):
                errors.append(f'{filename}:case_type')
                continue
            identity = case.get('id')
            if not isinstance(identity, str) or not identity.strip() or identity in seen:
                errors.append(f'{filename}:duplicate_or_missing_id')
            else:
                seen.add(identity)
            if not isinstance(case.get('input'), str) or not case['input'].strip():
                errors.append(f'{filename}:{identity}:input')
            valid = True
            for field in ('expected_skills', 'excluded_skills', 'required_behavior', 'prohibited_behavior'):
                values = case.get(field)
                if (not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values)
                        or len(values) != len(set(values))):
                    errors.append(f'{filename}:{identity}:{field}')
                    valid = False
                elif field.endswith('_skills'):
                    if not set(values) <= skills:
                        errors.append(f'{filename}:{identity}:unknown_skill')
                elif not values:
                    errors.append(f'{filename}:{identity}:empty_behavior')
            if valid:
                expected, excluded = set(case['expected_skills']), set(case['excluded_skills'])
                if expected & excluded:
                    errors.append(f'{filename}:{identity}:overlap')
                covered.update(expected)
    if covered != skills:
        errors.append('positive_coverage')
    return errors


def inspect(root=ROOT):
    spec = json.loads((root / 'tests/fixtures' / CONTRACT.name).read_bytes())
    catalog = load_catalog(root)
    documents = {name: json.loads((root / 'tests/fixtures' / name).read_bytes())
                 for name in spec['scenario_files']}
    errors = scenario_errors(documents, set(catalog))
    identities = [c['skill'] for c in spec['contracts']]
    if len(identities) != 32 or len(set(identities)) != 32 or set(identities) != set(catalog):
        errors.append('contract_catalog_coverage')
    cases = [case for doc in documents.values() for case in doc['cases']]
    rows = []
    for contract in spec['contracts']:
        skill = contract['skill']
        issues = declaration_errors(contract, catalog[skill]) if skill in catalog else ['missing_skill']
        errors.extend(f'{skill}:{issue}' for issue in issues)
        rows.append({'skill': skill, 'status': 'fail' if issues else 'pass',
                     'source': f'{skill}/SKILL.md', 'trigger_anchor': contract['trigger'],
                     'boundary_anchor': contract['boundary'], 'errors': issues,
                     'positive_scenarios': [c['id'] for c in cases if skill in c['expected_skills']],
                     'excluded_scenarios': [c['id'] for c in cases if skill in c['excluded_skills']]})
    return {'kind': spec['kind'], 'status': 'fail' if errors else 'pass', 'errors': errors,
            'skill_count': len(catalog), 'scenario_count': len(cases), 'skills': rows,
            'nonselection_scenarios': [c['id'] for c in cases if not c['expected_skills']],
            'host_routing': 'not_run', 'model_behavior': 'not_run'}


if __name__ == '__main__':
    import sys

    report = inspect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['status'] == 'pass' else 1)
