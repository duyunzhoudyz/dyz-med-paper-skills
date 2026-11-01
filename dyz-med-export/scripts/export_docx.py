#!/usr/bin/env python3
"""Local, dependency-free Markdown subset to review DOCX. No uploads, macros, or raw XML."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def local(root, value):
    if not isinstance(value, str) or not value or ':' in value or '\\' in value or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('Expected project-relative path')
    p = (root / value).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError('Path escapes project')
    return p


def run_text(text):
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    return ''.join('<w:r>' + ('<w:rPr><w:b/></w:rPr>' if part.startswith('**') else '') +
                   '<w:t xml:space="preserve">' + escape(part[2:-2] if part.startswith('**') else part) + '</w:t></w:r>'
                   for part in parts if part)


def paragraph(text, style=None):
    prop = '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>' if style else ''
    return '<w:p>' + prop + run_text(text) + '</w:p>'


def table(rows):
    if not rows:
        raise ValueError('A table must contain cells, not only separator lines')
    cols = len(rows[0])
    if not 1 <= cols <= 8 or any(len(row) != cols for row in rows):
        raise ValueError('Tables require 1–8 consistently sized columns')
    width = 9360 // cols
    border = ''.join('<w:' + side + ' w:val="single" w:sz="4" w:color="D9D9D9"/>' for side in ('top','left','bottom','right','insideH','insideV'))
    result = '<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:tblBorders>' + border + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>'
    result += '<w:tblGrid>' + ('<w:gridCol w:w="' + str(width) + '"/>') * cols + '</w:tblGrid>'
    for i, row in enumerate(rows):
        result += '<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if i == 0 else '') + '</w:trPr>'
        for cell in row:
            result += '<w:tc><w:tcPr><w:tcW w:w="' + str(width) + '" w:type="dxa"/><w:vAlign w:val="center"/>'
            if i == 0:
                result += '<w:shd w:fill="E8EDF2"/>'
            result += '</w:tcPr>' + paragraph(cell, 'TableText') + '</w:tc>'
        result += '</w:tr>'
    return result + '</w:tbl>' + paragraph('')


def picture(rel, index, width, height, caption):
    cx = min(width * 9525, 5943600)
    cy = round(cx * height / width)
    if cy > 7315200:
        cx, cy = round(cx * 7315200 / cy), 7315200
    return f'''<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{index}" name="Figure {index}" descr="{escape(caption, {chr(34): '&quot;'})}"/>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{index}" name="figure.png"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{rel}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>
</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''


def build(root, manifest_path, output):
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('Output must be a new directory inside project')
    manifest_raw = manifest_path.read_bytes()
    config = json.loads(manifest_raw.decode('utf-8-sig'))
    if not isinstance(config, dict) or config.get('schema_version') != '1.0' or not isinstance(config.get('title'), str) or not config['title'].strip():
        raise ValueError('schema_version 1.0 and title required')
    inputs = [{'path': str(manifest_path), 'sha256': sha(manifest_raw)}]

    def bound(ref):
        p = local(root, ref['path'])
        if p == output or output in p.parents:
            raise ValueError('Input cannot be under output directory')
        data = p.read_bytes()
        if len(data) > 20_000_000 or sha(data) != ref.get('sha256'):
            raise ValueError('Input hash mismatch or oversized input: ' + ref['path'])
        inputs.append({'path': ref['path'], 'sha256': sha(data)})
        return data

    sections = config.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('Nonempty sections required')
    texts = [bound(ref).decode('utf-8-sig') for ref in sections]
    all_text = config['title'] + '\n' + '\n'.join(texts)
    if any(x in all_text for x in config.get('forbidden_identity_terms', []) if x):
        raise ValueError('Anonymous manuscript contains a listed identity term')
    if re.search(r'</?[A-Za-z][^>]*>|<!--|```|\$\$', all_text):
        raise ValueError('Raw HTML, code fences and math blocks require another explicit export route')
    references = config.get('references', {})
    if not isinstance(references, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in references.items()):
        raise ValueError('references must map citation keys to author-verified display strings')
    citation_order = []
    for key in re.findall(r'\[@([^\]\n]+)\]', all_text):
        if key not in references:
            raise ValueError('Unresolved citation key: ' + key)
        if key not in citation_order:
            citation_order.append(key)
    def citations(text):
        text = re.sub(r'\[(?:claim|evidence):[^\]\n]+\]', '', text)
        return re.sub(r'\[@([^\]\n]+)\]', lambda m: '[' + str(citation_order.index(m[1]) + 1) + ']', text)
    figures = {}
    for ref in config.get('figures', []):
        data = bound(ref)
        if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) < 24:
            raise ValueError('This export route supports PNG figures only')
        width, height = struct.unpack('>II', data[16:24])
        if not width or not height:
            raise ValueError('Invalid PNG dimensions')
        figures[ref['path']] = (data, width, height)
    warnings = []
    if re.search(r'\[(?:claim|evidence):', all_text):
        warnings.append('INTERNAL_BINDING_MARKERS_OMITTED_FROM_REVIEW_COPY_NOT_VALIDATED_BY_EXPORTER')
    if re.search(r'\b(?:TODO|TBD|FIXME)\b|待补|待核实|占位', all_text, re.I):
        warnings.append('UNRESOLVED_PLACEHOLDERS_PRESERVED')
    body = paragraph(config['title'], 'Title') + paragraph('内部审阅版 / Review draft — 非投稿终版', 'DraftBanner')
    if warnings:
        body += paragraph('存在未解决项目，详见 export-check-report.json。', 'DraftBanner')
    media = []
    for source in texts:
        lines = source.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            if not line:
                continue
            img = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if img:
                if img[2] not in figures:
                    raise ValueError('Figure must be a bound local PNG: ' + img[2])
                data, width, height = figures[img[2]]
                index = len(media) + 1
                media.append(data)
                body += picture('rImg' + str(index), index, width, height, img[1]) + paragraph(citations(img[1]), 'Caption')
                continue
            if '![' in line:
                raise ValueError('Inline images unsupported; put image on a separate line')
            if line.startswith('|'):
                rows = []
                while True:
                    cells = [cell.strip() for cell in line.strip('|').split('|')]
                    if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
                        rows.append([citations(c) for c in cells])
                    if i == len(lines) or not lines[i].strip().startswith('|'):
                        break
                    line, i = lines[i].strip(), i + 1
                body += table(rows)
                continue
            head = re.match(r'^(#{1,3})\s+(.+)', line)
            if head:
                body += paragraph(citations(head[2]), 'Heading' + str(len(head[1])))
            else:
                body += paragraph(citations(line))
    if citation_order:
        body += paragraph('参考文献 References', 'Heading1')
        for i, key in enumerate(citation_order, 1):
            body += paragraph(f'[{i}] ' + references[key])
    # Never remove draft tags or rewrite scientific material to make the file appear complete.
    sect = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1273" w:bottom="1440" w:left="1273"/><w:lnNumType w:countBy="1" w:restart="continuous"/></w:sectPr>'
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}{sect}</w:body></w:document>'
    try:
        ET.fromstring(doc)
    except ET.ParseError as exc:
        raise ValueError('Manuscript contains characters invalid in DOCX XML') from exc
    styles = f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/><w:sz w:val="24"/><w:color w:val="000000"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    for name, size in [('Title', 32), ('Heading1', 28), ('Heading2', 26), ('Heading3', 24), ('DraftBanner', 22), ('TableText', 21), ('Caption', 22)]:
        styles += f'<w:style w:type="paragraph" w:styleId="{name}"><w:name w:val="{name}"/><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/>' + ('<w:keepNext/>' if name in {'Title','Heading1','Heading2','Heading3'} else '') + f'</w:pPr><w:rPr><w:sz w:val="{size}"/><w:color w:val="000000"/>' + ('<w:b/>' if name in {'Title','Heading1','Heading2','Heading3'} else '') + '</w:rPr></w:style>'
    styles += '</w:styles>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rStyles" Type="' + R + '/styles" Target="styles.xml"/>'
    for i in range(1, len(media) + 1):
        rels += f'<Relationship Id="rImg{i}" Type="{R}/image" Target="media/figure{i}.png"/>'
    rels += '</Relationships>'
    types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
    output.mkdir(parents=True)
    dest = output / 'manuscript-review.docx'
    with ZipFile(dest, 'x', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', types)
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rDoc" Type="' + R + '/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml', doc)
        archive.writestr('word/styles.xml', styles)
        archive.writestr('word/_rels/document.xml.rels', rels)
        for i, data in enumerate(media, 1):
            archive.writestr(f'word/media/figure{i}.png', data)
    receipt = {'schema_version': '1.0', 'status': 'generated_review_copy', 'created_at': datetime.now(timezone.utc).isoformat(),
               'inputs': inputs, 'output': {'path': dest.name, 'sha256': sha(dest.read_bytes()), 'bytes': dest.stat().st_size},
               'warnings': warnings, 'citations': citation_order, 'figures': len(media),
               'visual_review': 'not_run', 'scientific_acceptance': 'not_assessed', 'submission_ready': False,
               'limitations': ['Markdown subset: headings, paragraphs, bold, pipe tables, bound PNG, single citation keys.',
                              'No native tracked changes; numbered references use supplied display strings.',
                              'Anonymous identity-term checking is not a complete anonymization audit.']}
    (output / 'export-check-report.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        receipt = build(args.root, local(args.root, args.manifest), local(args.root, args.output_dir))
        print(json.dumps({'status': receipt['status'], 'visual_review': 'not_run', 'submission_ready': False}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
