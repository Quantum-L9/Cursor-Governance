---
name: VPS Deploy Scripts Integration
overview: Copy the 3 deployment scripts from VPS-Repo-Files/VPS-Deploy-Sequence/ to repo root, copy 6 docs to docs/vps-deployment/, fix VPS_USER from "admin" to "root", and make scripts executable. No new code generation needed - this leverages already-generated assets.
todos:
  - id: copy-scripts
    content: Copy 3 deployment scripts to repo root with VPS_USER fix
    status: pending
  - id: copy-docs
    content: Create docs/vps-deployment/ and copy 6 documentation files
    status: pending
    dependencies:
      - copy-scripts
  - id: validate
    content: Run ./docker-validator.sh check-only to verify integration
    status: pending
    dependencies:
      - copy-docs
---

# VPS Multi-Service Deployment System Integration

## Objective

Integrate the pre-generated VPS deployment pack (3 scripts + 6 docs) into the L9 repository to fix the broken Step 6 deployment that only built 1 of 4 services.

## Context Harvest Summary

- **9 files already generated** in `VPS-Repo-Files/VPS-Deploy-Sequence/`
- **0 new code to write** - pure file placement + one config fix
- **Time saved:** ~4-6 hours (vs regenerating from scratch)

---

## Implementation Plan

### Phase 1: Copy Deployment Scripts (3 files → repo root)

| Source | Destination | Notes ||--------|-------------|-------|| `VPS-Repo-Files/VPS-Deploy-Sequence/docker-validator.sh` | `docker-validator.sh` | Make executable || `VPS-Repo-Files/VPS-Deploy-Sequence/vps-deploy-helper.sh` | `vps-deploy-helper.sh` | Make executable || `VPS-Repo-Files/VPS-Deploy-Sequence/l9-deploy-runner-updated.sh` | `l9-deploy-runner-updated.sh` | Make executable + fix VPS_USER |**Config fix needed:** Line 25 of `l9-deploy-runner-updated.sh`:

```bash
# Change from:
VPS_USER="admin"
# To:
VPS_USER="root"
```



### Phase 2: Create docs/vps-deployment/ and copy documentation (6 files)

Create `docs/vps-deployment/` directory and copy:| Source | Destination ||--------|-------------|| `DOCKER-DEPLOYMENT-GUIDE.md` | `docs/vps-deployment/DOCKER-DEPLOYMENT-GUIDE.md` || `INTEGRATION-CHECKLIST-UPDATED.md` | `docs/vps-deployment/INTEGRATION-CHECKLIST.md` || `QUICK-START-4-SERVICES.md` | `docs/vps-deployment/QUICK-START.md` || `SOLUTION-SUMMARY.md` | `docs/vps-deployment/SOLUTION-SUMMARY.md` || `FINAL-SUMMARY.md` | `docs/vps-deployment/FINAL-SUMMARY.md` || `DEPLOYMENT-READY-CHECKPOINT.md` | `docs/vps-deployment/DEPLOYMENT-CHECKPOINT.md` |

### Phase 3: Update workflow_state.md

Add to Next Steps:

- VPS deployment scripts integrated and ready
- Test with `./docker-validator.sh check-only`

---

## Files Modified

| File | Action | Lines Changed ||------|--------|---------------|| `docker-validator.sh` | CREATE (copy) | 362 || `vps-deploy-helper.sh` | CREATE (copy) | 346 || `l9-deploy-runner-updated.sh` | CREATE (copy + fix) | 324 (1 line modified) || `docs/vps-deployment/` | CREATE (6 files) | ~1,832 total |**Total:** 9 files, ~2,864 lines (all copied from existing assets)---

## Validation

After integration:

```bash
# Verify scripts exist and are executable
ls -la docker-validator.sh vps-deploy-helper.sh l9-deploy-runner-updated.sh

# Run quick validation
./docker-validator.sh check-only

# Expected: discovers 4 services (redis, neo4j, l9-postgres, l9-api)
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation ||------|-------------|--------|------------|| Scripts don't work | LOW | LOW | Already tested in Perplexity session || VPS user wrong | FIXED | N/A | Changing "admin" to "root" in plan || Merge conflicts | NONE | N/A | New files only |---

## Post-Integration Workflow

After this GMP, the deployment workflow becomes:

1. **Before commit:** `./docker-validator.sh check-only`
2. **Full local test:** `./docker-validator.sh build`