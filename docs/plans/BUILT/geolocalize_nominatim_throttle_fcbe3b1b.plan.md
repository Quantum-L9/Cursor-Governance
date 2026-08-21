---
name: Geolocalize Nominatim Throttle
overview: Fix the nightly geo-backfill 429 noise with the only safe, in-scope levers (configurable throttle/batch via System Parameters), remove leftover debug instrumentation from the production cron file as a separate commit, verify the intake NOT NULL constraints are persisted (read-only), and defer the real durable fix (keyed geocoder provider) as a flagged follow-up.
todos:
  - id: branch
    content: Surgical stash of 3 WIP files; checkout clean staging; create fix/geolocalize-nominatim-throttle
    status: completed
  - id: cleanup
    content: "Commit 1 (chore): remove _dbg/_LOG_PATH/_SESSION/#region blocks + unused json import from res_partner_geo.py"
    status: completed
  - id: throttle
    content: "Commit 2 (fix): configurable delay/failure_delay/batch(default 25)/max_fail via ir.config_parameter with fail-soft defaults; replace all 4 constant refs incl. BOTH sleep sites; preserve lock + abort guard"
    status: completed
  - id: seed
    content: "Commit 2 (fix): create data/geolocalize_config_params.xml wrapped in <odoo noupdate='1'> seeding the 4 params; add to manifest data list"
    status: completed
  - id: version
    content: Bump plasticos_geolocalize __manifest__.py version 19.0.1.0.0 -> 19.0.1.1.0 (in commit 2)
    status: completed
  - id: verify
    content: "Action 2 read-only: run attnotnull SQL on staging for plasticos_intake.polymer_id/form_id; capture output"
    status: completed
  - id: validate
    content: Run ruff + odoo static checks + cron-invariants + pre-commit + targeted pytest
    status: completed
  - id: report
    content: Write reports/GMP-Report-{NEXT}-Geolocalize-Nominatim-Throttle.md and push via make push
    status: completed
  - id: followup
    content: Note keyed-provider durable fix as separate follow-up GMP (needs API key)
    status: completed
isProject: false
---

## Geolocalize Nominatim Throttle + Debug Cleanup

### Scrutiny summary (why this differs from the prior agent's delta)
- The cron already throttles at 1.1s (`_NOMINATIM_DELAY`) which is within Nominatim's 1 req/s policy, yet still gets HTTP 429. Root cause is IP/UA-level (Odoo.sh shared egress IP + the generic shared `Odoo (...)` UA hardcoded in core `base_geolocalize`). So throttle/batch tuning is a weak mitigation, not a true fix — this is stated honestly in the report.
- User-Agent is correctly DESCOPED: the backfill delegates to core `partner.geo_localize()` -> `base.geocoder._call_openstreetmap`, which hardcodes the UA with no override hook. A custom UA is technically possible via `_inherit = "base.geocoder"` but would duplicate fragile core logic and likely not clear an IP-level 429, so it is not worth it.
- The durable fix the prior agent missed: core `base_geolocalize` already supports a keyed Google provider via `ir.config_parameter` (`base_geolocalize.geo_provider` + `base_geolocalize.google_map_api_key`, see core `_call_googlemap`/`get_google_map_api_key`). That is a config + key decision, deferred per user choice (Strategy A).
- Tests only invoke `cron_geo_backfill()` and assert safe/idempotent execution (`tests/test_cron_runtime.py`, `tests/integration/test_cron_idempotency.py`, `tests/test_error_handling.py`); none assert on the constants or `_dbg`, so both changes are test-safe.

### Branch hygiene (surgical, not `git stash -u`)
`-u` would hide untracked working files including `current work - ib/` prompts and the untracked `reports/GMP-Report-131/132`. Use a pathspec stash of only the 3 unrelated tracked files:
- `git stash push -m "wip-pr-autopilot-reqs-docs" -- .github/workflows/pr-autopilot.yml requirements.txt docs/makefile-automation-enhancements.md`
- `git checkout staging && git pull && git checkout -b fix/geolocalize-nominatim-throttle`
- Restore later: `git checkout fix/semgrep-odoo-raw-sql-triage && git stash pop`

### Commit 1 - chore: remove leftover agent debug instrumentation
File: `plasticos_geolocalize/models/res_partner_geo.py`
- Remove `_LOG_PATH` (line 11), `_SESSION` (line 12), the entire `_dbg()` helper (lines ~15-31) including its local `import time as _t` (inside the function body), and all three `# #region agent log ... # #endregion` blocks (the `_dbg(...)` calls at batch-start, exception, and abort).
- Remove the now-unused `import json` (line 3, only used by `_dbg`).
- KEEP: `import time` (line 5, module-level - still used by `time.sleep()`), `import logging`, `from odoo import api, models`, `_logger`, and all `_logger.warning/error/info(...)` calls.
- Acceptance: `grep -rn "_dbg\|debug-75e499\|#region agent\|import json" plasticos_geolocalize/` returns 0 hits.

### Commit 2 - fix: configurable throttle/batch + version bump
File: `plasticos_geolocalize/models/res_partner_geo.py`
- Keep `_NOMINATIM_DELAY=1.1`, `_FAILURE_DELAY=5.0`, `_MAX_CONSECUTIVE_FAIL=3` as DEFAULT constants; change `_BATCH_SIZE` default to `25`.
- At the start of `cron_geo_backfill`, read four `ir.config_parameter` keys with fail-soft parsing (fall back to the constant on missing/malformed value), using `.sudo()` with an inline justification comment (reading global System Parameters from an unattended cron):
  - `plasticos_geolocalize.nominatim_delay` (float, floored at `max(value, 1.0)` to stay Nominatim-compliant)
  - `plasticos_geolocalize.failure_delay` (float)
  - `plasticos_geolocalize.batch_size` (int)
  - `plasticos_geolocalize.max_consecutive_failures` (int)
- Replace ALL FOUR constant references in the method body with the parsed locals (enumerated to avoid missing the `except`-block sleep):
  - `limit=_BATCH_SIZE` -> `limit=batch_size` (in `search()`)
  - `time.sleep(_NOMINATIM_DELAY)` -> `time.sleep(nominatim_delay)` (inside `try`, after `geo_localize()`)
  - `time.sleep(_FAILURE_DELAY)` -> `time.sleep(failure_delay)` (inside `except` block)
  - `consecutive_failures >= _MAX_CONSECUTIVE_FAIL` -> `>= max_consecutive_failures` (abort guard)
- Preserve exactly: the `pg_try_advisory_lock`/`try...finally` unlock, per-success `cr.commit()`, the success/failed counters, and the 3-consecutive-failure abort guard structure.
- Add a brief comment above the request loop documenting Nominatim usage-policy compliance (>=1 req/s) and that UA/provider is core-controlled (see follow-up).

File: `plasticos_geolocalize/data/geolocalize_config_params.xml` (NEW - seed defaults so params are discoverable in Settings > Technical > Parameters)
- MUST wrap in `<odoo noupdate="1">` so the version-bump `-u` seeds them once but never clobbers operator-tuned values on later upgrades (corrects the prior reviewer's bare-`<odoo>` snippet, which violated `75-plasticos-xml-data-rules`).
- Four records (`param_nominatim_delay`=1.1, `param_failure_delay`=5.0, `param_batch_size`=25, `param_max_consecutive_failures`=3) on `ir.config_parameter`, keys matching the four read in the cron.

File: `plasticos_geolocalize/__manifest__.py`
- Bump `version` `19.0.1.0.0` -> `19.0.1.1.0` (triggers `-u plasticos_geolocalize` on Odoo.sh).
- Add `"data/geolocalize_config_params.xml"` to the `data` list, after `security/ir.model.access.csv`, before the views/cron entries. Run `ruff format` after editing the manifest.

### Action 2 (read-only) - confirm intake NOT NULL persisted
- Migration `plasticos_intake/migrations/19.0.5.2.2/post-migrate.py` is confirmed to run `ALTER TABLE plasticos_intake ALTER COLUMN polymer_id SET NOT NULL, ALTER COLUMN form_id SET NOT NULL`.
- Run on staging (no writes), capture output for the report:
  - `SELECT attname, attnotnull FROM pg_attribute WHERE attrelid = 'plasticos_intake'::regclass AND attname IN ('polymer_id','form_id');`
  - Expect `attnotnull = t` for both. If false -> STOP and escalate as a new finding (do not re-add here).

### Action 3 - DEFER
- `grep -rn '\-\-\-' --include='__manifest__.py' .` returns nothing; no manifest has a `description` key with `---`. No in-scope target -> deferred (the docutils RST noise originates outside `__manifest__.py`).

### Validation (Phase 4)
- `ruff check . && ruff format --check .`
- `python3 scripts/check_module_wiring.py`
- `python3 ci/check_circular_deps.py`
- `python3 ci/check_orphan_model_refs.py`
- `python3 ci/check_odoo19_xml.py`
- `python3 tools/cron_invariant_check.py`
- `pre-commit run --all-files`
- `python -m pytest tests/test_cron_runtime.py tests/integration/test_cron_idempotency.py tests/test_error_handling.py -v` (then full `tests/` if green)
- Acceptance greps: `grep -rn "_dbg\|debug-75e499\|#region agent\|import json" plasticos_geolocalize/` -> 0 hits; exactly two `time.sleep(` calls remain in the method, both using locals (`nominatim_delay`, `failure_delay`); no `base_geolocalize/*` core file modified.

### Finalize (Phase 6) + push
- Write `reports/GMP-Report-{NEXT}-Geolocalize-Nominatim-Throttle.md` (NEXT = highest existing `reports/GMP-Report-*.md` + 1, zero-padded; expected 133). Sections: HEADER, PLAN, CHANGES, TODO_CHANGE_MAP, VALIDATION, DECLARATION. Must record: four configurable params + defaults, the new `noupdate="1"` seed file, `_BATCH_SIZE` 50->25, both sleep sites switched to locals, debug-removal grep=0, Action 2 SQL output, Action 3 deferred, and the honest note that 429 may persist on shared OSM IP until the keyed-provider follow-up.
- Push via `make push` (runs `make pr-check`). API push only if `git push` fails with the Dropbox mmap error after pr-check already passed.

### Phase 5 scope guard
`git diff --name-only staging...HEAD` must list ONLY:
- `plasticos_geolocalize/models/res_partner_geo.py`
- `plasticos_geolocalize/__manifest__.py`
- `plasticos_geolocalize/data/geolocalize_config_params.xml` (new file)
Must NOT contain: core `base_geolocalize/*`, `plasticos_intake/*`, the 3 stashed WIP files, or any `_dbg`/`debug-75e499`/`#region` remnant.

### Follow-up (out of scope, flagged)
File a separate GMP to evaluate the durable 429 fix: switch geocoder to a keyed provider (Google via `base_geolocalize.google_map_api_key` + `base_geolocalize.geo_provider`, or another keyed service). Requires an API key / billing decision.