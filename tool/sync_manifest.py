#!/usr/bin/env python3
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / 'manifest.json'
ASSESSMENTS_DIRECTORY = ROOT / 'assessments'
REFERENCES_PATH = ROOT / 'references' / 'references.json'
ASSESSMENT_SCHEMA_PATH = ROOT / 'schema' / 'assessment-schema.json'
RELIABILITY_PATH = ROOT / 'clinical_reliability' / 'clinical-reliability.json'
RELIABILITY_SCHEMA_PATH = ROOT / 'schema' / 'clinical-reliability-schema.json'
SEMVER_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')

def load_json(path): return json.loads(path.read_text(encoding='utf-8'))
def write_json(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def parts(value):
    if not SEMVER_PATTERN.fullmatch(value): raise SystemExit(f'Invalid semantic version: {value!r}')
    return tuple(map(int, value.split('.')))
def bump(value):
    a,b,c=parts(value); return f'{a}.{b}.{c+1}'
def max_version(values): return max(values, key=parts)

def main():
    previous = load_json(MANIFEST_PATH)
    existing = {e.get('id'): e for e in previous.get('assessments', []) if isinstance(e, dict)}
    entries=[]; versions=[]
    for p in sorted(ASSESSMENTS_DIRECTORY.glob('*.json')):
        doc=load_json(p); aid=doc.get('id'); title=doc.get('title'); version=doc.get('version')
        if not all(isinstance(x,str) and x for x in (aid,title,version)): raise SystemExit(f'Invalid assessment metadata: {p}')
        parts(version); versions.append(version)
        prior=existing.get(aid,{})
        entry={'id':aid,'title':title,'version':version,'file':p.relative_to(ROOT).as_posix(),'schema':'schema/assessment-schema.json','sha256':sha256(p),'schemaSha256':sha256(ASSESSMENT_SCHEMA_PATH)}
        entry.update({k:v for k,v in prior.items() if k not in entry})
        entries.append(entry)

    generated_without_version={
        'schemaVersion': 2,
        'minimumAppVersion': previous.get('minimumAppVersion','0.16.0'),
        'references': {'file':'references/references.json','sha256':sha256(REFERENCES_PATH)},
        'clinicalReliability': {'file':'clinical_reliability/clinical-reliability.json','schema':'schema/clinical-reliability-schema.json','sha256':sha256(RELIABILITY_PATH),'schemaSha256':sha256(RELIABILITY_SCHEMA_PATH)},
        'assessments': entries,
    }
    previous_without_version={k:v for k,v in previous.items() if k not in {'updatedAt','contentVersion'}}
    previous_version=previous.get('contentVersion','0.0.0'); parts(previous_version)
    highest=max_version(versions)
    changed=generated_without_version != previous_without_version
    if changed:
        base = previous_version if parts(previous_version) >= parts(highest) else highest
        version=bump(base)
        updated=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    else:
        version=previous_version
        updated=previous.get('updatedAt') or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    result={'schemaVersion':generated_without_version['schemaVersion'],'contentVersion':version,'updatedAt':updated,'minimumAppVersion':generated_without_version['minimumAppVersion'],'references':generated_without_version['references'],'clinicalReliability':generated_without_version['clinicalReliability'],'assessments':entries}
    write_json(MANIFEST_PATH,result)
    print(f'manifest.json synchronised: contentVersion={version}, changed={str(changed).lower()}')
if __name__ == '__main__': main()
