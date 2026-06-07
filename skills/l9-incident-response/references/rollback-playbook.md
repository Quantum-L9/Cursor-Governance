<!-- L9_META
l9_schema: 1
parent: l9-incident-response
layer: reference
role: incident_kernel
tags: [incident, rollback, emergency, recovery, sev]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
/L9_META -->

# Rollback Playbook

Load during SEV1–SEV2 or when a recent deploy correlates with failure. Pairs with main incident workflow in `SKILL.md`.

## Fix Pipeline Decision Tree

```text
Production issue detected
  │
  ├─ Recent deploy in last ~60 min?
  │    YES → Rollback first (forensic snapshot → restore known-good)
  │    NO  → Investigate (systematic debugging in l9-structured-reasoning)
  │
  After rollback:
  ├─ System stable? → Root-cause fix on branch; do NOT re-deploy until tested
  └─ Still broken? → Escalate ladder below
  │
  After fix:
  ├─ Tests pass? → Redeploy / merge fix
  └─ Fail? → Refine fix; do not skip validation
```

## Severity → Response

| Trigger | Maps to | Response |
|---------|---------|----------|
| Complete outage, data risk, all users | SEV1 | Immediate rollback or failover; incident commander |
| Key workflow broken, high error rate (>20%) | SEV2 | Rollback within 30 min if deploy-related |
| Single subsystem, workaround exists | SEV3 | Fix forward if faster; rollback optional |
| Minor / cosmetic | SEV4 | Normal fix process |

Align with SEV table in `SKILL.md`; use the **higher** severity when in doubt.

## Emergency Rollback Steps

| Step | Action | Target time |
|------|--------|-------------|
| 1 | Assess — what's broken, last change, blast radius | 30s–2min |
| 2 | **Forensic snapshot** — preserve broken state (commit SHA, logs, config export) before restore | 1min |
| 3 | Restore known-good — `git revert` / redeploy previous / module downgrade | 2–10min |
| 4 | Verify — health checks, smoke test, error rate normal | 1–5min |
| 5 | Communicate + schedule postmortem | ongoing |

**Doctrine:** Rollback first when production is broken and a recent change exists. Fix root cause after stability.

### PlasticOS restore paths

- **Code:** `git revert <sha>` on branch → `make push`
- **Odoo module:** prior module version or DB restore per runbook; `make update m=<module>` after fix validated
- **Config:** restore from governance backup or documented last-good params

## Escalation Ladder

1. **Previous known-good** — revert one deploy / restore prior backup
2. **Manual targeted restore** — restore specific files or modules from backup; compare diffs
3. **Platform support** — hosting provider (Odoo.sh, cloud vendor) with backup artifacts
4. **Rebuild from source** — git history + seed data; last resort

Document which level was used in the incident report.

## Rollback Report Skeleton

```markdown
# Rollback Report — {incident-id}
**Status:** RESOLVED | PARTIAL | FAILED
**Duration:** {min} · **Downtime:** {min}

| Step | Action | Duration | Status |
|------|--------|----------|--------|

## Forensic snapshot
- SHA / artifact: {id}
- Purpose: post-mortem analysis

## Root cause
{brief}

## MTTR
Detection → mitigation: {min}

## Follow-up
- [ ] Postmortem within 48h
- [ ] CI/runbook gap closed
```

## Rules

- Never delete forensic snapshot until postmortem complete.
- Communicate at start, at rollback complete, and at resolved.
- Record MTTR; target SEV1/2 rollback under 15 minutes when deploy-caused.
