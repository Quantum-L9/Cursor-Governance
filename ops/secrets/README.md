# ops/secrets — secret + capability control plane (Cursor-Governance SSOT)

> **Agent surfaces never receive raw secret material.** They request named
> capabilities; secret resolution happens only beyond the model-controlled trust
> boundary. See `capabilities.yaml` and `ADAPTER_CONTRACT.md` → *Capability carrier*.

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
| `resolve_secret.py` | Resolve `secret_id#json_key` (`--check` never prints values). **Operator only** |
| `capabilities.yaml` | Capability registry — maps capability ids to already-registered refs. Not a second inventory |
| `capability_registry.py` | Loader for `capabilities.yaml` |
| `capability_client.py` | **Model-side.** Reports capabilities as UNAVAILABLE (broker retired). Has no value-returning call at all |
| `capability_broker.py` | **Retired stub.** Implementation: `_archived/capability-broker/` |
| `broker_identity.py` | **Retired stub.** Same archive |
| `probe_broker.py` | **Retired stub.** Same archive |
| `surface_trust.py` | The one place that decides model-controlled vs trusted-operator |
| `bootstrap_agent_env.sh` | Shared capability bootstrap for every surface; denies `--export` on model surfaces |
| `hydrate_infisical.py` | Provider layer + **trusted-operator** CLI |
| `validate_capability_contract.py` | Regression barrier: fails the build on reintroduced secrets |
| `_archived/capability-broker/` | Never-shipped broker implementation (`git mv`, not a live server) |

## Architecture

```text
agent surface ──(named capability)──▶ capability_client ──▶ UNAVAILABLE (broker retired)
Infisical remains the secret SSOT on the trusted-operator side of the boundary.
```

Everything left of the boundary is assumed hostile: an LLM can read its own
environment, filesystem and child processes, so a secret placed there is a
secret the model possesses. The architecture removes raw-secret *possession*
rather than discouraging raw-secret *use*.

Two execution classes, default-deny:

| Class | Surfaces | Raw secrets |
|---|---|---|
| `model-controlled` | `claude-code`, `codex`, `gemini`, `manus`, `cursor`, `generic`, **and every unregistered id** | Denied |
| `trusted-operator` | `operator` / `broker` / `trusted-worker`, only from a runtime with no model-control markers | Permitted |

An `operator` claim raised from inside a model runtime is refused — a shell the
model can spawn cannot promote itself.

## Commands

```bash
make capability-check REQUIRE=sonar.read_issues,graphiti.query   # status only (UNAVAILABLE)
make capability-contract-validate                                # regression barrier
# capability-broker-preflight / broker-serve — retired (exit 2)
make secrets-sync          # AWS → local registry (operator)
make secrets-check REF='openclaw-igorbot/github#token'
# or:
.venv/bin/python ops/secrets/sync_secrets_registry.py
.venv/bin/python ops/secrets/resolve_secret.py --ref 'openclaw-igorbot/github#token' --check
.venv/bin/python ops/secrets/port_aws_to_infisical.py --dry-run
.venv/bin/python ops/secrets/port_aws_to_infisical.py   # AWS → Infisical Cursor-Governance prod
```

## Rules

- Secret **values** never in git, logs, receipts, or chat — and never in a
  model-controlled environment, argv, stdin/stdout/stderr, temp file, shell
  profile, `.env`, `.mcp.json`, workspace file or prompt
- **No generic raw-secret API.** `get_secret(name)`, `GET /secret/<name>` and
  `--print-secret` do not exist for model-controlled callers
- **No AWS bootstrap.** The instance-profile path to Universal Auth is removed,
  not merely unused
- Adding an integration = register a capability against an existing ref. It must
  never mean adding a token to an adapter env file, or changing every adapter
- No macOS Keychain / Chrome Safe Storage as primary auth
- Diagnose before mutating vault contents; prefer append of new secrets via AWS console/CLI then `secrets-sync`
- Skill: `l9-aws-secrets`
- **GitHub PAT SSOT:** `openclaw-igorbot/github#token` — sole agent GitHub
  credential (CANONICAL_LAW.md §14). Do not add a second PAT. Agents must use
  this ref and must not ask humans to click GitHub UI for operable API tasks.
