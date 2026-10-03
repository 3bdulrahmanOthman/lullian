#!/usr/bin/env python3
from pathlib import Path
import json,sys
try:
 from jsonschema import Draft202012Validator, FormatChecker
except Exception as e: print('BLOCKED: jsonschema package required:',e); sys.exit(2)
ROOT=Path(__file__).resolve().parents[1]
H='a'*64
examples={
'schema-approval.json':{'id':'ap1','artifactId':'plan1','owner':'owner','status':'PENDING','reviewDisposition':'NONE'},
'schema-project-intake.json':{'id':'p1','name':'Example','projectType':'saas','objective':'Launch','mode':'greenfield'},
'schema-requirement.json':{'id':'r1','statement':'x','priority':'MUST','status':'IMPLEMENTATION_READY','sourceRefs':['u1'],'acceptance':['a1']},
'schema-unknown.json':{'id':'u1','question':'q','impact':'HIGH','resolution':'RESEARCH','status':'OPEN'},
'schema-question.json':{'id':'q1','question':'q','targetUnknown':'u1','impact':'HIGH','expectedValue':1,'status':'CANDIDATE'},
'schema-research-plan.json':{'id':'rp1','question':'q','evidenceTarget':'e','depth':'STANDARD','budget':{'maxQueries':2,'maxSources':2,'maxMinutes':5},'status':'PLANNED'},
'schema-research-usage.json':{'planRef':'rp1','queriesUsed':1,'sourcesUsed':1,'elapsedSeconds':10,'withinBudget':True},
'schema-evidence.json':{'id':'e1','claim':'x','class':'OFFICIAL_SOURCE','status':'CONFIRMED','confidence':'HIGH','source':{'url':'https://example.com','publisher':'Example','retrievedAt':'2026-10-01T00:00:00Z'}},
'schema-decision.json':{'id':'d1','question':'q','chosen':'x','status':'PROPOSED','evidenceRefs':['e1'],'owner':'owner'},
'schema-architecture.json':{'id':'arch1','style':'modular-monolith','boundaries':['b'],'domains':['d'],'integrations':['i'],'qualityAttributes':['qa'],'decisionRefs':['d1'],'deploymentSummary':'container','securityBoundaries':['auth'],'failureModes':['db down']},
'schema-technology-decision.json':{'id':'td1','category':'db','selected':'postgres','status':'PROPOSED','evidenceRefs':['e1'],'owner':'owner'},
'schema-cross-cutting-concern.json':{'id':'c1','concern':'security','status':'material','rationale':'auth'},
'schema-quality-attribute.json':{'id':'qa1','name':'performance','target':'p95','priority':'MUST'},
'schema-workflow.json':{'id':'wf1','engineering':'JSM','depth':'ALPHA','reason':'fit'},
'schema-tool.json':{'name':'x','type':'MCP','capability':'browse','status':'BLOCKED','effectiveStatus':'CANDIDATE','reviewDisposition':'BLOCKED','blockedReasons':['NO_TRUSTED_PROVENANCE'],'activationCondition':'when needed','provenanceRef':'prov-1','securityReviewRef':'sec-1','trustLevel':'UNVERIFIED'},
'schema-tool-security-review.json':{'id':'ts1','target':'x','provenanceRef':'prov-1','scannerTrustRef':'scanner-1','snapshotRef':'snap-1','scanEvidenceRef':'scan-1','scopeRef':'scope-1','scopeHash':H,'subjectHash':H,'policyRevision':'v0.4-policy-1','scan':{'scanner':'NVIDIA_SKILLSPECTOR','version':'2.11.2','mode':'STATIC_NO_LLM','status':'PASS','analysisComplete':True,'reportHash':H,'severity':'LOW','exitCode':0},'verdict':'PENDING_USER_APPROVAL'},
'schema-tool-snapshot.json':{'id':'snap1','target':'x','capturedAt':'2026-10-01T00:00:00Z','contentHash':H,'snapshotArchiveHash':H,'snapshotArchiveRef':'snap.tar','scannerTrustHash':H,'sourceRef':'prov-1','changePolicy':'RESCAN_ON_ANY_CHANGE','subjectIdentityHash':H},
'schema-tool-provenance.json':{'id':'prov-1','kind':'MCP','canonicalUrl':'https://example.com/mcp','owner':'Example','versionOrRevision':'v1.0.0','retrievedAt':'2026-10-01T00:00:00Z','contentHash':H,'provenanceStrength':'CANONICAL_TAG'},
'schema-scanner-trust.json':{'id':'scanner1','scanner':'NVIDIA_SKILLSPECTOR','publisher':'NVIDIA','version':'2.11.2','releaseRef':'release','executableHash':H,'binaryPathPolicy':'PINNED_FILE','verifiedBy':'reviewer','verifiedAt':'2026-10-01T00:00:00Z','trustStatus':'TRUSTED','trustBasis':'VERIFIED_EXECUTABLE','verificationEvidenceRefs':['ev-1']},
'schema-scan-evidence.json':{'id':'scan-1','target':'x','scannerTrustRef':'scanner-1','scannerTrustHash':H,'targetHash':H,'reportHash':H,'reportRef':'raw.json','snapshotRef':'snap-1','snapshotArchiveHash':H,'snapshotArchiveRef':'snapshot.tar','mode':'STATIC_NO_LLM','status':'PASS','analysisComplete':True,'analysisCompleteness':'COMPLETE','analysisMode':'STATIC_NO_LLM','severity':'LOW','scannerExitCode':0,'scannedAt':'2026-10-01T00:00:00Z'},
'schema-tool-installation.json':{'id':'inst-1','toolRef':'x','provenanceRef':'prov-1','securityReviewRef':'sec-1','snapshotRef':'snap-1','approvalRef':'a-1','admissionPlanRef':'plan-1','installedAt':'2026-10-01T00:00:00Z','installedContentHash':H,'expectedArtifactHash':H,'expectedRevision':'v1','location':'/reviewed/install','status':'INSTALLED'},
'schema-documentation-manifest.json':{'schemaVersion':'1','documents':[{'id':'doc1','path':'docs/x.md','kind':'CANONICAL','status':'REQUIRED','sourceRefs':['d1'],'owner':'owner'}]},
'schema-document.json':{'id':'doc1','path':'docs/x.md','kind':'CANONICAL','status':'REQUIRED','sourceRefs':['d1'],'owner':'owner'},
'schema-trace-link.json':{'id':'tl1','from':'r1','to':'d1','relation':'SUPPORTS'},
'schema-handoff.json':{'status':'READY_WITH_SPIKES','summary':'x','nextStep':'y','spikes':['spike-1'],'readinessEvidenceRefs':['e1'],'governanceBlockers':[],'admissionPlanRefs':['plan-1']},
'schema-assessment.json':{'status':'PROCEED','rationale':'x'},
'schema-source-precedence.json':{'rules':[{'rank':1,'sourceClass':'USER_FACT'}]},
'schema-artifact-dependency.json':{'id':'dep1','from':'e1','to':'d1','relation':'DERIVED_FROM'},
'schema-project-state.json':{'schemaVersion':'2','project':{'id':'p1','name':'x','mode':'greenfield'},'readiness':'READY','readinessSummary':{'blockingUnknowns':[],'unresolvedMustRequirements':[],'unapprovedTools':[],'staleRecords':[],'missingCanonicalDocs':[],'pendingApprovals':[],'blockingSpikes':[]}},
'schema-eval-case.json':{'id':'e1','prompt':'Build','expected_output':'Foundation evidence','assertions':['has evidence'],'executableAssertions':[{'type':'MUST_CONTAIN','value':'evidence'},{'type':'MUST_NOT_CONTAIN','value':'npm install'}],'category':'CORE'},
'schema-metamorphic-case.json':{'id':'m1','input_change':'change x','expected_local_changes':['decision'],'must_not_change':['unrelated'],'category':'CORE'},
'schema-tool-scope.json':{'id':'scope-1','toolRef':'x','allowedCapabilities':['read:browse'],'deniedCapabilities':['write:external'],'approvalRequired':True,'policyRevision':'v0.4-policy-1','createdAt':'2026-10-01T00:00:00Z','canonicalHash':H},
'schema-tool-admission-plan.json':{'id':'plan-1','toolRef':'x','provenanceRef':'prov-1','snapshotRef':'snap-1','artifactHash':H,'revision':'v1','scopeRef':'scope-1','scopeHash':H,'securityReviewRef':'sec-1','policyRevision':'v0.4-policy-1','installationMethod':'EXTERNAL_EXECUTOR','verificationRequirements':['HASH_COMPARE'],'reapprovalTriggers':['ARTIFACT_CHANGED'],'createdAt':'2026-10-01T00:00:00Z','planHash':H},
'schema-installation-verification.json':{'id':'iv-1','installationRef':'inst-1','admissionPlanRef':'plan-1','expectedArtifactHash':H,'observedArtifactHash':H,'expectedRevision':'v1','observedRevision':'v1','verificationMethod':'HASH_COMPARE','verifier':'host','verifiedAt':'2026-10-01T00:00:00Z','result':'PASS','evidenceRefs':['ev-1']},
'schema-dependency-audit.json':{'id':'dep-audit-1','targetRef':'x','ecosystem':'npm','analysisCompleteness':'COMPLETE','scanner':'OSV-Scanner','scannerVersion':'2.1.0','resolvedDependencies':[{'name':'pkg','version':'1.0.0'}],'scannedAt':'2026-10-01T00:00:00Z','resolutionSource':'package-lock.json'},
'schema-mcp-surface.json':{'id':'mcp-1','targetRef':'x','protocolRevision':'2026-07-28','transport':'STDIO','serverIdentity':'example/mcp:v1','authorizationModel':'local host registration','maturity':'DECLARED','verificationBasis':'STATIC','declaredAnnotationsHash':H,'verificationStatus':'UNVERIFIED'},
'schema-capability-interaction.json':{'id':'ci-1','capabilityRefs':['cap-private-read','cap-external-write'],'riskFactors':['private data + external egress'],'interactionRuleRef':'policy-7','riskLevel':'HIGH','policyDecision':'REQUIRES_HUMAN_REVIEW','evidenceRefs':['e1']},
'schema-tool-lifecycle-event.json':{'id':'ev-1','subjectRef':'x','subjectKind':'TOOL','eventType':'REVIEW_REQUIRED','previousState':'AVAILABLE','newState':'STALE','source':'validator','actor':'system','occurredAt':'2026-10-01T00:00:00Z','causeRefs':['scope-1'],'evidenceRefs':['e1'],'sequence':1},
'schema-release-attestation.json':{'id':'att-1','subjectType':'PACKAGE','subjectDigest':H,'attestationType':'SLSA_PROVENANCE','issuer':'release-system','createdAt':'2026-10-01T00:00:00Z','verificationStatus':'VERIFIED','evidenceRef':'attestation.json'},
}
errors=[]
for p in sorted((ROOT/'assets').glob('schema-*.json')):
    if p.name not in examples: errors.append(f'missing example for {p.name}'); continue
    try:
        schema=json.loads(p.read_text()); Draft202012Validator(schema,format_checker=FormatChecker()).validate(examples[p.name])
    except Exception as e: errors.append(f'{p.name}: {getattr(e,"message",e)}')
if errors:
 print('FAIL'); [print(' -',e) for e in errors]; sys.exit(1)
print(f'PASS: {len(examples)} representative instances validate against all schemas')
