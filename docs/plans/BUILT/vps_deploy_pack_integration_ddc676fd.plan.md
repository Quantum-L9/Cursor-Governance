---
name: VPS Deploy Pack Integration
overview: Copy 9 pre-generated files from VPS-Repo-Files/VPS-Deploy-Sequence/ to their destinations EXACTLY as written. No modifications, no fixes, no creative thinking. Pure file placement.
todos:
  - id: copy-scripts
    content: Copy 3 deployment scripts to repo root EXACTLY as generated
    status: completed
  - id: copy-docs
    content: Create docs/vps-deployment/ and copy 7 docs EXACTLY as generated
    status: completed
  - id: make-executable
    content: chmod +x the 3 shell scripts
    status: completed
  - id: validate
    content: Verify files exist and syntax check scripts
    status: completed
---

# VPS Deploy Pack Integration (GMP Deterministic)

## Variable Bindings

| Variable | Value |

|----------|-------|

| TASK_NAME | vps_deploy_pack_integration |

| EXECUTION_SCOPE | Copy 9 pre-generated files to repo destinations |

| RISK_LEVEL | Low |

| SOURCE_DIR | VPS-Repo-Files/VPS-Deploy-Sequence/ |

## Constraint Check

- [x] KERNEL-TIER files NOT in scope
- [x] No code generation required
- [x] Files copied EXACTLY as written (no modifications)

---

## TODO PLAN (LOCKED)

### Phase 1: Copy Scripts to Repo Root

| TODO | Source | Destination | Action |

|------|--------|-------------|--------|

| T1 | [docker-validator.sh](VPS-Repo-Files/VPS-Deploy-Sequence/docker-validator.sh) | `/docker-validator.sh` | Copy exact |

| T2 | [vps-deploy-helper.sh](VPS-Repo-Files/VPS-Deploy-Sequence/vps-deploy-helper.sh) | `/vps-deploy-helper.sh` | Copy exact |

| T3 | [l9-deploy-runner-updated.sh](VPS-Repo-Files/VPS-Deploy-Sequence/l9-deploy-runner-updated.sh) | `/l9-deploy-runner.sh` | Copy exact |

### Phase 2: Create docs/vps-deployment/ and Copy Docs

| TODO | Source | Destination | Action |

|------|--------|-------------|--------|

| T4 | [SOLUTION-SUMMARY.md](VPS-Repo-Files/VPS-Deploy-Sequence/SOLUTION-SUMMARY.md) | `docs/vps-deployment/` | Copy exact |

| T5 | [QUICK-START-4-SERVICES.md](VPS-Repo-Files/VPS-Deploy-Sequence/QUICK-START-4-SERVICES.md) | `docs/vps-deployment/` | Copy exact |

| T6 | [DOCKER-DEPLOYMENT-GUIDE.md](VPS-Repo-Files/VPS-Deploy-Sequence/DOCKER-DEPLOYMENT-GUIDE.md) | `docs/vps-deployment/` | Copy exact |

| T7 | [DEPLOYMENT-READY-CHECKPOINT.md](VPS-Repo-Files/VPS-Deploy-Sequence/DEPLOYMENT-READY-CHECKPOINT.md) | `docs/vps-deployment/` | Copy exact |

| T8 | [INTEGRATION-CHECKLIST.md](VPS-Repo-Files/VPS-Deploy-Sequence/INTEGRATION-CHECKLIST.md) | `docs/vps-deployment/` | Copy exact |

| T9 | [INTEGRATION-CHECKLIST-UPDATED.md](VPS-Repo-Files/VPS-Deploy-Sequence/INTEGRATION-CHECKLIST-UPDATED.md) | `docs/vps-deployment/` | Copy exact |

| T10 | [FINAL-SUMMARY.md](VPS-Repo-Files/VPS-Deploy-Sequence/FINAL-SUMMARY.md) | `docs/vps-deployment/` | Copy exact |

### Phase 3: Make Scripts Executable

| TODO | File | Action |

|------|------|--------|

| T11 | `/docker-validator.sh` | chmod +x |

| T12 | `/vps-deploy-helper.sh` | chmod +x |

| T13 | `/l9-deploy-runner.sh` | chmod +x |

### Phase 4: Validation

| TODO | Check | Command |

|------|-------|---------|

| T14 | Verify scripts exist | `ls -la *.sh` |

| T15 | Verify docs exist | `ls -la docs/vps-deployment/` |

| T16 | Syntax check | `bash -n docker-validator.sh` |---

## Execution Commands

```bash
# Phase 1: Copy scripts
cp VPS-Repo-Files/VPS-Deploy-Sequence/docker-validator.sh ./docker-validator.sh
cp VPS-Repo-Files/VPS-Deploy-Sequence/vps-deploy-helper.sh ./vps-deploy-helper.sh
cp VPS-Repo-Files/VPS-Deploy-Sequence/l9-deploy-runner-updated.sh ./l9-deploy-runner.sh

# Phase 2: Copy docs
mkdir -p docs/vps-deployment
cp VPS-Repo-Files/VPS-Deploy-Sequence/SOLUTION-SUMMARY.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/QUICK-START-4-SERVICES.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/DOCKER-DEPLOYMENT-GUIDE.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/DEPLOYMENT-READY-CHECKPOINT.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/INTEGRATION-CHECKLIST.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/INTEGRATION-CHECKLIST-UPDATED.md docs/vps-deployment/
cp VPS-Repo-Files/VPS-Deploy-Sequence/FINAL-SUMMARY.md docs/vps-deployment/

# Phase 3: Make executable
chmod +x docker-validator.sh vps-deploy-helper.sh l9-deploy-runner.sh

# Phase 4: Validate
ls -la *.sh
ls -la docs/vps-deployment/
bash -n docker-validator.sh && echo "Syntax OK"
```

---

## File Budget

| MAY Modify | MAY NOT Modify |

|------------|----------------|

| `docker-validator.sh` (new) | Any existing files |

| `vps-deploy-helper.sh` (new) | docker-compose.yml |

| `l9-deploy-runner.sh` (new) | runtime/Dockerfile |

| `docs/vps-deployment/*` (new) | Any Python files |---

## Report
