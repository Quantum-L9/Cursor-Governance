---
name: Audit finding verdict
overview: The scanners report a finding only when they can prove it. Proved missing fields and proved per-record queries are removed at their source. The cron-lock test parses repository XML with the stdlib parser and switches to the defusedxml parser this tier already pins. The allowlist and nosec comments are not used to hide any of these.
todos:
  - id: recount-on-staging
    content: Branch from Staging in the main workspace, rerun both scanners, and treat that proved set as the work list.
    status: in_progress
  - id: field-registry
    content: Build one class-level field registry from _name, string and list _inherit, and the mail mixins. Views, constraints, and nested lists resolve through that registry.
    status: pending
  - id: field-truth-gate
    content: Emit FIELD_NOT_FOUND or INVALID_CONSTRAINT_FIELD only when the model is fully resolved and the field is absent. Cron and action records are not views. Unresolved models produce no gated finding.
    status: pending
  - id: query-truth-gate
    content: Emit N_PLUS_ONE_QUERY only for a lookup or create whose arguments change per loop item. A page cursor and a per-item savepoint command are not findings.
    status: pending
  - id: coded-master
    content: Replace the copied code uniqueness loops with one abstract helper owned by plasticos_material_profile. Facility types use that helper.
    status: pending
  - id: set-queries
    content: Replace every proved per-record search, search_count, and create with one recordset operation. Do not leave a proved call inside the loop.
    status: pending
  - id: empty-proved-baseline
    content: Bump every changed module, rescan, and delete baseline rows for these types only after the proved report is empty.
    status: pending
  - id: cron-xml-parser
    content: Parse cron XML in tests/test_cron_xml_lock.py with defusedxml.ElementTree. Do not add a nosec suppression.
    status: pending
isProject: false
---

# Report only what is proved, then remove that cause

The 101 critical rows are the field scanner blaming the wrong model. The views are already telling the truth. The 77 high rows mix real per-record queries with page fetches and isolation loops. The allowlist is what makes both look closed. This plan stops using it that way.

A gated finding is emitted only when the scanner can prove the claim. Everything else is silent. Every proved claim is then removed in the product code or, for a field, confirmed as a real missing field and added to the model that owns it. No new allowlist row is added to finish the job.

Branch from `Staging` in the main workspace. Do not edit the CRM worktree. The roadmap README failure, the VanillaSoft phantom-enum failure, `make pr-nosmoke`, `pipeline_v2.py`, and enrichment behavior stay out of scope. Enrichment views clear because the nested comodel is resolved, not because that module is rewritten.

## Field truth

The root defect in [scripts/audit/odoo_audit.py](scripts/audit/odoo_audit.py) is a file-level parse that keeps a single `_name` or a single string `_inherit`, then checks every later XML field against that model. Inherit extensions, list-form mixins, nested lists, and the next `ir.cron` or `ir.actions.*` record are invisible, so the scanner reports fields that exist.

Build one registry, per class:

- Fields declared on `_name` belong to that model.
- Fields declared on an inherit-only class are added to every model named by `_inherit`, string or list.
- A class that has both `_name` and `_inherit` keeps its own fields and also receives the fields of each inherited model already in the registry.
- `mail.thread` contributes `message_follower_ids` and `message_ids`. `mail.activity.mixin` contributes `activity_ids`. No other framework field is invented.

A view column is checked against the model it actually belongs to. An `ir.ui.view` uses its own model. A `<list>` or `<form>` nested under a field uses that field's comodel when the field is a `One2many` or `Many2many` whose comodel is a string literal in the registry. `ir.cron`, `ir.actions.server`, and `ir.actions.act_window` are not views, so their `model_id`, `state`, `code`, `interval_number`, `target`, and `res_id` are not field findings. Those names are not globally ignored.

Gated rule: emit `FIELD_NOT_FOUND` or `INVALID_CONSTRAINT_FIELD` only when the owning model is fully present in the registry and the field is not in it. If the comodel is not a resolved literal, or the model is an Odoo core model this repo does not define, emit nothing. A typo on `plasticos.transaction`, and a constraint on a field that no extension defines, still emit. `load_id`, `commission_override_pct`, nested line columns, chatter fields, and cron metadata do not.

Fixtures prove both sides. An inherit-only field, a list-form mixin field, a nested column on its comodel, and a cron record after a view produce no gated finding. A field absent from a fully resolved model still produces one. An unresolvable comodel produces none.

## Query truth

The root defect in [scripts/audit/performance_audit.py](scripts/audit/performance_audit.py) is lexical. Any `.search()`, `.search_count()`, or `.create()` inside any `for` or `while` is called N+1. That flags the page fetch in [plasticos_documents_native/models/document_sync.py](plasticos_documents_native/models/document_sync.py), which searches `id > last_id` with `limit=200` and then syncs each document inside its own savepoint.

Gated rule: emit `N_PLUS_ONE_QUERY` only when the call runs once per loop item and its domain or values contain that item. A search that is the loop's own page cursor is not a finding. A call inside a per-item `savepoint` is the item's own command and is not a finding. `browse()` stays silent. A call the resolver cannot bind to a model stays silent.

A `search_count` on `mail.activity` per load, a `search([("code", "=", code)])` per vals dict, and a `create` per partner log row remain findings. Existing tests in [tests/test_audit_n_plus_one.py](tests/test_audit_n_plus_one.py) keep the per-item search as a finding and gain a page-cursor case that is not one.

## Close the proved queries at the source

After the query rule is in place, the rescan is the work list. Every remaining `N_PLUS_ONE_QUERY` is closed in product code. Nothing proved is left on the allowlist.

**One code master.** The `create` and `write` bodies in [plasticos_material_profile/models/material_form.py](plasticos_material_profile/models/material_form.py), and the same bodies on the other `unique(code)` masters, are copies. The cause is that each model re-asks the database once per row for a uniqueness rule it already declares. Add one abstract helper in `plasticos_material_profile`. It searches the incoming codes once, raises the existing `ValidationError` when a code is already stored or repeated inside the same `vals_list`, and on `write` excludes `self.ids`. Comparison stays exact. Each master calls that helper and deletes its loop. `plasticos_facility_profile` already depends on `plasticos_material_profile`, so `equipment_type` and `partner_type` call the same helper. The SQL constraint stays. The helper does not replace any other `create` or `write` logic a model already has.

**One recordset query.** Every other proved per-item `search` or `search_count` becomes one search whose domain uses `in` on the collected ids, then a map. The cron that checks "already logged today" loads today's keys once and creates the missing log rows with one `create(vals_list)`. `message_post` stays per record. A lookup that exists only to support a later per-record decision is deleted from the loop, not wrapped. [plasticos_logistics/models/load.py](plasticos_logistics/models/load.py) is included wherever the rescan still proves a per-item lookup, including the dispatch activity `search_count`.

The page loop and the per-document savepoint in `document_sync` stay. They are the isolation boundary, and the scanner no longer calls them N+1.

`plasticos_enrichment` model code is not edited. The retired buyer-match file is not recreated.

## Baseline and versions

[ci/baselines/odoo_audit_baseline.json](ci/baselines/odoo_audit_baseline.json) and [ci/baselines/extended_audit_baseline.json](ci/baselines/extended_audit_baseline.json) stop carrying these proved types. After the rescan shows zero `FIELD_NOT_FOUND`, zero `INVALID_CONSTRAINT_FIELD`, and zero `N_PLUS_ONE_QUERY`, delete those entries. The files stay, so a later proved finding still fails [scripts/audit/check_baseline.py](scripts/audit/check_baseline.py). Do not log a leftover to make the gate green. If a proved finding remains, the registry or the recordset rewrite is unfinished.

Bump `__manifest__.py` for each module whose Python changed. `plasticos_material_profile` carries the helper. Facility, logistics, automation, and any other module whose loop was removed get their own bump. Upgrade only those modules. Scanner and test edits do not bump a module.

## Cron XML parser

The ERROR on [tests/test_cron_xml_lock.py](tests/test_cron_xml_lock.py) line 21 is a true description of the call. `xml.etree.ElementTree.parse` resolves external entities and entity expansion. The file it reads is repository `ir.cron` XML, not a request body. A `# nosec` comment would only hide that call. The pure-test tier already pins `defusedxml==0.7.1` in [requirements-ci.txt](requirements-ci.txt), and [tests/test_phantom_enum_values.py](tests/test_phantom_enum_values.py) parses addon XML with `defusedxml.ElementTree`.

Replace the stdlib import in `test_cron_xml_lock.py` with `defusedxml.ElementTree`. `parse`, `iter`, and `findall` stay the same, so the cron-to-method lock does not change. Well-formed cron XML without entities still parses. An entity payload fails closed.

Do not edit the `ci/` and `tools/` parsers in this change. They already carry a trusted-local-XML `nosec` marker, and this finding does not name them.

## Done when

- A missing field on a fully resolved PlasticOS model is still gated, and the current false positives are not.
- A per-item search is still gated, and a page cursor is not.
- The rescan report contains none of the three proved types.
- Both baseline files contain none of those types.
- No new allowlist row was added.
- The copied uniqueness loops are gone, and one helper owns that check.
- `tests/test_cron_xml_lock.py` imports `defusedxml.ElementTree` and has no `nosec` marker on the parse.
- Publication remains a later `make pr` into `Staging`.
