<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-gmp-protocol
layer: reference
role: workflow_kernel
tags: [gmp, lifecycle, discover, build, ship, check, maintenance]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - harvested: pipelines-README, pipelines-build/ship/check, pipelines-000, pipelines-_legacy-00, pipelines-rapid-analysis (Suite-5 legacy, Cursor-native rewrite)
--- /SKILL_META ---

Purpose:
Repo-native lifecycle pipelines — Discover → Build → Ship → Check — mapped to L9 skills and PlasticOS make targets.
-->

# Lifecycle Pipelines

Use instead of legacy `pipelines-*` slash packs. Chain stages manually or via GMP locked plans (`references/pipeline-composition.md`).

**Rule:** Run **individual stages** ~95% of the time. Full end-to-end chains only for greenfield onboarding or disaster recovery.

## Decision Tree

```text
What do you need?

├─ "Don't understand this repo / onboarding"
│  └─ DISCOVER (12–18 min, safe)
│
├─ "Building or changing features"
│  └─ BUILD → SHIP
│
├─ "Ready to land on remote / production path"
│  └─ SHIP (after BUILD or small fix + pr-check)
│
├─ "Weekly health / preventive maintenance"
│  └─ CHECK (8–10 min, safe)
│
├─ "Quick status without full discover"
│  └─ DISCOVER abbreviated (parallel analysis, 5–8 min)
│
└─ "Production broken"
   └─ l9-incident-response + references/rollback-playbook.md
```

## PlasticOS Mapping

| Stage | L9 / repo actions |
|-------|-------------------|
| **Discover** | `l9-code-analysis` + `l9-gap-analysis`; optional `make audit` |
| **Build** | `l9-plan` / `l9-structured-reasoning` → implement → local `make pr-check` |
| **Ship** | `make push` (runs pr-check) → PR to Staging → CI green |
| **Check** | `make audit`; advisory security scans; review open PRs/CI |
| **Fix** | `l9-incident-response`; git revert; Odoo `make update` rollback path |

Generic repos: swap `make pr-check` / `make push` / `make audit` for equivalent CI gates.

---

## DISCOVER — Onboarding & Architecture

**When:** first open, return after long break, pre-major refactor, quarterly review.

**Sequence** (backup first if mutating later):

```text
1. Snapshot baseline (commit state or governance backup if touching GlobalCommands)
2. Structure scan — l9-code-analysis (orientation, hotspots)
3. Dependency map — l9-code-analysis/references/dependency-analysis.md
4. Readiness gap — l9-gap-analysis vs target (prod-ready / L9)
5. Pattern alignment — l9-code-analysis/references/pattern-alignment.md (optional)
6. Synthesize report with ranked action items
```

**Abbreviated discover** (rapid analysis): run steps 2–4 with parallel tool calls where independent.

**Output:** architecture summary, gap %, prioritized TODOs — no code changes unless explicitly in scope.

---

## BUILD — Feature Development

**When:** new feature, non-trivial refactor, integration work.

| Step | Action | Gate |
|------|--------|------|
| 1. Design | `l9-structured-reasoning` or `l9-plan`; Block 9 impl plan if coding | Requirements clear; confidence ≥ 0.8 |
| 2. Implement | Locked scope only | Incremental validation |
| 3. Static validate | `make pr-check` or repo lint/test equivalent | Must pass before ship |
| 4. Backup checkpoint | Commit or stash before risky steps | Rollback point exists |
| 5. Ready for SHIP | Pre-ship checklist (below) | All gates green |

**Pre-ship checklist:**

- [ ] No open TODO/FIXME without tracking
- [ ] Tests added/updated for behavior change
- [ ] Docs/manifest/wiring updated if applicable
- [ ] `make pr-check` passed this session
- [ ] Rollback plan named (revert commit / module downgrade)

---

## SHIP — Deploy / Release

**When:** feature complete, fix validated, config change approved.

| Step | Action | On failure |
|------|--------|------------|
| 1. Pre-flight | Confirm pr-check passed; review diff | Stop — fix locally |
| 2. Security | `l9-auditing-security` or CI secret scan | Stop on critical |
| 3. Backup | Commit pushed; tag or note SHA for rollback | Required before merge |
| 4. Push / PR | `make push` or `make push pr=1` | Never raw `git push` (PlasticOS) |
| 5. Verify | CI green; smoke test if applicable | Rollback per playbook |

**Auto-rollback / abort triggers:**

- Pre-push validation fails
- Critical security finding
- CI blocking jobs fail post-merge
- Error rate or health check fails beyond threshold after deploy
- Error rate > 20% in first monitoring window (if metrics available)

**Deployment windows:** prefer low-traffic periods; avoid Friday evening deploys without on-call coverage.

**Post-deploy monitoring:**

| Window | Activity |
|--------|----------|
| First 30 min | Active — logs, CI, smoke tests |
| Next 2 hours | Periodic checks |
| Next 24 hours | Review logs/metrics vs baseline |

---

## CHECK — Weekly Maintenance

**When:** weekly (e.g. Sunday), before major release, after incident recovery.

| Step | Action |
|------|--------|
| 1. Health baseline | CI status, open failures, docker/services if applicable |
| 2. Security pass | `l9-auditing-security` or CI advisory; governance secret hygiene |
| 3. Performance | `l9-auditing-performance` if slowness reported |
| 4. Backup verify | Governance backup / git remote in sync |
| 5. Cleanup | `l9-code-maintenance` lint/format debt (explicit scope only) |
| 6. Report | Week-over-week table + action items |

**CHECK report skeleton:**

```markdown
# Weekly CHECK — {date}
**Health score:** {0–100} · **Duration:** {min}

| Metric | This week | Last week | Δ |
|--------|-----------|-----------|---|

## Action items
| Priority | Item | Owner |
|----------|------|-------|

**Next CHECK:** {date}
```

---

## Master Chain (Rare)

Full **Discover → Build → Ship → Check** in one GMP run — only for:

- Brand-new repo onboarding
- Disaster recovery rebuild
- Annual deep refresh

Insert **validation gates between stages**; allow pause/review between stages. Default: run stages separately.

---

## New Integration Gate

Before merging a new component, module, or external integration:

```text
1. Structural validate (lint, wiring, manifest)
2. Dependency / blast-radius analysis
3. Security review (secrets, auth, input validation)
4. Documentation + rollback note
5. Checkpoint backup / commit
```

Maps to BUILD step 3 + dependency-analysis + auditing-security.
