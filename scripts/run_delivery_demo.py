#!/usr/bin/env python3
"""Offline synthetic literature -> evidence -> translation -> DOCX demonstration. No medical acceptance."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT/'tests/results') or output.exists():
        raise ValueError('Use a new directory within tests/results')
    output.mkdir(parents=True)

    def write(name, value):
        p = output/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if isinstance(value, bytes) else value.encode('utf-8'))
        return p

    def ref(name):
        return {'path': name, 'sha256': hashlib.sha256((output/name).read_bytes()).hexdigest()}

    imp = load('dyz-med-cnki/scripts/import_references.py', 'demo_import')
    audit = load('dyz-med-evidence-audit/scripts/audit_manuscript.py', 'demo_audit')
    protect = load('dyz-med-translate/scripts/compare_protected.py', 'demo_protect')
    export = load('dyz-med-export/scripts/export_docx.py', 'demo_export')
    ris = write('synthetic.ris', 'TY  - JOUR\nTI  - Synthetic methods example not a real publication\nAU  - Example Author\nPY  - 2026\nER  -\n')
    library = imp.import_files([ris])
    write('library.json', json.dumps(library, ensure_ascii=False, indent=2))
    evidence = 'Synthetic software test only. N=120; group A=60; group B=60; RR=0.80; 95% CI 0.60 to 1.20. No real patients or treatment findings.'
    write('evidence.txt', evidence)
    zh = '本合成示例共纳入120人，A组60人、B组60人。RR为0.80（95%CI 0.60–1.20），结果存在不确定性。'
    en = 'This synthetic example includes 120 participants, with 60 in group A and 60 in group B. The RR is 0.80 (95% CI 0.60–1.20), with uncertainty in the result.'
    manuscript = '# 合成队列研究软件验收样稿\n\n本稿仅用于工具验收，不代表真实临床研究。\n\n## 结果\n\n' + zh + ' [claim:C001] [evidence:E001]\n'
    write('source.md', zh)
    write('translation.md', en)
    write('manuscript.md', manuscript)
    registry = {'schema_version':'1.0','sources':[{'id':'E001',**ref('evidence.txt')}],
                'claims':[{'id':'C001','text_sha256':hashlib.sha256(zh.encode()).hexdigest(),'evidence_ids':['E001'],
                           'source_locators':{'E001':'Synthetic source line 1'},'support_status':'SUPPORTED',
                           'reason':'Synthetic software fixture; not a real evidence judgment.'}]}
    write('registry.json', json.dumps(registry, ensure_ascii=False, indent=2))
    manifest = {'schema_version':'1.0','manuscript':ref('manuscript.md'),'registry':ref('registry.json')}
    write('audit-input.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    audit_report = audit.audit(output, manifest)
    write('audit-report.json', json.dumps(audit_report, ensure_ascii=False, indent=2))
    protected = protect.compare(zh, en)
    write('protected-report.json', json.dumps(protected, ensure_ascii=False, indent=2))
    # A factual mutation must be caught even after the overall file binding is refreshed.
    write('mutated.md', manuscript.replace('120人', '121人'))
    mutation = audit.audit(output, {**manifest, 'manuscript':ref('mutated.md')})
    write('mutation-report.json', json.dumps(mutation, ensure_ascii=False, indent=2))
    table_text = '## 表格与图\n\n|组别 Group|样本量 N|\n|---|---|\n|A|60|\n|B|60|\n\n![图1 合成样本分组示意](figures/groups.png)\n\n## 英文对照\n\n' + en
    write('displays.md', table_text)
    def chunk(tag, data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    width,height=600,160
    pixels=[]
    for y in range(height):
        row=bytearray([0])
        for x in range(width):
            row.extend((56,110,160) if (20<=y<65 or 95<=y<140) and 20<=x<500 else (255,255,255))
        pixels.append(bytes(row))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(pixels)))+chunk(b'IEND',b'')
    write('figures/groups.png',png)
    export_input={'schema_version':'1.0','title':'合成队列研究工具验收样稿','sections':[ref('manuscript.md'),ref('displays.md')],
                  'figures':[ref('figures/groups.png')],'references':{}}
    p=write('export-input.json',json.dumps(export_input,ensure_ascii=False,indent=2))
    delivery=export.build(output,p,output/'delivery')
    summary={'kind':'synthetic_toolchain_demo','imported_records':len(library['records']),
             'manuscript_binding':audit_report['status'],'protected_content':protected['status'],
             'planted_numeric_fault':mutation['status'],'docx':delivery['output'],
             'visual_review':'not_run','semantic_review':'not_run','clinical_acceptance':'not_run',
             'passed':audit_report['status']=='consistent' and protected['status']=='consistent' and mutation['status']=='discrepant'}
    write('summary.json',json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=run(args.output)
        print(json.dumps(result,ensure_ascii=True))
        return 0 if result['passed'] else 1
    except (ValueError,OSError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
