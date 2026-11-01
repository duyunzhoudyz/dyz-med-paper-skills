#!/usr/bin/env python3
"""Import local RIS, BibTeX, NBIB or PubMed XML; preserve provenance and emit <=100-row identity batches."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tagged(text, nbib=False):
    records, fields, key = [], {}, None
    pattern = r'^([A-Z0-9]{2,4})\s*-\s?(.*)$' if nbib else r'^([A-Z0-9]{2})  - ?(.*)$'
    for line in text.splitlines():
        m = re.match(pattern, line)
        if m:
            tag, value = m.groups()
            if (nbib and tag == 'PMID' and fields) or (not nbib and tag == 'TY' and fields):
                if not nbib:
                    raise ValueError('RIS record missing ER terminator')
                records.append(fields)
                fields = {}
            if tag == 'ER':
                records.append(fields)
                fields, key = {}, None
                continue
            fields.setdefault(tag, []).append(value.strip())
            key = tag
        elif line.strip() and key and line[:1].isspace():
            fields[key][-1] += ' ' + line.strip()
        elif line.strip():
            raise ValueError('Unrecognized tagged record line')
    if fields:
        if not nbib:
            raise ValueError('RIS record missing ER terminator')
        records.append(fields)
    return records


def bibtex(text):
    """Bounded literal BibTeX parser; reject macros/concatenation rather than corrupt values."""
    records, pos = [], 0
    while pos < len(text):
        m = re.search(r'@([A-Za-z]+)\s*\{', text[pos:])
        if not m:
            break
        kind = m[1].lower()
        start = pos + m.end()
        depth, quoted, escaped, end = 1, False, False, start
        for end in range(start, len(text)):
            char = text[end]
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == '"' and depth == 1:
                quoted = not quoted
            if not quoted:
                depth += (char == '{') - (char == '}')
            if depth == 0:
                break
        if depth:
            raise ValueError('Unclosed BibTeX entry')
        body, pos = text[start:end], end + 1
        if kind == 'comment':
            continue
        if kind in {'string', 'preamble'}:
            raise ValueError('BibTeX macros/preamble unsupported; export literal fields')
        if ',' not in body:
            raise ValueError('BibTeX entry lacks fields')
        citekey, body = body.split(',', 1)
        fields, cursor = {'citekey': [citekey.strip()]}, 0
        while cursor < len(body):
            while cursor < len(body) and (body[cursor].isspace() or body[cursor] == ','):
                cursor += 1
            if cursor == len(body):
                break
            field = re.match(r'([A-Za-z][A-Za-z0-9_-]*)\s*=\s*', body[cursor:])
            if not field:
                raise ValueError('Unsupported BibTeX field syntax')
            tag, cursor = field[1].lower(), cursor + field.end()
            if tag in fields:
                raise ValueError('Duplicate BibTeX field')
            begin = cursor
            if cursor < len(body) and body[cursor] in '{"':
                opener = body[cursor]
                cursor += 1
                begin, depth, escaped = cursor, 1, False
                while cursor < len(body):
                    ch = body[cursor]
                    if escaped:
                        escaped = False
                    elif ch == '\\':
                        escaped = True
                    elif opener == '{':
                        depth += (ch == '{') - (ch == '}')
                    elif ch == '"':
                        depth = 0
                    if not depth:
                        break
                    cursor += 1
                if depth:
                    raise ValueError('Unclosed BibTeX field')
                value = body[begin:cursor]
                cursor += 1
            else:
                while cursor < len(body) and body[cursor] != ',':
                    cursor += 1
                value = body[begin:cursor].strip()
                if not re.fullmatch(r'\d+', value):
                    raise ValueError('BibTeX string macros/concatenation unsupported')
            if body[cursor:].lstrip().startswith('#'):
                raise ValueError('BibTeX concatenation unsupported')
            fields[tag] = [' '.join(value.split())]
        records.append(fields)
    return records


def xml_records(text):
    if '<!ENTITY' in text.upper():
        raise ValueError('XML entity declarations unsupported')
    tree = ET.fromstring(text)
    records = []
    for article in tree.findall('.//PubmedArticle'):
        def value(path):
            node = article.find(path)
            return ''.join(node.itertext()).strip() if node is not None else ''
        author = article.find('.//AuthorList/Author')
        last = author.findtext('LastName', '') if author is not None else ''
        initials = author.findtext('Initials', '') if author is not None else ''
        doi = next((n.text or '' for n in article.findall('.//ArticleId') if n.get('IdType') == 'doi'), '')
        records.append({'TI': [value('.//ArticleTitle')], 'PMID': [value('.//MedlineCitation/PMID')],
                        'DO': [doi], 'AU': [(' '.join([last, initials])).strip()],
                        'JT': [value('.//Journal/Title')],
                        'DP': [value('.//JournalIssue/PubDate/Year') or value('.//JournalIssue/PubDate/MedlineDate')]})
    return records


def normalize(fields):
    def pick(*keys):
        return next((fields[k][0].strip() for k in keys if fields.get(k) and fields[k][0].strip()), '')
    doi = pick('DO', 'doi')
    if not doi:
        doi = next((v.split(' [doi]')[0] for tag in ('AID', 'LID') for v in fields.get(tag, []) if v.endswith('[doi]')), '')
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', doi, flags=re.I).strip().lower()
    year = re.search(r'\b(\d{4})\b', pick('PY', 'Y1', 'DP', 'year'))
    author = pick('AU', 'A1', 'FAU', 'author').split(' and ')[0]
    return {'title': pick('TI', 'T1', 'title'), 'doi': doi, 'pmid': pick('PMID', 'pmid'),
            'year': year[1] if year else '', 'first_author': author, 'journal': pick('JO', 'JF', 'T2', 'JT', 'TA', 'journal')}


def title_key(title):
    # Formatting braces/punctuation affect neither the candidate warning nor
    # identifier conflict comparison. Preserve the original title/raw fields.
    return re.sub(r'\W', '', unicodedata.normalize('NFKC', title)).casefold()


def import_files(paths):
    records, warnings, inputs = [], [], []
    for path in paths:
        data = path.read_bytes()
        if len(data) > 20_000_000:
            raise ValueError('Input exceeds 20 MB')
        text = data.decode('utf-8-sig')
        suffix = path.suffix.lower()
        if suffix == '.ris':
            rows = tagged(text)
        elif suffix in {'.bib', '.bibtex'}:
            rows = bibtex(text)
        elif suffix in {'.nbib', '.medline'}:
            rows = tagged(text, True)
        elif suffix == '.xml':
            rows = xml_records(text)
        else:
            raise ValueError('Supported formats: RIS, BibTeX, NBIB, PubMed XML')
        if not rows:
            raise ValueError('No recognized records in ' + path.name)
        inputs.append({'path': str(path), 'sha256': sha(data), 'records': len(rows)})
        for index, fields in enumerate(rows, 1):
            row = normalize(fields)
            provenance = {'input_sha256': sha(data), 'record_number': index, 'raw_fields': fields}
            matches = [r for r in records if any(row[k] and row[k] == r[k] for k in ('doi', 'pmid'))]
            if len(matches) == 1:
                existing = matches[0]
                conflict = any(row[k] and existing[k] and row[k] != existing[k] for k in ('doi', 'pmid'))
                title_equal = title_key(row['title']) == title_key(existing['title'])
                if conflict or (row['title'] and existing['title'] and not title_equal):
                    warnings.append({'code': 'IDENTIFIER_CONFLICT', 'record': index, 'input_sha256': sha(data)})
                else:
                    for key, value in row.items():
                        if not existing[key]:
                            existing[key] = value
                    existing['provenance'].append(provenance)
                    continue
            elif len(matches) > 1:
                warnings.append({'code': 'AMBIGUOUS_IDENTIFIER_MERGE', 'record': index, 'input_sha256': sha(data)})
            row.update(id=f'R{len(records) + 1:06}', provenance=[provenance], identity_status='unverified', access_status='imported_metadata')
            if not row['title']:
                warnings.append({'code': 'TITLE_MISSING', 'id': row['id']})
            key = title_key(row['title']), row['year']
            if row['title'] and any((title_key(r['title']), r['year']) == key for r in records):
                warnings.append({'code': 'POSSIBLE_DUPLICATE_REVIEW', 'id': row['id']})
            records.append(row)
    return {'schema_version': '1.0', 'status': 'needs_review' if warnings else 'imported',
            'inputs': inputs, 'records': records, 'warnings': warnings, 'identity_verification': 'not_run'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, nargs='+')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output_dir.exists():
            raise ValueError('Output directory already exists')
        result = import_files(args.inputs)
        args.output_dir.mkdir(parents=True)
        result['batches'] = []
        for start in range(0, len(result['records']), 100):
            name = f'identity-batch-{start // 100 + 1:03}.json'
            rows = [{k: row[k] for k in ('id', 'title', 'doi', 'pmid', 'year', 'first_author', 'journal')}
                    for row in result['records'][start:start + 100]]
            (args.output_dir / name).write_text(json.dumps({'schema_version': '1.0', 'references': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
            result['batches'].append(name)
        (args.output_dir / 'library.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': result['status'], 'records': len(result['records']), 'batches': len(result['batches'])}))
        return 0
    except (OSError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
