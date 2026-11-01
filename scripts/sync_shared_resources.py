#!/usr/bin/env python3
"""Synchronize only declared shared resources while keeping every skill self-contained."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [
    ('dyz-med-translate/scripts/compare_protected.py', 'dyz-med-deai/scripts/compare_protected.py'),
    ('dyz-med-translate/references/protected-content-cli.md', 'dyz-med-deai/references/protected-content-cli.md'),
] + [('dyz-med-writing-plan/references/writing-craft.md', f'dyz-med-{name}/references/writing-craft.md')
     for name in ('introduction', 'discussion', 'abstract', 'deai', 'translate')]


def synchronize(root, apply=False):
    changed = []
    for source, target in PAIRS:
        a, b = root/source, root/target
        if not a.resolve().is_relative_to(root.resolve()) or not b.resolve().is_relative_to(root.resolve()):
            raise ValueError('Shared resource escapes repository')
        data = a.read_bytes()
        if not b.exists() or b.read_bytes() != data:
            changed.append(target)
            if apply:
                b.parent.mkdir(parents=True, exist_ok=True)
                b.write_bytes(data)
    return {'consistent': not changed or apply, 'changed': changed, 'applied': apply}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    report = synchronize(ROOT, args.apply)
    print(json.dumps(report))
    return 0 if report['consistent'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
