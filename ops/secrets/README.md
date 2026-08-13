# ops/secrets — AWS Secrets Manager registry (Cursor-Governance SSOT)

This directory owns the **openclaw-igorbot/\*** inventory for Quantum-L9 coding
workspaces. Other repos consume refs from here — they do not supply the
manifest back into Governance.

Infisical project **Cursor-Governance** (`cursor-governance`, prod) holds a
ported copy of every `openclaw-igorbot/*` AWS secret (env-var names at `/`,
structured copies at `/aws/openclaw-igorbot/<name>/`). Bootstrap Universal
Auth for that project is still in AWS as
`openclaw-igorbot/infisical-cursor-governance` (chicken-egg). See
`infisical-cursor-governance.yaml` (IDs and key names only).

## Layout

| Path | Role |
|---|---|
| `openclaw-igorbot.registry.yaml` | Committed registry (IDs + JSON key names + annotations only) |
| `infisical-cursor-governance.yaml` | Infisical project inventory (IDs + env key names, no values) |
| `port_aws_to_infisical.py` | Re-port AWS `openclaw-igorbot/*` → Infisical prod |
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
.venv/bin/python ops/secrets/port_aws_to_infisical.py --dry-run
.venv/bin/python ops/secrets/port_aws_to_infisical.py   # AWS → Infisical Cursor-Governance prod
```

## Rules

- Secret **values** never in git, logs, receipts, or chat
- No macOS Keychain / Chrome Safe Storage as primary auth
- Diagnose before mutating vault contents; prefer append of new secrets via AWS console/CLI then `secrets-sync`
- Skill: `l9-aws-secrets`
- **GitHub PAT SSOT:** `openclaw-igorbot/github#token` — sole agent GitHub
  credential (CANONICAL_LAW.md §14). Do not add a second PAT. Agents must use
  this ref and must not ask humans to click GitHub UI for operable API tasks.
