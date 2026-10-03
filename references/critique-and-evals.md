# Critique and Evaluations

Lullian's native eval corpus is authoritative for its own deterministic expectations. External evaluators receive an exported dataset through `scripts/export_eval_dataset.py`.

The corpus preserves legacy cases and adds governance cases covering approval expiry/revocation, scope drift, dependency resolution, provenance/signature mismatch, installation verification, MCP metadata trust, capability composition, and scanner upgrades.

Metamorphic tests assert locality: a material change invalidates only its subject and direct dependents.
