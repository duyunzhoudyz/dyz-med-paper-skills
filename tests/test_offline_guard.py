"""护栏自检仅尝试不会执行的动作；所有异常都应发生在网络/进程启动之前。"""

import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('test_guard_impl', ROOT / 'scripts/offline_guard.py')
offline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(offline)


class OfflineGuardTests(unittest.TestCase):
    def test_network_is_blocked_before_dns_or_socket_creation(self):
        guard = offline.Guard()
        with guard.installed():
            with self.assertRaisesRegex(offline.OfflineViolation, 'OFFLINE_BLOCKED'):
                socket.getaddrinfo('offline-self-test.invalid', 443)
            with self.assertRaises(offline.OfflineViolation):
                socket.socket()
        self.assertEqual([e['event'] for e in guard.events], ['socket.getaddrinfo', 'socket.__new__'])

    def test_model_cli_shell_and_python_command_are_rejected(self):
        guard = offline.Guard()
        with guard.installed(), guard.local_tools():
            for command in (['claude', '--version'], ['codex', 'exec', 'synthetic'],
                            [sys.executable, '-c', 'raise SystemExit(0)'], 'echo blocked'):
                with self.subTest(command=command[0]):
                    with self.assertRaises(offline.OfflineViolation):
                        subprocess.run(command, capture_output=True)
        self.assertEqual(guard.allowed_processes, 0)
        self.assertEqual(len(guard.events), 4)

    def test_allowlisted_tool_runs_in_guarded_child(self):
        guard = offline.Guard()
        script = ROOT / 'dyz-med-passport/scripts/validate_passport.py'
        with guard.installed(), guard.local_tools():
            result = subprocess.run([sys.executable, '-B', str(script)],
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('usage:', result.stderr)
        self.assertEqual(guard.allowed_processes, 1)
        self.assertEqual(guard.events, [])

    def test_isolated_child_preserves_chinese_error_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / 'manifest.json'
            manifest.write_text('{}', encoding='utf-8')
            guard = offline.Guard()
            with guard.installed(), guard.local_tools():
                result = subprocess.run(
                    [sys.executable, '-B', str(ROOT / 'dyz-med-results/scripts/check_result_consistency.py'),
                     str(manifest), '--root', str(root), '--report', 'report.json',
                     '--record', 'check.json', '--check-id', 'synthetic-encoding'],
                    capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertTrue(any(ord(char) > 127 for char in result.stdout))
            self.assertEqual(guard.events, [])

    def test_unknown_script_is_rejected_even_with_known_basename(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'validate_passport.py'
            path.write_text('raise SystemExit(0)\n', encoding='utf-8')
            guard = offline.Guard()
            with guard.installed(), guard.local_tools():
                with self.assertRaisesRegex(offline.OfflineViolation, 'script_not_allowlisted'):
                    subprocess.run([sys.executable, '-B', str(path)], capture_output=True)
            self.assertEqual(guard.allowed_processes, 0)

    def test_child_guard_blocks_network_and_grandchild(self):
        # 只模拟已验证的子进程执行入口；仍受审计钩子约束，不创建任何进程。
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'probe.py'
            for source, event in (
                ('import socket\nsocket.getaddrinfo("offline-self-test.invalid", 443)', 'socket.getaddrinfo'),
                ('import subprocess\nsubprocess.run(["codex", "--version"])', 'subprocess.Popen'),
            ):
                with self.subTest(event=event):
                    path.write_text(source, encoding='utf-8')
                    digest = offline.hashlib.sha256(path.read_bytes()).hexdigest()
                    saved = sys.argv[:]
                    try:
                        with self.assertRaisesRegex(offline.OfflineViolation, event):
                            offline.child([digest, '', str(path)])
                    finally:
                        sys.argv = saved


if __name__ == '__main__':
    unittest.main()
