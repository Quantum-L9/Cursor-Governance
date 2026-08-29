<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 2.0.0
updated: 2026-08-12
/L9_META -->

# Agent surface adapter contract

Every agent surface adapter is thin. Claude Code is not a gold-standard thick
adapter and no peer catches up by copying Claude implementation.

## Surface responsibilities

A surface adapter may carry only surface discovery/bootstrap, memory endpoint
configuration, identity environment examples, and references to canonical
shared policy. It MUST NOT own Program lifecycle, scheduler logic, autonomy
policy, memory semantics, execution budgets, canonical receipts, or duplicated
execution machinery.

## Memory carrier

Graphiti HTTPS front door:

```text
${GRAPHITI_MCP_URL}
```

**No adapter MCP template carries a bearer.** The capability broker
(`L9_CAPABILITY_BROKER_URL`) never shipped and is retired. Cursor uses the
local Graphiti CLI / SSH tunnel. Adapter surfaces use `GRAPHITI_MCP_URL`.
An adapter template that interpolates `Authorization: Bearer ${GRAPHITI_MCP_TOKEN}`
is a contract violation.

The direct cloud endpoint `https://memory.quantumaipartners.com/graphiti/mcp`
is now reachable only from behind the broker. `ops/graphiti/mcp.json.example`
is the separate trusted-operator (Cursor SSH tunnel) shape and is not an
adapter template.

Writer identity is separate and comes from `agent_registry.yaml` through
`USER_ID`, `L9_MEMORY_AGENT_ID`, and `L9_MEMORY_SOURCE`. Surface adapters never
invent a second `agent_id`.

## Publish path

`PR_REMEDIATE=0 make pr` is the only sanctioned way any surface reaches GitHub.
It runs the Makefile checkers, then pushes and opens the PR through
`ops/scripts/open_pr_after_gate.sh`.

This is **mechanically enforced**, not a convention. `ops/autonomy/local_execution_gate.py`
denies raw `git push`, `gh pr create`, `gh pr edit`, `make push`, and the MCP
`create_pull_request` / `push_files` tools — on every surface, through the
Claude PreToolUse hook and the Cursor `beforeShellExecution` hook alike.

L4 and the publish path are different questions and are enforced separately:

| Question | Owner |
|---|---|
| *When* may this workspace reach a remote at all? | L4 release receipt |
| *How* must it reach GitHub when it may? | publish-path enforcement |

Being `release_authorized` therefore does **not** permit a raw push — that would
skip the checkers the receipt was granted on the strength of.

`ops/scripts/bootstrap_agent_environment.sh` proves the rule is live on each
surface at startup: it feeds the gate a raw `git push` and requires a deny, and
`make pr` and requires an allow. A surface where that cannot be proven is
reported DEGRADED rather than assumed safe.

Breakglass is human/ops only: `L9_PUBLISH_PATH_OVERRIDE=<reason>`. It must never
be set in a surface environment file, and it does not bypass L4 — an
unauthorized workspace still denies.

## Capability carrier

> **Agent surfaces never receive raw secret material. Agent adapters request
> named capabilities from the canonical shared capability plane. Secret
> resolution occurs only beyond the model-controlled trust boundary.**

This doctrine binds every present and future adapter. It replaces the former
"secret carrier" model, under which a surface held `INFISICAL_CLIENT_SECRET`,
could fall back to AWS, and hydrated downstream tokens with
`eval "$(... --export ...)"`. All three are now prohibited on model-controlled
surfaces.

The reasoning is not about trusting a particular model. Everything an LLM can
execute can read that LLM's environment, filesystem, process arguments and
child-process environment. A secret placed there is a secret the model
possesses, however careful the surrounding code is. So the architecture removes
raw-secret *possession* rather than discouraging raw-secret *use*.

```text
agent surface ──(named capability)──▶ L9 broker ──(workload identity)──▶ Infisical ──▶ upstream
              ◀──(sanitized result)──┘        [trust boundary]
```

`ops/secrets/` remains the SSOT inventory. `ops/secrets/capabilities.yaml` maps
capability ids onto refs already registered there — it is a mapping, never a
second inventory.

The bootstrap is shared, not per-surface. Every adapter calls the identical
entrypoint and passes its own surface id:

```bash
bash ops/secrets/bootstrap_agent_env.sh --check --surface <surface-id> \
  --require-capabilities sonar.read_issues,semgrep.appsec_scan,graphiti.query
```

### Execution classes

| Class | Surfaces | Raw secrets |
|---|---|---|
| `model-controlled` | `claude-code`, `codex`, `gemini`, `manus`, `cursor`, `generic`, **and every unregistered id** | Denied |
| `trusted-operator` | explicit `operator` / `broker` / `trusted-worker`, only from a runtime with no model-control markers | Permitted |

Trust is never inferred from the absence of a known surface id. An unknown
surface is model-controlled, so a new adapter cannot acquire secret access by
failing to register. An `operator` claim raised from inside a model runtime is
refused — a shell the model can spawn cannot promote itself.

Rules binding on every surface, present and future:

- An adapter environment file carries **no credentials at all**. Adding an
  integration means registering a capability in `ops/secrets/capabilities.yaml`
  against an existing ref — never appending a token to an adapter env file.
- `--export` is **denied** on every model-controlled and unregistered surface,
  by the shell bootstrap and independently by `hydrate_infisical.py`, so
  bypassing one gate buys nothing.
- No adapter implements its own resolver, vault path, broker, or bootstrap
  script. A surface-specific copy is a contract violation.
- There is **no generic raw-secret API**. `get_secret(name)`, `GET /secret/<name>`
  and `--print-secret` do not exist for model-controlled callers, and the broker
  serves no route that returns secret material.
- Values never reach git, logs, receipts, or chat. `--check` reports capability
  names and status only.
- A broker that cannot be reached is **DEGRADED, reported, and non-fatal** —
  adapters degrade and continue rather than aborting the session. An outage is
  never reported as a passing check.
- A capability that cannot be delivered is a *delivery* problem. Do not ask a
  human to paste a credential into a surface environment to work around it.

## Executable peer carrier

Execution topology lives only in `environment/agents/PEER_RUNTIME_BINDINGS.yaml`.
Each binding declares:

```yaml
surface: claude-cli
provider_ref: claude-code-direct
execution_profile_ref: worker-default
```

`agent_ref` belongs to the peer entry, not the provider descriptor. Program
Execution resolves the binding, applies the execution profile, and invokes the
provider through `environment/program-execution/peer_execution/`.

Provider-specific Program modules are thin. Shared lifecycle, permissions,
context, budgets, transports, telemetry, receipts, and admitted-dispatch
concurrency live upstream.

## Autonomy

Root `autonomy/` is the canonical authorization/control plane and never owns
Program state. Shared bounded-concurrency mechanics live at
`environment/program-execution/peer_execution/autonomy/`, not under a provider adapter.

## Validation

```bash
make agents-env
make agents-runtime-bindings-validate
make program-execution-adapters
make program-execution-conformance
make peer-execution-validate
make peer-execution-probe
make peer-execution-conformance
```

Thin-provider violations are merge-blocking.
