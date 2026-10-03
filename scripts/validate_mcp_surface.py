#!/usr/bin/env python3
"""Validate MCP security-surface evidence without executing MCP servers."""
from pathlib import Path
import json,sys

def main():
 if len(sys.argv)!=2: print('usage: validate_mcp_surface.py STATE-BUNDLE.json'); return 2
 try:b=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
 except Exception as e: print('FAIL:',e); return 1
 errs=[]
 for m in b.get('mcpSurfaces',[]):
  if m.get('maturity')=='VERIFIED' and m.get('verificationStatus')!='PASS': errs.append(f"{m.get('id')}: VERIFIED requires PASS")
  if m.get('verificationStatus')=='PASS' and not m.get('evidenceRefs'): errs.append(f"{m.get('id')}: PASS without evidenceRefs")
  for tool in m.get('tools',[]):
   if tool.get('declaredReadOnly') is True and 'annotation' in tool.get('description','').lower():
    # Declaration remains metadata; deliberately do not elevate it to a security verdict.
    pass
  if m.get('maturity')=='VERIFIED' and not m.get('inspectedCapabilityHash'): errs.append(f"{m.get('id')}: VERIFIED without inspectedCapabilityHash")
 if errs: print('FAIL'); [print(' -',e) for e in errs]; return 1
 print(f"PASS: {len(b.get('mcpSurfaces',[]))} MCP surface records validated without server execution"); return 0
if __name__=='__main__': sys.exit(main())
