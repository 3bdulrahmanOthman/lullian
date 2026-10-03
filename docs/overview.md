# Lullian Overview

**Lullian** is a pre-implementation intelligence and governance layer for AI agents, shipped as an installable [Agent Skill](https://agentskills.io). It turns incomplete project intent — or an existing repository — into an evidence-backed **Project Foundation**: requirements, uncertainty, decisions, architecture, technology selection, a governed toolchain, canonical documentation, and an implementation-ready handoff.

Lullian is **not** a coding harness, runtime orchestrator, package installer, MCP executor, or credential manager. It does its work *before* implementation starts.

## Why it exists

The expensive failures usually happen before the first line of code:

- the problem is underspecified and the assumptions are invisible
- "research" is a single model response with no evidence trail
- decisions are made implicitly and never recorded
- third-party Skills, MCP servers, and CLI tools are trusted the moment they are mentioned

Lullian makes each of these explicit, structured, and verifiable.

## How it works

Lullian runs a staged operating model. Every stage ends in a **checkpoint** that verifies structure, traceability, consistency, freshness, and security; a failed blocking check stops progression until the smallest affected stage is repaired.

```text
RAW INTENT
  -> UNDERSTANDING -> UNCERTAINTY -> CLARIFY / RESEARCH
  -> REQUIREMENTS -> DOMAIN MODEL -> DECISIONS
  -> ARCHITECTURE -> TECHNOLOGY -> WORKFLOW + TOOLCHAIN
  -> TOOL ADMISSION (when applicable)
  -> DOCUMENTATION -> CRITIQUE -> RECONCILE -> HANDOFF
```

Three principles run through the whole model:

1. **Everything is a projection of an evidence/decision graph.** Documents are never free-standing prose; they trace back to evidence records and decision records. Certainty is never manufactured to make a document look complete.
2. **External content is untrusted data, never instructions.** Repository files, web pages, package metadata, tool descriptions, and reports are treated as data to be assessed, not commands to be followed.
3. **Readiness is derived, never asserted.** States such as a tool being `AVAILABLE` are computed from the evidence graph; a legacy `status` field is compatibility metadata only and is never treated as proof.

## Where Lullian fits

```text
        ┌──────────────────────┐
        │       Lullian        │   pre-implementation:
        │ intent → foundation  │   understanding, decisions,
        └──────────┬───────────┘   governed toolchain, handoff
                   │  Project Foundation + handoff
                   ▼
        coding agent / implementation workflow
```

Lullian sits **in front of** implementation. Coding agents receive a cleaner, evidence-backed specification; orchestrators receive a governed, verified toolchain instead of ad-hoc installs. Downstream visual/product design work consumes the handoff through a generic **Design Authority Interface** — any conforming implementation can fill that role, and nothing in the package depends on a specific design tool.

## What's in the package

| Group | Count | Purpose |
|---|---|---|
| `SKILL.md` | 1 | activation contract and operating instructions |
| `references/` | 14 | progressive-disclosure operating contracts (architecture, research, lifecycle, governance, …) |
| `assets/` | 39 | offline JSON Schemas for every governed artifact type |
| `evals/` | 7 files | 36 behavioral cases + 8 metamorphic cases |
| `scripts/` | 28 | deterministic validators, security gate, admission/lifecycle verifiers, release gates |

The package declares **zero runtime dependencies**, performs **no network calls** during validation (all schemas are offline URNs), and keeps every check deterministic and re-runnable.

## Boundaries

| Lullian owns | Lullian deliberately does not own |
|---|---|
| project understanding, requirements, uncertainty mapping | code generation · routine coding · isolated fixes |
| evidence-backed research with budgets and freshness | runtime orchestration · deployment execution |
| explicit decisions, architecture, technology selection | package installation · MCP server execution |
| third-party Skill/MCP/tool admission governance | credential storage · sandboxing · CI/CD |
| canonical documentation, critique, implementation handoff | final visual art direction |
| derived readiness states | approval on the owner's behalf — consent is never invented |

See also: [governance.md](governance.md) · [installation.md](installation.md) · [validation.md](validation.md)
