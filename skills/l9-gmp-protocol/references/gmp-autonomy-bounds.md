# GMP autonomy bounds

GMP is a backup pipeline beside Program Execution. `/gmp` is the authorization
packet. Do not create a PE campaign packet. Do not admit a Program Lock. Do not
set `PR_BASE=origin/campaign/<id>`. Do not import or cite
`environment/contracts/autonomy`.

## Shared bounds (root `autonomy/` + `ops/autonomy/`)

- L4 local commits, no mid-work push: `ops/autonomy/l4_local.py`
- Lane / claim: max 4 total / 2 mutation when fanning Tasks
- No autonomous merge: `ops/autonomy/merge_gate.py`
- Native Task admission: `autonomy/adapters/cursor/host_bridge.py` opaque token
  per Task. If host_bridge is missing or the lease is denied, serialize on the
  main agent. Do not ask.

## Publish

`--mode start` / `--mode full` call `l4_local.py begin --contract-id gmp-<id>`
when `L9_L4_LOCAL_AUTONOMY` is on.

**Every surface** (Cursor, Claude Code desktop, Claude Code Mobile):
finalize calls `authorize-release`, then `PR_REMEDIATE=0 make pr` /
`l9 pr`. Do not run `make precommit-repo` then `make pr`. Cursor skips
the tree-kernel latch; adapters still fire it. Merge still requires
`/l9-pr-remediation` Converge. PR-poll Tasks spawn only after that
`make pr` opens a PR.

## Skill references to reuse (do not run PE steps)

- `skills/l9-bounded-autonomy/references/parallel-nondependent.md`
- `skills/l9-bounded-autonomy/references/pr-poll-subagent.md`
- `skills/l9-bounded-autonomy/references/join-and-merge-gate.md`

Do not run that skill's campaign-packet, `PR_BASE=origin/campaign/...`, or
`PR_REMEDIATE=0` steps on the GMP path.
