#!/usr/bin/env python3
"""Save an authenticated, read-only GitHub traffic snapshot to ignored local state."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPO='duyunzhoudyz/dyz-med-paper-skills'


def api(path):
    result=subprocess.run(['gh','api',f'repos/{REPO}/{path}'],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'GitHub request failed for {path}; check gh authentication and repository permissions.')
    return json.loads(result.stdout)


if __name__=='__main__':
    timestamp=datetime.now(timezone.utc)
    data={'repository':REPO,'captured_at_utc':timestamp.isoformat(),'window':'GitHub rolling 14-day views/clones; not installation counts'}
    for key,path in {'views':'traffic/views','clones':'traffic/clones','referrers':'traffic/popular/referrers','paths':'traffic/popular/paths'}.items():
        data[key]=api(path)
    output=ROOT/'audit-reports/seo'/('traffic-'+timestamp.strftime('%Y%m%dT%H%M%SZ')+'.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(f'Saved local traffic snapshot: {output}')
