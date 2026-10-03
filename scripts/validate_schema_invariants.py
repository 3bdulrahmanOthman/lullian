#!/usr/bin/env python3
from pathlib import Path
import json,sys
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
H='a'*64

def valid(fn, obj):
    s=json.loads((ROOT/'assets'/fn).read_text())
    return not list(Draft202012Validator(s,format_checker=FormatChecker()).iter_errors(obj))

cases=[
('schema-decision.json',{'id':'d','question':'q','chosen':'x','status':'LOCKED','evidenceRefs':['e'],'owner':'o'},False,'locked needs approval'),
('schema-decision.json',{'id':'d','question':'q','chosen':'x','status':'LOCKED','evidenceRefs':['e'],'owner':'o','approver':'o','approvalRef':'a','lockedAt':'2026-10-01T00:00:00Z'},True,'locked approved fields'),
('schema-decision.json',{'id':'d','question':'q','chosen':'x','status':'SUPERSEDED','evidenceRefs':['e'],'owner':'o'},False,'superseded needs link'),
('schema-question.json',{'id':'q','question':'q','targetUnknown':'u','impact':'HIGH','expectedValue':1,'status':'ANSWERED'},False,'answered needs answer'),
('schema-unknown.json',{'id':'u','question':'q','impact':'HIGH','resolution':'RESEARCH','status':'RESOLVED'},False,'resolved needs evidence/time'),
('schema-evidence.json',{'id':'e','claim':'x','class':'OFFICIAL_SOURCE','status':'CONFIRMED','confidence':'HIGH'},False,'official evidence needs source'),
('schema-tool.json',{'name':'m','type':'MCP','capability':'shell','status':'AVAILABLE','effectiveStatus':'AVAILABLE','activationCondition':'now','provenanceRef':'p','securityReviewRef':'s','trustLevel':'SCANNED_PENDING_APPROVAL'},False,'available cannot be preapproval'),
('schema-tool-security-review.json',{'id':'s','target':'m','provenanceRef':'p','scannerTrustRef':'st','snapshotRef':'sn','scanEvidenceRef':'se','scopeRef':'scp','scopeHash':H,'subjectHash':H,'policyRevision':'p1','scan':{'scanner':'NVIDIA_SKILLSPECTOR','version':'2.11.2','mode':'STATIC_NO_LLM','status':'PASS','analysisComplete':True,'reportHash':H,'severity':'MEDIUM','exitCode':0},'verdict':'APPROVED','approvalRef':'a','approvedBy':'o','approvedAt':'2026-10-01T00:00:00Z'},False,'approved cannot have medium finding'),
('schema-tool-security-review.json',{'id':'s','target':'m','provenanceRef':'p','scannerTrustRef':'st','snapshotRef':'sn','scanEvidenceRef':'se','scopeRef':'scp','scopeHash':H,'subjectHash':H,'policyRevision':'p1','scan':{'scanner':'NVIDIA_SKILLSPECTOR','version':'2.11.2','mode':'STATIC_NO_LLM','status':'PASS','analysisComplete':True,'reportHash':H,'severity':'LOW','exitCode':0},'verdict':'APPROVED','approvalRef':'a','approvedBy':'o','approvedAt':'2026-10-01T00:00:00Z'},True,'clean approved scan'),
('schema-project-state.json',{'schemaVersion':'2','project':{'id':'p','name':'x','mode':'greenfield'},'readiness':'READY','readinessSummary':{'blockingUnknowns':['u'],'unresolvedMustRequirements':[],'unapprovedTools':[],'staleRecords':[],'missingCanonicalDocs':[],'pendingApprovals':[],'blockingSpikes':[]}},False,'ready cannot have blocking summary'),
('schema-project-state.json',{'schemaVersion':'2','project':{'id':'p','name':'x','mode':'greenfield'},'readiness':'READY','unknowns':['u'],'readinessSummary':{'blockingUnknowns':[],'unresolvedMustRequirements':[],'unapprovedTools':[],'staleRecords':[],'missingCanonicalDocs':[],'pendingApprovals':[],'blockingSpikes':[]}},False,'ready cannot have unknowns'),
('schema-approval.json',{'id':'a','artifactId':'plan','owner':'o','status':'APPROVED','approver':'o','approvedAt':'2026-10-01T00:00:00Z','scope':'x','scopeRef':'s','scopeHash':H,'admissionPlanRef':'plan','admissionPlanHash':H,'artifactHash':H,'policyRevision':'p1'},True,'fully bound approval'),
('schema-approval.json',{'id':'a','artifactId':'plan','owner':'o','status':'APPROVED','approver':'o','approvedAt':'2026-10-01T00:00:00Z','scope':'x'},False,'approval without exact binding'),
('schema-mcp-surface.json',{'id':'m','targetRef':'t','protocolRevision':'2026-07-28','transport':'STDIO','serverIdentity':'x','authorizationModel':'host','maturity':'VERIFIED','verificationBasis':'STATIC','declaredAnnotationsHash':H,'verificationStatus':'PASS','evidenceRefs':['e']},False,'verified mcp needs inspected hash'),
('schema-dependency-audit.json',{'id':'d','targetRef':'t','ecosystem':'npm','analysisCompleteness':'PARTIAL','scanner':'OSV','scannerVersion':'x','resolvedDependencies':[],'scannedAt':'2026-10-01T00:00:00Z','resolutionSource':'partial'},True,'partial dependency record is valid evidence but not clean'),
('schema-tool-lifecycle-event.json',{'id':'e','subjectRef':'t','subjectKind':'TOOL','eventType':'REVIEW_REQUIRED','previousState':'AVAILABLE','newState':'STALE','source':'validator','actor':'system','occurredAt':'2026-10-01T00:00:00Z','causeRefs':['c'],'evidenceRefs':['ev'],'sequence':1},True,'lifecycle event evidence'),
]
errs=[]
for fn,obj,want,label in cases:
    got=valid(fn,obj)
    if got!=want: errs.append(f'{fn}: {label}: expected {want}, got {got}')
if errs:
    print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print(f'PASS: {len(cases)} adversarial lifecycle/schema invariant cases')
