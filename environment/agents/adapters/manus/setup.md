<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-09-13
/L9_META -->

# Manus adapter setup

The Manus adapter is a **thin remote-surface binding**. It deliberately reuses
the shared L9 bootstrap, agent registry, autonomy profile, and secret boundary.
It does not reproduce the Cursor hook plane or Claude Code projection engine.

## Required project configuration

1. Make `Quantum-L9/Cursor-Governance` available through the Manus GitHub
   integration so a session can clone or open the governance checkout.
2. Copy the non-secret values from `environment.env.example` to the Manus
   project/session environment. Do not add a literal `L9_GOVERNANCE_DIR`; hosted
   environment values do not expand `$HOME`.
3. Install `session_bootstrap.md` as a project instruction or project-scoped
   Manus skill. This gives each session the exact identity, authority order, and
   upstream activation route.
4. Do **not** create a Custom MCP connector from `mcp-connector.json`. Its
   `transport: none` value is intentional: the memory package has not published
   a sanctioned remote transport for Manus.

## Local checkout verification

From a Manus workspace that has both an active git repository and the governance
checkout, run:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-install-check WS="$(pwd)"
```

`manus-adapter-check` validates the committed carrier files and registry
identity. `manus-install-check` invokes only the shared bootstrap in diagnostic
mode; it does not modify Manus account configuration or create a remote memory
connection. A degraded named capability is an honest result, not a reason to
persist a credential.

## Operating limits

The current Manus Program Execution provider (`manus-cloud`) is intentionally
dormant until a Controller execution transport exists. This surface adapter does
not change that status. Manus may perform the ordinary in-session work available
to the platform, governed by the shared L4 and publish-path gates, but it must
not advertise a background execution bridge, a remote memory path, or a secret
capability that the upstream packages do not supply.
