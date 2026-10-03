#!/usr/bin/env python3
"""Validate dependency audit completeness, lineage, and time-bounded exceptions."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys

def expired(v):
 try:return datetime.fromisoformat(v.replace('Z','+00:00'))<=datetime.now(timezone.utc)
 except:return True

def main():
 if len(sys.argv)!=2: print('usage: validate_dependency_audit.py STATE-BUNDLE.json'); return 2
 try:b=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
 except Exception as e: print('FAIL:',e); return 1
 errs=[]
 for d in b.get('dependencyAudits',[]):
  if d.get('analysisCompleteness') in {'PARTIAL','UNRESOLVED'} and any(p.get('effectiveStatus')=='AVAILABLE' for p in b.get('tools',[]) if p.get('dependencyAuditRef')==d.get('id')): errs.append(f"{d.get('id')}: incomplete dependency analysis cannot back an available tool")
  for ex in d.get('exceptions',[]):
   if expired(ex.get('expiresAt','')): errs.append(f"{d.get('id')}: exception {ex.get('id')} expired")
  names=[p.get('name') for p in d.get('resolvedDependencies',[])]
  if len(names)!=len(set(names)): errs.append(f"{d.get('id')}: duplicate resolved dependency names")
 if errs: print('FAIL'); [print(' -',e) for e in errs]; return 1
 print(f"PASS: {len(b.get('dependencyAudits',[]))} dependency audits satisfy completeness and exception rules"); return 0
if __name__=='__main__': sys.exit(main())
