#!/usr/bin/env python3
"""Conservative deterministic migration from v0.3.2 project-state bundles to v0.4.

Migration never upgrades trust. Legacy approved records are moved to PENDING and
legacy installations receive explicitly non-admissible migration plans/scopes so
the resulting graph remains structurally valid without claiming v0.4 admission.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, sys


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def canonical_hash(obj, excluded=()):
    data = {k: v for k, v in obj.items() if k not in set(excluded)}
    raw = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def migrate(src):
    b = json.loads(Path(src).read_text(encoding='utf8'))
    st = b.get('projectState')
    if not isinstance(st, dict):
        raise ValueError('projectState mapping missing')
    if str(st.get('schemaVersion')) not in {'1', '1.0'}:
        raise ValueError(f'expected v0.3.x schemaVersion=1, got {st.get("schemaVersion")}')

    b = json.loads(json.dumps(b))
    st = dict(b['projectState'])
    st['schemaVersion'] = '2'
    st['governanceRevision'] = 'v0.4.0-migration'
    migrated_at = now()

    for k in ['toolScopes','admissionPlans','installationVerifications','dependencyAudits',
              'mcpSurfaces','capabilityInteractions','toolLifecycleEvents']:
        st.setdefault(k, [])

    # New v0.4 governance collections are top-level collections, not embedded state objects.
    for k in ['toolScopes','admissionPlans','installationVerifications','dependencyAudits',
              'mcpSurfaces','capabilityInteractions','toolLifecycleEvents']:
        b.setdefault(k, [])

    snapshots = {x.get('id'): x for x in b.get('toolSnapshots', []) if isinstance(x, dict)}
    provenances = {x.get('id'): x for x in b.get('provenance', []) if isinstance(x, dict)}
    reviews = {x.get('id'): x for x in b.get('securityReviews', []) if isinstance(x, dict)}

    # Deterministically lift legacy evidence fields without increasing trust.
    for snap in snapshots.values():
        snap.setdefault('subjectIdentityHash', snap.get('contentHash'))
        snap.setdefault('snapshotSchemaVersion', '2')
    for scan in b.get('scanEvidence', []):
        if 'analysisCompleteness' not in scan:
            scan['analysisCompleteness'] = 'COMPLETE' if scan.get('analysisComplete') is True else ('PARTIAL' if scan.get('analysisComplete') is False else 'UNRESOLVED')
        scan.setdefault('analysisMode', 'STATIC_NO_LLM')

    # Legacy approvals cannot prove exact v0.4 scope/plan/hash binding.
    for ap in b.get('approvals', []):
        if ap.get('status') == 'APPROVED':
            ap['status'] = 'PENDING'
            ap['reviewDisposition'] = 'REQUIRES_REVIEW'
            note = 'v0.4 migration: exact admission-plan, scope, artifact, and policy bindings must be re-approved.'
            ap['notes'] = ((ap.get('notes') + ' ') if ap.get('notes') else '') + note

    # Build one explicit migration scope + admission plan for every legacy installation.
    scopes = {x.get('id'): x for x in b.get('toolScopes', []) if isinstance(x, dict)}
    plans = {x.get('id'): x for x in b.get('admissionPlans', []) if isinstance(x, dict)}
    tools_by_name = {x.get('name'): x for x in b.get('tools', []) if isinstance(x, dict)}
    approvals_by_id = {x.get('id'): x for x in b.get('approvals', []) if isinstance(x, dict)}

    # Every migrated tool receives a conservative scope so security reviews can be rebound
    # to an explicit v0.4 context without granting approval.
    for tool_ref, tool in tools_by_name.items():
        scope_id = f'migration-scope-{tool_ref}'
        if scope_id in scopes: continue
        scope = {
            'id': scope_id, 'toolRef': tool_ref,
            'allowedCapabilities': [tool.get('capability', 'legacy-capability')],
            'deniedCapabilities': [], 'approvalRequired': True,
            'policyRevision': 'v0.4.0-migration', 'createdAt': migrated_at,
            'notes': 'Migration placeholder. This scope conveys no v0.4 trust until explicitly re-approved.',
            'canonicalHash': ''
        }
        scope['canonicalHash'] = canonical_hash(scope, ('canonicalHash',))
        scopes[scope_id] = scope
        tool['scopeRef'] = scope_id

    # Legacy APPROVED reviews are no longer valid after approval binding is downgraded.
    for review in reviews.values():
        ap = approvals_by_id.get(review.get('approvalRef'))
        if ap and ap.get('status') != 'APPROVED' and review.get('verdict') == 'APPROVED':
            review['verdict'] = 'PENDING_USER_APPROVAL'
        if review.get('target') in tools_by_name:
            scope_id = f'migration-scope-{review.get("target")}'
            review['scopeRef'] = scope_id
            review['scopeHash'] = scopes[scope_id]['canonicalHash']
            snap = snapshots.get(review.get('snapshotRef'))
            if snap and snap.get('contentHash'):
                review['subjectHash'] = snap['contentHash']
            review['policyRevision'] = 'v0.4.0-migration'
            if review.get('evidenceRefs') is None: review['evidenceRefs'] = []

    for ins in b.get('installations', []):
        tool_ref = ins.get('toolRef')
        snap = snapshots.get(ins.get('snapshotRef'))
        prov = provenances.get(ins.get('provenanceRef'))
        review = reviews.get(ins.get('securityReviewRef'))
        tool = tools_by_name.get(tool_ref)
        if not tool or not snap or not prov or not review:
            ins['status'] = 'QUARANTINED'
            ins['notes'] = ((ins.get('notes') + ' ') if ins.get('notes') else '') + 'v0.4 migration: unresolved legacy binding; installation quarantined pending manual reconstruction.'
            ins['admissionPlanRef'] = ins.get('admissionPlanRef') or f'migration-plan-unresolved-{tool_ref or ins.get("id")}'
            continue

        scope_id = f'migration-scope-{tool_ref}'
        plan_id = f'migration-plan-{tool_ref}'
        artifact_hash = snap.get('contentHash') or prov.get('artifactDigest') or ins.get('installedContentHash')
        revision = snap.get('version') or prov.get('sourceRevision') or prov.get('versionOrRevision') or 'legacy-unknown'
        if not artifact_hash or len(str(artifact_hash)) != 64:
            ins['status'] = 'QUARANTINED'
            ins['notes'] = ((ins.get('notes') + ' ') if ins.get('notes') else '') + 'v0.4 migration: no verifiable legacy artifact hash; installation quarantined.'
            ins['admissionPlanRef'] = plan_id
            continue

        scope = scopes[scope_id]

        plan = {
            'id': plan_id,
            'toolRef': tool_ref,
            'provenanceRef': prov.get('id'),
            'snapshotRef': snap.get('id'),
            'artifactHash': artifact_hash,
            'revision': str(revision),
            'scopeRef': scope_id,
            'scopeHash': scope['canonicalHash'],
            'securityReviewRef': review.get('id'),
            'policyRevision': 'v0.4.0-migration',
            'installationMethod': 'EXTERNAL_EXECUTOR',
            'verificationRequirements': ['HASH_COMPARE', 'MANIFEST_COMPARE'],
            'reapprovalTriggers': ['MIGRATION_REVIEW', 'SCOPE_CHANGED', 'DEPENDENCY_CHANGED', 'MCP_SURFACE_CHANGED'],
            'createdAt': migrated_at,
            'requiredEvidenceRefs': [],
            'rollbackCondition': 'Any exact binding mismatch requires quarantine and re-admission.',
            'notes': 'Migration placeholder. Not admissible until a new v0.4 approval is issued.'
        }
        plan['planHash'] = canonical_hash(plan, ('planHash',))
        plans[plan_id] = plan

        ins['admissionPlanRef'] = plan_id
        ins['expectedArtifactHash'] = artifact_hash
        ins['expectedRevision'] = str(revision)
        ins.pop('verificationRef', None)
        # Do not carry forward old verification as authoritative.
        ins['notes'] = ((ins.get('notes') + ' ') if ins.get('notes') else '') + 'v0.4 migration: prior approval/verification is non-authoritative and requires re-admission.'

        ap = approvals_by_id.get(ins.get('approvalRef'))
        if ap and ap.get('status') == 'APPROVED':
            ap['status'] = 'PENDING'
            ap['reviewDisposition'] = 'REQUIRES_REVIEW'

    b['toolScopes'] = list(scopes.values())
    b['admissionPlans'] = list(plans.values())

    for t in b.get('tools', []):
        if not isinstance(t, dict):
            continue
        t['status'] = t.get('status') or 'PENDING_REVIEW'
        t['effectiveStatus'] = 'PENDING_REVIEW'
        t['reviewDisposition'] = 'REQUIRES_REVIEW'
        reasons = list(t.get('blockedReasons') or [])
        if 'MIGRATION_REVIEW_REQUIRED' not in reasons:
            reasons.append('MIGRATION_REVIEW_REQUIRED')
        t['blockedReasons'] = reasons
        t.pop('designAuthority', None)
        # Existing references remain opaque/legacy; the new graph is what gates availability.

    st['readiness'] = 'NOT_READY'
    rs = dict(st.get('readinessSummary') or {})
    rs['unapprovedTools'] = sorted({t.get('name') for t in b.get('tools', []) if t.get('name')})
    rs['pendingApprovals'] = sorted({a.get('id') for a in b.get('approvals', []) if a.get('id') and a.get('status') in {'PENDING', 'EXPIRED', 'REVOKED', 'REJECTED', 'SUPERSEDED'}})
    st['readinessSummary'] = rs
    st['approvals'] = [a.get('id') for a in b.get('approvals', []) if a.get('id')]
    st['toolSnapshots'] = [x.get('id') for x in b.get('toolSnapshots', []) if x.get('id')]
    st['toolScopes'] = [x.get('id') for x in b.get('toolScopes', []) if x.get('id')]
    st['admissionPlans'] = [x.get('id') for x in b.get('admissionPlans', []) if x.get('id')]
    st['installationVerifications'] = []
    st['dependencyAudits'] = [x.get('id') for x in b.get('dependencyAudits', []) if x.get('id')]
    st['mcpSurfaces'] = [x.get('id') for x in b.get('mcpSurfaces', []) if x.get('id')]
    st['capabilityInteractions'] = [x.get('id') for x in b.get('capabilityInteractions', []) if x.get('id')]
    st['toolLifecycleEvents'] = [x.get('id') for x in b.get('toolLifecycleEvents', []) if x.get('id')]
    b['projectState'] = st
    return b


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('source'); ap.add_argument('output'); args = ap.parse_args()
    try:
        out = migrate(args.source)
    except Exception as e:
        print('FAIL:', e); return 1
    p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(f'PASS: migrated v0.3.2 state to schemaVersion=2 at {p}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
