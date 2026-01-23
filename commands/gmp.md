---
name: gmp
version: "3.2.0"
description: "Governance Managed Process — phased execution with audit trail"
auto_chain: ynp
---

# /gmp — Governance Managed Process

## USAGE

```
/gmp "task description"
/gmp --scope-file path/to/scope.yaml
```

## CHAIN

```
/gmp → Phase 0-6 → REPORT → workflow_state.md → /ynp
```

---

## MODIFICATION LOCK

| ❌ FORBIDDEN | ✅ ALLOWED |
|--------------|------------|
| Modify files not in TODO | Implement exact TODO |
| Create files outside scope | Operate within phases |
| Fix adjacent issues | Report in format |
| Skip phases | STOP if ambiguous |

---

## PHASES

| # | Phase | Purpose |
|---|-------|---------|
| 0 | PLAN | Lock TODO, scope boundaries |
| 0.5 | HARVEST | Analyze provided files, extract patterns |
| 1 | BASELINE | Verify files/lines exist |
| 2 | IMPLEMENT | Execute TODO only |
| 3 | ENFORCE | Add guards, fail-fast |
| 4 | VALIDATE | py_compile, ruff, tests |
| 5 | RECURSE | Verify no scope drift |
| 6 | FINALIZE | Report + memory write |

---

## TODO FORMAT

| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|
| T1 | path/file.py | 44-52 | Replace | Change X to Y |

**Actions:** `Create | Insert | Replace | Delete | Wrap`

---

## TIER CLASSIFICATION

| Tier | Examples |
|------|----------|
| KERNEL | executor.py, websocket_orchestrator.py |
| RUNTIME | tool_registry.py, redis_client.py |
| INFRA | docker-compose.yml, deploy/ |
| UX | frontend/, scripts/ |

---

## PROTECTED FILES

```
runtime/websocket_orchestrator.py
core/agents/executor.py
memory/substrate_service.py
docker-compose.yml
core/singleton_registry.py
```

→ Require dedicated KERNEL GMP with approval

---

## SCOPE LOCK OUTPUT

```markdown
## GMP SCOPE LOCK

**GMP ID:** GMP-XXX
**Tier:** KERNEL | RUNTIME | INFRA | UX

### TODO PLAN (LOCKED)
| T# | File | Lines | Action | Description |
|----|------|-------|--------|-------------|

### FILE BUDGET
- MAY: [files in TODO]
- MAY NOT: [protected]

⏸️ AWAITING: "CONFIRM"
```

---

## REPORT (Phase 6)

```bash
python3 scripts/generate_gmp_report.py \
  --task "description" \
  --tier RUNTIME_TIER \
  --todo "T1|file|lines|action|desc" \
  --validation "py_compile|✅" \
  --update-workflow
```

---

## STOP CONDITIONS

| Condition | Action |
|-----------|--------|
| TODO underspecified | STOP → clarify |
| Protected file | STOP → KERNEL GMP |
| Ambiguous intent | STOP → /analyze first |
| Assumption fails | Re-run Phase 0 |

--- End Command ---
