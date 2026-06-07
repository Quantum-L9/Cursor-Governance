<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [governance, backup, github]
status: active
/L9_META -->

# Governance Backup

Push GlobalCommands SSOT to cryptoxdog/Cursor-Governance.

```bash
bash .cursor-commands/ops/scripts/backup_to_github.sh
make governance-backup  # PlasticOS
```

Dry run: `GOVERNANCE_BACKUP_DRY_RUN=1`. Skip session: `GOVERNANCE_BACKUP_SKIP=1`.

Runs automatically via sessionEnd hook after setup_workspace_symlinks.sh.
