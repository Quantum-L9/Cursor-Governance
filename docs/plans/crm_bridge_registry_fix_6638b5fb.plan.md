---
name: crm bridge registry fix
overview: "Fix the single fatal Odoo 19 registry-load blocker on Staging: plasticos_crm_bridge overrides a CRM action XML ID (crm.crm_lead_all_pipeline) that was removed in Odoo 19. Remove the obsolete override, bump the module version, and push directly to origin Staging."
todos:
  - id: git-sync
    content: Repair local git index and fast-forward/reset local Staging to origin/Staging (verify clean base)
    status: pending
  - id: edit-view
    content: Remove the obsolete crm.crm_lead_all_pipeline override block in plasticos_crm_bridge/views/crm_lead_views.xml
    status: pending
  - id: bump-version
    content: Bump plasticos_crm_bridge __manifest__.py version 19.0.3.2.0 -> 19.0.3.2.1
    status: pending
  - id: commit-push
    content: Commit the fix and push directly to origin Staging (verify correct branch)
    status: pending
  - id: verify
    content: SSH to staging build and confirm update.log shows Registry loaded with no ERROR; address any newly-surfaced module 149/150 error
    status: pending
isProject: false
---

# Fix CRM Bridge Registry-Load Failure on Staging

## Root-cause analysis (from the pasted update.log + local Odoo 19.0 source)

The traceback is unambiguous. Only **one** error is fatal:

- **P0 — FATAL (blocks the entire Staging DB):** `plasticos_crm_bridge/views/crm_lead_views.xml:276` overrides core record `crm.crm_lead_all_pipeline`:

```xml
<record id="crm.crm_lead_all_pipeline" model="ir.actions.act_window">
    <field name="view_mode">kanban,list,form,activity,pivot,calendar</field>
</record>
```

That XML ID was **removed in Odoo 19**. The CRM pipeline action is now `crm.crm_lead_action_pipeline`. Odoo raises `Cannot update missing record 'crm.crm_lead_all_pipeline'` -> `Failed to load registry` -> `Failed to initialize database`. Verified in local source `/Users/macm2/odoo/odoo/addons/crm/views/crm_lead_views.xml`: only `crm_lead_all_leads` (line 1066) and `crm_lead_action_pipeline` (line 1203) exist. The Odoo 19 `crm_lead_action_pipeline` already declares `view_mode = kanban,list,graph,pivot,form,calendar,activity` — so **pivot and calendar are already present**, making this override obsolete.

The other items in the logs are **non-fatal noise**, not registry blockers (do NOT touch in this pass):
- `<string>:NN (ERROR/WARNING)` RST messages -> docutils parsing module `README.md` markdown tables (`|---|`) as reStructuredText (e.g. `plasticos_commission/README.md`). Cosmetic.
- `Could not import library pdf417gen` -> raised by **standard** Odoo `l10n_cl_edi*` modules (no reference in our codebase). Library simply absent on the build. Cosmetic.
- `Geo backfill: 3 consecutive failures` -> external geocoder rate-limit, operational not code.

## The surgical fix

### 1. Remove the obsolete override
In `plasticos_crm_bridge/views/crm_lead_views.xml`, delete the comment block + record (origin lines ~272-278):

```xml
<record id="crm.crm_lead_all_pipeline" model="ir.actions.act_window">
    <field name="view_mode">kanban,list,form,activity,pivot,calendar</field>
</record>
```

Rationale: Odoo 19's `crm_lead_action_pipeline` already includes pivot + calendar, so the override adds nothing and is the lowest-risk fix. (Re-pointing the id to `crm.crm_lead_action_pipeline` is rejected: its view_mode omits `graph`, which would drop the graph view and risk orphaning `crm_lead_action_pipeline_view_graph`.) The custom `crm_lead_plastos_calendar`/pivot view definitions remain harmless and need no change.

### 2. Bump the module version (triggers Odoo.sh re-update)
`plasticos_crm_bridge/__manifest__.py`: `"version": "19.0.3.2.0"` -> `"19.0.3.2.1"`.

## Prerequisite: repair local git state (fragile)
- `.git/index` was corrupted (Dropbox sync of `.git`); local `Staging` is **91 commits behind** `origin/Staging`.
- Before editing, sync the working tree to the latest server code so the fix lands on the right base: `git fetch origin`, then reset local `Staging` to `origin/Staging` (confirmed: origin has the broken record at line 276 and manifest at `19.0.3.2.0`).
- Edit the two files against that synced tree.

## Commit + deploy (direct to Staging, no PR — per your instruction)
- Verify branch resolves to push target `Staging` (remote branch is capital `Staging`).
- `git add plasticos_crm_bridge/views/crm_lead_views.xml plasticos_crm_bridge/__manifest__.py`
- Commit: `fix(crm_bridge): drop removed Odoo 19 action crm_lead_all_pipeline override (registry load blocker)`
- Push directly: `git push origin Staging`.

## Verify
- After push, Odoo.sh rebuilds Staging. Confirm via SSH that `update.log` ends with `Registry loaded` and no `ERROR`: `ssh <build>@cryptoxdog-ib-odoo-19-staging-32807868.dev.odoo.com "tail -100 ~/logs/update.log"`.
- Registry aborts at the *first* error, so if a new error surfaces in the last 2 modules (149/150) it was previously masked — diagnose + fix iteratively.

## Notes / decisions for you
- I'll leave the README.md RST warnings and `pdf417gen` warnings alone unless you want them silenced (separate, non-blocking cleanup).
- Pushing straight to `Staging` skips PR review; confirmed this is what you want.