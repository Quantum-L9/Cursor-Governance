Cursor never runs this file by name. **`sessionStart` runs the bootstrap**, and the bootstrap runs this first, in the foreground, before it trusts `~/.cursor-governance`.

### What triggers it

Registered in `~/.cursor/hooks.json`:

```14:22:/Users/ib-mac/.cursor/hooks.json
    "sessionStart": [
      {
        "command": "./hooks/session-start-bootstrap.sh",
        "timeout": 60
      },
      {
        "command": "./hooks/code-graph-health.sh",
        "timeout": 15
      }
    ],
```

Every new Cursor chat/session fires that. Timeout is **60s**. The installed file is a real copy at `~/.cursor/hooks/session-start-bootstrap.sh`, not a symlink.

That bootstrap resolves the activator in this order, then execs it:

1. `$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh`
2. else `$HOME/.cursor/hooks/governance-activate-fresh.sh` (sidecar)
3. else chicken-egg shallow clone of the GitHub repo, then retry (1)

Manual triggers (same bootstrap, or the script alone):

```bash
make start WS="$(pwd)"          # L9_BOOTSTRAP_SYNC=1 — reconcilers stay foreground
bash "$HOME/.cursor-governance/ops/scripts/governance_activate_fresh.sh"
```

`setup_workspace_symlinks.sh` only **installs** the sidecar. It does not run activation.

### Sequence

```text
Cursor sessionStart (60s)
  ├─ session-start-bootstrap.sh          ← this is the entry
  │    1. resolve + RUN governance_activate_fresh.sh   (foreground, first)
  │    2. parse STATUS line (action / sha / remote_sha / detail)
  │    3. resolve SSOT (~/.cursor-governance)
  │    4. scratch_hold.py restore --all
  │    5. copy bootstrap + activator sidecars from tip SSOT
  │    6. background: Claude plugins, IDE profile, cold venv
  │    7. auto-wire .cursor-commands / plans / l9-governance plugin
  │    8. Graphiti env + SSH tunnel + health
  │    9. check_governance_wiring.sh
  │   10. session_start_memory_orchestrator.sh  (hydrate + code-graph fields)
  │   11. emit additional_context JSON (the L9 session state you see)
  │
  └─ code-graph-health.sh                ← parallel sibling hook (15s), not a child
```

Inside activate itself, **before a swap only**, it may call `backup_to_github.sh` so a dirty/ahead clone is pushed before the tree is moved to `.bak.*`. On success it writes `~/.cursor/governance-activate.last` and prints one `STATUS` line. It always exits 0.

### What does *not* run with it

| Script | Role |
|---|---|
| `governance_sync.sh` | Manual bidirectional reconcile. **Not** sessionStart tip activation. |
| `backup_to_github.sh` | session**End** hook (`governance-backup.sh`). Also pre-swap inside activate. |
| Graphiti hydrate | After activate, via the orchestrator. |
| `make pr` / hygiene | Unrelated. |

This session’s hydrate (`action=swapped detail=shallow_clone_swap`) is the STATUS line from step 1: the clone was not a clean fast-forward, so activate replaced `~/.cursor-governance` with a fresh shallow `origin/main`, then the rest of the bootstrap ran against that tip.
