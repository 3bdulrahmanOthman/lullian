# Lifecycle and State

## Tool lifecycle

`CANDIDATE -> PENDING_REVIEW -> PENDING_INSTALLATION -> PENDING_VERIFICATION -> AVAILABLE`

Material change: `AVAILABLE -> STALE -> REQUIRES_REVIEW -> PENDING_INSTALLATION/PENDING_VERIFICATION -> AVAILABLE`.

Security revocation: `AVAILABLE -> QUARANTINED -> REMOVED`.

`BLOCKED` and `CAUTION_HUMAN_REVIEW` are dispositions/reasons, not lifecycle states.

`AVAILABLE` is derived from the evidence graph. Legacy status fields are compatibility projections only.

## Approval lifecycle

`PENDING | APPROVED | EXPIRED | REVOKED | REJECTED | SUPERSEDED`. Approval binds to exact admission plan and scope hashes and may expire or require re-approval.

## Events

State-changing events record previous/new state, source/actor, causal references, evidence references, timestamp, and sequence.
