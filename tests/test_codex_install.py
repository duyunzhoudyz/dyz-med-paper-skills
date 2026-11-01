"""Public installer acceptance in temporary user/project directories only."""

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import install_codex as installer


class CodexInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.target = self.base / 'user/.agents/skills'

    def install(self, **kwargs):
        return installer.synchronize(ROOT, self.target, **kwargs)

    def test_fresh_install_and_check_with_legal_notices(self):
        result = self.install()
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['skill_count'], 32)
        self.assertFalse(result['runtime_loading_verified'])
        for directory in self.target.glob('dyz-med-*'):
            for filename in installer.LEGAL:
                self.assertEqual((directory / filename).read_bytes(), (ROOT / filename).read_bytes())
        self.assertEqual(self.install(check=True)['status'], 'pass')

    def test_check_and_dry_run_do_not_write(self):
        self.assertEqual(self.install(check=True)['status'], 'mismatch')
        self.assertFalse(self.target.exists())
        self.assertEqual(self.install(dry_run=True)['status'], 'planned')
        self.assertFalse(self.target.exists())

    def test_temp_path_alias_is_normalized_before_installation(self):
        target = Path(self.temp.name) / 'raw-path/skills'
        result = installer.synchronize(ROOT, target)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(Path(result['target']), target.resolve())
        self.assertEqual(installer.synchronize(ROOT, target, check=True)['status'], 'pass')

    def test_repeat_install_keeps_bytes_and_mtime(self):
        self.install()
        before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(self.install()['copied'], 0)
        self.assertEqual(before, {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in before})

    def test_conflict_refused_then_upgrade_preserves_backup(self):
        self.install()
        path = self.target / 'dyz-med-results/SKILL.md'
        original = path.read_bytes()
        path.write_bytes(b'local user edit\r\n')
        with self.assertRaisesRegex(ValueError, '--upgrade'):
            self.install()
        self.assertEqual(path.read_bytes(), b'local user edit\r\n')
        backup = self.base / 'backup'
        result = self.install(upgrade=True, backup=backup)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual((backup / 'dyz-med-results/SKILL.md').read_bytes(), b'local user edit\r\n')
        self.assertEqual(path.read_bytes(), original)
        self.assertIn('dyz-med-results/SKILL.md', json.loads((backup / 'manifest.json').read_bytes())['replaced'])

    def test_extra_files_and_other_skills_are_preserved(self):
        self.install()
        extra = self.target / 'dyz-med-results/personal.txt'
        extra.write_text('keep', encoding='utf-8')
        unrelated = self.target / 'other-skill'
        unrelated.mkdir()
        (unrelated / 'SKILL.md').write_text('keep too', encoding='utf-8')
        self.assertEqual(self.install(check=True)['extra'], ['dyz-med-results/personal.txt'])
        with self.assertRaises(ValueError):
            self.install(upgrade=True, backup=self.base / 'backup')
        self.assertEqual(extra.read_text(), 'keep')
        self.assertTrue((unrelated / 'SKILL.md').exists())

    def test_unsafe_target_and_backup_are_refused(self):
        with self.assertRaises(ValueError):
            installer.synchronize(ROOT, ROOT / 'dyz-med-results/installed')
        self.install()
        (self.target / 'dyz-med-results/SKILL.md').write_text('changed', encoding='utf-8')
        for backup in (self.target / 'backup', ROOT / 'backup', self.base):
            with self.subTest(path=str(backup)), self.assertRaises(ValueError):
                self.install(upgrade=True, backup=backup)
        with patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
            self.install()

    def test_missing_legal_and_invalid_source_identity_fail_before_write(self):
        root = self.base / 'source'
        root.mkdir()
        for index in range(32):
            folder = root / f'dyz-med-test-{index}'
            (folder / 'agents').mkdir(parents=True)
            (folder / 'SKILL.md').write_text(f'---\nname: {folder.name}\ndescription: synthetic\n---\n', encoding='utf-8')
            (folder / 'agents/openai.yaml').write_text(f'policy:\n  allow_implicit_invocation: true\ninterface:\n  default_prompt: "Use ${folder.name}"\n', encoding='utf-8')
        with self.assertRaises(FileNotFoundError):
            installer.synchronize(root, self.target)
        for filename in installer.LEGAL:
            shutil.copyfile(ROOT / filename, root / filename)
        (root / 'dyz-med-test-0/SKILL.md').write_text('bad identity', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.synchronize(root, self.target)
        self.assertFalse(self.target.exists())

    def test_project_cli_and_json_status(self):
        project = self.base / 'my paper'
        project.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            code = installer.main(['--project', str(project), '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'pass')
        self.assertTrue((project / '.agents/skills/dyz-med-orchestrator/SKILL.md').is_file())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['--project', str(project), '--check']), 0)
            self.assertEqual(installer.main(['--project', str(self.base / 'absent')]), 2)

    def test_installed_tool_runs_from_separate_paper_directory(self):
        self.install()
        script = self.target / 'dyz-med-passport/scripts/validate_passport.py'
        spec = importlib.util.spec_from_file_location('installed_passport_test', script)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        project = self.base / 'paper'
        project.mkdir()
        fixture = json.loads((ROOT / 'tests/fixtures/project-state.json').read_bytes())
        for name, content in fixture['files'].items():
            artifact = project / name
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(content, encoding='utf-8')

        def bind(value):
            if isinstance(value, dict):
                return {key: bind(item) for key, item in value.items()}
            if isinstance(value, list):
                return [bind(item) for item in value]
            if isinstance(value, str) and value.startswith('__SHA256__:'):
                return hashlib.sha256((project / value.split(':', 1)[1]).read_bytes()).hexdigest()
            return value

        document = bind(fixture['passport'])
        path = project / 'passport.json'
        path.write_text(json.dumps(document), encoding='utf-8')
        before = path.read_bytes()
        result = tool.validate(path, project)
        self.assertEqual(tool.exit_code(result), 0, result)
        self.assertEqual(path.read_bytes(), before)

    def test_legacy_installation_warns_without_deleting(self):
        legacy = self.target / 'med-results'
        legacy.mkdir(parents=True)
        (legacy / 'SKILL.md').write_text('old user copy', encoding='utf-8')
        self.assertEqual(self.install()['legacy_skills'], ['med-results'])
        self.assertEqual((legacy / 'SKILL.md').read_text(), 'old user copy')


if __name__ == '__main__':
    unittest.main()
