<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 3.0.0
updated: 2026-09-19
/L9_META -->

# Manus adapter — native Infisical capability binding

This is the active adapter for the `manus` registry identity. It implements a
small, **Manus-native stdio MCP lane** for operations that need an Infisical
secret without making that secret available to the model, project environment,
repository, command line, receipt, or tool result. It does not invoke, copy, or
depend on the Cursor SessionStart secret bootstrap.

| Concern | Manus-native binding |
|---|---|
| Identity | `environment.env.example` supplies only registry-derived, model-safe values. |
| Infisical authentication | A dedicated Universal Auth machine identity is supplied only as encrypted Custom MCP connector environment values. |
| Capability boundary | `infisical_capabilities.json` fixes the allowed secret reference, upstream origin, method, parameters, and output fields. |
| MCP transport | `serve_infisical_mcp.sh` starts a local stdio JSON-RPC server named `l9-manus-infisical`. |
| Secret inspection | `infisical_list_secret_metadata` requests `viewSecretValue=false`; it returns names and metadata only. |
| Secret use | `infisical_invoke` retrieves one manifest-approved value in memory, performs one fixed request, and returns a whitelisted response subset. |
| Memory | `mcp-connector.json` remains a separate, retired memory carrier; this connector is not a memory transport. |
| Program Execution | The `manus-cloud` provider remains dormant until a Controller transport exists. |

## Current capability

The initial manifest intentionally contains one read-only capability:

| Capability | Secret reference | Fixed upstream operation | Returned fields |
|---|---|---|---|
| `github.get_repository` | `GITHUB_TOKEN` | `GET https://api.github.com/repos/{owner}/{repo}` | Curated repository metadata only |

It is not a generic HTTP proxy, a shell runner, or a secret-reading API. Adding
a capability requires an explicit manifest change, strict argument validation,
a fixed HTTPS origin, and an output allowlist.

## Connector configuration

1. Make `Quantum-L9/Cursor-Governance` available through the Manus GitHub integration.
2. Copy the non-secret values from `environment.env.example` into the Manus project/session environment.
3. Create a **dedicated** Infisical Machine Identity for Manus. Grant the smallest project role necessary and create a Universal Auth client secret for that identity. Do not reuse a Cursor profile or broad human credential.
4. Store the client secret in a local mode-0600 file outside the repository. Render the temporary Custom MCP draft:

   ```bash
   .venv/bin/python environment/agents/adapters/manus/render_infisical_mcp_connector.py \
     --client-id <machine-identity-client-id> \
     --client-secret-file /secure/path/manus-infisical-client-secret \
     --project-id <infisical-project-id> \
     --output /tmp/l9-manus-infisical.json
   manus-config connector create --file /tmp/l9-manus-infisical.json
   rm -f /tmp/l9-manus-infisical.json
   ```

   The generated draft stores `L9_MANUS_INFISICAL_CLIENT_SECRET` only in the
   encrypted connector environment. It does not add it to a project environment,
   source file, launcher argument, URL, or task text.

5. After the Custom MCP connector is enabled, verify it with `infisical_status`.
   It should report `ready`, `secret_values_exposed: false`, and the declared
   capability list. Then call `infisical_list_secret_metadata` with a small limit
   to confirm that the Machine Identity is scoped to the expected project.

The connector can be configured through the Manus UI or an approved Custom MCP
configuration workflow. Never paste a client secret into a chat, command line,
project instruction, or project/session environment.

## Verification

```bash
make manus-adapter-check
python -m unittest environment/agents/adapters/manus/tests/test_manus_adapter.py
python -m unittest environment/agents/adapters/manus/tests/test_infisical_mcp_server.py
```

The test suite uses a fake Infisical API and verifies that metadata requests
explicitly exclude values, invocation output is sanitized, invalid caller input
does not resolve a secret, and a response containing the resolved value is
withheld.
