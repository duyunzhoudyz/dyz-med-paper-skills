"""静态规格覆盖与术语合法性，不模拟实际模型调用。"""

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FILES = ('intent-routing.json', 'intent-routing-supplement-v1.json')
SPEC = importlib.util.spec_from_file_location('routing_contract', ROOT / 'scripts/check_routing_contract.py')
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
CONTRACTS = json.loads(checker.CONTRACT.read_bytes())['contracts']


class RoutingCoverageTests(unittest.TestCase):
    def test_all_entrypoints_have_explicit_positive_scenarios(self):
        skills = {p.parent.name for p in ROOT.glob('dyz-med-*/SKILL.md')}
        covered = set()
        for filename in FILES:
            data = json.loads((ROOT / 'tests/fixtures' / filename).read_bytes())
            self.assertEqual(data['verification_status'], 'not_run')
            ids = set()
            for case in data['cases']:
                with self.subTest(file=filename, case=case['id']):
                    self.assertNotIn(case['id'], ids)
                    ids.add(case['id'])
                    self.assertTrue(case['input'].strip())
                    expected, excluded = set(case['expected_skills']), set(case['excluded_skills'])
                    self.assertFalse(expected & excluded)
                    self.assertLessEqual(expected | excluded, skills)
                    self.assertTrue(case['required_behavior'])
                    self.assertTrue(case['prohibited_behavior'])
                    covered.update(expected)
        self.assertEqual(covered, skills)


class RoutingDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = checker.load_catalog()

    def test_full_matrix_and_nonselection_scenarios(self):
        report = checker.inspect()
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['skill_count'], 32)
        self.assertEqual(report['scenario_count'], 38)
        self.assertEqual(set(report['nonselection_scenarios']),
                         {'ambiguous-manuscript-request', 'nonmedical-intent'})
        self.assertEqual(report['host_routing'], 'not_run')
        for row in report['skills']:
            self.assertTrue(row['positive_scenarios'], row)

    def test_scenario_contract_rejects_invalid_declarations(self):
        original = {name: json.loads((ROOT / 'tests/fixtures' / name).read_bytes()) for name in FILES}
        mutations = {
            'unknown_skill': lambda d: d[FILES[0]]['cases'][0]['expected_skills'].append('dyz-med-unknown'),
            'overlap': lambda d: d[FILES[0]]['cases'][0]['excluded_skills'].append('dyz-med-orchestrator'),
            'empty_behavior': lambda d: d[FILES[0]]['cases'][0].update(required_behavior=[]),
            'duplicate_or_missing_id': lambda d: d[FILES[1]]['cases'][0].update(id='progress-only'),
            'unexecuted_claim': lambda d: d[FILES[0]].update(verification_status='pass'),
            'input': lambda d: d[FILES[0]]['cases'][0].update(input=''),
            'positive_coverage': lambda d: d[FILES[1]]['cases'][0].update(expected_skills=[]),
            'schema': lambda d: d[FILES[0]].update(schema_version=True),
        }
        for expected, mutate in mutations.items():
            with self.subTest(branch=expected):
                changed = copy.deepcopy(original)
                mutate(changed)
                errors = checker.scenario_errors(changed, set(self.catalog))
                self.assertTrue(any(e.endswith(expected) for e in errors), errors)


def declaration_test(contract):
    def test(self):
        self.assertEqual(checker.declaration_errors(contract, self.catalog[contract['skill']]), [])
    return test


def mutation_test(contract):
    def test(self):
        baseline = self.catalog[contract['skill']]
        mutations = {
            'identity': lambda d: d['metadata'].update(name='dyz-med-unknown'),
            'trigger': lambda d: d['metadata'].update(description=checker.compact(d['metadata']['description']).replace(checker.compact(contract['trigger']), '')),
            'boundary': lambda d: d['metadata'].update(description=checker.compact(d['metadata']['description']).replace(checker.compact(contract['boundary']), '')),
            'frontmatter_disabled': lambda d: d['metadata'].update({'disable-model-invocation': True}),
            'implicit_disabled': lambda d: d['agent']['policy'].update(allow_implicit_invocation=False),
            'prompt_identity': lambda d: d['agent']['interface'].update(default_prompt='Use $dyz-med-unknown'),
        }
        self.assertEqual(checker.declaration_errors(contract, baseline), [])
        for expected, mutate in mutations.items():
            with self.subTest(skill=contract['skill'], branch=expected):
                changed = copy.deepcopy(baseline)
                mutate(changed)
                self.assertIn(expected, checker.declaration_errors(contract, changed))
        self.assertEqual(checker.declaration_errors(contract, baseline), [])
    return test


# 每个技能有独立测试ID，报告可逐项定位，不用单个循环冒充32项执行记录。
for contract in CONTRACTS:
    suffix = contract['skill'].replace('-', '_')
    setattr(RoutingDeclarationTests, 'test_declaration_' + suffix, declaration_test(contract))
    setattr(RoutingDeclarationTests, 'test_mutations_' + suffix, mutation_test(contract))


if __name__ == '__main__':
    unittest.main()
