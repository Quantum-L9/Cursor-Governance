# Post-publish handoff contract

Two handoffs are written once per publication, after `make pr`, by two Stop hooks
that Claude Code runs **in parallel**. They answer different questions and land in
different namespaces:

| | Repository handoff | Governance handoff |
|---|---|---|
| File the agent writes | `.l9/memory/handoff.json` | `.l9/memory/governance-handoff.json` |
| Schema id | `l9.session_handoff.v1` | `l9.governance_handoff.v1` |
| JSON Schema | [`schemas/l9.session_handoff.v1.schema.json`](schemas/l9.session_handoff.v1.schema.json) | [`schemas/l9.governance_handoff.v1.schema.json`](schemas/l9.governance_handoff.v1.schema.json) |
| Enforced by | `ops/memory/session_handoff.py` | `ops/memory/governance_handoff.py` |
| Stop hook | `memory_writeback.py` | `governance_handoff_writeback.py` |
| Namespace | the **in-scope repository's**, only | **`cursor-governance`**, only |
| Hook surface | `claude-session-end` | `claude-governance-handoff` (namespace-restricted) |
| Record | carried inside the ONE continuation record the close already writes | ONE `observation` record |
| Content | where the contract stands | environment friction, blockers, degraded bootstrap |
| Cap | 32 KiB brief | 12 KiB brief, 16 KiB record |

The JSON Schemas are the machine form of the code, and
`tests/ops/memory/test_handoff_schemas.py` holds them to the same verdict on every
case. Its table is generated per section of each schema, and each fixture
carries the verdict both must reach. That covers:
- missing required fields, a wrong `schema`, and bad `pr_number` values;
- unknown keys, and sections placed in the wrong file;
- sections that are absent, null or empty;
- bare-string shorthand, structured items, and whitespace-only strings;
- 40 against 41 items, and oversized values.

When the two disagree, that test fails. The code is what runs.

Two rules cannot be expressed in JSON Schema. Each schema states them in its own
text, and each has its own test:
- the aggregate byte cap of the normalized brief;
- `pr_number` equal to this publication's number.

## Repository handoff — `l9.session_handoff.v1`

Required: `schema`, `pr_number`, `objective`, `status`. Every other section is a
list, and an empty section is `[]`.

| Section | Item shape | Meaning |
|---|---|---|
| `objective` | string | what this contract set out to do |
| `status` | string | where things stand right now |
| `published` | string | what shipped in this PR |
| `completed` | string | done and verified |
| `not_completed` | `{item, reason}` | not done, and why |
| `blocked` | `{item, blocker, unblock}` | blocked, by what, and what unblocks it |
| `decisions` | `{decision, rationale}` | decisions made |
| `conflicts` | `{conflict, resolution}` | conflicts met, and how resolved (or `open`) |
| `human_actions` | `{action, where, why, then}` | what the human must do elsewhere, and what to do on return |
| `next_actions` | string | the next concrete steps |
| `open_questions` | string | still open |
| `risks` | string | known risks |
| `verification` | string | commands run and their results |

## Governance handoff — `l9.governance_handoff.v1`

Required: `schema` and `pr_number`. This file carries environment and governance
material **only**. Nothing about the product work goes here.

| Section | Item shape | Meaning |
|---|---|---|
| `environment_friction` | `{item, detail, impact}` | what got in the way; evidence; cost |
| `blockers` | `{item, blocker, unblock}` | environment or governance blockers |
| `degraded_bootstrap` | `{component, detail}` | bootstrap components or hooks seen degraded |
| `workarounds` | `{item, workaround}` | what was done instead |
| `governance_actions` | `{action, where, why}` | settings, files or secrets a human must change |

The hook adds an **observed** block to the record. It is copied verbatim from
receipts and never written by the agent:

- the bootstrap receipt, read through `ops/scripts/claude_bootstrap_receipt.py`, when its verdict is not `ready`;
- the SessionStart prefetch receipt, when it is `degraded`;
- hook skips logged in `~/.l9/claude/hook-skips.log` since this session started.

As a result, a degraded bootstrap is recorded even when the agent wrote no brief.

## Rules shared by both files

- **Bound to the publication.** `pr_number` must equal the `number` in
  `.l9/pr/pr-summary.json`. A brief for another PR is refused.
- **Closed shape.** An unknown top-level key is refused. A section put in the
  wrong file is refused, and the error names the file it belongs in, for example
  `governance_friction belongs in .l9/memory/governance-handoff.json`.
- **Items.** A bare string is shorthand for the object's required field.
  Whitespace is collapsed. A value over 1200 characters is truncated with an
  ellipsis. Each section holds at most 40 items. An optional field that is
  absent, `null`, empty or whitespace-only is omitted. Any other non-string
  value in an optional field is refused.
- **`pr_number`** is a positive integer. `7.0` is the integer 7, as it is to
  JSON Schema. A boolean is not a number.
- **Hooks never author content.** Both hooks validate, normalize, cap and render
  what the agent wrote. The only non-agent content is the verbatim receipt copy
  described above (CANONICAL_LAW §8.6, INV-03b).

## Lifecycle: once per publication

1. `make pr` writes `.l9/pr/pr-summary.json`. A publication counts as this
   session's only if that file post-dates the session's prefetch receipt.
2. **First Stop after the publication.** If either file is missing or invalid,
   `memory_writeback.py` blocks that Stop **once**. Its single request gives both
   shapes and says why each file was refused. Only this hook ever blocks, because
   Claude Code does not document how two parallel `decision: block` outputs
   combine. `governance_handoff_writeback.py` only arms its ledger and stays
   silent.
3. **Next Stop.**
   - The repository close runs with the brief if it is valid; otherwise it
     closes without it and says so.
   - The governance hook writes its record, or reports what is missing.
   - Both hooks run in parallel, and each announces its own outcome.
4. **After that.** Nothing more for that publication. Each hook keeps its own
   ledger: `.l9/memory/handoffs/` and `.l9/memory/governance-handoffs/`.

A subagent or background Stop never closes or hands off. A **degraded**
hydration still closes, because the hooks check `usable_receipt` rather than
`fresh_receipt`.

`environment/agents/adapters/claude-code/tests/test_post_publish_stop_state_machine.py`
runs both hooks' real `main()` together, in either order, as one state machine.
It asserts that one publication and any number of Stops produce at most:
- one repository close;
- one governance result;
- one block, which always comes from the repository hook.

It also asserts that the persisted ledgers do not depend on which hook ran
first. A seeded random walk extends this over hundreds of sequences. If a
ledger is lost, both hooks retry under the same publication-scoped idempotency
key, so the store replays rather than writing twice.

## Announcements: loud by design

Every outcome after a publication is announced to the user as a Stop-hook
`systemMessage`. Nothing fails silently.

| Hook | Outcomes |
|---|---|
| `memory_writeback.py` | `L9 MEMORY HANDOFF — WRITTEN / PARTIAL / FAILED`, with `HANDOFF NOT CAPTURED` when the brief was missing |
| `governance_handoff_writeback.py` | `L9 GOVERNANCE HANDOFF — WRITTEN / PARTIAL / FAILED / NOT CAPTURED / NOTHING TO REPORT` |

A governance brief with every section empty, and nothing observed, writes **no
record**, so nothing clutters the store. It is still announced as
`NOTHING TO REPORT`.

Every written record is announced with its id and a `verify` command that runs
the operator CLI `search` from any later session.
