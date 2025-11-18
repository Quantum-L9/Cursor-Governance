---
title: Deployment Orchestrator
purpose: Manage and automate multi-phase deployments with validations
summary: Coordinates project deployment by enforcing order, governance, and validation
version: 1.0.0
created: 2025-10-13
owner: Igor Beylin
source: 04_deployment-orchestrator.md
tags: [deployment, automation, governance]
domain: deployment
type: orchestrator
production_ready: true
---

## 🔄 DEPLOYMENT PHASES
1. Validate project configuration
2. Load environment (.env.template)
3. Scan governance and learning files
4. Perform dry-run (preflight)
5. Execute push with rollback conditions
6. Write results to `session_status.md` + `change_log.md`

## 🔧 COMMAND
```bash
deploy-orchestrator --env .env.template --schema supabase-schema.sql
```