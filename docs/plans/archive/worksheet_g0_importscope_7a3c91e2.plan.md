---
name: Worksheet G0 identity and ImportScope
overview: "While the decoded image copy continues, derive ImportScope on a private copy of the already complete journal and record a read-only identity of the running Odoo.sh Production build. The original journal.csv stays byte-for-byte unchanged. No image hash, no importer, and no Production write."
todos:
  - id: T1
    content: "Write /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv from the existing journal. Add ImportScope from RefType only: W and # are eligible, P is archive_only, E and B are unattached. Any other RefType fails the write. Leave Status, hashes, and every other column unchanged. Refuse if the destination is journal.csv. After the write, the original file hash must still match the hash taken before the write."
    status: pending
    phase: execute
    depends_on: []
  - id: T2
    content: "Using only ODOO_SH_PRODUCTION_SSH, open a read-only shell on the running Production database. Record the build hostname, database name, company ids and names, installed state of documents, documents_account, and plasticos_documents_native, and the plasticos.transaction count, unique name count, and company distribution. Write id,name,company_id for every transaction to /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv and the identity to /Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json. The export row count must equal the transaction count from the same session. Do not call write, create, unlink, or a module install."
    status: pending
    phase: execute
    depends_on: []
isProject: false
kind: simple
execute_via: cursor-build
status: current
---

# PLAN: Worksheet G0 identity and ImportScope

> **Projected by** `scripts/render_plan_pe_autonomy.py` from validated PLAN_DOCUMENT JSON.

> **First-class SSOT (git):** `environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md` · metadata sidecar `*.meta.md` · registered in `environment/contracts/execution/MANIFEST.yaml`. Skill path is a symlink; `.cursor/plans/_TEMPLATE.plan.md` is a local mirror only.
> **Schema:** `canonical.schema.plan_document.v1` (status: fill → `executable` only when law holds)
> **Parameters:** every value is projected from PLAN_DOCUMENT. A value reading `unknown — …` or `unbound — …` is absent from PLAN_DOCUMENT and must be resolved before status becomes `executable`.
> **Execute:** when status is `executable`, press **Build**, stack on the unique open-PR tip if any open PR exists (`PR_STACK=auto`; never `origin/main`), then `PR_STACK=auto PR_REMEDIATE=0 make pr` and display the PR URL. Do **not** run `make campaign`, admit a Program Lock, or free-form mutate from this markdown alone.
> **Cursor todos:** frontmatter `todos` project to Build todos. Body is the binding contract.
> **File name:** `worksheet_g0_identity_and_importscope_c5e211f3.plan.md`
> **Law:** executable only when baseline matches, capability probes pass, invariants match, and envelope is respected. Markdown completeness alone is insufficient.

## Execute via Cursor Build

Press **Build**. Plan on the current workspace. Execute on the unique open-PR chain tip.

- If any open PR exists: **never** branch from `origin/main`. Start from the unique chain tip (`PR_STACK=auto`). Use `agent_worktree_start.sh` when this checkout is not already that tip. Sibling open-PR chains fail closed.
- If the board is empty: `origin/main` is allowed.
- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a **planning** requirement.
- After Build todos complete: scoped-commit (pathspecs), `l4_local.py authorize-release`, then `PR_STACK=auto PR_REMEDIATE=0 make pr`. Do not skip `make pr`.
- The finish reply **must** display the opened PR URL as proof. Without that URL the Build is incomplete.

## Metadata

| Field | Value |
|-------|-------|
| plan_id | `plan.simple.worksheet_g0_identity_and_importscope.v1` |
| name | Worksheet G0 identity and ImportScope |
| overview | While the decoded image copy continues, derive ImportScope on a private copy of the already complete journal and record a read-only identity of the running Odoo.sh Production build. The original journal.csv stays byte-for-byte unchanged. No image hash, no importer, and no Production write. |
| schema_version | `1.0.0` |
| status | `draft` — planning convergence is `partial` |
| is_project | `false` |
| owner | igor_beylin |
| created_at | 2026-11-10T14:13:44+00:00 |
| updated_at | 2026-11-10T14:13:44+00:00 |
| depth | `deep` |
| estimate | one read-only Production session and one local journal derivation |

## Architect framing

| Field | Value |
|-------|-------|
| planning_ssot | validated PLAN_DOCUMENT JSON (`validate_plan_document.py`) |
| plan_class | `bounded_execution_contract` — PLAN_DOCUMENT mode `plan` |
| redesign_allowed | `false` |
| follow_on_schema_evolution_separate | `true` |
| framing_notes | Execute via Cursor Build; stacked make pr if any open PR exists; no redesign unless plan_class requires it |

## Immutable baseline

| Field | Value |
|-------|-------|
| captured_at | `2026-11-10T14:13:44+00:00` |
| repository | `cryptoxdog/IB-Odoo_19` |
| workspace | `/Users/ib-mac/IB-Odoo_19 (LOCAL)/IB-Odoo_19` |
| branch | `Staging` |
| commit_sha | `a1f93f3fd42a7c949f21fce48c856946abc00e1f` |
| dirty | `true` |
| artifact_hashes | `{}` — none pinned by PLAN_DOCUMENT |
| allowed_local_dirt | none |
| overlap_policy | `stop_if_dirty_overlaps_may_modify` |
| verification_rule | `reverify_at_execution_start` |
| on_drift | `stop_and_replan` |

## Objective

### Mission

While the decoded image copy continues, derive ImportScope on a private copy of the already complete journal and record a read-only identity of the running Odoo.sh Production build. The original journal.csv stays byte-for-byte unchanged. No image hash, no importer, and no Production write.

### Scope in

- Private copy of /Users/ib-mac/Odoo-ERP-Files/journal.csv with ImportScope derived only from RefType
- Read-only Odoo.sh Production identity: running build, company distribution, plasticos.transaction count, and the three Documents module states
- Private export of plasticos.transaction id, name, and company_id

### Success properties

Each property's proof is the `final_validation` entry it names (by id or by script/file). A property with no proving validation, or only skipped / not_applicable ones, blocks `executable`.

| id | property | evidence_type | proof | blocking |
|----|----------|---------------|-------|----------|
| SP-01 | V1 proves the private journal copy has 111010 rows, ImportScope eligible 97346, archive_only 13077, and unattached 587, and the original journal.csv hash is unchanged. | `quality_gate` | V1: `python3 -c 'census of journal.import-scope.csv and sha256 of journal.csv'` → 111010 rows; eligible 97346; archive_only 13077; unattached 587; original journal.csv sha256 unchanged. | `true` |
| SP-02 | V2 proves one read-only Production receipt names the running build, the installed state of documents, documents_account, and plasticos_documents_native, the transaction count, and a private id,name,company_id export whose row count equals that count. | `quality_gate` | V2: `python3 -c 'compare g0-identity.json transaction_count with production-transactions.csv rows'` → The receipt names the running build and the three module states, and the export row count equals the transaction count. | `true` |

## Capability preflight

`schema_ref:` `canonical.schema.capability_preflight.v1`
`instance_binding:` `capability_preflight_ref` → `preflight.plan.simple.worksheet_g0_identity_and_importscope.v1`

| Field | Value |
|-------|-------|
| preflight_id | `preflight.plan.simple.worksheet_g0_identity_and_importscope.v1` |
| source_ref | `plan.simple.worksheet_g0_identity_and_importscope.v1` |
| phase_id | `preflight` |
| blocking | `true` |
| immutable_baseline_ref | `baseline.plan.simple.worksheet_g0_identity_and_importscope.v1` |
| baseline_verified | `false` — reverify at execution start |
| drift_detected | `false` — baseline captured at render |

### Probes (from PLAN_DOCUMENT `pre_validation`; failed blocking probe → status `preflight_blocked`)

| id | capability | command_or_action | pass_criteria | blocking |
|----|------------|-------------------|---------------|----------|
| P0 | pre-validation (status `passed`) | `Census /Users/ib-mac/Odoo-ERP-Files/journal.csv` | 111010 data rows, ImageID ceiling 721202, Status ok 111009 and not_gzip 1, RefType W 97328, P 13077, E 586, # 18, B 1, and no ImportScope column. | `true` |
| P1 | pre-validation (status `passed`) | `Confirm .env.local names ODOO_SH_PRODUCTION_SSH and that 11_IMPORT_SCOPE.md keeps W and # eligible` | Production SSH is named separately from Staging. Eligible images remain RefType W and #. | `true` |

## Execution envelope

Mutations outside this envelope are forbidden (PLAN-SCHEMA-004).

### Filesystem

- **write_allow:** `/Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv`, `/Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json`, `/Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv`
- **write_deny:** `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Odoo-ERP-Files/decoded`, `plasticos_documents_native`, `the Production database`
- **delete_allow:** none — no Delete todo

### Commands

- **allow:** `V1 journal.import-scope.csv census and original sha256`, `V2 g0-identity.json against production-transactions.csv`, `python3 -c 'census of journal.import-scope.csv and sha256 of journal.csv'`, `python3 -c 'compare g0-identity.json transaction_count with production-transactions.csv rows'`
- **deny:** `git push --force`, `git reset --hard`, admin merge, committing secrets

### Network

| Field | Value |
|-------|-------|
| mode | `read_only` |
| allowed_services | `odoo.sh production ssh` |

### Secrets

| Field | Value |
|-------|-------|
| access | `read_only_named` |
| redaction_required | `true` |

### Autonomous merge

`autonomous_merge:` `false` always. This plan confers no merge authority.

### Preserved contracts

- W and # stay eligible. P stays archive_only. E and B stay unattached.
- The original journal is not rewritten.
- Production is read only.
- Private rows stay outside git.

## Side effects and idempotency

Required for every destructive / external-write TODO (PLAN-SCHEMA-005). One row per todo.

| todo_id | side_effects | idempotency | retry | compensation | irreversible |
|---------|--------------|-------------|-------|--------------|--------------|
| T1 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv` | `false` |
| T2 | `filesystem_mutation` | `safe_with_dedupe` | `retry_once` | `git restore -- /Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv` | `false` |

## Architecture impact

| todo_id | bounded_context | layer | owning_contract | prohibited |
|---------|-----------------|-------|-----------------|------------|
| T1 | `//Users/ib-mac/Odoo-ERP-Files` | `data_plane` | `W and # stay eligible. P stays archive_only. E and B stay unattached.`, `The original journal is not rewritten.`, `Production is read only.`, `Private rows stay outside git.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Odoo-ERP-Files/decoded`, `plasticos_documents_native`, `the Production database` |
| T2 | `//Users/ib-mac/Odoo-ERP-Files/private` | `external_system` | `W and # stay eligible. P stays archive_only. E and B stay unattached.`, `The original journal is not rewritten.`, `Production is read only.`, `Private rows stay outside git.` | `/Users/ib-mac/Odoo-ERP-Files/journal.csv`, `/Users/ib-mac/Odoo-ERP-Files/decoded`, `plasticos_documents_native`, `the Production database` |

## Rollback

`schema_ref:` `canonical.schema.rollback_contract.v1`
`instance_binding:` `rollback_contract_ref` → `rollback.plan.simple.worksheet_g0_identity_and_importscope.v1`

| Field | Value |
|-------|-------|
| rollback_id | `rollback.plan.simple.worksheet_g0_identity_and_importscope.v1` |
| source_execution_ref | `plan.simple.worksheet_g0_identity_and_importscope.v1` |
| supported | `true` |
| automatic_allowed | `false` |
| approval_required | `false` |
| trigger_conditions | C1 fails (V1 passes with the four scope counts and the unchanged original hash.) → Delete the private copy and stop. Do not alter journal.csv.; C2 fails (V2 passes and the export row count equals the transaction count.) → Do not call the export complete and do not start the crosswalk. |

### Strategies (typed — PLAN-SCHEMA-009)

| domain | mode | notes |
|--------|------|-------|
| code | `git_restore_scoped_paths` | Delete the private journal copy and the private export. The original journal and the Production database are not modified, so they need no restore. |
| data | `none` | PLAN_DOCUMENT declares no data mutation |
| external_state | `none` | PLAN_DOCUMENT declares no external write |
| local_state | `git_restore_scoped_paths` | scoped to todo files |

### Irreversible operations

- none — no todo is marked `irreversible` (PLAN-SCHEMA-010)

### Rollback verification

- re-run `V1 journal.import-scope.csv census and original sha256`
- re-run `V2 g0-identity.json against production-transactions.csv`
- re-run `python3 -c 'census of journal.import-scope.csv and sha256 of journal.csv'`
- re-run `python3 -c 'compare g0-identity.json transaction_count with production-transactions.csv rows'`

## Complexity and uncertainty

| Field | Value |
|-------|-------|
| complexity | `medium` — highest todo risk across 2 todo(s) |
| uncertainty | `low` — 0 unknown(s), 0 blocking |
| blast_radius | `medium` — A wrong scope label would make the later crosswalk import archive images or drop eligible ones. A write on the Production shell would change the live database. Both are refused by the checks above. |
| architectural_boundaries_crossed | `private journal derivation`, `hosted Production read` |
| external_systems_touched | `Odoo.sh Production` |
| migration_required | `false` |
| unknown_dependency_count | `0` |

## Inventory and classification *(optional — activate if retire/migrate/replace)*

Not activated — PLAN_DOCUMENT declares no retire / migrate / replace inventory.

## Gated write pipeline *(optional — irreversible or external writes)*

Not activated — PLAN_DOCUMENT declares no irreversible or external write.

## Regeneration extinguishment *(optional — retirement/deprecation)*

Not activated — PLAN_DOCUMENT declares no retirement or deprecation.

## Execution DAG

`schema_ref:` `canonical.schema.dependency_topology.v1`
`instance_binding:` `dependency_topology_ref` → `dag.plan.simple.worksheet_g0_identity_and_importscope.v1`
Must be acyclic before status may become `executable` (PLAN-SCHEMA-007).

| Field | Value |
|-------|-------|
| topology_id | `dag.plan.simple.worksheet_g0_identity_and_importscope.v1` |
| topology_kind | `execution` |
| graph_type | `directed_acyclic_graph` |

### Nodes / edges

| id | task | owner | risk | effort | depends_on | outputs |
|----|------|-------|------|--------|------------|---------|
| T1 | Write /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv from the existing journal. Add ImportScope from RefType only: W and # are eligible, P is archive_only, E and B are unattached. Any other RefType fails the write. Leave Status, hashes, and every other column unchanged. Refuse if the destination is journal.csv. After the write, the original file hash must still match the hash taken before the write. | Cursor Build agent | `low` | S | `[]` | `/Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv` |
| T2 | Using only ODOO_SH_PRODUCTION_SSH, open a read-only shell on the running Production database. Record the build hostname, database name, company ids and names, installed state of documents, documents_account, and plasticos_documents_native, and the plasticos.transaction count, unique name count, and company distribution. Write id,name,company_id for every transaction to /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv and the identity to /Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json. The export row count must equal the transaction count from the same session. Do not call write, create, unlink, or a module install. | Cursor Build agent | `medium` | M | `[]` | `/Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json`, `/Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv` |

**Critical path:** T1 → T2

**Forbidden edges:** any edge not listed above; any todo writing outside `write_allow`.

### Milestones

| id | outcome | unlocks |
|----|---------|---------|
| M1 | A private journal with ImportScope exists and the original journal is unchanged. | The reconciler can load the journal as soon as the transaction export exists. |
| M2 | The Production identity and the complete transaction export are on disk outside git. | The exact crosswalk can run without waiting for decoded files. File hashes stay blocked until decoded is stable. |

### Checkpoints

| id | after | evidence_required | no_go_action |
|----|-------|-------------------|--------------|
| C1 | M1 | V1 passes with the four scope counts and the unchanged original hash. | Delete the private copy and stop. Do not alter journal.csv. |
| C2 | M2 | V2 passes and the export row count equals the transaction count. | Do not call the export complete and do not start the crosswalk. |

### Leverage

- **Ranked todos:** `T1`, `T2`
- **Shared causes:** the copied journal has no ImportScope column; hosted Production identity is unobserved
- **Deletions / consolidations:** Do not re-extract the blobs to add ImportScope.; Do not hash the partial decoded folder.; Do not build the importer in this pass.

### Doc / root surface impact

| surface | action | todo_ids | reason |
|---------|--------|----------|--------|
| AGENTS.md | `n_a` | — | No addon, importer, or root-file contract changes. The journal copy and the Production export stay outside the repository. |
| INVARIANTS.md | `n_a` | — | No invariant changes. The read uses the hosted Production database and writes nothing. |

## Property evidence matrix

`schema_ref:` `canonical.schema.validation_evidence.v1`
`instance_binding:` `validation_evidence_refs` / `property_evidence_matrix_ref`
Exit-0 alone is insufficient when property needs structural/runtime proof (PLAN-SCHEMA-008).

| evidence_id | claim_id / SP | evidence_kind | method | command | expected_positive | status |
|-------------|---------------|---------------|--------|---------|-------------------|--------|
| E-V1 | SP-01 | `quality_gate_evidence` | command | `python3 -c 'census of journal.import-scope.csv and sha256 of journal.csv'` | 111010 rows; eligible 97346; archive_only 13077; unattached 587; original journal.csv sha256 unchanged. | `not_run` |
| E-V2 | SP-02 | `quality_gate_evidence` | command | `python3 -c 'compare g0-identity.json transaction_count with production-transactions.csv rows'` | The receipt names the running build and the three module states, and the export row count equals the transaction count. | `not_run` |

## Stress and disconfirm

### Disconfirming cases

- Can the derived file replace or rewrite journal.csv?
- Can a RefType outside W, #, P, E, and B receive a guessed ImportScope?
- Can the Staging SSH target be used as the Production identity?
- Can an export whose row count differs from the transaction count be called complete?

### Assumption failure conditions

- The partial decoded folder is required before ImportScope can be derived.
- Git installability of plasticos_documents_native proves it is installed on the running build.
- A Git Production SHA is the running Odoo.sh build.

### Blast radius notes

- A wrong scope label would make the later crosswalk import archive images or drop eligible ones. A write on the Production shell would change the live database. Both are refused by the checks above.

### Rollback constraints

- Delete the private journal copy and the private export. The original journal and the Production database are not modified, so they need no restore.

### Risks

| risk | mitigation |
|------|------------|
| The derived writer overwrites journal.csv. | The destination path is a different file, and the original hash is compared after the write. |
| The Production shell is pointed at Staging or performs a write. | Use only ODOO_SH_PRODUCTION_SSH. The shell runs search and read_group only. |
| The transaction export is saved into the git tree. | Both receipts stay under /Users/ib-mac/Odoo-ERP-Files/private, which is outside the repository. |

## Out of scope

- Rewriting or re-extracting the server blobs
- Hashing the partial decoded folder
- A second Postgres or a second document store
- Any Production write, backup restore, or importer
- Committing the journal, the export, or the identity receipt
- Architecture redesign (unless plan_class + redesign_allowed)
- Force-push, hard-reset, admin-merge, secret exfil
- Weakening scanners / gates to obtain PASS
- Follow-on schema/platform evolution

## Follow-on milestone *(optional — keep separate; PLAN-SCHEMA-014)*

Not activated — PLAN_DOCUMENT declares no follow-on milestone; separate_plan_required `true` for any follow-on.

## Convergence

`schema_ref:` `canonical.schema.convergence_contract.v1`
`instance_binding:` `convergence_contract_ref` → `conv.plan.simple.worksheet_g0_identity_and_importscope.v1`
Convergence requires all blocking evidence + gates (PLAN-SCHEMA-015).

| Field | Value |
|-------|-------|
| convergence_id | `conv.plan.simple.worksheet_g0_identity_and_importscope.v1` |
| source_ref | `plan.simple.worksheet_g0_identity_and_importscope.v1` |
| current_state | `draft` |
| implementation_ready | `false` |

### Gates

- **executable_when:**
  - baseline locked + reverified
  - blocking capability probes pass
  - DAG acyclic
  - envelope + side-effect matrix complete for mutate todos
  - no blocking unknowns
- **complete_when:**
  - all blocking success-property evidence `passed`
  - rollback contract still valid / unused-or-verified
  - out_of_scope respected (diff hygiene)
- **blocking_conditions:**
  - `preflight_blocked`
  - envelope breach
  - baseline drift
  - failed blocking property

### Evidence

- **required_evidence_refs:** E-V1, E-V2
- **observed_evidence_refs:** none
- **missing_evidence:** E-V1, E-V2

### Blockers / unknowns

| kind | id | note | resolution |
|------|----|------|------------|
| `open_blocker` | stop_reason | The two private artifacts are specified. V1 and V2 run when the todos are built. | planning convergence `partial` |

### Next

| Field | Value |
|-------|-------|
| next_convergence_gate | `executable_when` |
| minimum_safe_next_action | When law holds and status=`executable`, press **Build**, stack if any open PR exists (`PR_STACK=auto`), then `make pr` and display the PR URL — do not free-form execute |
| execute_via | Cursor Build; stacked PR if any open PR exists; display PR URL |
| next_skill | Build then stacked make pr |
| broader_work_requires_separate_contract | `true` |

---

## Machine stub (optional YAML instance seed)

Projected from PLAN_DOCUMENT; keep in sync with the sections above.

```yaml
schema_id: "canonical.schema.plan_document.v1"
schema_version: "1.0.0"
metadata:
  plan_id: "plan.simple.worksheet_g0_identity_and_importscope.v1"
  name: "Worksheet G0 identity and ImportScope"
  overview: "While the decoded image copy continues, derive ImportScope on a private copy of the already complete journal and record a read-only identity of the running Odoo.sh Production build. The original journal.csv stays byte-for-byte unchanged. No image hash, no importer, and no Production write."
  status: "draft"
  is_project: false
  owner: "igor_beylin"
architect_framing:
  planning_ssot: "PLAN_DOCUMENT"
  plan_class: "bounded_execution_contract"
  redesign_allowed: false
  follow_on_schema_evolution_separate: true
immutable_baseline:
  repository: "cryptoxdog/IB-Odoo_19"
  commit_sha: "a1f93f3fd42a7c949f21fce48c856946abc00e1f"
  dirty: "true"
  overlap_policy: "stop_if_dirty_overlaps_may_modify"
  verification_rule: "reverify_at_execution_start"
  on_drift: "stop_and_replan"
objective:
  mission: "While the decoded image copy continues, derive ImportScope on a private copy of the already complete journal and record a read-only identity of the running Odoo.sh Production build. The original journal.csv stays byte-for-byte unchanged. No image hash, no importer, and no Production write."
  success_properties:
    - id: "SP-01"
      property: "V1 proves the private journal copy has 111010 rows, ImportScope eligible 97346, archive_only 13077, and unattached 587, and the original journal.csv hash is unchanged."
      evidence_type: "quality_gate"
      proof: ["V1"]
      blocking: true
    - id: "SP-02"
      property: "V2 proves one read-only Production receipt names the running build, the installed state of documents, documents_account, and plasticos_documents_native, the transaction count, and a private id,name,company_id export whose row count equals that count."
      evidence_type: "quality_gate"
      proof: ["V2"]
      blocking: true
capability_preflight_ref: "preflight.plan.simple.worksheet_g0_identity_and_importscope.v1"
execution_envelope:
  filesystem:
    write_allow: ["/Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv", "/Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json", "/Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv"]
    write_deny: ["/Users/ib-mac/Odoo-ERP-Files/journal.csv", "/Users/ib-mac/Odoo-ERP-Files/decoded", "plasticos_documents_native", "the Production database"]
  commands:
    allow: ["V1 journal.import-scope.csv census and original sha256", "V2 g0-identity.json against production-transactions.csv", "python3 -c 'census of journal.import-scope.csv and sha256 of journal.csv'", "python3 -c 'compare g0-identity.json transaction_count with production-transactions.csv rows'"]
  network:
    mode: "read_only"
  secrets:
    access: "read_only_named"
    redaction_required: true
  autonomous_merge: false
side_effects_and_idempotency:
  - todo_id: "T1"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
  - todo_id: "T2"
    side_effects: "filesystem_mutation"
    idempotency: "safe_with_dedupe"
    retry: "retry_once"
rollback_contract_ref: "rollback.plan.simple.worksheet_g0_identity_and_importscope.v1"
dependency_topology_ref: "dag.plan.simple.worksheet_g0_identity_and_importscope.v1"
validation_evidence_refs: ["E-V1", "E-V2"]
stress_and_disconfirm:
  disconfirming_cases: ["Can the derived file replace or rewrite journal.csv?", "Can a RefType outside W, #, P, E, and B receive a guessed ImportScope?", "Can the Staging SSH target be used as the Production identity?", "Can an export whose row count differs from the transaction count be called complete?"]
  assumption_failure_conditions: ["The partial decoded folder is required before ImportScope can be derived.", "Git installability of plasticos_documents_native proves it is installed on the running build.", "A Git Production SHA is the running Odoo.sh build."]
out_of_scope: ["Rewriting or re-extracting the server blobs", "Hashing the partial decoded folder", "A second Postgres or a second document store", "Any Production write, backup restore, or importer", "Committing the journal, the export, or the identity receipt"]
convergence_contract_ref: "conv.plan.simple.worksheet_g0_identity_and_importscope.v1"
execute_via:
  pipeline: cursor-build
  mention_program: "Cursor Build"
  command_ref: PR_STACK=auto make pr
  authority_order:
    - plan_document
    - cursor_build
todos:
  - id: "T1"
    content: "Write /Users/ib-mac/Odoo-ERP-Files/journal.import-scope.csv from the existing journal. Add ImportScope from RefType only: W and # are eligible, P is archive_only, E and B are unattached. Any other RefType fails the write. Leave Status, hashes, and every other column unchanged. Refuse if the destination is journal.csv. After the write, the original file hash must still match the hash taken before the write."
    status: "pending"
  - id: "T2"
    content: "Using only ODOO_SH_PRODUCTION_SSH, open a read-only shell on the running Production database. Record the build hostname, database name, company ids and names, installed state of documents, documents_account, and plasticos_documents_native, and the plasticos.transaction count, unique name count, and company distribution. Write id,name,company_id for every transaction to /Users/ib-mac/Odoo-ERP-Files/private/production-transactions.csv and the identity to /Users/ib-mac/Odoo-ERP-Files/private/g0-identity.json. The export row count must equal the transaction count from the same session. Do not call write, create, unlink, or a module install."
    status: "pending"
```
