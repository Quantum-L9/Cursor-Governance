<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/generic/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-09-21
/L9_META -->

# Generic Adapter — future agent surfaces

Use this template only when a surface has no dedicated adapter. Read and follow
[`../ADAPTER_CONTRACT.md`](../ADAPTER_CONTRACT.md) first. An adapter is a thin
carrier for surface bootstrap, identity examples, and canonical-policy references;
it must not duplicate shared execution, autonomy, memory, or secret-resolution
logic.

Claude Code remains at `environment/agents/adapters/claude-code/`; do not
relocate or copy it here.

## 1. Register the identity

Register the surface in [`../../agent_registry.yaml`](../../agent_registry.yaml)
under the naming and ownership rules in the registry. The identity declaration is
reviewable metadata, not a credential. Validate the change before continuing:

```bash
make agents-env
make agents-runtime-bindings-validate
```

## 2. Create the thin surface carrier

Create `adapters/<agent-id>/` with only the artifacts required by the surface:

| Carrier | Requirement |
|---|---|
| Environment example | Identity fields such as `USER_ID`, `L9_MEMORY_AGENT_ID`, and `L9_MEMORY_SOURCE`; **no credentials** |
| MCP configuration | The canonical stdio memory runtime: `${L9_MEMORY_INTERPRETER} -m l9_graphite_memory.server --transport stdio` |
| Bootstrap instructions | Surface setup and role limits, referring to shared policy rather than copying it |
| README | Installation, supported capabilities, and explicit authority limits |

Do not add provider URLs, HTTP headers, bearer tokens, `env` secret blocks, or a
surface-local memory/secret resolver. A model-controlled surface never receives
raw secret material.

## 3. Bind the surface through shared control planes

The canonical memory runtime resolves its own configuration. If it is not bound,
report the surface as **memory-blind** and use the supported recovery commands:

```bash
make memory-binding
make memory-mcp-install
```

Capabilities are named requests handled on the trusted-operator side of the
boundary. Register capability references in `ops/secrets/capabilities.yaml` only
when an existing secret reference already exists; never place a token in an
adapter environment file.

## 4. Validate and publish

```bash
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
make program-execution-conformance
make peer-execution-validate
```

Publish only through `PR_REMEDIATE=0 make pr`. Raw `git push`, `gh pr create`,
and direct GitHub write tools are prohibited for all adapter surfaces.
