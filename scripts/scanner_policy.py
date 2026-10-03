#!/usr/bin/env python3
"""Single source of truth for the exact trusted-scanner admission policy.

Policy (manifest securityPolicy: "exact-trusted-scanner-or-blocked"):
a scanner trust record claiming TRUSTED status must identify the exact
validated scanner baseline — identity, publisher, version, and pinned
binary-path policy — and must carry verification evidence. Any other
scanner version, prerelease, publisher, or missing evidence fails closed
and can never back a PASS scan or an AVAILABLE tool.

Consumed by security_gate.py (scan-time trust), verify_admission.py
(legacy packet and state-bundle verification), validate_project_state.py
and validate_tool_admission.py (state-bundle admission path).
"""
from __future__ import annotations

EXACT_SCANNER = 'NVIDIA_SKILLSPECTOR'
EXACT_PUBLISHER = 'NVIDIA'
EXACT_VERSION = '2.11.2'
EXACT_BINARY_PATH_POLICY = 'PINNED_FILE'
EXACT_VERSION_TUPLE = tuple(int(part) for part in EXACT_VERSION.split('.'))

REQUIRED_TRUST_FIELDS = (
    'scanner', 'publisher', 'version', 'releaseRef', 'executableHash',
    'binaryPathPolicy', 'verifiedBy', 'verifiedAt', 'trustStatus', 'trustBasis',
)


def is_trusted(record) -> bool:
    return isinstance(record, dict) and record.get('trustStatus') == 'TRUSTED'


def trust_record_errors(record) -> list[str]:
    """Errors for a trust record claiming TRUSTED status; empty means policy-valid.

    Records not claiming TRUSTED status are out of scope here (they may exist
    as untrusted/prerelease observations) but can never satisfy this policy.
    """
    if not isinstance(record, dict):
        return ['scanner trust record must be an object']
    rid = record.get('id', '<unnamed>')
    if not is_trusted(record):
        return [f'scannerTrust {rid}: trustStatus must be TRUSTED to satisfy the exact-scanner policy']
    errs = []
    for field in REQUIRED_TRUST_FIELDS:
        if not record.get(field):
            errs.append(f'scannerTrust {rid}: missing required field {field}')
    if record.get('scanner') != EXACT_SCANNER:
        errs.append(f'scannerTrust {rid}: scanner must be exactly {EXACT_SCANNER}')
    if record.get('publisher') != EXACT_PUBLISHER:
        errs.append(f'scannerTrust {rid}: publisher must be exactly {EXACT_PUBLISHER}')
    if record.get('version') != EXACT_VERSION:
        errs.append(f'scannerTrust {rid}: version must be exactly {EXACT_VERSION} (no inherited trust for other releases)')
    if record.get('binaryPathPolicy') != EXACT_BINARY_PATH_POLICY:
        errs.append(f'scannerTrust {rid}: binaryPathPolicy must be {EXACT_BINARY_PATH_POLICY}')
    if not record.get('verificationEvidenceRefs'):
        errs.append(f'scannerTrust {rid}: verification evidence references required')
    return errs
