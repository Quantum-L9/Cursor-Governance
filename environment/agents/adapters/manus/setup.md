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

The Manus adapter has a native Infisical capability lane. It is intentionally
independent of Cursor activation: it does not install a Cursor hook, read a
Cursor machine profile, call a shared SessionStart secret plane, or export
secrets to the Manus session.

## Required setup

1. Create a **Manus-specific Infisical Machine Identity**. Give it project
   access that is limited to the required secret paths and permissions. A
   read-only initial capability needs only access to `GITHUB_TOKEN` in the
   chosen project scope.
2. Configure **Universal Auth** for that identity. Keep the Client ID and Client
   Secret outside this repository and outside Manus project/session environment.
3. Render a temporary local Custom MCP draft with
   `render_infisical_mcp_connector.py`. The renderer reads the Client Secret from
   a mode-0600 file and creates a mode-0600 draft with encrypted connector
   environment values.
4. Add that draft as the `l9-manus-infisical` Custom MCP server. Its command is
   the checked-in `serve_infisical_mcp.sh`; no remote URL, bearer header, or
   project environment secret is required.
5. Delete the temporary draft immediately after it has been accepted. Retain the
   client-secret source only in the approved operator secret store.

## Runtime behavior

The server sends the machine identity Client ID and Client Secret only to
Infisical's Universal Auth login endpoint. It retains the resulting access token
in process memory until shortly before expiry. For metadata listing it sends
`viewSecretValue=false`. For invocation it reads exactly one manifest-declared
secret, uses it in one fixed HTTPS request, serializes an allowlisted response
subset, and refuses the response if the resolved value appears in it.

No MCP tool returns a secret value. There is no `get_secret`, `resolve_secret`,
generic outbound HTTP, command execution, environment dump, or arbitrary
capability-selection tool.

## Adding a capability

Edit `infisical_capabilities.json` and the accompanying tests in the same
change. A capability must have a unique identifier, a single approved inventory
key, a fixed HTTPS origin, an allowlisted method, strict caller argument regexes,
a path template that uses only declared arguments, and an explicit response
field allowlist. The adapter's Python validator and tests must be extended for
every new upstream family before it can be used.

## Diagnostic checks

```bash
make manus-adapter-check
make manus-install-check WS="$(pwd)"
```

These checks validate the carrier assets and repository workspace only. They do
not authenticate to Infisical, create a Manus Custom MCP connector, or retrieve
a secret. At runtime, use `infisical_status` for connector posture and
`infisical_list_secret_metadata` for an explicit, value-free scope check.
