#!/usr/bin/env python3
"""Build the bilingual, fully static documentation site and skill indexes.

Install requirements-docs.txt, then run python scripts/build_docs.py.
Only explicitly selected public assets and authored pages enter dist/site.
"""
import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape

import markdown
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/site'
REPO = 'https://github.com/duyunzhoudyz/dyz-med-paper-skills'
DEFAULT_URL = 'https://duyunzhoudyz.github.io/dyz-med-paper-skills/'
GROUPS = {
    'start': ('起点与项目状态', 'Starting points and project state'),
    'evidence': ('研究设计与文献证据', 'Study design and literature evidence'),
    'analysis': ('统计分析与图表', 'Statistical analysis and figures'),
    'writing': ('论证与论文写作', 'Argument and manuscript writing'),
    'delivery': ('翻译、修订与交付', 'Translation, revision and delivery'),
}
GUIDES = {
    'writing': ('医学论文写作', 'Manuscript writing'),
    'pubmed': ('PubMed 文献检索', 'PubMed literature search'),
    'systematic-review': ('系统综述与 PRISMA', 'Systematic review and PRISMA'),
    'statistics': ('统计结果与临床意义', 'Statistics and clinical importance'),
    'translation': ('医学论文中英翻译', 'Medical translation'),
    'reviewer-response': ('审稿意见逐条回复', 'Response to reviewers'),
}


def source_link(path):
    return f'{REPO}/blob/main/{quote(path, safe="/")}'


def catalog_index(catalog, lang):
    zh = lang == 'zh'
    title = '32 个医学论文 Agent Skills：完整技能索引' if zh else '32 Medical Writing & Research Agent Skills: Complete Catalog'
    out = [f'# {title}', '',
           '[中文首页](../README.md) · [English](../README_EN.md) · [中文索引](skills.md) · [English catalog](skills.en.md)', '',
           ('按当前任务选择技能。每行给出最小输入、主要输出和合成教学示例；示例不是已发表研究或用户反馈。'
            if zh else 'Choose by your current task. Each entry includes inputs, outputs and a synthetic teaching example, not a published study or user testimonial.'), '',
           ('完整技能目录可安装到 Claude Code、Codex 或其他支持 Agent Skills 的宿主。宿主验证范围见 [项目说明](readme-reference.md#status)。'
            if zh else 'Install complete skill directories in Claude Code, Codex or another Agent Skills host. See [validation scope](../README_EN.md#status).'), '']
    for group, names in GROUPS.items():
        out += [f'## {names[0 if zh else 1]}', '',
                '| 技能 / Task | 用途 | 最小输入 | 主要输出 | 示例 |' if zh else '| Skill / Task | Purpose | Minimum input | Main output | Example |',
                '|---|---|---|---|---|']
        for s in catalog:
            if s['group'] != group:
                continue
            out.append(f'| [{s["title"][lang]}](../{s["id"]}/SKILL.md)<br>{s["title"]["en"] if zh else s["id"]} | {s["summary"][lang]} | {s["input"][lang]} | {s["output"][lang]} | [示例 / Example](../{s["example"]}) |')
        out += ['']
    out += [('`passport` 主要由其他技能内部使用；查进度用 `orchestrator`。正式统计、在线数据库检索及复杂排版需要相应软件、权限与材料。'
             if zh else '`passport` primarily supports other skills internally; use `orchestrator` to review progress. Statistical execution, online databases and advanced formatting require the relevant software, access and materials.'), '',
            '<!-- Generated from docs/catalog.json by scripts/build_docs.py; edit the catalog, then use --sync-indexes. -->', '']
    return '\n'.join(out)


def catalog_html(catalog, lang):
    zh = lang == 'zh'
    e = html.escape
    out = [f'<div class="catalog-filter"><label for="skill-filter">{"查找技能" if zh else "Find a skill"}</label>',
           f'<input id="skill-filter" type="search" placeholder="{"输入任务、关键词或技能名" if zh else "Task, keyword or skill name"}" aria-describedby="filter-count">',
           f'<p id="filter-count" role="status" aria-live="polite">32 / 32 {"个技能" if zh else "skills"}</p></div>']
    for group,names in GROUPS.items():
        out += [f'<section class="skill-group"><h2 id="{group}">{names[0 if zh else 1]}</h2>']
        for s in catalog:
            if s['group'] != group:
                continue
            search = e(' '.join([s['id'],*s['title'].values(),*s['summary'].values()]), quote=True)
            out += [f'<article class="skill-entry" id="{s["id"]}" data-skill="{search}">',
                    f'<div class="skill-title"><h3>{e(s["title"][lang])}</h3><code>{s["id"]}</code></div>',
                    f'<p>{e(s["summary"][lang])}</p><dl>',
                    f'<div><dt>{"最小输入" if zh else "Input"}</dt><dd>{e(s["input"][lang])}</dd></div>',
                    f'<div><dt>{"主要输出" if zh else "Output"}</dt><dd>{e(s["output"][lang])}</dd></div></dl>',
                    f'<p class="skill-links"><a href="{source_link(s["id"]+"/SKILL.md")}">{"技能说明" if zh else "Skill instructions"} ↗</a>',
                    f'<a href="{source_link(s["example"])}">{"查看教学示例" if zh else "Teaching example"} ↗</a></p></article>']
        out += ['</section>']
    out += [f'<p id="filter-empty" hidden>{"没有匹配的技能。试试 PubMed、翻译、revision 或写作。" if zh else "No matching skills. Try PubMed, translation, revision or writing."}</p>']
    return '\n'.join(out)


def parse_page(path):
    raw = path.read_text(encoding='utf-8')
    if not raw.startswith('---\n'):
        raise ValueError(f'Missing frontmatter: {path}')
    _, front, body = raw.split('---', 2)
    meta = yaml.safe_load(front)
    if not all(isinstance(meta.get(k), str) and meta[k].strip() for k in ('title','description')):
        raise ValueError(f'Missing title/description: {path}')
    return meta, body


def page_key(path):
    return path.with_suffix('').relative_to(SOURCE).as_posix()


def page_route(key):
    lang, slug = key.split('/', 1)
    return ('en/' if lang == 'en' else '') + ('' if slug == 'index' else slug + '/')


def page_schema(meta, url, base_url, zh, slug, catalog, faq):
    """Describe the site, page and visible navigation without inventing authorship."""
    lang = 'zh-CN' if zh else 'en'
    key = 'zh' if zh else 'en'
    site = base_url + '#website'
    home_url = base_url + ('' if zh else 'en/')
    graph = [
        {'@type': 'WebSite', '@id': site, 'name': 'DYZ MedPaper', 'url': base_url,
         'inLanguage': ['zh-CN', 'en'], 'sameAs': [REPO]},
    ]
    page = {'@type': 'WebPage', '@id': url, 'url': url, 'name': meta['title'],
            'description': meta['description'], 'inLanguage': lang,
            'isPartOf': {'@id': site}}
    if slug != 'index':
        page['breadcrumb'] = {'@id': url + '#breadcrumb'}
        graph.append({'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': '首页' if zh else 'Home', 'item': home_url},
            {'@type': 'ListItem', 'position': 2, 'name': meta['title'], 'item': url}]})
    graph.append(page)
    if slug.startswith('tutorials/'):
        page['mainEntity'] = {'@id': url + '#article'}
        graph.append({'@type': 'TechArticle', '@id': url + '#article', 'headline': meta['title'],
                      'description': meta['description'], 'inLanguage': lang,
                      'mainEntityOfPage': {'@id': url}, 'isPartOf': {'@id': site}})
    if slug == 'index':
        # The site as a product for answer engines, plus the FAQ text they may quote.
        page['mainEntity'] = {'@id': url + '#application'}
        graph.append({'@type': 'SoftwareApplication', '@id': url + '#application',
                      'name': 'DYZ MedPaper', 'url': base_url,
                      'applicationCategory': 'DeveloperApplication',
                      'operatingSystem': 'Windows, macOS, Linux', 'isAccessibleForFree': True,
                      'license': REPO + '/blob/main/LICENSE', 'sameAs': [REPO],
                      'description': meta['description'], 'inLanguage': lang})
        graph.append({'@type': 'FAQPage', '@id': url + '#faq', 'isPartOf': {'@id': site},
                      'mainEntityOfPage': {'@id': url}, 'inLanguage': lang,
                      'mainEntity': [{'@type': 'Question', 'name': item['q'][key],
                                      'acceptedAnswer': {'@type': 'Answer', 'text': item['a'][key]}}
                                     for item in faq]})
    if slug == 'skills':
        graph.append({'@type': 'ItemList', '@id': url + '#skills', 'numberOfItems': len(catalog),
                      'itemListElement': [{'@type': 'ListItem', 'position': position,
                                           'name': s['id'], 'description': s['summary'][key],
                                           'url': source_link(s['id'] + '/SKILL.md')}
                                          for position, s in enumerate(catalog, 1)]})
    return json.dumps({'@context': 'https://schema.org', '@graph': graph},
                      ensure_ascii=False).replace('<', '\\u003c')


LICENSE_LINE = 'PolyForm Noncommercial 1.0.0'
SEARCH_BOTS = ('OAI-SearchBot', 'ChatGPT-User', 'Claude-SearchBot', 'Claude-User', 'PerplexityBot',
               'Googlebot', 'Bingbot', 'DuckAssistBot', 'Amzn-SearchBot')
TRAINING_BOTS = ('GPTBot', 'ClaudeBot', 'Google-Extended', 'Applebot-Extended', 'Bytespider', 'CCBot')


def skill_frontmatter_description(skill_id):
    """Reuse the authored trigger text so agents match the same wording the host sees."""
    text = (ROOT/skill_id/'SKILL.md').read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError(f'Missing frontmatter: {skill_id}')
    front = text.split('\n---', 1)[0][len('---\n'):]
    description = (yaml.safe_load(front) or {}).get('description')
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f'Missing description: {skill_id}')
    return ' '.join(description.split())


def skills_manifest(base_url, catalog):
    """One file an agent can read to decide whether this collection fits a request."""
    return {
        'schema_version': 1,
        'name': 'DYZ MedPaper',
        'aliases': ['dyz-med-paper-skills', 'DYZ MedPaper 医学论文技能'],
        'description': {
            'zh': '面向中国医生与医学研究生的 32 个医学论文写作与科研 Agent Skills，适用于 Claude Code、Codex 等支持 Agent Skills 的智能体。',
            'en': '32 medical writing and research Agent Skills for doctors and medical postgraduate students in China, for Claude Code, Codex and other Agent Skills hosts.'},
        'homepage': base_url,
        'repository': REPO,
        'license': LICENSE_LINE,
        'license_url': REPO + '/blob/main/LICENSE',
        'status': 'public beta',
        'hosts': ['Claude Code', 'Codex', 'other Agent Skills hosts'],
        'install': {'claude_code': 'python scripts/install_codex.py --target "~/.claude/skills"',
                    'codex': 'python scripts/install_codex.py'},
        'documentation': {'index_zh': base_url, 'index_en': base_url + 'en/',
                          'catalog_zh': base_url + 'skills/', 'catalog_en': base_url + 'en/skills/',
                          'faq': base_url + '#faq', 'llms_txt': base_url + 'llms.txt',
                          'llms_full_txt': base_url + 'llms-full.txt'},
        'skills': [{'id': s['id'], 'group': s['group'], 'title': s['title'], 'summary': s['summary'],
                    'input': s['input'], 'output': s['output'],
                    'triggers': skill_frontmatter_description(s['id']),
                    'instructions_url': source_link(s['id'] + '/SKILL.md'),
                    'example_url': source_link(s['example'])} for s in catalog],
    }


def skill_blocks(catalog, key, heading='##'):
    lines = []
    for s in catalog:
        lines += [f'{heading} {s["id"]} — {s["title"][key]}', '', s['summary'][key], '',
                  f'- 输入 / Input: {s["input"][key]}',
                  f'- 输出 / Output: {s["output"][key]}',
                  f'- 说明 / Instructions: {source_link(s["id"] + "/SKILL.md")}', '']
    return lines


def faq_markdown(faq, key):
    lines = []
    for item in faq:
        lines += [f'**{item["q"][key]}**', '', item['a'][key], '']
    return lines


def faq_html(faq, zh):
    key = 'zh' if zh else 'en'
    e = html.escape
    out = [f'<section class="faq" id="faq"><h2>{"常见问题" if zh else "Frequently asked questions"}</h2>']
    out += [f'<details><summary>{e(item["q"][key])}</summary><p>{e(item["a"][key])}</p></details>' for item in faq]
    out += ['</section>']
    return '\n'.join(out)


def llms_txt(base_url, pages, catalog, faq):
    def entries(prefix):
        return [f'- [{meta["title"]}]({base_url}{page_route(key)}): {meta["description"]}'
                for key, (_, meta, _body) in pages.items() if key.split('/', 1)[0] == prefix]
    out = ['# DYZ MedPaper', '',
           ('> 面向中国医生与医学研究生的 32 个医学论文写作与科研 Agent Skills，适用于 Claude Code、Codex 等支持 '
            'Agent Skills 的智能体；中文沟通，中英写作，覆盖选题、PubMed 检索、统计结果解读、选刊与审稿修回。'
            '32 medical writing and research Agent Skills for doctors and medical postgraduate students in China, '
            'for Claude Code, Codex and other Agent Skills hosts.'), '',
           f'- 仓库 / Repository: {REPO}',
           f'- 文档站 / Documentation: {base_url}',
           f'- 机器可读技能清单 / Machine-readable catalog: {base_url}skills.json',
           f'- 全文 Markdown / Full Markdown: {base_url}llms-full.txt',
           f'- 许可 / License: {LICENSE_LINE} — {REPO}/blob/main/LICENSE',
           '- 状态 / Status: 公开测试版 public beta；真实宿主路由、连续写作与独立医学质量尚未全部验收。',
           '- 范围 / Scope: 内置在线检索只覆盖 PubMed；统计执行需要已批准的方案与本地环境。', '',
           '## 中文文档', ''] + entries('zh') + \
          ['', '## English documentation', ''] + entries('en') + \
          ['', '## 技能 / Skills (32)', ''] + [f'- [{s["id"]} — {s["title"]["zh"]} / {s["title"]["en"]}]'
                                              f'({source_link(s["id"] + "/SKILL.md")}): {s["summary"]["zh"]} '
                                              f'{s["summary"]["en"]}' for s in catalog] + \
          ['', '## 常见问题 / FAQ', ''] + faq_markdown(faq, 'zh') + ['---', ''] + faq_markdown(faq, 'en') + \
          ['## Optional', '',
           f'- [llms-full.txt]({base_url}llms-full.txt): 全部页面正文与 32 个技能的完整清单 / every page body and the full skill catalog',
           f'- [skills.json]({base_url}skills.json): 结构化技能清单与触发词 / structured skill catalog with trigger text', '']
    return '\n'.join(out)


def llms_full_txt(base_url, pages, catalog, faq):
    out = ['# DYZ MedPaper — full text', '',
           f'> 32 个医学论文写作与科研 Agent Skills / 32 medical writing and research Agent Skills. '
           f'仓库 / Repository: {REPO} · 文档站 / Docs: {base_url}', '',
           '## 常见问题 / FAQ', ''] + faq_markdown(faq, 'zh') + faq_markdown(faq, 'en')
    out += ['## 技能完整清单 / Complete skill catalog', ''] + skill_blocks(catalog, 'zh') + skill_blocks(catalog, 'en')
    out += ['## 页面正文 / Page text', '']
    for key, (_, meta, body) in pages.items():
        zh = key.startswith('zh/')
        lang_root = base_url + ('' if zh else 'en/')
        text = (body.replace('{{root}}', lang_root).replace('{{repo}}', REPO)
                .replace('{{catalog}}', '\n'.join(skill_blocks(catalog, 'zh' if zh else 'en', '###')))
                .replace('{{faq}}', '\n'.join(faq_markdown(faq, 'zh' if zh else 'en'))))
        out += [f'### {meta["title"]}', '', f'{base_url}{page_route(key)}', '', text.strip(), '']
    return '\n'.join(out)


def robots_text(base_url):
    """State retrieval intent in the file type these crawlers read first."""
    lines = ['# DYZ MedPaper：允许检索、训练语料与用户触发的抓取，便于被检索与引用。',
             '# GitHub Pages 的项目子路径 robots.txt 只对主动请求该路径的客户端生效；',
             '# 域名根级 robots.txt 由 github.io 提供，无法在此修改。', '',
             'User-agent: *', 'Allow: /', '',
             '# 搜索索引与用户触发抓取 / search indexes and user-triggered fetches']
    lines += [f'User-agent: {bot}' for bot in SEARCH_BOTS]
    lines += ['Allow: /', '', '# 训练语料 / training corpora']
    lines += [f'User-agent: {bot}' for bot in TRAINING_BOTS]
    lines += ['Allow: /', '', f'Sitemap: {base_url}sitemap.xml', '']
    return '\n'.join(lines)


def build(output, base_url, sync_indexes=False):
    base_url = base_url.rstrip('/') + '/'
    parts = urlsplit(base_url)
    if parts.scheme != 'https' or not parts.netloc or parts.query or parts.fragment:
        raise ValueError('base-url must be an absolute HTTPS URL without query or fragment')
    base_path = parts.path
    metadata = json.loads((ROOT/'docs/repository-metadata.json').read_text(encoding='utf-8'))
    verification = metadata.get('site_verification', {})
    verification_names = {'google': 'google-site-verification', 'bing': 'msvalidate.01'}
    if not isinstance(verification, dict) or verification.keys() - verification_names.keys():
        raise ValueError('site_verification supports only google and bing tokens')
    verification_tags = []
    for provider, token in verification.items():
        if not isinstance(token, str) or not token.strip():
            raise ValueError(f'Empty or invalid site verification token: {provider}')
        verification_tags.append(f'<meta name="{verification_names[provider]}" content="{html.escape(token, quote=True)}">')
    faq = json.loads((ROOT/'docs/faq.json').read_text(encoding='utf-8'))
    if not isinstance(faq, list) or len(faq) < 4:
        raise ValueError('docs/faq.json must hold at least four question entries')
    for item in faq:
        for field in ('q', 'a'):
            values = item.get(field) if isinstance(item, dict) else None
            if not isinstance(values, dict) or not all(isinstance(values.get(lang), str) and values[lang].strip()
                                                       for lang in ('zh', 'en')):
                raise ValueError(f'FAQ entry needs non-empty zh and en {field}')
    indexnow = json.loads((ROOT/'docs/indexnow.json').read_text(encoding='utf-8'))
    indexnow_key = indexnow.get('key') if isinstance(indexnow, dict) else None
    if not isinstance(indexnow_key, str) or not re.fullmatch(r'[A-Za-z0-9-]{8,128}', indexnow_key):
        raise ValueError('docs/indexnow.json needs an 8-128 character alphanumeric key')
    catalog = json.loads((ROOT/'docs/catalog.json').read_text(encoding='utf-8'))
    actual = {p.parent.name for p in ROOT.glob('dyz-med-*/SKILL.md')}
    if len(catalog) != 32 or len({s['id'] for s in catalog}) != 32 or {s['id'] for s in catalog} != actual:
        raise ValueError('Catalog must cover exactly the 32 existing skills')
    for s in catalog:
        if s['group'] not in GROUPS or not (ROOT/s['example']).is_file():
            raise ValueError(f'Invalid catalog source: {s["id"]}')
    for lang, name in [('zh','skills.md'),('en','skills.en.md')]:
        expected = catalog_index(catalog, lang)
        target = ROOT/'docs'/name
        if sync_indexes:
            target.write_text(expected, encoding='utf-8', newline='\n')
        elif not target.exists() or target.read_text(encoding='utf-8') != expected:
            raise ValueError(f'Stale {name}; run with --sync-indexes')
    pages = {page_key(p):(p,*parse_page(p)) for p in sorted(SOURCE.glob('**/*.md'))}
    template = (SOURCE/'template.html').read_text(encoding='utf-8')
    output.mkdir(parents=True,exist_ok=True)
    assets=output/'assets'
    assets.mkdir(exist_ok=True)
    for filename in ('site.css','site.js','favicon.svg'):
        shutil.copyfile(SOURCE/filename, assets/filename)
    for filename in ('social-preview.jpg',):
        shutil.copyfile(ROOT/'docs/assets'/filename, assets/filename)
    sitemap=[]
    for key,(path,meta,body) in pages.items():
        lang, slug=key.split('/',1)
        zh=lang=='zh'
        other=('en' if zh else 'zh')+'/'+slug
        if other not in pages:
            raise ValueError(f'Missing language counterpart: {other}')
        route=page_route(key)
        url=base_url+route
        lang_root=base_path+('' if zh else 'en/')
        body=body.replace('{{root}}',lang_root).replace('{{repo}}',REPO)
        content=markdown.markdown(body,extensions=['tables','fenced_code','toc','attr_list'],output_format='html')
        content=content.replace('<p>{{catalog}}</p>',catalog_html(catalog,lang))
        content=content.replace('<p>{{faq}}</p>',faq_html(faq,zh))
        nav=[]
        for name,labels in [('index',('项目首页','Overview')),('install',('安装与开始','Installation')),('skills',('32 个技能','32 skills')),('about',('状态与许可','Status & license'))]:
            link=lang_root+('' if name=='index' else name+'/')
            current=' aria-current="page"' if slug==name else ''
            nav.append(f'<a href="{link}"{current}>{labels[0 if zh else 1]}</a>')
        nav.append(f'<p class="nav-label">{"任务教程" if zh else "TASK GUIDES"}</p>')
        for i,(name,labels) in enumerate(GUIDES.items(),1):
            current=' aria-current="page"' if slug=='tutorials/'+name else ''
            nav.append(f'<a href="{lang_root}tutorials/{name}/"{current}><span class="nav-number">{i:02}</span>{labels[0 if zh else 1]}</a>')
        breadcrumb = ''
        if slug != 'index':
            label = '当前位置' if zh else 'Breadcrumb'
            home = '首页' if zh else 'Home'
            breadcrumb = (f'<nav class="breadcrumbs" aria-label="{label}">'
                          f'<a href="{lang_root}">{home}</a><span aria-hidden="true"> / </span>'
                          f'<span aria-current="page">{html.escape(meta["title"])}</span></nav>')
        data={
            'html_lang':'zh-CN' if zh else 'en','title':html.escape(meta['title']+' | DYZ MedPaper'),
            'description':html.escape(meta['description'],quote=True),'canonical':url,
            'zh_url':base_url+page_route('zh/'+slug),'en_url':base_url+page_route('en/'+slug),
            'base':base_path,'root':lang_root,'other':base_path+page_route(other),
            'other_label':'English' if zh else '简体中文','other_lang':'en' if zh else 'zh-CN','nav':'\n'.join(nav),'content':content,
            'heading':html.escape(meta.get('heading',meta['title'])),'lead':html.escape(meta['description']),
            'eyebrow':'为中国医生与医学研究生' if zh else 'FOR DOCTORS & MEDICAL POSTGRADUATES IN CHINA',
            'kind':'home' if slug=='index' else 'document','skip':'跳到正文' if zh else 'Skip to content',
            'menu':'文档导航' if zh else 'Documentation navigation','repo':REPO,
            'image':base_url+'assets/social-preview.jpg','locale':'zh_CN' if zh else 'en_US',
            'footer':'源码公开 · PolyForm Noncommercial 1.0.0 · 公开测试版' if zh else 'Source-available · PolyForm Noncommercial 1.0.0 · Public beta',
            'edit_label':'在 GitHub 查看本页源码' if zh else 'View page source on GitHub',
            'edit_url':source_link(path.relative_to(ROOT).as_posix()),
            'schema':page_schema(meta,url,base_url,zh,slug,catalog,faq),
            'breadcrumb':breadcrumb,'verification':'\n  '.join(verification_tags),
            'og_type':'article' if slug.startswith('tutorials/') else 'website',
        }
        rendered=template
        for token,value in data.items():
            rendered=rendered.replace('{{'+token+'}}',value)
        if re.search(r'{{\w+}}',rendered):
            raise ValueError(f'Unresolved template token in {key}')
        target=output/route/'index.html'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(rendered,encoding='utf-8',newline='\n')
        sitemap.append(f'<url><loc>{escape(url)}</loc><xhtml:link rel="alternate" hreflang="zh-CN" href="{escape(data["zh_url"])}"/><xhtml:link rel="alternate" hreflang="en" href="{escape(data["en_url"])}"/></url>')
    (output/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'+'\n'.join(sitemap)+'\n</urlset>\n',encoding='utf-8')
    (output/'robots.txt').write_text(robots_text(base_url),encoding='utf-8')
    (output/f'{indexnow_key}.txt').write_text(indexnow_key,encoding='utf-8',newline='\n')
    (output/'llms.txt').write_text(llms_txt(base_url,pages,catalog,faq),encoding='utf-8',newline='\n')
    (output/'llms-full.txt').write_text(llms_full_txt(base_url,pages,catalog,faq),encoding='utf-8',newline='\n')
    (output/'skills.json').write_text(json.dumps(skills_manifest(base_url,catalog),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    (output/'404.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Page not found | DYZ MedPaper</title><link rel="stylesheet" href="{base_path}assets/site.css"><main class="not-found"><p>404 · DYZ MedPaper</p><h1>这一页不在这里。<br>Page not found.</h1><a href="{base_path}">返回文档首页 / Documentation home →</a></main></html>',encoding='utf-8')
    print(f'Built {len(pages)} bilingual pages, {len(catalog)} catalog entries, llms.txt, llms-full.txt and skills.json in {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/site')
    parser.add_argument('--base-url',default=DEFAULT_URL)
    parser.add_argument('--sync-indexes',action='store_true')
    args=parser.parse_args()
    build(args.output,args.base_url,args.sync_indexes)
