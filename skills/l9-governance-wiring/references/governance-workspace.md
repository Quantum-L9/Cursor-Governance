<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [governance, symlinks, workspace]
status: active
/L9_META -->

# Governance Workspace Wiring

Does NOT use wire_executor.py.

```bash
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"
bash .cursor-commands/ops/scripts/wire_governance_workspace.sh "$(pwd)"
```

Aliases: `/wire governance`, `/wire governance-workspace`, `/wire .cursor-commands`

Ensures `.cursor-commands` → `$HOME/.cursor-governance` SSOT and sessionEnd backup hook active.
