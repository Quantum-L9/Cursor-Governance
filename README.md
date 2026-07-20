---
title: L9 Governance
version: 2.0.0
created: 2025-01-27
updated: 2026-07-04
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
summarizes.

## 📁 Directory Structure

```
~/.cursor-governance/            (this repo)
├── skills/            # l9-* agent skills (SKILL.md per skill)
├── commands/          # Slash commands (/gmp, /plan, /end-session, ...)
├── rules/             # Global .mdc rules, symlinked as @.cursor-commands/rules
├── workflows/         # DAG definitions + executors
├── ops/
│   ├── scripts/       # Active automation (setup, validation, backup, sync)
│   ├── scripts/_archived/  # Retired pre-Graphiti / Suite-6 scripts (do not depend on)
│   ├── hooks/         # sessionStart / sessionEnd hooks
│   ├── graphiti/       # Graphiti memory client + activation runbooks
│   └── logs/          # Runtime logs
├── intelligence/      # Active signal corpus — chat exports, distillation, mining
├── profiles/          # Reasoning / session-startup profiles
├── learning/          # Curated lessons, repeated-mistakes, quick-fixes
├── protocols/         # GMP protocol contracts and templates
├── security/          # Security governance docs
├── integrity/         # Integrity verification docs/scripts
├── pipeline/          # Pipeline orchestration & validation docs
├── reports/           # GMP execution reports
├── C_GOV_FILES/       # Legacy duplicate tree — pending removal (see hygiene PRs)
├── ORG_INVARIANTS.yaml # Canonical Quantum-L9 org policy
├── CANONICAL_LAW.md   # Authoritative governance contract (read first)
└── README.md          # This file
```

`execution-governance/`, `foundation/`, `operations/`, `environment/`,
`telemetry/`, `key components/`, `prompts/`, `current_work/`, and `logs/`
hold supporting docs, in-progress notes, and legacy scaffolding; treat
`CANONICAL_LAW.md` and `skills/*/SKILL.md` as the sources of truth over any
directory listing, including this one.

## 🔗 Access Methods

### In Cursor workspaces
- `.cursor-commands/` — the sole symlink target in every coding repo
- `@.cursor-commands/skills/...`, `@.cursor-commands/rules/...`, `@.cursor-commands/commands/...`

### Direct path
- `~/.cursor-governance`

## 📋 Key Files

### Governance contract
- [`CANONICAL_LAW.md`](CANONICAL_LAW.md) — SSOT, symlink law, memory layer, anti-patterns
- [`ORG_INVARIANTS.yaml`](ORG_INVARIANTS.yaml) — canonical Quantum-L9 org policy

### Skills
- [`skills/l9-gmp-protocol/SKILL.md`](skills/l9-gmp-protocol/SKILL.md) — locked phase-0–6 execution
- [`skills/l9-structured-reasoning/SKILL.md`](skills/l9-structured-reasoning/SKILL.md) — planning/debugging reasoning stack
- [`skills/l9-graphiti-memory/SKILL.md`](skills/l9-graphiti-memory/SKILL.md) — Graphiti memory wiring

### Learning
- [`learning/repeated-mistakes.md`](learning/repeated-mistakes.md) — critical mistakes to never repeat
- [`learning/quick-fixes.md`](learning/quick-fixes.md) — fast solution patterns

### Operations
- [`ops/scripts/setup_workspace_symlinks.sh`](ops/scripts/setup_workspace_symlinks.sh) — install symlinks in a workspace
- [`ops/scripts/validate_governance_symlinks.sh`](ops/scripts/validate_governance_symlinks.sh) — verify symlink wiring
- [`ops/scripts/backup_to_github.sh`](ops/scripts/backup_to_github.sh) — commit + push SSOT to GitHub

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

**Last Updated:** 2026-07-04
**Version:** 2.0.0
