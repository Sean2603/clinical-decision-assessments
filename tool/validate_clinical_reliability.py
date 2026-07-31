#!/usr/bin/env python3
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parent.parent
DOC=ROOT/'clinical_reliability'/'clinical-reliability.json'
SCHEMA=ROOT/'schema'/'clinical-reliability-schema.json'
REFS=ROOT/'references'/'references.json'
def main():
 d=json.loads(DOC.read_text()); s=json.loads(SCHEMA.read_text()); errors=[]
 for e in Draft202012Validator(s,format_checker=FormatChecker()).iter_errors(d): errors.append(f"{'.'.join(map(str,e.absolute_path))}: {e.message}")
 refs={r['id'] for r in json.loads(REFS.read_text())['references']}; seen=set()
 for item in d.get('items',[]):
  key=(item.get('category'),item.get('id'))
  if key in seen: errors.append(f'duplicate reliability item: {key}')
  seen.add(key)
  missing=set(item.get('referenceIds',[]))-refs
  if missing: errors.append(f"{item.get('id')}: unknown reference IDs: {', '.join(sorted(missing))}")
  if item.get('reviewStatus')=='current':
   for f in ('reviewedBy','reviewerRole','lastReviewed','nextReviewDue'):
    if not item.get(f): errors.append(f"{item.get('id')}: current item requires {f}")
 if errors:
  print('Clinical reliability validation failed:'); [print('-',x) for x in errors]; return 1
 print(f"Clinical reliability validation passed: {len(d.get('items',[]))} item(s).")
 return 0
if __name__=='__main__': sys.exit(main())
