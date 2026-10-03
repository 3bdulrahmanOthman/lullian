# Evaluation and Validation Summary

Lullian v0.4.0 is validated by **deterministic, re-runnable gates** — not by claims. Everything below can be reproduced from the package itself.

## What is validated

### Deterministic local gates

`python scripts/release_check.py` composes every local gate and must end with `RELEASE CHECK: PASS`:

- skill-format and frontmatter contracts
- resource links, flat portable layout
- schema syntax, offline `$id`s, example validity, cross-schema invariants
- eval inventory, package contract (exact file allowlist + manifest parity)
- state/admission/dependency/MCP-surface/lifecycle validators on a valid v0.4 state bundle
- conservative v0.3.2 → v0.4.0 migration (trust must downgrade, never inherit)
- release-provenance helper, including a tampered-attestation rejection case
- research-budget helper
- release hygiene: zero bytecode, no hidden files, no secret patterns, no symlinks

### Behavioral evaluation corpus

- **36 executable behavioral cases** — every case in `evals/evals.json` is graded deterministically on every release run.
- **8 metamorphic cases** — invariant-preserving input transformations must not change the governed outcome.
- **36-case external export** — `scripts/export_eval_dataset.py` exports the corpus in a neutral format for third-party evaluators, without coupling the skill to any evaluator.

### Adversarial (negative) testing

The governance validators are tested by *attempting to break them*: changed artifact hashes, changed scope, expired and revoked approvals, altered admission plans, stale provenance, forged `AVAILABLE` states, and altered MCP declarations. A correctly governed system must **reject** every one of these — and does.

### External static security checks (release time)

- Agent Skills reference validator (`skills-ref`) — PASS
- Semgrep (`p/default`) — 0 findings
- Gitleaks — clean
- bandit + pip-audit — PASS
- NVIDIA SkillSpector 2.11.2 (static, real execution) — findings triaged individually and retained in evidence; none suppressed

## Artifact integrity

The shipped skill is a **93-file canonical artifact** with a reproducible build recipe, a per-file SHA-256 manifest, and a pinned digest. It is signed with a detached [OpenSSF Model Signing](https://github.com/sigstore/model-transparency) (OMS) signature; the attestation lives in an **external sidecar** — the artifact never contains the signature that attests to it. Tamper tests (modified file, injected unsigned file) are rejected with per-file hash mismatches.

## Known limitations

Recorded fail-closed — absence of a gate is never converted into a pass:

1. **LLM-backed semantic analysis was not run at release time.** The SkillSpector semantic layer and SkillEvaluator Tiers 2–3 require model-provider credentials that were not available in the validation environment. Not simulated.
2. **SkillEvaluator Tier 1 is incomplete** (9/11 validators pass); the single gap is the same LLM-backed semantic completeness flag.
3. **OSV-Scanner is not applicable as run** — the package declares no dependency manifests, so there is no in-package dependency surface to scan. No "no vulnerabilities" claim is made or implied.
4. **No benchmark claims.** No performance benchmark is published for this release; none is claimed.
5. **Release attestation publication follows the GitHub release.** The signed artifact and signature are ready; the public attestation step completes after publication.

## Re-running the gates

```bash
python scripts/release_check.py            # everything local, offline
python scripts/export_eval_dataset.py --output evaluator-dataset.json
```

External scanner/evaluator configuration (a reproducible Linux CI environment) is provided in `external-validation-ci/` — repository-only, not part of the shipped skill.
