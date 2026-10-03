#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,sys
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
def main():
    if len(sys.argv)!=3: print('usage: check_research_budget.py PLAN.json USAGE.json'); return 2
    plan=json.loads(Path(sys.argv[1]).read_text()); usage=json.loads(Path(sys.argv[2]).read_text())
    schema=json.loads((ROOT/'assets/schema-research-plan.json').read_text()); Draft202012Validator(schema).validate(plan)
    usage_schema=json.loads((ROOT/'assets/schema-research-usage.json').read_text()); Draft202012Validator(usage_schema).validate(usage)
    budget=plan['budget']; ok=(usage.get('planRef')==plan['id'] and usage.get('queriesUsed',-1)<=budget['maxQueries'] and usage.get('sourcesUsed',-1)<=budget['maxSources'] and usage.get('elapsedSeconds',float('inf'))<=budget['maxMinutes']*60)
    if usage.get('withinBudget') is not ok: print('FAIL: withinBudget flag does not match calculated budget usage'); return 1
    if not ok: print('FAIL: research budget exceeded or planRef mismatch'); return 1
    if plan.get('status')=='COMPLETE' and usage.get('egressApproved') is False and plan.get('depth')=='DEEP':
        # Deep research may be local-only; this is informational rather than a block.
        print('PASS: budget within limits (remote egress remains governed separately)'); return 0
    print('PASS: research usage is within declared budget'); return 0
if __name__=='__main__': sys.exit(main())
