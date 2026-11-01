#!/usr/bin/env python3
"""Freeze a reproducible evaluation packet; never runs or grades a model."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

FIXTURES = ('intent-routing', 'statistical-consistency', 'evidence-registration', 'writing-boundaries')
FIRST = {
    'statistical-consistency': {'evalue-protective-rr', 'evalue-hr-conversion-unverified', 'mcid-ci-crosses-threshold', 'cox-p-only'},
    'evidence-registration': {'evidence-unverifiable-real-doi', 'registration-no-result', 'registration-unexplained-one-person'},
    'writing-boundaries': {'deai-fragment-missing-effect-timing', 'deai-disclosure-preserved', 'bias-direction-unknown'},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def prepare(root, output):
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root / 'tests/results') or output.exists():
        raise ValueError('Output must be a new directory within tests/results')
    paths = sorted(p for d in root.glob('dyz-med-*') if d.is_dir() for p in d.rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts)
    inputs = [root / f'tests/fixtures/{name}.json' for name in FIXTURES]
    inputs += [root / 'scripts/validate_skills.py', root / 'scripts/check_eval_results.py', root / 'tests/evaluation-protocol.md']
    for p in paths + inputs:
        if p.is_symlink() or not p.resolve().is_relative_to(root):
            raise ValueError('Evaluation sources must be ordinary workspace files')
    sources = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in paths}
    stamp = datetime.now(timezone.utc).isoformat()
    manifest = {'schema_version': 1, 'algorithm': 'sha256', 'captured_at': stamp,
                'skill_count': len({n.split('/')[0] for n in sources}), 'source_file_count': len(sources),
                'sources': sources, 'source_sha256': sha(canonical(sources).encode()),
                'inputs': {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in inputs}}
    cases, queue = [], []
    # Validate all fixture inputs before creating the packet.
    for name in FIXTURES:
        fixture = json.loads((root / f'tests/fixtures/{name}.json').read_text(encoding='utf-8-sig'))
        for case in fixture['cases']:
            identity = name + '/' + case['id']
            prompt = case['input'] if isinstance(case['input'], str) else canonical(case['input'])
            selected = name == 'intent-routing' or case['id'] in FIRST.get(name, set())
            queue.append({'case_id': identity, 'first_batch': selected, 'prompt': prompt})
            cases.append({'id': identity, 'attempted': False, 'submitted': False, 'executed': False,
                          'routing_status': 'not_run', 'behavior_status': 'not_run', 'raw_output': None,
                          'invocation_evidence': None, 'reviewer': None, 'reason': 'Prepared; no model execution or human review yet.'})
    output.mkdir(parents=True)
    for p in paths + inputs:
        target = output / 'frozen-source' / p.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    write(output / 'source-manifest.json', manifest)
    write(output / 'queue.json', {'kind': 'input_only_queue', 'cases': queue})
    for item in queue:
        target = output / 'prompts' / (item['case_id'].replace('/', '__') + '.txt')
        target.parent.mkdir(exist_ok=True)
        target.write_text(item['prompt'], encoding='utf-8')
    receipt = {'schema_version': 1, 'run_id': output.name, 'recorded_on': stamp[:10],
               'source_manifest': 'source-manifest.json', 'source_sha256': manifest['source_sha256'],
               'fixtures': [f'tests/fixtures/{name}.json' for name in FIXTURES],
               'host': {'name': 'unverified', 'version': None}, 'model': {'id': None},
               'environment': {'id': 'unverified', 'verified': False, 'actual_skill_set': None, 'evidence': None},
               'blockers': {}, 'cases': cases}
    write(output / 'results.json', receipt)
    return {'prepared': len(cases), 'first_batch': sum(c['first_batch'] for c in queue),
            'source_sha256': manifest['source_sha256'], 'output': str(output), 'executed': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.root, args.output), ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
