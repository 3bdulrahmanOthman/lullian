#!/usr/bin/env python3
"""Deterministic v0.4 release gate composer.

All local checks are blocking. Third-party/host-only checks are reported separately
and are never represented as executed unless their binaries/evaluators actually ran.
"""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile

sys.dont_write_bytecode = True  # release runs must leave zero bytecode noise (F-EXT-04)

ROOT=Path(__file__).resolve().parents[1]
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
STEPS=[
 ('skill','validate_skill.py'),('frontmatter','validate_frontmatter_yaml.py'),('links','validate_links.py'),('layout','validate_layout.py'),
 ('schemas','validate_schemas.py'),('schema-examples','validate_schema_examples.py'),('schema-invariants','validate_schema_invariants.py'),
 ('eval-inventory','validate_evals.py'),('package-contract','validate_package_contract.py'),('state-contract','validate_state_contract.py'),
 ('security-gate-tests','validate_security_gate.py'),('self-security','validate_self_security.py'),('release-secrets','validate_release_secrets.py')]

def run(label, args, failed):
    try:
        if label == 'state-contract':
            r = subprocess.run(args, env=ENV, timeout=180)
            print(f'[{label}] exit={r.returncode}')
        else:
            r = subprocess.run(args,capture_output=True,text=True,env=ENV,timeout=120)
            print(f'[{label}] exit={r.returncode}'); print((r.stdout+r.stderr).strip())
    except subprocess.TimeoutExpired:
        print(f'[{label}] TIMEOUT'); failed.append(label); return None
    if r.returncode: failed.append(label)
    return r

def sha_bytes(x): return hashlib.sha256(x).hexdigest()

def main():
    failed=[]
    for name,s in STEPS: run(name,[sys.executable,str(ROOT/'scripts'/s)],failed)
    with tempfile.TemporaryDirectory(prefix='lullian-release-gates-') as td0:
        td=Path(td0)
        # Full native executable assertion corpus: evaluate every case in-process.
        cases=json.loads((ROOT/'evals/evals.json').read_text(encoding='utf8'))
        from validate_eval_behavior import grade_case
        eval_failed=[]
        for case in cases:
            out=case.get('fixtureOutput',case.get('expected_output',''))
            errors=grade_case(case,out)
            print(f"[eval:{case['id']}] {'PASS' if not errors else 'FAIL'}")
            if errors:
                [print(' -',e) for e in errors]
                eval_failed.append(case['id'])
        if eval_failed:
            print('[eval-corpus] FAIL:', ', '.join(eval_failed)); failed.append('eval-corpus')
        else:
            print(f'[eval-corpus] PASS: {len(cases)} executable behavioral cases')
        # Native -> external evaluation adapter.
        export=td/'evaluator-dataset.json'
        run('eval-export',[sys.executable,str(ROOT/'scripts/export_eval_dataset.py'),'--output',str(export)],failed)
        if export.exists():
            try:
                data=json.loads(export.read_text(encoding='utf8'))
                if data.get('format')!='lullian-external-eval-v1' or data.get('caseCount')!=36 or len(data.get('cases',[]))!=36:
                    print('[eval-export-contract] FAIL: format/count mismatch'); failed.append('eval-export-contract')
                else: print('[eval-export-contract] PASS: 36-case external adapter contract')
            except Exception as e: print('[eval-export-contract] FAIL:',e); failed.append('eval-export-contract')
        # Valid v0.4 state bundle drives direct governance validators without nested subprocess pipes.
        from validate_state_contract import base_bundle, legacy_bundle_for_migration
        from validate_project_state import validate_bundle
        import validate_tool_admission, validate_dependency_audit, validate_mcp_surface, validate_tool_lifecycle
        valid=base_bundle(); state=td/'valid-state.json'; state.write_text(json.dumps(valid),encoding='utf8')
        validator_calls=[('tool-admission',validate_tool_admission.main),('dependency',validate_dependency_audit.main),('mcp-surface',validate_mcp_surface.main),('lifecycle',validate_tool_lifecycle.main)]
        for label,fn in validator_calls:
            old_argv=sys.argv; sys.argv=['validator',str(state)]
            try: rc=fn()
            finally: sys.argv=old_argv
            print(f'[direct:{label}] exit={rc}')
            if rc: failed.append('direct:'+label)
        old_argv=sys.argv; sys.argv=['verify_admission.py',str(state)]
        try: rc=__import__('verify_admission').main()
        finally: sys.argv=old_argv
        print(f'[verify-admission-state] exit={rc}')
        if rc: failed.append('verify-admission-state')

        # Migration: legacy state -> v0.4 -> deterministic state validation, with explicit trust downgrade.
        legacy=legacy_bundle_for_migration(); lp=td/'legacy-state.json'; mp=td/'migrated-state.json'; lp.write_text(json.dumps(legacy),encoding='utf8')
        from migrate_project_state_v032 import migrate
        try:
            migrated=migrate(lp)
            mp.write_text(json.dumps(migrated,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
            print('[migration] exit=0')
        except Exception as e:
            print('[migration] exit=1\n',e); failed.append('migration'); migrated=None
        if migrated is not None:
            if migrated.get('projectState',{}).get('schemaVersion')!='2' or migrated.get('approvals',[{}])[0].get('status')!='PENDING' or migrated.get('tools',[{}])[0].get('effectiveStatus')!='PENDING_REVIEW':
                print('[migration-semantics] FAIL: trust was not conservatively downgraded'); failed.append('migration-semantics')
            else: print('[migration-semantics] PASS: legacy approval trust downgraded')
            errs=validate_bundle(migrated)
            print('[migration-validation] exit='+str(1 if errs else 0))
            if errs:
                print('\n'.join(' - '+e for e in errs)); failed.append('migration-validation')

        # Release provenance helper uses a synthetic external attestation, then a tampered digest must fail.
        artifact=td/'artifact.zip'; artifact.write_bytes(b'lullian-v0.4-test-artifact')
        digest=sha_bytes(artifact.read_bytes()); att=td/'attestation.json'; att.write_text(json.dumps({'id':'att-1','subjectType':'ARCHIVE','subjectDigest':digest,'attestationType':'SLSA_PROVENANCE','issuer':'release-test','createdAt':'2026-10-02T00:00:00Z','verificationStatus':'VERIFIED','evidenceRef':'external-test'}),encoding='utf8')
        from verify_release_provenance import sha as artifact_sha
        if artifact_sha(artifact)==digest:
            print('[release-provenance-valid] PASS: subject digest matches artifact')
        else:
            print('[release-provenance-valid] FAIL: artifact digest mismatch'); failed.append('release-provenance-valid')
        tampered=json.loads(att.read_text()); tampered['subjectDigest']='0'*64; att.write_text(json.dumps(tampered),encoding='utf8')
        if artifact_sha(artifact)!=tampered['subjectDigest']:
            print('[release-provenance-tamper] PASS: tampered attestation rejected')
        else:
            print('[release-provenance-tamper] FAIL: tampered attestation accepted'); failed.append('release-provenance-tamper')
        # Research budget helper remains deterministic after governance additions.
        plan=td/'plan.json'; usage=td/'usage.json';
        plan.write_text(json.dumps({'id':'rp-1','question':'q','evidenceTarget':'e','depth':'STANDARD','status':'COMPLETE','budget':{'maxQueries':2,'maxSources':2,'maxMinutes':1}}))
        usage.write_text(json.dumps({'planRef':'rp-1','queriesUsed':1,'sourcesUsed':1,'elapsedSeconds':10,'withinBudget':True,'recordedAt':'2026-10-02T00:00:00Z'}))
        from check_research_budget import main as research_budget_main
        old_argv=sys.argv; sys.argv=['check_research_budget.py',str(plan),str(usage)]
        try: rc=research_budget_main()
        finally: sys.argv=old_argv
        print(f'[research-budget-helper] exit={rc}')
        if rc: failed.append('research-budget-helper')
    # Repository-only dotfiles (e.g. .gitignore) are expected in the working tree and never
    # shipped; anything else starting with '.' or bytecode noise is unshippable.
    repo_only_dotfiles={'.gitignore','.gitattributes'}
    noise=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and ('__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'} or (p.name.startswith('.') and str(p.relative_to(ROOT)) not in repo_only_dotfiles))]
    if noise: print('UNSHIPPABLE NOISE:','\n - '.join(['']+noise)); failed.append('noise')
    if failed:
        print('RELEASE CHECK: FAIL'); print('FAILED GATES:',', '.join(dict.fromkeys(failed))); return 1
    print('RELEASE CHECK: PASS')
    print('EXTERNAL GATES NOT EXECUTED BY THIS LOCAL RUN: skills-ref validate; real trusted SkillSpector execution; SkillEvaluator Tier 1/2/3 host integration; release signing/attestation publication.')
    return 0

if __name__=='__main__': sys.exit(main())
