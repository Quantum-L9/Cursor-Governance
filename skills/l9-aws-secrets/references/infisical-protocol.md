<!-- L9_META
l9_schema: 1
parent: l9-aws-secrets
layer: reference
role: protocol
tags: [infisical, secrets, cursor-governance, openclaw-igorbot, ssot]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-13
/L9_META -->

# Infisical protocol (Cursor-Governance project)

## Purpose

How this agent hydrates and uses the Infisical project created for
Cursor-Governance. Identifiers and key **names** only — never secret values.

## Project (committed inventory)

SSOT for IDs + env-var key names: `ops/secrets/infisical-cursor-governance.yaml`.

| Field | Value |
|---|---|
| Host | `https://app.infisical.com` |
| Org slug | `infiscal-l9` |
| Project name | Cursor-Governance |
| Project slug | `cursor-governance` |
| Project id | `9f92179d-3caa-4d7a-90a9-bb896499bfe6` |
| Environment | `prod` (dev/staging exist; ported values live in prod) |
| Machine identity | `Cursor` (Universal Auth; shared with Website-Bot / SEO-Bot) |

Sibling Infisical projects (do not dump secrets into those): `SEO-Bot`,
`Website-Bot`, `l9-graphite-memory`.

## Chicken-egg bootstrap (AWS)

Infisical login credentials are **not** stored at Infisical `/`. Resolve AWS:

`openclaw-igorbot/infisical-cursor-governance`

| JSON key | Process env |
|---|---|
| `client_id` | `INFISICAL_CLIENT_ID` |
| `client_secret` | `INFISICAL_CLIENT_SECRET` |
| `project_id` | `INFISICAL_PROJECT_ID` |
| `env` | `INFISICAL_ENV` (`prod`) |
| `host` | `INFISICAL_SITE_URL` |

Org-level identity metadata (same UA) also lives at
`openclaw-igorbot/infisical-cursor` (`identity_id`, `org_id`, `org_slug`).

Login: `POST {host}/api/v1/auth/universal-auth/login` with `clientId` /
`clientSecret`. Never print `accessToken`.

## Layout

| Path | Contents |
|---|---|
| `/` | Env-var names (`GITHUB_TOKEN`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, …). This is what `@quantum-l9/infisical-config` injects. |
| `/aws/openclaw-igorbot/<secret-suffix>/` | 1:1 AWS JSON keys (structured port). |

`GH_TOKEN` is an alias of `GITHUB_TOKEN` (`CANONICAL_LAW.md` §14).

Infisical UA fields for `infisical-cursor`, `infisical-seo-bot`,
`infisical-website-bot`, and `infisical-cursor-governance` stay under
`/aws/openclaw-igorbot/<name>/` only — not flattened to `/`.

Full key-name list: `ops/secrets/infisical-cursor-governance.yaml` → `root_env_keys`.

## Re-port from AWS

```bash
python3 ops/secrets/port_aws_to_infisical.py --dry-run   # key names only
python3 ops/secrets/port_aws_to_infisical.py             # upsert prod
```

`--dry-run` prints key names and folder paths, never values. Live run upserts;
HTTP 429 is retried.

## Anti-patterns

- Asking the human for a key that is already in Infisical `/` or AWS
- Echoing Infisical or AWS values into chat, git, or receipts
- Creating a second GitHub PAT
- Using Website-Bot / SEO-Bot Infisical projects as this agent's vault
- Storing Infisical `client_secret` at Infisical `/`
