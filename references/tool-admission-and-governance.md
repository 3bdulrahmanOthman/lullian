# Tool Admission and Governance

Lullian v0.4 treats external Skills, MCPs, libraries, CLIs, and services as governed evidence subjects.

## Admission chain

`candidate -> exact resolution -> provenance/integrity -> dependency/scope/capability review -> MCP surface review -> security review -> admission plan -> explicit approval -> external installation -> post-install verification -> derived availability`.

An admission plan is declarative. Lullian never executes the installation command.

## Exact binding

Approval binds to the exact admission plan hash, scope hash, artifact hash, policy revision, and expiry. A changed subject or broadened scope invalidates the approval.

## Availability

`AVAILABLE` is derived only when the applicable evidence graph is complete, approval is still valid, installation is bound to the admission plan, and post-install verification proves expected artifact identity.

## Exceptions

Security/dependency exceptions require reason, bounded scope, and an expiry. An exception does not erase the original finding.

## Drift

Material source, dependency, scope, MCP-surface, scanner-trust, or installed-artifact changes generate lifecycle evidence and force local re-review.
