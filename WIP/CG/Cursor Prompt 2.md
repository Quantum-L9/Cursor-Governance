We have completed the dormant contract-first Cursor-rules foundation install.

Proceed with PHASE 2: SHADOW VALIDATION.

This phase is observational only.

DO NOT:
- bootstrap ops/config/doctrine-baseline.rules.yaml
- change status: bootstrap_required
- create production Rule Activation Binding instances
- migrate 03, 70, 93, or any other rule
- change any rules/*.mdc semantics
- flip RULES-MANIFEST from v2 to v3
- activate new blocking doctrine policy
- modify pre-commit
- "clean up" legacy doctrine
- resolve conflicts by editing rules
- convert census findings directly into contracts

The purpose is to prove that the new architecture can correctly observe the
existing repository before it is allowed to govern it.

======================================================================
1. VERIFY FOUNDATION STRUCTURE
======================================================================

Confirm all installed modules import and execute from their canonical paths.

Specifically verify:

ops/contracts/build_rules.py
ops/contracts/build_rule_doctrine_census.py
ops/contracts/resolve_rule_contracts.py
ops/contracts/validate_rule_binding.py
ops/contracts/validate_rule_projections.py
ops/contracts/render_cursor_rule.py
ops/contracts/adapters/cursor_rules.py

and all required shared doctrine modules.

Fail on:
- import errors
- circular imports
- WIP/CG imports
- duplicate implementation paths
- unresolved local module paths

Do not solve import problems by adding WIP paths or compatibility wrappers.

======================================================================
2. RUN THE EXISTING COMPILER TEST SUITE
======================================================================

Run:

pytest -q tests/contracts/test_rules_contract_compiler.py

Then run any directly related existing contract/doctrine tests required by
those modules.

Fix TOOLING defects discovered here.

Do not fix legacy doctrine simply because a scanner reports debt.

======================================================================
3. BUILD THE RULE DOCTRINE CENSUS IN SHADOW MODE
======================================================================

Run:

python3 ops/contracts/build_rule_doctrine_census.py

and:

python3 ops/contracts/build_rules.py census

The census must inspect the existing rules/*.mdc corpus without modifying it.

Expected findings MAY include:
- unowned normative doctrine
- duplicate doctrine
- potential conflicts
- advisory material
- workflow/procedure candidates
- capability claims
- historical state
- unknown classifications

Those findings are migration inventory, not Foundation failures.

Integrity failures ARE failures.

Examples:
- parser crashes
- unstable extraction IDs
- invalid provenance
- nondeterministic census
- impossible source paths
- duplicate YAML keys
- malformed generated observational artifact

======================================================================
4. PROVE DETERMINISM
======================================================================

Generate the census twice from the same repository state.

Ignoring only fields explicitly designed as non-semantic volatile metadata,
the resulting semantic content/digest must be identical.

If the census currently includes nondeterministic wall-clock data in semantic
equality, fix the tooling rather than accepting drift.

======================================================================
5. RUN COMPILER CHECK MODE
======================================================================

Run:

python3 ops/contracts/build_rules.py check

There are currently no production generated rule bindings.

Therefore check mode must NOT demand that legacy rules become generated.

It must remain migration-state aware.

Legacy rules are allowed to remain legacy debt during SHADOW.

Fix the validator/compiler if it incorrectly applies generated-state
requirements to legacy files.

======================================================================
6. RUN EXISTING RULE ASSURANCE
======================================================================

Run:

python3 ops/scripts/check_rules_standard.py

The existing repository rule standards remain authoritative during SHADOW.

Do not silently promote existing warnings to blockers.

Do not move global budget ownership out of check_rules_standard.py.

======================================================================
7. RUN EXISTING GENERATED-ARTIFACT PARITY
======================================================================

Run the repository's existing generated artifact check, including:

python3 ops/scripts/sync_generated_artifacts.py --force --check

or the exact currently supported equivalent if flags differ.

Foundation must preserve existing generated artifacts.

======================================================================
8. PROVE ZERO EFFECTIVE RULE CHANGE
======================================================================

Capture git diff/status before and after the shadow commands.

There must be no semantic change to:

rules/*.mdc

There must be no production schema cutover of:

rules/RULES-MANIFEST.json
rules/RULES-MANIFEST.yaml
rules/RULES-MANIFEST.md

The production manifest must remain:

l9.cursor-rules-manifest/v2

A generated observational census under:

generated/governance/rule-doctrine-census.yaml

is allowed if that is the canonical generated location.

======================================================================
9. INSPECT THE CENSUS — DO NOT MIGRATE
======================================================================

Report the actual observed counts:

- total rules
- always-on rules
- doctrine candidates
- hard normative candidates
- conditional normative candidates
- advisory candidates
- unowned doctrine count
- duplicate clusters
- potential conflict clusters
- potential conflict pairs
- unknown classifications
- extraction integrity errors
- unresolved contract references
- highest-priority migration candidates

Also report the top 15 migration candidates by score with:

rule
path
line/section
activation
risk
candidate kind
doctrine strength
duplicate count
conflict count
priority score

Do NOT alter those rules yet.

======================================================================
10. SPECIAL REVIEW OF THE THREE PILOTS
======================================================================

From census evidence only, summarize what the scanner sees in:

rules/70-tool-efficiency.mdc
rules/93-c1-server-protection.mdc
rules/03-graphiti-memory.mdc

For each report:

- candidate blocks
- normative vs advisory split
- potential contract kinds
- potential conflicts
- duplicate doctrine
- extraction ambiguity
- current activation
- expected migration difficulty

Do not create contracts or bindings yet.

======================================================================
11. BASELINE MUST REMAIN DORMANT
======================================================================

Verify:

ops/config/doctrine-baseline.rules.yaml

still contains:

status: bootstrap_required

Do NOT execute --bootstrap-baseline.

That occurs only after the shadow census has been reviewed.

======================================================================
12. SHADOW ACCEPTANCE CONDITIONS
======================================================================

The phase passes when:

compiler/import integrity errors        == 0
census extraction integrity errors     == 0
duplicate binding IDs                  == 0
duplicate output ownership             == 0
generated production bindings          == 0
unexpected rule diffs                  == 0
manifest production version            == v2
manifest unintended diff               == 0
global budget owners                   == 1
baseline status                        == bootstrap_required
WIP/CG production references           == 0

These values MAY legitimately be > 0 during shadow:

legacy doctrine debt
potential duplicate doctrine
potential conflict clusters
unknown classifications

Do not make the architecture pass by suppressing those findings.

======================================================================
13. RETURN A SHADOW REPORT
======================================================================

Return:

A. commands executed + exit codes
B. files changed
C. census summary
D. top 15 migration candidates
E. pilot 70/93/03 classification summary
F. integrity/tooling defects found and fixed
G. unresolved Unknowns
H. proof rules/*.mdc stayed unchanged
I. proof manifest stayed v2
J. proof baseline is still bootstrap_required

STOP after the report.

Do not bootstrap the doctrine baseline.
Do not begin Pilot 70.