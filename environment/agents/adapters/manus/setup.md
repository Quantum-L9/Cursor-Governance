<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 3.0.0
updated: 2026-09-19
/L9_META -->

# Manus adapter setup

The Manus adapter is a **thin remote-surface binding**. It reuses the shared L9 bootstrap, agent registry, autonomy profile, and secret boundary. It does not reproduce the Cursor hook plane or Claude Code projection engine.

## Required project configuration

1. Make `Quantum-L9/Cursor-Governance` available through the Manus GitHub integration so a session can clone or open the governance checkout.
2. Copy the non-secret values from [`environment.env.example`](environment.env.example) to the Manus project or session environment. Do not add a literal `L9_GOVERNANCE_DIR`; hosted environment values do not expand `$HOME`.
3. Install [`session_bootstrap.md`](session_bootstrap.md) as a project instruction or project-scoped Manus skill. This gives each session the exact identity, authority order, and upstream activation route.
4. Deploy the L9 Governance MCP service only if direct governance discovery and validation are required. A default deployment is read/diagnostic only and does not replace the in-workspace installer or expose shared memory.

## Deploy the governance MCP service

The server uses streamable HTTP at `/mcp` and a health endpoint at `/health`. It is standard-library Python and uses the governance locked interpreter. Run it from a checkout whose `uv.lock` environment is already prepared:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh --port 8787
```

Expose that process through an HTTPS reverse proxy. The endpoint must end in `/mcp`; do not place credentials in the URL. After confirming `GET /health` responds with `{"status":"ok"}`, run `render_mcp_connector.py --help` and render a connector draft with the actual deployed HTTPS endpoint. Then add the generated JSON through Manus **Settings → Integrations → Custom MCP Servers**. The draft uses Manus’s direct Custom MCP form mode so it does not attempt OAuth discovery on this intentionally unauthenticated read-only endpoint, and registers the `l9-governance` server. It gives the Manus project focused access to governance status, validation, bounded policy/skill reads and search, skill inventory, and the diagnostic shared bootstrap.

After the connector is enabled, verify discovery and the no-secret posture from a Manus shell:

```bash
manus-mcp-cli tool list --server l9-governance
manus-mcp-cli tool call governance_status --server l9-governance --input '{}'
```

The status response must report `status: ready`, `memory: not exposed by this adapter`, and `bootstrap_enabled: false` for the public endpoint. Any result that reports a memory provider, credentials, an arbitrary shell, or enabled bootstrap access is a deployment error; disable the connector and correct the server configuration before use.

The default public service exposes only read/validation tools. Because both bootstrap modes write local readiness metadata, `governance_bootstrap` is available only from a bearer-protected service. To permit `apply` as well, launch with an externally managed token file and both bootstrap flags:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh \
  --auth-token-file /secure/path/l9-governance-mcp.token \
  --allow-bootstrap-apply \
  --port 8787
```

A bearer-protected deployment requires a Manus Custom MCP form configuration with the same user-managed secret. Do not commit, paste, or generate that secret in an adapter environment file, endpoint URL, chat transcript, or receipt. The `apply` mode invokes only the existing shared Manus installer for an explicit Git workspace; it does not add a shell, Git write tool, memory bridge, capability broker, or credentials.

## Local checkout verification

From a Manus workspace that has both an active Git repository and the governance checkout, run:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-mcp-test
make -C "$HOME/.cursor-governance" manus-install-check WS="$(pwd)"
```

`manus-adapter-check` validates the committed carrier files and registry identity. `manus-mcp-test` validates the tool contract and safety boundary. `manus-install-check` invokes only the shared bootstrap in diagnostic mode; it does not modify Manus account configuration or create a remote memory connection. A degraded named capability is an honest result, not a reason to persist a credential.

## Operating limits

The current Manus Program Execution provider (`manus-cloud`) remains intentionally dormant until a Controller execution transport exists. This surface adapter does not change that status. Manus may perform the ordinary in-session work available to the platform, governed by the shared L4 and publish-path gates, but it must not advertise a background execution bridge, a remote memory path, a secret capability, or a generic repository write API that the upstream packages do not supply.
