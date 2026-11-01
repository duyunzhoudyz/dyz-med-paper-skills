"""真实工具回执进入passport的离线合同回归；所有输入为临时合成材料。"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('handoff_passport', ROOT / 'dyz-med-passport/scripts/validate_passport.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
TOOLS = {
    'results': 'dyz-med-results/scripts/check_result_consistency.py',
    'prisma': 'dyz-med-screening-pipeline/scripts/compute_prisma_counts.py',
    'references': 'dyz-med-cnki/scripts/verify_references.py',
}
# producer, variant, producer exit, execution, domain result, passport exit, freshness
CASES = (
    ('results', 'normal', 0, 'completed', 'consistent', 0, 'current'),
    ('results', 'difference', 1, 'completed', 'discrepant', 0, 'current'),
    ('results', 'unverified', 3, 'completed', 'unverified', 0, 'current'),
    ('prisma', 'normal', 0, 'completed', 'reconciled', 0, 'current'),
    ('prisma', 'difference', 1, 'completed', 'discrepancy', 0, 'current'),
    ('prisma', 'unverified', 3, 'completed', 'unverified', 0, 'current'),
    ('prisma', 'invalid', 1, 'failed', None, 3, 'unverified'),
    ('references', 'normal', 0, 'completed', 'matched', 0, 'current'),
    ('references', 'difference', 1, 'completed', 'mismatch', 0, 'current'),
    ('references', 'unverified', 3, 'completed', 'unverified', 0, 'current'),
    ('references', 'blocked', 3, 'blocked', None, 3, 'unverified'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    raw = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    path.write_text(raw, encoding='utf-8')


class ArtifactHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def stage(self, producer, variant='normal'):
        root = self.root
        script = root / 'producer.py'
        shutil.copyfile(ROOT / TOOLS[producer], script)
        entries = []

        def add(identity, filename, data):
            write(root / filename, data)
            entries.append({'id': identity, 'path': filename, 'version': 'v1', 'sha256': sha(root / filename)})

        if producer == 'results':
            data = json.loads((ROOT / 'tests/fixtures/result-consistency.json').read_bytes())
            if variant == 'difference':
                data['reported']['reported_values'][0]['values']['denominator.value']['value'] = 235
            elif variant == 'unverified':
                data['results']['results'][0]['execution_status'] = 'not_run'
            add('analysis-results', 'results.json', data['results'])
            add('reported-values', 'reported.json', data['reported'])
            add('external-output', 'source.txt', data['source_text'])
            add('manuscript', 'manuscript.txt', data['manuscript_text'])
            manifest = {'artifacts': entries}
        elif producer == 'prisma':
            data = json.loads((ROOT / 'tests/fixtures/prisma-records/cases.json').read_bytes())['base']
            if variant == 'difference':
                data['expected_counts'] = {'included.studies': 2}
            elif variant == 'unverified':
                data['reports'][1]['decision'] = 'pending'
            elif variant == 'invalid':
                data['reports'][0]['decision'] = 'unknown'
            add('screening-data', 'rows.json', data)
            entries.append({'id': 'prisma-tool', 'path': script.name, 'version': 'v1', 'sha256': sha(script)})
            manifest = {'schema_version': '1.0', 'id': 'count-inputs', 'version': 'v1',
                        'dataset_artifact_id': 'screening-data', 'tool_artifact_id': 'prisma-tool',
                        'artifacts': entries}
        else:
            data = json.loads((ROOT / 'tests/fixtures/reference-verification.json').read_bytes())
            if variant == 'difference':
                data['references']['references'][0]['title'] = 'Different synthetic title'
            elif variant == 'unverified':
                data['references']['references'][0].pop('title')
            add('references', 'references.json', data['references'])
            add('responses', 'responses.json', data['responses'])
            manifest = {'artifacts': entries, 'roles': {'references': 'references', 'responses': 'responses'}}
        write(root / 'manifest.json', manifest)
        args = [sys.executable, '-B', str(script), 'manifest.json', '--root', str(root)]
        if producer == 'prisma':
            args += ['--output', 'report.json', '--check-output', 'check.json', '--run-id', 'handoff']
        else:
            args += ['--report', 'report.json', '--record', 'check.json', '--check-id', 'handoff']
            if variant == 'blocked':
                args += ['--online']  # 无授权，预期在传输前blocked；离线入口额外阻断socket。
        before = {path.name: path.read_bytes() for path in root.iterdir()}
        process = subprocess.run(args, cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(before, {name: (root / name).read_bytes() for name in before})
        self.assertTrue((root / 'check.json').exists(), process.stdout + process.stderr)
        document = json.loads((root / 'check.json').read_bytes())
        report = json.loads((root / 'report.json').read_bytes())
        return process, document, report

    def validate(self, document, expected=0):
        path = self.root / 'consumer-passport.json'
        write(path, document)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = validator.validate(path, self.root)
        self.assertEqual(validator.exit_code(report), expected, report)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        return report

    def closure(self, document):
        document['open_items'] = [{
            'id': 'SYNTHETIC-ISSUE', 'severity': 'major', 'status': 'verified_closed',
            'verification_check_id': document['checks'][0]['id'],
            'evidence': copy.deepcopy(document['checks'][0]['report']),
        }]


def handoff_test(case):
    def test(self):
        producer, variant, code, execution, domain, consumer_code, freshness = case
        process, document, output = self.stage(producer, variant)
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        check = document['checks'][0]
        self.assertEqual(check['execution_status'], execution)
        self.assertEqual(check['domain_result']['value'] if check['domain_result'] else None, domain)
        self.assertEqual(check['report']['sha256'], sha(self.root / 'report.json'))
        validated = self.validate(document, consumer_code)
        self.assertEqual(validated['checks'][0]['freshness'], freshness)
        self.assertEqual(validated['checks'][0]['domain_result'], check['domain_result'])
        if producer == 'references':
            self.assertEqual(output['network_requests'], 0)
        if producer == 'prisma' and variant != 'normal':
            self.assertFalse(output['finalizable'])
        # 合同验证不解释领域结论：差异/未核实的completed回执也可能current。
        self.closure(document)
        closed = self.validate(document, 0 if execution == 'completed' else 1)
        if execution != 'completed':
            self.assertIn('UNVERIFIED_CLOSURE', {e['code'] for e in closed['errors']})
    return test


def lifecycle_test(producer):
    def test(self):
        process, base, _ = self.stage(producer)
        self.assertEqual(process.returncode, 0)
        self.validate(base)
        write(self.root / 'unrelated.txt', 'synthetic unrelated change')
        self.assertEqual(self.validate(base)['checks'][0]['freshness'], 'current')

        changed = copy.deepcopy(base)
        changed['artifacts'][0]['version'] = 'v2'
        self.assertEqual(self.validate(changed, 3)['checks'][0]['freshness'], 'stale')
        self.closure(changed)
        self.assertIn('UNVERIFIED_CLOSURE', {e['code'] for e in self.validate(changed, 1)['errors']})

        for mutation in ('missing_report', 'report_tamper', 'input_tamper', 'duplicate_input',
                         'path_escape', 'unexecuted_result', 'missing_evidence', 'not_applicable'):
            with self.subTest(producer=producer, branch=mutation):
                document = copy.deepcopy(base)
                restore = None
                if mutation in ('missing_report', 'report_tamper', 'input_tamper'):
                    name = 'report.json' if mutation != 'input_tamper' else document['artifacts'][0]['path']
                    path = self.root / name
                    restore = (path, path.read_bytes())
                    if mutation == 'missing_report':
                        path.unlink()
                    else:
                        path.write_bytes(restore[1] + b'\nchanged')
                elif mutation == 'duplicate_input':
                    document['checks'][0]['inputs'].append(copy.deepcopy(document['checks'][0]['inputs'][0]))
                elif mutation == 'path_escape':
                    document['artifacts'][0]['path'] = '../outside.json'
                elif mutation == 'unexecuted_result':
                    document['checks'][0]['execution_status'] = 'not_run'
                else:
                    self.closure(document)
                    if mutation == 'missing_evidence':
                        document['open_items'][0].pop('evidence')
                    else:
                        document['checks'][0].update(applicability='not_applicable', applicability_reason='Synthetic scope')
                try:
                    report = self.validate(document, 1)
                    expected = {
                        'missing_report': 'FILE_UNREADABLE', 'report_tamper': 'HASH_MISMATCH',
                        'input_tamper': 'HASH_MISMATCH', 'duplicate_input': 'DUPLICATE_INPUT',
                        'path_escape': 'INVALID_PATH', 'unexecuted_result': 'UNEXECUTED_RESULT',
                        'not_applicable': 'UNVERIFIED_CLOSURE',
                    }.get(mutation)
                    if expected:
                        self.assertIn(expected, {e['code'] for e in report['errors']})
                finally:
                    if restore:
                        restore[0].write_bytes(restore[1])
        self.validate(base)
    return test


for case in CASES:
    setattr(ArtifactHandoffTests, f'test_handoff_{case[0]}_{case[1]}', handoff_test(case))
for producer in TOOLS:
    setattr(ArtifactHandoffTests, f'test_lifecycle_{producer}', lifecycle_test(producer))


if __name__ == '__main__':
    unittest.main()
