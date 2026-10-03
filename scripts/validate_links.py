#!/usr/bin/env python3
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
errors=[]
for m in re.finditer(r'`(references/[^`]+|scripts/[^`]+|assets/[^`]+|evals/[^`]+)`', skill):
    p=ROOT/m.group(1)
    if not p.exists(): errors.append(m.group(1))
for d in ['references','assets','evals','scripts']:
    for p in (ROOT/d).rglob('*'):
        if p.is_file() and any(part.startswith('.') for part in p.relative_to(ROOT).parts):
            errors.append(f'hidden resource path: {p.relative_to(ROOT)}')
if errors:
    print('FAIL')
    for e in errors: print(' -',e)
    sys.exit(1)
print('PASS: referenced resources and resource paths')
