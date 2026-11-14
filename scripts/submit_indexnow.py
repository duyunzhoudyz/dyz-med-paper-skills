#!/usr/bin/env python3
"""Submit the deployed public pages to IndexNow (Bing, Yandex and other participants).

Google has no equivalent API; use Search Console URL inspection for Googlebot.
Run only after the site is deployed and <base>/<key>.txt is reachable, otherwise
the endpoint rejects the submission. Uses the standard library only.
"""

import argparse
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://api.indexnow.org/indexnow'


def sitemap_urls(path):
    tree = ET.parse(path)
    return [element.text for element in tree.findall('{*}url/{*}loc')]


def key_location(base, key):
    return f'{base}{key}.txt'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sitemap', type=Path, default=ROOT/'dist/site/sitemap.xml',
                        help='built sitemap whose URLs are submitted')
    parser.add_argument('--endpoint', default=ENDPOINT, help='IndexNow endpoint')
    parser.add_argument('--dry-run', action='store_true', help='print the payload without sending')
    args = parser.parse_args()

    metadata = json.loads((ROOT/'docs/repository-metadata.json').read_text(encoding='utf-8'))
    key = json.loads((ROOT/'docs/indexnow.json').read_text(encoding='utf-8'))['key']
    base = metadata['homepage'].rstrip('/') + '/'
    host = urlsplit(base).netloc
    urls = sitemap_urls(args.sitemap)
    if not urls:
        print('No URLs in the sitemap; run scripts/build_docs.py first.')
        return 2

    payload = {'host': host, 'key': key, 'keyLocation': key_location(base, key), 'urlList': urls}
    print(f'{len(urls)} URLs · host {host} · key file {payload["keyLocation"]}')
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    request = urllib.request.Request(
        args.endpoint, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f'IndexNow: HTTP {response.status} {response.reason}')
            return 0 if response.status in (200, 202) else 1
    except urllib.error.HTTPError as exc:
        body = exc.read()[:400].decode('utf-8', 'replace')
        print(f'IndexNow: HTTP {exc.code} {exc.reason} — {body}')
        return 1
    except urllib.error.URLError as exc:
        print(f'IndexNow: network error — {exc.reason}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
