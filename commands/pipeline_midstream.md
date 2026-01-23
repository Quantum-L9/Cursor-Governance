---
name: pipeline_midstream
version: "1.0.0"
description: "Mid-pipeline operations"
auto_chain: null
---

# /pipeline_midstream — Mid-Pipeline Ops

## WHAT IT DOES

Operations during active pipeline:

1. Check CI status
2. Fix failures
3. Re-run checks
4. Monitor progress

---

## COMMANDS

### Check Status

```bash
gh run list --limit 5
gh run view {run_id}
gh run view {run_id} --log-failed
```

### Re-run Failed

```bash
gh run rerun {run_id} --failed
```

### Watch Progress

```bash
gh run watch {run_id}
```

---

## FAILURE TRIAGE

| Failure Type | Fix |
|--------------|-----|
| Lint | `ruff check --fix .` |
| Type error | Fix annotation |
| Test failure | Fix code or test |
| Security | Address finding |
| Build | Check Dockerfile |

---

## OUTPUT

```markdown
## 🔄 PIPELINE STATUS

### Current Run
**ID:** {run_id}
**Status:** {in_progress/success/failure}
**Branch:** {branch}

### Jobs
| Job | Status | Duration |
|-----|--------|----------|
| lint | ✅/❌ | Xs |
| test | ✅/❌ | Xs |

### Failures (if any)
| Job | Error |
|-----|-------|

### Action
→ {fix recommendation}
```

--- End Command ---
