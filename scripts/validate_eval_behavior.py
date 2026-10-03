#!/usr/bin/env python3
"""Deterministic grader for the executable portion of a Lullian eval case.
Input: CASE.json OUTPUT.txt. Natural-language rubric strings remain for manual review.
"""
from pathlib import Path
import json,re,sys

def grade_case(case, out):
    low=out.lower(); errs=[]
    for a in case.get('executableAssertions',[]):
        typ=a['type']; val=a['value']; flags=a.get('flags','')
        if typ=='MUST_CONTAIN' and str(val).lower() not in low: errs.append(f'MUST_CONTAIN failed: {val}')
        elif typ=='MUST_NOT_CONTAIN' and str(val).lower() in low: errs.append(f'MUST_NOT_CONTAIN failed: {val}')
        elif typ=='MUST_MATCH' and not re.search(str(val),out,re.I if 'i' in flags else 0): errs.append(f'MUST_MATCH failed: {val}')
        elif typ=='MUST_NOT_MATCH' and re.search(str(val),out,re.I if 'i' in flags else 0): errs.append(f'MUST_NOT_MATCH failed: {val}')
        elif typ=='MAX_QUESTIONS':
            marker=re.findall(r'(?im)^\s*(?:\d+[.)]|[-*])\s+.*\?\s*$',out)
            if len(marker)>int(val): errs.append(f'MAX_QUESTIONS failed: {len(marker)}>{val}')
    return errs

def main():
    if len(sys.argv)!=3: print('usage: validate_eval_behavior.py CASE.json OUTPUT.txt'); return 2
    try:
        case=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
        out=Path(sys.argv[2]).read_text(encoding='utf8')
    except Exception as e:
        print('FAIL\n - invalid eval input:',e); return 1
    errs=grade_case(case,out)
    if errs:
        print('FAIL'); [print(' -',e) for e in errs]; return 1
    print('PASS: executable eval assertions'); return 0
if __name__=='__main__': sys.exit(main())
