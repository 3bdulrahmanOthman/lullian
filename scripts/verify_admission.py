#!/usr/bin/env python3
"""Verify either a legacy Lullian admission packet or a v0.4 state bundle."""
from __future__ import annotations
from pathlib import Path
import hashlib, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
# Single shared policy sources of truth; no local copies of the scanner baseline
# or the lifecycle transition rules may drift from these.
import scanner_policy
import lifecycle_policy

EXACT_SCANNER=scanner_policy.EXACT_SCANNER
EXACT_VERSION=scanner_policy.EXACT_VERSION


def h(path):
    x=hashlib.sha256()
    with Path(path).open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): x.update(c)
    return x.hexdigest()


def classify(report: dict, rc: int) -> str:
    risk=report.get('risk_assessment') or {}
    sev=str(risk.get('severity') or report.get('risk_severity') or 'UNKNOWN').upper()
    rec=str(risk.get('recommendation') or report.get('risk_recommendation') or '').upper()
    comp=report.get('analysis_completeness') or {}
    incomplete=comp.get('is_complete') is False or report.get('execution_successful') is False or bool(comp.get('entirely_uninspected_files')) or bool(comp.get('partially_inspected_files'))
    issues=report.get('issues') or report.get('findings') or []
    if incomplete or rc!=0: return 'BLOCKED_SECURITY_UNVERIFIED'
    if sev in {'CRITICAL','HIGH'} or rec=='DO_NOT_INSTALL': return 'BLOCKED_SECURITY'
    if sev=='MEDIUM' or rec=='CAUTION' or issues: return 'CAUTION_HUMAN_REVIEW'
    if sev=='LOW' and rec=='SAFE': return 'PENDING_USER_APPROVAL'
    return 'BLOCKED_SECURITY_UNVERIFIED'


def verify_state_bundle(packet: Path, tool_name: str|None) -> int:
    cmd=[sys.executable, str(ROOT/'scripts/validate_project_state.py'), str(packet)]
    state=subprocess.run(cmd,capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
    print(state.stdout.strip())
    if state.returncode:
        if state.stderr.strip(): print(state.stderr.strip())
        return state.returncode
    admission=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_admission.py'),str(packet)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
    print(admission.stdout.strip())
    if admission.returncode:
        if admission.stderr.strip(): print(admission.stderr.strip())
        return admission.returncode
    try: d=json.loads(packet.read_text(encoding='utf8'))
    except Exception as e: print('FAIL: invalid state bundle JSON',e); return 1
    tools={x.get('name'):x for x in d.get('tools',[]) if isinstance(x,dict)}
    selected=[tool_name] if tool_name else sorted(tools)
    missing=[x for x in selected if x not in tools]
    if missing: print('FAIL: unknown tool(s):',', '.join(missing)); return 1
    # Shared lifecycle transition policy, applied in-process (same module as the
    # lifecycle and project-state validators): terminal states such as REMOVED and
    # QUARANTINED are never resurrectable through any admission path.
    events_by_subject={}
    for e in d.get('toolLifecycleEvents',[]):
        if isinstance(e,dict) and e.get('subjectKind')=='TOOL':
            events_by_subject.setdefault(e.get('subjectRef'),[]).append(e)
    for name in selected:
        chain=events_by_subject.get(name,[])
        chain_errs=lifecycle_policy.chain_errors(chain)
        if chain_errs:
            print(f'FAIL: tool {name}: lifecycle event chain violates shared transition policy')
            for ce in chain_errs: print(' -',ce)
            return 1
    for name in selected:
        t=tools[name]
        print(json.dumps({'tool':name,'effectiveStatus':t.get('effectiveStatus'),'reviewDisposition':t.get('reviewDisposition'),'admissionPlanRef':t.get('admissionPlanRef'),'scopeRef':t.get('scopeRef'),'installationVerificationRef':t.get('installationVerificationRef')},indent=2))
    return 0


def verify_legacy_packet(packet: Path) -> int:
    edir=packet.parent/packet.read_text(encoding='utf8') and packet.parent/json.loads(packet.read_text(encoding='utf8')).get('evidenceDir','')
    d=json.loads(packet.read_text(encoding='utf8'))
    if not edir.is_dir(): print('FAIL: evidence directory missing'); return 1
    required=['raw-skillspector-report.json','scanner-trust.json','snapshot-manifest.json','snapshot.tar','scan-evidence.json']
    for n in required:
        if not (edir/n).is_file(): print('FAIL: evidence missing',n); return 1
    try:
        raw=edir/'raw-skillspector-report.json'; trust=edir/'scanner-trust.json'; snap=edir/'snapshot-manifest.json'; archive=edir/'snapshot.tar'; ev=edir/'scan-evidence.json'
        td=json.loads(trust.read_text(encoding='utf8')); sd=json.loads(snap.read_text(encoding='utf8')); ed=json.loads(ev.read_text(encoding='utf8'))
        report=json.loads(raw.read_text(encoding='utf8'))
    except Exception as e: print('FAIL: malformed evidence artifact',e); return 1
    if td.get('scanner')!=EXACT_SCANNER or td.get('publisher')!='NVIDIA' or td.get('version')!=EXACT_VERSION or td.get('binaryPathPolicy')!='PINNED_FILE' or td.get('trustStatus')!='TRUSTED' or not td.get('verificationEvidenceRefs'): print('FAIL: scanner trust record invalid'); return 1
    trust_hash=h(trust)
    if trust_hash!=d.get('scannerTrustHash') or trust_hash!=ed.get('scannerTrustHash') or trust_hash!=sd.get('scannerTrustHash'): print('FAIL: scanner trust hash mismatch'); return 1
    raw_hash=h(raw)
    if raw_hash!=ed.get('reportHash') or raw_hash!=d.get('rawReportHash'): print('FAIL: raw report hash mismatch'); return 1
    archive_hash=h(archive)
    if archive_hash!=sd.get('snapshotArchiveHash') or archive_hash!=d.get('snapshotArchiveHash') or archive_hash!=ed.get('snapshotArchiveHash'): print('FAIL: snapshot archive hash mismatch'); return 1
    if sd.get('contentHash')!=d.get('snapshotHash') or sd.get('contentHash')!=ed.get('targetHash'): print('FAIL: snapshot content hash mismatch'); return 1
    if h(ev)!=d.get('scanEvidenceHash'): print('FAIL: scan evidence hash mismatch'); return 1
    if h(snap)!=d.get('snapshotManifestHash'): print('FAIL: snapshot manifest hash mismatch'); return 1
    if ed.get('snapshotArchiveRef')!='snapshot.tar' or ed.get('snapshotRef')!='snapshot-manifest.json': print('FAIL: scan evidence snapshot binding invalid'); return 1
    expected=classify(report,int(ed.get('scannerExitCode',999)))
    if d.get('verdict')!=expected: print(f'FAIL: verdict tampered/inconsistent: packet={d.get("verdict")}, evidence={expected}'); return 1
    if expected=='PENDING_USER_APPROVAL' and ed.get('status')!='PASS': print('FAIL: PASS verdict has inconsistent scan status'); return 1
    if expected in {'CAUTION_HUMAN_REVIEW','BLOCKED_SECURITY'} and ed.get('status')!='FINDINGS': print('FAIL: finding verdict has inconsistent scan status'); return 1
    if expected=='BLOCKED_SECURITY_UNVERIFIED' and ed.get('status') not in {'INCOMPLETE','ERROR'}: print('FAIL: unverified verdict has inconsistent scan status'); return 1
    if ed.get('mode')!='STATIC_NO_LLM' or not ed.get('analysisComplete',False) and expected!='BLOCKED_SECURITY_UNVERIFIED': print('FAIL: scan mode/completeness inconsistent'); return 1
    expected_comp='COMPLETE' if expected!='BLOCKED_SECURITY_UNVERIFIED' and ed.get('analysisComplete') else ('PARTIAL' if ed.get('status')=='INCOMPLETE' else 'UNRESOLVED')
    if ed.get('analysisCompleteness') and ed.get('analysisCompleteness')!=expected_comp: print('FAIL: analysisCompleteness inconsistent with packet status'); return 1
    print('PASS: legacy admission packet evidence, trust chain, archive/hash bindings, and verdict agree'); return 0


def main():
    if len(sys.argv) not in {2,3}:
        print('usage: verify_admission.py STATE-BUNDLE.json [TOOL_NAME] | PACKET.json'); return 2
    packet=Path(sys.argv[1]).resolve()
    if not packet.is_file(): print('FAIL: packet missing'); return 1
    try: d=json.loads(packet.read_text(encoding='utf8'))
    except Exception as e: print('FAIL: invalid JSON',e); return 1
    if 'projectState' in d:
        return verify_state_bundle(packet, sys.argv[2] if len(sys.argv)==3 else None)
    if len(sys.argv)==3:
        print('FAIL: TOOL_NAME is only valid for a v0.4 state bundle'); return 2
    return verify_legacy_packet(packet)

if __name__=='__main__': sys.exit(main())
