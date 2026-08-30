# Capability broker — RETIRED (never shipped)

**Retired:** 2026-08-29
**Why:** `broker.quantumaipartners.com` has no DNS. Hosted surfaces issue no
broker-verifiable identity. Every brokered capability (`sonar.read_issues`,
`semgrep.appsec_scan`, `graphiti.query`) reported DEGRADED. The experiment
scored Cursor sessions with Claude cloud probes.

## What to use instead

| Need | Path |
|---|---|
| Graphiti (Cursor) | Local CLI + SSH tunnel (`ops/graphiti/graphiti_memory_client.py`) |
| Graphiti (adapters) | `${GRAPHITI_MCP_URL}` in MCP templates |
| Sonar on a model surface | Unauthenticated public read (`sonar_fetch.py`) |
| Sonar as a human | `DirectTransport` + operator `SONAR_TOKEN` |
| Infisical | Operator `hydrate_infisical.py` only — never on the agent plane |

## What still exists in-tree

The Python modules (`capability_broker.py`, `capability_client.py`,
`probe_broker.py`, `broker_identity.py`) remain for history and for
`L9_BROKER_FORCE=1` diagnostics. Live SessionStart, shared bootstrap,
`install.sh`, MCP templates, and `make capability-check` / `broker-serve`
do **not** treat the plane as live. Makefile recipes are unchanged
(root `Makefile` is additive_only); the CLIs exit 0 with RETIRED.

Do not paste `SONAR_TOKEN`, `SEMGREP_APP_TOKEN`, `INFISICAL_CLIENT_SECRET`,
or `GRAPHITI_MCP_TOKEN` onto a model-controlled surface.
