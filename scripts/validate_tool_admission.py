#!/usr/bin/env python3
"""Focused validator for exact v0.4 tool-admission bindings."""
from pathlib import Path
from datetime import datetime, timezone
import json,sys,hashlib
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scanner_policy

def ch(obj,exclude): return hashlib.sha256(json.dumps({k:v for k,v in obj.items() if k not in exclude},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def expired(a):
 try:return datetime.fromisoformat(a.get('expiresAt','').replace('Z','+00:00')) <= datetime.now(timezone.utc)
 except:return False
def load(p): return json.loads(Path(p).read_text(encoding='utf8'))

def main():
 if len(sys.argv)!=2: print('usage: validate_tool_admission.py STATE-BUNDLE.json'); return 2
 try:b=load(sys.argv[1])
 except Exception as e: print('FAIL:',e); return 1
 scopes={x.get('id'):x for x in b.get('toolScopes',[]) if isinstance(x,dict)}; plans={x.get('id'):x for x in b.get('admissionPlans',[]) if isinstance(x,dict)}; aps={x.get('id'):x for x in b.get('approvals',[]) if isinstance(x,dict)}; tools={x.get('name'):x for x in b.get('tools',[]) if isinstance(x,dict)}; ivs={x.get('id'):x for x in b.get('installationVerifications',[]) if isinstance(x,dict)}; installs={x.get('id'):x for x in b.get('installations',[]) if isinstance(x,dict)}; snaps={x.get('id'):x for x in b.get('toolSnapshots',[]) if isinstance(x,dict)}; prov={x.get('id'):x for x in b.get('provenance',[]) if isinstance(x,dict)}; reviews={x.get('id'):x for x in b.get('securityReviews',[]) if isinstance(x,dict)}
 errs=[]
 for sid,s in scopes.items():
  if s.get('canonicalHash')!=ch(s,{'canonicalHash'}): errs.append(f'scope {sid}: canonicalHash mismatch')
  if set(s.get('allowedCapabilities',[])) & set(s.get('deniedCapabilities',[])): errs.append(f'scope {sid}: capability overlap')
  if not s.get('approvalRequired'): errs.append(f'scope {sid}: approvalRequired must remain true for admission')
 for pid,p in plans.items():
  if p.get('planHash')!=ch(p,{'planHash'}): errs.append(f'plan {pid}: planHash mismatch')
  s=scopes.get(p.get('scopeRef')); sn=snaps.get(p.get('snapshotRef')); rv=reviews.get(p.get('securityReviewRef')); pv=prov.get(p.get('provenanceRef')); ap=aps.get(p.get('approvalRef')) if p.get('approvalRef') else None
  if not s or not sn or not rv or not pv: errs.append(f'plan {pid}: missing core plan binding')
  if s and p.get('scopeHash')!=s.get('canonicalHash'): errs.append(f'plan {pid}: scope hash mismatch')
  if sn and p.get('artifactHash')!=sn.get('contentHash'): errs.append(f'plan {pid}: artifact differs from snapshot')
  if pv and pv.get('artifactDigest') and p.get('artifactHash')!=pv.get('artifactDigest'): errs.append(f'plan {pid}: artifact differs from provenance digest')
  if rv and rv.get('target')!=p.get('toolRef'): errs.append(f'plan {pid}: security review target mismatch')
  if p.get('dependencyAuditRef') and p.get('dependencyAuditRef') not in {x.get('id') for x in b.get('dependencyAudits',[]) if isinstance(x,dict)}: errs.append(f'plan {pid}: dependency audit missing')
  if p.get('mcpSurfaceRef') and p.get('mcpSurfaceRef') not in {x.get('id') for x in b.get('mcpSurfaces',[]) if isinstance(x,dict)}: errs.append(f'plan {pid}: MCP surface missing')
  if ap and ap.get('admissionPlanHash')!=p.get('planHash'): errs.append(f'plan {pid}: approval plan binding mismatch')
 for aid,a in aps.items():
  if a.get('status')=='APPROVED':
   p=plans.get(a.get('admissionPlanRef')); s=scopes.get(a.get('scopeRef'))
   if not p or not s: errs.append(f'approval {aid}: bound plan/scope missing')
   if p and a.get('admissionPlanHash')!=p.get('planHash'): errs.append(f'approval {aid}: planHash mismatch')
   if s and a.get('scopeHash')!=s.get('canonicalHash'): errs.append(f'approval {aid}: scopeHash mismatch')
   if p and a.get('artifactHash')!=p.get('artifactHash'): errs.append(f'approval {aid}: artifactHash mismatch')
   if p and a.get('policyRevision')!=p.get('policyRevision'): errs.append(f'approval {aid}: policyRevision mismatch')
   if expired(a): errs.append(f'approval {aid}: expired approval cannot be APPROVED')
 for iid,ins in installs.items():
  p=plans.get(ins.get('admissionPlanRef')); ap=aps.get(ins.get('approvalRef')); iv=[v for v in ivs.values() if v.get('installationRef')==iid]
  if not p: errs.append(f'installation {iid}: admission plan missing')
  if p and ins.get('expectedArtifactHash')!=p.get('artifactHash'): errs.append(f'installation {iid}: expected artifact mismatch')
  if ap and ap.get('status')=='APPROVED' and p and ap.get('admissionPlanHash')!=p.get('planHash'): errs.append(f'installation {iid}: approval/plan binding mismatch')
  if ins.get('status')=='INSTALLED' and not iv: errs.append(f'installation {iid}: installed record lacks verification record')
 for vid,v in ivs.items():
  ins=installs.get(v.get('installationRef')); p=plans.get(v.get('admissionPlanRef'))
  if not ins or not p: errs.append(f'verification {vid}: unresolved installation/admission')
  if ins and ins.get('admissionPlanRef')!=v.get('admissionPlanRef'): errs.append(f'verification {vid}: admission binding mismatch')
  if p and v.get('expectedArtifactHash')!=p.get('artifactHash'): errs.append(f'verification {vid}: expected artifact mismatch')
  if v.get('result')=='PASS' and v.get('expectedArtifactHash')!=v.get('observedArtifactHash'): errs.append(f'verification {vid}: PASS hash mismatch')
  if v.get('result')=='PASS' and v.get('expectedRevision')!=v.get('observedRevision'): errs.append(f'verification {vid}: PASS revision mismatch')
 for tid,t in tools.items():
  if t.get('effectiveStatus')=='AVAILABLE':
   p=plans.get(t.get('admissionPlanRef')); s=scopes.get(t.get('scopeRef')); iv=ivs.get(t.get('installationVerificationRef')); ap=aps.get(p.get('approvalRef')) if p else None
   if not p or not s or not iv: errs.append(f'tool {tid}: AVAILABLE missing exact admission chain')
   if ap and ap.get('status')!='APPROVED': errs.append(f'tool {tid}: AVAILABLE without current approval')
   if iv and iv.get('result')!='PASS': errs.append(f'tool {tid}: AVAILABLE without PASS verification')
   # Shared exact-scanner policy: an AVAILABLE tool must be backed by a policy-valid trusted scanner record.
   rv=reviews.get(t.get('securityReviewRef'))
   tr={x.get('id'):x for x in b.get('scannerTrust',[]) if isinstance(x,dict)}.get(rv.get('scannerTrustRef')) if rv else None
   if tr:
    errs.extend(f'tool {tid}: {e}' for e in scanner_policy.trust_record_errors(tr))
   else:
    errs.append(f'tool {tid}: AVAILABLE without a resolvable scanner trust record')
 if errs: print('FAIL'); [print(' -',e) for e in errs]; return 1
 print('PASS: exact tool admission, scope, provenance, approval, installation, and verification bindings'); return 0
if __name__=='__main__': sys.exit(main())
