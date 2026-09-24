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
| `memory_class` | **Required.** One of `decision`, `insight`, `observation`, `constraint`, `episodic`, `semantic`, in canonical form. |
| `tags` | **Required.** 2–12 unique lowercase tags. Exactly one is `agent:<id>` (`claude-code`, `cursor`, …); at least one is a topic tag. |
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

### Classes: why canonical only

- `memory_write_governed` has no alias table in the 2.4.0 package, so
  `memory_class: "lesson"` fails there. The builder therefore maps legacy words
  (`lesson`→`insight`, `note`→`observation`, `rule`→`decision`), and the
  payload always carries the canonical class, which is valid on both tools.
- `procedural` is not on the `memory_write_agent` allowlist.
- `preference` and `identity` need a consent object that memory admission checks.
- `meta` is the class of the continuation record, which the hook lane writes.

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
