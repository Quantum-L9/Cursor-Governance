# Agent memory write contract — `l9.agent_memory_write.v1`

A model never writes memory freehand. Every model-authored durable fact is **one
atomic fact in a fixed shape**: the arguments of one call to
`memory_write_agent`, or to `memory_write_governed` when a `task_signature` is
present. The agent builds those arguments with the builder and passes them to
the tool unchanged.

| | |
|---|---|
| Schema | [`schemas/l9.agent_memory_write.v1.schema.json`](schemas/l9.agent_memory_write.v1.schema.json) |
| Builder / checker | `ops/memory/agent_write.py` (`python -m ops.memory.agent_write`) |
| Parity test | `tests/ops/memory/test_agent_write_schema.py`: the code and the schema give the same verdict on every case |
| Tool | `mcp__l9-graphite-memory__memory_write_agent`; `…__memory_write_governed` when `task_signature` is present |

## How to write a fact

```bash
python -m ops.memory.agent_write build \
  --namespace "$(python -m ops.memory.cli resolve …  # write hint)" \
  --class decision \
  --content "Stop hooks gate on usable_receipt, not fresh_receipt, so degraded sessions still close" \
  --tag hooks --source-id Quantum-L9/Cursor-Governance#651
```

The command prints `{"tool": …, "arguments": {…}}`. Call that tool with those
arguments, unchanged. A payload built some other way is checked with
`python -m ops.memory.agent_write validate <file|->`. Both commands print
`REFUSED (l9.agent_memory_write.v1): <why>` and exit 1 when the payload does not
conform.

## The shape

| Field | Rule |
|---|---|
| `namespace` | **Required.** The repository namespace: the write hint from `python -m ops.memory.cli resolve`. It must be a lowercase slug. It must never be `main`, `master`, `default`, `test`, or the shared `l9-workspace`. |
| `content` | **Required.** One fact on one line, 12–600 characters. No `SESSION:` / `WORK:`-style preamble, no prose summary, never a credential. |
| `memory_class` | **Required.** A canonical class from the bound package's agent-lane allowlist (every class except `identity`), in canonical form. |
| `tags` | **Required.** 2–12 unique lowercase tags. Exactly one is `agent:<id>` (`claude-code`, `cursor`, …); at least one is a topic tag. The builder also stamps at most one `surface:<id>` — the derived SurfaceIdentity (`cursor-ide`, `claude-code-cli`, `claude-code-mobile`), never chosen by the caller. An unknown surface omits the tag. |
| `idempotency_key` | **Required.** The builder's default is `agent:<namespace>:<sha256(class, normalized content)[:16]>`, so the same fact written twice is one record, not two. |
| `source_id` | Evidence: a PR, commit, ADR or file path. |
| `subject`, `predicate`, `object` | An assertion triple, all three given together or none. |
| `supersedes`, `references` | Record ids (UUIDs), at most 20 each. |
| `confidence` | A number from 0 to 1. |
| `valid_from`, `valid_to` | ISO 8601 date-times. |
| `task_signature` | Present means the governed write, after `memory_phase_lock`. |
| `dry_run` | A self-check: returns the verdict without committing anything. |

No other field is allowed. In particular, `consent` and `source_trust` are not
agent-set.

### Classes: the bound vocabulary

The builder and the operator CLI call `resolve_memory_class` /
`agent_writable_class` on the bound `l9-graphite-memory`. They keep no
`CLASSES`, `ALIASES`, or `REFUSED_CLASSES` table. A missing package fails
the builder closed.

- `lesson` resolves to `procedural`. `note` resolves to `observation`.
  `pickup_context` and `session_summary` resolve to `episodic`.
- The payload always carries the canonical class.
- The agent lane accepts every class except `identity`: `constraint`,
  `decision`, `episodic`, `insight`, `meta`, `observation`, `preference`,
  `procedural`, `semantic`. `identity` is refused with the package's message.

## Boundaries (CANONICAL_LAW §8.6, ADR-0033, INV-03b)

- **The agent keeps this contract itself.** The builder does no memory I/O and
  constructs no client. It sits in front of no tool call: no hook, matcher,
  deny list or receipt stands between the agent and `memory_write_agent`.
  `tests/ops/memory/test_no_agent_lane_interposition.py` keeps it that way.
- **`MemoryService` still decides** identity, namespace grants, admission and
  quarantine. A refused write is the verdict. Report it; never reroute it
  through `memory.ingest` or the operator CLI.
- **Hard enforcement belongs in memory.** Making the server reject a
  non-conforming payload is a change to `l9-graphite-memory` admission, which
  lives upstream in that package, not in this repository.
- **No permission dialog.** The agent-lane tools are pre-approved in
  `settings.template.json` under the names Claude Code actually emits
  (`memory_write_agent`, …). The ordinary write runs with no popup.

## Signed agent identity: every memory names its author

A memory must name the agent that wrote it, and the operator must be able to
hold each surface accountable for what it wrote. The identity is therefore
**derived** at write time from markers the host sets on the running process.
It is never configured, so it cannot drift from where the code actually ran.
`ops/memory/agent_identity.py` is the one resolver, used by both memory lanes
and by the MCP launcher:

Two dimensions, never mixed. The **ActorIdentity** is the author and the
join key. The **SurfaceIdentity** says where that actor ran. Both names come
from the upstream registries pinned in `environment/agents/agent_registry.yaml`
(`identity_authority`).

| ActorIdentity | SurfaceIdentity | Derived from |
|---|---|---|
| `l9.actor-registry/global@1#cursor` | `l9.surface-registry/global@1#cursor-ide` | `CURSOR_AGENT`. Cursor wins when Claude markers are also present. |
| `l9.actor-registry/global@1#claude-code` | `l9.surface-registry/global@1#claude-code-cli` | Claude markers and local `CLAUDE_CODE_ENTRYPOINT=cli` |
| `l9.actor-registry/global@1#claude-code` | `l9.surface-registry/global@1#claude-code-mobile` | `CLAUDE_CODE_REMOTE=true` and `CLAUDE_CODE_ENTRYPOINT=remote_mobile` |
| `l9.actor-registry/global@1#claude-code` | `unknown` | Claude markers with any other entrypoint, including empty, `remote_web`, and `remote_unknown`. The `surface:` tag is omitted. |
| `l9.actor-registry/global@1#codex` | `unknown` | `L9_MEMORY_AGENT_ID=codex` and no host markers |
| `l9.actor-registry/global@1#gemini` | `unknown` | `L9_MEMORY_AGENT_ID=gemini` and no host markers |
| `l9.actor-registry/global@1#manus` | `unknown` | `L9_MEMORY_AGENT_ID=manus` and no host markers |

`claude-code-desktop` and `claude-code-ide` are canonical surfaces this plane does not assign. Missing evidence does not select them. `claude-code-web` is assigned and has no host marker, so it is not filled in. `perplexity`, `perplexity-computer`, `l-cto`, and `igorbot` are not actors. `human` is canonical and has no agent binding here.

`claude-code-desktop` and `claude-code-mobile` are also **historical
ActorIdentity aliases** of `claude-code`. Stored memories and receipts that
carry them stay readable and are never rewritten, but a new write never uses
them as its author (`agent:claude-code-desktop` is refused).

Agents without host markers are identified only by the `L9_MEMORY_AGENT_ID`
their own adapter sets, and only when it names `manus`, `codex`, or `gemini`.
Any other value is refused. Those three actors, plus `cursor` and
`claude-code`, are the resolver's set and are active rows in
`environment/agents/agent_registry.yaml`.

- **Configured values are ignored.** On these surfaces a configured
  `L9_MEMORY_AGENT_ID` or `USER_ID` is ignored, and SessionStart reports it as
  drift. `USER_ID` is always derived from the identity, for example
  `claude_code_agent`. Only agents without host markers of their own
  (manus, codex, gemini) are identified by `L9_MEMORY_AGENT_ID`, which their
  adapters set. That id does not select a surface.
- **No guessing.** Claude host markers prove the actor `claude-code`. The
  entrypoint proves a surface only for `cli` and `remote_mobile`. Every other
  entrypoint leaves `surface_identity: unknown` and omits the `surface:` tag.
  A process with no host markers and no admitted adapter identity has **no**
  actor, and every writer refuses to write and says why.
- **Release and runtime stay unknown on this binding.** The consumer pin is
  `l9-graphite-memory` 2.6.0. `release_identity` stays `unknown` until Memory
  publishes a digest-verified ReleaseIdentity under `l9.contract/product-release@1`.
  The pin's version, git SHA, and wheel digest are examined in provenance and
  are not that ref. `runtime_identity` stays `unknown`: the 2.6.0 rule points
  at the consumer runtime, and this process has no admitted runtime ref. A
  service RuntimeIdentity exists only for an admitted deployment at or after
  3.0.0 under `l9.product-kind-exception/memory-hosted-service@1`. That
  exception does not apply here. `constellation_identity` is omitted because
  it is outside both dimension lists. Package version, actor, surface, and
  hostname are not runtime identity. OAuth client ids are not identity.
- **Drift is refused.** When a caller names an identity that disagrees with the
  running surface (an explicit `agent_id`, or the builder's `--agent-id`), the
  write is refused as drift.
- **At spawn**, `ops/memory/run_memory_mcp.sh`:
  1. derives the identity;
  2. reads the local key maps in `~/.config/l9-memory` (on a hosted container
     it mints them first if they are missing), or `L9_MEMORY_AGENT_AUTHORITY_JSON`
     when a launcher deliberately supplies one;
  3. passes on only that identity's key, never the human door;
  4. derives the grants from `environment/agents/agent_registry.yaml`;
  5. mints the signed assertion.

  The server's principal is that identity, for example
  `claude-code-memory-client`. Without a door the server refuses to
  start. `L9_MEMORY_ALLOW_LOCAL_OPERATOR=1` is the announced operator opt-out.
- **SessionStart prints** `memory identity: <id> (derived from host markers)`,
  or `NONE` with the reason.

### Provisioning, once per surface

No key ever goes into the Claude Code environment settings. That field is
plaintext and model-readable, and by its own contract
(`environment/agents/adapters/claude-code/web/environment.env.example`) carries
no credentials. It does not need one: the memory server verifies the agent's
assertion against the door and keys handed to that same process
(`l9_graphite_memory/server.py`). So a key minted where the server runs is
exactly as valid as one minted anywhere else.

1. **Claude Code Mobile (hosted): nothing to do.** The container mints its own
   authority into `~/.config/l9-memory` (directory 0700, files 0600). This
   happens at environment setup (`web/setup.sh`) and, if that did not run, at
   MCP spawn (`run_memory_mcp.sh`):
   `python -m ops.memory.materialize_agent_authority --provision-hosted --governance ~/.cursor-governance`.
   The hosted identities come from `ops/memory/agent_identity.py`, and the
   grants from `agent_registry.yaml`. It only ever adds: an existing key is
   never replaced. SessionStart reports `signed-agent door: PROVISIONED`.
2. **Claude Code Desktop (workstation): once.** Existing keys are kept and no
   values are printed:
   `python -m ops.memory.materialize_agent_authority --add-keys-to ~/.config/l9-memory/agent_tokens.local.json --agent-id claude-code`
3. **Cursor:** its SessionStart mints the `cursor` door from the same local
   maps (`ops/hooks/session_start_bootstrap.sh`).
4. **Environment settings:** delete any `L9_MEMORY_AGENT_ID`, `USER_ID`,
   `L9_MEMORY_SOURCE` or `L9_MEMORY_AGENT_AUTHORITY_JSON` still there. The
   first three are ignored and reported as drift. The last is a credential in a
   plaintext field that the hosted container no longer needs.
   `web/environment.env.example` is the text to paste, and it sets none of them.
