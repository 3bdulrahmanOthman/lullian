# Supply-Chain Provenance

Lullian separates artifact identity, provenance, dependency evidence, signatures/attestations, and policy approval.

## Identity

`artifactHash` identifies content. It does not by itself establish authenticity.

## Provenance

Record source, exact revision, distribution identity, build provenance when available, retrieval time, and evidence references.

## Attestations

External release attestations may use SLSA, in-toto, Sigstore, GitHub artifact attestations, or another compatible system. The attestation instance is a release sidecar and MUST NOT be embedded inside the artifact whose digest it attests to.

## Dependency evidence

Prefer resolved lockfile evidence. Distinguish complete resolution from partial/unresolved analysis. Exceptions are time-bounded and auditable.
