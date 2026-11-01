#!/usr/bin/env python3
"""32技能离线回归入口：声明、单元合同、跨工具交接、合成流程及只读安装核对。

python -B scripts/run_offline_regression.py [--output tests/results/<new-run>]
需要Python 3.10+及已有PyYAML，不安装依赖。0=全部通过，1=失败/缺覆盖/跳过，2=前置或路径错误。
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback
import unittest

from offline_guard import Guard


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def inventory():
    paths = set(ROOT.glob('scripts/*.py')) | set(ROOT.glob('tests/test_*.py'))
    paths.update(ROOT.glob('tests/fixtures/**/*'))
    paths.update(ROOT.glob('tests/*.md'))
    paths.update(ROOT / name for name in ('README.md', 'LICENSE', 'NOTICE', 'COMMERCIAL-LICENSE.md',
                                          'requirements-dev.txt', '.gitignore', '.gitattributes'))
    for folder in ROOT.glob('dyz-med-*'):
        if folder.is_dir():
            paths.update(folder.rglob('*'))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, value):
        for stream in self.streams:
            stream.write(value)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def record(self, test, status, **extra):
        self.events.append({'test_id': test.id(), 'status': status, **extra})

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'pass')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'fail', detail=self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error', detail=self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped', reason=reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, 'expected_failure')

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, 'unexpected_success')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.record(subtest, 'fail' if err else 'pass', parent=test.id(),
                    detail=self._exc_info_to_string(err, subtest) if err else None)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def run(output):
    root = ROOT.resolve()
    output = (root / output).resolve()
    results_root = (root / 'tests/results').resolve()
    if not output.is_relative_to(results_root) or output == results_root or output.exists():
        raise ValueError('输出必须是tests/results内尚不存在的新目录；历史结果不能覆盖')
    try:
        import yaml
    except ImportError as exc:
        raise ValueError('BLOCKED: 需要已有PyYAML，未执行测试；不会自动安装') from exc

    import install_codex as installer
    import check_routing_contract as routing
    import run_workflow_cases as workflows
    import sync_workspace_skills as sync
    import validate_skills as structure

    sources = inventory()
    # 冻结历史结果单独核对，不纳入新报告自己的哈希，避免自引用。
    histories = {p.relative_to(root).as_posix(): sha(p)
                 for base in (root / 'tests/results', root / 'audit-reports')
                 for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    output.mkdir(parents=True)
    write(output / 'source-manifest.json', {'algorithm': 'sha256', 'files': sources,
                                          'historical_files': histories})
    summary = {'schema_version': 1, 'kind': 'offline_skill_contract_regression',
               'started_at': datetime.now(timezone.utc).isoformat(),
               'python': sys.version, 'pyyaml': yaml.__version__,
               'host_routing': 'not_run', 'model_behavior': 'not_run',
               'scientific_acceptance': 'not_run', 'checks': {}, 'errors': []}
    started = time.monotonic()
    guard = Guard(output / 'guard-events.jsonl')
    events = []
    results = []
    try:
        with (output / 'unittest.log').open('x', encoding='utf-8') as log:
            runner = unittest.TextTestRunner(stream=Tee(sys.stdout, log), verbosity=2,
                                             resultclass=EvidenceResult)
            # 自检具有自己的阻断钩子；先执行，避免嵌套护栏抢先记录预期拒绝事件。
            self_tests = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_offline_guard.py')
            first = runner.run(self_tests)
            results.append(first)
            events.extend(first.events)
            if not first.wasSuccessful() or first.skipped:
                raise RuntimeError('离线护栏自检失败，停止业务回归')
            with guard.installed(), guard.local_tools(root):
                discovered = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_*.py')
                suite = unittest.TestSuite(t for t in flatten(discovered)
                                           if not t.id().startswith('test_offline_guard.'))
                actual = runner.run(suite)
                results.append(actual)
                events.extend(actual.events)
                summary['checks']['unit_contracts'] = actual.wasSuccessful() and not actual.skipped
                matrix = routing.inspect(root)
                passed_ids = {e['test_id'] for e in events if e['status'] == 'pass' and 'parent' not in e}
                for row in matrix['skills']:
                    suffix = row['skill'].replace('-', '_')
                    row['executed_tests'] = [f'test_routing_coverage.RoutingDeclarationTests.test_{kind}_{suffix}'
                                             for kind in ('declaration', 'mutations')]
                    row['tests_passed'] = all(name in passed_ids for name in row['executed_tests'])
                write(output / 'routing-coverage.json', matrix)
                summary['checks']['routing_contracts'] = matrix['status'] == 'pass' and all(r['tests_passed'] for r in matrix['skills'])
                branch_spec = json.loads((root / 'tests/fixtures/offline-coverage-v1.json').read_bytes())
                branches = [{'branch': name, 'tests': ids, 'status': 'pass' if ids and all(i in passed_ids for i in ids) else 'fail',
                             'missing_or_not_passed': [i for i in ids if i not in passed_ids]}
                            for name, ids in branch_spec['branches'].items()]
                write(output / 'failure-coverage.json', {'kind': branch_spec['kind'], 'branches': branches})
                summary['checks']['named_branches'] = bool(branches) and all(b['status'] == 'pass' for b in branches)
                errors, counts = structure.validate(root)
                write(output / 'structure.json', {'errors': errors, 'counts': counts})
                summary['checks']['structure'] = not errors
                with tempfile.TemporaryDirectory() as temp:
                    target = Path(temp) / 'skills'
                    installer.synchronize(root, target)
                    installation = installer.synchronize(root, target, check=True)
                    installation['target'] = '<temporary-isolated-skills>'
                    installation['mode'] = 'isolated_codex_install_and_check'
                if (root / '.breezell/skills').is_dir():
                    installation['workspace_copy'] = sync.synchronize(root)
                write(output / 'installation.json', installation)
                summary['checks']['installation_consistent'] = (
                    installation['status'] == 'pass'
                    and installation.get('workspace_copy', {}).get('consistent', True))
                summary['checks']['synthetic_workflows'] = workflows.run(output / 'workflows') == 0
                summary['coverage'] = {'skills': len(matrix['skills']), 'scenario_specs': matrix['scenario_count'],
                                       'named_failure_branches': len(branches)}
    except Exception:
        summary['errors'].append(traceback.format_exc())
    finally:
        write(output / 'test-events.json', events)
        summary['tests'] = {'run': sum(r.testsRun for r in results),
                            'failures': sum(len(r.failures) for r in results),
                            'errors': sum(len(r.errors) for r in results),
                            'skipped': sum(len(r.skipped) for r in results),
                            'subtests': sum('parent' in e for e in events)}
        guard_log = output / 'guard-events.jsonl'
        denials = [json.loads(line) for line in guard_log.read_text(encoding='utf-8').splitlines()] if guard_log.exists() else []
        summary['offline'] = {'guard_self_tests_passed': bool(results) and results[0].wasSuccessful() and not results[0].skipped,
                              'unexpected_blocked_operations': denials,
                              'allowlisted_python_processes': guard.allowed_processes,
                              'external_model_processes_allowed': 0,
                              'network_policy': 'Python socket operations blocked in parent and child',
                              'boundary': '防误联网/误启动护栏；不防御恶意本机代码或原生扩展绕过，不是OS沙箱'}
        summary['checks']['offline_guard'] = summary['offline']['guard_self_tests_passed'] and not denials
        summary['checks']['source_unchanged'] = sources == inventory()
        summary['checks']['history_unchanged'] = all((root / name).is_file() and sha(root / name) == digest
                                                    for name, digest in histories.items())
        summary['duration_seconds'] = round(time.monotonic() - started, 3)
        summary['status'] = 'pass' if not summary['errors'] and all(summary['checks'].values()) else 'fail'
        summary['evidence_files'] = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
        write(output / 'summary.json', summary)
    print(json.dumps({'status': summary['status'], 'tests': summary['tests'], 'checks': summary['checks'],
                      'report': output.relative_to(root).as_posix() + '/summary.json'}, ensure_ascii=True), flush=True)
    return 0 if summary['status'] == 'pass' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('tests/results') / ('offline-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
    args = parser.parse_args()
    try:
        return run(args.output)
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
