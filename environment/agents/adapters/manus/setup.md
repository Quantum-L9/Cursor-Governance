<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 4.0.0
updated: 2026-09-19
/L9_META -->

# Manus adapter setup

The Manus adapter is a **thin remote-surface binding**. It reuses the shared L9 bootstrap, agent registry, autonomy profile, Infisical profile bootstrap, and memory control plane. It does not reproduce the Cursor hook plane, Claude Code projection engine, or a direct memory provider client.

It also has a native Infisical capability lane. That lane is intentionally independent of Cursor activation: it does not install a Cursor hook, read a Cursor machine profile, call a shared SessionStart secret plane, or export secrets to the Manus session.

## Required setup

1. Make `Quantum-L9/Cursor-Governance` available through the Manus GitHub integration so a session can clone or open the governance checkout.
2. Copy the non-secret values from [`environment.env.example`](environment.env.example) to the Manus project or session environment. Do not add a literal `L9_GOVERNANCE_DIR`; hosted environment values do not expand `$HOME`.
3. Install [`session_bootstrap.md`](session_bootstrap.md) as a project instruction or project-scoped Manus skill. This gives each session the exact identity, authority order, bootstrap procedure, and explicit memory lifecycle protocol.
4. Add the controlled L9 Governance Custom MCP server described below. The existing public connection may stay read-only; lifecycle requires a separate bearer-protected deployment.
5. Add the separate package-owned `l9-memory-manus` stdio Custom MCP connector described below. It is the only Manus connection for ordinary `memory.*` agent tools.
6. Create a **Manus-specific Infisical Machine Identity**. Give it project access that is limited to the required secret paths and permissions. A read-only initial capability needs only access to `GITHUB_TOKEN` in the chosen project scope.
7. Configure **Universal Auth** for that identity. Keep the Client ID and Client Secret outside this repository and outside Manus project/session environment.
8. Render a temporary local Custom MCP draft with `render_infisical_mcp_connector.py`. The renderer reads the Client Secret from a mode-0600 file and creates a mode-0600 draft with encrypted connector environment values.
9. Add that draft as the `l9-manus-infisical` Custom MCP server. Its command is the checked-in `serve_infisical_mcp.sh`; no remote URL, bearer header, or project environment secret is required.
10. Delete the temporary draft immediately after it has been accepted. Retain the client-secret source only in the approved operator secret store.

## Deploy the governance MCP service

The server uses streamable HTTP at `/mcp` and a health endpoint at `/health`. It is standard-library Python and uses the governance locked interpreter. A basic read/diagnostic deployment is:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh --port 8787
```

Expose that process through HTTPS. The endpoint must end in `/mcp`; do not place credentials in the URL. After `GET /health` responds with `{"status":"ok"}`, run `render_mcp_connector.py --help` and render a connector draft with the actual deployed endpoint. Then add the generated JSON through Manus **Settings → Integrations → Custom MCP Servers**. The draft uses Manus’s direct Custom MCP form mode so it does not attempt OAuth discovery on the intentionally custom endpoint.

The default public service exposes governance reads, search, status, validation, and skill inventory. Its optional `workspace` argument and bootstrap are refused because an unauthenticated caller must not inspect arbitrary local Git status or write readiness metadata. It intentionally does not list memory lifecycle tools.

## Enable the bounded memory lifecycle bridge

Lifecycle mode requires two distinct controls:

- A **governance-wrapper bearer token** protects Custom MCP requests. It is generated and stored outside the repository, then supplied to Manus only through the Custom MCP connector’s header field. It is not a memory credential.
- A **pre-launch signed Manus memory assertion** lets the local package identify the service as `manus`. `serve_mcp.sh` resolves it from the existing scoped local assertion/grant maps using `ops/memory/export_agent_assertion_env.sh`. The values are never printed, returned, or placed in a Manus project environment. If the maps do not exist, the service starts but lifecycle status is honestly `blocked`.

Launch the protected service with:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh \
  --auth-token-file /secure/path/l9-governance-mcp.token \
  --enable-memory-lifecycle \
  --port 8787
```

`--enable-memory-lifecycle` is rejected without `--auth-token-file`. The launcher rejects the human memory door and any non-Manus identity before it begins. It passes only the scoped signed Manus assertion, signing-key entry, and grant entry to the child process; a raw provider endpoint, provider bearer, or human secret is never configured.

Create the transient connector draft from a local token file:

```bash
.venv/bin/python environment/agents/adapters/manus/render_mcp_connector.py \
  --url https://governance.example.com/mcp \
  --token-file /secure/path/l9-governance-mcp.token \
  --output /tmp/l9-governance-manus.json
manus-config connector create --file /tmp/l9-governance-manus.json
rm -f /tmp/l9-governance-manus.json
```

The draft includes an `Authorization: Bearer …` header for the Custom MCP form only. Do not commit it, add it to `mcp-connector.json`, put it in a URL, print it, or paste it into task text. A separate public read-only connector does not need this header and must not receive lifecycle tools.

## Validate the protected connection

After the connector is enabled, verify the tool inventory and lifecycle posture from a Manus shell:

```bash
manus-mcp-cli tool list --server l9-governance
manus-mcp-cli tool call governance_status --server l9-governance --input '{}'
manus-mcp-cli tool call memory_lifecycle_status --server l9-governance --input '{}'
```

A correct protected deployment lists `memory_lifecycle_status`, `memory_lifecycle_start`, and `memory_lifecycle_close`. A status of `blocked` means the signed agent assertion is not available and must result in **memory-blind** operation. It is not safe to substitute a local-operator principal, a direct provider endpoint, a pasted credential, or a generic memory HTTP bridge.

When lifecycle status is `ready`, a Manus task calls `memory_lifecycle_start` before governed work and `memory_lifecycle_close` after the work has a concise, secret-free handoff summary. Start uses canonical bounded hydration; close reuses canonical continuation admission and idempotent memory close. The bridge does not offer ordinary agent writes, search, phase locks, or a generic shell. Those belong exclusively to the package-owned signed agent lane.

## Enable the package-owned ordinary memory MCP lane

`l9-memory-manus` is intentionally a **separate local stdio connector**, not an extension of `l9-governance` and not a remote HTTP/provider bridge. Its generated command launches the exact pinned `l9-memory-server --transport stdio` entrypoint after [`serve_memory_mcp.sh`](serve_memory_mcp.sh) has loaded only Manus’s scoped signed assertion, signing-key entry, and grant entry. Tool schemas, authorization, admission, conflict checks, and durable writes stay inside `l9-graphite-memory`.

Create a no-secret local connector draft from the authoritative checkout:

```bash
.venv/bin/python environment/agents/adapters/manus/render_memory_mcp_connector.py \
  --governance "$HOME/.cursor-governance" \
  --output /tmp/l9-memory-manus.json
manus-config connector create --file /tmp/l9-memory-manus.json
rm -f /tmp/l9-memory-manus.json
```

That no-secret draft supports a pre-provisioned host map only. To make the **same enabled connector** work in every Manus chat, render the encrypted connector environment from an existing Manus-scoped authority file:

```bash
.venv/bin/python environment/agents/adapters/manus/render_memory_mcp_connector.py \
  --governance "$HOME/.cursor-governance" \
  --authority-file /secure/path/manus-agent-tokens.local.json \
  --output /tmp/l9-memory-manus.json
manus-config connector create --file /tmp/l9-memory-manus.json
rm -f /tmp/l9-memory-manus.json
```

The authority file must contain **only** `agents_door_secret` and `agent_signing_keys.manus`; it must not contain the human door, any peer-agent key, a provider credential, or a pre-minted assertion. The renderer checks this scope, writes the temporary draft mode `0600`, and stores the map only as a Custom MCP encrypted environment value after approval. At launch, the wrapper validates it again, derives a Manus-only public grant from the canonical registry, materializes both maps under a unique mode-0700 process directory, unsets the connector value, and removes the directory at exit. This hard stop is required: a missing or over-broad assertion must never cause package memory tools to use the compatibility `local-operator` principal.

After connector discovery succeeds, verify package authority rather than a wrapper inventory:

```bash
manus-mcp-cli tool list --server l9-memory-manus
manus-mcp-cli tool call memory.capabilities --server l9-memory-manus --input '{}'
manus-mcp-cli tool call memory.search --server l9-memory-manus \
  --input '{"query":"current task","namespaces":["<authorized-namespace>"],"limit":5}'
```

The connector must list package-owned `memory.search`, `memory.hydrate`, `memory.write_agent`, `memory.phase_lock`, and `memory.write_governed` tools. A failed launch or unavailable connector is an honest **memory-blind** condition until either the host maps are provisioned or the connector has the approved Manus-scoped encrypted authority value. Do not replace it with a direct provider endpoint, an HTTP proxy, a local-operator fallback, a pasted token, or a generic governance tool.

## Runtime behavior (native Infisical)

The Infisical server sends the machine identity Client ID and Client Secret only to Infisical's Universal Auth login endpoint. It retains the resulting access token in process memory until shortly before expiry. For metadata listing it sends `viewSecretValue=false`. For invocation it reads exactly one manifest-declared secret, uses it in one fixed HTTPS request, serializes an allowlisted response subset, and refuses the response if the resolved value appears in it.

No MCP tool returns a secret value. There is no `get_secret`, `resolve_secret`, generic outbound HTTP, command execution, environment dump, or arbitrary capability-selection tool.

## Adding a capability

Edit `infisical_capabilities.json` and the accompanying tests in the same change. A capability must have a unique identifier, a single approved inventory key, a fixed HTTPS origin, an allowlisted method, strict caller argument regexes, a path template that uses only declared arguments, and an explicit response field allowlist. The adapter's Python validator and tests must be extended for every new upstream family before it can be used.

## Diagnostic checks

From a Manus workspace that has both an active Git repository and the governance checkout, run:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-mcp-test
make -C "$HOME/.cursor-governance" manus-install-check WS="$(pwd)"
make -C "$HOME/.cursor-governance" memory-egress-check
```

`manus-adapter-check` validates the committed governance and memory connector carriers, registry identity, package-launch boundary, and canonical lifecycle markers. `manus-mcp-test` validates the governance tool contract and lifecycle safety boundary. `manus-install-check` invokes only the shared bootstrap in diagnostic mode; it does not modify Manus account configuration. The memory egress check confirms neither the lifecycle wrapper nor the service acquired a provider transport. These checks do not authenticate to Infisical, create a Manus Custom MCP connector, or retrieve a secret. At runtime, use `infisical_status` for connector posture and `infisical_list_secret_metadata` for an explicit, value-free scope check.

## Operating limits

The current Manus Program Execution provider (`manus-cloud`) remains intentionally dormant until a Controller execution transport exists. This surface adapter does not change that status. Manus may perform ordinary in-session work under the shared L4 and publish-path gates, but it must not advertise a background execution bridge, a remote provider memory path, a secret capability, or a generic repository write API that the upstream packages do not supply.
