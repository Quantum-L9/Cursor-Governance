---
title: Folder Reorganizer
purpose: Reorganize Cursor project files into correct folders
summary: Moves stray files into appropriate structure using filename + metadata
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 10_rapid-operations.md
tags: [file-management, automation]
domain: ops
type: command
production_ready: true
---

## 📦 ORGANIZATION LOGIC
- Prompts: `Prompts - Production/`
- Workflows: `agents/`
- Schema: `Data_Management/`
- Learning: `@.GlobalCommands/learning/`
- Config: root or `/config/`
- Unknown: `/inbox/` for manual review

## 🚚 COMMAND
```bash
organize-folders --source ./ --rules folder-logic.yaml
```