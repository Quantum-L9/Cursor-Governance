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

# Manus adapter — thin L9 governance binding

This is the active Manus surface adapter for the `manus` registry identity. It sits beside the Cursor and Claude Code adapters while consuming the same upstream control planes rather than copying them. The canonical identity is `environment/agents/agent_registry.yaml`; the binding topology is `environment/agents/PEER_RUNTIME_BINDINGS.yaml`; the surface contract is [`../ADAPTER_CONTRACT.md`](../ADAPTER_CONTRACT.md).

| Concern | Canonical owner | Manus binding |
|---|---|---|
| Identity | `agent_registry.yaml` | `environment.env.example` supplies the registry-derived values. |
| Governance readiness | `ops/scripts/bootstrap_agent_environment.sh` | `install.sh --surface manus` delegates without reimplementation. |
| Governance discovery | This adapter’s streamable-HTTP MCP service | Read/validate/bootstrap tools wrap existing upstream sources; no shell or write tool is exposed. |
| Secrets and capabilities | `ops/secrets/` and the adapter contract | No credentials, provider URL, or secret resolver is exposed on the surface. |
| Autonomy and L4 | `ops/autonomy/surface_profile.yaml` | Exact `manus` surface ID plus the existing shared gates. |
| Memory | Package-owned `l9-graphite-memory` | No connector until the package publishes a sanctioned remote transport. |
| Program Execution | `environment/program-execution/` | Existing `manus-cloud` provider remains explicitly dormant. |

## What activates in Manus

Manus does not provide Cursor's persistent hook model or Claude Code's tracked projection format. Its durable carrier is a **project instruction**. Install [`session_bootstrap.md`](session_bootstrap.md) into the Manus project, then add the non-secret values from [`environment.env.example`](environment.env.example) to the same project or session environment. The bootstrap points each workspace at the shared L9 installer and authority chain.

The local helper remains intentionally small:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-install WS="$(pwd)"
```

`manus-install` is not an account configurator. It validates the supplied Git workspace and delegates shared readiness to `ops/scripts/bootstrap_agent_environment.sh --surface manus`. It cannot claim that an external project instruction was installed, and it never fabricates a remote memory connection.

## L9 Governance MCP

`mcp_server.py` adds a narrow streamable-HTTP control plane so Manus can discover and verify the same governance sources available to peer coding surfaces. The server exposes six focused tools:

| Tool | Behavior | Mutation posture |
|---|---|---|
| `governance_status` | Reports governance, adapter, and optional workspace Git status. | Read-only. |
| `governance_validate` | Runs the existing Manus adapter validator; `full` also runs existing agent and PE descriptor validators. | Read-only. |
| `governance_read` | Reads bounded text from an allowlisted governance path. | Read-only. |
| `governance_search` | Searches bounded, allowlisted governance text. | Read-only. |
| `governance_list_skills` | Lists active L9 skill packs. | Read-only. |
| `governance_bootstrap` | Invokes the existing shared Manus installer for an explicit workspace. | Disabled unless the server is bearer-protected because `check` writes local readiness metadata; `apply` also requires `--allow-bootstrap-apply`. |

The MCP server is **not** a memory bridge. It does not expose the retired Graphiti URL, a bearer, a secret resolver, an arbitrary shell, arbitrary file access, repository-writing tools, or Program Execution scheduling. Manus continues ordinary repository work through its authorized workspace and GitHub integration; the server makes the existing L9 contract and readiness path directly available in a Manus task.

Launch a development or controlled-network instance with the locked governance interpreter:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh --port 8787
```

The public/default server exposes only the five read/validation tools. To enable `governance_bootstrap`, supply a token file managed outside the repository and launch with `--auth-token-file`; additionally pass `--allow-bootstrap-apply` for `apply` mode. Do not place the token in this repository, a command line, a project environment, or an MCP URL.

Use [`render_mcp_connector.py`](render_mcp_connector.py) to create a no-secret URL-mode Custom MCP connector draft after the service is available over HTTPS. The committed [`mcp-connector.json`](mcp-connector.json) is a deployment-neutral carrier, not a server URL or a memory connector.

## Current memory posture

The canonical memory server is package-owned and stdio-only. A remote Manus surface has no sanctioned bridge to that process today. The L9 Governance MCP does not alter this: the honest state remains **memory-blind** until an upstream remote transport exists. Do not restore a direct provider endpoint, bearer header, or custom secret carrier to make memory appear available.

## Current autonomy and publish posture

`L9_AUTONOMY_ENABLED=true` activates only the authority already defined for the `manus` row in `ops/autonomy/surface_profile.yaml`. Local work stays bounded by the shared L4 release gate. The first publication route is `PR_REMEDIATE=0 make pr`; no adapter-specific raw publish, merge permission, or breakglass is added here. Merge, force push, hard reset, and secret exfiltration remain forbidden.

## Verification

```bash
make manus-adapter-check
make manus-mcp-test
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
```

For the precise project configuration and the explicit limitations, see [`setup.md`](setup.md).
