---
name: l9-secrets
description: bind a named credential (api key, token, password) from Infisical project cursor-governance as this surface's machine identity, in-process and never printed. use when a command must bind or check a credential, add a new secret, or translate a legacy openclaw-igorbot/* ref to its Infisical name. not for discussing secrets policy.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, infisical, secrets, capability-bind, fail-closed, ssot]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-11-02
---

# l9-secrets

## Purpose

Resolve credentials for Quantum-L9 agents from **Cursor-Governance** `ops/secrets/`
without printing values, Keychain, or asking the human first.

A name in Infisical project Cursor-Governance **is** the grant. Bind it via
`capability_bind.py` whenever a secret is required. Do not ask. Do not wait
for approval. Do not paste a token. Do not `hydrate --export` on a model
surface.

| Vault | Role |
|---|---|
| **Infisical** project `Cursor-Governance` (`prod`, path `/`) | App-key grant. Bind names (`GITHUB_TOKEN`, `SEMGREP_APP_TOKEN`, …). |
| **Machine identity** (the one bootstrap secret) | `L9_INFISICAL_CLIENT_ID` + `L9_INFISICAL_CLIENT_SECRET` in the environment settings (or an operator's `~/.infisical/l9-machine.json`). One dedicated, least-privilege identity per surface. Not AWS. |
| **AWS Secrets Manager** | Cursor's bootstrap (in place of a `.env`), unchanged: it seeds `~/.infisical/l9-machine.json` (`login_registry.py`). No new secret goes to AWS. Claude never uses AWS. Do not delete AWS SM objects. |

**Adding a secret:** create it in Infisical project `cursor-governance` (`prod`,
path `/`) under a bare env-var name, then add that name to `root_env_keys` in
`ops/secrets/infisical-cursor-governance.yaml` (the bind name gate). Never AWS
first (`CANONICAL_LAW.md` §14.1).

SessionStart owns the plane (`session_start_secrets.py`). The reporter is a
derived view. There is no Makefile `secrets-bind` target.

Values never go into git, logs, receipts, or chat.

## Law — bind Infisical before asking the human

**Hard rule:** If a task needs a credential, token, API key, or password, agents
MUST bind the Infisical name **before** asking the human.

1. `capability_bind.py --check NAME` (source only). SessionStart already probed
   `SEMGREP_APP_TOKEN`, `SONAR_TOKEN`, `GITHUB_TOKEN`, `CONTEXT7_API_KEY`.
2. Fetchers call `bind_first`. They do not require a `.env`.
3. The bind authenticates as this surface's Infisical machine identity —
   Claude: from the environment, no AWS; Cursor / operator: the profile seeded
   once from the AWS login seed (unchanged).
4. `source=aws` on an app key is a fault. `source=unbound` is a vault miss —
   not a reason to paste. `source=infisical-machine-absent` means the surface
   has no identity yet: say so; the operator sets it once.

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

**CANONICAL_LAW.md §14 / §14.1:** Infisical `GITHUB_TOKEN` (legacy ref
`openclaw-igorbot/github#token`) is the **sole** agent GitHub PAT. Do **not**
create a second PAT in any store; rotate it in Infisical.
Do **not** ask the human to click `github.com` UI when this PAT can finish the job.

## npm / GitHub Packages auth

Hosted / agent surfaces: use the same GitHub identity `git`/`gh` already have.
Do **not** paste `NODE_AUTH_TOKEN` into account Environment variables.

```bash
ops/secrets/gh_npm.sh npm ci
```

Hosted Claude SessionStart (`install.sh`) also runs `gh_npm.sh --install-userconfig`
into ephemeral user npm config when `CLAUDE_CODE_REMOTE` is set.

Trusted-operator Infisical (sole PAT in the vault) remains a separate wrapper:

```bash
ops/secrets/authed_npm.sh npm ci
ops/secrets/authed_npm.sh npm publish
```

Plain `NODE_AUTH_TOKEN` env is **not** honored by npm for the `@quantum-l9`
scoped registry unless an `.npmrc` line maps it. A committed
`_authToken=${NODE_AUTH_TOKEN}` line 401s when that env is empty — drop it;
CI should keep `NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` with `packages: read`.


## Interpreter

```bash
GOV="${HOME}/.cursor-governance"
[ -d "$GOV/ops/secrets" ] || GOV="${HOME}/Cursor-Governance"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
SECRETS="${GOV}/ops/secrets"
```

## Compact workflow

**Bind (every surface):**

1. `"$PY" "$SECRETS/capability_bind.py" --check NAME` — name and source only, never the value.
   A legacy ref works too: `--check 'openclaw-igorbot/github#token'` checks `GITHUB_TOKEN`.
2. In code: `capability_bind.bind("NAME")` / `bind_first(...)` — held in-process, never exported
3. `source=infisical-machine-absent` means this surface has no machine identity:
   the operator sets `L9_INFISICAL_CLIENT_ID` + `L9_INFISICAL_CLIENT_SECRET` once in the
   environment settings. Never paste anything into chat.
4. A remote MCP server that needs a key is a vault bridge
   (`ops/secrets/vault_mcp_bridge.py`, `vault-mcp-bridges.json`) — never a `${VAR}` header.

**AWS tools (Cursor bootstrap / operator only, never an agent path):**
`resolve_secret.py --ref … --check`, `make secrets-aws-sync`,
`port_aws_to_infisical.py --dry-run`.

See [references/infisical-protocol.md](references/infisical-protocol.md).

## Behavior rules

- Infisical key names at `/` match process env vars; `root_env_keys` is the gate.
- Legacy ref → name map: `ops/secrets/legacy_refs.py` (`openclaw-igorbot/<svc>#<key>` → `NAME`).
- Structured legacy copies live under `/aws/openclaw-igorbot/<suffix>/` (bootstrap seeds only).
- Do not store any machine identity's `client_secret` inside Infisical `/`; each identity's secret lives only where that surface starts (environment settings or the operator's profile file).
- UI session overlays (`ui-session-*`) ship `provisioned: false` until provisioned.
- No macOS Keychain. No Chrome Safe Storage / cookie decrypt.
- Never commit `.env` secret values or Playwright `storage_state` blobs.

## Resource map

- [references/infisical-protocol.md](references/infisical-protocol.md) — Cursor-Governance Infisical project, hydrate, layout
- [references/resolver-protocol.md](references/resolver-protocol.md) — legacy AWS resolver (Cursor / operator only)
- Runtime: `ops/secrets/capability_bind.py`, `ops/secrets/legacy_refs.py`
- Infisical inventory + name gate (IDs/keys only): `ops/secrets/infisical-cursor-governance.yaml`
- Legacy AWS inventory (operator): `ops/secrets/openclaw-igorbot.registry.yaml`
- Overlays: `ops/secrets/registry.overlays.yaml`
- Actions secret mirror (**operator-only**; hosted sessions get 403 on Actions secrets): `ops/secrets/sync_actions_secrets.py` + plan `ops/secrets/actions-secret-sync.json` — binds vault names in-process, `gh secret set` via stdin, `--dry-run` writes nothing
- Child-env exec for tools that read their own credential (Semgrep Pro):
  `ops/secrets/capability_exec.py` + `capability-exec.json` — registered entries
  only, secret in that child's environment only, output scrubbed
  (`AGENTS.md` → CI_PARITY_HOSTED_CLAUDE_V1). Never export the token instead.

## Validation

- `capability_bind.py --check NAME` reports `bound` (no secret value on stdout)
- Infisical inventory YAML contains project id/slug/key **names** only — never values
- Unit tests: `tests/ops/secrets/test_capability_bind.py` (Infisical bind, legacy-ref translation); `ops/secrets/test_aws_secrets.py` covers the Cursor AWS bootstrap tools (mocked AWS)
- Registry `source.authority: cursor-governance`

## Failure handling

| Code | Meaning | Next action |
|---|---|---|
| `<not-in-inventory>` | Name (or legacy ref) not in `root_env_keys` | Add the secret in Infisical and its name to `root_env_keys`; do not invent names |
| `unbound` | In the inventory but absent from the vault | Create it in Infisical project `cursor-governance` |
| `infisical-machine-absent` | No machine identity on this surface | Operator sets `L9_INFISICAL_CLIENT_ID` + `L9_INFISICAL_CLIENT_SECRET` |
| `LOGIN_REFUSED` | Infisical refused the identity (revoked, wrong secret) or unreachable | Rotate the identity's client secret in Infisical; re-set it |
| NOT_FOUND / RESOLUTION_ERROR | (Cursor / operator AWS tools) | Check `aws sts get-caller-identity`; prefer the Infisical name |
| AWS_CLI_NOT_FOUND | (Cursor / operator) aws CLI missing | Install AWS CLI v2 |
