#!/usr/bin/env python3
"""Deterministic v0.4 project-state and tool-admission integrity validator."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, sys
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[1]
STATE_SCHEMA=ROOT/'assets/schema-project-state.json'
sys.path.insert(0, str(ROOT/'scripts'))
import lifecycle_policy
import scanner_policy
TOOL_STATES={'CANDIDATE','PENDING_REVIEW','PENDING_INSTALLATION','PENDING_VERIFICATION','AVAILABLE','STALE','REQUIRES_REVIEW','QUARANTINED','REMOVED'}
# Declared tool status is non-authoritative; any declared state that implies
# non-availability must never coexist with a derived AVAILABLE.
DECLARED_NON_AVAILABLE_STATES=(TOOL_STATES-{'AVAILABLE'})|{'BLOCKED'}
APPROVAL_STATES={'PENDING','APPROVED','EXPIRED','REVOKED','REJECTED','SUPERSEDED'}
BLOCKED_DISPOSITIONS={'BLOCKED','CAUTION_HUMAN_REVIEW','REJECTED','REQUIRES_REVIEW'}
COLLECTIONS={'requirements':'id','unknowns':'id','questions':'id','research':'id','evidence':'id','decisions':'id','architecture':'id','technologyDecisions':'id','workflow':'id','tools':'name','documents':'id','traceLinks':'id','concerns':'id','artifactDependencies':'id','approvals':'id','toolSnapshots':'id','provenance':'id','scannerTrust':'id','scanEvidence':'id','securityReviews':'id','installations':'id','toolScopes':'id','admissionPlans':'id','installationVerifications':'id','dependencyAudits':'id','mcpSurfaces':'id','capabilityInteractions':'id','toolLifecycleEvents':'id'}

def fail(errors):
    print('FAIL')
    for e in errors: print(' -',e)
    return 1

def load(path): return json.loads(Path(path).read_text(encoding='utf8'))

def canonical_hash(obj, excluded=()):
    data={k:v for k,v in obj.items() if k not in set(excluded)} if isinstance(obj,dict) else obj
    raw=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')
    return hashlib.sha256(raw).hexdigest()

def parse_time(value):
    try: return datetime.fromisoformat(value.replace('Z','+00:00'))
    except Exception: return None

def expired(ap, now=None):
    now=now or datetime.now(timezone.utc)
    t=parse_time(ap.get('expiresAt',''))
    return bool(t and t <= now)

def derive_tool(tool, indexes, now=None):
    now=now or datetime.now(timezone.utc)
    name=tool.get('name'); reviews=indexes['reviews']; approvals=indexes['approvals']; plans=indexes['plans']; installs=indexes['installs']; verifications=indexes['verifications']
    events=[e for e in indexes['events'].values() if e.get('subjectRef')==name and e.get('subjectKind')=='TOOL']
    events.sort(key=lambda e:(e.get('sequence',0),e.get('occurredAt','')))
    if events:
        # Shared transition policy (same implementation as validate_tool_lifecycle.py and
        # verify_admission.py). An illegal or malformed chain fails closed, so terminal
        # states (REMOVED/QUARANTINED) can never be resurrected through a forged event.
        ns=lifecycle_policy.derived_state_from_events(events)
        if ns is None: return 'QUARANTINED'
        if ns in {'QUARANTINED','REMOVED'}: return ns
        if ns in {'STALE','REQUIRES_REVIEW'}: return ns
    review=reviews.get(tool.get('securityReviewRef'))
    if not review: return 'PENDING_REVIEW'
    if review.get('verdict') in {'BLOCKED_SECURITY','BLOCKED_SECURITY_UNVERIFIED','REJECTED'}: return 'CANDIDATE'
    plan=plans.get(tool.get('admissionPlanRef'))
    scope=indexes['scopes'].get(tool.get('scopeRef'))
    if not plan or not scope: return 'PENDING_REVIEW'
    ap=approvals.get(review.get('approvalRef') or tool.get('approvalRef') or plan.get('approvalRef'))
    if not ap or ap.get('status')!='APPROVED' or expired(ap,now): return 'PENDING_REVIEW'
    inst=installs.get(tool.get('installationRef'))
    if not inst: return 'PENDING_INSTALLATION'
    iv=verifications.get(tool.get('installationVerificationRef') or inst.get('verificationRef'))
    if not iv or iv.get('result')!='PASS': return 'PENDING_VERIFICATION'
    return 'AVAILABLE'

def validate_bundle(b):
    errs=[]; st=b.get('projectState')
    if not isinstance(st,dict): return ['projectState mapping missing']
    try: Draft202012Validator(json.loads(STATE_SCHEMA.read_text()),format_checker=FormatChecker()).validate(st)
    except Exception as e: errs.append(f'projectState schema invalid: {getattr(e,"message",e)}')
    ids={}; indexes={}
    for coll,key in COLLECTIONS.items():
        vals=b.get(coll,[])
        if not isinstance(vals,list): errs.append(f'{coll} must be array'); indexes[coll]={}; continue
        idx={}
        for i,x in enumerate(vals):
            if not isinstance(x,dict): errs.append(f'{coll}[{i}] must be object'); continue
            ident=x.get(key)
            if not ident: errs.append(f'{coll}[{i}] missing identity {key}'); continue
            if ident in ids: errs.append(f'duplicate identity {ident} in {coll} and {ids[ident][0]}')
            else: ids[ident]=(coll,i)
            idx[ident]=x
        indexes[coll]=idx
    # Project-state references must resolve.
    state_ref_collections=list(COLLECTIONS)
    for coll in state_ref_collections:
        for ref in st.get(coll,[]) or []:
            if ref not in ids: errs.append(f'projectState.{coll} unresolved reference {ref}')
    # Generic lifecycle/data invariants inherited from v0.3.2.
    for x in indexes['questions'].values():
        if x.get('status')=='ANSWERED' and (not x.get('answer') or not x.get('answerSourceRefs')): errs.append(f'question {x.get("id")} answered without answer/source refs')
    for x in indexes['unknowns'].values():
        if x.get('status')=='RESOLVED' and (not x.get('resolutionEvidenceRefs') or not x.get('resolvedAt')): errs.append(f'unknown {x.get("id")} resolved without evidence/time')
    for coll in ['decisions','technologyDecisions','requirements']:
        for x in indexes[coll].values():
            if x.get('status')=='SUPERSEDED' and not x.get('supersedes'): errs.append(f'{coll}:{x.get("id")} superseded without supersedes')
            if x.get('status')=='LOCKED' and not x.get('approvalRef'): errs.append(f'{coll}:{x.get("id")} locked without approvalRef')
    # Indexes and exact graph binding.
    reviews=indexes['securityReviews']; scans=indexes['scanEvidence']; snaps=indexes['toolSnapshots']; prov=indexes['provenance']; trusts=indexes['scannerTrust']; approvals=indexes['approvals']; scopes=indexes['toolScopes']; plans=indexes['admissionPlans']; installs=indexes['installations']; verifications=indexes['installationVerifications']; deps=indexes['dependencyAudits']; mcps=indexes['mcpSurfaces']; interactions=indexes['capabilityInteractions']; events=indexes['toolLifecycleEvents']
    for sid,s in scans.items():
        tr=trusts.get(s.get('scannerTrustRef')); sn=snaps.get(s.get('snapshotRef'))
        if not tr: errs.append(f'scanEvidence {sid} unresolved scannerTrustRef')
        if not sn: errs.append(f'scanEvidence {sid} unresolved snapshotRef')
        if tr and s.get('scannerTrustHash') and canonical_hash(tr) != s.get('scannerTrustHash'): errs.append(f'scanEvidence {sid} scannerTrustHash mismatch')
        if sn and s.get('targetHash') != sn.get('contentHash'): errs.append(f'scanEvidence {sid} targetHash does not match snapshot contentHash')
        if sn and s.get('target') != sn.get('target'): errs.append(f'scanEvidence {sid} target differs from snapshot')
        if s.get('status')=='PASS' and s.get('analysisCompleteness')!='COMPLETE': errs.append(f'scanEvidence {sid} PASS without COMPLETE analysis')
        if s.get('analysisCompleteness') in {'PARTIAL','UNRESOLVED'} and s.get('status')=='PASS': errs.append(f'scanEvidence {sid} incomplete analysis cannot be PASS')
    # Exact trusted-scanner policy: one shared source of truth (scanner_policy).
    # A self-declared TRUSTED record for any other scanner identity/version fails closed,
    # and a PASS scan can never be backed by a record that violates the policy.
    for tid,t in trusts.items():
        if scanner_policy.is_trusted(t):
            errs.extend(scanner_policy.trust_record_errors(t))
    for sid,s in scans.items():
        if s.get('status')=='PASS':
            tr=trusts.get(s.get('scannerTrustRef'))
            if tr:
                errs.extend(f'scanEvidence {sid}: {pe}' for pe in scanner_policy.trust_record_errors(tr))
    for rid,r in reviews.items():
        for field,idxname in [('scannerTrustRef','scannerTrust'),('snapshotRef','toolSnapshots'),('scanEvidenceRef','scanEvidence'),('provenanceRef','provenance')]:
            if r.get(field) not in indexes[idxname]: errs.append(f'securityReview {rid} unresolved {field}')
        sc=scans.get(r.get('scanEvidenceRef')); sn=snaps.get(r.get('snapshotRef'))
        if sc:
            if sc.get('scannerTrustRef') != r.get('scannerTrustRef'): errs.append(f'securityReview {rid} scanner trust binding differs')
            if sc.get('snapshotRef') != r.get('snapshotRef'): errs.append(f'securityReview {rid} scan/snapshot binding differs')
            if sc.get('target') != r.get('target'): errs.append(f'securityReview {rid} target differs from scan')
            # The review's embedded scan record must describe the exact same scan evidence
            # (R3: reportHash, scanner identity/version, and status are binding, not prose).
            rs=r.get('scan') or {}
            if rs.get('reportHash') and sc.get('reportHash') and rs.get('reportHash')!=sc.get('reportHash'):
                errs.append(f'securityReview {rid} scan reportHash differs from scanEvidence reportHash')
            if rs.get('status') and sc.get('status') and rs.get('status')!=sc.get('status'):
                errs.append(f'securityReview {rid} scan status differs from scanEvidence status')
            tr=trusts.get(r.get('scannerTrustRef'))
            if tr:
                if rs.get('scanner') and rs.get('scanner')!=tr.get('scanner'):
                    errs.append(f'securityReview {rid} scan scanner identity differs from pinned trust record')
                if rs.get('version') and rs.get('version')!=tr.get('version'):
                    errs.append(f'securityReview {rid} scan scanner version differs from pinned trust record version')
        if sn and sn.get('target') != r.get('target'): errs.append(f'securityReview {rid} target differs from snapshot')
        if r.get('scopeRef'):
            scp=scopes.get(r.get('scopeRef'))
            if not scp: errs.append(f'securityReview {rid} unresolved scopeRef')
            elif r.get('scopeHash') != scp.get('canonicalHash'): errs.append(f'securityReview {rid} scope binding mismatch')
        if r.get('subjectHash') and sn and r.get('subjectHash') != sn.get('contentHash'): errs.append(f'securityReview {rid} subjectHash differs from snapshot contentHash')
        if r.get('verdict')=='APPROVED':
            if r.get('approvalRef') not in approvals: errs.append(f'securityReview {rid} approved without approval')
            else:
                ap=approvals[r['approvalRef']]
                if ap.get('artifactId') != r.get('id'): errs.append(f'securityReview {rid} approval artifact binding mismatch')
                if ap.get('status')!='APPROVED': errs.append(f'securityReview {rid} approval is not APPROVED')
    # Scope hash + policy.
    for sid,s in scopes.items():
        if s.get('canonicalHash') != canonical_hash(s,('canonicalHash',)): errs.append(f'toolScope {sid} canonicalHash mismatch')
        if set(s.get('allowedCapabilities',[])) & set(s.get('deniedCapabilities',[])): errs.append(f'toolScope {sid} capability both allowed and denied')
    # Admission plans.
    for pid,p in plans.items():
        if p.get('planHash') != canonical_hash(p,('planHash',)): errs.append(f'admissionPlan {pid} planHash mismatch')
        sc=scopes.get(p.get('scopeRef')); sn=snaps.get(p.get('snapshotRef')); rv=reviews.get(p.get('securityReviewRef')); pv=prov.get(p.get('provenanceRef'))
        if not sc: errs.append(f'admissionPlan {pid} unresolved scopeRef')
        if not sn: errs.append(f'admissionPlan {pid} unresolved snapshotRef')
        if not rv: errs.append(f'admissionPlan {pid} unresolved securityReviewRef')
        if not pv: errs.append(f'admissionPlan {pid} unresolved provenanceRef')
        if sc and p.get('scopeHash')!=sc.get('canonicalHash'): errs.append(f'admissionPlan {pid} scopeHash mismatch')
        if sn and p.get('artifactHash')!=sn.get('contentHash'): errs.append(f'admissionPlan {pid} artifactHash differs from snapshot')
        if pv and pv.get('artifactDigest') and p.get('artifactHash')!=pv.get('artifactDigest'): errs.append(f'admissionPlan {pid} artifactHash differs from provenance artifactDigest')
        if rv and rv.get('target')!=p.get('toolRef'): errs.append(f'admissionPlan {pid} security review target mismatch')
        if p.get('dependencyAuditRef'):
            da=deps.get(p.get('dependencyAuditRef'))
            if not da: errs.append(f'admissionPlan {pid} unresolved dependencyAuditRef')
            elif da.get('targetRef') != p.get('toolRef'): errs.append(f'admissionPlan {pid} dependency audit target mismatch')
        if p.get('mcpSurfaceRef'):
            ms=mcps.get(p.get('mcpSurfaceRef'))
            if not ms: errs.append(f'admissionPlan {pid} unresolved mcpSurfaceRef')
            elif ms.get('targetRef') != p.get('toolRef'): errs.append(f'admissionPlan {pid} MCP surface target mismatch')
        if p.get('capabilityInteractionRef') and p.get('capabilityInteractionRef') not in interactions: errs.append(f'admissionPlan {pid} unresolved capabilityInteractionRef')
    # Approvals.
    for aid,ap in approvals.items():
        if ap.get('status') not in APPROVAL_STATES: errs.append(f'approval {aid} invalid lifecycle state')
        if ap.get('status')=='APPROVED':
            plan=plans.get(ap.get('admissionPlanRef')); scope=scopes.get(ap.get('scopeRef'))
            if not plan: errs.append(f'approval {aid} missing admission plan')
            if not scope: errs.append(f'approval {aid} missing scope')
            if plan and ap.get('admissionPlanHash')!=plan.get('planHash'): errs.append(f'approval {aid} admissionPlanHash mismatch')
            if scope and ap.get('scopeHash')!=scope.get('canonicalHash'): errs.append(f'approval {aid} scopeHash mismatch')
            if plan and ap.get('artifactHash')!=plan.get('artifactHash'): errs.append(f'approval {aid} artifactHash mismatch')
            if plan and ap.get('policyRevision')!=plan.get('policyRevision'): errs.append(f'approval {aid} policyRevision mismatch')
            if ap.get('expiresAt') and expired(ap): errs.append(f'approval {aid} is expired but still APPROVED')
    # Installation and verification.
    for iid,ins in installs.items():
        plan=plans.get(ins.get('admissionPlanRef')); ap=approvals.get(ins.get('approvalRef')); sn=snaps.get(ins.get('snapshotRef')); rv=reviews.get(ins.get('securityReviewRef'))
        for label,obj in [('admission plan',plan),('approval',ap),('snapshot',sn),('security review',rv)]:
            if not obj: errs.append(f'installation {iid} unresolved {label}')
        if plan and ins.get('expectedArtifactHash')!=plan.get('artifactHash'): errs.append(f'installation {iid} expectedArtifactHash mismatch')
        if sn and ins.get('installedContentHash')!=sn.get('contentHash'): errs.append(f'installation {iid} installedContentHash mismatch')
        # A recorded installation may predate v0.4 approval re-binding; it is not AVAILABLE until the exact approval is APPROVED.
        if ap and ap.get('status') not in APPROVAL_STATES: errs.append(f'installation {iid} bound approval has invalid lifecycle state')
        if rv and ins.get('securityReviewRef')!=rv.get('id'): errs.append(f'installation {iid} security review binding mismatch')
    for vid,v in verifications.items():
        ins=installs.get(v.get('installationRef')); plan=plans.get(v.get('admissionPlanRef'))
        if not ins: errs.append(f'installationVerification {vid} unresolved installationRef')
        if not plan: errs.append(f'installationVerification {vid} unresolved admissionPlanRef')
        if ins and ins.get('admissionPlanRef')!=v.get('admissionPlanRef'): errs.append(f'installationVerification {vid} admission binding mismatch')
        if plan and v.get('expectedArtifactHash')!=plan.get('artifactHash'): errs.append(f'installationVerification {vid} expected artifact mismatch')
        if v.get('result')=='PASS' and v.get('expectedArtifactHash')!=v.get('observedArtifactHash'): errs.append(f'installationVerification {vid} PASS with mismatched artifact hash')
        if v.get('result')=='PASS' and v.get('expectedRevision')!=v.get('observedRevision'): errs.append(f'installationVerification {vid} PASS with mismatched revision')
    # Dependency audits: completeness is never a clean substitute.
    for did,d in deps.items():
        if d.get('analysisCompleteness') in {'PARTIAL','UNRESOLVED'} and not d.get('resolutionSource'): errs.append(f'dependencyAudit {did} incomplete without resolutionSource')
        for ex in d.get('exceptions',[]):
            if expired(ex): errs.append(f'dependencyAudit {did} exception {ex.get("id")} expired')
    # MCP evidence.
    for mid,m in mcps.items():
        if m.get('verificationStatus')=='PASS' and m.get('maturity')!='VERIFIED': errs.append(f'mcpSurface {mid} PASS without VERIFIED maturity')
        if m.get('maturity')=='VERIFIED' and not m.get('inspectedCapabilityHash'): errs.append(f'mcpSurface {mid} VERIFIED without inspectedCapabilityHash')
    # Lifecycle events: shared transition policy + causal/evidence completeness + sequence.
    by_subject={}
    for eid,e in events.items():
        errs.extend(lifecycle_policy.event_errors(e))
        by_subject.setdefault((e.get('subjectKind'),e.get('subjectRef')),[]).append(e)
    for key,arr in by_subject.items():
        for ce in lifecycle_policy.chain_errors(arr):
            errs.append(f'lifecycle events for {key}: {ce}')
    # Tool effective status is derived, not trusted from declared status.
    local_indexes={'reviews':reviews,'approvals':approvals,'plans':plans,'installs':installs,'verifications':verifications,'scopes':scopes,'events':events}
    for tool in indexes['tools'].values():
        for ref_key, coll_name in [('dependencyAuditRef','dependencyAudits'),('mcpSurfaceRef','mcpSurfaces'),('capabilityInteractionRef','capabilityInteractions')]:
            ref=tool.get(ref_key)
            if ref and ref not in indexes[coll_name]: errs.append(f'tool {tool.get("name")} unresolved {ref_key} {ref}')
        if tool.get('dependencyAuditRef'):
            da=indexes['dependencyAudits'].get(tool.get('dependencyAuditRef'))
            if da and da.get('targetRef') != tool.get('name'): errs.append(f'tool {tool.get("name")} dependency audit target mismatch')
        if tool.get('mcpSurfaceRef'):
            ms=indexes['mcpSurfaces'].get(tool.get('mcpSurfaceRef'))
            if ms and ms.get('targetRef') != tool.get('name'): errs.append(f'tool {tool.get("name")} MCP surface target mismatch')
        for ref in tool.get('lifecycleEventRefs',[]) or []:
            if ref not in indexes['toolLifecycleEvents']: errs.append(f'tool {tool.get("name")} unresolved lifecycleEventRef {ref}')
        if tool.get('effectiveStatus') not in TOOL_STATES: errs.append(f'tool {tool.get("name")} invalid effectiveStatus')
        expected=derive_tool(tool, {**local_indexes})
        if tool.get('effectiveStatus')!=expected: errs.append(f'tool {tool.get("name")} effectiveStatus mismatch: stored={tool.get("effectiveStatus")} derived={expected}')
        if tool.get('reviewDisposition')=='BLOCKED' and not tool.get('blockedReasons'): errs.append(f'tool {tool.get("name")} BLOCKED disposition without reasons')
        if tool.get('effectiveStatus')=='AVAILABLE' and tool.get('status') in DECLARED_NON_AVAILABLE_STATES:
            errs.append(f'tool {tool.get("name")} declared status {tool.get("status")} conflicts with derived AVAILABLE')
    # Trace/dependency endpoints.
    for x in indexes['traceLinks'].values():
        if x.get('from') not in ids: errs.append(f'trace from missing {x.get("from")}')
        if x.get('to') not in ids: errs.append(f'trace to missing {x.get("to")}')
    for x in indexes['artifactDependencies'].values():
        if x.get('from') not in ids: errs.append(f'dependency from missing {x.get("from")}')
        if x.get('to') not in ids: errs.append(f'dependency to missing {x.get("to")}')
    # Readiness assertions.
    rs=st.get('readinessSummary') or {}
    blocking_unknowns=sorted(x.get('id') for x in indexes['unknowns'].values() if x.get('status') in {'OPEN','PARTIALLY_RESOLVED','CARRIED'} and x.get('impact') in {'HIGH','CRITICAL'})
    unresolved_must=sorted(x.get('id') for x in indexes['requirements'].values() if x.get('priority')=='MUST' and x.get('status') not in {'IMPLEMENTATION_READY'})
    unapproved=sorted(x.get('name') for x in indexes['tools'].values() if x.get('effectiveStatus')!='AVAILABLE')
    pending_approvals=sorted(x.get('id') for x in approvals.values() if x.get('status')=='PENDING')
    stale=sorted(set(st.get('staleRecords',[]) or []))
    checks={'blockingUnknowns':blocking_unknowns,'unresolvedMustRequirements':unresolved_must,'unapprovedTools':unapproved,'pendingApprovals':pending_approvals}
    for k,want in checks.items():
        if sorted(rs.get(k,[]))!=want: errs.append(f'readinessSummary.{k} is stale/inaccurate')
    if st.get('readiness')=='READY':
        if any(st.get(k) for k in ['blockers','spikes','staleRecords','unknowns']): errs.append('READY contains blockers/spikes/stale/unknowns')
        if any(rs.get(k) for k in ['blockingUnknowns','unresolvedMustRequirements','unapprovedTools','staleRecords','missingCanonicalDocs','pendingApprovals','blockingSpikes']): errs.append('READY readinessSummary not clear')
    if st.get('readiness')=='READY_WITH_SPIKES':
        if not st.get('spikes'): errs.append('READY_WITH_SPIKES requires spikes')
        if st.get('blockers') or st.get('staleRecords'): errs.append('READY_WITH_SPIKES cannot contain blockers/stale records')
    return errs

def main():
    if len(sys.argv)!=2:
        print('usage: validate_project_state.py STATE-BUNDLE.json'); return 2
    try: b=load(sys.argv[1])
    except Exception as e: return fail([f'invalid JSON: {e}'])
    errs=validate_bundle(b)
    return fail(errs) if errs else (print('PASS: project-state graph, lifecycle, derived availability, exact admission binding, and readiness integrity') or 0)

if __name__=='__main__': sys.exit(main())
