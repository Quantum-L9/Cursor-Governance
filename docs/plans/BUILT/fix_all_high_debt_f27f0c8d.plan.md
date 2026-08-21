---
name: Fix All HIGH Debt
overview: "Fix all 4 HIGH-severity code debt items: rewire Send Offer button, relax facility constraints, remove dead packet stub, and import PROCESS_SELECTION from registry."
todos:
  - id: h1
    content: "H1: Rewire button in intake_views.xml + delete action_send_offer from intake.py"
    status: completed
  - id: h2
    content: "H2: Relax _check_partner_is_facility in facility_profile.py and material_profile.py to use is_facility"
    status: completed
  - id: h3
    content: "H3: Remove _emit_capability_packet stub + its calls in create/write from facility_profile.py"
    status: completed
  - id: h4
    content: "H4: Import PROCESS_SELECTION in facility_profile.py, replace hardcoded list"
    status: completed
  - id: verify
    content: "Phase 5: git diff, pre-commit, commit, push"
    status: completed
isProject: false
---

# Fix All HIGH Code Debt

## H1 — Rewire Send Offer Button + Delete Dead Method

**Problem:** XML button calls `action_send_offer` (status-only stub at line 674). The real method is `action_send_offers` (line 877) which creates offer records.

**Files:**

- [plasticos_intake/views/intake_views.xml](plasticos_intake/views/intake_views.xml) line 213
- [plasticos_intake/models/intake.py](plasticos_intake/models/intake.py) lines 674-679

**Changes:**

1. In `intake_views.xml` line 213: change `name="action_send_offer"` to `name="action_send_offers"`
2. In `intake.py`: delete the entire `action_send_offer` method (lines 674-679) — it is now dead code since the button will call `action_send_offers` directly

**Verification:** Button click on a "matched" intake with selected buyers should create `plasticos.offer` records and advance to `offer_sent`.

---

## H2 — Relax `_check_partner_is_facility` Constraints

**Problem:** Both constraints require `partner_id.parent_id`, but `is_facility=True` for standalone companies (no parent, no children). Tab is visible, profile creation blocked.

**Files:**

- [plasticos_facility_profile/models/facility_profile.py](plasticos_facility_profile/models/facility_profile.py) lines 250-254
- [plasticos_material_profile/models/material_profile.py](plasticos_material_profile/models/material_profile.py) lines 485-489

**Changes (identical pattern in both files):**

Replace the `parent_id` check with the `is_facility` computed field:

```python
# BEFORE (both files)
@api.constrains("partner_id")
def _check_partner_is_facility(self):
    for rec in self:
        if not rec.partner_id.parent_id:
            raise ValidationError("...")

# AFTER (both files)
@api.constrains("partner_id")
def _check_partner_is_facility(self):
    for rec in self:
        if not rec.partner_id.is_facility:
            raise ValidationError("...")
```

Update error messages:

- facility_profile.py: `"Capability profile can only be attached to facility-level partners (locations or standalone companies)."`
- material_profile.py: `"Material profiles can only attach to facility-level partners (locations or standalone companies)."`

**Note:** `is_facility` is not stored, but constraint runs on create/write when the record is in memory, so computed value is available. No migration needed.

---

## H3 — Remove Dead `_emit_capability_packet` Stub

**Problem:** Builds a dict and discards it (`_ = packet`). Called on every `create()` and `write()`. Pure overhead, zero behavior.

**File:** [plasticos_facility_profile/models/facility_profile.py](plasticos_facility_profile/models/facility_profile.py)

**Changes:**

1. Delete the `_emit_capability_packet` method (lines 360-407)
2. Remove the call in `create()` (line 326): `record._emit_capability_packet()`
3. Remove the call in `write()` (line 339): `rec._emit_capability_packet()`
4. Delete the section comment block (lines 356-358)

The gap analysis doc (`plasticos_buyer_match_engine/doc/gap_analysis_v2.md` line 18) already marks this as "Removed in P03" — this is catching up to that plan.

---

## H4 — Import `PROCESS_SELECTION` from Registry

**Problem:** `process_type` field uses a hardcoded inline list instead of importing from `process_codes.py`. A test (`test_process_enum_alignment.py`) explicitly checks for this import and will fail.

**File:** [plasticos_facility_profile/models/facility_profile.py](plasticos_facility_profile/models/facility_profile.py) lines 139-154

**Changes:**

1. Add import at top of file:

```python
   from plasticos_facility_profile.process_codes import PROCESS_SELECTION
   

```

1. Replace the inline selection list with the import:

```python
   process_type = fields.Selection(
       PROCESS_SELECTION,
       help="Primary processing type at this facility.",
   )
   

```

   This removes the hardcoded 9-item list and the stale comment on line 141.

---

## Commit Strategy

Single commit with all 4 fixes — they are all in the same debt sweep and touch related files:

```
fix: resolve 4 HIGH code debt items (H1-H4)

H1: Rewire Send Offer button to action_send_offers, delete dead stub
H2: Relax _check_partner_is_facility to use is_facility (both modules)
H3: Remove dead _emit_capability_packet stub from facility_profile
H4: Import PROCESS_SELECTION from process_codes registry
```

## Deploy

- `docker compose run --rm odoo -u plasticos_facility_profile,plasticos_material_profile,plasticos_intake`
- No migrations — no stored field changes, only logic and view updates

