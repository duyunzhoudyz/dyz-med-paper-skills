#!/usr/bin/env python3
"""Install/check 32 local Codex skills without network, model calls or dependencies.

python scripts/install_codex.py [--project PATH | --target PATH] [--check | --dry-run]
Upgrades require --upgrade --backup NEW_PATH. Existing extras are never deleted.
Exit: 0=installed/consistent/dry-run, 1=check mismatch, 2=input/dependency/path error.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

from sync_workspace_skills import collect, digest


ROOT = Path(__file__).resolve().parents[1]
LEGAL = ('LICENSE', 'NOTICE', 'COMMERCIAL-LICENSE.md')


def plain_path(path):
    """Refuse symlinks/junctions before resolving a source or destination."""
    path = Path(os.path.abspath(path.expanduser()))
    for part in (path, *path.parents):
        try:
            attributes = getattr(part.lstat(), 'st_file_attributes', 0)
        except FileNotFoundError:
            attributes = 0
        if part.is_symlink() or attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
            raise ValueError(f'拒绝符号链接或重定向路径: {part}')
    # Windows 8.3短路径是同一目录的别名，不是junction；检查后再规范化。
    return path.resolve()


def source_files(root):
    root = plain_path(root)
    directories = sorted(p for p in root.glob('dyz-med-*') if p.is_dir())
    if len(directories) != 32:
        raise ValueError(f'需要完整32个技能目录，实际为{len(directories)}')
    files = collect(root, directories)
    for directory in directories:
        name = directory.name
        raw = files.get(f'{name}/SKILL.md', b'').decode('utf-8-sig')
        header = raw.split('---', 2)
        if (len(header) != 3 or header[0].strip()
                or not re.search(r'^name:\s*' + re.escape(name) + r'\s*$', header[1], re.M)
                or not re.search(r'^description:\s*\S', header[1], re.M)):
            raise ValueError(f'技能身份或frontmatter缺失: {name}')
        agent = files.get(f'{name}/agents/openai.yaml', b'').decode('utf-8-sig')
        if (not re.search(r'^policy:\s*\n\s+allow_implicit_invocation:\s*true\s*$', agent, re.M)
                or set(re.findall(r'\$(dyz-med-[a-z0-9-]+)', agent)) != {name}):
            raise ValueError(f'技能调用配置不匹配: {name}')
    for filename in LEGAL:
        path = plain_path(root / filename)
        content = path.read_bytes()
        if not content:
            raise ValueError(f'许可文件为空: {filename}')
        for directory in directories:
            key = f'{directory.name}/{filename}'
            if key in files and files[key] != content:
                raise ValueError(f'技能内许可文件与根目录冲突: {key}')
            files[key] = content
    return root, directories, files


def environment():
    return {'python': sys.version.split()[0], 'codex_on_path': bool(shutil.which('codex')),
            'rscript_on_path': bool(shutil.which('Rscript')),
            'pyyaml_available': importlib.util.find_spec('yaml') is not None,
            'note': '仅探测存在性；不运行程序，不核对登录、包版本或宿主实际加载。'}


def synchronize(root=ROOT, target=None, check=False, dry_run=False, upgrade=False, backup=None):
    root, directories, sources = source_files(Path(root))
    target = plain_path(Path(target) if target is not None else Path.home() / '.agents/skills')
    if target.exists() and not target.is_dir():
        raise ValueError('安装目标必须是目录')
    if any(target.is_relative_to(d) or d.is_relative_to(target) for d in directories):
        raise ValueError('安装目标不能与技能源目录重叠')
    installed = collect(target, [target / d.name for d in directories])
    missing = sorted(sources.keys() - installed.keys())
    changed = sorted(p for p in sources.keys() & installed.keys() if sources[p] != installed[p])
    extra = sorted(installed.keys() - sources.keys())
    hashes = {p: digest(raw) for p, raw in sorted(sources.items())}
    report = {'status': 'pass' if not (missing or changed or extra) else 'mismatch',
              'skill_count': len(directories), 'file_count': len(sources), 'target': str(target),
              'missing': missing, 'changed': changed, 'extra': extra, 'copied': 0,
              'source_sha256': digest(json.dumps(hashes, sort_keys=True).encode()),
              'runtime_loading_verified': False, 'environment': environment(),
              'legacy_skills': sorted(p.name for p in target.glob('med-*') if p.is_dir())}
    if check or not (missing or changed or extra):
        return report
    if extra:
        raise ValueError('安装目录内存在额外文件，已保留；请先人工核对: ' + ', '.join(extra))
    if changed and not (upgrade and backup):
        raise ValueError('同名技能内容不同；升级需 --upgrade --backup <尚不存在的目录>，不会静默覆盖')
    backup_path = None
    if backup:
        backup_path = plain_path(Path(backup))
        if (backup_path.exists() or backup_path.is_relative_to(target) or target.is_relative_to(backup_path)
                or backup_path.is_relative_to(root) or root.is_relative_to(backup_path)):
            raise ValueError('备份须为尚不存在、位于源码与安装目录之外的新目录')
    if dry_run:
        report['status'] = 'planned'
        return report
    if changed:
        backup_path.mkdir(parents=True)
        for name in changed:
            path = backup_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(installed[name])
        (backup_path / 'manifest.json').write_text(json.dumps({
            'target': str(target), 'replaced': {p: digest(installed[p]) for p in changed},
            'created': missing, 'new_sources': hashes,
            'recovery': '按replaced恢复旧文件；created是新增文件，回滚前人工核对。'},
            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report['backup'] = str(backup_path)
    if source_files(root)[2] != sources or collect(target, [target / d.name for d in directories]) != installed:
        raise ValueError('源或安装文件在预检后改变；未开始写入')
    target.mkdir(parents=True, exist_ok=True)
    # 每个替换先写同目录临时文件，再原子替换；新文件用xb避免静默覆盖并发创建。
    for name in changed + missing:
        dest = target / name
        plain_path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if name in installed:
            if dest.read_bytes() != installed[name]:
                raise ValueError(f'安装文件在写入前改变，已保留备份: {name}')
            staged = None
            try:
                with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as stream:
                    staged = Path(stream.name)
                    stream.write(sources[name])
                os.replace(staged, dest)
            finally:
                if staged and staged.exists():
                    staged.unlink()
        else:
            with dest.open('xb') as stream:
                stream.write(sources[name])
    if collect(target, [target / d.name for d in directories]) != sources or source_files(root)[2] != sources:
        raise ValueError('写后字节核对失败；不能标记安装成功')
    report.update(status='pass', copied=len(changed) + len(missing), missing=[], changed=[])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument('--project', type=Path, help='已有论文项目；安装到其.agents/skills')
    destination.add_argument('--target', type=Path, help='明确指定技能目录，用于高级用户/隔离自检')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='只读核对，不安装')
    mode.add_argument('--dry-run', action='store_true', help='只显示可执行安装计划')
    parser.add_argument('--upgrade', action='store_true')
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--json', action='store_true', help='输出JSON')
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 10):
            raise ValueError('需要Python 3.10或以上')
        if args.backup and not args.upgrade:
            raise ValueError('--backup须与--upgrade一起使用')
        target = args.target
        if args.project:
            project = plain_path(args.project)
            if not project.is_dir():
                raise ValueError('--project须指定已存在的论文项目目录')
            target = project / '.agents/skills'
        report = synchronize(target=target, check=args.check, dry_run=args.dry_run,
                             upgrade=args.upgrade, backup=args.backup)
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False))
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status'].upper()}: {report['skill_count']} skills, {report['file_count']} files")
        print('安装目录: ' + report['target'])
        print(f"本次复制 {report['copied']}，缺失 {len(report['missing'])}，差异 {len(report['changed'])}，额外 {len(report['extra'])}")
        print('环境探测: ' + json.dumps(report['environment'], ensure_ascii=False))
        if report['legacy_skills']:
            print('发现旧版med-*，可能重复；未修改: ' + ', '.join(report['legacy_skills']))
        if report['status'] == 'pass':
            print('文件核对通过；在论文项目中打开Codex，用 /skills 或 $ 查看 dyz-med-orchestrator。')
            print('宿主实际加载与模型选择仍需在Codex验证；这里未运行模型。')
        elif report['status'] == 'mismatch':
            print('运行安装命令修复缺失；有修改时先核对，再使用 --upgrade --backup。可加 --json 查看具体文件。')
    return 1 if report['status'] == 'mismatch' else 0


if __name__ == '__main__':
    sys.exit(main())
