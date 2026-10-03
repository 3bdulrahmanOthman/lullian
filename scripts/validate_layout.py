#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for d in ['references','assets','scripts']:
    base=ROOT/d
    for p in base.rglob('*'):
        if p.is_dir() and p!=base: errors.append(f'nested directory: {p.relative_to(ROOT)}')
# evals may contain only one level of files; no nested dirs.
base=ROOT/'evals'
for p in base.rglob('*'):
    if p.is_dir(): errors.append(f'nested eval directory: {p.relative_to(ROOT)}')
if errors:
    print('FAIL'); [print(' -',e) for e in errors]; sys.exit(1)
print('PASS: resource directories are flat and portable')
