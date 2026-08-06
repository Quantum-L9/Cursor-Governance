# ops/ui-operator — Portable SaaS UI console

Configure SaaS admin dashboards when API/CLI is insufficient. Driven by skill
`l9-ui-operator` and playbook `saas-dashboard-when-api-insufficient`. Auth refs
come from `ops/secrets` via `l9-aws-secrets`.

## Install (optional — not required for validate/dry_run)

```bash
make ui-operator-sync
# equivalent:
uv sync --extra ui-operator
playwright install
```

Playwright is **not** on the default `dev` extra and is **not** required for
`make pr`.

## Layout

| Path | Role |
|---|---|
| `console.py` | `validate` / `dry_run` / `run` (run needs `--approve` + provisioned ui-session) |
| `jit_drafter.py` | Draft cartridge scaffold → `drafts/` (human approve before promote) |
| `schemas/` | Cartridge + receipt schemas |
| `cartridges/` | Site journey data (e.g. `github-packages-actions-access`, Vercel stub) |
| `receipts/` | Generated receipts (gitignored content; refs ids only) |
| `drafts/` | Unapproved JIT drafts (gitignored content) |

## Quick start

```bash
.venv/bin/python ops/ui-operator/console.py \
  --cartridge github-packages-actions-access --mode validate

.venv/bin/python ops/ui-operator/console.py \
  --cartridge github-packages-actions-access --mode dry_run

# Live mutate — blocked until ui-session-* provisioned in AWS:
.venv/bin/python ops/ui-operator/console.py \
  --cartridge github-packages-actions-access --mode run --approve
```

Profiles (when provisioned) seed under `~/.l9-ui-profiles/<site>/` — never commit
storage_state blobs.
