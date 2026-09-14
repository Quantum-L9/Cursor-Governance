<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-09-13
/L9_META -->

# Manus adapter — thin L9 governance binding

This is the active Manus surface adapter for the `manus` registry identity. It
sits beside the Cursor and Claude Code adapters while deliberately consuming the
same upstream control planes rather than copying them. The canonical identity is
`environment/agents/agent_registry.yaml`; the binding topology is
`environment/agents/PEER_RUNTIME_BINDINGS.yaml`; the surface contract is
[`../ADAPTER_CONTRACT.md`](../ADAPTER_CONTRACT.md).

| Concern | Canonical owner | Manus binding |
|---|---|---|
| Identity | `agent_registry.yaml` | `environment.env.example` supplies the registry-derived values |
| Governance readiness | `ops/scripts/bootstrap_agent_environment.sh` | `install.sh --surface manus` delegates without reimplementation |
| Secrets and capabilities | `ops/secrets/` and the adapter contract | No credentials, provider URL, or secret resolver on the surface |
| Autonomy and L4 | `ops/autonomy/surface_profile.yaml` | Exact `manus` surface ID plus existing shared gates |
| Memory | Package-owned `l9-graphite-memory` | No connector until the memory package publishes a remote transport |
| Program Execution | `environment/program-execution/` | Existing `manus-cloud` provider remains explicitly dormant |

## What activates in Manus

Manus does not provide Cursor's persistent hook model or Claude Code's tracked
projection format. Its durable carrier is a **project instruction**. Install
[`session_bootstrap.md`](session_bootstrap.md) into the Manus project, then add
the non-secret values from [`environment.env.example`](environment.env.example)
to the same project or session environment. The bootstrap points each workspace
at the shared L9 installer and authority chain.

The local helper is intentionally small:

```bash
make -C "$HOME/.cursor-governance" manus-adapter-check
make -C "$HOME/.cursor-governance" manus-install WS="$(pwd)"
```

`manus-install` is not an account configurator. It validates the supplied git
workspace and delegates shared readiness to
`ops/scripts/bootstrap_agent_environment.sh --surface manus`. It cannot claim
that an external project instruction was installed, and it never fabricates a
remote memory connection.

## Current memory posture

The canonical memory server is package-owned and stdio-only. A remote Manus
surface has no sanctioned bridge to that process today. Accordingly,
[`mcp-connector.json`](mcp-connector.json) is an explicit `transport: none`
carrier, not a Custom MCP configuration template. The honest state is
**memory-blind** until an upstream remote transport exists. Do not restore a
direct provider endpoint, a bearer header, or a custom secret carrier to make
memory appear available.

## Current autonomy and publish posture

`L9_AUTONOMY_ENABLED=true` activates only the authority already defined for the
`manus` row in `ops/autonomy/surface_profile.yaml`. Local work stays bounded by
the shared L4 release gate. The first publication route is
`PR_REMEDIATE=0 make pr`; no adapter-specific raw publish, merge permission, or
breakglass is added here. Merge, force push, hard reset, and secret exfiltration
remain forbidden.

## Verification

```bash
make manus-adapter-check
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
```

For the precise project configuration and the explicit limitations, see
[`setup.md`](setup.md).
