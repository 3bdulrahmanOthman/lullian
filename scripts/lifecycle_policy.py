#!/usr/bin/env python3
"""Single source of truth for tool lifecycle transition legality.

Consumed by validate_tool_lifecycle.py, validate_project_state.py, and
verify_admission.py so that no admission path can apply different
transition rules than the lifecycle validator.

Terminal-state rule (fail-closed): REMOVED is fully terminal and has no
outgoing transitions. QUARANTINED can only leave toward REMOVED or an
explicit human-review chain (REQUIRES_REVIEW -> PENDING_REVIEW ->
PENDING_INSTALLATION -> PENDING_VERIFICATION -> AVAILABLE); there is no
direct or derived shortcut from a terminal/review state to AVAILABLE.

Every event that changes effective state must record actor, source, a
cause or evidence reference, a compatible eventType, and a monotonically
numbered chain per subject.
"""
from __future__ import annotations

STATES = {
    'CANDIDATE', 'PENDING_REVIEW', 'PENDING_INSTALLATION', 'PENDING_VERIFICATION',
    'AVAILABLE', 'STALE', 'REQUIRES_REVIEW', 'QUARANTINED', 'REMOVED',
}
TERMINAL_STATES = {'REMOVED'}

ALLOWED_TRANSITIONS = {
    'CANDIDATE': {'CANDIDATE', 'PENDING_REVIEW', 'QUARANTINED', 'REMOVED'},
    'PENDING_REVIEW': {'PENDING_REVIEW', 'PENDING_INSTALLATION', 'QUARANTINED', 'REMOVED'},
    'PENDING_INSTALLATION': {'PENDING_INSTALLATION', 'PENDING_VERIFICATION', 'QUARANTINED', 'REMOVED'},
    'PENDING_VERIFICATION': {'PENDING_VERIFICATION', 'AVAILABLE', 'STALE', 'QUARANTINED', 'REMOVED'},
    'AVAILABLE': {'AVAILABLE', 'STALE', 'REQUIRES_REVIEW', 'QUARANTINED', 'REMOVED'},
    'STALE': {'STALE', 'REQUIRES_REVIEW', 'QUARANTINED', 'REMOVED'},
    'REQUIRES_REVIEW': {'REQUIRES_REVIEW', 'PENDING_REVIEW', 'PENDING_INSTALLATION', 'QUARANTINED', 'REMOVED'},
    'QUARANTINED': {'QUARANTINED', 'REMOVED', 'REQUIRES_REVIEW'},
    'REMOVED': {'REMOVED'},
}

EVENT_STATE_REQUIREMENTS = {
    'DRIFT_DETECTED': {'STALE', 'REQUIRES_REVIEW'},
    'APPROVAL_EXPIRED': {'REQUIRES_REVIEW', 'QUARANTINED'},
    'APPROVAL_REVOKED': {'REQUIRES_REVIEW', 'QUARANTINED'},
    'SCOPE_CHANGED': {'STALE', 'REQUIRES_REVIEW'},
    'DEPENDENCY_CHANGED': {'STALE', 'REQUIRES_REVIEW'},
    'MCP_SURFACE_CHANGED': {'STALE', 'REQUIRES_REVIEW'},
    'SCANNER_TRUST_CHANGED': {'REQUIRES_REVIEW', 'QUARANTINED'},
    'INSTALLATION_MISMATCH': {'QUARANTINED', 'REQUIRES_REVIEW'},
    'SECURITY_REVIEW_UPDATED': {'PENDING_REVIEW', 'REQUIRES_REVIEW', 'PENDING_INSTALLATION'},
    'ADMISSION_CREATED': {'PENDING_REVIEW', 'PENDING_INSTALLATION'},
    'INSTALLATION_RECORDED': {'PENDING_VERIFICATION', 'AVAILABLE'},
    'VERIFICATION_PASSED': {'AVAILABLE'},
    'VERIFICATION_FAILED': {'PENDING_VERIFICATION', 'QUARANTINED', 'REQUIRES_REVIEW'},
    'QUARANTINED': {'QUARANTINED'},
    'REMOVED': {'REMOVED'},
    'REVIEW_REQUIRED': {'REQUIRES_REVIEW', 'PENDING_REVIEW'},
}


def transition_legal(previous_state, new_state) -> bool:
    return new_state in ALLOWED_TRANSITIONS.get(previous_state, set())


def event_errors(event) -> list[str]:
    """Structural/semantic errors for a single lifecycle event (no subject lookup)."""
    eid = event.get('id', '<unnamed>')
    errs = []
    if event.get('previousState') not in STATES or event.get('newState') not in STATES:
        errs.append(f'event {eid}: invalid lifecycle state')
    elif not transition_legal(event.get('previousState'), event.get('newState')):
        errs.append(f"event {eid}: illegal transition {event.get('previousState')} -> {event.get('newState')}")
    if not event.get('actor') or not event.get('source'):
        errs.append(f'event {eid}: actor/source required')
    if not event.get('causeRefs') and not event.get('evidenceRefs'):
        errs.append(f'event {eid}: causeRefs or evidenceRefs required')
    required = EVENT_STATE_REQUIREMENTS.get(event.get('eventType'))
    if required and event.get('newState') not in required:
        errs.append(f"event {eid}: eventType {event.get('eventType')} incompatible with newState {event.get('newState')}")
    return errs


def chain_errors(events) -> list[str]:
    """Sequence, continuity, and transition errors for one subject's event list.

    Fails closed on any malformed entry; never raises on malformed input.
    """
    errs = []
    clean = [e for e in events if isinstance(e, dict)]
    if len(clean) != len(events):
        errs.append('event chain contains a non-object entry')
    ordered = sorted(clean, key=lambda e: (e.get('sequence', 0), e.get('occurredAt', '')))
    seq = [e.get('sequence') for e in ordered]
    if seq != list(range(1, len(seq) + 1)):
        errs.append('event sequence must start at 1 with no gaps/duplicates')
    for a, c in zip(ordered, ordered[1:]):
        if a.get('newState') != c.get('previousState'):
            errs.append(f'event chain broken between {a.get("id", "<unnamed>")} and {c.get("id", "<unnamed>")}')
    for e in clean:
        errs.extend(event_errors(e))
    return errs


def derived_state_from_events(events) -> str | None:
    """Latest recorded state for a subject, or None when the chain is invalid.

    An invalid chain never yields a state; callers must fail closed.
    """
    if chain_errors(events):
        return None
    ordered = sorted((e for e in events if isinstance(e, dict)),
                     key=lambda e: (e.get('sequence', 0), e.get('occurredAt', '')))
    return ordered[-1].get('newState') if ordered else None
