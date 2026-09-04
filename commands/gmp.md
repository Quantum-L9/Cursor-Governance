---
name: gmp
version: "9.1.0"
description: "Slash that Shells the GMP executor then Builds the named plan — no second confirm"
auto_chain: null
---

# /gmp — Governance Managed Process

`/gmp` is authorization. Do not ask. Cursor does not exec YAML; this file's last
block is the mechanical sequence the agent must run in the same turn.

Do not chain `/ynp`. Do not confirm scope. Do not wait for a Build button.

Load skill `l9-gmp-protocol`. Bounded-autonomy **references only**
(`parallel-nondependent`, `pr-poll-subagent`, `join-and-merge-gate`). Do not
create a Program Execution campaign packet. Do not import
`environment/contracts/autonomy`.

The LangGraph package under `workflows/dags/gmp/` remains a TTY/graph runtime.
The slash does not invoke it.

---

## EXECUTION (MANDATORY)

Resolve the plan path. Stop at the first hit. Do not ask.

1. First `*.plan.md` path in the `/gmp` message, workspace-relative.
2. The focused editor file when its name ends in `.plan.md`.
3. Miss with a non-empty remainder: `--mode full` (no Build).
4. Miss with an empty remainder: the executor exits `2` `NO_TASK`.

Path hit — run immediately:

```bash
GOV_PY="${HOME}/.cursor-governance/.venv/bin/python"
test -x "$GOV_PY" || GOV_PY="$(pwd)/.venv/bin/python"
test -x "$GOV_PY" || exit 1

"$GOV_PY" workflows/gmp_executor.py \
  --authorized-by slash-gmp \
  --plan <resolved.plan.md> \
  --mode start \
  --tier RUNTIME \
  "<task remainder or Build <resolved.plan.md>>"
```

Then **Build** the resolved `.plan.md` now (execute that plan in this turn, no
confirm). Tests once belong to that Build. Then:

```bash
"$GOV_PY" workflows/gmp_executor.py --resume --mode finalize --commit-when-done
```

Finalize is one path on every surface: L4 release when L4 is on, then
`PR_REMEDIATE=0 make pr` / `l9 pr`. Do not run `make precommit-repo`
then `make pr`. Do not merge. Do not start pytest in finalize.

Path miss + remainder:

```bash
"$GOV_PY" workflows/gmp_executor.py \
  --authorized-by slash-gmp \
  --mode full \
  --tier RUNTIME \
  "<remainder>"
```

Then run skill phases 2–6 on the main agent (no Cursor Build). Then `--mode finalize --commit-when-done` as above.

---


Path hit with a machine TODO list (optional; plan frontmatter todos still win
when `--plan` is set without `--todos-json`):

```bash
"$GOV_PY" workflows/gmp_executor.py \
  --authorized-by slash-gmp \
  --todos-json '@path/to/todos.json' \
  --mode start \
  --tier RUNTIME \
  "<task>"
```

`--todos-json` accepts an inline JSON list of `{id,task,files}` or a path /
`@path`. Authorized start/full fails fast at scope-lock when neither `--plan`
todos nor `--todos-json` provide a non-empty list.

## Interpreter

`GOV_PY` is `$HOME/.cursor-governance/.venv/bin/python`, else `$(pwd)/.venv/bin/python`.
If both are missing, exit 1. Do not fall back to `/usr/bin/python3`.

## Bounds

- L4 local commits; no mid-work push. Finalize is `authorize-release` then
  `PR_REMEDIATE=0 make pr` / `l9 pr` on every surface.
- Max 4 / 2 mutation Tasks. Admission via `autonomy/adapters/cursor/host_bridge.py`.
  If the lease is denied, serialize on the main agent. Do not ask.
- No autonomous merge.
- TTY without `--authorized-by` still uses USER_GATE.
