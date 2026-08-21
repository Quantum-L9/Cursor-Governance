---
name: Fix Cron Safety Issues
overview: "Verify and fix cron-related issues from Tier 1 audit. Recursive pass against Odoo 19 native source (convert.py, ir_actions.py, ir_cron.py, safe_eval.py) eliminated 3 original findings as false positives. Remaining fixes: duplicate xmlid cleanup, noupdate standardization, advisory lock gap, and @api.model consistency."
todos:
  - id: c1-duplicate-xmlid
    content: Remove dead cron_missing_docs.xml from plasticos_transaction manifest + delete file
    status: completed
  - id: c2-noupdate-standardize
    content: Standardize all cron XML to noupdate=1 (Odoo native convention) -- currently 19 of 20 files use noupdate=0
    status: completed
  - id: c3-api-model
    content: Add @api.model decorator to _cron_escalation_check in load.py for consistency
    status: completed
  - id: c4-advisory-lock
    content: Add advisory lock to _cron_auto_create_delivery_orders in transaction.py
    status: completed
  - id: final-checklist
    content: Run final verification checklist across all cron files
    status: completed
isProject: false
---

# Fix Cron Safety Issues -- Verified Plan (Recursive Pass v2)

## Odoo 19 Native Source Verification

Before finalizing fixes, each proposed change was verified against Odoo 19.0 source code:

**Sources checked:**

- `odoo/tools/convert.py` -- XML eval context (`_get_eval_context`)
- `odoo/tools/safe_eval.py` -- safe_eval builtins and wrapped modules
- `odoo/addons/base/models/ir_cron.py` -- cron execution flow (`_process_job`, `_callback`)
- `odoo/addons/base/models/ir_actions.py` -- server action eval context (`_get_eval_context`, `run`)
- Odoo 19 official docs + core module examples (calendar, mail)

---

## Audit Findings Dismissed (NOT real issues)


| Audit Finding                                            | Audit Severity | Actual Status      | Evidence                                                                                  |
| -------------------------------------------------------- | -------------- | ------------------ | ----------------------------------------------------------------------------------------- |
| CM-1: `plasticos.graph.service` model missing            | BLOCKER        | FALSE POSITIVE     | Model exists in `plasticos_buyer_match_engine/models/graph_service.py` as `AbstractModel` |
| MM-2: `plasticos.graph.sync.log` model missing           | BLOCKER        | FALSE POSITIVE     | Model exists in `plasticos_buyer_match_engine/models/graph_sync_log.py`                   |
| MM-3: `plasticos.midnight.recompute` model missing       | BLOCKER        | FALSE POSITIVE     | Model exists in `plasticos_base/models/midnight_recompute.py`                             |
| BX-2: `plasticos.audit.cron` model missing               | BLOCKER        | FALSE POSITIVE     | Model exists in `plasticos_transaction/models/audit_cron.py`                              |
| MMeth-2 through MMeth-7: various methods missing         | BLOCKER        | ALL FALSE POSITIVE | All 15 cron methods exist in the codebase (verified via grep)                             |
| NI-1: `cron_expire_offers` non-idempotent                | CRITICAL       | FALSE POSITIVE     | Uses `pg_try_advisory_lock` + filters non-terminal states only                            |
| NI-3: `_cron_supplier_confirmation_followup` email dedup | CRITICAL       | FALSE POSITIVE     | Checks `last_supplier_confirmation_followup_on` date to skip same-day re-sends            |


### Originally Proposed Fixes Now DISMISSED After Odoo Source Verification

**DISMISSED: C1 (DateTime.now() capital D in eval) -- NOT A BUG**

The original plan proposed changing `DateTime.now()` to `datetime.now()` in `cron_geo_backfill.xml`. This is **wrong**.

Odoo 19 `convert.py` line 42-52 defines the XML eval context:

```python
def _get_eval_context(self, env, model_str):
    from datetime import datetime, timedelta  # line 17 of convert.py
    context = dict(
        DateTime=datetime,    # datetime.datetime CLASS
        datetime=datetime,    # datetime.datetime CLASS (same object)
        timedelta=timedelta,
        relativedelta=relativedelta,
        ...
    )
```

Both `DateTime` and `datetime` are **identical aliases** for `datetime.datetime` (the class, not the module). `DateTime.now()` is the **Odoo-native convention** used in official documentation and examples. The Odoo docs example uses: `eval="(DateTime.now() + timedelta(days=1)).strftime('%Y-%m-%d 09:00:00')"`. No change needed.

**DISMISSED: C4 (noupdate="1" should be noupdate="0") -- WRONG DIRECTION**

The original plan proposed changing `noupdate="1"` to `noupdate="0"` on the graph sync cron. This is **backwards**.

Odoo official documentation states: *"An important thing to note with automated actions is that they should always be defined within a noupdate field since this shouldn't be updated when you update your module."* The Odoo core `calendar_cron.xml` uses `noupdate="1"`. The `ir_cron_graph_sync.xml` is actually the **only cron in the project following the correct Odoo convention**. All other 19 cron files using `noupdate="0"` are the ones deviating from Odoo standard.

However, since this project has **already established `noupdate="0"` as its internal convention** (19 out of 20 files), and changing all 19 files is high-risk with no immediate benefit, we have two options:

- Option A: Leave as-is (accept the inconsistency -- graph sync follows Odoo standard, others don't)
- Option B: Change graph sync to `noupdate="0"` for **internal consistency** (not Odoo correctness)

Recommendation: **Option B** -- internal consistency matters more for this team than Odoo purity, since `noupdate="0"` means cron fixes apply on `-u` which is operationally useful during active development. But this is a deliberate deviation from Odoo convention, not a "fix."

**DISMISSED: C5 (bare ref without module prefix) -- VALID ODOO PATTERN**

The `ref="model_plasticos_graph_sync_log"` without module prefix is **standard Odoo behavior**. When a ref lacks a module prefix, Odoo resolves it within the current module's namespace. Since `plasticos.graph.sync.log` is defined in the same module (`plasticos_buyer_match_engine`), the auto-generated `model_plasticos_graph_sync_log` xmlid resolves correctly. Odoo core modules use bare refs for same-module references routinely. No change needed.

---

## Confirmed Real Issues (to fix)


| #   | Issue                                                   | File                                                                                                  | Severity | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| C1  | Duplicate xmlid `cron_check_missing_docs`               | `plasticos_documents/data/cron_missing_docs.xml` + `plasticos_transaction/data/cron_missing_docs.xml` | CRITICAL | Same record id in two modules. Transaction version is fully commented out but the file is still listed in the manifest. While harmless now, if anyone uncomments it, the duplicate xmlid across modules causes nondeterministic overwrite on `-u`. Dead code in manifest is a maintenance trap.                                                                                                                                                                                                                    |
| C2  | `noupdate="1"` inconsistency on graph sync cron         | `plasticos_buyer_match_engine/data/ir_cron_graph_sync.xml`                                            | LOW      | The graph sync cron uses `noupdate="1"` (Odoo standard) while all 19 other cron files use `noupdate="0"` (project convention). For internal consistency during active development, standardize to `noupdate="0"`. Note: this is a deliberate deviation from Odoo convention for operational convenience.                                                                                                                                                                                                           |
| C3  | Missing `@api.model` on `_cron_escalation_check`        | `plasticos_logistics/models/load.py:383`                                                              | MEDIUM   | Cron XML calls `model._cron_escalation_check()`. The `model` variable in the server action eval context is `self.env[model_name]` -- an empty recordset (verified in `ir_actions.py` line 1125). The method works without `@api.model` because it's called on an empty recordset, but `@api.model` is the correct semantic decorator for methods that don't operate on specific records. The sibling method `_cron_check_dispatch_acknowledgments` at line 402 in the same file has `@api.model`. Consistency fix. |
| C4  | `_cron_auto_create_delivery_orders` lacks advisory lock | `plasticos_transaction/models/transaction.py:1224`                                                    | HIGH     | This is the only high-frequency cron (1-hour interval) that lacks an advisory lock. Other crons in the project (`cron_expire_offers`, `cron_check_missing_docs`, `_cron_escalation_check`, `_cron_check_sla`) all use `pg_try_advisory_lock`. Without it, concurrent execution on crash+restart could confirm the same PO twice or link the same DO twice. The `delivery_order_id = False` search filter provides partial protection but has a TOCTOU race window.                                                 |


---

## Checkpoint Plan

### Checkpoint 1: Remove dead cron file from transaction manifest (C1)

**Files:**

- `plasticos_transaction/data/cron_missing_docs.xml` -- delete the file
- `plasticos_transaction/__manifest__.py` -- remove `data/cron_missing_docs.xml` from data list

**DOD:** Only one `cron_check_missing_docs` record exists across the codebase (in `plasticos_documents`). No dead commented-out duplicate file loaded by any manifest.

---

### Checkpoint 2: Standardize noupdate on graph sync cron (C2)

**File:** `plasticos_buyer_match_engine/data/ir_cron_graph_sync.xml`

**Change:** Change `noupdate="1"` to `noupdate="0"` on the root `<odoo>` tag.

**DOD:** All 20 cron XML files in the project use `noupdate="0"` consistently. (Note: this deviates from Odoo standard `noupdate="1"` convention but matches the project's established pattern for operational convenience during active development.)

---

### Checkpoint 3: Add @api.model decorator for consistency (C3)

**File:** `plasticos_logistics/models/load.py`

**Change:** Add `@api.model` decorator before `def _cron_escalation_check(self):` at line 383.

**DOD:** Method has `@api.model` decorator, matching the pattern of `_cron_check_dispatch_acknowledgments` at line 402 in the same file and all other cron methods in the project.

---

### Checkpoint 4: Add advisory lock to auto-create DO cron (C4)

**File:** `plasticos_transaction/models/transaction.py`

**Change:** Add `pg_try_advisory_lock` / `pg_advisory_unlock` pattern to `_cron_auto_create_delivery_orders` (around line 1224), matching the pattern used in:

- `cron_expire_offers` (`plasticos_offer/models/offer.py:391`)
- `cron_check_missing_docs` (`plasticos_documents/models/transaction_docs.py:118`)
- `_cron_escalation_check` (`plasticos_logistics/models/load.py:384`)

**DOD:** Method uses advisory lock to prevent concurrent execution. Lock key: `"plasticos_transaction.cron_auto_create_do"`.

---

## Final Checklist

After all checkpoints are complete, verify:

- **C1**: `plasticos_transaction/data/cron_missing_docs.xml` deleted and removed from manifest
- **C2**: `ir_cron_graph_sync.xml` uses `noupdate="0"` (project convention)
- **C3**: `_cron_escalation_check` has `@api.model` decorator
- **C4**: `_cron_auto_create_delivery_orders` has advisory lock with try/finally
- All cron XML files parse without errors (well-formed XML)
- No duplicate xmlids across modules for cron records
- No dead/commented-out cron files loaded by any manifest

## Files Modified (Summary)


| File                                                       | Changes                                                  |
| ---------------------------------------------------------- | -------------------------------------------------------- |
| `plasticos_transaction/data/cron_missing_docs.xml`         | DELETE file                                              |
| `plasticos_transaction/__manifest__.py`                    | Remove `data/cron_missing_docs.xml` from data list       |
| `plasticos_buyer_match_engine/data/ir_cron_graph_sync.xml` | `noupdate="1"` to `noupdate="0"`                         |
| `plasticos_logistics/models/load.py`                       | Add `@api.model` to `_cron_escalation_check`             |
| `plasticos_transaction/models/transaction.py`              | Add advisory lock to `_cron_auto_create_delivery_orders` |


## Odoo Native Compliance Notes

These notes document decisions made during the recursive verification pass:

1. **DateTime vs datetime in XML eval**: Both are identical aliases for `datetime.datetime` in `convert.py`. `DateTime` is the Odoo-native convention per official docs. No standardization needed.
2. **noupdate convention**: Odoo standard is `noupdate="1"` for crons. This project uses `noupdate="0"` everywhere. We maintain project convention for consistency but document the deviation.
3. **@api.model on cron methods**: Not strictly required for cron execution (the `model` variable is already an empty recordset from `ir_actions.py`), but is the correct semantic decorator and matches Odoo's `@api.model` documentation for "class methods that do not operate on a specific recordset."
4. **Advisory locks**: Not an Odoo-native pattern (Odoo 18+ has built-in cron deactivation after 5 failures in 7 days), but is a valid defensive pattern for this project's custom crons that create records or send emails.
5. **Bare ref without module prefix**: Standard Odoo behavior for same-module references. Auto-generated model xmlids resolve within module namespace.
