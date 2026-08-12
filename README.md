---
title: L9 Governance
version: 2.0.0
created: 2025-01-27
updated: 2026-07-19
owner: Igor Beylin
source: Post-Suite-6, Graphiti-native governance
tags: [governance, skills, commands, rules, ops, graphiti]
domain: system-governance
type: documentation
production_ready: true
---

# L9 Governance

## 🎯 Purpose

Centralized, IDE-agnostic governance system for L9/Quantum-L9 repos. The clone at
`~/.cursor-governance/` **is** the governance root — there is no nested
`GlobalCommands/` subfolder. Every coding workspace exposes it through a single
symlink: `.cursor-commands` → `~/.cursor-governance/`.

See `CANONICAL_LAW.md` for the authoritative, binding contract this README
summarizes, and `AGENTS.md` for exactly how a session activates this
governance layer.

## ⚡ Activation (TL;DR)

Activation is automatic — one hook, no manual step:

`ops/hooks/session_start_bootstrap.sh` → installed at
`~/.cursor/hooks/session-start-bootstrap.sh` → registered in
`~/.cursor/hooks.json` under `sessionStart`. It syncs this clone, reconciles
the declared Claude Code plugin set (`ops/scripts/setup_claude_code_plugins.sh`),
reconciles the IDE profile (`environment/ide/` — Biome/Ruff/Pyright extensions plus
a managed-key merge into `.vscode/settings.json`), auto-wires symlinks, checks Graphiti
(activated and round-trip verified as of 2026-07-27 — see `AGENTS.md` §2.3), and reads
`memory-bank/activeContext.md`. See `AGENTS.md` §2
for the full activation contract and manual/repair commands. `start-session.yaml`
(the old YAML "protocol") was retired 2026-07-19 — the `.sh` hook above is now
the sole activation mechanism.

To trigger that same pipeline by hand — synchronously, with visible output:

```bash
make -C "$HOME/.cursor-governance" start WS="$(pwd)"
```

## 📁 Directory Structure

```
~/.cursor-governance/            (this repo)
├── skills/            # l9-* agent skills (SKILL.md per skill)
├── commands/          # Slash commands (/gmp, /l9-plan, /end-session, ...)
├── rules/             # Global .mdc rules, symlinked as @.cursor-commands/rules
├── workflows/         # DAG definitions + executors
├── ops/
│   ├── scripts/       # Active automation (setup, validation, backup, sync)
│   ├── scripts/_archived/  # Retired pre-Graphiti / Suite-6 scripts (do not depend on)
│   ├── hooks/         # sessionStart / sessionEnd hooks
│   ├── graphiti/      # Graphiti memory client + activation runbooks
│   ├── secrets/       # AWS SM registry SSOT (openclaw-igorbot/*) + resolve
│   ├── ui-operator/   # Portable SaaS UI console, cartridges, receipts
│   └── logs/          # Runtime logs
├── intelligence/      # Active signal corpus — chat exports, distillation, mining
├── environment/       # Runtime environment adapters (IDE-neutral policy + per-target renderers)
│   ├── contracts/     # First-class execution contracts/templates (executable plan SSOT)
│   ├── ide/           # Editor profile: policy.json + render.cursor.json (Cursor/VS Code)
│   ├── program-execution/  # Program Execution System (Blueprint/Controller/adapters)
│   └── claude-code/   # Claude Code environment (CLI · Web · Mobile) — committed .claude/ + account env
├── profiles/          # DEPRECATED — content ported into skills/ + rules/; pending retirement
├── learning/          # Curated lessons, repeated-mistakes, quick-fixes
├── protocols/         # GMP protocol contracts and templates
├── security/          # Security governance docs
├── integrity/         # Integrity verification docs/scripts
├── pipeline/          # Pipeline orchestration & validation docs
├── reports/           # GMP execution reports
├── C_GOV_FILES/       # Legacy duplicate tree — pending removal (see hygiene PRs)
├── ORG_INVARIANTS.yaml # Canonical Quantum-L9 org policy
├── CANONICAL_LAW.md   # Authoritative governance contract (read first)
├── AGENTS.md          # Activation contract + agent operating rules (read second)
└── README.md          # This file
```

`execution-governance/`, `foundation/`, `environment/`,
`telemetry/`, `key components/`, `prompts/`, `current_work/`, and `logs/`
hold supporting docs, in-progress notes, and legacy scaffolding; treat
`CANONICAL_LAW.md` and `skills/*/SKILL.md` as the sources of truth over any
directory listing, including this one. The former nested `operations/ops/`
tree was merged into top-level `ops/` (see `ops/operational-oversight.md`).

## 🔗 Access Methods

### In Cursor workspaces
- `.cursor-commands/` — the sole symlink target in every coding repo
- `@.cursor-commands/skills/...`, `@.cursor-commands/rules/...`, `@.cursor-commands/commands/...`

### Direct path
- `~/.cursor-governance`

## 📋 Key Files

### Governance contract
- [`CANONICAL_LAW.md`](CANONICAL_LAW.md) — SSOT, symlink law, memory layer, anti-patterns
- [`AGENTS.md`](AGENTS.md) — activation contract, change policy, agent operating rules
- [`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml) — canonical Quantum-L9 org policy

### Skills
- [`skills/l9-gmp-protocol/SKILL.md`](skills/l9-gmp-protocol/SKILL.md) — locked phase-0–6 execution
- [`skills/l9-plan/SKILL.md`](skills/l9-plan/SKILL.md) — execution planning → PE+autonomy `.plan.md`
- [`environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md`](environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md) — **first-class** executable plan template SSOT
- [`skills/l9-structured-reasoning/SKILL.md`](skills/l9-structured-reasoning/SKILL.md) — adaptive evidence-based reasoning (plan/review/architecture/debug/corpus)
- [`skills/_archived/`](skills/_archived/) — retired skill packs (not discoverable; do not activate)
- [`skills/l9-graphiti-memory/SKILL.md`](skills/l9-graphiti-memory/SKILL.md) — Graphiti memory wiring
- [`skills/l9-aws-secrets/SKILL.md`](skills/l9-aws-secrets/SKILL.md) — AWS SM refs via `ops/secrets` (Governance SSOT)
- [`skills/l9-ui-operator/SKILL.md`](skills/l9-ui-operator/SKILL.md) — SaaS UI console when API is insufficient (explicit-only)

### Learning
- [`learning/repeated-mistakes.md`](learning/repeated-mistakes.md) — critical mistakes to never repeat
- [`learning/quick-fixes.md`](learning/quick-fixes.md) — fast solution patterns

### Operations
- [`ops/scripts/setup_workspace_symlinks.sh`](ops/scripts/setup_workspace_symlinks.sh) — install symlinks in a workspace
- [`ops/scripts/validate_governance_symlinks.sh`](ops/scripts/validate_governance_symlinks.sh) — verify symlink wiring
- [`ops/scripts/backup_to_github.sh`](ops/scripts/backup_to_github.sh) — commit + push SSOT to GitHub
- [`ops/scripts/backup_gate.sh`](ops/scripts/backup_gate.sh) — gate the sessionEnd backup (reason filter, debounce, activity guard)
- [`ops/secrets/README.md`](ops/secrets/README.md) — secrets registry sync/resolve
- [`ops/ui-operator/README.md`](ops/ui-operator/README.md) — UI console + cartridges

### UI operator install (optional)
```bash
make ui-operator-sync    # uv sync --extra ui-operator
playwright install
```
Not required for `make pr`.
## 🚀 Usage

### Reference in prompts
```markdown
@.cursor-commands/learning/repeated-mistakes.md
@.cursor-commands/skills/l9-structured-reasoning/SKILL.md
@.cursor-commands/rules/00-global.mdc
```

### Wire a new workspace
```bash
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh
bash .cursor-commands/ops/scripts/validate_governance_symlinks.sh
```

## 📊 Status

**Origin:** `Quantum-L9/Cursor-Governance` (GitHub is the SSOT remote; this
clone at `~/.cursor-governance/` is the SSOT working copy — see
`CANONICAL_LAW.md` §1, §5).

---

**Last Updated:** 2026-07-19
**Version:** 2.0.0
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:README -->

## Program Execution

`environment/program-execution/` contains the sealed Program Execution core,
replaceable execution adapters, conformance contracts, routing policy, and bridges
to existing Cursor-Governance runtimes. Mutable program state remains outside Git
under `$HOME/.l9/programs/`.
