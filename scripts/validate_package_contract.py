#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
errs=[]
manifest=json.loads((ROOT/'lullian.manifest.json').read_text())
# Exact top-level allowlist; release artifact must remain portable and code-free except approved scripts.
allowed_files={'SKILL.md','README.md','CHANGELOG.md','LICENSE','lullian.manifest.json'}
# Repository-only governance files: kept in the repo for evidence and agent productivity, never
# shipped in the public skill artifact. Internal audit reports stay repository-only (they are
# gitignored); everything not in this set or the allowlist still fails closed.
repo_only_files={'AGENTS.md','.gitignore','.gitattributes','CONTRACT-MATRIX.md','FORENSIC-COVERAGE.md','FORENSIC-CODE-AUDIT-v0.3.2.md','FORENSIC-CODE-AUDIT-v0.4.0.md','VALIDATION-REPORT.md','PUBLIC-PACKAGE-FINAL-v0.4.0.md','PUBLIC-RELEASE-CANDIDATE-v0.4.0.md','PRE-RELEASE-AUDIT-v0.4.0-R2.md','PRE-RELEASE-AUDIT-v0.4.0-R3.md','PRE-RELEASE-EXTERNAL-VALIDATION-v0.4.0.md','PRE-RELEASE-EXTERNAL-VALIDATION-v0.4.0-R2.md','PRE-RELEASE-EXTERNAL-VALIDATION-v0.4.0-R3.md','PRE-RELEASE-FINAL-v0.4.0.md'}
repo_only_dirs={'external-validation-evidence','external-validation-ci','docs','.github'}  # registration-only repo-only entries (public docs + brand), shipped set unchanged
repo_only=[]
allowed_dirs={'assets','references','evals','scripts'}
for p in ROOT.rglob('*'):
    rel=p.relative_to(ROOT).as_posix()
    if p.is_file():
        # Detached OMS signature sidecar is part of the distributed artifact, not package content.
        if rel=='skill.oms.sig' and not (ROOT/'.gitignore').is_file(): continue
        if rel in repo_only_files or rel.split('/')[0] in repo_only_dirs: repo_only.append(rel); continue
        if rel in allowed_files: continue
        if rel.split('/')[0] not in allowed_dirs: errs.append(f'unexpected shipped file: {rel}')
        elif rel.startswith('assets/') and not p.name.startswith('schema-'): errs.append(f'unapproved asset: {rel}')
        elif rel.startswith('references/') and p.suffix!='.md': errs.append(f'unapproved reference: {rel}')
        elif rel.startswith('evals/') and p.suffix!='.json': errs.append(f'unapproved eval file: {rel}')
        elif rel.startswith('scripts/') and p.suffix!='.py': errs.append(f'unapproved script: {rel}')
    elif rel.split('/')[0] not in allowed_dirs and rel.split('/')[0] not in repo_only_dirs: errs.append(f'unexpected shipped directory: {rel}')
# Internal audit reports: repository-only by contract. The shipped manifest must declare them.
# Repo mode (working tree with .gitignore): audit files must be present and gitignored.
# Artifact mode (no .gitignore): the same files must be absent — shipping one is a boundary breach.
internal_audit_files=['CONTRACT-MATRIX.md','FORENSIC-COVERAGE.md','FORENSIC-CODE-AUDIT-v0.3.2.md','FORENSIC-CODE-AUDIT-v0.4.0.md','VALIDATION-REPORT.md']
if sorted(manifest.get('repositoryOnlyFiles',[]))!=sorted(internal_audit_files): errs.append('manifest repositoryOnlyFiles must list exactly the five internal audit files')
if (ROOT/'.gitignore').is_file():
    gi_lines=[l.strip() for l in (ROOT/'.gitignore').read_text(encoding='utf8').splitlines() if l.strip() and not l.startswith('#')]
    import fnmatch
    def gitignored(rel):
        for pat in gi_lines:
            if '/' not in pat and fnmatch.fnmatch(Path(rel).name,pat): return True
            if fnmatch.fnmatch(rel,pat) or fnmatch.fnmatch(rel,'**/'+pat): return True
        return False
    for f in internal_audit_files:
        if not (ROOT/f).is_file(): errs.append(f'repository-only audit file missing from working tree: {f}')
        elif not gitignored(f): errs.append(f'internal audit file not ignored by .gitignore: {f}')
else:
    for f in internal_audit_files:
        if (ROOT/f).is_file(): errs.append(f'internal audit file must not be shipped in the artifact: {f}')
# Manifest exact consistency.
actual={k:sorted(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/d).glob('schema-*.json' if d=='assets' else ('*.md' if d=='references' else ('*.json' if d=='evals' else '*.py')))) for k,d in [('schemas','assets'),('references','references'),('evals','evals'),('scripts','scripts')]}
for k,v in actual.items():
    if sorted(manifest.get(k,[]))!=v: errs.append(f'manifest {k} mismatch')
for count_key,actual_key in [('schemaCount','schemas'),('scriptCount','scripts')]:
    if manifest.get('releaseGates',{}).get(count_key) != len(actual[actual_key]): errs.append(f'manifest releaseGates.{count_key} mismatch')
# Required shipped root files must exist (repo mode) and the total shipped set must match the manifest count.
for f in sorted(allowed_files):
    if not (ROOT/f).is_file(): errs.append(f'required shipped root file missing: {f}')
shipped_count=sum((ROOT/f).is_file() for f in allowed_files)+sum(len(list((ROOT/d).glob(pat))) for d,pat in [('assets','schema-*.json'),('references','*.md'),('evals','*.json'),('scripts','*.py')])
if manifest.get('packageFileCount') != shipped_count: errs.append(f'manifest packageFileCount {manifest.get("packageFileCount")} != actual shipped set {shipped_count}')
if manifest.get('evalCount') != len(json.loads((ROOT/'evals/evals.json').read_text())): errs.append('manifest evalCount mismatch with eval corpus')
if manifest.get('metamorphicCount') != len(json.loads((ROOT/'evals/metamorphic.json').read_text())): errs.append('manifest metamorphicCount mismatch')
# Version sync.
sk=(ROOT/'SKILL.md').read_text(); m=re.search(r'version:\s*"([^"]+)"',sk)
if not m or manifest.get('version')!=m.group(1): errs.append('manifest/version mismatch')
if '\\n' in ''.join((ROOT/f).read_text(errors='ignore') for f in ['README.md','CHANGELOG.md','SKILL.md']): errs.append('literal escaped newline in human-readable file')
# Schema IDs must be offline URNs and unique; forbid external refs except meta-schema declaration.
ids=set()
for p in (ROOT/'assets').glob('schema-*.json'):
 d=json.loads(p.read_text()); sid=d.get('$id','')
 if not sid.startswith('urn:lullian:schema:'): errs.append(f'{p.name}: non-offline $id {sid}')
 if sid in ids: errs.append(f'duplicate schema id {sid}')
 ids.add(sid)
 refs=[]
 def walk(x):
  if isinstance(x,dict):
   if '$ref' in x: refs.append(x['$ref'])
   for v in x.values(): walk(v)
  elif isinstance(x,list):
   for v in x: walk(v)
 walk(d)
 for ref in refs:
  if not ref.startswith('#/') and not ref.startswith('assets/'): errs.append(f'{p.name}: external/local-unmapped $ref {ref}')
# Release attestation is an external sidecar; do not package a self-attesting payload.
for p in ROOT.rglob('*'):
 if p.is_file() and p.name != 'schema-release-attestation.json' and ('attestation' in p.stem.lower() or 'signature' in p.stem.lower()):
  errs.append(f'release attestation/signature payload must remain external: {p.relative_to(ROOT)}')
# Noise and hidden files. Repository-only dotfiles (e.g. .gitignore) are a distinct class:
# they are never shipped, but their presence in the working tree is expected, not noise.
for p in ROOT.rglob('*'):
 rel=p.relative_to(ROOT).as_posix()
 if p.is_file() and rel not in repo_only_files and rel.split('/')[0] not in repo_only_dirs and ('__pycache__' in p.parts or p.suffix in {'.pyc','.pyo'} or p.name.startswith('.') or p.name=='.DS_Store'): errs.append(f'shipping noise: {rel}')
for rel in sorted(repo_only): print(f'repository-only (not shipped): {rel}')
if errs:
 print('FAIL'); [print(' -',e) for e in errs]; sys.exit(1)
print('PASS: exact package allowlist, manifest parity, offline schemas, version sync, and release hygiene')
