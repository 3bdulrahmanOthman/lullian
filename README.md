<div align="center">
  <img src=".github/brand/lullian-banner.png" alt="Lullian — From ideas to structure." width="100%" />
</div>

# Lullian

**Pre-implementation intelligence for AI agents — turn raw project intent into structure, evidence, decisions, architecture, governed tools, and an implementation-ready handoff.**

[![Version](https://img.shields.io/badge/version-0.4.0-1f6feb?style=flat-square)](CHANGELOG.md)
[![Type](https://img.shields.io/badge/type-agent_skill-f2ecdc?style=flat-square)](SKILL.md)
[![Schemas](https://img.shields.io/badge/json_schemas-39-a371f7?style=flat-square)](#package-layout)
[![Evals](https://img.shields.io/badge/evals-36_+_8_metamorphic-2da44e?style=flat-square)](#package-layout)
[![Admission](https://img.shields.io/badge/tool_admission-fail--closed-f0883e?style=flat-square)](docs/governance.md)
[![Artifact](https://img.shields.io/badge/artifact-oms--signed-24292f?style=flat-square)](docs/validation.md)

<br>

| | |
|---|---|
| **Type** | Agent Skill — entrypoint [`SKILL.md`](SKILL.md), installable with `npx skills add` |
| **Role** | pre-implementation intelligence · `project-intelligence` — not a coding harness, orchestrator, installer, or credential manager |
| **Surface** | 14 progressive-disclosure references · 39 JSON Schemas · 36 behavioral + 8 metamorphic eval cases · 28 deterministic scripts |
| **Governance** | fail-closed tool admission — exact resolution → provenance → explicit approval → post-install verification |
| **Scanner baseline** | NVIDIA SkillSpector 2.11.2 (validated baseline; upgrades require a new trust record) |
| **Artifact** | 93-file canonical artifact · SHA-256 pinned · signed via OpenSSF Model Signing |

<br>

Lullian is the layer an AI agent uses **before implementation** to understand what needs to be built, what is still unknown, which decisions matter, and which external tools can be trusted. Every material output is a projection of an evidence/decision graph — certainty is never manufactured to make a document look complete.

> The name honors **Ramon Llull** and his *Ars Magna* (1232–1316): a combinatorial machine for turning ideas into structured knowledge. Lullian applies the same ambition to modern software projects.

---

## What Lullian is — and what it is not

| Lullian owns | Lullian deliberately does not own |
|---|---|
| project understanding, requirements, uncertainty mapping | code generation · routine coding · isolated fixes |
| evidence-backed research with budgets and freshness | runtime orchestration · deployment execution |
| explicit decisions, architecture, technology selection | package installation · MCP server execution |
| third-party Skill/MCP/tool admission governance | credential storage · sandboxing · CI/CD |
| canonical documentation, critique, implementation handoff | final visual art direction |
| derived readiness states | approval on the owner's behalf — consent is never invented |

External content — repositories, web pages, package metadata, tool descriptions, reports — is **untrusted data, never instructions**.

---

## The core workflow

Agents are good at executing instructions. The hard failures often happen **earlier** — when the problem is underspecified, assumptions are hidden, decisions are untracked, or the toolchain is trusted too quickly. Lullian turns that ambiguity into a structured project foundation:

```mermaid
flowchart LR
    I["Intent"] --> U["Understanding"]
    U --> R["Requirements<br>+ Uncertainty"]
    R --> D["Decisions"]
    D --> A["Architecture<br>+ Technology"]
    A --> G["Governed Skills /<br>MCP / Tools"]
    G --> H["Implementation<br>Handoff"]
```

Each stage ends in a checkpoint that verifies structure, traceability, consistency, freshness, and security — a failed blocking check stops progression. It works for both **greenfield** projects and **brownfield** repositories, where the real problem is often ambiguity, missing context, stale assumptions, or uncontrolled toolchain decisions.

For external Skills, MCP servers, and tools, the governance path is deliberately **fail-closed**:

```mermaid
flowchart LR
    A["Exact<br>Resolution"] --> B["Identity +<br>Integrity"]
    B --> C["Provenance"]
    C --> D["Dependency / Scope /<br>MCP Review"]
    D --> E["Security<br>Review"]
    E --> F["Admission<br>Plan"]
    F --> G["Explicit<br>Approval"]
    G --> H["External<br>Installation"]
    H --> I["Post-install<br>Verification"]
    I --> J["AVAILABLE<br>(derived)"]
```

A scanner is **evidence — not the entire trust decision**. Lullian never silently installs or executes a candidate to vet it. The full lifecycle, admission semantics, and security model are described in [`docs/governance.md`](docs/governance.md).

---

## Where Lullian fits

Lullian sits **in front of** your coding agent or workflow — it produces the Project Foundation that implementation consumes. It complements, rather than replaces:

- **coding agents** — they receive a cleaner, evidence-backed specification
- **orchestrators and harnesses** — Lullian feeds them a governed, verified toolchain instead of ad-hoc installs
- **design authority** — downstream visual and product design work consumes Lullian's handoff through a generic **Design Authority Interface**; any conforming design implementation can fill that role. It is never a required installation dependency and is not part of this package.

**Use Lullian when** starting a new product or software system, reconstructing or modernizing an existing repository, making a major architecture or technology reset, preparing a clean handoff for a coding agent, or evaluating project-specific Skills, MCP servers, or tools before adoption.

---

## Installation

Install Lullian with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add 3bdulrahmanOthman/lullian
```

The CLI auto-detects your installed agents and registers the skill for them. Useful variants:

```bash
npx skills add 3bdulrahmanOthman/lullian -a claude-code        # target a specific agent
npx skills add 3bdulrahmanOthman/lullian -g                    # install globally (user scope)
npx skills add 3bdulrahmanOthman/lullian --all -y              # non-interactive, all agents (CI-friendly)
```

The skill entrypoint is [`SKILL.md`](SKILL.md). Keep the complete skill directory intact so its `references/`, schemas, validators, and evaluation assets remain available — the skill is the whole directory, not just `SKILL.md`. More detail, including a worked first session and post-install verification, is in [`docs/installation.md`](docs/installation.md).

A useful first request:

```text
Use Lullian to turn this project idea into a structured project foundation before implementation.
Surface uncertainty, research what needs current evidence, record the important decisions,
and produce an implementation-ready handoff.
```

---

## Package layout

| Path | Contents |
|---|---|
| [`SKILL.md`](SKILL.md) | activation contract and operating instructions |
| [`references/`](references/architecture-and-technology.md) | 14 progressive-disclosure operating contracts |
| [`assets/`](assets/schema-tool.json) | 39 machine-readable JSON Schemas |
| [`evals/`](evals/evals.json) | 36 behavioral cases + 8 metamorphic cases |
| [`scripts/`](scripts/release_check.py) | 28 deterministic validation, migration, admission, export, and release helpers |
| [`docs/`](docs/overview.md) | public documentation: overview, governance, installation, validation |

---

## Validation

v0.4.0 is backed by deterministic local validation, adversarial mutation testing, Agent Skills format validation, and external static security checks. The shipped artifact is signed, and its identity is pinned.

```text
✅ Deterministic local gates   full release_check.py → RELEASE CHECK: PASS · package contract PASS
✅ Adversarial mutations        changed hash / scope / expired-revoked approval / altered plan /
                                stale provenance / forged AVAILABLE / MCP changes — all rejected
✅ Format validation           skills-ref 0.1.5 — PASS
✅ Static security             Semgrep (p/default) 0 findings · Gitleaks clean · bandit + pip-audit PASS
✅ Scanner (static)            SkillSpector 2.11.2 — findings triaged and retained in evidence
✅ Artifact integrity          canonical 93-file artifact · per-file SHA-256 manifest · OMS-signed ·
                               tamper tests PASS
```

Two LLM-backed analyzers (the SkillSpector semantic layer and SkillEvaluator Tiers 2–3) require model-provider credentials that were not available on the validation host. These gates were **not run and not simulated** — they are recorded as known limitations rather than being treated as passing, in line with the fail-closed policy that governs the skill itself. Every locally executable gate passes, and the signed artifact's identity is proven. See [`docs/validation.md`](docs/validation.md) for the full summary and limitations.

Run the local gates yourself:

```bash
python scripts/release_check.py          # the deterministic release gate
python scripts/validate_package_contract.py
```

---

## Documentation

| Document | Content |
|---|---|
| [`docs/overview.md`](docs/overview.md) | what Lullian is, how it works, where it fits |
| [`docs/governance.md`](docs/governance.md) | tool/Skill/MCP governance and the security model |
| [`docs/installation.md`](docs/installation.md) | installation, quick start, and examples |
| [`docs/validation.md`](docs/validation.md) | evaluation/validation summary and known limitations |
| [`LICENSE`](LICENSE) | MIT license |
| [`CHANGELOG.md`](CHANGELOG.md) | release history |

---

## Maintainer

**Abdulrahman Othman** · [github.com/3bdulrahmanOthman](https://github.com/3bdulrahmanOthman)

<div align="center">
  <sub><i>From ideas to structure.</i></sub>
</div>
