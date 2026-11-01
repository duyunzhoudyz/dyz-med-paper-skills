#!/usr/bin/env python3
"""核对/同步本仓库的工作区技能副本；默认只读，不处理全局技能。

python -B scripts/sync_workspace_skills.py
python -B scripts/sync_workspace_skills.py --apply --backup audit-reports/<run>/installation-backup
退出码：0=一致，1=操作/路径错误，3=只读核对发现差异。
覆盖前备份旧字节及清单，不删除安装侧额外文件，不声称宿主已重新索引。
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(p in {'.', '..'} for p in path.parts):
        raise ValueError('需要根目录内相对路径')
    target = root / path
    for part in [target, *target.parents]:
        if part == root:
            break
        if part.is_symlink() or part.resolve() != part.absolute():
            raise ValueError(f'拒绝链接/重定向路径: {relative}')
    if not target.resolve().is_relative_to(root):
        raise ValueError(f'路径越界: {relative}')
    return target


def collect(root, directories):
    result = {}
    for directory in directories:
        if not directory.exists():
            continue
        safe_path(root, directory.relative_to(root))
        for path in sorted(directory.rglob('*')):
            if '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            safe_path(root, path.relative_to(root))
            if path.is_file():
                result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def synchronize(root, apply=False, backup=None):
    root = root.resolve()
    directories = sorted(p for p in root.glob('dyz-med-*') if p.is_dir())
    if not directories or any(not (p / 'SKILL.md').is_file() for p in directories):
        raise ValueError('源码技能目录为空或缺少SKILL.md')
    source = collect(root, directories)
    target = safe_path(root, '.breezell/skills')
    installed = collect(target, [target / p.name for p in directories])
    changed = sorted(p for p in source.keys() & installed.keys() if source[p] != installed[p])
    missing = sorted(source.keys() - installed.keys())
    extra = sorted(installed.keys() - source.keys())
    hashes = {p: digest(raw) for p, raw in sorted(source.items())}
    report = {'skill_count': len(directories), 'source_file_count': len(source),
              'source_sha256': digest(json.dumps(hashes, sort_keys=True, ensure_ascii=True,
                                                separators=(',', ':')).encode()),
              'changed': changed, 'missing': missing, 'extra': extra,
              'applied': False, 'runtime_loading_verified': False}
    if not apply or not (changed or missing or extra):
        report['consistent'] = not (changed or missing or extra)
        return report
    if extra:
        raise ValueError('安装目录有源码中不存在的文件；保留原件，需先人工处理差异')
    if not backup:
        raise ValueError('--apply需要新的--backup目录以保存被覆盖字节')
    backup_path = safe_path(root, backup)
    if (backup_path.exists() or backup_path.is_relative_to(target)
            or any(backup_path.is_relative_to(d) for d in directories)):
        raise ValueError('备份必须是尚不存在、位于源码与安装目录之外的项目内目录')
    # 全部旧内容备份完成且源/目标仍匹配快照后，才开始覆盖。
    backup_path.mkdir(parents=True)
    for name in changed:
        dest = backup_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(installed[name])
    manifest = {'source_sha256': report['source_sha256'], 'sources': hashes,
                'replaced': {p: digest(installed[p]) for p in changed}, 'created': missing,
                'destination': '.breezell/skills',
                'recovery': '备份文件对应被覆盖的旧文件；created为此次新增，回滚前人工核对当前改动。'}
    (backup_path / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if collect(root, directories) != source or collect(target, [target / p.name for p in directories]) != installed:
        raise ValueError('同步预检后源或目标发生变化；已保留备份，未开始覆盖')
    for name in changed + missing:
        dest = safe_path(target, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source[name])
    actual = collect(target, [target / p.name for p in directories])
    if actual != source or collect(root, directories) != source:
        raise ValueError('写入后源或目标与快照不同；保留备份并报告，不能标记同步成功')
    report.update(applied=True, consistent=True, backup=backup_path.relative_to(root).as_posix(),
                  copied=len(changed) + len(missing))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    args = parser.parse_args()
    try:
        report = synchronize(args.root, args.apply, args.backup)
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'consistent': False}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['consistent'] else 3


if __name__ == '__main__':
    sys.exit(main())
