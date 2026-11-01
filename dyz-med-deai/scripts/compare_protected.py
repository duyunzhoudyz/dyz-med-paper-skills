#!/usr/bin/env python3
"""Compare numeric/citation occurrences and explicit bilingual protected phrases. Offline."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import unicodedata

# CJK prose, N120 and P<0.05 may have no intervening space. Do not use
# Unicode \w as a boundary: it drops the whole number or its minus sign.
NUMBER = re.compile(r'(?<![\d.])(?:[<>≤≥]=?\s*)?[+−-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?\s*(?:%|％)?')
CITATION = re.compile(r'\[@[^\]\n]+\]|\[(?:\d+(?:\s*[,;–-]\s*\d+)*)\]')


def normal_number(value):
    value = re.sub(r'\s+', '', unicodedata.normalize('NFKC', value).replace('−', '-').replace(',', ''))
    match = re.fullmatch(r'([<>≤≥]=?)?([+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(%)?', value)
    if not match:
        return value
    return (match[1] or '').replace('≤', '<=').replace('≥', '>=') + str(Decimal(match[2]).normalize()) + (match[3] or '')


def compare(source, target, phrases=None):
    issues = []
    for code, extract in [('NUMBER', lambda s: Counter(normal_number(x.group()) for x in NUMBER.finditer(CITATION.sub('', s)))),
                          ('CITATION', lambda s: Counter(re.sub(r'\s', '', x) for x in CITATION.findall(s)))]:
        before, after = extract(source), extract(target)
        for token in sorted(before.keys() | after.keys()):
            if before[token] != after[token]:
                issues.append({'code': code + '_COUNT_CHANGED', 'token': token,
                               'source_count': before[token], 'target_count': after[token]})
    for row in phrases or []:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in ('id', 'source', 'target', 'kind')):
            raise ValueError('Protected phrase requires id/source/target/kind strings')
        before, after = source.count(row['source']), target.count(row['target'])
        if before == 0 or before != after:
            issues.append({'code': 'PROTECTED_PHRASE_CHANGED', 'id': row['id'], 'kind': row['kind'],
                           'source_count': before, 'target_count': after})
    return {'status': 'discrepant' if issues else 'consistent', 'issues': issues,
            'semantic_review': 'required', 'phrase_count': len(phrases or []),
            'limitations': ['Occurrence comparison cannot detect swapped values, negation, causal strength or semantic equivalence.',
                           'Add explicit phrase pairs for doses, units, timepoints and declarations; review sentence alignment.',
                           'Numeric normalization allows trailing zeros and decimal/scientific notation, not unit conversion.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--phrases', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output already exists')
        inputs = [args.source, args.target] + ([args.phrases] if args.phrases else [])
        raw = [p.read_bytes() for p in inputs]
        phrases = json.loads(raw[2].decode('utf-8-sig')) if args.phrases else []
        if not isinstance(phrases, list):
            raise ValueError('phrases must be an array')
        result = compare(raw[0].decode('utf-8-sig'), raw[1].decode('utf-8-sig'), phrases)
        result.update(schema_version='1.0', tool='compare_protected', checked_at=datetime.now(timezone.utc).isoformat(),
                      inputs=[{'path': str(p), 'sha256': hashlib.sha256(b).hexdigest()} for p, b in zip(inputs, raw)])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'semantic_review': 'required'}))
        return 0 if not result['issues'] else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
