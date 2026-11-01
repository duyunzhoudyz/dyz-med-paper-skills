#!/usr/bin/env python3
"""Check generated public pages, metadata, links and sitemap without networking."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids=set(); self.duplicates=[]; self.urls=[]; self.links=[]; self.meta={}
        self.lang=None; self.headings=0; self.title=''; self.in_title=False
        self.jsons=[]; self.in_json=False; self.current_json=''
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')
        if tag=='h1': self.headings+=1
        if tag=='title': self.in_title=True
        if tag=='script' and a.get('type')=='application/ld+json': self.in_json=True
        if 'id' in a:
            if a['id'] in self.ids: self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        if tag=='meta': self.meta[a.get('name',a.get('property'))]=a.get('content')
        if tag=='link': self.links.append(a)
        if tag=='img' and not a.get('alt'): self.duplicates.append('missing-image-alt')
        for attr in ('href','src'):
            if a.get(attr): self.urls.append(a[attr])

    def handle_endtag(self,tag):
        if tag=='title': self.in_title=False
        if tag=='script' and self.in_json:
            self.jsons.append(json.loads(self.current_json)); self.current_json=''; self.in_json=False

    def handle_data(self,data):
        if self.in_title: self.title+=data
        if self.in_json: self.current_json+=data


def check(site):
    metadata=json.loads((ROOT/'docs/repository-metadata.json').read_text(encoding='utf-8'))
    base=metadata['homepage']; prefix=urlsplit(base).path; host=urlsplit(base).netloc
    docs={p.relative_to(site).as_posix():Page(p.read_text(encoding='utf-8')) for p in site.rglob('*.html')}
    errors=[]; checked_links=0; titles=set(); descriptions=set(); canonicals=set()
    for name,page in docs.items():
        if name=='404.html':
            if page.meta.get('robots')!='noindex': errors.append('404 must be noindex')
            continue
        expected_url=base+(name[:-10] if name.endswith('index.html') else name)
        canonical=[x.get('href') for x in page.links if x.get('rel')=='canonical']
        alternates={x.get('hreflang'):x.get('href') for x in page.links if x.get('rel')=='alternate'}
        expected_lang='en' if name.startswith('en/') else 'zh-CN'
        if canonical!=[expected_url]: errors.append(f'{name}: canonical mismatch {canonical}')
        canonicals.add(expected_url)
        if page.lang!=expected_lang or page.headings!=1 or page.duplicates: errors.append(f'{name}: language, h1 or id error')
        if not {'zh-CN','en','x-default'}<=set(alternates): errors.append(f'{name}: missing language alternatives')
        if not page.title or page.title in titles: errors.append(f'{name}: empty or duplicated title')
        titles.add(page.title)
        description=page.meta.get('description')
        if not description or description in descriptions: errors.append(f'{name}: empty or duplicated description')
        descriptions.add(description)
        if page.meta.get('og:url')!=expected_url or page.meta.get('og:image')!=base+'assets/social-preview.jpg': errors.append(f'{name}: social metadata mismatch')
        if not page.jsons or page.jsons[0].get('url')!=expected_url: errors.append(f'{name}: invalid structured data')
        for url in page.urls:
            u=urlsplit(url)
            if u.netloc and u.netloc!=host:
                # Known source links must point to a real repository artifact.
                marker='/duyunzhoudyz/dyz-med-paper-skills/blob/main/'
                if u.netloc=='github.com' and u.path.startswith(marker):
                    target=ROOT/unquote(u.path[len(marker):])
                    if not target.is_file(): errors.append(f'{name}: missing source {target}')
                continue
            if u.scheme in ('mailto','tel'): continue
            if u.path:
                if not u.path.startswith(prefix): errors.append(f'{name}: URL escapes Pages base path {url}'); continue
                relative=unquote(u.path[len(prefix):])
                target=site/relative
                if u.path.endswith('/'): target/='index.html'
            else: target=site/name
            if not target.is_file(): errors.append(f'{name}: broken local URL {url}'); continue
            checked_links+=1
            if u.fragment and target.suffix=='.html':
                other=docs[target.relative_to(site).as_posix()]
                if unquote(u.fragment) not in other.ids: errors.append(f'{name}: broken anchor {url}')
        # Every translated page must link back to the current page.
        for language,url in alternates.items():
            rel=unquote(urlsplit(url).path[len(prefix):])+'index.html'
            other=docs.get(rel)
            if other is None: errors.append(f'{name}: missing translated page {url}'); continue
            if not any(x.get('rel')=='alternate' and x.get('hreflang')==expected_lang and x.get('href')==expected_url for x in other.links):
                errors.append(f'{name}: non-reciprocal language link {language}')
    tree=ET.parse(site/'sitemap.xml')
    listed={e.text for e in tree.findall('{*}url/{*}loc')}
    if listed!=canonicals: errors.append('Sitemap does not exactly cover canonical pages')
    if len(canonicals)!=20: errors.append(f'Expected 20 public pages, got {len(canonicals)}')
    for catalog_path in ('skills/index.html','en/skills/index.html'):
        skill_ids={s['id'] for s in json.loads((ROOT/'docs/catalog.json').read_text(encoding='utf-8'))}
        if not skill_ids<=docs[catalog_path].ids: errors.append(f'{catalog_path}: incomplete skill index')
    if (site/'assets/social-preview.jpg').stat().st_size>=1_000_000: errors.append('Social preview must stay below 1 MB')
    for p in site.rglob('*'):
        if p.is_file() and any(part in {'.git','.env','tests','audit-reports','profile'} for part in p.relative_to(site).parts): errors.append(f'Non-public artifact in site: {p}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(canonicals)} pages, {checked_links} internal links, 32 skills per language, reciprocal hreflang and exact sitemap')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=ROOT/'dist/site')
    check(parser.parse_args().site)
