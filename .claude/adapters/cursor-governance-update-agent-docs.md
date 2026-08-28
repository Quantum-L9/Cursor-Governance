# Cursor-Governance adapter — `l9-update-agent-docs`

First-match adapter for this repository. PlasticOS / Odoo inventory steps do **not** apply.

## Live write targets

| File | Role | Write rule |
|---|---|---|
| `ARCHITECTURE.md` | This-repo map (modules, CI/CD workflow index, version) | Managed. Refresh as a **pointer index**. |
| `INVARIANTS.md` | This-repo invariant index, CI enforcement map, cited false positives | Managed. Point at `ORG_INVARIANTS.yaml`; do not copy `L9-ORG-*` bodies. |
| `AGENTS.md` | Operating-instruction SSOT | `additive_only`. Append only. Do not fold. Do not re-dump CI / hook / skill tables that already live here. |
| `CLAUDE.md` | Load pointer | Managed. Keep short. No Always/Never lists. No CI tables. One-line maps-not-rungs pointer is enough. |
| `README.md` | Human index | Managed. Surgical pointers only. Required headings/pointers come from `skills/l9-update-agent-docs/references/pointer-heading-map.yaml` — fail closed via `validate_pointer_headings.py`; never generate the file. |

`CANONICAL_LAW.md` and `ORG_INVARIANTS.yaml` are out of scope for this skill.

## Pointer-not-dump contract

1. Every metric comes from a cited live file. Unverified counts are `Unknown`.
2. Do not paste `AGENTS.md` §4–6 tables, skill registries, or the YAML `invariants:` list into `ARCHITECTURE.md` / `INVARIANTS.md`.
3. Workflow map = file names + job ids + blocking vs janitor. Pins and full job prose stay in the workflow files.
4. False positives must cite **where** the exclude/ignore lives.
5. After adding a new root file, register it in `ops/config/root-file-protection.json` in the same change (`managed` if this skill must refresh it).

## Domain inventory

Skip Odoo / PlasticOS module inventory. Optional bind (do not invent packages):

- Top-level dirs: `ls` the repo root.
- Workflow count: files under `.github/workflows/` (not `WIP/**`).
- Hook count: hooks in `.pre-commit-config.yaml`.

## Step 7 for this repo

Treat root `ARCHITECTURE.md` and `INVARIANTS.md` as **live indexes**. Update surgically. Bump their Version when the map or exclusion citations change.
