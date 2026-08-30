# RETIRED — L9 capability broker (never shipped)

**Retired:** 2026-08-29
**Reason:** The capability-broker experiment never shipped. Every brokered
capability stayed DEGRADED. `broker.quantumaipartners.com` was never a live
front door. Restoring this tree would re-introduce a second secret plane that
the model-controlled surfaces must not hold.

This directory is the archived implementation (`git mv`, not a hard delete).
`pyproject.toml` `norecursedirs` includes `_archived`, so these tests are not
collected. Do not import this tree from live code.

Live surfaces reach Graphiti at `${GRAPHITI_MCP_URL}` (default
`https://memory.quantumaipartners.com/graphiti/mcp`) with **no bearer**.
Authenticated Sonar / Semgrep AppSec / Context7 / GitGuardian via the broker
are **not delivered**. That is never a reason to paste a secret into a
model-controlled environment.

Refuse-only stubs remain at the former live paths
(`ops/secrets/capability_broker.py`, `probe_broker.py`, `broker_identity.py`)
so a stray `make broker-serve` fails closed instead of resurrecting a server.

See `environment/agents/adapters/ADAPTER_CONTRACT.md` (memory carrier) and
`docs/DEGRADED_MODE_CONTRACT.md`.
