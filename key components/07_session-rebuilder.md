---
title: Session Rebuilder
purpose: Reconstruct session context from saved logs and memory files
summary: Restores reasoning context by loading all relevant governance, learning, and prompt state
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 07_workflow-manager.md
tags: [session, context, reconstruction]
domain: session
type: loader
production_ready: true
---

## 📁 LOAD SEQUENCE
1. `.env.template`
2. `supabase-schema.sql`
3. `project_config.yaml`
4. `@.GlobalCommands/profiles/*.md`
5. `memory_log.json` + `session_status.md`

## 🚀 COMMAND
```bash
rebuild-session --source ./memory_log.json --restore
```