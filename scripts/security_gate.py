#!/usr/bin/env python3
"""Fail-closed admission gate for third-party Skills/MCPs.

Security design:
- candidate is copied to a fresh symlink-free snapshot before scanning;
- scanner executable must match a separately trusted scanner record by exact SHA-256 and version;
- scanner runs with scrubbed Python/user-site environment and a hard timeout;
- raw scanner report, snapshot manifest, and hashes are persisted;
- output packet binds verdict to those evidence artifacts;
- exit 3 means security identity/infrastructure is unverified, exit 1 means a security block/caution,
  exit 0 means the scan itself is clean and the next state is pending explicit human approval.
The target is never executed by this helper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import tarfile
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scanner_policy
# Exact scanner baseline comes from the shared scanner_policy module (single source of truth).
MIN_SUPPORTED_VERSION = scanner_policy.EXACT_VERSION_TUPLE
EXACT_SUPPORTED_VERSION = scanner_policy.EXACT_VERSION
MAX_FILES = 5000
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DEPTH = 20
MAX_REPORT_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT = 300


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_version(raw: str | None) -> tuple[int, int, int] | None:
    import re
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', raw or '')
    return tuple(map(int, m.groups())) if m else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _assert_no_symlink_components(path: Path, label: str) -> None:
    raw = path.expanduser()
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    current = raw.anchor and Path(raw.anchor) or Path()
    for part in raw.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError(f'{label} path contains symlink component: {current}')

def resolved_no_symlink(path: Path, label: str, *, must_exist: bool = True) -> Path:
    raw = path.expanduser()
    _assert_no_symlink_components(raw, label)
    if raw.is_symlink():
        raise ValueError(f'{label} must not be a symlink: {raw}')
    resolved = raw.resolve(strict=must_exist)
    return resolved


def ensure_not_nested(a: Path, b: Path, label: str) -> None:
    try:
        b.relative_to(a)
    except ValueError:
        return
    raise ValueError(f'{label} must not be inside candidate target: {b}')


def inspect_source(target: Path) -> tuple[int, int, int]:
    """Return (file_count, total_bytes, max_depth), rejecting symlinks/special files/oversize files."""
    if target.is_file():
        st = target.stat()
        if not stat.S_ISREG(st.st_mode):
            raise ValueError('target is not a regular file')
        if st.st_size > MAX_FILE_BYTES:
            raise ValueError(f'target file exceeds {MAX_FILE_BYTES} bytes')
        return 1, st.st_size, 0
    files = 0; total = 0; depth_max = 0
    for root, dirs, names in os.walk(target, topdown=True, followlinks=False):
        rp = Path(root)
        depth = len(rp.relative_to(target).parts)
        depth_max = max(depth_max, depth)
        if depth > MAX_DEPTH:
            raise ValueError('candidate exceeds maximum directory depth')
        safe_dirs = []
        for name in dirs:
            p = rp / name
            if p.is_symlink():
                raise ValueError(f'symlink is forbidden in candidate: {p.relative_to(target)}')
            st = p.stat(follow_symlinks=False)
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError(f'non-directory entry found in directory set: {p.relative_to(target)}')
            safe_dirs.append(name)
        dirs[:] = safe_dirs
        for name in names:
            p = rp / name
            if p.is_symlink():
                raise ValueError(f'symlink is forbidden in candidate: {p.relative_to(target)}')
            st = p.stat(follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError(f'special/non-regular file forbidden: {p.relative_to(target)}')
            files += 1
            total += st.st_size
            if files > MAX_FILES:
                raise ValueError(f'candidate exceeds {MAX_FILES} files')
            if st.st_size > MAX_FILE_BYTES:
                raise ValueError(f'candidate contains file over {MAX_FILE_BYTES} bytes: {p.relative_to(target)}')
            if total > MAX_TOTAL_BYTES:
                raise ValueError(f'candidate exceeds {MAX_TOTAL_BYTES} total bytes')
    return files, total, depth_max


def tree_manifest(root: Path) -> dict:
    entries = []
    if root.is_file():
        entries.append({'path': root.name, 'sha256': sha256_file(root), 'size': root.stat().st_size})
    else:
        for p in sorted(root.rglob('*'), key=lambda x: x.as_posix()):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            entries.append({'path': rel, 'sha256': sha256_file(p), 'size': p.stat().st_size})
    h = hashlib.sha256()
    for e in entries:
        h.update((e['path'] + '\0' + e['sha256'] + '\0' + str(e['size']) + '\n').encode())
    return {'algorithm': 'SHA-256', 'entries': entries, 'contentHash': h.hexdigest(), 'fileCount': len(entries), 'totalBytes': sum(e['size'] for e in entries)}


def copy_snapshot(source: Path, destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=False)
    if source.is_file():
        shutil.copy2(source, destination / source.name)
    else:
        for root, dirs, files in os.walk(source, topdown=True, followlinks=False):
            src_root = Path(root); rel = src_root.relative_to(source); dst_root = destination / rel
            dst_root.mkdir(parents=True, exist_ok=True)
            for d in dirs:
                sp = src_root / d
                if sp.is_symlink(): raise ValueError(f'symlink appeared during snapshot: {sp}')
                (dst_root / d).mkdir()
            for f in files:
                sp = src_root / f
                if sp.is_symlink(): raise ValueError(f'symlink appeared during snapshot: {sp}')
                st = sp.stat(follow_symlinks=False)
                if not stat.S_ISREG(st.st_mode): raise ValueError(f'special file appeared during snapshot: {sp}')
                shutil.copy2(sp, dst_root / f)
    return tree_manifest(destination)


def scrubbed_env(scanner: Path, sandbox_home: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ['PYTHONPATH','PYTHONHOME','PYTHONUSERBASE','VIRTUAL_ENV','CONDA_PREFIX','CONDA_DEFAULT_ENV','NODE_OPTIONS','RUBYOPT','PERL5OPT']:
        env.pop(key, None)
    env['HOME'] = str(sandbox_home)
    env['USERPROFILE'] = str(sandbox_home)
    env['XDG_CONFIG_HOME'] = str(sandbox_home / 'config')
    env['XDG_CACHE_HOME'] = str(sandbox_home / 'cache')
    # Keep PATH, but put the verified scanner directory first; hash verification remains the trust decision.
    env['PATH'] = str(scanner.parent) + os.pathsep + os.pathsep.join(p for p in env.get('PATH','').split(os.pathsep) if p and Path(p).resolve() != scanner.parent.resolve())
    return env


def load_trust(path: Path) -> dict:
    d = json.loads(path.read_text(encoding='utf-8'))
    required = ['scanner','publisher','version','releaseRef','executableHash','binaryPathPolicy','verifiedBy','verifiedAt','trustStatus','trustBasis']
    missing = [x for x in required if not d.get(x)]
    if missing: raise ValueError('scanner trust record missing: ' + ', '.join(missing))
    if d['trustStatus'] != 'TRUSTED': raise ValueError('scanner trust record is not TRUSTED')
    if not isinstance(d.get('verificationEvidenceRefs'), list) or not d.get('verificationEvidenceRefs'):
        raise ValueError('trusted scanner requires non-empty verificationEvidenceRefs')
    if d['scanner'] != 'NVIDIA_SKILLSPECTOR' or d['publisher'] != 'NVIDIA':
        raise ValueError('scanner trust record is not for NVIDIA SkillSpector')
    if d['version'] != EXACT_SUPPORTED_VERSION:
        raise ValueError(f'trust record must pin exact supported version {EXACT_SUPPORTED_VERSION}')
    if d['binaryPathPolicy'] != 'PINNED_FILE':
        raise ValueError('scanner trust record must use PINNED_FILE')
    if not isinstance(d['executableHash'], str) or len(d['executableHash']) != 64:
        raise ValueError('scanner trust executableHash must be SHA-256')
    return d


def check_scanner(scanner_arg: str, trust: dict) -> tuple[Path, str]:
    found = shutil.which(scanner_arg)
    if not found:
        raise FileNotFoundError('NVIDIA SkillSpector is unavailable')
    scanner_path = Path(found)
    if scanner_path.is_symlink():
        raise ValueError('scanner executable is a symlink')
    scanner_path = scanner_path.resolve(strict=True)
    if not scanner_path.is_file(): raise ValueError('scanner is not a regular file')
    digest = sha256_file(scanner_path)
    if digest.lower() != trust['executableHash'].lower():
        raise ValueError('scanner executable SHA-256 does not match trusted scanner record')
    with tempfile.TemporaryDirectory(prefix='lullian-scanner-home-') as home:
        sandbox_home = Path(home)
        vr = subprocess.run(
            [str(scanner_path), '--version'],
            capture_output=True,
            text=True,
            timeout=30,
            env=scrubbed_env(scanner_path, sandbox_home),
        )
    raw=(vr.stdout+' '+vr.stderr).strip()
    import re
    exact_output = re.fullmatch(r'SkillSpector\s+v?'+re.escape(EXACT_SUPPORTED_VERSION), raw, flags=re.IGNORECASE)
    ver=parse_version(raw)
    if vr.returncode != 0 or ver != MIN_SUPPORTED_VERSION or not exact_output:
        raise ValueError(f'scanner version check failed: expected exact {EXACT_SUPPORTED_VERSION}, got {raw!r}')
    return scanner_path, digest


def classify(report: dict, scanner_rc: int) -> tuple[str, str, bool]:
    risk=report.get('risk_assessment') or {}
    sev=str(risk.get('severity') or report.get('risk_severity') or 'UNKNOWN').upper()
    rec=str(risk.get('recommendation') or report.get('risk_recommendation') or '').upper()
    comp=report.get('analysis_completeness') or {}
    incomplete=(comp.get('is_complete') is False or report.get('execution_successful') is False or bool(comp.get('entirely_uninspected_files')) or bool(comp.get('partially_inspected_files')))
    issues=report.get('issues') or report.get('findings') or []
    if incomplete or scanner_rc != 0:
        return 'BLOCKED_SECURITY_UNVERIFIED','',False
    if sev in {'CRITICAL','HIGH'} or rec == 'DO_NOT_INSTALL':
        return 'BLOCKED_SECURITY','',True
    if sev == 'MEDIUM' or rec == 'CAUTION' or issues:
        return 'CAUTION_HUMAN_REVIEW','',True
    if sev == 'LOW' and rec == 'SAFE':
        return 'PENDING_USER_APPROVAL','',True
    return 'BLOCKED_SECURITY_UNVERIFIED','',False


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--scanner-trust', required=True)
    ap.add_argument('--scanner-bin', default='skillspector')
    ap.add_argument('--output', required=True, help='JSON summary output; raw evidence is written beside it')
    ap.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument('--allow-medium', action='store_true', help='Return 0 for CAUTION only; never approves installation')
    args=ap.parse_args()
    output=Path(args.output).expanduser()
    try:
        target=resolved_no_symlink(Path(args.target),'target')
        trust_path=resolved_no_symlink(Path(args.scanner_trust),'scanner trust record')
        _assert_no_symlink_components(output, 'output')
        if output.expanduser().exists() and output.expanduser().is_symlink():
            raise ValueError('output must not be a symlink')
        output_abs=output.expanduser().resolve(strict=False)
        output_parent=output_abs.parent
        ensure_not_nested(target, output_abs, 'output')
        ensure_not_nested(target, trust_path, 'scanner trust record')
        trust=load_trust(trust_path)
        scanner, scanner_hash=check_scanner(args.scanner_bin, trust)
        ensure_not_nested(target, scanner, 'scanner executable')
    except (OSError,ValueError,FileNotFoundError,json.JSONDecodeError) as e:
        print('BLOCKED_SECURITY_UNVERIFIED:', e)
        return 3

    try:
        inspect_source(target)
        source_before=tree_manifest(target) 
    except Exception as e:
        print('BLOCKED_SECURITY_UNVERIFIED:', e); return 3

    evidence_dir=output_parent / (output_abs.stem + '.evidence')
    _assert_no_symlink_components(evidence_dir, 'evidence')
    if evidence_dir.exists():
        print('BLOCKED_SECURITY_UNVERIFIED: evidence directory already exists; choose a fresh output path')
        return 3
    evidence_dir.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='lullian-security-stage-') as td:
        stage=Path(td)/'snapshot'
        try:
            snapshot=copy_snapshot(target,stage)
            source_after=tree_manifest(target)
            if source_before['contentHash'] != source_after['contentHash']:
                raise ValueError('source target changed while staging; aborting admission')
            scanner_trust_hash=sha256_file(trust_path)
            trust_copy=evidence_dir/'scanner-trust.json'
            shutil.copy2(trust_path, trust_copy)
            # Create a deterministic, read-only evidence archive of the exact pre-scan snapshot.
            archive=evidence_dir/'snapshot.tar'
            with tarfile.open(archive, 'w') as tf:
                for entry in snapshot['entries']:
                    src=stage/entry['path']
                    info=tf.gettarinfo(str(src), arcname=entry['path'])
                    info.mtime=0; info.uid=0; info.gid=0; info.uname=''; info.gname=''
                    with src.open('rb') as fh:
                        tf.addfile(info, fh)
            archive_hash=sha256_file(archive)
            snapshot_manifest={
                'target':target.name,'capturedAt':utc_now(),'contentHash':snapshot['contentHash'],
                'snapshotArchiveHash':archive_hash,'snapshotArchiveRef':'snapshot.tar',
                'scannerTrustHash':scanner_trust_hash,'sourceRef':target.name,
                'changePolicy':'RESCAN_ON_MATERIAL_CHANGE','fileCount':snapshot['fileCount'],'totalBytes':snapshot['totalBytes']
            }
            (evidence_dir/'snapshot-manifest.json').write_text(json.dumps(snapshot_manifest,indent=2)+'\n',encoding='utf8')
            scan_dir=stage / '._lullian_scan'
            scan_dir.mkdir()
            raw_report=scan_dir/'report.json'
            cmd=[str(scanner),'scan',str(stage),'--no-llm','--format','json','--output',str(raw_report),'--fail-on-incomplete']
            invocation_hash=sha256_bytes(json.dumps(cmd,separators=(',',':')).encode())
            sandbox_home=Path(td)/'home'; sandbox_home.mkdir()
            env=scrubbed_env(scanner,sandbox_home)
            try:
                run=subprocess.run(cmd,text=True,capture_output=True,env=env,timeout=max(1,args.timeout),start_new_session=True)
                rc=run.returncode
            except subprocess.TimeoutExpired:
                print('BLOCKED_SECURITY_UNVERIFIED: scanner timed out')
                return 3
            if not raw_report.exists():
                print('BLOCKED_SECURITY_UNVERIFIED: SkillSpector did not produce a report')
                return 3
            if raw_report.stat().st_size > MAX_REPORT_BYTES:
                print('BLOCKED_SECURITY_UNVERIFIED: scanner report exceeds output bound')
                return 3
            raw_bytes=raw_report.read_bytes(); report_hash=sha256_bytes(raw_bytes)
            try: report=json.loads(raw_bytes.decode('utf8'))
            except Exception as e:
                print('BLOCKED_SECURITY_UNVERIFIED: invalid scanner report:',e); return 3
            snapshot_after=tree_manifest(stage)
            # Exclude internal report from candidate integrity comparison by hashing snapshot before/after through a filtered view.
            filtered_entries=[e for e in snapshot_after['entries'] if not e['path'].startswith('._lullian_scan/')]
            h=hashlib.sha256()
            for e in filtered_entries: h.update((e['path']+'\0'+e['sha256']+'\0'+str(e['size'])+'\n').encode())
            staged_content_after=h.hexdigest()
            if staged_content_after != snapshot['contentHash']:
                print('BLOCKED_SECURITY: reviewed snapshot changed during scan'); return 1
            # Persist the raw report outside the staged tree.
            (evidence_dir/'raw-skillspector-report.json').write_bytes(raw_bytes)
            verdict,_,complete=classify(report,rc)
            risk=report.get('risk_assessment') or {}
            severity=str(risk.get('severity') or report.get('risk_severity') or 'UNKNOWN').upper()
            comp=report.get('analysis_completeness') or {}
            incomplete=(comp.get('is_complete') is False or report.get('execution_successful') is False or bool(comp.get('entirely_uninspected_files')) or bool(comp.get('partially_inspected_files')))
            status='INCOMPLETE' if incomplete else ('ERROR' if rc!=0 else ('PASS' if verdict=='PENDING_USER_APPROVAL' else 'FINDINGS'))
            analysis_completeness='COMPLETE' if complete and not incomplete else ('PARTIAL' if comp else 'UNRESOLVED')
            evidence={'id':'scan-'+report_hash[:12],'target':target.name,'scannerTrustRef':trust_path.name,'scannerTrustHash':scanner_trust_hash,'targetHash':snapshot['contentHash'],'reportHash':report_hash,'reportRef':'raw-skillspector-report.json','snapshotRef':'snapshot-manifest.json','mode':'STATIC_NO_LLM','status':status,'scannedAt':utc_now(),'scannerExitCode':rc,'analysisComplete':complete,'analysisCompleteness':analysis_completeness,'analysisMode':'STATIC_NO_LLM','invocationHash':invocation_hash,'severity':severity}
            score=risk.get('score',report.get('risk_score'))
            if score is not None: evidence['score']=score
            evidence['snapshotArchiveHash']=archive_hash; evidence['snapshotArchiveRef']='snapshot.tar'
            (evidence_dir/'scan-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8')
            packet={'schemaVersion':'1','createdAt':utc_now(),'target':str(target),'scannerTrustRef':'scanner-trust.json','scannerTrustHash':scanner_trust_hash,'scannerExecutableHash':scanner_hash,'scannerVersion':trust['version'],'verdict':verdict,'analysisComplete':complete,'evidenceDir':evidence_dir.name,'rawReportHash':report_hash,'snapshotHash':snapshot['contentHash'],'snapshotArchiveHash':archive_hash,'scanEvidenceHash':sha256_file(evidence_dir/'scan-evidence.json'),'snapshotManifestHash':sha256_file(evidence_dir/'snapshot-manifest.json'),'approval':'REQUIRED'}
            # Normalize output summary and keep all evidence local to packet directory.
            output_abs.write_text(json.dumps(packet,indent=2)+'\n',encoding='utf8')
            print(json.dumps(packet,indent=2))
            if verdict=='PENDING_USER_APPROVAL' or (args.allow_medium and verdict=='CAUTION_HUMAN_REVIEW'):
                return 0
            if verdict=='BLOCKED_SECURITY_UNVERIFIED': return 3
            return 1
        except (OSError,ValueError) as e:
            print('BLOCKED_SECURITY_UNVERIFIED:', e); return 3

if __name__=='__main__': sys.exit(main())
