---
name: l9-aws-secrets
description: resolve openclaw-igorbot aws secrets manager refs via the cursor-governance ops/secrets registry — use when an agent needs a registered secret by ref (secret_id#json_key), to sync the local aws inventory, ui-session stubs, or fail-closed credential checks without keychain or printing values.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, aws, secrets, openclaw-igorbot, registry, fail-closed, ssot]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-06
---

# l9-aws-secrets

## Purpose

Resolve registered AWS Secrets Manager refs under namespace `openclaw-igorbot/*` (region `us-east-1`) using the **Cursor-Governance SSOT** at `ops/secrets/`.

This repository **owns** the inventory. Sync pulls secret *names* (and JSON key names) directly from AWS — not from igorbot or any other git repo. Consumers (igorbot, bots, CI) depend on this registry.

Values never go into git, logs, receipts, or chat unless the human explicitly needs a one-shot programmatic capture.

## Law — check registry before asking the human

**Hard rule:** If a task needs a credential, token, API key, or password, agents
MUST attempt resolution via this skill / `ops/secrets/` **before** asking the
human. Asking first while the secret is already in AWS is a protocol failure.

1. `sync_secrets_registry.py` (or use current registry if fresh)
2. `resolve_secret.py --ref '…' --check` then resolve into the process env
3. Only after `UNREGISTERED` / `NOT_PROVISIONED` / `NOT_FOUND` may you ask —
   and you must name the failing ref

**Known aliases (non-exhaustive):**

| Need | Prefer ref |
|------|------------|
| `NODE_AUTH_TOKEN` / GitHub Packages `@quantum-l9/*` | `openclaw-igorbot/github#token` |
| GitHub API PAT for `gh` automation | `openclaw-igorbot/github#token` |
| Infisical Cursor UA (`INFISICAL_CLIENT_ID` / `_SECRET`) | `openclaw-igorbot/infisical-cursor#client_id` / `#client_secret` |
| Infisical Website-Bot bootstrap (`INFISICAL_PROJECT_ID`) | `openclaw-igorbot/infisical-website-bot#project_id` (+ `#client_id` / `#client_secret`) |
| PostHog personal / project keys | `openclaw-igorbot/posthog#personal_api_key` / `#project_api_key` |

## Interpreter

Prefer the governance locked venv:

```bash
GOV="${HOME}/.cursor-governance"
[ -d "$GOV/ops/secrets" ] || GOV="${HOME}/Cursor-Governance"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
SECRETS="${GOV}/ops/secrets"
```

## Compact workflow

1. Sync registry from AWS (refs only): `"$PY" "$SECRETS/sync_secrets_registry.py"`
2. Check a ref without printing the value: `"$PY" "$SECRETS/resolve_secret.py" --ref 'openclaw-igorbot/github#token' --check`
3. Programmatic resolve (stdout value only; never paste into chat/logs): capture stdout from resolve without `--check`
4. Fail closed on `UNREGISTERED`, `NOT_PROVISIONED`, AWS errors

## Behavior rules

- Ref format: `secret_id#json_key` (or bare `secret_id` for whole SecretString).
- Default gate: ref must appear enabled in `ops/secrets/openclaw-igorbot.registry.yaml`.
- New AWS secrets under `openclaw-igorbot/` are auto-added on sync; local annotations (mode/notes) are preserved.
- UI session overlays (`ui-session-*`, key `storage_state`) ship with `provisioned: false` until humans create the AWS secret.
- No dependency on Quantum-L9/igorbot (or any external repo) for inventory.
- No macOS Keychain. No Chrome Safe Storage / cookie decrypt.
- Never commit `.env` secret values or Playwright `storage_state` blobs.

## Resource map

- [references/resolver-protocol.md](references/resolver-protocol.md) — ID format, CLI flags, error codes
- Runtime: `ops/secrets/sync_secrets_registry.py`, `ops/secrets/resolve_secret.py`
- Registry SSOT: `ops/secrets/openclaw-igorbot.registry.yaml`
- Overlays: `ops/secrets/registry.overlays.yaml`

## Validation

- `resolve_secret.py --ref … --check` exits 0 and stdout contains `OK ref=` only
- Unit tests: `ops/secrets/test_aws_secrets.py` (mocked AWS)
- Registry `source.authority: cursor-governance`; no secret values in YAML

## Failure handling

| Code | Meaning | Next action |
|---|---|---|
| UNREGISTERED | Ref not in enabled registry | Run AWS sync; do not invent IDs |
| NOT_PROVISIONED | Overlay stub; AWS secret missing | Human provisions secret, re-sync |
| NOT_FOUND / RESOLUTION_ERROR | AWS/IAM/region issue | Check `aws sts get-caller-identity` and IAM |
| AWS_CLI_NOT_FOUND | aws CLI missing | Install AWS CLI v2 |
