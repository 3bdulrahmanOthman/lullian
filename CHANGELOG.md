# Changelog

## 0.4.0 — Governance & Trust Expansion

- Added exact tool scope, admission-plan, installation-verification, dependency-audit, MCP-surface, capability-interaction, lifecycle-event, and external release-attestation contracts.
- Reworked availability so `AVAILABLE` is derived from the evidence graph rather than trusted from a declared status field.
- Bound approvals to exact admission-plan hash, scope hash, artifact hash, and policy revision, with explicit expiry/reapproval semantics.
- Added conservative v0.3.2 → v0.4 migration with trust downgrade for legacy approvals and explicit non-admissible migration placeholders.
- Added dependency completeness and time-bounded exception validation.
- Added MCP surface evidence with `DECLARED → INSPECTED → VERIFIED` maturity; annotations remain non-authoritative hints.
- Added capability-interaction risk evidence without turning Lullian into a runtime policy engine.
- Added post-install verification binding and drift/revocation lifecycle records.
- Added external evaluation export so Lullian's native eval contracts remain independent from SkillEvaluator/Harbor formats.
- Preserved the NVIDIA SkillSpector **2.11.2** validated baseline; scanner upgrades require independent trust migration and regression.
- Replaced private Design Director coupling with a generic Design Authority Interface; the private implementation is not a public dependency.
- Expanded the native evaluation corpus to **36 behavioral + 8 metamorphic** cases.
- Expanded deterministic release validation to cover v0.4 governance contracts, migration, admission, lifecycle, dependency, MCP, export, and release-provenance helpers.
- Hardened the release harness so governance regressions and native eval assertions run deterministically without nested pipe deadlocks; corrected brownfield/evaluation fixtures to test v0.4 semantics rather than stale vocabulary.
- Added an independent v0.4.0 forensic audit and refreshed the final validation/coverage reports after the complete local gate run.
- External host gates remain separate: `skills-ref validate`, real SkillSpector execution, SkillEvaluator Tier 1/2/3, and release signing/attestation when policy-enabled.

## 0.3.2 — Hardened Implementation Candidate

- Closed the v0.3.1 forensic findings across security admission, state integrity, lifecycle semantics, evaluation, package hygiene, and documentation typing.
- Expanded the machine-readable contract surface to **31 JSON Schemas**, including explicit document records and IDs for state-referenced artifacts.
- Hardened third-party Skill/MCP admission with a separately trusted NVIDIA SkillSpector record, exact `2.11.2` scanner pin, exact executable SHA-256 matching, symlink-free staging, bounded snapshots, static/no-LLM scanning, timeout/error fail-closed behavior, retained raw reports, and deterministic snapshot archives.
- Added independent admission verification for scanner-trust, raw-report, snapshot, archive, and verdict hash bindings.
- Reworked project-state validation into a cross-record integrity graph covering provenance → scanner trust → snapshot → scan evidence → security review → approval → installation → tool.
- Strengthened readiness projections, lifecycle/supersession/approval invariants, research-usage validation, executable eval assertions, metamorphic eval coverage, and helper release probes.
- Added an independent forensic audit and final validation report; local deterministic release gates are green.
- External `skills-ref`, real SkillSpector execution, and live-agent evaluation remain explicit host-level admission gates and are not claimed as executed in this environment.

## 0.3.0 — Implementation Candidate

- Converted the v0.2.0 architecture baseline into a portable Agent Skill package.
- Added progressive-disclosure lifecycle, evidence, requirements, architecture, workflow, documentation, design-boundary, and security contracts.
- Added 23 machine-readable JSON Schemas covering project state, requirements, evidence, decisions, architecture, technology, workflow, tools, security review, approvals, dependencies, quality attributes, documentation, and handoff.
- Added 18 behavior eval cases and 4 metamorphic cases, including hidden-requirement and third-party-tool security scenarios.
- Added fail-closed SkillSpector security gate wrapper with target-integrity checking.
- Added content-hash/tool-definition drift protection and self-security surface validation.
- Added deterministic package validation and representative schema-instance validation.
- Kept harness/runtime orchestration explicitly outside scope.
