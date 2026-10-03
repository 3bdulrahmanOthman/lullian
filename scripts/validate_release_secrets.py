#!/usr/bin/env python3
from pathlib import Path
import re,sys
ROOT=Path(__file__).resolve().parents[1]; errs=[]
patterns=[
 ('private-key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
 ('aws-key',re.compile(r'AKIA[0-9A-Z]{16}')),
 ('github-token',re.compile(r'gh[pousr]_[A-Za-z0-9_]{20,}')),
 ('generic-secret-assignment',re.compile(r'(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*["\'][^"\']{8,}["\']')),
]
for p in ROOT.rglob('*'):
 if not p.is_file() or p.suffix.lower() not in {'.md','.json','.py','.txt'}: continue
 try: s=p.read_text(encoding='utf8')
 except UnicodeDecodeError: continue
 for name,rx in patterns:
  if rx.search(s): errs.append(f'{p.relative_to(ROOT)}: possible {name}')
if errs:
 print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print('PASS: release secret-pattern scan')
