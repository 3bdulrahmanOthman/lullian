#!/usr/bin/env python3
"""Adversarial v0.4 project-state/admission contract regression suite."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_project_state import validate_bundle
H = 'a' * 64
G = 'b' * 64
T = '2026-10-02T00:00:00Z'


def h(obj, exclude=()):
    payload = {k: v for k, v in obj.items() if k not in set(exclude)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


class _Result:
    def __init__(self, returncode, stdout='', stderr=''):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

def run_bundle(bundle, td, name):
    errors = validate_bundle(bundle)
    return _Result(1 if errors else 0, '\n'.join(errors), '')


def base_bundle():
    scanner = {
        'id':'st1','scanner':'NVIDIA_SKILLSPECTOR','publisher':'NVIDIA','version':'2.11.2',
        'releaseRef':'release/2.11.2','executableHash':H,'binaryPathPolicy':'PINNED_FILE',
        'verifiedBy':'test-suite','verifiedAt':T,'trustStatus':'TRUSTED','trustBasis':'PUBLISHED_RELEASE',
        'verificationEvidenceRefs':['e1']
    }
    scanner_hash = h(scanner)
    snap = {
        'id':'sn1','target':'t1','capturedAt':T,'contentHash':H,'snapshotArchiveHash':G,
        'snapshotArchiveRef':'snapshot.tar','scannerTrustHash':scanner_hash,'sourceRef':'p1',
        'changePolicy':'RESCAN_ON_MATERIAL_CHANGE','subjectIdentityHash':H,'snapshotSchemaVersion':'2'
    }
    scope = {
        'id':'scope1','toolRef':'t1','allowedCapabilities':['x'],'deniedCapabilities':[],
        'approvalRequired':True,'policyRevision':'v0.4.0','createdAt':T,'canonicalHash':''
    }
    scope['canonicalHash'] = h(scope, {'canonicalHash'})
    dep = {
        'id':'dep1','targetRef':'t1','ecosystem':'python','analysisCompleteness':'COMPLETE',
        'scanner':'OSV-Scanner','scannerVersion':'2.0','resolvedDependencies':[{'name':'demo','version':'1.0'}],
        'scannedAt':T,'resolutionSource':'lockfile','evidenceRefs':['e1']
    }
    mcp = {
        'id':'mcp1','targetRef':'t1','protocolRevision':'2026-07-28','transport':'STDIO',
        'serverIdentity':'example/mcp@v1','authorizationModel':'HOST_MANAGED','maturity':'VERIFIED',
        'verificationBasis':'STATIC','declaredAnnotationsHash':G,'inspectedCapabilityHash':H,
        'verificationStatus':'PASS','evidenceRefs':['e1']
    }
    interaction = {
        'id':'cap1','capabilityRefs':['cap:x','cap:y'],'riskFactors':['network-output','private-data-read'],
        'interactionRuleRef':'rule1','riskLevel':'LOW','policyDecision':'ALLOW','evidenceRefs':['e1']
    }
    plan = {
        'id':'plan1','toolRef':'t1','provenanceRef':'p1','snapshotRef':'sn1','artifactHash':H,
        'revision':'v1','scopeRef':'scope1','scopeHash':scope['canonicalHash'],'securityReviewRef':'sr1',
        'dependencyAuditRef':'dep1','mcpSurfaceRef':'mcp1','capabilityInteractionRef':'cap1',
        'policyRevision':'v0.4.0','installationMethod':'EXTERNAL_EXECUTOR',
        'verificationRequirements':['HASH_COMPARE','MANIFEST_COMPARE'],
        'reapprovalTriggers':['SCOPE_CHANGED','DEPENDENCY_CHANGED','MCP_SURFACE_CHANGED'],
        'createdAt':T,'requiredEvidenceRefs':['e1'],'rollbackCondition':'Mismatch => quarantine','planHash':''
    }
    plan['planHash'] = h(plan, {'planHash'})
    approval = {
        'id':'ap1','artifactId':'sr1','owner':'owner','status':'APPROVED','approver':'owner','approvedAt':T,
        'scope':'scope1','scopeRef':'scope1','scopeHash':scope['canonicalHash'],'admissionPlanRef':'plan1',
        'admissionPlanHash':plan['planHash'],'artifactHash':H,'policyRevision':'v0.4.0',
        'expiresAt':'2026-12-31T00:00:00Z','reapprovalTriggers':['SCOPE_CHANGED'],'reviewDisposition':'NONE'
    }
    evidence = {'id':'e1','claim':'test evidence','class':'USER_FACT','status':'CONFIRMED','confidence':'HIGH'}
    prov = {'id':'p1','kind':'MCP','canonicalUrl':'https://example.com/mcp','owner':'Example','versionOrRevision':'v1',
            'retrievedAt':T,'contentHash':H,'provenanceStrength':'CANONICAL_TAG','subjectType':'MCP_SERVER','artifactDigest':H}
    scan = {'id':'se1','target':'t1','scannerTrustRef':'st1','targetHash':H,'scannerTrustHash':scanner_hash,
            'reportHash':G,'reportRef':'raw.json','snapshotRef':'sn1','mode':'STATIC_NO_LLM','status':'PASS',
            'analysisComplete':True,'scannedAt':T,'analysisCompleteness':'COMPLETE','analysisMode':'STATIC_NO_LLM',
            'scannerExitCode':0,'severity':'LOW','evidenceRefs':['e1']}
    review = {'id':'sr1','target':'t1','provenanceRef':'p1','scannerTrustRef':'st1','snapshotRef':'sn1','scanEvidenceRef':'se1',
              'approvalRef':'ap1','scan':{'scanner':'NVIDIA_SKILLSPECTOR','version':'2.11.2','mode':'STATIC_NO_LLM',
              'status':'PASS','analysisComplete':True,'reportHash':G,'severity':'LOW','exitCode':0},
              'verdict':'APPROVED','approvedBy':'owner','approvedAt':T,'scopeRef':'scope1',
              'scopeHash':scope['canonicalHash'],'subjectHash':H,'policyRevision':'v0.4.0','evidenceRefs':['e1'],'findings':[]}
    inst = {'id':'i1','toolRef':'t1','provenanceRef':'p1','securityReviewRef':'sr1','snapshotRef':'sn1','approvalRef':'ap1',
            'admissionPlanRef':'plan1','installedAt':T,'installedContentHash':H,'expectedArtifactHash':H,'expectedRevision':'v1',
            'observedRevision':'v1','location':'/reviewed/t1','status':'INSTALLED'}
    ver = {'id':'iv1','installationRef':'i1','admissionPlanRef':'plan1','expectedArtifactHash':H,'observedArtifactHash':H,
           'expectedRevision':'v1','observedRevision':'v1','verificationMethod':'HASH_COMPARE','verifier':'test-suite',
           'verifiedAt':T,'result':'PASS','evidenceRefs':['e1']}
    tool = {'name':'t1','type':'MCP','capability':'x','status':'AVAILABLE','effectiveStatus':'AVAILABLE',
            'activationCondition':'on demand','provenanceRef':'p1','securityReviewRef':'sr1','trustLevel':'APPROVED',
            'snapshotRef':'sn1','installationRef':'i1','scopeRef':'scope1','admissionPlanRef':'plan1',
            'installationVerificationRef':'iv1','dependencyAuditRef':'dep1','mcpSurfaceRef':'mcp1','capabilityInteractionRef':'cap1',
            'reviewDisposition':'NONE','blockedReasons':[],'lifecycleEventRefs':[]}
    state = {'schemaVersion':'2','project':{'id':'proj','name':'Test','mode':'greenfield'},'requirements':[],'unknowns':[],
             'questions':[],'evidence':['e1'],'decisions':[],'architecture':[],'technologyDecisions':[],'workflow':[],
             'tools':['t1'],'documents':[],'traceLinks':[],'concerns':[],'blockers':[],'spikes':[],'assumptions':[],
             'staleRecords':[],'qualityAttributes':[],'artifactDependencies':[],'approvals':['ap1'],'toolSnapshots':['sn1'],
             'toolScopes':['scope1'],'admissionPlans':['plan1'],'installationVerifications':['iv1'],'dependencyAudits':['dep1'],
             'mcpSurfaces':['mcp1'],'capabilityInteractions':['cap1'],'toolLifecycleEvents':[],'governanceRevision':'v0.4.0',
             'readiness':'READY','readinessSummary':{'blockingUnknowns':[],'unresolvedMustRequirements':[],'unapprovedTools':[],
             'staleRecords':[],'missingCanonicalDocs':[],'pendingApprovals':[],'blockingSpikes':[]}}
    return {'projectState':state,'evidence':[evidence],'provenance':[prov],'scannerTrust':[scanner], 'toolSnapshots':[snap],
            'scanEvidence':[scan],'securityReviews':[review],'approvals':[approval],'toolScopes':[scope],'admissionPlans':[plan],
            'dependencyAudits':[dep],'mcpSurfaces':[mcp],'capabilityInteractions':[interaction],'installations':[inst],
            'installationVerifications':[ver],'tools':[tool],'toolLifecycleEvents':[]}


def legacy_bundle_for_migration():
    b=base_bundle(); b['projectState']['schemaVersion']='1'
    for k in ['toolScopes','admissionPlans','installationVerifications','dependencyAudits','mcpSurfaces','capabilityInteractions','toolLifecycleEvents']:
        b.pop(k,None); b['projectState'].pop(k,None)
    for k in ['effectiveStatus','scopeRef','admissionPlanRef','installationVerificationRef','dependencyAuditRef','mcpSurfaceRef','capabilityInteractionRef','reviewDisposition','blockedReasons','lifecycleEventRefs']:
        b['tools'][0].pop(k,None)
    for k in ['scopeRef','scopeHash','subjectHash','policyRevision']:
        b['securityReviews'][0].pop(k,None)
    for k in ['scopeRef','scopeHash','admissionPlanRef','admissionPlanHash','artifactHash','policyRevision']:
        b['approvals'][0].pop(k,None)
    for k in ['admissionPlanRef','expectedArtifactHash','expectedRevision','verificationRef']:
        b['installations'][0].pop(k,None)
    b['toolSnapshots'][0].pop('subjectIdentityHash',None)
    for k in ['analysisCompleteness','analysisMode']:
        b['scanEvidence'][0].pop(k,None)
    return b

def _add_event(b, previous_state, new_state):
    """Regression helper (F-01): a fully well-formed but illegal lifecycle event."""
    ev={'id':'evx','subjectRef':'t1','subjectKind':'TOOL','eventType':'VERIFICATION_PASSED',
        'sequence':1,'previousState':previous_state,'newState':new_state,'cause':'forged',
        'actor':'attacker','source':'manual','occurredAt':T,'causeRefs':['e1'],'evidenceRefs':['e1']}
    b['toolLifecycleEvents'].append(ev); b['projectState']['toolLifecycleEvents'].append('evx')

def _rebind_scanner(b, changes):
    """Regression helper (F-02): scanner trust record mutated and all hash bindings reborn,
    so only the exact-scanner policy itself can catch the upgrade."""
    b['scannerTrust'][0].update(changes)
    nh=h(b['scannerTrust'][0])
    b['scanEvidence'][0]['scannerTrustHash']=nh
    b['toolSnapshots'][0]['scannerTrustHash']=nh

def main():
    with tempfile.TemporaryDirectory(prefix='lullian-state-test-') as td0:
        td=Path(td0); valid=base_bundle()
        checks=[
            ('valid-complete-admission', lambda b: None),
            ('orphan-reference', lambda b: b['projectState'].__setitem__('tools',['missing'])),
            ('approval-plan-hash', lambda b: b['approvals'][0].__setitem__('admissionPlanHash',G)),
            ('approval-scope-hash', lambda b: b['approvals'][0].__setitem__('scopeHash',G)),
            ('scope-canonical-hash', lambda b: b['toolScopes'][0].__setitem__('canonicalHash',G)),
            ('plan-hash', lambda b: b['admissionPlans'][0].__setitem__('planHash',G)),
            ('plan-scope-hash', lambda b: b['admissionPlans'][0].__setitem__('scopeHash',G)),
            ('verification-hash', lambda b: b['installationVerifications'][0].__setitem__('observedArtifactHash',G)),
            ('verification-revision', lambda b: b['installationVerifications'][0].__setitem__('observedRevision','v2')),
            ('snapshot-target', lambda b: b['toolSnapshots'][0].__setitem__('target','other')),
            ('scan-target', lambda b: b['scanEvidence'][0].__setitem__('targetHash',G)),
            ('security-review-scope', lambda b: b['securityReviews'][0].__setitem__('scopeHash',G)),
            ('tool-effective-state', lambda b: b['tools'][0].__setitem__('effectiveStatus','PENDING_REVIEW')),
            ('install-pending-approval-allowed-but-not-available', lambda b: (b['approvals'][0].update({'status':'PENDING','reviewDisposition':'REQUIRES_REVIEW'}), b['securityReviews'][0].update({'verdict':'PENDING_USER_APPROVAL'}), b['tools'][0].update({'status':'PENDING_REVIEW','effectiveStatus':'PENDING_REVIEW','reviewDisposition':'REQUIRES_REVIEW','blockedReasons':['MIGRATION_REVIEW_REQUIRED']}), b['projectState']['readinessSummary'].update({'unapprovedTools':['t1'],'pendingApprovals':['ap1']}), b['projectState'].update({'readiness':'NOT_READY'}))),
            # R2 regressions: terminal states are not resurrectable through forged events (F-01).
            ('forged-removed-to-available-event', lambda b: _add_event(b, 'REMOVED', 'AVAILABLE')),
            ('forged-quarantined-to-available-event', lambda b: _add_event(b, 'QUARANTINED', 'AVAILABLE')),
            # R2 regressions: exact trusted-scanner policy on the state-bundle path (F-02).
            ('scanner-upgrade-trusted-record', lambda b: _rebind_scanner(b, {'version': '2.12.0'})),
            ('scanner-arbitrary-trusted-version', lambda b: _rebind_scanner(b, {'version': '9.9.9', 'publisher': 'Someone Else'})),
            ('scanner-trust-hash-mismatch', lambda b: b['scanEvidence'][0].__setitem__('scannerTrustHash', G)),
            # R2 regression: malformed lifecycle event produces a finding, never a crash (F-03).
            ('malformed-event-missing-subject', lambda b: b['toolLifecycleEvents'].append({'id': 'ev9', 'sequence': 1, 'previousState': 'REMOVED', 'newState': 'AVAILABLE', 'actor': 'a', 'source': 's', 'occurredAt': T})),
            # R2 regression: declared-vs-effective conflict detected for every relevant state (F-04).
            ('declared-quarantined-effective-available', lambda b: b['tools'][0].__setitem__('status', 'QUARANTINED')),
            ('declared-removed-effective-available', lambda b: b['tools'][0].__setitem__('status', 'REMOVED')),
            ('declared-stale-effective-available', lambda b: b['tools'][0].__setitem__('status', 'STALE')),
            ('declared-blocked-effective-available', lambda b: b['tools'][0].__setitem__('status', 'BLOCKED')),
            # R3 regressions: a security review's embedded scan record must describe the exact
            # same scan evidence (reportHash) and the exact pinned scanner version (F-02 family).
            ('review-scan-reporthash-mismatch', lambda b: b['securityReviews'][0]['scan'].__setitem__('reportHash', 'c' * 64)),
            ('review-scan-version-mismatch', lambda b: b['securityReviews'][0]['scan'].__setitem__('version', '2.12.0')),
        ]
        for name,mut in checks:
            bad=copy.deepcopy(valid); mut(bad); r=run_bundle(bad,td,name)
            should_pass = name.startswith('valid-') or name.startswith('install-pending-')
            if should_pass and r.returncode != 0:
                print('FAIL expected PASS:',name); print(r.stdout,r.stderr); return 1
            if not should_pass and r.returncode == 0:
                print('FAIL mutation accepted:',name); return 1
        (td/'valid-governance.json').write_text(json.dumps(valid),encoding='utf8')
        # Directly exercise every new governance validator against the valid graph.
        for script in ['validate_tool_admission.py','validate_dependency_audit.py','validate_mcp_surface.py']:
            r=subprocess.run([sys.executable,str(ROOT/'scripts'/script),str(td/'valid-governance.json')],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
            if r.returncode:
                print('FAIL direct validator:',script); print(r.stdout,r.stderr); return 1
        # Lifecycle validator gets a concrete one-step event fixture.
        lifecycle=copy.deepcopy(valid)
        lifecycle['projectState']['readiness']='NOT_READY'
        lifecycle['projectState']['readinessSummary']['unapprovedTools']=[]
        lifecycle['tools'][0]['effectiveStatus']='STALE'; lifecycle['tools'][0]['status']='STALE'
        lifecycle['toolLifecycleEvents']=[{'id':'ev1','subjectRef':'t1','subjectKind':'TOOL','eventType':'DRIFT_DETECTED','previousState':'AVAILABLE','newState':'STALE','source':'validator','actor':'system','occurredAt':T,'causeRefs':['scope1'],'evidenceRefs':['e1'],'sequence':1}]
        lp=td/'lifecycle.json'; lp.write_text(json.dumps(lifecycle),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_lifecycle.py'),str(lp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode:
            print('FAIL direct validator: validate_tool_lifecycle.py'); print(r.stdout,r.stderr); return 1
        lifecycle_bad=copy.deepcopy(lifecycle)
        lifecycle_bad['toolLifecycleEvents'][0]['previousState']='PENDING_REVIEW'
        lbp=td/'lifecycle-bad.json'; lbp.write_text(json.dumps(lifecycle_bad),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_lifecycle.py'),str(lbp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0:
            print('FAIL lifecycle validator accepted broken previousState'); return 1
        # R2 regression (F-03): a malformed event with a missing subject must produce a normal
        # validation finding — never an unhandled crash/traceback — in the lifecycle validator.
        malformed=copy.deepcopy(valid)
        malformed['toolLifecycleEvents']=[{'id':'ev9','sequence':1,'previousState':'REMOVED','newState':'AVAILABLE','actor':'a','source':'s','occurredAt':T}]
        mlp=td/'lifecycle-malformed.json'; mlp.write_text(json.dumps(malformed),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_lifecycle.py'),str(mlp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0 or 'Traceback' in r.stderr or 'KeyError' in r.stderr:
            print('FAIL lifecycle validator crashed or accepted malformed event'); print(r.stdout,r.stderr); return 1
        # R2 regression (F-01): the forged REMOVED->AVAILABLE event must also be rejected by
        # verify_admission.py (shared transition policy, in-process) — the designated
        # admission-verification entry point.
        forged=copy.deepcopy(valid); _add_event(forged,'REMOVED','AVAILABLE')
        fgp=td/'forged-admission.json'; fgp.write_text(json.dumps(forged),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/verify_admission.py'),str(fgp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60)
        if r.returncode==0:
            print('FAIL verify_admission accepted forged REMOVED->AVAILABLE event'); print(r.stdout,r.stderr); return 1
        # R2 regression (F-02): a scanner-upgraded trust record with rebound hashes must be
        # rejected by the admission validator through the shared scanner_policy module.
        scan_bad=copy.deepcopy(valid); _rebind_scanner(scan_bad, {'version': '2.12.0'})
        sbp=td/'scanner-bad.json'; sbp.write_text(json.dumps(scan_bad),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_admission.py'),str(sbp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0:
            print('FAIL admission validator accepted scanner 2.12.0 trusted record'); print(r.stdout,r.stderr); return 1
        # Dependency and MCP validators get explicit negative probes too.
        dep_bad=copy.deepcopy(valid); dep_bad['dependencyAudits'][0]['analysisCompleteness']='PARTIAL'; dp=td/'dep-bad.json'; dp.write_text(json.dumps(dep_bad),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_dependency_audit.py'),str(dp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0:
            print('FAIL dependency validator accepted incomplete evidence for an available tool'); return 1
        mcp_bad=copy.deepcopy(valid); mcp_bad['mcpSurfaces'][0].pop('evidenceRefs'); mp=td/'mcp-bad.json'; mp.write_text(json.dumps(mcp_bad),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_mcp_surface.py'),str(mp)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0:
            print('FAIL MCP validator accepted VERIFIED surface without evidence'); return 1
        admission_bad=copy.deepcopy(valid); admission_bad['installationVerifications'][0]['observedArtifactHash']=G; ap=td/'admission-bad.json'; ap.write_text(json.dumps(admission_bad),encoding='utf8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_tool_admission.py'),str(ap)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
        if r.returncode==0:
            print('FAIL admission validator accepted mismatched installed artifact'); return 1
        # Migration must produce a schema-valid v0.4 graph while never preserving trust implicitly.
        legacy=legacy_bundle_for_migration(); legacy_path=td/'legacy.json'; migrated_path=td/'migrated.json'
        legacy_path.write_text(json.dumps(legacy),encoding='utf8')
        import importlib.util
        spec=importlib.util.spec_from_file_location('lullian_migration', ROOT/'scripts/migrate_project_state_v032.py')
        migration=importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
        migrated=migration.migrate(legacy_path)
        migrated_path.write_text(json.dumps(migrated),encoding='utf8')
        if migrated['projectState']['schemaVersion']!='2' or migrated['tools'][0].get('effectiveStatus')!='PENDING_REVIEW' or migrated['approvals'][0].get('status')!='PENDING':
            print('FAIL migration trust downgrade semantics'); return 1
        # The full migrated graph is validated separately by the release runner.
        # Keep this contract suite focused on deterministic migration semantics to avoid
        # importing another argparse/validator module into the same Python process.
        if migrated['securityReviews'][0].get('verdict') != 'PENDING_USER_APPROVAL':
            print('FAIL migration did not downgrade legacy security approval'); return 1
        if migrated['toolSnapshots'][0].get('subjectIdentityHash') != H:
            print('FAIL migration did not backfill subjectIdentityHash deterministically'); return 1
        if migrated['scanEvidence'][0].get('analysisCompleteness') != 'COMPLETE':
            print('FAIL migration did not preserve legacy analysis completeness'); return 1
    print('PASS: v0.4 project-state/admission regression suite')
    return 0

if __name__=='__main__': sys.exit(main())
