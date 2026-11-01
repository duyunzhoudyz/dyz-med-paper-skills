"""Synthetic executable invariants, never clinical acceptance or live model evaluation."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


audit = module('dyz-med-evidence-audit/scripts/audit_manuscript.py', 'manuscript_audit')
protect = module('dyz-med-translate/scripts/compare_protected.py', 'protection')
imports = module('dyz-med-cnki/scripts/import_references.py', 'reference_import')
search = module('dyz-med-cnki/scripts/search_pubmed.py', 'pubmed_search')
export = module('dyz-med-export/scripts/export_docx.py', 'docx_export')
prepare = module('scripts/prepare_evaluation.py', 'prepare_eval')


class Tools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode('utf-8'))
        return p

    def ref(self, name):
        return {'path': name, 'sha256': hashlib.sha256((self.root / name).read_bytes()).hexdigest()}

    def fixture(self):
        self.put('evidence.txt', 'Synthetic source. N=120, HR=0.8.')
        text = '纳入120人，HR为0.8。[claim:C001] [evidence:E001]'
        self.put('draft.md', text)
        registry = {'schema_version': '1.0', 'sources': [{'id': 'E001', **self.ref('evidence.txt')}],
                    'claims': [{'id': 'C001', 'text_sha256': audit.sha(audit.plain(text).encode()),
                                'evidence_ids': ['E001'], 'source_locators': {'E001': 'Synthetic line 1'},
                                'support_status': 'SUPPORTED', 'reason': 'Synthetic contract fixture only.'}]}
        self.put('registry.json', json.dumps(registry))
        manifest = {'schema_version': '1.0', 'manuscript': self.ref('draft.md'), 'registry': self.ref('registry.json')}
        return manifest, registry

    def test_actual_prose_edit_detected_even_after_manifest_rebinding(self):
        manifest, _ = self.fixture()
        self.put('draft.md', '纳入121人，HR为0.8。[claim:C001] [evidence:E001]')
        manifest['manuscript'] = self.ref('draft.md')
        report = audit.audit(self.root, manifest)
        self.assertIn('CLAIM_TEXT_CHANGED', {x['code'] for x in report['issues']})

    def test_moved_paragraph_gets_actual_new_location(self):
        manifest, _ = self.fixture()
        self.put('draft.md', '# Results\n\n' + (self.root / 'draft.md').read_text(encoding='utf-8'))
        manifest['manuscript'] = self.ref('draft.md')
        result = audit.audit(self.root, manifest)
        self.assertEqual(result['status'], 'consistent')
        self.assertEqual(result['observed_claims'][0]['line'], 3)
        self.assertEqual(result['scientific_acceptance'], 'not_assessed')

    def test_removed_or_unknown_claim_and_orphan_evidence(self):
        manifest, _ = self.fixture()
        self.put('draft.md', 'N=120 [claim:C002] [evidence:E001]\n\nText [evidence:E001]')
        manifest['manuscript'] = self.ref('draft.md')
        codes = {x['code'] for x in audit.audit(self.root, manifest)['issues']}
        self.assertTrue({'UNKNOWN_CLAIM', 'CLAIM_NOT_IN_MANUSCRIPT', 'EVIDENCE_WITHOUT_CLAIM'} <= codes)

    def test_missing_numeric_coverage_and_source_change(self):
        manifest, _ = self.fixture()
        self.put('evidence.txt', 'Changed source')
        self.put('draft.md', 'N=123')
        manifest['manuscript'] = self.ref('draft.md')
        codes = {x['code'] for x in audit.audit(self.root, manifest)['issues']}
        self.assertTrue({'INPUT_CHANGED', 'UNREGISTERED_NUMERIC_PARAGRAPH'} <= codes)

    def test_non_supported_claim_cannot_be_mechanical_clean_without_action(self):
        manifest, registry = self.fixture()
        registry['claims'][0]['support_status'] = 'PARTIAL'
        self.put('registry.json', json.dumps(registry))
        manifest['registry'] = self.ref('registry.json')
        codes = {x['code'] for x in audit.audit(self.root, manifest)['issues']}
        self.assertTrue({'CLAIM_REQUIRES_REVIEW', 'ACTION_MISSING'} <= codes)

    def test_path_escape_rejected(self):
        for value in ['../outside', '/root/file', 'C:/secret', 'a//b', 'a\\b']:
            with self.subTest(path=value), self.assertRaises(ValueError):
                audit.local(self.root, value)

    def test_numeric_and_citation_changes_detected(self):
        report = protect.compare('N=120, HR=0.80; P<0.05 [@R1]', 'N=121, HR=0.8; P>0.05 [@R2]')
        self.assertEqual(report['status'], 'discrepant')
        self.assertEqual({x['code'] for x in report['issues']}, {'NUMBER_COUNT_CHANGED', 'CITATION_COUNT_CHANGED'})

    def test_allowed_numeric_formats_and_semantic_limit(self):
        report = protect.compare('N=1,200; HR=0.80', 'N=1200; HR=8e-1')
        self.assertEqual(report['status'], 'consistent')
        self.assertEqual(report['semantic_review'], 'required')
        swapped = protect.compare('A=1; B=2', 'A=2; B=1')
        self.assertEqual(swapped['semantic_review'], 'required')

    def test_chinese_adjacent_numbers_signs_and_comparators(self):
        source = '纳入120人，每组60人。随访30天，评分变化为-4分；P<0.05。'
        target = 'Included 120 people, 60 per group. Follow-up 30 days; change -4 points; P < 0.05.'
        self.assertEqual(protect.compare(source, target)['status'], 'consistent')
        for changed in [target.replace('120 people', 'people'), target.replace('-4 points', '4 points'), target.replace('< 0.05', '> 0.05')]:
            with self.subTest(target=changed):
                self.assertEqual(protect.compare(source, changed)['status'], 'discrepant')
        self.assertEqual(protect.compare('P<.05; 值为−.5', 'P < 0.05; value -0.5')['status'], 'consistent')
        self.assertEqual(protect.compare('N=120\nHR=0.8', 'N=120 HR=0.8')['status'], 'consistent')

    def test_dose_unit_disclosure_phrase_not_satisfied_by_same_numbers(self):
        pairs = [{'id': 'dose', 'kind': 'dose', 'source': '5 mg daily', 'target': '每日5 mg'},
                 {'id': 'ai', 'kind': 'disclosure', 'source': 'AI edited', 'target': 'AI辅助编辑'}]
        report = protect.compare('5 mg daily. AI edited.', '每日5 g。', pairs)
        self.assertEqual(len([x for x in report['issues'] if x['code'] == 'PROTECTED_PHRASE_CHANGED']), 2)

    def test_protected_copy_standalone_consistency(self):
        self.assertEqual((ROOT / 'dyz-med-translate/scripts/compare_protected.py').read_bytes(),
                         (ROOT / 'dyz-med-deai/scripts/compare_protected.py').read_bytes())

    def test_ris_bib_nbib_and_xml_provenance(self):
        a = self.put('a.ris', 'TY  - JOUR\nTI  - Trial\nDO  - 10.1234/example\nPY  - 2025\nER  -\n')
        b = self.put('b.bib', '@article{x, title={Trial}, doi="https://doi.org/10.1234/example", year=2025, author={Smith, J and Lee, K}}')
        c = self.put('c.nbib', 'PMID- 12345\nTI  - Other\n      title\nDP  - 2024\nAU  - Lee K\n')
        d = self.put('d.xml', '<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345</PMID><Article><ArticleTitle>Other title</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>')
        result = imports.import_files([a,b,c,d])
        self.assertEqual(len(result['records']), 2)
        self.assertEqual([len(r['provenance']) for r in result['records']], [2,2])
        self.assertEqual(result['identity_verification'], 'not_run')

    def test_identifier_conflict_not_silently_merged(self):
        a = self.put('a.bib', '@article{x,title={One},doi={10.1234/x}}\n@article{y,title={Different},doi={10.1234/x}}')
        result = imports.import_files([a])
        self.assertEqual(len(result['records']), 2)
        self.assertIn('IDENTIFIER_CONFLICT', {w['code'] for w in result['warnings']})

    def test_bibtex_protection_braces_only_flag_possible_duplicates(self):
        a = self.put('a.ris', 'TY  - JOUR\nTI  - Follow-up of RNA\nPY  - 2024\nER  -\n')
        b = self.put('b.bib', '@article{x,title={Follow-up of {RNA}},year=2024}')
        result = imports.import_files([a, b])
        self.assertEqual(len(result['records']), 2)
        self.assertIn('POSSIBLE_DUPLICATE_REVIEW', {w['code'] for w in result['warnings']})
        self.assertEqual(result['records'][1]['title'], 'Follow-up of {RNA}')

    def test_nested_bibtex_and_macros(self):
        result = imports.bibtex('@article{x,title={Nested {RNA} title},year=2024}')
        self.assertEqual(result[0]['title'], ['Nested {RNA} title'])
        for s in ['@string{x="bad"}', '@article{x,title=macro}', '@article{x,title={a} # {b}}', '@article{x,title={unclosed}']:
            with self.subTest(text=s), self.assertRaises(ValueError):
                imports.bibtex(s)

    def test_incomplete_ris_rejected(self):
        with self.assertRaises(ValueError):
            imports.tagged('TY  - JOUR\nTI  - Missing terminator')

    def search_transport(self, total, fail_page=None):
        class Fake:
            attempts = []
            def get(self, name, endpoint, params):
                if name == 'search.json':
                    return json.dumps({'esearchresult': {'count': str(total), 'querykey': '1', 'webenv': 'synthetic'}}).encode()
                offset = params['retstart']
                if offset == fail_page:
                    raise ValueError('synthetic failed page')
                articles = ''.join(f'<PubmedArticle><MedlineCitation><PMID>{i+1}</PMID></MedlineCitation></PubmedArticle>' for i in range(offset, offset + params['retmax']))
                return ('<PubmedArticleSet>' + articles + '</PubmedArticleSet>').encode()
        return Fake()

    def test_search_pagination_and_saved_identity(self):
        result = search.search('public query', 205, self.root / 'run', self.search_transport(205), 'offline_replay')
        self.assertEqual(result['retrieved'], 205)
        self.assertEqual(len(result['response_files']), 4)
        self.assertTrue(result['retrieval_complete'])
        self.assertEqual(result['mode'], 'offline_replay')

    def test_search_limit_and_network_failure_stay_partial(self):
        for label, limit, fail in [('limit', 100, None), ('failed', 205, 100)]:
            result = search.search('query', limit, self.root / label, self.search_transport(205, fail), 'offline_replay')
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['retrieved'], 100)
            self.assertFalse(result['retrieval_complete'])

    def test_zero_hits_is_valid_but_no_fulltext_claim(self):
        result = search.search('query', 10, self.root / 'zero', self.search_transport(0), 'offline_replay')
        self.assertEqual(result['status'], 'complete')
        self.assertFalse(result['full_text_read'])

    def test_replay_is_bound_to_saved_query(self):
        replay = self.root/'raw'
        self.put('raw/context.json', json.dumps({'query_sha256': search.sha(b'original')}))
        with self.assertRaises(ValueError):
            search.search('changed', 1, self.root/'replay', search.Transport(replay), 'offline_replay')
        self.assertFalse((self.root/'replay').exists())

    def test_search_rejects_negative_counts_and_duplicate_pages(self):
        for label, count, duplicate in [('negative', -1, False), ('duplicate', 101, True)]:
            transport = self.search_transport(count)
            get = transport.get
            def bad(name, endpoint, params):
                if duplicate and name.startswith('page-'):
                    params = dict(params, retstart=0)
                return get(name, endpoint, params)
            transport.get = bad
            result = search.search('query', 101, self.root/label, transport, 'offline_replay')
            self.assertFalse(result['retrieval_complete'])
            self.assertTrue(result['errors'])

    def test_online_no_authorization_zero_requests(self):
        q = self.put('q.txt', 'public query')
        with patch('sys.argv', ['search_pubmed.py','--query-file',str(q),'--online','--output-dir',str(self.root/'online')]), patch.object(search.Transport,'get') as get:
            self.assertEqual(search.main(), 2)
            get.assert_not_called()

    def export_fixture(self):
        self.put('draft.md', '# Results\n\n纳入120人，HR=0.8；P <0.05。[@R1]\n\n|组别|人数|\n|---|---|\n|A|60|\n|B|60|\n\n![Figure 1](fig.png)\n')
        # Valid 1x1 PNG; standard-library fixture avoids optional imaging packages.
        import base64
        self.put('fig.png', base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4o8AAAAASUVORK5CYII='))
        config = {'schema_version':'1.0','title':'Synthetic clinical review', 'sections':[self.ref('draft.md')],
                  'figures':[self.ref('fig.png')], 'references':{'R1':'Synthetic test reference; not a real citation.'}}
        self.put('export.json', json.dumps(config))
        return config

    def test_docx_preserves_chinese_numbers_tables_images_and_references(self):
        self.export_fixture()
        before = self.ref('draft.md')
        report = export.build(self.root, self.root/'export.json', self.root/'out')
        with ZipFile(self.root/'out/manuscript-review.docx') as z:
            for name in ['word/document.xml','word/styles.xml','word/_rels/document.xml.rels','[Content_Types].xml']:
                ET.fromstring(z.read(name))
            tree = ET.fromstring(z.read('word/document.xml'))
            text = ''.join(tree.itertext())
            self.assertIn('纳入120人，HR=0.8；P <0.05。[1]', text)
            self.assertIn('Synthetic test reference', text)
            self.assertEqual(len(tree.findall('.//{' + export.W + '}tbl')), 1)
            self.assertIn('word/media/figure1.png', z.namelist())
        self.assertFalse(report['submission_ready'])
        self.assertEqual(report['visual_review'], 'not_run')
        self.assertEqual(before, self.ref('draft.md'))

    def test_export_does_not_overwrite_or_hide_placeholders(self):
        config = self.export_fixture()
        self.put('draft.md', 'TODO: verify outcome\n')
        config['sections'] = [self.ref('draft.md')]
        self.put('export.json', json.dumps(config))
        r = export.build(self.root, self.root/'export.json', self.root/'out')
        self.assertIn('UNRESOLVED_PLACEHOLDERS_PRESERVED', r['warnings'])
        with self.assertRaises(ValueError):
            export.build(self.root, self.root/'export.json', self.root/'out')

    def test_export_hides_internal_markers_only_in_copy(self):
        config = self.export_fixture()
        self.put('draft.md', 'N=120 [claim:C001] [evidence:E001]')
        config['sections'] = [self.ref('draft.md')]
        self.put('export.json', json.dumps(config))
        result = export.build(self.root, self.root/'export.json', self.root/'out')
        with ZipFile(self.root/'out/manuscript-review.docx') as z:
            text = ''.join(ET.fromstring(z.read('word/document.xml')).itertext())
        self.assertIn('N=120', text)
        self.assertNotIn('[claim:', text)
        self.assertIn('[claim:', (self.root/'draft.md').read_text())
        self.assertIn('INTERNAL_BINDING_MARKERS_OMITTED_FROM_REVIEW_COPY_NOT_VALIDATED_BY_EXPORTER', result['warnings'])

    def test_export_bad_hash_missing_reference_external_image_and_identity(self):
        config = self.export_fixture()
        variants = []
        bad = deepcopy(config); bad['sections'][0]['sha256'] = '0'*64; variants.append(bad)
        bad = deepcopy(config); bad['references'] = {}; variants.append(bad)
        bad = deepcopy(config); bad['figures'] = []; variants.append(bad)
        bad = deepcopy(config); bad['forbidden_identity_terms'] = ['纳入']; variants.append(bad)
        for index, variant in enumerate(variants):
            self.put('export.json', json.dumps(variant))
            with self.subTest(index=index), self.assertRaises(ValueError):
                export.build(self.root, self.root/'export.json', self.root/f'bad{index}')
            self.assertFalse((self.root/f'bad{index}').exists())

    def test_export_malformed_table_or_xml_never_creates_broken_docx(self):
        config = self.export_fixture()
        for i, value in enumerate(['|---|---|', 'N=120\x00']):
            self.put('draft.md', value)
            config['sections'] = [self.ref('draft.md')]
            self.put('export.json', json.dumps(config))
            with self.subTest(value=value), self.assertRaises(ValueError):
                export.build(self.root, self.root/'export.json', self.root/f'invalid{i}')
            self.assertFalse((self.root/f'invalid{i}').exists())

    def test_evaluation_packet_no_answer_leak_and_no_false_execution(self):
        self.put('dyz-med-example/SKILL.md', 'Synthetic skill')
        for name in prepare.FIXTURES:
            self.put(f'tests/fixtures/{name}.json', json.dumps({'cases':[{'id':'example','input':'Only this prompt', 'prohibited_behavior':['SECRET RUBRIC']}]}))
        for name in ['scripts/validate_skills.py','scripts/check_eval_results.py','tests/evaluation-protocol.md']:
            self.put(name, 'Synthetic checker/protocol')
        out = self.root/'tests/results/test-run'
        r = prepare.prepare(self.root, out)
        self.assertEqual(r['executed'], 0)
        self.assertNotIn('SECRET RUBRIC', (out/'queue.json').read_text(encoding='utf-8'))
        (self.root/'dyz-med-example/SKILL.md').write_text('Changed')
        self.assertEqual((out/'frozen-source/dyz-med-example/SKILL.md').read_text(), 'Synthetic skill')
        with self.assertRaises(ValueError):
            prepare.prepare(self.root, out)


if __name__ == '__main__':
    unittest.main()
