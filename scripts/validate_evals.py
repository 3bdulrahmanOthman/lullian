#!/usr/bin/env python3
from pathlib import Path
import json,sys,re
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
errs=[]
eval_schema=json.loads((ROOT/'assets/schema-eval-case.json').read_text()); meta_schema=json.loads((ROOT/'assets/schema-metamorphic-case.json').read_text())
arr=json.loads((ROOT/'evals/evals.json').read_text()); ids=set()
for x in arr:
    if x.get('id') in ids: errs.append(f'duplicate eval id {x.get("id")}')
    ids.add(x.get('id'))
    try: Draft202012Validator(eval_schema,format_checker=FormatChecker()).validate(x)
    except Exception as e: errs.append(f'eval {x.get("id")}: {getattr(e,"message",e)}')
meta=json.loads((ROOT/'evals/metamorphic.json').read_text())
for x in meta:
    try: Draft202012Validator(meta_schema,format_checker=FormatChecker()).validate(x)
    except Exception as e: errs.append(f'metamorphic {x.get("id")}: {getattr(e,"message",e)}')
if len(meta)!=len({x.get('id') for x in meta}): errs.append('duplicate metamorphic ids')
if len(arr)!=36: errs.append(f'expected 36 native behavioral cases, found {len(arr)}')
if len(meta)!=8: errs.append(f'expected 8 native metamorphic cases, found {len(meta)}')
ids_set={x.get('id') for x in arr}
required_new=['expired-approval','revoked-approval','scope-escalation','permission-drift','dependency-vulnerability','dependency-exception-expiry','signature-mismatch','provenance-conflict','post-install-hash-mismatch','mcp-annotation-lie','mcp-oauth-risk','mcp-remote-metadata-only','mcp-capability-combination','scanner-upgrade','registry-discovery-not-trust','unsigned-release']
missing=[x for x in required_new if x not in ids_set]
if missing: errs.append('missing governance evals: '+', '.join(missing))
meta_ids={x.get('id') for x in meta}; req_meta=['change-tool-scope','change-lockfile','change-mcp-surface','change-unrelated-requirement']
if any(x not in meta_ids for x in req_meta): errs.append('missing governance metamorphic cases: '+', '.join(x for x in req_meta if x not in meta_ids))
if errs:
 print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print(f'PASS: {len(arr)} eval cases and {len(meta)} metamorphic cases validate, preserving the v0.3.2 corpus and adding the v0.4 governance corpus')
