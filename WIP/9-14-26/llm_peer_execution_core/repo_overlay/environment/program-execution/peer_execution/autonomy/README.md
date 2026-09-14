# Peer Execution bounded-autonomy runtime

This runtime is shared Peer Execution infrastructure. It was originally proven
inside the Claude Code adapter, but it is not owned by Claude Code and is not a
provider adapter.

It supplies provider-neutral bounded-concurrency mechanics beneath Program
Execution admission: dependency readiness, explicit resource locks, resumable
campaign state, leases, deterministic ready-set selection, isolated worktrees,
and join barriers. Program Execution remains the sole Program state authority.
Root `autonomy/` remains the canonical authorization/control plane and declares
`owns_program_state: false`.

Providers may expose capabilities that use this runtime. No provider may fork,
copy, or privately own these mechanics.

## Canonical path

`environment/program-execution/peer_execution/autonomy/`

## Validate

```bash
python3 environment/program-execution/peer_execution/autonomy/validate_autonomy.py
```

The runtime's historical Claude-facing environment variables remain accepted for
compatibility during migration. They are transport/surface compatibility only,
not ownership signals.
