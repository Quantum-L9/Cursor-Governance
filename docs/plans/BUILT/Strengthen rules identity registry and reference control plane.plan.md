---
name: Cursor-primary memory unify
built: true
status: built
overview: Kill Dropbox SSOT doctrine that makes agents ENOENT-loop, then relocate the HTTP memory brain into ops/memory/ (Cursor-primary) with thin Claude/Manus adapters — validated PLAN_DOCUMENT already PASSes l9-plan schema.
todos:
  - id: M1-dropbox-doctrine
    content: "M1: Kill Dropbox SSOT in rules/92, learning lessons, skills, commands, ops fallbacks; regenerate llm-rules"
    status: completed
  - id: M2-ops-memory
    content: "M2: Create ops/memory/ brain; thin-wrap Claude memory hooks + retarget contract/settings/validators"
    status: completed
  - id: M3-cursor-hydrate
    content: "M3: Cursor sessionStart HTTPS hydrate via ops/memory; update CANONICAL_LAW §8 / MEMORY_TOPOLOGY / skills"
    status: completed
  - id: gate-pr-check
    content: "Final: Dropbox rg zero + validate_memory_enforcement PASS + make pr-check before PR"
    status: completed
isProject: false
---
---

name: Strengthen rules identity registry and reference control plane
overview: >-
Harden the Cursor-Governance rules control plane before any large corpus
merge, renumber, activation-demotion, or extraction migration. Establish
explicit stable rule identity, complete disk-to-manifest registration,
schema-validated metadata/manifest/selection contracts, deterministic
generated artifacts, compatibility-aware selector resolution, typed
stale-reference auditing, and stabilization idempotence. The outcome is a
control plane capable of proving correctness for the later high-fanout rules
corpus cleanup without changing rule semantics or renumbering the corpus in
this plan.
todos:

- id: CP0-bind-baseline
content: Bind exact Cursor-Governance SHA/worktree, dirty overlap, applicable rule instructions, schemas, generators, selectors, projections, and mandatory validation
status: pending
- id: CP1-freeze-identity
content: Inventory every rules/*.mdc file and freeze current explicit/effective identity, filename, stem, prefix, activation, domain, authority, selectors, and consumers before any identity mutation
status: pending
- id: CP2-complete-registry
content: Repair disk↔manifest completeness so every eligible .mdc appears exactly once and stale/missing manifest entries fail closed
status: pending
- id: CP3-schema-gates
content: Enforce rule-metadata, rule-manifest, and rule-selection JSON Schemas through existing validators without weakening schema consts/enums
status: pending
- id: CP4-selector-contract
content: Make canonical id the durable selector while preserving explicitly mapped compatibility aliases for existing stem/file consumers
status: pending
- id: CP5-reference-graph
content: Build a typed in-repo rule-reference graph and implement audit_rule_references.py with active-selector/link/prose vs migration/history/fixture semantics
status: pending
- id: CP6-generated-integrity
content: Strengthen manifest and LLM projection generation so generated artifacts are deterministic, complete, source-owned, and never hand-edited
status: pending
- id: CP7-prefix-audit
content: Add prefix-collision reporting and one-prefix validation capability without renumbering any rule in this plan
status: pending
- id: CP8-stabilization
content: Make rules-stabilize authoritative and idempotent; run generation/validation twice and require zero material second-pass diff
status: pending
- id: CP9-regression
content: Add focused tests for missing manifest members, duplicate ids, alias resolution, stale active refs, permitted historical refs, generated drift, and repeated stabilization
status: pending
- id: CP10-full-validation
content: Run targeted control-plane validation, make rules-stabilize, make pr-check, final diff audit, and convergence check
status: pending
isProject: false

---

# Strengthen Rules Identity, Registry, and Reference Control Plane

## 1. Mission

Strengthen the machinery that proves correctness of the `rules/` corpus **before**
performing the high-fanout consolidation/renumbering proposed in the Rules Corpus
Cleanup plan.

The control plane must be able to prove:

```text
rule source
   ↓
schema-valid explicit identity
   ↓
complete generated manifest
   ↓
canonical selector + compatibility aliases
   ↓
surface selection/projection
   ↓
typed reference audit
   ↓
deterministic stabilization

```

Only after this plan is green should the corpus migration perform merges,
renames, demotions, extraction, or large consumer rewrites.

## 2. Architectural decision

The durable architecture is:

```yaml
identity:
  machine_identity: frontmatter.id
  human_sorting: filename numeric prefix
  filename_identity: false
  prefix_authority: false
  activation_authority: metadata/runtime contract

registry:
  source: rules/*.mdc frontmatter
  generated_register: RULES-MANIFEST.json
  generation_direction: source_to_manifest
  manifest_editing: generated_only

selection:
  canonical_selector: id
  compatibility_selectors:
    - stem
    - file
  compatibility_policy: explicit_and_auditable

projection:
  source: canonical manifest + projection configuration
  generated_outputs: deterministic

validation:
  failure_policy: fail_closed
  stale_active_reference_policy: fail_closed
  historical_reference_policy: permitted_when_classified

```

The numeric filename prefix is a human navigation/delivery-order field, not a
stable machine identity or authority signal.

## 3. Plan class

```yaml
plan_class: control_plane_hardening
redesign_allowed: bounded
rule_semantic_changes_allowed: false
bulk_renumber_allowed: false
activation_demotions_allowed: false
rule_merges_allowed: false
rule_deletions_allowed: false
schema_loosening_allowed: false
generated_output_direct_edit_allowed: false
autonomous_merge_allowed: false

```

## 4. Relationship to the corpus-cleanup plan

This plan is a prerequisite to the larger cleanup.

It specifically removes the following migration risks identified in the source
plan:

- manifest/disk drift;
- unstable or derived machine identity;
- ambiguous old/new selector semantics;
- stale hard-coded references;
- false-positive stale-reference scanning;
- generated artifact drift;
- unsafe renumbering before the reference graph is known;
- inability to prove second-run convergence.

The later corpus plan may consume the artifacts produced here, especially:

```text
rules identity inventory
selector compatibility map
typed reference graph
prefix collision report
validated manifest
stabilization command

```

## 5. Authority and contracts

Bind and inspect the exact current versions of:

```text
CANONICAL_LAW.md
AGENTS.md
commands/rules.md

ops/schemas/rule-metadata.schema.json
ops/schemas/rule-manifest.schema.json
ops/schemas/rule-selection.schema.json

ops/scripts/generate_rules_manifest.py
ops/scripts/validate_rules_manifest.py
ops/scripts/sync_selected_rules.py
ops/scripts/project_llm_rules.py
ops/scripts/sync_generated_artifacts.py
ops/scripts/audit_rules_corpus.py

ops/config/llm_rules_projection.yaml

rules/*.mdc
rules/RULES-MANIFEST.*

tests covering rules, manifest, selection, projection, or stabilization
Make targets: rules-validate / rules-stabilize / pr-check

```

Do not infer parallel contracts if current authoritative equivalents exist under
different names.

## 6. Baseline binding

At execution start record:

```yaml
repository: Quantum-L9/Cursor-Governance
workspace: /Users/ib-mac/Cursor-Governance
branch: <observed>
commit_sha: <observed>
dirty: <observed>
rules_file_count: <observed>
manifest_rule_count: <observed>
explicit_id_count: <observed>
derived_or_missing_id_count: <observed>
prefix_collision_count: <observed>

```

Also capture SHA256 for:

```text
rules/*.mdc
rules/RULES-MANIFEST.*
ops/schemas/rule-*.schema.json
ops/config/llm_rules_projection.yaml

```

Stop if dirty state overlaps any write-allowed control-plane surface and cannot
be safely attributed.

## 7. Identity freeze before migration

Create an authoritative migration-preflight report under `reports/`, for example:

```text
reports/rules-control-plane-identity-map.yaml

```

This report is evidence, not runtime SSOT.

For every `rules/*.mdc`, record:

```yaml
file: 99-no-auto-commit.mdc
stem: 99-no-auto-commit
numeric_prefix: "99"

explicit_id: <value-or-null>
effective_current_id: <actual currently resolved id>
planned_canonical_id: <same as existing durable identity unless separately migrated>

activation:
  alwaysApply: <bool>
  activation: <metadata value>

scope: <value>
domain: <value>
authority: <value>

selectors_observed:
  - id
  - stem
  - file

references:
  active_selectors: []
  active_file_links: []
  active_prose: []
  generated: []
  tests: []
  historical: []

```

No rename/delete/merge may occur until every current rule has an entry.

## 8. Stable identity law

### Existing explicit ID

If valid and already consumed:

```text
preserve exactly

```

### Existing effective ID derived from filename/stem

Before assigning a new semantic ID, determine whether that effective identity is
already durable through:

- selection config;
- generated artifacts;
- tests;
- adapters;
- docs;
- out-of-repo migration contract.

If it is consumed, either:

```text
freeze current effective id

```

or define an explicit compatibility migration.

### New semantic IDs

A new semantic ID is allowed only when:

- no durable machine identity existed; or
- an explicit migration record exists.

Do not silently turn:

```text
old stem-derived identity
→ new semantic identity

```

into an untracked breaking change.

## 9. Identity migration record

If a semantic ID migration is necessary, record:

```yaml
old_selectors:
  - <old-id>
  - <stem>
  - <filename>

canonical_id: <new-id>

compatibility:
  aliases:
    - <required-old-selector>
  behavior: resolve_to_canonical
  deprecation_status: active
  removal_condition:
    - all in-repo active consumers migrated
    - migration window documented
    - external compatibility decision recorded

```

Aliases must not create a second canonical identity.

## 10. Metadata schema enforcement

Every register-member `.mdc` must validate against:

```text
ops/schemas/rule-metadata.schema.json

```

The validator must enforce the schema as written.

Do not weaken:

- enum values;
- required fields;
- identifier patterns;
- activation semantics;
- deprecated/replacement constraints.

Where current corpus metadata does not conform, this plan may normalize metadata
only as necessary to make the current semantic state explicit.

It must not change behavioral intent.

## 11. Disk ↔ manifest completeness

The current baseline in the source plan reports 64 `.mdc` files but only 63
manifest members, with `87-l4-local-autonomy.mdc` missing.

Before mass corpus migration, fix the registry contract so:

```text
eligible rules on disk
==
manifest entries

```

Required invariants:

```yaml
manifest_integrity:
  each_disk_rule_exactly_once: true
  manifest_entry_without_disk_rule: forbidden
  duplicate_manifest_id: forbidden
  duplicate_manifest_file: forbidden
  generated_manifest_stale: failure

```

The generator and validator must disagree loudly with stale state rather than
silently tolerating it.

## 12. Manifest schema enforcement

Generated:

```text
RULES-MANIFEST.json

```

must validate against:

```text
ops/schemas/rule-manifest.schema.json

```

and retain the expected schema contract:

```text
$schema = l9.cursor-rules-manifest/v2

```

unless the actual authoritative schema differs at execution time.

Do not bump manifest schema merely to perform this hardening.

## 13. Selection contract

Selection must validate against:

```text
ops/schemas/rule-selection.schema.json

```

Preserve existing contract constants, including those identified in the source
plan when still authoritative:

```yaml
mode: individual_symlink
failure_mode: fail_closed
preserve_unknown_files: true

```

The canonical selection preference must become:

```text
id first

```

Compatibility lookup may accept:

```text
id ∪ aliases ∪ stem ∪ filename

```

where current implementation supports it.

Resolution must return exactly one canonical rule.

Ambiguous selectors fail closed.

## 14. Selector uniqueness

For every selector accepted by `sync_selected_rules.py` or equivalent:

```text
selector → exactly one canonical rule

```

Fail on:

- duplicate IDs;
- alias collisions;
- alias equal to another rule's canonical ID;
- stem collision that resolves ambiguously;
- filename collision;
- selector resolving to deleted/nonexistent rule.

Do not silently choose the first match.

## 15. Typed rule-reference graph

Add a deterministic reference audit rather than plain global `rg`.

Recommended implementation:

```text
ops/scripts/audit_rule_references.py

```

The auditor must classify references.

Allowed classes:

```yaml
active_selector:
  blocking_if_stale: true

active_file_link:
  blocking_if_stale: true

active_prose_instruction:
  blocking_if_stale: true

generated_reference:
  blocking_if_stale: true
  remediation: regenerate_source_owned_artifact

compatibility_alias_fixture:
  blocking_if_stale: false
  must_resolve: true

migration_map:
  blocking_if_stale: false

changelog_history:
  blocking_if_stale: false

archived_or_historical_evidence:
  blocking_if_stale: false

unknown:
  blocking_if_stale: true
  action: classify_before_completion

```

## 16. Reference audit scope

Audit at minimum:

```text
CANONICAL_LAW.md
AGENTS.md
commands/**
skills/**
environment/**
ops/**
tests/**
.cursor-plugin/**
rules/** metadata/links
active root docs

```

Explicitly classify:

```text
reports/**
_archived/**
migration maps
CHANGELOG history
legacy compatibility fixtures

```

before deciding whether an old stem is stale.

Do not create broad exclusions that hide active references.

## 17. Reference identity preference

When modifying active machine-consumed selectors in this plan:

```text
prefer canonical id

```

When human-facing prose benefits from filename visibility, use:

```text
human file name + canonical id

```

where useful.

Example:

```text
99-no-auto-commit.mdc (`l9.rule.git.mutation-gate`)

```

Do not require prose to become unreadable merely to use IDs.

## 18. Prefix control-plane semantics

Add validation/reporting for numeric prefixes now, but do not renumber rules in
this plan.

The contract is:

```yaml
numeric_prefix:
  pattern: NN
  purpose:
    - human navigation
    - deterministic filename ordering
    - coarse category band
  not_authoritative_for:
    - identity
    - precedence
    - activation
    - policy authority

```

## 19. Prefix collision reporting

The validator/auditor must report:

```yaml
prefix: "87"
files:
  - ...
severity: migration_blocker

```

for duplicate prefixes.

During this control-plane plan, collisions may remain as known baseline debt if
the existing corpus contains them.

The validator must support two modes:

```yaml
baseline_mode:
  collisions: report

migration_final_mode:
  collisions: fail

```

or an equivalent project-native mechanism.

Do not make the current branch unworkable before the migration plan has authority
to resolve the collisions.

## 20. Future one-prefix invariant

Prepare validation for the later corpus target:

```text
exactly one rules/{NN}-*.mdc per numeric prefix

```

but activate it as a mandatory final gate only in the migration plan once all
collisions are resolved.

This avoids conflating control-plane hardening with corpus mutation.

## 21. Generated artifact law

Generated artifacts include, where currently authoritative:

```text
rules/RULES-MANIFEST.*
environment/generated/llm-rules/**

```

Rules:

1. never hand-edit generated content;
2. identify authoritative source/config;
3. regenerate via supported command;
4. validate;
5. regenerate again;
6. require zero material second-run diff.

Known candidate commands:

```bash
python3 ops/scripts/generate_rules_manifest.py
python3 ops/scripts/project_llm_rules.py

```

Re-verify actual command ownership at execution.

## 22. Projection integrity

`project_llm_rules.py` or equivalent must consume canonical rule identity and
manifest state rather than reconstructing policy from filename conventions when
the manifest already provides the information.

Validate:

```text
source rules
  ↓
manifest
  ↓
projection config
  ↓
generated surface

```

No independent projection-time identity inference should compete with the
manifest.

## 23. Preserve pinned projection contracts

Do not change high-fanout pin/alias behavior in this plan except where required
to make the control plane explicit.

Known contracts from the source plan include:

```text
23-l9-skill-routing
84-cursor-governance-wiring

```

Verify rather than assume their exact current projection semantics.

The later corpus plan owns their rename/pin decisions.

## 24. Strengthen `audit_rules_corpus.py`

Extend the existing corpus audit only with control-plane checks such as:

- missing explicit/effective identity;
- duplicate canonical ID;
- duplicate selector alias;
- disk/manifest count mismatch;
- manifest entry missing file;
- file missing manifest entry;
- schema invalidity;
- prefix collisions;
- generated artifact drift;
- unknown stale-reference classification.

Do not implement activation quotas or semantic demotion policy in this plan.

## 25. `validate_rules_manifest.py`

Strengthen the validator to prove:

```yaml
metadata_schema_valid: true
manifest_schema_valid: true
disk_manifest_bijection: true
canonical_ids_unique: true
selectors_unambiguous: true
generated_manifest_current: true

```

Prefix collision may remain warning/report-only until the migration plan enables
the final invariant.

## 26. `audit_rule_references.py`

The auditor should operate from a frozen rename/identity map or current
manifest—not a hand-maintained list of grep strings.

Required inputs should include:

```text
canonical IDs
filenames
stems
compatibility aliases
historical classifications

```

Required outputs:

```yaml
active_stale_references: []
historical_references: []
compatibility_references: []
unknown_references: []

```

Exit nonzero when:

```text
active_stale_references != []
or unknown_references != []

```

## 27. Control-plane reports

Permitted persistent reports:

```text
reports/rules-control-plane-identity-map.yaml
reports/rules-control-plane-reference-audit.json

```

Only create them if they materially support the subsequent migration/review.

They are migration evidence, not runtime authority.

## 28. Stabilization contract

`make rules-stabilize` should become the authoritative composed control-plane
operation if that target already owns this responsibility.

It should result in a fully synchronized state containing:

```text
validated rule metadata
generated manifest
validated manifest
projected generated rules
validated projections
reference audit
corpus audit

```

Do not create a competing stabilization command if one already exists.

## 29. Stabilization idempotence

Blocking sequence:

```bash
make rules-stabilize
git diff --exit-code <generated-and-control-plane-derived-state>

make rules-stabilize
git diff --exit-code <generated-and-control-plane-derived-state>

```

Operationally, when the first run legitimately updates generated files:

1. run stabilization;
2. capture resulting state;
3. run stabilization again;
4. require zero additional material diff.

A stabilization command that changes its own already-stabilized output is not
converged.

## 30. Regression scenarios

### CP-R1 — Missing disk member from manifest

Remove/omit one rule in a fixture.

Expected:

```text
validator fails

```

### CP-R2 — Ghost manifest entry

Manifest references nonexistent rule.

Expected:

```text
validator fails

```

### CP-R3 — Duplicate canonical ID

Two rules share one ID.

Expected:

```text
validator fails

```

### CP-R4 — Ambiguous selector

Alias/stem/file resolves to multiple rules.

Expected:

```text
selection fails closed

```

### CP-R5 — Legacy alias

Known compatibility selector maps to one canonical rule.

Expected:

```text
resolution succeeds
canonical identity returned

```

### CP-R6 — Active stale reference

Active skill/command uses removed test fixture stem.

Expected:

```text
reference auditor fails

```

### CP-R7 — Historical old reference

Migration report/CHANGELOG references old stem.

Expected:

```text
reference auditor classifies historical
does not fail solely for presence

```

### CP-R8 — Unknown reference class

Reference is neither clearly active nor historical.

Expected:

```text
audit fails closed until classified

```

### CP-R9 — Schema-invalid metadata

Expected:

```text
validator fails

```

### CP-R10 — Schema-invalid selection fixture

Expected:

```text
validator fails

```

### CP-R11 — Generated drift

Manually alter generated manifest/projection fixture.

Expected:

```text
stabilization restores canonical output
validation detects pre-regeneration drift

```

### CP-R12 — Second stabilization

Expected:

```text
zero material diff

```

## 31. Write envelope

Allowed:

```text
ops/scripts/generate_rules_manifest.py
ops/scripts/validate_rules_manifest.py
ops/scripts/sync_selected_rules.py
ops/scripts/project_llm_rules.py
ops/scripts/audit_rules_corpus.py
ops/scripts/audit_rule_references.py

direct tests/fixtures for these tools

commands/rules.md
Makefile/rules target wiring only if required

rules/*.mdc metadata only where necessary to freeze current identity or make
metadata schema-valid without changing semantic behavior

rules/RULES-MANIFEST.* via generator only
environment/generated/llm-rules/** via generator only

ops/config/llm_rules_projection.yaml only if required to preserve existing
projection contract

reports/rules-control-plane-*.{yaml,json,md}

```

Conditionally allowed:

```text
ops/schemas/rule-*.schema.json

```

only if execution proves an additive defect in the schema itself.

Schema loosening to accommodate broken implementation is forbidden.

Denied:

```text
bulk rule renumber
rule merges
rule deletions
activation demotions
large content extraction
Git/autonomy doctrine consolidation
Graphiti doctrine rewrite
unrelated skill changes
out-of-repo consumers
force push
merge

```

## 32. No semantic rule migration

This plan must not:

- merge `01/96/99`;
- delete `03-mcp-memory`;
- merge `99-graphiti-temporal`;
- extract `92`;
- demote `alwaysApply`;
- rename colliding rules;
- alter rule precedence;
- enact the target band map.

Those belong to the subsequent corpus migration.

Metadata normalization is allowed only when it preserves current behavior.

## 33. Execution DAG

```mermaid
flowchart LR
  bind[Bind exact baseline] --> inventory[Freeze identity + consumers]
  inventory --> registry[Repair disk-manifest completeness]
  registry --> schema[Enforce metadata/manifest/selection schemas]
  schema --> selectors[Harden canonical selector + aliases]
  selectors --> refs[Build typed reference graph]
  refs --> generated[Harden deterministic generation]
  generated --> prefixes[Add prefix collision audit]
  prefixes --> stabilize[Compose rules-stabilize]
  stabilize --> regress[Run control-plane regression suite]
  regress --> full[make pr-check]
  full --> idem[Second stabilization idempotence]
  idem --> final[Final diff + convergence]

```



## 34. Blocking success properties

```yaml
success_properties:
  - id: CP-SP01-explicit-identity
    requirement: >
      Every register-member rule has a valid, stable canonical machine identity
      or an explicitly recorded compatibility migration.

  - id: CP-SP02-id-not-filename
    requirement: >
      Canonical machine identity is not inferred from a future filename rename
      once explicit identity is established.

  - id: CP-SP03-disk-manifest-bijection
    requirement: >
      Every eligible rules/*.mdc file appears exactly once in the manifest and
      every manifest member resolves to exactly one disk file.

  - id: CP-SP04-schema-metadata
    requirement: >
      Rule metadata validates against rule-metadata.schema.json.

  - id: CP-SP05-schema-manifest
    requirement: >
      RULES-MANIFEST.json validates against rule-manifest.schema.json.

  - id: CP-SP06-schema-selection
    requirement: >
      Selection fixtures/configuration validate against
      rule-selection.schema.json.

  - id: CP-SP07-id-unique
    requirement: >
      Canonical rule ids are globally unique in the corpus.

  - id: CP-SP08-selector-unambiguous
    requirement: >
      Every supported id/alias/stem/file selector resolves to at most one
      canonical rule; ambiguous selectors fail closed.

  - id: CP-SP09-reference-types
    requirement: >
      Stale-reference validation distinguishes active references from permitted
      migration/history/compatibility evidence.

  - id: CP-SP10-active-stale-zero
    requirement: >
      No unresolved stale active rule reference remains in the validated scope.

  - id: CP-SP11-generated-source-owned
    requirement: >
      Manifest and LLM projections are generated only from authoritative sources
      and are not hand-maintained.

  - id: CP-SP12-generation-idempotent
    requirement: >
      Re-running manifest/projection generation on stabilized state yields no
      material diff.

  - id: CP-SP13-prefix-visible
    requirement: >
      Existing numeric-prefix collisions are deterministically detected and
      reported for the later migration.

  - id: CP-SP14-no-semantic-migration
    requirement: >
      This control-plane plan does not renumber, merge, delete, demote, or
      materially change behavioral rule contracts.

  - id: CP-SP15-rules-stabilize
    requirement: >
      make rules-stabilize establishes the complete validated derived state and
      a second run produces no material diff.

  - id: CP-SP16-pr-check
    requirement: >
      make pr-check passes against the exact final state.

  - id: CP-SP17-scope
    requirement: >
      Final diff contains only control-plane, metadata-normalization,
      validation, generated, and directly required documentation changes.

```

## 35. Validation commands

Discover authoritative project equivalents first.

Expected:

```bash
python3 ops/scripts/generate_rules_manifest.py
python3 ops/scripts/validate_rules_manifest.py
python3 ops/scripts/project_llm_rules.py
python3 ops/scripts/audit_rules_corpus.py
python3 ops/scripts/audit_rule_references.py

make rules-stabilize
make pr-check

```

Also run all directly associated unit/shell tests discovered during inventory.

## 36. Final-state checks

Before convergence:

```text
all rules represented in manifest
all canonical ids unique
all schemas valid
all supported selectors unambiguous
no active stale references
all generated outputs current
prefix collision report complete
rules-stabilize second run clean
pr-check green
working tree contains no unrelated residue

```

## 37. Stress / disconfirm

Fail the plan if:

- the current 64/63 disk-manifest mismatch can still pass validation;
- a rule can disappear from the manifest silently;
- two rules can share a canonical ID;
- one selector can resolve ambiguously;
- a stale active stem can survive the reference audit;
- historical migration text triggers an unavoidable false-positive failure;
- generated artifacts require hand edits;
- second stabilization produces drift;
- the implementation weakens schema validation to make legacy files pass;
- a semantic ID change occurs without compatibility treatment;
- this plan begins renumbering or merging the corpus;
- mandatory validation fails or is Unknown.

## 38. Out of scope

- target band renumbering;
- unique-prefix migration itself;
- `alwaysApply` reduction;
- rule content extraction;
- Git-rule consolidation;
- temporal-memory merge;
- deprecated-rule deletion;
- incident-rule extraction;
- anti-pattern extraction;
- `00-global` tightening;
- consumer renames tied to the later rename map;
- out-of-repo `rules.yaml` mutation;
- schema redesign;
- unrelated governance architecture.

## 39. Handoff contract to the corpus-migration plan

The later corpus cleanup may begin only when this plan provides:

```yaml
control_plane_ready: true

identity:
  every_rule_canonical_id: true
  duplicate_ids: 0

registry:
  disk_count: <observed>
  manifest_count: <same>
  missing_manifest_members: 0
  ghost_manifest_members: 0

selection:
  ambiguous_selectors: 0
  compatibility_aliases: <recorded>

references:
  active_stale: 0
  historical_classified: true
  unknown: 0

prefixes:
  collisions:
    - <complete observed collision set>

generation:
  manifest_idempotent: true
  llm_projection_idempotent: true

validation:
  rules_stabilize: Passed
  make_pr_check: Passed

```

The handoff must also include the frozen identity/reference map required to safely
construct the later rename and merge plan.

## 40. Convergence

Declare `Converged` only when:

- every current rule has a stable canonical identity;
- disk and manifest form a verified bijection;
- metadata, manifest, and selection schemas pass;
- selectors are deterministic and unambiguous;
- stale active references fail closed;
- historical/compatibility references are explicitly classified;
- generated artifacts are source-owned and deterministic;
- prefix collision inventory is complete;
- stabilization is idempotent;
- `make pr-check` passes;
- no semantic corpus migration occurred;
- no Critical/High control-plane finding remains;
- another control-plane pass has no specific evidence-backed high-value
objective.

## 41. Handoff

Deliver:

- exact base/final SHA;
- rule identity map;
- selector compatibility map;
- typed reference audit;
- prefix collision inventory;
- changed control-plane scripts/tests;
- generated manifest/projection state;
- schema-validation results;
- stabilization idempotence evidence;
- `make pr-check` evidence;
- residual Unknowns, if any.

Only after this handoff is green should the corpus merge/renumber/tighten plan be
executed.
