#!/usr/bin/env python3
"""回归进程的离线防误调用护栏，不是抵御恶意Python代码的系统沙箱。

阻止Python socket及系统进程启动；仅包装器可运行字节白名单内的本地Python工具。
子进程使用-I与相同审计护栏，从已核对的字节执行，且禁止进一步创建进程。
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = (
    'dyz-med-passport/scripts/validate_passport.py',
    'dyz-med-results/scripts/check_result_consistency.py',
    'dyz-med-screening-pipeline/scripts/compute_prisma_counts.py',
    'dyz-med-cnki/scripts/verify_references.py',
)


class OfflineViolation(RuntimeError):
    pass


class Guard:
    def __init__(self, event_file=None):
        self.active = False
        self.expected_popen = None
        self.expected_posix_spawn = None
        self.event_file = Path(event_file) if event_file else None
        self.events = []
        self.allowed_processes = 0

    def deny(self, event):
        record = {'event': event, 'action': 'blocked', 'pid': os.getpid()}
        self.events.append(record)
        if self.event_file:
            with self.event_file.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record) + '\n')
        raise OfflineViolation(f'OFFLINE_BLOCKED: {event}')

    def audit(self, event, args):
        if not self.active:
            return
        if event.startswith('socket.'):
            self.deny(event)
        if event == 'subprocess.Popen':
            executable, argv = args[:2]
            audited_argv = argv if isinstance(argv, str) else tuple(argv)
            if self.expected_popen == (executable, audited_argv):
                self.expected_popen = None
                # POSIX上的Popen可能继续触发一次底层spawn事件，仍须绑定同一命令。
                if os.name != 'nt':
                    self.expected_posix_spawn = (os.fsdecode(executable), audited_argv)
                return
            self.deny(event)
        if event == 'os.posix_spawn':
            expected = self.expected_posix_spawn
            self.expected_posix_spawn = None
            if expected == (os.fsdecode(args[0]), tuple(args[1])):
                return
            self.deny(event)
        if (event in {'os.system', 'os.fork', 'os.forkpty', 'os.startfile', 'os.startfile/2'}
                or event.startswith(('os.exec', 'os.spawn', 'os.posix_spawn'))):
            self.deny(event)

    @contextmanager
    def installed(self):
        sys.addaudithook(self.audit)
        self.active = True
        try:
            yield self
        finally:
            self.active = False

    @contextmanager
    def local_tools(self, root=ROOT):
        allowed = {hashlib.sha256((root / name).read_bytes()).hexdigest() for name in TOOLS}
        original = subprocess.Popen

        def guarded_popen(args, *positional, **kwargs):
            if (positional or not isinstance(args, (list, tuple)) or len(args) < 3
                    or kwargs.get('shell') or kwargs.get('executable') is not None
                    or Path(args[0]).resolve() != Path(sys.executable).resolve()
                    or args[1] != '-B'):
                self.deny('process_not_allowlisted')
            script = Path(args[2])
            if not script.is_absolute():
                script = Path(kwargs.get('cwd') or Path.cwd()) / script
            script = script.resolve()
            try:
                digest = hashlib.sha256(script.read_bytes()).hexdigest()
            except OSError:
                self.deny('script_unreadable')
            if digest not in allowed:
                self.deny('script_not_allowlisted')
            command = [sys.executable, '-I', '-X', 'utf8', '-B', str(Path(__file__).resolve()),
                       '--child', digest, str(self.event_file or ''), str(script),
                       *[os.fspath(arg) for arg in args[3:]]]
            # 只允许紧邻的一次Popen；子进程不会继承这个例外。
            # Windows的审计事件携带list2cmdline字符串，POSIX携带argv数组。
            audited_argv = subprocess.list2cmdline(command) if os.name == 'nt' else tuple(command)
            self.expected_popen = (sys.executable, audited_argv)
            try:
                process = original(command, executable=sys.executable, **kwargs)
                self.allowed_processes += 1
                return process
            finally:
                self.expected_popen = None
                self.expected_posix_spawn = None

        with patch.object(subprocess, 'Popen', guarded_popen):
            yield


def child(argv):
    digest, event_file, filename, *arguments = argv
    path = Path(filename).resolve()
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise OfflineViolation('OFFLINE_BLOCKED: child_script_changed')
    guard = Guard(event_file or None)
    sys.argv = [str(path), *arguments]
    with guard.installed():
        # 从已验证字节编译，避免核对后又从磁盘读取另一版本。
        exec(compile(raw, str(path), 'exec'), {'__name__': '__main__', '__file__': str(path)})


if __name__ == '__main__':
    if len(sys.argv) < 5 or sys.argv[1] != '--child':
        raise SystemExit('Internal offline child entry; use run_offline_regression.py')
    child(sys.argv[2:])
