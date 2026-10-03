#!/usr/bin/env python3
"""Export Lullian native evals to a stable external evaluator dataset contract."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); ap.add_argument('--input',default=str(ROOT/'evals/evals.json')); args=ap.parse_args()
 cases=json.loads(Path(args.input).read_text(encoding='utf8'))
 out=[]
 for c in cases:
  out.append({'id':c['id'],'prompt':c['prompt'],'expected_output':c['expected_output'],'assertions':c['assertions'],'executableAssertions':c.get('executableAssertions',[]),'metadata':{'category':c.get('category','CORE'),'sandboxRequired':bool((c.get('externalExportHint') or {}).get('sandboxRequired',False)),'sourceExternalExportHint':c.get('externalExportHint',{})}})
 target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps({'format':'lullian-external-eval-v1','source':'lullian-native-evals','caseCount':len(out),'cases':out},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print(f'PASS: exported {len(out)} cases to {target}')
 return 0
if __name__=='__main__':sys.exit(main())
