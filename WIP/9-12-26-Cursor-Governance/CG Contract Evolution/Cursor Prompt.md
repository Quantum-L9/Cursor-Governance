We are installing the contract-first Cursor-rules foundation from WIP/CG.

WIP/CG IS A STAGING AREA ONLY.

Hard rule:
- Do not import anything from WIP/CG.
- Do not add WIP/CG to sys.path.
- Do not create wrappers, forwarding modules, compatibility modules, aliases,
  package facades, or temporary architecture around WIP/CG.
- Install every artifact directly into its final canonical repository path.
- After installation, production code must have zero references to WIP/CG.
- If a destination already exists, DIFF and integrate deliberately at that exact
  destination. Do not create a second implementation elsewhere.
- Do not invent new directories when a destination is specified below.

======================================================================
A. CANONICAL CONTRACT SCHEMAS
======================================================================

Install these directly:

WIP/CG/canonical.schema.governance_contract.v1.yaml
  -> contracts/schemas/canonical.schema.governance_contract.v1.yaml

WIP/CG/canonical.schema.invariant_contract.v1.yaml
  -> contracts/schemas/canonical.schema.invariant_contract.v1.yaml

WIP/CG/canonical.schema.policy_contract.v1.yaml
  -> contracts/schemas/canonical.schema.policy_contract.v1.yaml

WIP/CG/canonical.schema.capability_contract.v1.yaml
  -> contracts/schemas/canonical.schema.capability_contract.v1.yaml

WIP/CG/canonical.schema.workflow_contract.v1.yaml
  -> contracts/schemas/canonical.schema.workflow_contract.v1.yaml

WIP/CG/canonical.schema.evidence_contract.v1.yaml
  -> contracts/schemas/canonical.schema.evidence_contract.v1.yaml

WIP/CG/canonical.schema.contract_extraction_record.v1.yaml
  -> contracts/schemas/canonical.schema.contract_extraction_record.v1.yaml

WIP/CG/canonical.schema.contract_projection_binding.v1.yaml
  -> contracts/schemas/canonical.schema.contract_projection_binding.v1.yaml

WIP/CG/canonical.schema.contract_registry.v1.yaml
  -> contracts/schemas/canonical.schema.contract_registry.v1.yaml

WIP/CG/canonical.schema.rule_activation_binding.v1.yaml
  -> contracts/schemas/canonical.schema.rule_activation_binding.v1.yaml

WIP/CG/canonical.schema.cursor_rules_manifest.v3.yaml
  -> contracts/schemas/canonical.schema.cursor_rules_manifest.v3.yaml

IMPORTANT:
The v3 schema belongs at the path above now, but merely installing the schema
does NOT authorize flipping the production RULES-MANIFEST writer from v2 to v3.

======================================================================
B. ARCHITECTURE DECISIONS
======================================================================

WIP/CG/ADR-0007-contracts-own-rule-semantics.md
  -> docs/decisions/ADR-0007-contracts-own-rule-semantics.md

WIP/CG/ADR-0008-rule-activation-binding-intermediate-representation.md
  -> docs/decisions/ADR-0008-rule-activation-binding-intermediate-representation.md

WIP/CG/ADR-0009-normative-advisory-rule-channels.md
  -> docs/decisions/ADR-0009-normative-advisory-rule-channels.md

WIP/CG/ADR-0010-rule-activation-and-context-budget.md
  -> docs/decisions/ADR-0010-rule-activation-and-context-budget.md

WIP/CG/ADR-0011-deterministic-generated-cursor-rule-projections.md
  -> docs/decisions/ADR-0011-deterministic-generated-cursor-rule-projections.md

WIP/CG/ADR-0012-rules-manifest-generated-projection-registry.md
  -> docs/decisions/ADR-0012-rules-manifest-generated-projection-registry.md

WIP/CG/ADR-0013-rule-compiler-fail-closed-conflicts-scope-and-drift.md
  -> docs/decisions/ADR-0013-rule-compiler-fail-closed-conflicts-scope-and-drift.md

WIP/CG/ADR-0014-rules-strangler-migration-and-doctrine-ratchet.md
  -> docs/decisions/ADR-0014-rules-strangler-migration-and-doctrine-ratchet.md

======================================================================
C. SHARED DOCTRINE ENGINE
======================================================================

These live together under ops/contracts. They are shared infrastructure, not a
new Cursor-rules package.

WIP/CG/extract_doctrine.py
  -> ops/contracts/extract_doctrine.py

WIP/CG/cluster_doctrine.py
  -> ops/contracts/cluster_doctrine.py

WIP/CG/detect_hidden_doctrine.py
  -> ops/contracts/detect_hidden_doctrine.py

WIP/CG/build_doctrine_census.py
  -> ops/contracts/build_doctrine_census.py

WIP/CG/validate_doctrine_ratchet.py
  -> ops/contracts/validate_doctrine_ratchet.py

If any of these already exist:
- preserve this exact destination;
- diff WIP against the repository copy;
- integrate only required compatible changes;
- do NOT fork them into rule-specific duplicates.

======================================================================
D. CURSOR-RULE ADAPTER
======================================================================

Create the adapter directory if absent:

  ops/contracts/adapters/

Install:

WIP/CG/cursor_rules.py
  -> ops/contracts/adapters/cursor_rules.py

This is the platform adapter. Do NOT place cursor_rules.py beside build_rules.py
and do not create ops/contracts/cursor/.

======================================================================
E. RULE CONTRACT COMPILER / ASSURANCE MODULES
======================================================================

Install directly:

WIP/CG/resolve_rule_contracts.py
  -> ops/contracts/resolve_rule_contracts.py

WIP/CG/validate_rule_binding.py
  -> ops/contracts/validate_rule_binding.py

WIP/CG/render_cursor_rule.py
  -> ops/contracts/render_cursor_rule.py

WIP/CG/validate_rule_projections.py
  -> ops/contracts/validate_rule_projections.py

WIP/CG/build_rule_doctrine_census.py
  -> ops/contracts/build_rule_doctrine_census.py

WIP/CG/build_rules.py
  -> ops/contracts/build_rules.py

These modules form one implementation topology:

ops/contracts/build_rules.py
    |
    +-- ops/contracts/adapters/cursor_rules.py
    +-- ops/contracts/validate_rule_binding.py
    +-- ops/contracts/resolve_rule_contracts.py
    +-- ops/contracts/render_cursor_rule.py
    +-- ops/scripts/generate_rules_manifest.py

Do NOT reorganize these into a Python package during this task.
Do NOT introduce __init__.py/refactor work merely to make imports prettier.
Use the repository's existing script/module conventions.

======================================================================
F. RULE DOCTRINE BASELINE
======================================================================

WIP/CG/doctrine-baseline.rules.yaml
  -> ops/config/doctrine-baseline.rules.yaml

It MUST remain:

  status: bootstrap_required

Do NOT bootstrap it in this installation task.

The bootstrap operation is a later reviewed activation step.

======================================================================
G. RULE PROJECTION SOURCE DIRECTORY
======================================================================

Ensure this canonical directory exists:

  contracts/projections/rules/

This is where Rule Activation Binding INSTANCES will eventually live.

DO NOT create pilot bindings yet.
DO NOT populate 03, 70, or 93 bindings yet.
DO NOT create bindings for all legacy rules.

An empty directory may require a repository-standard placeholder only if Git
tracking conventions require it; otherwise simply allow build tooling to create
it when the first binding is added.

======================================================================
H. TEST
======================================================================

WIP/CG/test_rules_contract_compiler.py
  -> tests/contracts/test_rules_contract_compiler.py

Do not move these tests under ops/contracts.
They belong in the repository's contract test suite.

======================================================================
I. EXISTING MANIFEST GENERATOR -- SPECIAL CASE
======================================================================

WIP/CG/generate_rules_manifest.py is NOT a new parallel generator.

Its only legal destination is:

  ops/scripts/generate_rules_manifest.py

However, DO NOT blindly replace the current production file with the WIP
version because the WIP implementation already emits manifest v3.

Instead:

1. diff:
   WIP/CG/generate_rules_manifest.py
   against
   ops/scripts/generate_rules_manifest.py

2. integrate the contract-first projection-index capability into the EXISTING
   file at:
   ops/scripts/generate_rules_manifest.py

3. keep the production/default writer on:
   l9.cursor-rules-manifest/v2

4. preserve the current v2 output contract during Foundation.

5. do not import build_rules from generate_rules_manifest.py.

Dependency direction must be:

build_rules.py
    -> generate_rules_manifest.py

NEVER:

generate_rules_manifest.py
    -> build_rules.py

The manifest renderer may accept an explicit projection_index argument from its
caller, but it must not discover/load compiler state by reaching upward.

======================================================================
J. CORRECTION REQUIRED WHILE INSTALLING build_rules.py
======================================================================

Do NOT install WIP/CG/build_rules.py byte-for-byte.

Install it at:

  ops/contracts/build_rules.py

but remove the duplicate repository-global rules budget ownership during the
installation.

Specifically, build_rules.py must NOT define or own:

  GLOBAL_ALWAYS_BUDGET
  RULES_ALWAYS_BUDGET
  181203

The existing:

  ops/scripts/check_rules_standard.py

remains the sole owner of the repository-global always-on rules budget.

build_rules.py MAY:
- measure generated rule bytes;
- expose those measurements;
- enforce each binding's context_budget_bytes.

It must NOT become a second global-budget policy owner.

======================================================================
K. EXISTING FILES TO MODIFY FOR WIRING
======================================================================

These are NOT staging files to relocate. Modify them in place only after the
foundation files above are installed.

1. ops/scripts/generate_rules_manifest.py

Purpose:
- leaf manifest renderer;
- accept projection information explicitly;
- remain production v2 during Foundation;
- never import build_rules.

2. ops/scripts/sync_generated_artifacts.py

Purpose:
eventually establish:

sync_generated_artifacts.py
    -> ops/contracts/build_rules.py
    -> generated rule projections + manifest renderer

For this Foundation pass, wire only if it can preserve EXACT current generated
artifacts. No effective rules or manifest-schema cutover is permitted.

3. ops/scripts/check_rules_standard.py

Purpose:
remain the repository-facing rules assurance owner and the sole global
always-on budget owner.

Do not duplicate its existing budget/policy constants into compiler modules.

Foundation may expose/delegate new read-only checks only when that produces no
legacy-corpus breakage.

4. Makefile

Only add/adjust narrow command surfaces needed to invoke the installed
foundation in read-only/shadow mode.

Do not create a second build topology.

5. Existing CI workflow containing governance-self-check / generated-artifact
checks

Do not fan six low-level Python commands into CI.
Keep the existing repository-facing gate topology.
Foundation wiring must be minimal and non-disruptive.

6. .pre-commit-config.yaml

DO NOT MODIFY during this phase.

======================================================================
L. GENERATED OUTPUT DESTINATIONS -- DO NOT CREATE BY HAND
======================================================================

These remain their canonical existing locations:

rules/*.mdc

rules/RULES-MANIFEST.json
rules/RULES-MANIFEST.yaml
rules/RULES-MANIFEST.md

Later, generated .mdc files are written directly to their existing rules/*
paths according to binding.target.output_path.

Never create:

rules/generated/
generated/rules/
contracts/generated-rules/
WIP/CG/generated/
RULES-MANIFEST.v3.yaml
RULES-MANIFEST.v2.yaml

There is one rule namespace and one manifest artifact set.

The doctrine census may generate:

generated/governance/rule-doctrine-census.yaml

That file is observational/generated state, not semantic authority.

======================================================================
M. INSTALLATION INVARIANTS
======================================================================

After this task:

WIP/CG references in production code                == 0
parallel compiler implementations                   == 0
parallel manifest generators                        == 0
global rules-budget owners                          == 1
production manifest schema                          == v2
production Rule Activation Binding instances        == 0
rules migrated to generated                         == 0
legacy .mdc semantic changes                        == 0
doctrine baseline status                            == bootstrap_required
pre-commit changes                                  == 0

No pilot migration.
No manifest v3 cutover.
No doctrine baseline bootstrap.
No rule authority transfer.

======================================================================
N. FINAL VERIFICATION
======================================================================

Report:

1. every WIP/CG source file found;
2. its exact final destination;
3. whether destination was CREATE, MERGE, or EXISTING/UNCHANGED;
4. any WIP file not covered by this map;
5. any expected mapped WIP file that was absent;
6. all existing repository files modified for wiring;
7. tests/checks executed and exit codes;
8. proof that no production code references WIP/CG;
9. proof that tracked rules/*.mdc did not change semantically;
10. proof that production RULES-MANIFEST remains v2;
11. proof doctrine-baseline.rules.yaml remains bootstrap_required.

If a WIP/CG artifact cannot be mapped unambiguously to one of the paths above,
STOP FOR THAT ARTIFACT and report it rather than inventing a destination.