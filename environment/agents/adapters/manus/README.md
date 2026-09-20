<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 4.0.0
updated: 2026-09-19
/L9_META -->

# Manus adapter — thin L9 governance binding

This is the active Manus surface adapter for the `manus` registry identity. It sits beside the Cursor and Claude Code adapters while consuming the same upstream control planes rather than copying them. The canonical identity is `environment/agents/agent_registry.yaml`; the binding topology is `environment/agents/PEER_RUNTIME_BINDINGS.yaml`; the surface contract is [`../ADAPTER_CONTRACT.md`](../ADAPTER_CONTRACT.md).

| Concern | Canonical owner | Manus binding |
|---|---|---|
| Identity | `agent_registry.yaml` | `environment.env.example` supplies the registry-derived values. |
| Governance readiness | `ops/scripts/bootstrap_agent_environment.sh` | `install.sh --surface manus` delegates without reimplementation. |
| Governance discovery | This adapter’s streamable-HTTP MCP service | Read/validate/bootstrap tools wrap existing upstream sources; no shell or general write tool is exposed. |
| Secrets and capabilities | `ops/secrets/` | SessionStart bootstrap initializes the existing Infisical machine profile without returning secret values. |
| Autonomy and L4 | `ops/autonomy/surface_profile.yaml` | Exact `manus` surface ID plus the existing shared gates. |
| Memory agent lane | Package-owned `l9-graphite-memory` | A separate signed stdio Custom MCP connector starts the pinned package server directly for ordinary reads and writes. |
| Memory lifecycle | `ops/memory/hydration.py` and `ops/graphiti/hydration/close_session.py` | A bearer-protected MCP bridge invokes canonical hydrate and close under bounded `manus-session-*` envelopes. |
| Program Execution | `environment/program-execution/` | Existing `manus-cloud` provider remains explicitly dormant. |

## What activates in Manus

Manus does not provide Cursor’s persistent hook model or Claude Code’s tracked projection format. Its durable carrier is a **project instruction**. Install [`session_bootstrap.md`](session_bootstrap.md) into the Manus project, then add the non-secret values from [`environment.env.example`](environment.env.example) to the same project or session environment. The project instruction makes the explicit lifecycle start the first action in a governed task and makes lifecycle close the last action after the work result is complete.

The shared installer remains intentionally small:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-install WS="$(pwd)"
```

`manus-install` is not an account configurator. It validates the supplied Git workspace and delegates shared readiness to `ops/scripts/bootstrap_agent_environment.sh --surface manus`. It cannot claim that an external project instruction was installed. It does initialize the existing Infisical machine profile when its AWS preflight is authorized, then records only the profile/binding status in a local receipt.

## L9 Governance MCP

`mcp_server.py` adds a narrow streamable-HTTP control plane so Manus can discover and verify the same governance sources available to peer coding surfaces. A public/default service exposes only six focused governance tools:

| Tool | Behavior | Mutation posture |
|---|---|---|
| `governance_status` | Reports governance and adapter status; optional workspace Git status is available only on a bearer-protected service. | Read-only. |
| `governance_validate` | Runs the existing Manus adapter validator; `full` also runs existing agent and PE descriptor validators. | Read-only. |
| `governance_read` | Reads bounded text from an allowlisted governance path. | Read-only. |
| `governance_search` | Searches bounded, allowlisted governance text. | Read-only. |
| `governance_list_skills` | Lists active L9 skill packs. | Read-only. |
| `governance_bootstrap` | Invokes the existing shared Manus installer for an explicit workspace. | Disabled unless the server is bearer-protected because `check` writes local readiness metadata; `apply` also requires `--allow-bootstrap-apply`. |

The MCP server is **not** a provider bridge. It does not expose the retired provider URL, a secret resolver, an arbitrary shell, arbitrary file access, generic repository-writing tools, or Program Execution scheduling. Manus continues ordinary repository work through its authorized workspace and GitHub integration; the server makes the existing L9 contract and readiness path directly available in a Manus task.

### Canonical memory lifecycle mode

A protected deployment may additionally expose `memory_lifecycle_status`, `memory_lifecycle_start`, and `memory_lifecycle_close`. These tools are the Manus equivalent of peer lifecycle bindings, not a copied Claude hook implementation:

1. **Start is explicit rather than a fabricated platform hook.** `memory_lifecycle_start` invokes `canonical_hydrate` with the `manus-session-start` read-only envelope, persists only non-authoritative session evidence, and returns bounded canonical context. The task and session identifier are explicit because Manus does not publish a portable raw session-ID hook event.
2. **Close reuses the sole canonical authority.** `memory_lifecycle_close` passes a redacted, bounded summary to `close_session` under `manus-session-end`. That authority admits the continuation candidate, records the exact close obligation before calling `memory.close`, checks replay drift, and performs optional bounded distillation only after close. The bridge returns receipts and IDs, not the close summary or raw warnings.
3. **The service refuses local-operator fallback.** Both calls require the ADR-0031 signed Manus agent door (`L9_MEMORY_AGENTS_DOOR_SECRET`, `L9_MEMORY_AGENT_ASSERTION`, scoped signing key, and scoped grants). Missing material produces a names-only `blocked` result; it never silently writes as `local-operator`, and the human door is refused.
4. **Ordinary model writes remain package-owned.** The bridge does not proxy `memory.write_agent`, `memory.write_governed`, search, or phase locks. These are supplied by the separate signed `l9-memory-manus` Custom MCP connector, which launches the pinned `l9-memory-server --transport stdio` package process directly. No lifecycle receipt, phase lock, or close is required before an ordinary cold-safe agent write.

The launcher resolves a scoped assertion before it starts the protected process using `ops/memory/export_agent_assertion_env.sh`. It exports only Manus’s signing key and grant entry and never exports the human private door. The assertion source is an already-provisioned local secret/grant map; it is not fetched into the model environment and is never printed, committed, or included in a connector draft. If those maps are absent, the lifecycle connector remains safely usable for governance but reports memory as unavailable.

Launch controlled mode with the locked governance interpreter and a locally managed bearer token file:

```bash
bash environment/agents/adapters/manus/serve_mcp.sh \
  --auth-token-file /secure/path/l9-governance-mcp.token \
  --enable-memory-lifecycle \
  --port 8787
```

Use [`render_mcp_connector.py`](render_mcp_connector.py) to create a Custom MCP **form-mode** connector draft after the service is available over HTTPS. Passing `--token-file` adds the bearer header to the transient draft only; never commit the draft or token. The committed [`mcp-connector.json`](mcp-connector.json) is deployment-neutral and contains no URL, header, or credential.

## Package-owned ordinary memory MCP

The adapter now carries a **separate** [`memory-mcp-connector.json`](memory-mcp-connector.json) for ordinary agent memory activity. Its renderer, [`render_memory_mcp_connector.py`](render_memory_mcp_connector.py), produces a local stdio Custom MCP draft that starts [`serve_memory_mcp.sh`](serve_memory_mcp.sh). That launcher resolves the scoped Manus signed assertion before `exec`-ing the exact pinned `l9-memory-server --transport stdio` package entrypoint. No proxy translates tools, no wrapper stores a memory credential, and package-owned `MCPToolApplication` remains the tool authority.

This connector exposes the package’s canonical tools, including `memory.search`, `memory.hydrate`, `memory.write_agent`, `memory.phase_lock`, `memory.write_governed`, conflict checks, and package health/capability receipts. Memory authorization is determined by the signed Manus principal and its scoped grants inside the package. The connector does not expose the human door, promote or deletion authority beyond what the package grants, a provider endpoint, a generic shell, or lifecycle start/close. Lifecycle remains intentionally isolated in `l9-governance`.

The connection is intentionally fail-closed. A missing, partial, wrong-agent, or human-door assertion causes the stdio command to exit before the package can select its compatibility `local-operator` principal. Provision the assertion/grant maps on the host that launches the connector; never put raw door material in the Manus model environment, connector draft, repository, or task text.

## Current autonomy and publish posture

`L9_AUTONOMY_ENABLED=true` activates only the authority already defined for the `manus` row in `ops/autonomy/surface_profile.yaml`. Local work stays bounded by the shared L4 release gate. The first publication route is `PR_REMEDIATE=0 make pr`; no adapter-specific raw publish, merge permission, or breakglass is added here. Merge, force push, hard reset, and secret exfiltration remain forbidden.

## Verification

```bash
make manus-adapter-check
make manus-mcp-test
make memory-egress-check
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
```

For project configuration and deployment steps, see [`setup.md`](setup.md).
