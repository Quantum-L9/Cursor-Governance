---
name: l9-ui-operator
description: portable saas dashboard ui operator — use when apis are insufficient and an agent must configure github packages, vercel, or similar admin ui via playbook plus site cartridges, loading l9-aws-secrets for refs without keychain.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, ui-operator, playwright, cartridges, playbook, aws-secrets]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-06
disable-model-invocation: true
---

# l9-ui-operator

## Purpose

Discoverable control plane for configuring SaaS dashboards when API/CLI is insufficient. Loads **`l9-aws-secrets`** for refs. Owns the operating playbook and drives `ops/ui-operator/console.py` with site **cartridges** (data only).

## Interpreter

```bash
GOV="${HOME}/.cursor-governance"
[ -d "$GOV/ops/ui-operator" ] || GOV="${HOME}/Cursor-Governance"
PY="${GOV}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
UI="${GOV}/ops/ui-operator"
```

Optional install (not required for validate/dry_run):

```bash
uv sync --extra ui-operator && playwright install
```

## Compact workflow

1. Read playbook: [playbooks/saas-dashboard-when-api-insufficient.md](playbooks/saas-dashboard-when-api-insufficient.md)
2. Load `l9-aws-secrets`; sync/check required refs
3. Prefer API; only then UI
4. Cartridge: use shipped YAML under `ops/ui-operator/cartridges/` or JIT-draft → human approve
5. Console:
   - `"$PY" "$UI/console.py" --cartridge github-packages-actions-access --mode validate`
   - `"$PY" "$UI/console.py" --cartridge … --mode dry_run`
   - `"$PY" "$UI/console.py" --cartridge … --mode run --approve` (session must be provisioned)
6. File receipt; never echo secret values

## Behavior rules

- Explicit-only (`disable-model-invocation: true`) — high blast radius UI mutations
- One altitude playbook; site detail lives in cartridges
- No Keychain / Chrome Safe Storage
- Fail closed on allowlist miss, missing approve, unprovisioned ui-session, PAT creation

## Resource map

- Playbook: [playbooks/saas-dashboard-when-api-insufficient.md](playbooks/saas-dashboard-when-api-insufficient.md)
- Runtime: `ops/ui-operator/console.py`, `jit_drafter.py`
- Schemas: `ops/ui-operator/schemas/`
- First cartridge: `ops/ui-operator/cartridges/github-packages-actions-access.yaml`
- Secrets: skill `l9-aws-secrets` → `ops/secrets/`

## Validation

- Cartridge validate exits 0
- Dry-run emits receipt `verdict: DRY_RUN` with refs ids only
- Unit tests: `ops/ui-operator/test_ui_operator.py`

## Failure handling

Stop and report `stop_reason` from the receipt. Do not invent selectors or widen `mutation_allowlist` without human approve.
