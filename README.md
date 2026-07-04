---
title: GlobalCommands Directory
version: 1.0.0
created: 2025-01-27
owner: Igor Beylin
source: Migrated from L9 Governance (L9 + Suite 5)
tags: [governance, global-commands, learning, profiles, ops]
domain: system-governance
type: documentation
production_ready: true
---

# GlobalCommands Directory

## 🎯 Purpose

Centralized governance system accessible across all workspaces via `@.globalcommands/` or `@.GlobalCommands/` references.

## 📁 Directory Structure

```
GlobalCommands/
├── learning/          # Learning system files
│   ├── repeated-mistakes.md
│   ├── quick-fixes.md
│   ├── L9-ai-agent-patterns.md
│   └── L9-configs/
├── profiles/          # Reasoning profiles
│   ├── reasoning_docs.md
│   ├── reasoning_L9.md
│   ├── reasoning_technical_operations.md
│   └── orchestrator.md
├── ops/              # Operations scripts
│   ├── scripts/       # Automation scripts
│   └── logs/         # System logs
├── integrity/        # Integrity verification
│   ├── system-check.sh
│   └── integrity-audit.md
├── intelligence/     # Intelligence layer (governance)
│   ├── reasoning/    # Reasoning frameworks
│   └── meta-learning/
├── foundation/       # Foundation layer (governance)
│   ├── agents/       # Agent stubs
│   ├── logic/        # Logic systems
│   └── security/     # Security governance
├── execution/        # Execution layer (governance)
│   ├── api/          # Governance APIs
│   ├── dashboard/    # Governance dashboard
│   └── validation/   # Validation tools
├── environment/      # Environment layer (governance)
│   └── env-manager.py
├── telemetry/       # Telemetry layer (governance)
│   └── telemetry-collector.py
├── operations/      # Operations layer (governance)
├── key components/ # Key component documentation
├── pipeline/       # Pipeline orchestration & validation
│   ├── pipeline-orchestration.md
│   ├── pipeline_validate.md
│   └── workspace-doctor.md
├── security/       # Security governance
│   ├── api-key-verification.md
│   ├── security-audit.md
│   └── supabase-auth.md
├── Prompt Artisan - Prompts & Primitives/  # Prompt templates
│   ├── reasoning-engine.prompt.md
│   ├── agent-profile.modular-reasoning.v1.0.md
│   └── 17 more prompt templates
├── templates/       # Template files (.cursorrules)
├── L9 research/   # Node research database
└── README.md       # This file
```

## 🔗 Access Methods

### In Cursor Workspaces
- `@.globalcommands/` - Dot-prefixed access (via symlink)
- `@.GlobalCommands/` - Standard access

### Direct Path
- `~/.cursor-governance`

## 📋 Key Files

### Learning System
- [`learning/repeated-mistakes.md`](learning/repeated-mistakes.md) - Critical mistakes to never repeat
- [`learning/quick-fixes.md`](learning/quick-fixes.md) - Fast solution patterns
- [`learning/L9-ai-agent-patterns.md`](learning/L9-ai-agent-patterns.md) - AI Agent node patterns

### Reasoning Profiles
- [`profiles/reasoning_L9.md`](profiles/reasoning_L9.md) - L9 orchestration reasoning
- [`profiles/reasoning_technical_operations.md`](profiles/reasoning_technical_operations.md) - Technical decisions
- [`profiles/orchestrator.md`](profiles/orchestrator.md) - Central coordinator

### Operations
- [`ops/scripts/setup_workspace_symlinks.sh`](ops/scripts/setup_workspace_symlinks.sh) - Setup script
- [`ops/logs/memory_index.json`](ops/logs/memory_index.json) - Learning database

## 🚀 Usage

### Reference in Prompts
```markdown
@.GlobalCommands/learning/repeated-mistakes.md
@.GlobalCommands/L9 research/[node_name].md
@.GlobalCommands/profiles/reasoning_L9.md
```

### Node Research Database
Save node research findings to:
```
@.GlobalCommands/L9 research/[node_name].md
```

## 📊 Migration Status

**Migrated:** 2025-01-27  
**Source:** L9 Governance (L9 + Suite 5)  
**Files:** 59 files across 4 directories  
**Status:** ✅ Complete

---

**Last Updated:** 2025-01-27  
**Version:** 1.0.0

