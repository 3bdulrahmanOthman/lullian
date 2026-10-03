from pathlib import Path
import sys,re
try: import yaml
except Exception as e: print('BLOCKED: PyYAML required:',e); sys.exit(2)
ROOT=Path(__file__).resolve().parents[1]; text=(ROOT/'SKILL.md').read_text(encoding='utf8'); parts=text.split('\n---\n',1)
if len(parts)!=2 or not parts[0].startswith('---\n'): print('FAIL: invalid frontmatter delimiters'); sys.exit(1)
try: fm=yaml.safe_load(parts[0][4:])
except Exception as e: print('FAIL: frontmatter YAML parse:',e); sys.exit(1)
if not isinstance(fm,dict): print('FAIL: mapping required'); sys.exit(1)
allowed={'name','description','license','compatibility','metadata','allowed-tools'}; unknown=set(fm)-allowed
errs=[]
if unknown: errs.append('unsupported keys: '+','.join(sorted(unknown)))
if fm.get('name')!='lullian' or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',fm.get('name','')): errs.append('invalid name')
d=fm.get('description');
if not isinstance(d,str) or not 1<=len(d)<=1024 or '<' in d or '>' in d: errs.append('invalid description')
meta=fm.get('metadata',{})
if meta and (not isinstance(meta,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in meta.items())): errs.append('metadata invalid')
if errs: print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print('PASS: frontmatter YAML contract')
