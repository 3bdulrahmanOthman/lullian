#!/usr/bin/env python3
from pathlib import Path
import ast,sys,re,stat
ROOT=Path(__file__).resolve().parents[1]; errors=[]
bad_controls={0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069,0x200B,0x200C,0x200D,0xFEFF}
allowed_subprocess={'release_check.py','security_gate.py','validate_security_gate.py','verify_admission.py','validate_state_contract.py'}
for p in ROOT.rglob('*'):
 if p.is_symlink(): errors.append(f'symlink is forbidden in release: {p.relative_to(ROOT)}'); continue
 if not p.is_file(): continue
 try: text=p.read_text(encoding='utf8')
 except UnicodeDecodeError: continue
 if any(ord(ch) in bad_controls for ch in text): errors.append(f'{p.relative_to(ROOT)}: hidden/bidi control chars')
for p in (ROOT/'scripts').glob('*.py'):
 try: tree=ast.parse(p.read_text(encoding='utf8'),filename=str(p))
 except SyntaxError as e: errors.append(f'{p.name}: syntax error: {e}'); continue
 imports={n.names[0].name for n in tree.body if isinstance(n,ast.Import) and n.names}
 if 'requests' in imports or 'httpx' in imports or 'socket' in imports: errors.append(f'{p.name}: outbound/network library import forbidden')
 for node in ast.walk(tree):
  if isinstance(node,ast.Call):
   fn=node.func
   if isinstance(fn,ast.Name) and fn.id in {'eval','exec','compile'}: errors.append(f'{p.name}: dynamic execution {fn.id}()')
   if isinstance(fn,ast.Attribute) and fn.attr=='system' and isinstance(fn.value,ast.Name) and fn.value.id=='os': errors.append(f'{p.name}: os.system forbidden')
   if isinstance(fn,ast.Attribute) and fn.attr in {'Popen','run','call','check_call','check_output'} and isinstance(fn.value,ast.Name) and fn.value.id=='subprocess':
    if p.name not in allowed_subprocess: errors.append(f'{p.name}: unexpected subprocess use')
    for kw in node.keywords:
     if kw.arg=='shell' and isinstance(kw.value,ast.Constant) and kw.value.value is True: errors.append(f'{p.name}: shell=True forbidden')
# Binary/executable surface: release scripts must be source-only.
for p in (ROOT/'scripts').glob('*'):
 if p.suffix!='.py' and p.is_file(): errors.append(f'unapproved script file: {p.name}')
for p in ROOT.rglob('*'):
 if p.is_file() and p.suffix.lower() in {'.exe','.dll','.so','.dylib','.bin'}: errors.append(f'binary payload forbidden: {p.relative_to(ROOT)}')
if errors:
 print('FAIL'); [print(' -',e) for e in errors]; sys.exit(1)
print('PASS: self-security scan')
