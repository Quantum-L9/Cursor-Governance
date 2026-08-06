# ops/secrets — AWS Secrets Manager registry (Cursor-Governance SSOT)

This directory owns the **openclaw-igorbot/\*** inventory for Quantum-L9 coding
workspaces. Other repos consume refs from here — they do not supply the
manifest back into Governance.

## Layout

| Path | Role |
|---|---|
| `openclaw-igorbot.registry.yaml` | Committed registry (IDs + JSON key names + annotations only) |
| `registry.overlays.yaml` | Local stubs not yet in AWS (`ui-session-*`, `provisioned: false`) |
| `registry.schema.yaml` | Shape contract |
| `sync_secrets_registry.py` | Sync secret *names* (and optional key names) from AWS SM |
| `resolve_secret.py` | Resolve `secret_id#json_key` (`--check` never prints values) |

## Commands

```bash
make secrets-sync          # AWS → local registry
make secrets-check REF='openclaw-igorbot/github#token'
# or:
.venv/bin/python ops/secrets/sync_secrets_registry.py
.venv/bin/python ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check
```

## Rules

- Secret **values** never in git, logs, receipts, or chat
- No macOS Keychain / Chrome Safe Storage as primary auth
- Diagnose before mutating vault contents; prefer append of new secrets via AWS console/CLI then `secrets-sync`
- Skill: `l9-aws-secrets`
