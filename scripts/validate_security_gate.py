#!/usr/bin/env python3
from pathlib import Path
import contextlib, io, json, hashlib, subprocess, sys, tempfile
from unittest import mock
import security_gate
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def make_env(report, *, tamper=False, rc=0, version='SkillSpector 2.11.2', wrong_hash=False, timeout=False):
 td=tempfile.TemporaryDirectory(prefix='lullian-gate-test-'); base=Path(td.name)
 target=base/'candidate'; target.mkdir(); (target/'SKILL.md').write_text('# safe\n',encoding='utf8')
 scanner=base/'skillspector'; scanner.write_bytes(b'trusted-test-scanner'); scanner.chmod(0o755)
 trust=base/'scanner-trust.json'; digest=sha(scanner)
 trust.write_text(json.dumps({'scanner':'NVIDIA_SKILLSPECTOR','publisher':'NVIDIA','version':'2.11.2','releaseRef':'test-release','executableHash':'0'*64 if wrong_hash else digest,'verifiedBy':'test','verifiedAt':'2026-10-02T00:00:00Z','binaryPathPolicy':'PINNED_FILE','trustStatus':'TRUSTED','trustBasis':'VERIFIED_EXECUTABLE','verificationEvidenceRefs':['test-evidence']}),encoding='utf8')
 out=base/'packet.json'
 def which(_): return str(scanner)
 def fake_run(cmd,**kwargs):
  if cmd[1:]==['--version']: return type('R',(),{'stdout':version,'stderr':'','returncode':0})()
  if timeout: raise subprocess.TimeoutExpired(cmd,1)
  stage=Path(cmd[cmd.index('scan')+1]); report_path=Path(cmd[cmd.index('--output')+1])
  if tamper: (stage/'tampered.txt').write_text('x',encoding='utf8')
  report_path.write_text(json.dumps(report),encoding='utf8'); return type('R',(),{'stdout':'','stderr':'','returncode':rc})()
 return td,base,target,scanner,trust,out,which,fake_run

def invoke(report, **kw):
 td,base,target,scanner,trust,out,which,fake_run=make_env(report,**kw)
 buf=io.StringIO()
 with mock.patch.object(security_gate.shutil,'which',which),mock.patch.object(security_gate.subprocess,'run',fake_run),mock.patch.object(sys,'argv',['security_gate.py',str(target),'--scanner-trust',str(trust),'--output',str(out)]),contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
  code=security_gate.main()
 return td,code,buf.getvalue(),out

safe={'risk_assessment':{'severity':'LOW','recommendation':'SAFE','score':1},'analysis_completeness':{'is_complete':True},'issues':[]}
medium={'risk_assessment':{'severity':'MEDIUM','recommendation':'CAUTION','score':25},'analysis_completeness':{'is_complete':True},'issues':['review']}
high={'risk_assessment':{'severity':'HIGH','recommendation':'DO_NOT_INSTALL','score':90},'analysis_completeness':{'is_complete':True},'issues':['poison']}
incomplete={'risk_assessment':{'severity':'LOW','recommendation':'SAFE','score':1},'analysis_completeness':{'is_complete':False,'partially_inspected_files':['x']},'issues':[]}
errors=[]
for name,want,rep,kw in [('safe',0,safe,{}),('medium',1,medium,{}),('high',1,high,{}),('incomplete',3,incomplete,{'rc':1}),('scanner-error',3,safe,{'rc':2}),('old-scanner',3,safe,{'version':'SkillSpector 2.10.9'}),('patch-version',3,safe,{'version':'SkillSpector 2.11.20'}),('prerelease-version',3,safe,{'version':'SkillSpector 2.11.2-beta'}),('new-version',3,safe,{'version':'SkillSpector 2.12.0'}),('wrong-scanner-hash',3,safe,{'wrong_hash':True}),('snapshot-tamper',1,safe,{'tamper':True}),('scanner-timeout',3,safe,{'timeout':True})]:
 td,code,out,_=invoke(rep,**kw); td.cleanup()
 if code!=want: errors.append(f'{name}: expected {want}, got {code}\n{out}')
# Scanner trust is mandatory.
td,base,target,scanner,trust,out,which,fake_run=make_env(safe)
trust.unlink(); buf=io.StringIO()
with mock.patch.object(security_gate.shutil,'which',which),mock.patch.object(security_gate.subprocess,'run',fake_run),mock.patch.object(sys,'argv',['security_gate.py',str(target),'--scanner-trust',str(trust),'--output',str(out)]),contextlib.redirect_stdout(buf): code=security_gate.main()
if code!=3: errors.append('missing trust record did not fail closed')
td.cleanup()
# Admission evidence is independently verified while temp dir exists.
td,code,stdout,packet=invoke(safe)
if code==0:
 vr=subprocess.run([sys.executable,str(ROOT/'scripts/verify_admission.py'),str(packet)],capture_output=True,text=True)
 if vr.returncode!=0: errors.append('clean admission packet failed verification: '+vr.stdout+vr.stderr)
 meta=json.loads(packet.read_text()); raw=packet.parent/meta['evidenceDir']/'raw-skillspector-report.json'; raw.write_text('{"risk_assessment":{"severity":"HIGH","recommendation":"DO_NOT_INSTALL"}}',encoding='utf8')
 vr=subprocess.run([sys.executable,str(ROOT/'scripts/verify_admission.py'),str(packet)],capture_output=True,text=True)
 if vr.returncode==0: errors.append('tampered raw report was accepted')
td.cleanup()
if errors:
 print('FAIL'); [print(' -',e) for e in errors]; sys.exit(1)
print('PASS: security admission tests (trusted scanner, exact hash, snapshot integrity, incomplete/error/timeout, evidence verification)')
