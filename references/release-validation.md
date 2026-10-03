# Release Validation

Internal release checks validate package structure, schemas, examples, state invariants, security invariants, evaluation inventory, and release hygiene.

External validation is recorded separately:

- `skills-ref validate` for Agent Skills format compliance; this is not the security boundary.
- real NVIDIA SkillSpector execution for static security analysis.
- SkillEvaluator Tier 1 for deterministic/static checks; Tier 2 is reviewed; Tier 3 is measured/advisory by default.
- release artifact signing/attestation when the publication policy enables it.

The release artifact is identified by canonical content manifest and final artifact SHA-256. Release attestations are external sidecars, not self-referential package files.
