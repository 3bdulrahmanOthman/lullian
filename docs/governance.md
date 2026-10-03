# Tool, Skill, and MCP Governance

Lullian's most distinctive subsystem is **fail-closed admission governance** for third-party Skills, MCP servers, and CLI tools. Nothing external becomes usable because it was mentioned, recommended, or declared — it becomes usable only through the admission pipeline below.

## The admission pipeline

```text
Exact Resolution → Identity + Integrity → Provenance → Dependency/Scope/MCP Review
→ Security Review → Admission Plan → Explicit Approval → External Installation
→ Post-install Verification → AVAILABLE (derived)
```

Each arrow is a gate with recorded evidence:

1. **Exact resolution** — the candidate is pinned to a specific name/version/source; fuzzy "latest" references are not admissible.
2. **Identity + integrity** — the artifact is hashed; every later check binds to that exact hash.
3. **Provenance** — where the artifact came from and what vouches for it, recorded as structured provenance.
4. **Dependency / scope / MCP review** — declared dependencies, requested scopes, and MCP surface are reviewed. MCP declarations are treated as *claims to verify*, never as authorization proof; annotations are never trusted as evidence.
5. **Security review** — a trusted scanner runs and its findings are triaged and retained. A scanner is **evidence, not the trust decision**, and Lullian never installs or executes a candidate in order to vet it.
6. **Admission plan** — the exact scope of what may be installed and used, hashed and bound.
7. **Explicit approval** — the project owner approves *this* plan, *this* scope, *this* artifact hash. Consent is never invented on the owner's behalf.
8. **External installation** — performed by the external executor, not by Lullian.
9. **Post-install verification** — what landed on disk must match what was approved.
10. **`AVAILABLE` is derived** — computed from the evidence graph, never asserted.

## Scanner trust

Security scanning uses an explicitly trusted scanner baseline. For v0.4.0 that baseline is **NVIDIA SkillSpector 2.11.2**, enforced as `skillspector-or-blocked`: if no trusted scanner is available, the gate blocks rather than degrades silently. A newer scanner release does **not** inherit trust automatically — scanner upgrades require a new trust record and a regression pass.

## Lifecycle and invalidation

```text
CANDIDATE → PENDING_REVIEW → PENDING_INSTALLATION → PENDING_VERIFICATION → AVAILABLE

AVAILABLE → STALE → REQUIRES_REVIEW → re-admission
AVAILABLE → QUARANTINED → REMOVED
```

Approval is **never permanent authorization**. An approval record binds to the exact admission-plan hash, scope hash, artifact hash, and policy revision, and it moves through `PENDING | APPROVED | EXPIRED | REVOKED | REJECTED | SUPERSEDED`. On material drift — expiry, revocation, scanner-trust change, dependency/scope/MCP-surface change, or verification mismatch — only the affected subject and its direct dependents are invalidated, and re-admission is required. Silent trust inheritance is impossible by construction, including when migrating a v0.3.2 project state forward: legacy approvals arrive as `PENDING` and legacy installations are rebound through explicit migration placeholders.

## Security model (high level)

- **Fail-closed everywhere.** Missing evidence, an unavailable trusted scanner, or an unverifiable claim results in *blocked*, never *allowed by default*.
- **Separation of concerns.** Provenance, integrity, security review, and approval are distinct record types with distinct validators; one cannot substitute for another.
- **Offline validation.** All 39 schemas use offline URN identifiers; validation requires no network access.
- **Deterministic enforcement.** Every rule above is enforced by a re-runnable script in `scripts/`, and the release gate (`scripts/release_check.py`) composes them.

Key entry points:

```bash
python scripts/security_gate.py ./candidate --scanner-trust ./scanner-trust.json --output report.json
python scripts/verify_admission.py ./project-state.json
python scripts/validate_project_state.py ./project-state.json
python scripts/validate_mcp_surface.py ./project-state.json
```

`security_gate.py` produces a fail-closed review state for a candidate — it does **not** install the candidate.
