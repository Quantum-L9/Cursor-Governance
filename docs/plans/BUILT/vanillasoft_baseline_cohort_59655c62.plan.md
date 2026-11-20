---
name: VanillaSoft baseline cohort
overview: Select VanillaSoft contacts from the tracked addon export, fetch each ContactID through the existing API and orchestrator, and stop at a local commit. Do not publish.
todos:
  - id: tracked-export
    content: Use plasticos_crm_sync/Vanillasoft-Scrap-Management.csv as the selection file and commit it. Its raw SHA-256 is 93fbbf261aa175d16c66ffc9c6bc8add7c51bce83a548d2af6da8d5e28ed0da9.
    status: completed
  - id: id-parser
    content: Parse that tracked file in memory. Require 262 columns and 4,818 unique ContactIDs. Fetch those IDs through the existing orchestrator. Leave the two-column census loader in place for its own files.
    status: completed
  - id: tests-version
    content: Cover the tracked-export loader in the existing history test module and bump plasticos_crm_sync to 19.0.1.9.22.
    status: completed
  - id: local-commit
    content: Local commit only. Do not push, do not run make pr, and do not run the promotion rehearsal.
    status: completed
isProject: false
---

# Tracked VanillaSoft export

## Execute via Cursor Build

Build on the current workspace. Local commit only. Do not publish.

The selection file is [plasticos_crm_sync/Vanillasoft-Scrap-Management.csv](plasticos_crm_sync/Vanillasoft-Scrap-Management.csv). It is tracked. It is not copied to Dropbox, to evidence, or to a second path.

Verified: the file exists, is readable, and is 4,282,658 bytes. A quoted parse finds `ContactID`, 262 columns, and 4,818 unique ContactIDs. Raw SHA-256 is `93fbbf261aa175d16c66ffc9c6bc8add7c51bce83a548d2af6da8d5e28ed0da9`. The earlier declared digest `46244f9b0965f7893fdd61db2a74c1d9cffa0098be1f1cac2f9f4dd2fced88f9` does not match these bytes. This file is the one the operator named, so that older digest is not the gate.

The file is inside the checkout, which is the container's only bind mount. `VANILLASOFT_HISTORY_CENSUS` can name this relative path. No Dropbox path and no extra copy.

## Selection

`load_tracked_export` reads the file when the header starts with `ContactID`. It checks the raw digest, the 262-column header, and 4,818 unique ContactIDs, and returns those IDs as the fetch set. Contact fields still come from the existing VanillaSoft API through `SyncOrchestrator.upsert_contact_external_id`.

The two-column `load_census` path stays for a `vanillasoft_contact_id,decision` file. This export does not go through it. The crosswalk still binds an approved contact to an ERP person and does not decide membership. `verify_identity` runs only for the two-column census.

No date floor selects this run. Gates 1 through 6 stay. Gate 7 is unchanged in this commit. Historical accounting is unchanged.

Bump [plasticos_crm_sync/__manifest__.py](plasticos_crm_sync/__manifest__.py) from `19.0.1.9.21` to `19.0.1.9.22`.

## Stop

After the local commit, stop. Do not push. Do not run `make pr`. Do not merge. Do not run the promotion rehearsal.
