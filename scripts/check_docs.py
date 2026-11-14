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
        self.breadcrumb_links=[]; self.in_breadcrumb=False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')
        if tag=='h1': self.headings+=1
        if tag=='title': self.in_title=True
        if tag=='nav' and 'breadcrumbs' in a.get('class','').split(): self.in_breadcrumb=True
        if tag=='a' and self.in_breadcrumb: self.breadcrumb_links.append(a.get('href'))
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
        if tag=='nav': self.in_breadcrumb=False
        if tag=='title': self.in_title=False
        if tag=='script' and self.in_json:
            self.jsons.append(json.loads(self.current_json)); self.current_json=''; self.in_json=False

    def handle_data(self,data):
        if self.in_title: self.title+=data
        if self.in_json: self.current_json+=data


def check_machine_layer(site, base, page_urls, skill_ids, faq):
    """Validate the files agents read directly: llms.txt, llms-full.txt, skills.json, robots.txt."""
    errors=[]
    llms=site/'llms.txt'
    if not llms.is_file(): return ['llms.txt is missing']
    text=llms.read_text(encoding='utf-8')
    if not text.startswith('# ') or '\n> ' not in text: errors.append('llms.txt needs an H1 and a summary blockquote')
    missing=[url for url in sorted(page_urls) if f']({url})' not in text]
    if missing: errors.append(f'llms.txt omits {len(missing)} page(s), first: {missing[0]}')
    absent=sorted(skill_ids-{i for i in skill_ids if i in text})
    if absent: errors.append(f'llms.txt omits {len(absent)} skill(s), first: {absent[0]}')
    for artifact in ('llms-full.txt','skills.json'):
        if artifact not in text: errors.append(f'llms.txt does not point at {artifact}')
    full=site/'llms-full.txt'
    if not full.is_file(): errors.append('llms-full.txt is missing')
    else:
        body=full.read_text(encoding='utf-8')
        if len(body)<20_000: errors.append(f'llms-full.txt looks truncated ({len(body)} characters)')
        absent=[i for i in sorted(skill_ids) if i not in body]
        if absent: errors.append(f'llms-full.txt omits skill {absent[0]}')
        absent=[url for url in sorted(page_urls) if url not in body]
        if absent: errors.append(f'llms-full.txt omits page {absent[0]}')
    manifest=site/'skills.json'
    if not manifest.is_file(): errors.append('skills.json is missing')
    else:
        data=json.loads(manifest.read_text(encoding='utf-8'))
        if data.get('schema_version')!=1 or data.get('name')!='DYZ MedPaper': errors.append('skills.json header is invalid')
        if data.get('homepage')!=base: errors.append('skills.json homepage must equal the configured site URL')
        entries=data.get('skills') if isinstance(data.get('skills'),list) else []
        if len(entries)!=len(skill_ids) or {e.get('id') for e in entries}!=skill_ids:
            errors.append('skills.json must list every catalog skill exactly once')
        for entry in entries:
            for field in ('triggers','instructions_url','example_url'):
                if not isinstance(entry.get(field),str) or not entry[field].strip():
                    errors.append(f'skills.json {entry.get("id")}: {field} is empty'); break
            for language in ('zh','en'):
                if not entry.get('title',{}).get(language) or not entry.get('summary',{}).get(language):
                    errors.append(f'skills.json {entry.get("id")}: missing {language} title or summary'); break
    robots=site/'robots.txt'
    if not robots.is_file(): errors.append('robots.txt is missing')
    else:
        rules=robots.read_text(encoding='utf-8')
        required=('OAI-SearchBot','ChatGPT-User','Claude-SearchBot','Claude-User','PerplexityBot',
                  'GPTBot','ClaudeBot','Google-Extended','Bytespider')
        absent=[token for token in required if token not in rules]
        if absent: errors.append(f'robots.txt omits AI crawler token {absent[0]}')
        if f'Sitemap: {base}sitemap.xml' not in rules: errors.append('robots.txt sitemap URL does not match the site')
        if 'Disallow' in rules: errors.append('robots.txt must not block crawling for a public beta site')
    key=json.loads((ROOT/'docs/indexnow.json').read_text(encoding='utf-8')).get('key')
    key_file=site/f'{key}.txt'
    if not key_file.is_file() or key_file.read_text(encoding='utf-8').strip()!=key:
        errors.append(f'IndexNow key file {key}.txt is missing or does not contain the key')
    return errors


def check(site):
    metadata=json.loads((ROOT/'docs/repository-metadata.json').read_text(encoding='utf-8'))
    base=metadata['homepage']; prefix=urlsplit(base).path; host=urlsplit(base).netloc
    catalog=json.loads((ROOT/'docs/catalog.json').read_text(encoding='utf-8'))
    faq=json.loads((ROOT/'docs/faq.json').read_text(encoding='utf-8'))
    skill_ids={s['id'] for s in catalog}
    verification_names={'google':'google-site-verification','bing':'msvalidate.01'}
    verification=metadata.get('site_verification',{})
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
        if not page.jsons: errors.append(f'{name}: missing structured data')
        graph=[n for doc in page.jsons if isinstance(doc,dict) for n in doc.get('@graph',[])]
        types={n.get('@type') for n in graph}
        nodes={n.get('@id'):n for n in graph}
        if {'WebSite','WebPage'} - types: errors.append(f'{name}: incomplete structured data graph')
        web_page=nodes.get(expected_url,{})
        if web_page.get('@type')!='WebPage' or web_page.get('url')!=expected_url or web_page.get('inLanguage')!=expected_lang:
            errors.append(f'{name}: WebPage node does not match canonical URL or language')
        site_node=nodes.get(base+'#website',{})
        if site_node.get('@type')!='WebSite' or site_node.get('url')!=base or web_page.get('isPartOf')!={'@id':base+'#website'}:
            errors.append(f'{name}: invalid WebSite reference')
        for node in graph:
            for prop in ('isPartOf','mainEntityOfPage','mainEntity','breadcrumb'):
                ref=node.get(prop,{})
                if isinstance(ref,dict) and '@id' in ref and ref['@id'] not in nodes:
                    errors.append(f'{name}: unresolved structured data reference {prop}')
        tutorial=name.startswith(('tutorials/','en/tutorials/'))
        article=nodes.get(expected_url+'#article',{})
        if tutorial and (article.get('@type')!='TechArticle' or article.get('mainEntityOfPage')!={'@id':expected_url}
                         or web_page.get('mainEntity')!={'@id':expected_url+'#article'}
                         or article.get('inLanguage')!=expected_lang):
            errors.append(f'{name}: invalid task guide article markup')
        if page.meta.get('og:type')!=('article' if tutorial else 'website'):
            errors.append(f'{name}: incorrect Open Graph page type')
        if page.meta.get('robots')!='index, follow, max-snippet:-1, max-image-preview:large':
            errors.append(f'{name}: missing snippet-friendly robots meta')
        if name in ('index.html','en/index.html'):
            if not {'SoftwareApplication','FAQPage'}<=types:
                errors.append(f'{name}: missing application or FAQ structured data')
            if nodes.get(expected_url+'#application',{}).get('name')!='DYZ MedPaper':
                errors.append(f'{name}: application node is missing or misnamed')
            questions=nodes.get(expected_url+'#faq',{}).get('mainEntity',[])
            if len(questions)!=len(faq) or any(not q.get('acceptedAnswer',{}).get('text') for q in questions):
                errors.append(f'{name}: FAQ structured data does not match docs/faq.json')
        if name.endswith('skills/index.html'):
            items=nodes.get(expected_url+'#skills',{}).get('itemListElement',[])
            if len(items)!=len(catalog) or [i.get('position') for i in items]!=list(range(1,len(catalog)+1)):
                errors.append(f'{name}: skill ItemList must cover all {len(catalog)} skills in order')
        for provider,meta_name in verification_names.items():
            if page.meta.get(meta_name)!=verification.get(provider): errors.append(f'{name}: verification tag mismatch for {provider}')
        crumbs=[n for n in graph if n.get('@type')=='BreadcrumbList']
        if name in ('index.html','en/index.html'):
            if crumbs or page.breadcrumb_links: errors.append(f'{name}: home page should not carry a breadcrumb')
        else:
            home_url=base+('en/' if expected_lang=='en' else '')
            items=crumbs[0].get('itemListElement',[]) if len(crumbs)==1 else []
            if len(crumbs)!=1 or [i.get('position') for i in items]!=[1,2] or [i.get('item') for i in items]!=[home_url,expected_url]:
                errors.append(f'{name}: missing or malformed breadcrumb trail')
            if page.breadcrumb_links!=[urlsplit(home_url).path]: errors.append(f'{name}: visible breadcrumb does not match markup')
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
    errors.extend(check_machine_layer(site, base, canonicals, skill_ids, faq))
    for p in site.rglob('*'):
        if p.is_file() and any(part in {'.git','.env','tests','audit-reports','profile'} for part in p.relative_to(site).parts): errors.append(f'Non-public artifact in site: {p}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(canonicals)} pages, {checked_links} internal links, 32 skills per language, reciprocal hreflang and exact sitemap')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=ROOT/'dist/site')
    check(parser.parse_args().site)
