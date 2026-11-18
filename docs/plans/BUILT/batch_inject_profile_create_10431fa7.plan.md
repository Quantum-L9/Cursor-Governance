---
name: Batch inject profile create
overview: Move the material-profile insert in action_inject out of the raw-material
  walk so one create() covers every new identity, then merge same-run repeats. Drop
  the matching audit baseline entry in the same change.
todos:
- id: split-inject
  content: 'Split action_inject: queue creates and merges, one MatProf.create(vals_list)
    after the walk, then merge in encounter order'
  status: completed
- id: prune-baseline
  content: Remove fingerprint 13881d09c66d6989 and append the AGENTS.md correction
  status: completed
- id: bump-and-test
  content: Bump plasticos_enrichment to 19.0.2.5.7, extend the repeated-identity test,
    re-run the extended audit and make update m=plasticos_enrichment
  status: completed
isProject: false
built: true
status: built
---

# Batch the enrichment profile create

The HIGH `N_PLUS_ONE_QUERY` is `MatProf.create(create_vals)` at line 657 of [`plasticos_enrichment/models/enrichment_run.py`](plasticos_enrichment/models/enrichment_run.py), inside the `extraction_ids` / `material_json` walk in `action_inject`. Same-run repeats must still merge into the profile the first sighting inserted. The interleaving change (all new profiles first, then merges) is accepted.

## Behavior to keep

The walk already loads the partner's profiles once into `profiles_by_identity` keyed by `(polymer_id, form_id)`. That search stays one query.

For each injectable raw material, resolution stays the same: skip when polymer or form cannot be resolved. An identity already on the partner, or already queued in this walk, is a merge. The first sighting only records `create_vals`.

After that walk, call `MatProf.create(vals_list)` once, outside both loops, and zip the returned records back into `profiles_by_identity` in input order. Then apply queued merges in encounter order with the existing merge-not-overwrite body: blank fields only, `skipped_immutable` when the current value differs, the "merged fields" chatter post, and `_record_provenance`. Unmapped provenance stays with the raw material it came from.

`existing.write` is not an env-model call, so the scanner does not flag it. Do not hide `create` in a helper the loop calls, and do not edit [`scripts/audit/performance_audit.py`](scripts/audit/performance_audit.py). A private flush used once after the walk is fine; `create` must not sit lexically inside `for` / `while`.

Provenance rows for new profiles are written after the batch insert, in first-sighting order, then merge provenance runs. End state for a repeated identity is one profile, merged blanks, one provenance trail. Counts `profiles_created`, `profiles_updated`, and `fields_written` stay the same.

## Baseline

Delete fingerprint `13881d09c66d6989` from [`ci/baselines/extended_audit_baseline.json`](ci/baselines/extended_audit_baseline.json) so `entries` is empty, and adjust the `_root_cause` sentence that still says one entry remains. Append a dated correction to [`AGENTS.md`](AGENTS.md) so the 2026-11-05 note that this REAL_ACCEPT row is the remaining HIGH finding is superseded. Do not special-case the scanner.

## Version and tests

Bump [`plasticos_enrichment/__manifest__.py`](plasticos_enrichment/__manifest__.py) from `19.0.2.5.6` to `19.0.2.5.7`, and the same version in the README frontmatter.

Extend [`plasticos_enrichment/tests/test_inject_batch_queries.py`](plasticos_enrichment/tests/test_inject_batch_queries.py) `test_material_inject_looks_profiles_up_once_and_merges_a_repeated_identity`: three identical PP rows still produce one profile and one partner-profile search. Also count `plasticos.material.profile.create`: one call, whose argument is a one-element list. Add a follow-up raw material that fills a blank field (`certification_notes`) and leaves `freeform_notes` unchanged, with `profiles_updated` reflecting that merge.

Re-run `python3 scripts/audit/run_all_audits.py .` and `check_baseline.py` against the extended baseline. HIGH must be empty. Then `make update m=plasticos_enrichment`.

## Build evidence (auto)

- detected_at: `2026-11-06T16:03:12Z`
- conversation_id: `9a697480-779d-432e-900a-6e4cbd10bf03`
- generation_id: `618871d5-d762-4cae-b53d-3a4c6bcae2c2`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/9a697480-779d-432e-900a-6e4cbd10bf03/9a697480-779d-432e-900a-6e4cbd10bf03.jsonl`
- todos at build time:
- `split-inject`: completed
- `prune-baseline`: completed
- `bump-and-test`: completed
