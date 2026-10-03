# Installation and Quick Start

## Requirements

- any agent that supports the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Cursor, Gemini CLI, and others)
- Node.js (for the `skills` CLI) and Python 3.10+ (for the deterministic validators)

## Install

```bash
npx skills add 3bdulrahmanOthman/lullian
```

The CLI auto-detects installed agents and registers the skill for them. Useful variants:

```bash
npx skills add 3bdulrahmanOthman/lullian -a claude-code   # target a specific agent
npx skills add 3bdulrahmanOthman/lullian -g               # install globally (user scope)
npx skills add 3bdulrahmanOthman/lullian --all -y         # non-interactive, all agents (CI-friendly)
```

**Keep the whole skill directory.** The entrypoint is [`SKILL.md`](../SKILL.md), but the skill is the entire directory: the `references/` contracts, the 39 schemas in `assets/`, the evaluation corpus in `evals/`, and the validators in `scripts/` are all part of the operating surface. Do not copy `SKILL.md` alone.

## Quick start

After installation, ask your agent:

```text
Use Lullian to turn this project idea into a structured project foundation before implementation.
Surface uncertainty, research what needs current evidence, record the important decisions,
and produce an implementation-ready handoff.
```

For a brownfield repository:

```text
Use Lullian to reconstruct this repository's intent, map its real requirements and hidden
assumptions, and produce an evidence-backed foundation before the next major change.
```

A typical session produces:

- a project intake and domain understanding
- requirements with explicit, tracked uncertainty
- recorded decisions with evidence and alternatives
- an architecture and technology selection
- a governed toolchain (only for tools that passed admission)
- canonical documentation and an implementation-ready handoff

## Post-install verification

The package ships its own validators. From the installed skill directory:

```bash
python scripts/release_check.py             # full deterministic release gate
python scripts/validate_skill.py            # skill-format contract
python scripts/validate_package_contract.py # exact package allowlist + manifest parity
```

`release_check.py` should end with `RELEASE CHECK: PASS`. It runs entirely offline.

## Verifying a shipped artifact (for maintainers)

Release artifacts are signed with a detached [OpenSSF Model Signing](https://github.com/sigstore/model-transparency) signature and pinned by a SHA-256 digest. Verification instructions and the public key ship with each release.

## Upgrading from v0.3.2

Migration is conservative by design: legacy approvals are downgraded to `PENDING`, legacy installations are rebound through explicit migration placeholders, and old verification is never treated as fresh v0.4 verification.

```bash
python scripts/migrate_project_state_v032.py OLD-BUNDLE.json NEW-BUNDLE.json
```
