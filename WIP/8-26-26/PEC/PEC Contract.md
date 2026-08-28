CONTRACT: BOOTSTRAP-PEC-000
TITLE: Build PEC Intent-Compiler Conformance + Shadow Comparison Harness

ROLE
You are the implementation executor for this contract.

You are NOT being asked to redesign PEC from scratch.
You are NOT executing this work through PEC.
Claude Code Desktop is the temporary execution substrate while PEC is being repaired.

Your job is to inspect the live repository deeply, reconcile this contract against actual current implementation, then implement the smallest correct set of changes necessary to satisfy the objective and acceptance tests.

Do not merge.
Do not push unless separately authorized.
Do not invent parallel architecture when canonical machinery already exists.

======================================================================
PRIMARY OBJECTIVE
======================================================================

Build the bridge that lets us repair PEC using real human-intent workloads.

PEC must eventually accept ordinary human intent, normalize it through however many internal IR/compiler phases are required, ground it against the live repository, and produce a faithful executable Blueprint without requiring the human to understand PEC-internal schemas or choose the correct compiler route.

For now:

1. Claude Code + model executes explicit implementation contracts.
2. The exact same raw human intent is also compiled through PEC in SHADOW MODE.
3. PEC MUST NOT execute the shadow campaign.
4. We compare PEC's semantic interpretation against a trusted expected semantic contract.
5. The harness reports intent loss, false CREATE decisions, grounding errors, authority drift, missing prohibitions, missing acceptance conditions, and other compiler defects.
6. The resulting fixture corpus becomes permanent PEC compiler conformance infrastructure.

This contract is about the HUMAN-INTENT → COMPILER portion of PEC.

Do NOT implement RiskPacket, ImpactEngine, World Model, or autonomous risk-aware replanning in this contract.

======================================================================
ARCHITECTURE LAW
======================================================================

The required direction is:

    HUMAN INPUT
        permissive / arbitrary understandable prose
              |
              v
        SOURCE CAPTURE
              |
              v
        SEMANTIC INTENT IR
              |
              v
        LIVE REPOSITORY GROUNDING
              |
              v
        RECONCILIATION / DISPOSITION
              |
              v
        REQUIREMENT + AUTHORITY IR
              |
              v
        EXECUTION GRAPH
              |
              v
           BLUEPRINT
              |
              v
         PROGRAM LOCK
              |
              v
            PEC

Strictness increases as the compiler moves downstream.

The human MUST NOT be required to manually speak Blueprint, CampaignSource,
ProgramIntent, ArchitectureIntent, or any other PEC-internal representation.

Internal schemas may remain strict.

Human ingress must be permissive.

Unknowns must remain UNKNOWN until safely resolved.
They must not be silently converted into assumptions.

======================================================================
CANONICAL PRINCIPLES
======================================================================

Preserve these:

- Blueprint owns design-time scope and authorization ceilings.
- Program Controller owns mutable runtime Program truth.
- Existing REPLAN_CONTRACT remains canonical.
- Existing authorization model remains canonical.
- Existing evidence model remains canonical.
- Existing receipt families remain canonical.
- TransportPacket remains the L9 transport contract.
- Compiler/extractor output is not authority.
- Runtime/machine-readable implementation outranks stale prose when they conflict.
- Existing canonical implementation must be MERGED/HARDENED, not recreated.

Forbidden architectural moves:

- second Program Controller
- second Program-state store
- second replanning protocol
- second authorization model
- second evidence model
- second receipt universe
- second transport protocol
- new human-facing requirement to choose an internal compiler representation
- treating an unknown implementation seam as permission to invent a write target
- silently dropping human constraints because they are lowercase or conversational
- declaring success merely because a generated artifact validates syntactically

======================================================================
PHASE 0 — MICROSOCOPE BEFORE MUTATION
======================================================================

Before editing anything, deeply inspect every current seam involved in:

human input
→ input classification/routing
→ minimal intent
→ architecture intent
→ source capture
→ architecture extraction
→ IR
→ coverage
→ critic/repair
→ repository truth/grounding
→ campaign-source lowering
→ Blueprint synthesis
→ Blueprint validation
→ launchability
→ Program Lock
→ campaign execution entry point

At minimum inspect current implementations and all important callers/tests around:

- environment/program-execution/scripts/campaign_input.py
- environment/program-execution/scripts/run_campaign.py
- environment/program-execution/compiler/
- compiler intent parsing
- architecture intent/source capture
- architecture extractor
- architecture IR
- architecture coverage
- critic/repair
- repo_truth
- architecture_to_campaign
- campaign source schemas
- Blueprint synthesis
- Blueprint validation
- launchability
- Program Lock construction
- Makefile campaign targets
- AGENTS.md
- CLAUDE.md
- applicable canonical-law/shared-contract files

Do NOT assume these exact filenames still describe the current implementation.

Follow imports, symbols, callers, schemas, tests, generated artifacts, and runtime entrypoints.

For every relevant mechanism classify it:

- CANONICAL_ACTIVE
- PARTIAL
- DUPLICATE
- LEGACY
- SUPERSEDED
- GENERATED
- DEAD_PATH
- UNKNOWN

Do not modify code until this map is understood.

======================================================================
PHASE 1 — CHARACTERIZE CURRENT FAILURE
======================================================================

Create characterization tests BEFORE semantic fixes.

Establish how current PEC handles at least:

A. one-sentence freeform human intent
B. ordinary Markdown without PEC schema markers
C. explicit program-execution.intent.v1
D. explicit architecture-intent input
E. long ADR/design document
F. lowercase conversational prohibition:
      "don't replace assurance"
G. uppercase normative prohibition:
      "DO NOT REPLACE ASSURANCE"
H. request for something that already exists
I. vague but harmless implementation intent
J. ambiguous authority-bearing intent

For each case capture:

- selected input route
- compiler stages reached
- canonical intermediate artifacts
- semantic concepts preserved
- semantic concepts lost
- rejection point
- whether user had to know an internal PEC schema/route
- whether any side effects occurred

The test harness must make current defects reproducible.

======================================================================
PHASE 2 — BUILD PERMANENT INTENT CONFORMANCE CORPUS
======================================================================

Create a permanent test corpus in the canonical compiler-test location.

If no appropriate location exists, choose one consistent with current repository
test organization and justify it.

Include fixtures equivalent to:

01_one_sentence_intent
02_brain_dump
03_long_architecture_adr
04_lowercase_prohibition
05_conflicting_requirements
06_existing_feature_requested_again
07_superseded_design_requested
08_vague_business_goal
09_detailed_technical_spec
10_chat_transcript_style_intent
11_no_explicit_target
12_explicit_target
13_authority_ambiguity
14_safe_resolvable_ambiguity

Do not test for exact LLM wording.

Define semantic assertions.

Examples:

- objective retained
- prohibition retained
- constraint retained
- acceptance condition retained
- unknown remains unknown
- authority is not widened
- existing implementation is not classified CREATE
- superseded implementation is not selected as canonical
- source provenance exists
- target resolution is correct
- no material human requirement silently disappears

======================================================================
PHASE 3 — DEFINE A NORMALIZED SEMANTIC ASSERTION FORMAT
======================================================================

Implement a test-facing semantic expectation format.

It does NOT need to become production runtime law.

It must allow a fixture to state expected semantics such as:

objective_contains:
  - runtime consequence-aware execution

preserve:
  - existing Assurance authority
  - existing replanning contract

prohibitions:
  - do not create duplicate Assurance
  - do not create duplicate replanning subsystem

expected_dispositions:
  replanning: HARDEN_WIRE_EXISTING
  impact_engine: CREATE

unknowns_expected:
  - runtime impact implementation location

authority_must_not_expand: true

source_traceability_required: true

Use the smallest representation that can support durable semantic regression tests.

Do not create another Blueprint format.

======================================================================
PHASE 4 — UNIFY HUMAN INGRESS
======================================================================

Repair the public input boundary so that ordinary human intent can enter the compiler without requiring the operator to select an internal PEC representation.

Desired behavior:

    raw text / markdown / ADR / explicit supported schema
                    |
                    v
              unified ingress
                    |
                    v
        deterministic source capture
                    |
                    v
         internal normalization route

The compiler MAY internally choose different normalization strategies for:

- tiny/simple intent
- dense architecture intent
- explicit canonical IR

but that distinction must not be required knowledge for the user.

Important:

Do NOT delete strict internal schemas merely to make ingress permissive.

Instead introduce/repair the normalization boundary before them.

An explicit valid PEC schema must continue to work.

======================================================================
PHASE 5 — SEMANTIC FIDELITY
======================================================================

Inspect current materiality/coverage behavior carefully.

Fix semantic loss where reasonable human expressions such as:

- don't
- never
- must not
- should not
- preserve
- keep
- reuse
- don't replace
- only
- except
- unless

can disappear merely because they were not expressed as uppercase normative keywords.

Preserve deterministic lexical anchors if useful.

Add semantic handling rather than replacing strong deterministic checks with unconstrained LLM interpretation.

Every materially relevant source unit must receive an explicit disposition such as:

- represented
- intentionally omitted with reason
- duplicate
- superseded
- unknown
- conflict
- non-material

No silent disappearance.

======================================================================
PHASE 6 — REPOSITORY GROUNDING SEAM
======================================================================

Inspect current repo_truth/grounding machinery.

Do NOT replace useful existing RepoTruth functionality.

Extend or add the minimal missing structure necessary for the compiler to answer:

- what implementation already exists?
- what file/symbol owns it?
- who calls it?
- which schema governs it?
- which tests prove it?
- is it canonical?
- is it generated?
- is it legacy?
- is it superseded?
- is there a duplicate?
- does this requested concept already exist under another name?
- which architecture authority owns the behavior?

The compiler needs dispositions BEFORE task synthesis:

- ALREADY_SATISFIED
- KEEP
- MERGE_WITH_EXISTING
- HARDEN_WIRE_EXISTING
- CREATE
- DELETE_SUPERSEDED
- MIGRATION_CONTEXT
- UNKNOWN

If implementing the full repository microscope is too large for this contract,
implement the smallest durable IR/interface + enough grounding capability to support
the conformance harness, and explicitly record residual work.

Do not fake completeness.

======================================================================
PHASE 7 — SHADOW COMPILER
======================================================================

Implement a command/test harness that takes one source human-intent fixture and:

1. preserves the exact source;
2. compiles it through current PEC compiler stages;
3. does NOT execute the resulting campaign;
4. extracts normalized semantic results;
5. compares them against the fixture's semantic expectations;
6. emits a structured report.

The report must identify at least:

- missing objectives
- missing requirements
- missing prohibitions
- missing acceptance conditions
- lost unknowns
- false CREATE classifications
- incorrect KEEP/MERGE/HARDEN classifications
- authority widening
- target-resolution mismatch
- missing source provenance
- ungrounded implementation claims

No execution side effects are allowed in shadow mode.

======================================================================
PHASE 8 — CONFORMANCE SCORE
======================================================================

Expose machine-readable and human-readable summary metrics.

At minimum:

material_intent_loss_count
prohibition_loss_count
acceptance_loss_count
unknown_loss_count
false_create_count
grounding_error_count
authority_widening_count
source_traceability_percent
fixture_pass_count
fixture_fail_count

Do not collapse all semantics into one opaque score.

A summary score may exist, but raw dimensions must remain visible.

======================================================================
PHASE 9 — END-TO-END GOLDEN JOURNEY
======================================================================

After compiler fixes, prove these journeys:

1.
one-sentence human intent
→ compiler normalization
→ valid Blueprint
→ NO manual intermediate artifact editing

2.
long architecture ADR
→ compiler normalization
→ source-grounded Blueprint
→ constraints/prohibitions preserved

3.
explicit program-execution.intent.v1
→ supported canonical route
→ no dead-end requiring manual conversion

4.
request for functionality already implemented
→ grounding recognizes implementation
→ compiler avoids false CREATE

5.
authority-bearing ambiguity
→ UNKNOWN / blocked / escalation
→ no authority widening

6.
safe ambiguity that can be resolved from repository truth
→ grounding resolves it
→ compilation continues

======================================================================
PHASE 10 — PRODUCE BOOTSTRAP BRIDGE ARTIFACT
======================================================================

Document the temporary bridge workflow for subsequent implementation contracts:

    raw human intent
        |
        v
    trusted explicit implementation contract
        |
        v
    Claude Code / model execution

IN PARALLEL:

    same raw human intent
        |
        v
    PEC shadow compiler
        |
        v
    semantic conformance report

The bridge is TEMPORARY.

Do not create a competing orchestrator.

Its purpose is to generate real compiler fixtures while useful repository work continues.

======================================================================
ACCEPTANCE TESTS
======================================================================

AT-001
Given ordinary one-sentence human intent,
when submitted through the public compiler ingress,
then the user is not required to identify an internal PEC schema or compiler route.

AT-002
Given lowercase "don't replace assurance",
then the prohibition survives normalization with source provenance.

AT-003
Given equivalent uppercase and lowercase prohibitions,
then both produce semantically equivalent prohibition assertions.

AT-004
Given program-execution.intent.v1 input,
then it does not dead-end merely because the campaign router refuses that internal kind.

AT-005
Given architecture input,
then every materially relevant source unit receives an explicit disposition.

AT-006
Given requested functionality already present in the repository,
then the compiler can represent ALREADY_SATISFIED / KEEP / HARDEN_WIRE_EXISTING
instead of blindly producing CREATE.

AT-007
Given an unknown implementation seam,
then the compiler does not fabricate a mutation path.

AT-008
Given authority-bearing ambiguity,
then uncertainty does not become permission.

AT-009
Given shadow compilation,
then no repository/runtime execution side effect occurs.

AT-010
Given semantic fixture expectations,
then the comparator reports semantic differences independently of exact generated wording.

AT-011
Given an explicit valid PEC canonical input,
then unified ingress preserves compatibility.

AT-012
Given a malformed or unsafe source,
then failure occurs before execution side effects.

======================================================================
NON-GOALS
======================================================================

Do NOT in this contract:

- implement RiskPacket
- implement ImpactEngine
- modify l9-assurance protocol
- build World Model
- build autonomous risk-aware replanning
- replace REPLAN_CONTRACT
- redesign peer execution
- redesign Gate
- change Program Controller ownership
- merge or push

======================================================================
IMPLEMENTATION DISCIPLINE
======================================================================

Before each substantive implementation choice:

1. locate current canonical implementation;
2. follow callers/imports;
3. inspect tests;
4. inspect schemas/contracts;
5. identify ownership;
6. determine whether the requested behavior is missing, partial, or superseded.

If this contract names a component that has already been superseded in live code:

DO NOT recreate it.

Use the live canonical implementation and record the deviation.

If the repository materially contradicts this contract:

STOP that branch of implementation and report CONTRACT_DRIFT with:
- exact path/symbol
- observed behavior
- why the contract is stale
- recommended converged action

Continue unrelated safe work where possible.

======================================================================
REQUIRED FINAL EVIDENCE
======================================================================

Return:

1. BASE REVISION
2. RESULT REVISION / working-tree status
3. FILES CHANGED
4. FILES CREATED
5. FILES DELETED
6. CANONICAL SEAMS DISCOVERED
7. SUPERSEDED/DEAD PATHS DISCOVERED
8. TESTS ADDED
9. EXACT TEST COMMANDS
10. TEST RESULTS
11. GOLDEN-JOURNEY RESULTS
12. COMPILER CONFORMANCE METRICS
13. REMAINING FAILURES
14. RESIDUAL UNKNOWNS
15. CONTRACT_DRIFT findings
16. ARCHITECTURE BOUNDARY CHECK:
    - second controller created? NO
    - second transport created? NO
    - second authorization model created? NO
    - second evidence model created? NO
    - second replanner created? NO
17. RECOMMENDED NEXT CONTRACT

Do not report COMPLETE if required tests fail.

Do not hide existing failures.
Distinguish:
- pre-existing failure
- regression introduced by this contract
- unresolved contract requirement

======================================================================
SUCCESS CONDITION
======================================================================

This contract succeeds when PEC has a measurable, repeatable compiler-conformance harness proving how faithfully it transforms normal human intent toward Blueprint semantics, while Claude Code remains the actual implementation executor.

We must be able to take the NEXT real architecture request, execute it manually through a trusted contract, simultaneously shadow-compile the exact same raw intent through PEC, and use the semantic difference as actionable evidence for improving PEC.

That is the bridge.