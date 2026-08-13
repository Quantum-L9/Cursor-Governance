<!-- L9_META
l9_schema: 1
parent: l9-aws-secrets
layer: reference
role: protocol
tags: [aws, secrets, resolver, openclaw-igorbot, ssot]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-13
/L9_META -->

# Resolver protocol (AWS)

## Authority

**Cursor-Governance** owns `ops/secrets/openclaw-igorbot.registry.yaml`.
Sync source is **AWS Secrets Manager** (`list-secrets` + optional key-name inspect).
External repos must consume this registry — never the reverse.

Infisical project Cursor-Governance is the long-term **value** store. AWS remains
the **name inventory** SSOT and the Infisical Universal Auth bootstrap. See
[infisical-protocol.md](infisical-protocol.md).

## ID format

| Ref | Meaning |
|---|---|
| `openclaw-igorbot/github#token` | Secret `openclaw-igorbot/github`, JSON field `token` |
| `openclaw-igorbot/some-token` | Whole `SecretString` (plain or JSON text) |

Region: entry region → `AWS_REGION` → registry `region_default` → `us-east-1`.

## CLI

```bash
python ops/secrets/sync_secrets_registry.py [--refresh-keys] [--dry-run] [--json-summary]
python ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check
python ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token'   # value on stdout only
python ops/secrets/port_aws_to_infisical.py [--dry-run]   # AWS → Infisical prod
```

## Error codes (`resolve_secret`)

`UNREGISTERED`, `NOT_PROVISIONED`, `NOT_FOUND`, `NOT_JSON`, `FIELD_NOT_FOUND`,
`TIMEOUT`, `AWS_CLI_NOT_FOUND`, `RESOLUTION_ERROR`.

## Anti-patterns

- Fetching inventory from igorbot (or any other git repo)
- Keychain / browser-cookie3 as primary auth
- Echoing resolved values into chat, receipts, or git
- Inventing secret IDs not present in AWS or approved local overlays
- Asking the human before `--check` / Infisical list
