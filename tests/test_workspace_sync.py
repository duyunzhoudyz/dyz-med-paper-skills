"""安装同步只使用临时目录，覆盖前保留旧版本。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('workspace_sync', ROOT / 'scripts/sync_workspace_skills.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class WorkspaceSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        source = self.root / 'dyz-med-demo'
        source.mkdir()
        (source / 'SKILL.md').write_bytes(b'new source\r\n')
        (source / 'script.py').write_bytes(b'print(1)\n')
        self.target = self.root / '.breezell/skills/dyz-med-demo'
        self.target.mkdir(parents=True)
        (self.target / 'SKILL.md').write_bytes(b'old installed\n')

    def test_check_is_read_only(self):
        report = sync.synchronize(self.root)
        self.assertEqual(report['changed'], ['dyz-med-demo/SKILL.md'])
        self.assertEqual(report['missing'], ['dyz-med-demo/script.py'])
        self.assertFalse(report['consistent'])
        self.assertEqual((self.target / 'SKILL.md').read_bytes(), b'old installed\n')
        self.assertFalse((self.target / 'script.py').exists())

    def test_apply_preserves_backup_and_bytes_and_is_idempotent(self):
        report = sync.synchronize(self.root, True, 'audit/backup')
        self.assertTrue(report['consistent'])
        self.assertFalse(report['runtime_loading_verified'])
        self.assertEqual((self.root / 'audit/backup/dyz-med-demo/SKILL.md').read_bytes(), b'old installed\n')
        self.assertEqual((self.target / 'SKILL.md').read_bytes(), b'new source\r\n')
        manifest = json.loads((self.root / 'audit/backup/manifest.json').read_bytes())
        self.assertEqual(manifest['created'], ['dyz-med-demo/script.py'])
        second = sync.synchronize(self.root, True, 'audit/another')
        self.assertFalse(second['applied'])
        self.assertFalse((self.root / 'audit/another').exists())

    def test_extra_is_preserved_and_blocks_apply(self):
        extra = self.target / 'user-file.txt'
        extra.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            sync.synchronize(self.root, True, 'audit/backup')
        self.assertEqual(extra.read_bytes(), b'keep')
        self.assertEqual((self.target / 'SKILL.md').read_bytes(), b'old installed\n')

    def test_backup_cannot_escape_or_overwrite(self):
        for backup in ('../outside', 'dyz-med-demo/backup', '.breezell/skills/backup', 'dyz-med-demo'):
            with self.subTest(backup=backup), self.assertRaises(ValueError):
                sync.synchronize(self.root, True, backup)
        self.assertEqual((self.target / 'SKILL.md').read_bytes(), b'old installed\n')

    def test_apply_requires_backup(self):
        with self.assertRaises(ValueError):
            sync.synchronize(self.root, True)


if __name__ == '__main__':
    unittest.main()
