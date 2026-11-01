#!/usr/bin/env python3
"""Bounded PubMed history search with saved responses, partial-result receipts and offline replay."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import xml.etree.ElementTree as ET

BASE = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Transport:
    def __init__(self, replay=None):
        self.replay = replay
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.last = 0
        self.attempts = []

    def get(self, name, endpoint, params):
        if self.replay:
            return (self.replay / name).read_bytes()
        for attempt in range(3):
            time.sleep(max(0, .4 - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                req = Request(BASE + endpoint + '?' + urlencode(params), headers={'User-Agent': 'dyz-med-public-literature/1.0'})
                with self.opener.open(req, timeout=20) as response:
                    data = response.read(10_000_001)
                if len(data) > 10_000_000:
                    raise ValueError('Response exceeds 10 MB')
                self.attempts.append({'response': name, 'attempt': attempt + 1, 'status': 200})
                return data
            except HTTPError as exc:
                status = exc.code
                exc.close()
                self.attempts.append({'response': name, 'attempt': attempt + 1, 'status': status})
                if status != 429 and status < 500:
                    raise ValueError('HTTP ' + str(status)) from None
            except (URLError, TimeoutError, OSError):
                self.attempts.append({'response': name, 'attempt': attempt + 1, 'status': 'network_error'})
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise ValueError('PubMed request failed after bounded retries')


def search(query, max_records, output, transport, mode):
    if output.exists():
        raise ValueError('Output directory already exists')
    if not query.strip() or len(query) > 4000 or not 1 <= max_records <= 10000:
        raise ValueError('Query must be 1–4000 characters; max_records 1–10000')
    original_context = None
    if getattr(transport, 'replay', None):
        original_context = json.loads((transport.replay / 'context.json').read_text(encoding='utf-8'))
        if original_context.get('query_sha256') != sha(query.encode('utf-8')):
            raise ValueError('Replay query does not match the saved search context')
    output.mkdir(parents=True)
    raw_dir = output / 'responses'
    raw_dir.mkdir()
    context = {'query_sha256': sha(query.encode('utf-8')), 'mode': mode,
               'captured_at': datetime.now(timezone.utc).isoformat()}
    (raw_dir / 'context.json').write_text(json.dumps(context, indent=2), encoding='utf-8')
    receipt = {'schema_version': '1.0', 'mode': mode, 'query': query,
               'searched_at': datetime.now(timezone.utc).isoformat(), 'database': 'PubMed',
               'total_hits': None, 'requested_limit': max_records, 'retrieved': 0,
               'retrieval_complete': False, 'status': 'blocked', 'response_files': [], 'errors': [],
               'identity_verification': 'not_run', 'full_text_read': False}
    articles = []
    if original_context:
        receipt['replayed_context'] = original_context

    def request(name, endpoint, params):
        data = transport.get(name, endpoint, params)
        (raw_dir / name).write_bytes(data)
        receipt['response_files'].append({'path': 'responses/' + name, 'sha256': sha(data)})
        return data

    try:
        result = json.loads(request('search.json', 'esearch.fcgi', {'db': 'pubmed', 'term': query,
                    'retmode': 'json', 'retmax': 0, 'usehistory': 'y'}))['esearchresult']
        total = int(result['count'])
        if total < 0:
            raise ValueError('Invalid negative search count')
        receipt['total_hits'] = total
        receipt['query_translation'] = result.get('querytranslation')
        if result.get('errorlist') or result.get('warninglist'):
            receipt['search_warnings'] = {'errors': result.get('errorlist'), 'warnings': result.get('warninglist')}
            raise ValueError('Search returned query errors/warnings; inspect saved response')
        seen = set()
        limit = min(total, max_records)
        for offset in range(0, limit, 100):
            wanted = min(100, limit - offset)
            raw = request(f'page-{offset:06}.xml', 'efetch.fcgi', {'db': 'pubmed', 'query_key': result['querykey'],
                          'WebEnv': result['webenv'], 'retstart': offset, 'retmax': wanted, 'retmode': 'xml'})
            if b'<!ENTITY' in raw.upper():
                raise ValueError('XML entity declaration unsupported')
            tree = ET.fromstring(raw)
            batch = tree.findall('./PubmedArticle')
            if len(batch) != wanted:
                raise ValueError('Incomplete or unsupported PubMed page; see saved XML')
            for article in batch:
                pmid = article.findtext('./MedlineCitation/PMID')
                if not pmid or pmid in seen:
                    raise ValueError('Missing or duplicated PMID across pages')
                seen.add(pmid)
            articles.extend(ET.tostring(a, encoding='unicode') for a in batch)
        receipt['retrieval_complete'] = len(articles) == total
        receipt['status'] = 'complete' if receipt['retrieval_complete'] else 'partial'
    except (OSError, ValueError, KeyError, ET.ParseError, TypeError) as exc:
        receipt['errors'].append(str(exc))
        receipt['status'] = 'partial' if articles else 'blocked'
    receipt['retrieved'] = len(articles)
    receipt['attempts'] = transport.attempts
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<PubmedArticleSet>\n' + '\n'.join(articles) + '\n</PubmedArticleSet>').encode()
    (output / 'pubmed.xml').write_bytes(xml)
    receipt['export'] = {'path': 'pubmed.xml', 'sha256': sha(xml)}
    (output / 'search-record.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query-file', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-records', type=int, default=100)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--replay-dir', type=Path)
    group.add_argument('--online', action='store_true')
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    try:
        query_raw = args.query_file.read_bytes()
        query = query_raw.decode('utf-8-sig').strip()
        if args.online:
            approval = json.loads(args.authorization.read_text(encoding='utf-8-sig')) if args.authorization else {}
            source = approval.get('source', {})
            if (approval.get('query_sha256') != sha(query_raw) or approval.get('destination') != BASE
                    or approval.get('purpose') != 'public_literature_search' or source.get('kind') != 'human'
                    or not all(isinstance(source.get(k), str) and source[k].strip() for k in ('actor_id', 'statement', 'reference'))
                    or not approval.get('confirmed_at')):
                raise ValueError('Online search needs a current query-bound human authorization record; no request sent')
        result = search(query, args.max_records, args.output_dir, Transport(args.replay_dir), 'online' if args.online else 'offline_replay')
        print(json.dumps({k: result[k] for k in ('status', 'mode', 'total_hits', 'retrieved', 'retrieval_complete')}))
        return 0 if result['status'] == 'complete' else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
