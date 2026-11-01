#!/usr/bin/env python3
"""运行三类合成材料的工具交接检查，保存输入、实际CLI回执和版本失效证据。

python -B scripts/run_workflow_cases.py --output tests/results/workflow-cases-<run>
输出目录必须是项目内新目录。只运行本地确定性工具，不拟合统计模型、不运行LLM、不联网。
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/workflow-cases-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(raw)


def artifact(root, identity, path):
    return {'id': identity, 'path': path, 'version': 'synthetic-v1', 'sha256': sha(root / path)}


def execute(root, args, evidence, expected):
    start = time.monotonic()
    completed = subprocess.run([sys.executable, '-B', *args], cwd=root,
                               capture_output=True, text=True, encoding='utf-8', timeout=30)
    record = {'argv': [sys.executable, '-B', *args], 'exit_code': completed.returncode,
              'stdout': completed.stdout, 'stderr': completed.stderr,
              'duration_seconds': round(time.monotonic() - start, 4)}
    write(root / evidence, record)
    if completed.returncode != expected:
        raise ValueError(f'{evidence}: expected exit {expected}, got {completed.returncode}; see evidence')
    return json.loads(completed.stdout)


def validate_receipt(root, name, expected=0, label='binding'):
    result = execute(root, ['tools/validate_passport.py', name, '--root', '.'],
                     f'evidence/{label}.json', expected)
    return result['freshness']


def stage_result_case(root, case):
    write(root / 'source.txt', case['source_text'])
    write(root / 'manuscript.txt', case['manuscript_text'])
    write(root / 'analysis-results.json', case['results'])
    write(root / 'reported-values.json', case['reported'])
    entries = [artifact(root, identity, path) for identity, path in (
        ('analysis-results', 'analysis-results.json'), ('reported-values', 'reported-values.json'),
        ('external-output', 'source.txt'), ('manuscript', 'manuscript.txt'),
        ('consistency-tool', 'tools/check_result_consistency.py'))]
    write(root / 'manifest.json', {'artifacts': entries})
    args = ['tools/check_result_consistency.py', 'manifest.json', '--root', '.',
            '--report', 'reports/normal.json', '--record', 'reports/normal-check.json',
            '--check-id', case['id'] + '-normal']
    good = execute(root, args, 'evidence/normal-command.json', 0)
    if good['conclusion'] != 'consistent':
        raise ValueError('Expected consistent normal report')
    current = validate_receipt(root, 'reports/normal-check.json')
    write(root / 'unrelated.txt', 'unrelated synthetic document\n')
    unchanged = validate_receipt(root, 'reports/normal-check.json', label='unrelated-change')
    fault = copy.deepcopy(case['reported'])
    fault['reported_values'][0]['values'][case['fault']['field']]['value'] = case['fault']['value']
    write(root / 'fault-values.json', fault)
    write(root / 'fault-manuscript.txt', case['fault']['manuscript_text'])
    fault_entries = copy.deepcopy(entries)
    for entry in fault_entries:
        if entry['id'] == 'reported-values':
            entry.update(path='fault-values.json', sha256=sha(root / 'fault-values.json'))
        if entry['id'] == 'manuscript':
            entry.update(path='fault-manuscript.txt', sha256=sha(root / 'fault-manuscript.txt'))
    write(root / 'fault-manifest.json', {'artifacts': fault_entries})
    fault_args = ['tools/check_result_consistency.py', 'fault-manifest.json', '--root', '.',
                  '--report', 'reports/fault.json', '--record', 'reports/fault-check.json',
                  '--check-id', case['id'] + '-fault']
    bad = execute(root, fault_args, 'evidence/fault-command.json', 1)
    if bad['conclusion'] != 'discrepant':
        raise ValueError('Expected detection of planted discrepancy')
    fault_current = validate_receipt(root, 'reports/fault-check.json', label='fault-binding')
    # 用新路径/版本表示源更新，保留所有原字节和旧检查绑定。
    write(root / 'source-v2.txt', case['source_text'] + 'Synthetic revision: requires recheck.\n')
    stale = json.loads((root / 'reports/normal-check.json').read_bytes())
    for entry in stale['artifacts']:
        if entry['id'] == 'external-output':
            entry.update(path='source-v2.txt', version='synthetic-v2', sha256=sha(root / 'source-v2.txt'))
    write(root / 'reports/stale-check.json', stale)
    stale_result = validate_receipt(root, 'reports/stale-check.json', 3, 'input-version-change')
    if (current, unchanged, fault_current, stale_result) != ('current', 'current', 'current', 'stale'):
        raise ValueError('Unexpected freshness transitions')
    return {'normal': good['conclusion'], 'planted_fault': bad['conclusion'],
            'normal_binding': current, 'fault_binding': fault_current,
            'unrelated_change': unchanged, 'input_version_change': stale_result}


def stage_review_case(root, case):
    write(root / 'screening.json', case['screening'])
    entries = [artifact(root, 'screening-data', 'screening.json'),
               artifact(root, 'prisma-tool', 'tools/compute_prisma_counts.py')]
    manifest = {'schema_version': '1.0', 'id': 'screening-inputs', 'version': 'v1',
                'dataset_artifact_id': 'screening-data', 'tool_artifact_id': 'prisma-tool', 'artifacts': entries}
    write(root / 'manifest.json', manifest)
    (root / 'reports').mkdir()
    args = ['tools/compute_prisma_counts.py', 'manifest.json', '--root', '.',
            '--output', 'reports/normal.json', '--check-output', 'reports/normal-check.json',
            '--run-id', case['id'] + '-normal']
    execute(root, args, 'evidence/normal-command.json', 0)
    counts = json.loads((root / 'reports/normal.json').read_bytes())
    for metric, expected in case['expected_counts'].items():
        if counts['counts'][metric]['count'] != expected:
            raise ValueError(f'Count mismatch: {metric}')
    current = validate_receipt(root, 'reports/normal-check.json')
    write(root / 'unrelated.txt', 'unrelated synthetic document\n')
    unchanged = validate_receipt(root, 'reports/normal-check.json', label='unrelated-change')
    pending = copy.deepcopy(case['screening'])
    pending['reports'][1]['decision'] = 'pending'
    write(root / 'pending-screening.json', pending)
    pending_manifest = copy.deepcopy(manifest)
    pending_manifest['version'] = 'v2'
    pending_manifest['artifacts'][0].update(path='pending-screening.json', version='v2', sha256=sha(root / 'pending-screening.json'))
    write(root / 'pending-manifest.json', pending_manifest)
    execute(root, ['tools/compute_prisma_counts.py', 'pending-manifest.json', '--root', '.',
                  '--output', 'reports/pending.json', '--check-output', 'reports/pending-check.json',
                  '--run-id', case['id'] + '-pending'], 'evidence/pending-command.json', 3)
    pending_report = json.loads((root / 'reports/pending.json').read_bytes())
    if pending_report['finalizable'] or pending_report['status'] != 'unverified':
        raise ValueError('Pending decision was incorrectly finalized')
    pending_binding = validate_receipt(root, 'reports/pending-check.json', label='pending-binding')
    stale = json.loads((root / 'reports/normal-check.json').read_bytes())
    for entry in stale['artifacts']:
        if entry['id'] == 'screening-data':
            entry.update(path='pending-screening.json', version='v2', sha256=sha(root / 'pending-screening.json'))
    write(root / 'reports/stale-check.json', stale)
    stale_result = validate_receipt(root, 'reports/stale-check.json', 3, 'input-version-change')
    if (current, unchanged, pending_binding, stale_result) != ('current', 'current', 'current', 'stale'):
        raise ValueError('Unexpected PRISMA freshness transitions')
    return {'normal': counts['status'], 'counts': {k: counts['counts'][k]['count'] for k in case['expected_counts']},
            'pending': pending_report['status'], 'pending_finalizable': pending_report['finalizable'],
            'pending_binding': pending_binding, 'unrelated_change': unchanged, 'input_version_change': stale_result}


def run(output):
    root = ROOT.resolve()
    output = (root / output).resolve()
    results_root = (root / 'tests/results').resolve()
    if not output.is_relative_to(results_root) or output == results_root or output.exists():
        raise ValueError('输出须为tests/results内尚不存在的新目录')
    fixture_bytes = FIXTURE.read_bytes()
    fixture = json.loads(fixture_bytes)
    tools = {'validate_passport.py': root / 'dyz-med-passport/scripts/validate_passport.py',
             'check_result_consistency.py': root / 'dyz-med-results/scripts/check_result_consistency.py',
             'compute_prisma_counts.py': root / 'dyz-med-screening-pipeline/scripts/compute_prisma_counts.py'}
    source_hashes = {p.relative_to(root).as_posix(): sha(p) for p in [FIXTURE, Path(__file__).resolve(), *tools.values()]}
    output.mkdir(parents=True)
    summary = {'kind': 'synthetic_tool_integration', 'model_executions': 0, 'statistical_model_executions': 0,
               'human_scientific_review': 'not_run', 'research_end_to_end_acceptance': 'not_run',
               'source_hashes': source_hashes, 'cases': []}
    for case in fixture['cases']:
        folder = output / case['id']
        (folder / 'tools').mkdir(parents=True)
        for name, source in tools.items():
            shutil.copyfile(source, folder / 'tools' / name)
        write(folder / 'model-prompt.txt', case['model_prompt'])
        # 评分判据仅在fixture中，未来被测会话只获得该目录的数据与prompt。
        before = {name: sha(folder / 'tools' / name) for name in tools}
        try:
            result = stage_review_case(folder, case) if 'screening' in case else stage_result_case(folder, case)
            if before != {name: sha(folder / 'tools' / name) for name in tools}:
                raise ValueError('工具副本被修改')
            summary['cases'].append({'id': case['id'], 'tool_integration': 'pass', **result,
                                     'not_covered': case['not_covered']})
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            summary['cases'].append({'id': case['id'], 'tool_integration': 'fail', 'reason': str(exc)})
        print(json.dumps(summary['cases'][-1], ensure_ascii=False), flush=True)
    summary['source_unchanged'] = source_hashes == {p: sha(root / p) for p in source_hashes}
    summary['all_tool_checks_pass'] = summary['source_unchanged'] and all(c['tool_integration'] == 'pass' for c in summary['cases'])
    write(output / 'summary.json', summary)
    return 0 if summary['all_tool_checks_pass'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        return run(Path(args.output))
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
