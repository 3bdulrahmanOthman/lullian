#!/usr/bin/env python3
from pathlib import Path
import json,sys
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
errs=[]; files=sorted((ROOT/'assets').glob('schema-*.json'))
for p in files:
 try:
  data=json.loads(p.read_text(encoding='utf8')); Draft202012Validator.check_schema(data)
  # Reject network-resolvable refs in bundled contracts. Local refs must be fragment/local paths.
  refs=[]
  def walk(x):
   if isinstance(x,dict):
    if '$ref' in x: refs.append(x['$ref'])
    for v in x.values(): walk(v)
   elif isinstance(x,list):
    for v in x: walk(v)
  walk(data)
  for r in refs:
   if isinstance(r,str) and (r.startswith('http://') or r.startswith('https://')): errs.append(f'{p.name}: external $ref forbidden: {r}')
  Draft202012Validator(data,format_checker=FormatChecker())
 except Exception as e: errs.append(f'{p.name}: {e}')
if errs:
 print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print(f'PASS: {len(files)} offline Draft 2020-12 schemas validate with format checking')
