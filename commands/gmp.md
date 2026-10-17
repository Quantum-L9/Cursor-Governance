---
name: gmp
version: "10.0.0"
description: "Slash that Shells the GMP executor then Builds the named plan — no second confirm"
auto_chain: null
---

# /gmp — Governance Managed Process

`/gmp` is authorization. Do not ask. Cursor does not exec YAML; this file's last
block is the mechanical sequence the agent must run in the same turn.

Do not chain `/ynp`. Do not confirm scope. Do not wait for a Build button.

This file is the only `/gmp` teaching surface. Bounded-autonomy **references
only** (`parallel-nondependent`, `pr-poll-subagent`, `join-and-merge-gate`). Do
not create a Program Execution campaign packet. Do not import
`environment/contracts/autonomy`.

`/gmp` works in every governed repo. Cursor-Governance supplies the tools (its
venv, `workflows/gmp_executor.py`, `l4_local.py`, the memory CLI, and the
Makefile). The clone being edited is `WORK`, the caller's git toplevel. The
executor locks, records, and commits there, and mutates Cursor-Governance only
when it is that clone.

The LangGraph package under `workflows/dags/gmp/` remains a TTY/graph runtime.
The slash does not invoke it.

## Run contract

The executor enforces the lock and the outcome tokens. The agent owns the rest.

1. **Lock.** The plan's todos (their `file` fields) are the modification lock.
   The executor confines them to `$WORK` (`OUT_OF_WORKSPACE` otherwise) and
   prints `READY_FOR_BUILD`. Edit only locked files and the tests the plan
   names. A needed file outside the lock: stop, add it to the plan, re-run start.
2. **Ground truth.** Before each edit, confirm the target exists in `$WORK` and
   the anchor you replace is unique. A miss is a stop, not a guess.
3. **Protected paths.** Protected paths come from the work repo:
   `$WORK/AGENTS.md`, `$WORK/.cursor/rules/`, `$WORK/CODEOWNERS`.
   Cursor-Governance carries none for consumers.
4. **Memory evidence.** Run
   `(cd "$GOV" && "$GOV_PY" -m ops.memory.cli conflicts --workspace "$WORK")`
   and declare `MEMORY_PREFETCH:` from the canonical receipt: `namespace`,
   `snapshot_digest`, `checked_record_count`, `conflicts` (count or record ids),
   `policy_version`. It is evidence only. It never gates the edit and never
   locks the repository.
5. **Verify.** Before finalize, `git -C "$WORK" status --porcelain` and
   `git -C "$WORK" diff --name-only` must name only locked files, the plan's
   tests, and `reports/`. Anything else: stop and report it.
6. **Evidence.** The executor writes `$WORK/reports/<gmp_id>-<slug>.md`. The
   finish reply lists files changed, tests run with pass or fail, and the PR
   URL or the reason there is none.

Outcome tokens (all exit `2`): `NO_WORKSPACE` (no git toplevel), `NO_PLAN`
(the named plan is not a file), `NO_SCOPE` (no todos), `OUT_OF_WORKSPACE` (a
todo escapes `$WORK`), `NO_TASK` (full mode with no task).

---

## EXECUTION (MANDATORY)

Resolve the plan path. Stop at the first hit. Do not ask.

1. First `*.plan.md` path in the `/gmp` message. The executor tries it as
   absolute, then under `$WORK`, then `~/.cursor/plans/<name>`.
2. The focused editor file when its name ends in `.plan.md`.
3. Miss with a non-empty remainder: `--mode full` (no Build).
4. Miss with an empty remainder: the executor exits `2` `NO_TASK`.

Every block starts with this prefix:

```bash
GOV="${HOME}/.cursor-governance"
GOV_PY="${GOV}/.venv/bin/python"
GOV_EXEC="${GOV}/workflows/gmp_executor.py"
test -x "$GOV_PY" || exit 1
test -f "$GOV_EXEC" || exit 1
WORK="$(git rev-parse --show-toplevel)" || exit 1
```

Path hit — run immediately:

```bash
"$GOV_PY" "$GOV_EXEC" \
  --workspace "$WORK" \
  --authorized-by slash-gmp \
  --plan <resolved.plan.md> \
  --mode start \
  --tier RUNTIME \
  "<task remainder or Build <resolved.plan.md>>"
```

Then **Build** the resolved `.plan.md` now (execute that plan in this turn, no
confirm). Tests once belong to that Build. Then:

```bash
"$GOV_PY" "$GOV_EXEC" --workspace "$WORK" --resume --mode finalize --commit-when-done
```

Then publish the work clone through the governance Makefile:

```bash
"$GOV_PY" "$GOV/ops/autonomy/l4_local.py" --workspace "$WORK" authorize-release
PR_REMEDIATE=0 make -C "$GOV" pr WS="$WORK"
```

Do not run `make precommit-repo` then `make pr`. Do not merge. Do not start
pytest in finalize.

Path miss + remainder:

```bash
"$GOV_PY" "$GOV_EXEC" \
  --workspace "$WORK" \
  --authorized-by slash-gmp \
  --mode full \
  --tier RUNTIME \
  "<remainder>"
```

Then apply the Run contract on the main agent (no Cursor Build). Then
`--mode finalize --commit-when-done` and publish as above.

---


Path hit with a machine TODO list (optional; plan frontmatter todos still win
when `--plan` is set without `--todos-json`):

```bash
"$GOV_PY" "$GOV_EXEC" \
  --workspace "$WORK" \
  --authorized-by slash-gmp \
  --todos-json '@path/to/todos.json' \
  --mode start \
  --tier RUNTIME \
  "<task>"
```

`--todos-json` accepts an inline JSON list of `{id,task,files}` or a path /
`@path` under `$WORK`. Authorized start/full fails fast at scope-lock when
neither `--plan` todos nor `--todos-json` provide a non-empty list.

## Interpreter

`GOV_PY` is `$HOME/.cursor-governance/.venv/bin/python`. If it is missing,
exit 1. Do not use a workspace venv or `/usr/bin/python3`: the executor needs
the governance imports.

## Bounds

- L4 local commits; no mid-work push. Finalize is `authorize-release` then
  `PR_REMEDIATE=0 make pr` / `l9 pr` on every surface (from a consumer, the
  `make -C "$GOV" pr WS="$WORK"` form above).
- Max 4 / 2 mutation Tasks. Admission via `autonomy/adapters/cursor/host_bridge.py`.
  If the lease is denied, serialize on the main agent. Do not ask.
- No autonomous merge.
- TTY without `--authorized-by` still uses USER_GATE.
