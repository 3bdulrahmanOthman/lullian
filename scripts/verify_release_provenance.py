#!/usr/bin/env python3
"""Verify an external release attestation against a concrete artifact digest."""
from pathlib import Path
import hashlib,json,sys

def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def main():
 if len(sys.argv)!=3: print('usage: verify_release_provenance.py ARTIFACT ATTESTATION.json'); return 2
 artifact=Path(sys.argv[1]); att=Path(sys.argv[2])
 if not artifact.is_file() or not att.is_file(): print('FAIL: artifact/attestation missing'); return 1
 try:d=json.loads(att.read_text(encoding='utf8'))
 except Exception as e: print('FAIL: invalid attestation',e); return 1
 digest=sha(artifact)
 if d.get('subjectType') not in {'PACKAGE','ARCHIVE','DIRECTORY'}: print('FAIL: invalid subjectType'); return 1
 if d.get('subjectDigest')!=digest: print(f'FAIL: subject digest mismatch expected={digest} got={d.get("subjectDigest")}'); return 1
 if d.get('verificationStatus')!='VERIFIED': print('FAIL: attestation is not VERIFIED'); return 1
 print('PASS: external release attestation is bound to the exact artifact digest'); return 0
if __name__=='__main__': sys.exit(main())
