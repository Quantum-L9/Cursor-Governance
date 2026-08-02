---
name: governance-backup
version: "1.0.0"
description: "Push GlobalCommands (.cursor-commands) to cryptoxdog/Cursor-Governance"
---

# /governance-backup — GitHub SSOT Backup

Dropbox `GlobalCommands/` is the **live SSOT**. This command commits and pushes it to [cryptoxdog/Cursor-Governance](https://github.com/cryptoxdog/Cursor-Governance).

## When to run

- End of every session (also runs automatically via `sessionEnd` hook after setup)
- After editing any file under `@.cursor-commands/`
- Before switching machines

## Command

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
```

With message:

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh "chore(governance): describe change"
```

From PlasticOS repo:

```bash
make governance-backup
```

## Dry run (commit locally, no push)

```bash
GOVERNANCE_BACKUP_DRY_RUN=1 bash .cursor-commands/ops/scripts/backup_to_github.sh
```

## Skip automatic backup for one session

```bash
export GOVERNANCE_BACKUP_SKIP=1
```

## Requirements

- `git` and network access
- `gh auth login` (or SSH/credential helper configured for GitHub)
- Dropbox SSOT at `$HOME/Dropbox/cursor governance/GlobalCommands/`

## Setup (once per machine)

```bash
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh
```

Installs `~/.cursor/hooks.json` sessionEnd hook + symlink to this backup script.
