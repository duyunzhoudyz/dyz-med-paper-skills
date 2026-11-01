#!/usr/bin/env python3
"""Bind actual Markdown paragraphs to an existing claim/evidence registry. Offline."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata

CLAIM = re.compile(r'\[claim:([A-Za-z][A-Za-z0-9_-]*)\]')
EVIDENCE = re.compile(r'\[evidence:([^\]\n]+)\]')
SUPPORT = {'SUPPORTED', 'PARTIAL', 'MISSTATED', 'UNSUPPORTED', 'UNVERIFIABLE', 'CONFLICTING'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plain(block):
    return ' '.join(unicodedata.normalize('NFC', EVIDENCE.sub('', CLAIM.sub('', block))).split())


def local(root, name):
    if not isinstance(name, str) or not name or ':' in name or '\\' in name or any(x in ('', '.', '..') for x in name.split('/')):
        raise ValueError('Expected a safe project-relative path')
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Path escapes project')
    return p


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs)


def paragraphs(text):
    line, pending, start = 1, [], 1
    for value in text.splitlines():
        if value.strip():
            if not pending:
                start = line
            pending.append(value)
        elif pending:
            yield start, '\n'.join(pending)
            pending = []
        line += 1
    if pending:
        yield start, '\n'.join(pending)


def audit(root, manifest):
    root = root.resolve()
    if not isinstance(manifest, dict) or manifest.get('schema_version') != '1.0':
        raise ValueError('schema_version must be 1.0')
    issues, bound = [], []

    def issue(code, location, severity='error'):
        issues.append({'code': code, 'location': location, 'severity': severity})

    def load_bound(ref, location):
        if not isinstance(ref, dict):
            raise ValueError('Missing file binding: ' + location)
        p = local(root, ref.get('path'))
        data = p.read_bytes()
        actual = sha(data)
        bound.append({'path': ref['path'], 'sha256': actual})
        if actual != ref.get('sha256'):
            issue('INPUT_CHANGED', location)
        return data

    manuscript = load_bound(manifest.get('manuscript'), 'manuscript').decode('utf-8-sig')
    registry_bytes = load_bound(manifest.get('registry'), 'registry')
    registry = read_json(local(root, manifest['registry']['path']))
    if sha(registry_bytes) != sha(local(root, manifest['registry']['path']).read_bytes()):
        raise ValueError('Registry changed while reading')
    if not isinstance(registry, dict) or registry.get('schema_version') != '1.0':
        raise ValueError('Registry schema_version must be 1.0')
    claims, sources = {}, {}
    for row in registry.get('sources', []):
        if not isinstance(row, dict):
            raise ValueError('Each evidence source must be an object')
        identity = row.get('id')
        if not isinstance(identity, str) or not identity or identity in sources:
            raise ValueError('Duplicate or invalid evidence id')
        sources[identity] = row
        # Missing sources remain unverified; they are never silently passed.
        if not row.get('path'):
            issue('SOURCE_UNAVAILABLE', identity, 'review')
        else:
            try:
                load_bound(row, identity)
            except FileNotFoundError:
                issue('SOURCE_MISSING', identity)
    for row in registry.get('claims', []):
        if not isinstance(row, dict):
            raise ValueError('Each claim must be an object')
        identity = row.get('id')
        if not isinstance(identity, str) or not identity or identity in claims:
            raise ValueError('Duplicate or invalid claim id')
        claims[identity] = row
        if row.get('support_status') not in SUPPORT:
            issue('UNKNOWN_SUPPORT_STATUS', identity)
        elif row['support_status'] != 'SUPPORTED':
            issue('CLAIM_REQUIRES_REVIEW', identity, 'review')
            if not isinstance(row.get('action'), str) or not row['action'].strip():
                issue('ACTION_MISSING', identity)
        if not row.get('reason'):
            issue('SUPPORT_REASON_MISSING', identity, 'review')
        ids = row.get('evidence_ids')
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
            issue('EVIDENCE_LIST_INVALID', identity)
            ids = []
        locators = row.get('source_locators', {})
        if not isinstance(locators, dict):
            raise ValueError('source_locators must be an object')
        for source in ids:
            if source not in sources:
                issue('UNKNOWN_EVIDENCE', identity + '/' + str(source))
            if not isinstance(locators.get(source), str) or not locators[source].strip():
                issue('SOURCE_LOCATOR_MISSING', identity + '/' + str(source), 'review')
    seen, observed = set(), []
    for line, block in paragraphs(manuscript):
        ids = CLAIM.findall(block)
        marked = [item.strip() for group in EVIDENCE.findall(block) for item in group.split(',')]
        location = 'line:' + str(line)
        if re.search(r'\b(?:TODO|TBD|FIXME)\b|待补|待核实|占位', block, re.I):
            issue('UNRESOLVED_PLACEHOLDER', location, 'review')
        if not ids:
            if marked:
                issue('EVIDENCE_WITHOUT_CLAIM', location)
            if re.search(r'\d', block) and not block.lstrip().startswith('#'):
                issue('UNREGISTERED_NUMERIC_PARAGRAPH', location, 'review')
            continue
        if len(ids) != 1:
            issue('AMBIGUOUS_CLAIM_BLOCK', location)
            continue
        identity = ids[0]
        if identity in seen:
            issue('DUPLICATE_CLAIM_MARKER', location)
        seen.add(identity)
        row = claims.get(identity)
        if row is None:
            issue('UNKNOWN_CLAIM', location)
            continue
        checksum = sha(plain(block).encode('utf-8'))
        observed.append({'claim_id': identity, 'line': line, 'text_sha256': checksum})
        if checksum != row.get('text_sha256'):
            issue('CLAIM_TEXT_CHANGED', identity + '/' + location)
        if set(marked) != set(row.get('evidence_ids', [])) or len(marked) != len(set(marked)):
            issue('EVIDENCE_MARKER_MISMATCH', identity + '/' + location)
    for identity in claims.keys() - seen:
        issue('CLAIM_NOT_IN_MANUSCRIPT', identity)
    if not claims or not seen:
        issue('EMPTY_COVERAGE', 'manuscript')
    return {'schema_version': '1.0', 'tool': 'audit_manuscript', 'checked_at': datetime.now(timezone.utc).isoformat(),
            'status': 'discrepant' if any(x['severity'] == 'error' for x in issues) else 'needs_review' if issues else 'consistent',
            'scientific_acceptance': 'not_assessed', 'inputs': bound, 'issues': issues, 'observed_claims': observed,
            'coverage': {'registered': len(claims), 'observed': len(seen)},
            'limitations': ['Mechanical binding only; support statuses are author-supplied, not authenticated.',
                           'Unmarked nonnumeric claims and semantic entailment require human review.',
                           'One claim marker per blank-line-delimited Markdown paragraph; tables need explicit scoping.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        output = local(args.root, args.output)
        if output.exists():
            raise ValueError('Output already exists')
        result = audit(args.root, read_json(local(args.root, args.manifest)))
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'status': result['status'], 'report': args.output, 'scientific_acceptance': 'not_assessed'}))
        return 0 if result['status'] == 'consistent' else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
