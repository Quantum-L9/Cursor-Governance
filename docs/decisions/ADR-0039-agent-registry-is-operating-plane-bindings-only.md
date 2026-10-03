# ADR-0039: The agent registry holds operating-plane bindings only

## Status

Proposed

## Date

2026-10-03

## Supersedes

This ADR partially supersedes the identity-declaration role of `environment/agents/agent_registry.yaml` described in ADR-0031 (`agent_id` / `source` / `surfaces` per writer). The signed-door and dual-write-class decisions of ADR-0031 are not superseded by this ADR. See Consequences.

## Context

`environment/agents/agent_registry.yaml` (schema v2, version 2.2.0) currently mixes two kinds of data:

- **Identity:** `agent_id`, `source`, `surfaces`, `status`, and reserved identities such as `perplexity`, `perplexity-computer`, `l-cto` and `igorbot`.
- **Operating-plane bindings:** role, memory principal, token and signing-key environment names, assigned groups and adapter.

ADR-0038 moves canonical identity upstream. The registry therefore has to stop declaring identity and keep only the local bindings.

## Options Considered

1. **Keep both, and cross-check them against the projection.** This preserves current consumers, but leaves two places to edit an identity. Rejected.
2. **Split the registry into a new file and keep the old one as an alias.** This is a softer migration, but creates a third surface to keep consistent. Rejected.
3. **Rewrite the registry in place as `l9.cursor-governance.agent-bindings/v2`.** Each binding references `actor_ref` and `surface_refs`. `agent_id`, `source` and `surfaces` are derived from the reference fragments when rendering. **Chosen.**

## Decision

**`environment/agents/agent_registry.yaml` owns only these operating-plane bindings:**

- actor-to-surface assignment
- role
- memory principal
- token environment names
- assigned groups
- adapter
- binding status

**It must not declare these canonical properties:**

- actor or surface ids
- actor kind
- actor or surface lifecycle
- actor or surface aliases

The fields `agent_id`, `source`, `surfaces`, `actor_kind`, `actor_status`, `surface_status` and `aliases` are prohibited in a binding. `rendering:` derives `agent_id` and `source` from the `actor_ref` fragment, and derives `surfaces` from the `surface_refs` fragments.

## Consequences

This is a breaking schema change for registry consumers. These are not ported in this change, and must be ported or reconciled before merge:

- `ops/memory/agent_identity.py`
- `ops/memory/materialize_agent_authority.py`
- `environment/program-execution/integrations/agent-identity/registry_reader.py`
- `environment/program-execution/integrations/bootstrap/peer_context.py`
- `validate_agents.py`
- related tests under `tests/ops/memory/`

The supplied registry content also changes operating behavior beyond the schema move. Each of these items needs an explicit owner decision:

- **Claude Code:** `claude-code-desktop` and `claude-code-mobile` collapse into one `claude-code` binding. Surfaces become `claude-code-cli`, `claude-code-web` and `claude-code-mobile`. The `claude-code-desktop` and `claude-code-ide` surfaces exist upstream but are unbound here. The `constellation-gate` and `l9-ci-core` groups are dropped.
- **Human operator:** the `human` binding (private entrance, ADR-0031) and the `human-operator` role are removed. Upstream still registers the `human` actor and the `operator-shell` surface.
- **Signing keys:** all `signing_key_env` entries are removed. `legacy_token_env` is added for `cursor` and `claude-code`. ADR-0031's signed agent door depends on per-agent signing keys.
- **Reserved identities:** the reserved, unwired identities are removed: `perplexity`, `perplexity-computer`, `l-cto` and `igorbot`.
- **Memory contract section:** the shared memory contract section (realignment stage C9) is removed from the file.
- **Version number:** the file version goes from 2.2.0 to 2.0.0.
