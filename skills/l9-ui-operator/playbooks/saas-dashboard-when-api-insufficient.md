# saas-dashboard-when-api-insufficient
# Operating playbook owned by l9-ui-operator (campaign altitude — not per-button).

## Purpose

Configure a SaaS dashboard via the portable UI operator when API/CLI is insufficient.
Uses `l9-aws-secrets` for refs and `ops/ui-operator/console.py` for execution.

## Preconditions

- AWS creds available; `ops/secrets/resolve_secret.py --check` works for required refs
- Cartridge exists under `ops/ui-operator/cartridges/` **or** JIT-drafted and human-approved
- For `--mode run`: `uv sync --extra ui-operator && playwright install`; ui-session provisioned

## Sequence

1. **Bind** target site + goal. Fail-closed if requested mutation is outside cartridge `mutation_allowlist` or listed in `forbidden`.
2. **Load `l9-aws-secrets`**. Resolve/check required refs (ids only in logs/receipts).
3. **Prefer API/CLI**. If API can complete the goal, do that and skip UI. If UI is required, record why in the receipt evidence notes.
4. **Load cartridge** or **JIT-draft** via `ops/ui-operator/jit_drafter.py`. New/changed cartridges require **human approve** (`--approve` on run; drafts stay under `drafts/`).
5. **Console execute**:
   - `validate` → shape + allowlist + ref registration
   - `dry_run` → walk journey without mutations
   - `run` → browser journey only after approve + provisioned session
6. **Emit receipt** under `ops/ui-operator/receipts/` (actor, ref ids, actions, verdict). Redact all secret values.
7. **Stop** on: missing AWS, unregistered ref, missing approve, visibility/destructive change, PAT creation requested, unprovisioned ui-session.

## Hard stop rules

| Condition | Action |
|---|---|
| Mutation not on allowlist | BLOCKED |
| `change_visibility` / destructive delete requested | BLOCKED |
| PAT creation requested | BLOCKED |
| `human_approve_required` and no `--approve` | BLOCKED |
| ui-session `NOT_PROVISIONED` on `--mode run` | BLOCKED |
| Keychain / Chrome cookie decrypt suggested | REJECT — use AWS SM refs only |

## First shipped cartridge

`github-packages-actions-access` — Manage Actions access on `@quantum-l9/graphiti-memory-client`.
