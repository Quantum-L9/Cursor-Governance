---
name: l9-aws-secrets
description: resolve credentials from cursor-governance ops/secrets (aws secrets manager openclaw-igorbot refs and infisical project cursor-governance) — use when an agent needs an api key, token, password, infisical hydrate, aws secret ref, registry sync, or fail-closed credential check without keychain or printing values.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, aws, infisical, secrets, openclaw-igorbot, registry, fail-closed, ssot]
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-08-13
---

# l9-aws-secrets

## Purpose

Resolve credentials for Quantum-L9 agents from **Cursor-Governance** `ops/secrets/`
without printing values, Keychain, or asking the human first.

Two vaults, one inventory:

| Vault | Role |
|---|---|
| **Infisical** project `Cursor-Governance` (`cursor-governance`, env `prod`) | Long-term secret store. Env-var names at `/`. Structured AWS port at `/aws/openclaw-igorbot/<name>/`. |
| **AWS Secrets Manager** `openclaw-igorbot/*` (`us-east-1`) | Name inventory SSOT + chicken-egg Infisical Universal Auth bootstrap. |

This repository **owns** the inventory. Consumers (igorbot, bots, CI) depend on
`ops/secrets/` — do not reverse the dependency.

Values never go into git, logs, receipts, or chat unless the human explicitly
needs a one-shot programmatic capture.

## Law — check inventory before asking the human

**Hard rule:** If a task needs a credential, token, API key, or password, agents
MUST attempt resolution via this skill **before** asking the human. Asking first
while the secret is already in AWS or Infisical is a protocol failure.

1. Prefer current `ops/secrets/openclaw-igorbot.registry.yaml` + `infisical-cursor-governance.yaml` (IDs/keys only). Sync AWS if stale.
2. `--check` the AWS ref, then resolve into the process env (stdout value only; never paste).
3. For day-to-day app keys after bootstrap: Infisical `prod` path `/` using env-var names (`GITHUB_TOKEN`, `DEEPSEEK_API_KEY`, …).
4. Only after `UNREGISTERED` / `NOT_PROVISIONED` / `NOT_FOUND` may you ask — and you must name the failing ref.

**Known aliases (non-exhaustive):**

| Need | Prefer ref / Infisical key |
|------|------------|
| `NODE_AUTH_TOKEN` / GitHub Packages `@quantum-l9/*` | `openclaw-igorbot/github#token` → Infisical `GITHUB_TOKEN` / `GH_TOKEN` |
| GitHub API PAT for `gh` automation | same (`CANONICAL_LAW.md` §14 — sole agent PAT) |
| Infisical Cursor UA | `openclaw-igorbot/infisical-cursor#client_id` / `#client_secret` |
| Infisical Cursor-Governance project (this agent vault) | `openclaw-igorbot/infisical-cursor-governance#project_id` (+ `#client_id` / `#client_secret` / `#env`) |
| Infisical Website-Bot / SEO-Bot bootstrap | `openclaw-igorbot/infisical-website-bot#project_id` / `…/infisical-seo-bot#project_id` |
| DeepSeek (Claude Code Anthropic-compatible) | `openclaw-igorbot/deepseek#apikey` → Infisical `DEEPSEEK_API_KEY` |
| OpenRouter / Perplexity / PageSpeed / SEO-Bot / DataForSEO | `openclaw-igorbot/<name>#apikey` → matching `*_API_KEY` in Infisical `/` |
| PostHog | `openclaw-igorbot/posthog#personal_api_key` / `#project_api_key` |

**CANONICAL_LAW.md §14:** `openclaw-igorbot/github#token` is the **sole** agent
GitHub PAT. Export `GH_TOKEN` / `GITHUB_TOKEN`. Do **not** create a second PAT.
Do **not** ask the human to click `github.com` UI when this PAT can finish the job.

## Interpreter

```bash
GOV="${HOME}/.cursor-governance"
[ -d "$GOV/ops/secrets" ] || GOV="${HOME}/Cursor-Governance"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
SECRETS="${GOV}/ops/secrets"
```

## Compact workflow

**AWS (inventory + bootstrap + fail-closed check):**

1. `"$PY" "$SECRETS/sync_secrets_registry.py"` — refs/key names only
2. `"$PY" "$SECRETS/resolve_secret.py" --ref 'openclaw-igorbot/github#token' --check`
3. Capture stdout from resolve **without** `--check` into the process env — never paste into chat
4. Fail closed on `UNREGISTERED`, `NOT_PROVISIONED`, AWS errors

**Infisical (agent vault after bootstrap):**

1. Resolve `openclaw-igorbot/infisical-cursor-governance` into `INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, `INFISICAL_PROJECT_ID`, `INFISICAL_ENV=prod`, `INFISICAL_SITE_URL`
2. Universal Auth login → list/get secrets at `/` by env-var name
3. Re-port from AWS: `"$PY" "$SECRETS/port_aws_to_infisical.py"` (`--dry-run` first)

See [references/infisical-protocol.md](references/infisical-protocol.md).

## Behavior rules

- AWS ref format: `secret_id#json_key` (or bare `secret_id` for whole SecretString).
- Default AWS gate: ref must appear enabled in `ops/secrets/openclaw-igorbot.registry.yaml`.
- Infisical key names at `/` match process env vars. Structured copies live under `/aws/openclaw-igorbot/<suffix>/`.
- Do not flatten Infisical UA `client_secret` to Infisical `/` (chicken-egg). Bootstrap stays in AWS.
- New AWS secrets under `openclaw-igorbot/` are auto-added on sync; local annotations are preserved.
- UI session overlays (`ui-session-*`) ship `provisioned: false` until humans create the AWS secret.
- No macOS Keychain. No Chrome Safe Storage / cookie decrypt.
- Never commit `.env` secret values or Playwright `storage_state` blobs.

## Resource map

- [references/resolver-protocol.md](references/resolver-protocol.md) — AWS ID format, CLI flags, error codes
- [references/infisical-protocol.md](references/infisical-protocol.md) — Cursor-Governance Infisical project, hydrate, layout
- Runtime: `ops/secrets/sync_secrets_registry.py`, `ops/secrets/resolve_secret.py`, `ops/secrets/port_aws_to_infisical.py`
- AWS registry SSOT: `ops/secrets/openclaw-igorbot.registry.yaml`
- Infisical inventory (IDs/keys only): `ops/secrets/infisical-cursor-governance.yaml`
- Overlays: `ops/secrets/registry.overlays.yaml`

## Validation

- `resolve_secret.py --ref … --check` exits 0 (no secret value on stdout)
- Infisical inventory YAML contains project id/slug/key **names** only — never values
- Unit tests: `ops/secrets/test_aws_secrets.py` (mocked AWS)
- Registry `source.authority: cursor-governance`

## Failure handling

| Code | Meaning | Next action |
|---|---|---|
| UNREGISTERED | Ref not in enabled AWS registry | Run AWS sync; do not invent IDs |
| NOT_PROVISIONED | Overlay stub; AWS secret missing | Human provisions secret, re-sync |
| NOT_FOUND / RESOLUTION_ERROR | AWS/IAM/region or Infisical auth issue | Check `aws sts get-caller-identity`; re-login Universal Auth |
| AWS_CLI_NOT_FOUND | aws CLI missing | Install AWS CLI v2 |
