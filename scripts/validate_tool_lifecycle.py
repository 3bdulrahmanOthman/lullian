#!/usr/bin/env python3
"""Validate tool lifecycle transitions, event causality, sequence, and terminal semantics.

Transition rules come from the shared lifecycle_policy module, which is the same
implementation used by validate_project_state.py and verify_admission.py.
"""
from pathlib import Path
import json,sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lifecycle_policy as lp

def main():
 if len(sys.argv)!=2: print('usage: validate_tool_lifecycle.py STATE-BUNDLE.json'); return 2
 try:b=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
 except Exception as e: print('FAIL:',e); return 1
 errs=[]; tools={x.get('name'):x for x in b.get('tools',[]) if isinstance(x,dict)}; events=[x for x in b.get('toolLifecycleEvents',[]) if isinstance(x,dict)]
 groups={}
 for e in events:
  if e.get('subjectKind')!='TOOL': errs.append(f"event {e.get('id')}: subjectKind must be TOOL")
  if e.get('subjectRef') not in tools: errs.append(f"event {e.get('id')}: unknown tool subject {e.get('subjectRef')}")
  errs.extend(lp.event_errors(e))
  groups.setdefault(e.get('subjectRef'),[]).append(e)
 for name,arr in groups.items():
  errs.extend(lp.chain_errors(arr))
  tool=tools.get(name)
  if tool is None: continue
  latest=lp.derived_state_from_events(arr)
  if latest and tool.get('effectiveStatus') not in {latest,'AVAILABLE'}: errs.append(f'tool {name}: effectiveStatus disagrees with latest lifecycle event')
  if latest is None and arr: errs.append(f'tool {name}: lifecycle event chain invalid; effective status cannot be derived')
 if errs: print('FAIL'); [print(' -',e) for e in errs]; return 1
 print(f'PASS: {len(events)} tool lifecycle events have valid transitions, event semantics, causality, and sequence'); return 0
if __name__=='__main__': sys.exit(main())
