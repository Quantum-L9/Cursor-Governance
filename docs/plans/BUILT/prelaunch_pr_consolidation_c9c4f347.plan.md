---
name: Prelaunch PR Consolidation
overview: "Consolidate the genuinely-useful, non-superseded fixes from PRs #90/#91/#92 into one clean branch off origin/Staging (then close the three originals). Drops everything already on Staging and fixes a latent matcher.py AttributeError plus a hardcoded-path debug leak."
todos:
  - id: preflight
    content: Commit validated semgrep overhaul to its own branch off Staging; create fix/prelaunch-consolidation off origin/Staging
    status: completed
  - id: geolocalize
    content: "Apply #92 geolocalize cleanup: remove _dbg/hardcoded path, add _geo_backfill_param + config_params.xml + manifest bump"
    status: completed
  - id: logistics
    content: "Apply #92 load_dashboard fresh-DB probe fix + __init__ import reorder + logistics manifest bump"
    status: completed
  - id: intake-flags
    content: "Add #91 has_metal/is_metalized/has_fr computed fields + _compute_material_flags (fixes matcher.py latent crash); verify material codes & phantom-enum; bump intake manifest"
    status: completed
  - id: acl
    content: "Add #91 intake.match ACL rows to security_base (verify no dup in plasticos_intake); row-level evaluate buyer_match_engine ACL (likely skip)"
    status: completed
  - id: dev-tools-guard
    content: "Apply #90 ci/check_dev_tools_fence.py hardening (manifest already fenced; do not touch manifest)"
    status: completed
  - id: housekeeping
    content: "Apply #92 .gitignore, AGENTS.md + .cursor rule capitalization, ADR-002/003, Odoo Compiler Prompt doc"
    status: cancelled
  - id: validate-push
    content: "ruff + make pr-check, push consolidation branch, open PR, close #90/#91/#92 with superseded matrix"
    status: cancelled
isProject: false
---

# Prelaunch PR Consolidation — integrate only the useful fixes from #90/#91/#92

One fresh branch off `origin/Staging`, re-applying only the non-superseded hunks (re-create edits rather than `git cherry-pick`, since each PR mixes superseded + useful work). Then close #90, #91, #92. CodeRabbit skipped review on all three (path filters); SonarCloud passed (0 new issues) — no bot findings to action.

## Superseded — DO NOT re-apply (verified against `origin/Staging`)
- [#90] `plasticos_dev_tools/__manifest__.py` `installable/auto_install` — Staging already `False`.
- [#90] `tests/test_repo_dependency_integrity.py` `EXPECTED_VERSION` bump — Staging already `19.0.2.2.0`.
- [#90] phantom-enum allowlist `png/webp/gif/jpeg/partner_name/exc_type` — already in Staging [tests/test_phantom_enum_values.py](tests/test_phantom_enum_values.py) (L725-737). The pasted "Phase 1A" additions are moot (also: the geolocalize `_dbg` keys vanish once cleanup lands).
- [#92] `plasticos_admin_dashboard/models/admin_dashboard.py` rep-perf JOIN — Staging already has `LEFT JOIN plasticos_offer o ON o.intake_id = i.id` (L737).
- [#92] `plasticos_matching/security/ir.model.access.csv` removal of `access_match_result_all` — already absent on Staging.
- [#90] `.github/workflows/pr-gate.yml` `continue-on-error` — `pr-gate.yml` is a disabled/manual workflow; near-zero value. Recommend skip.

## Not addressed by any of the 3 PRs (flag only, out of scope)
Audit P0-1 (`crm_bridge auto_install:True`), P0-2 (`commission_locked` column guard), P1-1 (`action_send_offers` partner guard), P1-4 (financial MTD filter). Track separately.

## Step 0 — Preserve the in-flight semgrep work, branch off Staging
The current branch `fix/geolocalize-nominatim-throttle` (= PR #92) has my **validated, green** semgrep overhaul as uncommitted edits ([.semgrep/odoo-patterns.yml](.semgrep/odoo-patterns.yml), [Makefile](Makefile), [.github/workflows/ci.yml](.github/workflows/ci.yml)) + untracked `reports/GMP-Report-134-*.md`.
- Commit those to their own branch `fix/semgrep-rules-overhaul` off `origin/Staging` (separate PR — already passes `make pr-check`).
- Then: `git fetch origin && git checkout -b fix/prelaunch-consolidation origin/Staging`.
- Note ordering interaction: the load_dashboard fix (Step 2) uses an f-string `CREATE VIEW`. The semgrep `odoo-sql-injection` rule already exempts `def init(self)`, so the two branches are compatible regardless of merge order.

## Step 1 — Geolocalize cleanup (source #92) — removes hardcoded-path leak
Confirmed Staging [plasticos_geolocalize/models/res_partner_geo.py](plasticos_geolocalize/models/res_partner_geo.py) STILL contains `_LOG_PATH = "/Users/macm2/.../debug-75e499.log"` + `_dbg()`.
- `res_partner_geo.py`: remove `import json`, `_LOG_PATH`, `_dbg()` and all `_dbg(...)` calls; set `_BATCH_SIZE = 25`; add `_geo_backfill_param(key, default, cast, minimum)` (fail-soft `ir.config_parameter` read, justified `.sudo()`); in `cron_geo_backfill` read `nominatim_delay/failure_delay/batch_size/max_consecutive_failures` and use them; change `except Exception as exc:` to `except Exception:` where `exc` is now unused.
- New [plasticos_geolocalize/data/geolocalize_config_params.xml](plasticos_geolocalize/data/geolocalize_config_params.xml): 4 `ir.config_parameter` records in `<odoo noupdate="1">` (nominatim_delay=1.1, failure_delay=5.0, batch_size=25, max_consecutive_failures=3).
- `plasticos_geolocalize/__manifest__.py`: version `19.0.1.0.0` -> `19.0.1.1.0`; add `data/geolocalize_config_params.xml` to `data` before `data/cron_geo_backfill.xml`.

## Step 2 — Logistics load_dashboard fresh-DB crash fix (source #92)
Confirmed Staging lacks the probe and imports `load_dashboard` 3rd (before `transaction_inherit`).
- [plasticos_logistics/models/load_dashboard.py](plasticos_logistics/models/load_dashboard.py): add `information_schema.columns` probe for `plasticos_transaction.load_id`; branch `has_tx_link` selecting `tx_columns`/`tx_join` (real columns vs `NULL::` casts); build VIEW via f-string; keep both `# nosemgrep: odoo-raw-sql` comments.
- [plasticos_logistics/models/__init__.py](plasticos_logistics/models/__init__.py): reorder so `from . import load_dashboard` is LAST (after `transaction_inherit`), with the explanatory comment.
- `plasticos_logistics/__manifest__.py`: version `19.0.1.2.0` -> `19.0.1.2.1`.

## Step 3 — Intake material flags (source #91) — fixes latent matcher.py crash
Confirmed Staging [matcher.py](plasticos_buyer_match_engine/models/matcher.py) reads `intake.has_metal/is_metalized/has_fr` (L248-250) but Staging `intake.py` has no such fields -> `AttributeError` when matching runs. (Audit's "Unknown 1 resolved" was incorrect.)
- [plasticos_intake/models/intake.py](plasticos_intake/models/intake.py): add `has_metal`, `is_metalized`, `has_fr` (`Boolean, compute="_compute_material_flags", store=True`) + `@api.depends("material_attribute_ids.code")` `_compute_material_flags` mapping codes `with_metal`/`metalized`/`flame_retardant`. (Optionally restore the trivial `filler_type_id` help text from #91.)
- `plasticos_intake/__manifest__.py`: bump patch version (verify current value first).
- VERIFY before commit: (a) the `plasticos.material.attribute` seed data actually uses codes `with_metal`/`metalized`/`flame_retardant`; (b) those three strings won't trip `tests/test_phantom_enum_values.py` (add to GLOBAL_ALLOWLIST as material-attribute codes if flagged).

## Step 4 — ACL gap for plasticos.intake.match (source #91)
Confirmed Staging [plasticos_security_base/security/ir.model.access.csv](plasticos_security_base/security/ir.model.access.csv) has 0 `intake_match`/`automation_log_sales` rows.
- Add `access_intake_match_sales/logistics/accounting` (for `plasticos_intake.model_plasticos_intake_match`) and `access_automation_log_sales`, matching existing row id-format and column layout in that file.
- VERIFY: `plasticos_intake`'s own `security/ir.model.access.csv` does not already grant `plasticos.intake.match` to these groups (avoid duplicate ACL per rule 71).
- EVALUATE-then-likely-SKIP #91's `plasticos_buyer_match_engine` ACL rows (`access_buyer_matcher_sales`, `access_graph_sync_log_sales`): Staging already shows 6 matching rows for those models — do a row-level check and add only a genuinely missing (model, group) pair.

## Step 5 — Harden dev_tools fence guard (source #90)
Manifest is already fenced on Staging, but the guard that enforces it is not.
- [ci/check_dev_tools_fence.py](ci/check_dev_tools_fence.py): add the block that `ast.literal_eval`s `plasticos_dev_tools/__manifest__.py` and appends a violation if `auto_install` truthy or `installable` is not `False`; update the pass/fail messages. Do NOT touch the dev_tools manifest itself.

## Step 6 — Housekeeping + docs (source #92; user opted in to everything non-superseded)
- [.gitignore](.gitignore): add the 25-line content (DS_Store, `__pycache__`, caches, `.env.local`, audit JSON artifacts, `/reports/GMP-Report-*.md`, `current work - ib/`). Note: already-tracked GMP reports stay tracked; new ones (incl. GMP-134 on the semgrep branch) become ignored — acceptable per #92 intent.
- [AGENTS.md](AGENTS.md): `staging`/`main` -> `Staging`/`Production` capitalization (2 hunks).
- [.cursor/rules/70-github-api-commit.mdc](.cursor/rules/70-github-api-commit.mdc): append the branch-capitalization note.
- New docs: [docs/adr/ADR-002-navigation-menu-architecture.md](docs/adr/ADR-002-navigation-menu-architecture.md), [docs/adr/ADR-003-contact-import-configuration.md](docs/adr/ADR-003-contact-import-configuration.md), [docs/Odoo Compiler Prompt.md](docs/Odoo Compiler Prompt.md).

## Step 7 — Validate, push, supersede the old PRs
- `ruff check . && ruff format .` on edited Python.
- `python3 scripts/check_module_wiring.py`, `python3 ci/check_dev_tools_fence.py`, phantom-enum + repo-integrity pytest, then **`make pr-check`** (must pass).
- `make push b=...` (or API fallback per rule 70 if Dropbox mmap fails), open `fix/prelaunch-consolidation` -> `Staging` PR summarizing included vs dropped-as-superseded.
- Close #90, #91, #92 with a comment pointing to the consolidation PR and the superseded matrix above.

## Module update commands (post-merge, for the deployer)
`make update m=plasticos_geolocalize,plasticos_logistics,plasticos_intake,plasticos_security_base`
