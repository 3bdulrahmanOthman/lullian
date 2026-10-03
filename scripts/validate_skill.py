#!/usr/bin/env python3
from pathlib import Path
import re,sys
try:
    import yaml
except Exception as e:
    print('BLOCKED: PyYAML required:',e); sys.exit(2)
ROOT=Path(__file__).resolve().parents[1]; p=ROOT/'SKILL.md'; text=p.read_text(encoding='utf8'); errs=[]
if not text.startswith('---\n'): errs.append('missing frontmatter start')
parts=text.split('\n---\n',1)
if len(parts)!=2: errs.append('unterminated frontmatter')
else:
    fm=yaml.safe_load(parts[0][4:])
    if not isinstance(fm,dict): errs.append('frontmatter must be mapping')
    else:
        name=fm.get('name'); desc=fm.get('description')
        if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name) or not (1<=len(name)<=64): errs.append('invalid skill name')
        if not isinstance(desc,str) or not (1<=len(desc)<=1024) or '<' in desc or '>' in desc: errs.append('invalid description')
        meta=fm.get('metadata',{})
        if meta and (not isinstance(meta,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in meta.items())): errs.append('metadata must be string mapping')
body=parts[1] if len(parts)==2 else ''
if len(text.splitlines())>500: errs.append('SKILL.md exceeds 500 lines')
for h in ['Use When','Don\'t Use When','Core Operating Model','Workflow','Rules','Examples','Edge Cases','References']:
    if f'## {h}' not in body: errs.append(f'missing section: {h}')
# Required section content must not be empty.
for h in ['Use When','Don\'t Use When','Workflow']:
    m=re.search(rf'^## {re.escape(h)}\n(.*?)(?=^## |\Z)',body,re.M|re.S)
    if not m or not m.group(1).strip(): errs.append(f'empty section: {h}')
if '\\n' in text: errs.append('literal escaped newline found')
if errs:
    print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print('PASS: SKILL.md structural and content-shape contract')
