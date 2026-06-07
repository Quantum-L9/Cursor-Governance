<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [verify, component, diagnostic]
status: active
/L9_META -->

# Verify Component (/verify-component)

**Diagnostic only — NO edits.**

## Protocol

1. Enumerate imports (static)
2. Verify module paths exist
3. Verify symbols exist (file + line)
4. Import-safety scan
5. Runtime import proof (`python3 -c "..."`)
6. Protected file wiring matrix (read-only)

## Escalation

If protected file requires change → end with: `Kernel or protected-file wiring required → l9-gmp-protocol`

## Protected files (read-only diagnosis)

- `core/agents/executor.py`
- `runtime/websocket_orchestrator.py`
- `memory/substrate_service.py`
- `docker-compose.yml`
- `core/singleton_registry.py`

Output: evidence tables only; PASS / FAIL / PARTIAL.
