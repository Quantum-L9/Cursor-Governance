---
name: Scanner registry truth
overview: Reuse the existing field registry for depends and onchange, and flag a loop
  write only when every item would receive the same values. The profile-identity map
  already keeps the first stored row; this plan does not rewrite it.
todos:
- id: depends-onchange
  content: Walk model_classes in check_compute_depends and check_onchange_methods
    and test fields with _fields_on_model. Add inherit-only clean and missing-field
    fixtures.
  status: completed
- id: identical-write
  content: Flag a loop write only when the values are identical across items. Add
    both pytest cases. Leave differing product writes in place.
  status: completed
- id: identity-confirm
  content: Confirm enrichment by_identity uses setdefault for the first stored row.
    Edit that assignment only if the dict comprehension is still there.
  status: completed
- id: prove-scanners
  content: Ruff the touched files, run the scanner pytest modules, and run the baseline
    gate. Run the enrichment fixture test only if enrichment_run.py changes.
  status: completed
isProject: false
built: true
status: built
---

# Scanner registry and identical-write truth

GAR intervention is `USE_EXISTING`. [`scripts/audit/odoo_audit.py`](scripts/audit/odoo_audit.py) already builds `model_classes` and `_fields_on_model`. [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py) already yields loop calls. No second registry and no new scanner.

Target is the uncommitted worktree [`wt-audit-truth`](/Users/ib-mac/IB-Odoo_19%20(LOCAL)/wt-audit-truth) on `fix/audit-proved-findings`. Do not switch the dirty main checkout. Do not edit the CRM worktree. Hook catalog is `.pre-commit-config.yaml`. No `origin/main` lock.

First-order stops at two owners. Field membership and write-shape do not collapse into one edit. Further compression would hide one of them.

## Field checks

`check_constraints` already calls `_fields_on_model`. `check_compute_depends` and `check_onchange_methods` do not. Both take the first `_name = "..."` in the file and return when that regex misses. Depends then searches `model_fields` and `inherited_fields`. Onchange searches only `model_fields`. An `_inherit`-only class is invisible. A second model in the same file is invisible.

`scan_model_index` already resolves each class: `model = name or (parents[0] if len(parents) == 1 else None)`.

Change both checkers to walk those classes, not the first `_name` regex. For each `@api.depends` and `@api.onchange` field on that class, the field is present when it is in `self._fields_on_model(model)`. Emit `INVALID_DEPENDS` or `INVALID_ONCHANGE_FIELD` only when it is absent. A file with no resolvable model still emits nothing.

Add fixtures beside `test_constraint_sees_a_field_added_by_inherit` in [`tests/test_odoo_audit_field_attribution.py`](tests/test_odoo_audit_field_attribution.py):

- An inherit-only class depends on and onchanges a field declared on the `_name` class. Both checks are clean.
- The same class names a field that no class on that model declares. That field is the only finding of its type.

If a rescan of this repo emits a new `INVALID_DEPENDS` or `INVALID_ONCHANGE_FIELD`, fix the field reference or the registry. Do not add a baseline row.

## Identical write

`_loop_calls` flags every `write` whose call names the loop item. A write of different values per item cannot be one `write`. A write of the same values can.

In [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py), emit `N_PLUS_ONE_QUERY` for `write` only when the values argument is the same for every item: a name assigned outside the loop, or a constant dict. A dict built or mutated from the loop item is not a finding. A `write` whose values cannot be proved identical stays silent. `search`, `search_count`, and `create` keep the current per-item rule.

Add two tests in [`tests/test_audit_n_plus_one.py`](tests/test_audit_n_plus_one.py):

- `for rec in self: rec.write(same_vals)` with `same_vals` assigned before the loop is one finding.
- `for rec in self: rec.write({"name": rec.name})` is not a finding.

Do not wrap product `write` calls to satisfy the scanner. Do not edit [`plasticos_enrichment/models/enrichment_run.py`](plasticos_enrichment/models/enrichment_run.py) for this rule. Its per-profile `write` stays, because each profile has its own merge values.

## Profile identity

The old inject search was `search(domain, limit=1)`, which keeps the first row. A dict comprehension keeps the last. The working tree already replaces that comprehension with `setdefault`, so the first row in the search result wins. Confirm that line is present. If it is, do not edit the file again and do not bump `plasticos_enrichment` again. If the comprehension is still there, replace only that assignment with `setdefault` and leave the per-profile `write` in place.

## Proof

From the worktree, with ruff `0.16.0` from the main checkout `.venv`:

- `ruff check` and `ruff format --check` on the two scanner files and the two test files
- `python3 -m pytest tests/test_odoo_audit_field_attribution.py tests/test_audit_n_plus_one.py tests/test_audit_baseline_gate.py -q`
- `bash scripts/audit/run_baseline_gate.sh` must print no baseline regression

No Docker clone, no `make test-module`, and no `make update` for a scanner-only result. Run `make test-module m=plasticos_enrichment` on `config/test_env_fixture.conf` only when this plan changes `enrichment_run.py`. Do not set `TEST_ENV_ALLOW_NEW_TEMPLATE` or `TEST_ENV_PARITY=community`. Do not start a second Compose project. Probe `/mnt/extra-addons` before any live `make update`; skip the live upgrade when the mount is not this worktree.

Scanner and test edits do not bump a module version.

## Out of scope

- The six stdlib XML parsers and copying `tests/test_cron_xml_lock.py` onto this branch
- Unbounded search and unjustified `sudo()` findings
- The CRM roadmap and VanillaSoft phantom-enum failures
- `pipeline_v2.py`
- A live upgrade of the other ten already-bumped modules

## Handoff

Press Build on this worktree. After the todos, commit only the scanner and test paths, plus `enrichment_run.py` if it changed. Publication is `PR_STACK=auto PR_REMEDIATE=0 make pr` into `Staging`. Re-probe open pull requests first. Three sibling pull requests fail closed; do not pick one. The finish reply shows the PR URL. Do not run `make campaign`.

## Build evidence (auto)

- detected_at: `2026-10-29T15:11:17Z`
- conversation_id: `07d954b9-d92d-4df5-a528-abd67ec58f69`
- generation_id: `89010b69-af38-498c-897b-647560758a42`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/07d954b9-d92d-4df5-a528-abd67ec58f69/07d954b9-d92d-4df5-a528-abd67ec58f69.jsonl`
- todos at build time:
- `depends-onchange`: completed
- `identical-write`: completed
- `identity-confirm`: completed
- `prove-scanners`: completed

