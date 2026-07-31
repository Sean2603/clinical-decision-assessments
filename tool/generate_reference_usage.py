#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def collect(value):
    result=set()
    if isinstance(value,dict):
        for k,v in value.items():
            if k=='references' and isinstance(v,list): result.update(x for x in v if isinstance(x,str))
            else: result.update(collect(v))
    elif isinstance(value,list):
        for v in value: result.update(collect(v))
    return result
usage={r['id']:[] for r in load(ROOT/'references/references.json')['references']}
for p in sorted((ROOT/'assessments').glob('*.json')):
    d=load(p)
    for rid in collect(d): usage.setdefault(rid,[]).append({'type':'assessment','id':d['id'],'title':d['title']})
for item in load(ROOT/'clinical_reliability/clinical-reliability.json')['items']:
    for rid in item.get('referenceIds',[]): usage.setdefault(rid,[]).append({'type':item['category'],'id':item['id'],'title':item['displayName']})
out={'generated':True,'references':[{'referenceId':rid,'usedBy':items} for rid,items in sorted(usage.items())]}
path=ROOT/'reference-usage.json'; path.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(f'Generated {path.name} for {len(usage)} references.')
