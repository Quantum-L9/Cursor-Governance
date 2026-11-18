---
name: Full dress rehearsal
overview: Add a dress-rehearsal wrapper that runs every ERP worksheet and every VanillaSoft
  ContactID. The existing 10% rehearsal files stay unchanged, so that rehearsal can
  be run again as it is.
todos:
- id: erp-full
  content: New dress_rehearsal.sh runs make import-erp with no ERP_LIMIT and judges
    limit full. Do not edit run.sh or erp_slice.sh.
  status: cancelled
- id: crm-ids
  content: Add the ContactID-file mode, Makefile and test_env forwarding, and the
    module version bump
  status: cancelled
- id: stream
  content: Tee the dress rehearsal's ERP and CRM output, then run that wrapper unbuffered
  status: cancelled
isProject: false
built: true
status: built
---

# Full dress rehearsal

The 10% rehearsal is left as it is. [tests/production-rehearsal/run.sh](tests/production-rehearsal/run.sh), [tests/production-rehearsal/erp_slice.sh](tests/production-rehearsal/erp_slice.sh), [tests/production-rehearsal/common.py](tests/production-rehearsal/common.py), and the rehearsal tests are not edited. `bash tests/production-rehearsal/run.sh` remains the 10% run.

The dress rehearsal is a new wrapper, [tests/production-rehearsal/dress_rehearsal.sh](tests/production-rehearsal/dress_rehearsal.sh). It sources the existing helpers and calls the existing gate scripts that do not carry the cap (`rehearsal_common.sh`, `weblead_e2e.sh`, `fidelity_run.py`, `scripts/test_env.sh`). Gate 6 and Gate 7 are its own commands.

## ERP: the cap lives only in the wrapper

The wrapper calls `make import-erp` with no `ERP_LIMIT`. It then calls the existing `rlib check-erp --limit full`. That judge path already accepts `full` and records every worksheet. Partners stay complete. The 10% script keeps hardcoding `ERP_LIMIT=10%`.

The last 10% run wrote 897 of 8,961 worksheets in about 3.5 minutes at 4–5 worksheets a second. The rest of that book is about 30 minutes, plus the field comparison of the whole book. Gates 1–5 stay about a minute. Gate 4 reclones `odoo_test_cutover`, which drops the 10% data already on it.

## CRM: every ContactID, one API call at a time

The 30-day rolling window cannot see the rest of the book. The Contacts list refuses anything older than 31 days. `history()` cannot be used either: it requires the missing two-column census of exactly 4,876 ids and will refuse the export. The wrapper does not call the Gate 7 block inside `run.sh`.

The wrapper passes `VANILLASOFT_CONTACT_ID_FILE` pointed at `plasticos_crm_sync/Vanillasoft-Scrap-Management.csv`. The file is not hashed. The driver reads the `ContactID` column only, skips blanks, and fetches each id once through the existing `upsert_contact_external_id` path, which already commits one contact at a time and loads `plasticos_crm_sync/data/approved_contact_crosswalk.csv`. A crosswalk hit binds the existing ERP person. Everyone else becomes a `crm.lead`. Each line printed is the position, the ContactID, and the outcome. No name, phone, or email.

That mode is importer behavior, not a rehearsal-file edit. Wire the variable through the mode guard in [Makefile](Makefile) and the allowlist in [scripts/test_env.sh](scripts/test_env.sh). Bump [plasticos_crm_sync/__manifest__.py](plasticos_crm_sync/__manifest__.py) from `19.0.1.9.22` to `19.0.1.9.23`. The wrapper's clone upgrade loads it. Several thousand API calls; this part can take one to two hours.

## Stream it

The wrapper pipes its ERP and CRM commands through `tee`, so the same text hits the terminal and the evidence log, and it passes `PYTHONUNBUFFERED=1` into the import container. The 10% script's redirects stay as they are. Worksheet commits already log every 200 worksheets (`ERP import committed through worksheet N`). CRM logs one contact per line.

The run is `bash tests/production-rehearsal/dress_rehearsal.sh`, attached, so the output streams as it happens. It writes `tests/production-rehearsal/evidence/<timestamp>/` and repoints `evidence/latest` when the verdict is written.

## Build evidence (auto)

- detected_at: `2026-11-08T21:21:09Z`
- conversation_id: `875641d1-b189-410a-beda-6e1a6803d513`
- generation_id: `cb8692b8-7688-4a32-a50c-c9fb1764ec32`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/875641d1-b189-410a-beda-6e1a6803d513/875641d1-b189-410a-beda-6e1a6803d513.jsonl`
- todos at build time:
- `erp-full`: cancelled
- `crm-ids`: cancelled
- `stream`: cancelled
