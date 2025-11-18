---
title: Monitor Agent
purpose: Continuously monitor key files, workflows, and changes
summary: Runs in background, logging schema diffs, config drift, or policy violations
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 09_system-monitor.md
tags: [monitoring, observability, automation]
domain: monitoring
type: daemon
production_ready: true
---

## ⚙️ MONITORED PATHS
- `.env.template`
- `supabase-schema.sql`
- `project_config.yaml`
- All files in `/agents/` and `/Data_Management/`

## 🛠️ COMMAND
```bash
monitor-agent --paths .env.template supabase-schema.sql --log ./logs/monitoring.md
```