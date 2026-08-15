Claude Code Execution Contract

Program Execution Intent Compiler v1

Contract ID: CC-PE-INTENT-COMPILER-V1
Execution mode: autonomous, evidence-driven, repo-local
Primary objective: implement program-execution.intent.v1 and the intent-resolution/program-synthesis pipeline that converts minimal goal-level user input into a validator-clean Program Execution Blueprint v2 without weakening existing authority, verification, or runtime boundaries.

⸻

1. Mission

Evolve the current Quantum-L9 Program Execution architecture so a user can initiate a high-quality autonomous program with minimal input such as:

Evolve l9-devpack-compiler so I can give it a simple goal and it handles the full execution pipeline autonomously.

The system must resolve that sparse intent into:

1. target repositories;
2. governing authority;
3. relevant repository truth;
4. constraints and invariants;
5. accepted policy-derived decisions;
6. explicit Unknowns;
7. evidence requirements;
8. workstreams;
9. tasks and dependencies;
10. authorization ceilings;
11. convergence gates;
12. rollback requirements;
13. a validator-clean Program Execution Blueprint v2.

The user must not need to manually supply architecture, task decomposition, file plans, tests, sequencing, repository topology, validation commands, rollback implementation, or worker prompts when those facts can be discovered or derived safely.

⸻

2. Architectural Outcome

Implement this pipeline:

Natural-language user goal
        │
        ▼
program-execution.intent.v1
        │
        ▼
Intent Resolver
        │
        ├── target resolution
        ├── governing-policy resolution
        ├── repository evidence discovery
        ├── DPK / repository-truth loading
        ├── decision classification
        └── Unknown classification
        │
        ▼
INTENT_RESOLUTION.yaml
        │
        ▼
Program Synthesizer
        │
        ▼
Program Execution Blueprint v2
        │
        ▼
official Blueprint validation
        │
        ▼
Program Lock
        │
        ▼
RUN_REQUEST / Controller

This is a compiler boundary, not a new runtime controller.

The existing Program Execution Controller remains the exclusive runtime authority for mutable execution state, task attempts, verification results, gate results, leases, recovery state, and handoff receipts.

⸻

3. Non-Negotiable Authority Rules

Apply this precedence whenever information conflicts:

1. safety / security / legal constraints
2. latest accepted program decision
3. accepted architecture and authoritative contracts
4. verified current-state evidence
5. approved generated task authority
6. implementation
7. documentation
8. historical material
9. Unknown → fail closed only where dependent work requires it

Additional hard rules:

* downstream authority may narrow upstream authority but never widen it;
* generated task scope cannot override architecture or public contracts;
* the Intent Compiler may generate definitions but never Controller runtime state;
* a worker claim is not independent verification;
* Program Execution final convergence remains a program-owner decision;
* authority-affecting defaults require explicit governing provenance;
* an absent fact must never silently become authority;
* Unknowns block only named dependent work;
* permissions never default to allowed because a field is omitted;
* no remote mutation is authorized by this contract.

⸻

4. User-Facing Intent Contract

Implement a canonical schema named:

program-execution.intent.v1

The user-facing contract must remain deliberately small.

Minimum conceptual form:

schema: program-execution.intent.v1
objective: >
  Evolve l9-devpack-compiler so a user can trigger the complete
  Program Execution pipeline from minimal natural-language intent.
targets:
  - l9-devpack-compiler
policy_profile: quantum-l9.safe-autonomy.v1
termination:
  mode: program_handoff

Only require information that cannot safely be discovered.

Do not require the user to provide:

* implementation tasks;
* files to change;
* workstreams;
* dependency graphs;
* execution waves;
* architecture decisions already available from authority;
* validation commands discoverable from repository truth;
* rollback mechanisms already defined by authority;
* repository topology already resolvable from registered targets;
* worker prompts;
* test plans that can be compiled from acceptance criteria;
* credentials or secret values.

The schema may support optional user-supplied constraints, but those constraints must only narrow the active policy profile.

⸻

5. Intent Resolution Artifact

Create a canonical intermediate artifact:

INTENT_RESOLUTION.yaml

Use a schema similar to:

schema: program-execution.intent-resolution.v1
intent:
  id: INTENT-...
  original_objective: ...
  normalized_objective: ...
targets:
  - repository_id: ...
    resolution_source: ...
    evidence_ids: [...]
    confidence: high | medium | low
governing_authority:
  policy_profile: ...
  source_ids: [...]
  decision_ids: [...]
derived_requirements:
  - id: REQ-...
    statement: ...
    source:
      type: evidence | decision | policy | user
      ref: ...
decisions:
  accepted_from_authority: [...]
  accepted_from_policy: [...]
  requires_human_authority: [...]
unknowns:
  - id: UNK-...
    topic: ...
    blocks: [...]
    safe_state: ...
    resolution_requirements: [...]
evidence:
  authoritative: [...]
  supporting: [...]
  stale_or_conflicting: [...]
program_action:
  mode: create | extend | supersede
  parent_program_ref: null
confidence:
  intent_resolution: high | medium | low
  target_resolution: high | medium | low
  authority_resolution: high | medium | low
  repository_understanding: high | medium | low
synthesis_status: ready | blocked | requires_authority

Every material derived requirement must be traceable to:

* the user;
* verified repository evidence;
* an accepted decision;
* or a governing policy.

No unattributed machine inference may become execution authority.

⸻

6. Intent Resolution Semantics

The Intent Resolver must classify every unresolved issue into one of four classes.

A. Evidence-determined

The answer exists in authoritative evidence.

Resolve automatically.

Examples:

* repository runtime version;
* test command;
* package manager;
* existing public interface;
* architecture boundary;
* current ownership declaration.

B. Policy-determined

An explicit active policy determines the answer.

Resolve automatically and record provenance.

Examples:

* default autonomy tier;
* maximum permission ceiling;
* whether local writes are allowed;
* whether independent verification is required.

C. Reversible planning choice

No authority decision is required and the choice remains within the existing authority envelope.

The synthesizer may choose autonomously.

Examples:

* splitting one task into two;
* ordering two independent implementation steps;
* test fixture naming;
* internal helper structure.

Record the choice as generated planning metadata where useful.

D. Authority-bearing decision

The answer would:

* widen scope;
* change architecture;
* modify a public contract;
* accept material irreversible risk;
* expand permissions;
* redefine ownership;
* cross an explicit policy boundary;
* authorize remote/destructive behavior;
* or contradict accepted authority.

Do not invent the answer.

Create an explicit decision or Unknown and block only dependent work.

⸻

7. Policy Profiles

Implement support for referenced autonomy profiles rather than forcing users to specify low-level permissions.

Add or formalize:

quantum-l9.safe-autonomy.v1

Conceptual policy:

schema: program-execution.autonomy-policy.v1
id: quantum-l9.safe-autonomy.v1
execution:
  continue_until: blocking_authority_boundary
planning:
  generate_tasks: true
  reorder_independent_tasks: true
  split_tasks: true
  merge_tasks: true
  repair_failed_plan: true
  create_scoped_unknowns: true
decisions:
  evidence_determined: auto
  policy_determined: auto
  reversible_planning_choice: auto
  architecture_change: require_authority
  public_contract_change: require_authority
  permission_expansion: require_authority
  irreversible_risk_acceptance: require_authority
authorization_ceiling:
  inspect: true
  local_write: true
  commit: true
  push: true
  pull_request: true
  merge: false
  publish_or_release: false
  deploy_or_migrate: false
  destructive_change: false
  external_message: false
verification:
  independent: required
  worker_self_verification: insufficient
unknowns:
  block_only_dependents: true
  resolve_from_authoritative_evidence: true
replanning:
  allowed_within_locked_authority: true
  authority_widening: forbidden

The exact location should follow existing repository conventions discovered during execution.

Do not duplicate an existing policy system if one already exists.

⸻

8. Repository and DPK Integration

Reuse existing repository truth instead of regenerating it heuristically.

The Intent Resolver should consume, when present:

.ai/manifest.yaml
.ai/repository-map.yaml
.ai/constraints.yaml
.ai/execution-package.yaml
AGENTS.md
authoritative schemas
ADRs
accepted decisions
validation commands
rollback definitions
observability definitions
technical-debt registers
existing DPK intermediate representation

Evidence priority:

verified runtime/current-state evidence
>
machine-readable authoritative contracts
>
actual repository structure/code
>
verified architecture/ADR material
>
human prose
>
inference

Do not reimplement repository operability discovery if the remediated l9-devpack-compiler already supplies the required DPK IR.

Prefer:

repo
 ↓
DPK compiler
 ↓
canonical repository-truth IR
 ↓
Intent Resolver / Program Synthesizer

over:

repo
 ↓
independent second repository parser

⸻

9. Program Synthesis

Build a deterministic Program Synthesizer that consumes:

program-execution.intent-resolution.v1

and emits a complete Program Execution Blueprint v2.

The generated set must include every artifact required by the current official EXECUTION_INDEX.yaml.

At minimum, synthesis must correctly generate or project:

PROGRAM.yaml
EXECUTION_TARGETS.yaml
AUTHORITY_REGISTRY.yaml
DECISION_REGISTER.yaml
UNKNOWN_REGISTER.yaml
RISK_REGISTER.yaml
WAIVER_REGISTER.yaml
EVIDENCE_CATALOG.yaml
DO_NOT_BUILD.yaml
CURRENT_STATE_DELTA.yaml
WORKSTREAMS.yaml
DEPENDENCY_GRAPH.yaml
EXECUTION_WAVES.yaml
TASK_CARDS.yaml
CONVERGENCE_GATES.yaml
OBSERVABILITY_PLAN.yaml
CUTOVER_AND_ROLLBACK.yaml
SOURCE_TRACEABILITY.yaml

plus any other files required by the exact Program Execution v2 contract present at execution time.

Do not hard-code the source list if the governing Program Execution contract already provides a machine-readable index.

⸻

10. Task Synthesis Rules

Generated tasks must:

* have one clear objective;
* have one execution target;
* cite authority basis;
* cite required decisions;
* name blocking Unknowns;
* cite input evidence;
* define outputs;
* define acceptance criteria;
* define validation;
* define negative cases;
* define rollback;
* define risk;
* define the exact canonical authorization ceiling;
* name completion gates.

Task generation must favor the smallest independently verifiable mutation.

Do not generate giant implementation tasks when the work can be decomposed into independently evidenced steps.

Do not fragment work purely for token-count reasons.

⸻

11. Dependency and Wave Synthesis

Dependencies must be derived from actual information and execution dependencies.

Never duplicate dependency authority into multiple independent sources.

Respect the Program Execution canonical owner for task dependencies.

Generate parallelism where:

* tasks have no authority dependency;
* tasks do not contend over the same mutable ownership boundary;
* validation does not require ordered evidence;
* failure isolation remains clear.

Prefer:

authority/current-state lock
        ↓
parallel safe discovery / semantic corrections
        ↓
implementation
        ↓
integration
        ↓
independent verification
        ↓
handoff

when appropriate.

⸻

12. Evidence-Driven Acceptance

Every generated acceptance criterion must be verifiable.

Reject synthetic criteria such as:

"implementation looks correct"
"code quality is good"
"architecture seems clean"

Prefer:

command exits zero
schema validates
negative fixture fails as intended
contract compatibility remains unchanged
expected state is observed
forbidden state is absent
official validator passes

Evidence types must distinguish:

structural inspection
command execution
test execution
runtime observation
contract validation
human authority acceptance

Structural evidence must never be represented as runtime proof.

⸻

13. Program Validation

Generated programs must be validated with the exact governing Program Execution Blueprint validator available at runtime.

Do not maintain a second approximate validator when the official validator can be invoked.

The pipeline must be:

Intent
 ↓
Resolution
 ↓
Synthesis
 ↓
official Program Execution validation
 ↓
PASS → eligible for Program Lock
FAIL → repair or explicit blocker

Validation failure may trigger autonomous repair when:

* the repair does not alter user intent;
* no authority decision is required;
* no policy ceiling is widened.

Otherwise escalate.

⸻

14. Program Action Resolution

The Intent Resolver must determine whether a new request should:

create
extend
supersede

an existing program.

Rules:

create

Use when no accepted program governs the requested objective.

extend

Use only when the requested work is already within the accepted authority and scope of an active program and extension does not mutate locked authority illegally.

supersede

Use when:

* objective materially changes;
* authority changes;
* accepted decisions change;
* authorization ceiling changes;
* target set changes materially;
* convergence semantics change;
* a locked program needs architectural revision.

Never silently mutate an immutable Program Lock.

⸻

15. Minimal Front-Door UX

Provide a CLI or equivalent entrypoint consistent with repository conventions.

Desired UX:

program-execution intent \
  "Evolve l9-devpack-compiler so a user can trigger the full pipeline from a simple goal"

or equivalent.

If a target is required:

program-execution intent \
  --target l9-devpack-compiler \
  "Simplify user invocation while preserving output quality and long autonomous execution"

Expected result:

Intent parsed
Targets resolved
Authority resolved
Repository truth loaded
Program synthesized
Blueprint validation PASS
Program prepared for lock

If authority is required:

Intent parsed
Program partially synthesized
1 authority-bearing decision requires owner input
Independent work remains unblocked where possible

Do not dump a giant questionnaire onto the user.

Ask only for genuinely unresolved authority-bearing decisions.

⸻

16. Long-Chain Design Requirement

Design all state so future bounded replanning can operate without replaying the entire conversational history.

Persist typed state rather than relying on LLM memory.

At minimum preserve:

original intent
normalized intent
Program Lock
current execution state
decision register
Unknown register
evidence ledger
risk register
attempt receipts
verification receipts
gate receipts
source traceability

The implementation does not need to implement full program-execution.replan.v1 unless naturally required, but it must not make bounded replanning difficult.

Expose stable interfaces suitable for the future contract:

program-execution.replan.v1

⸻

17. Files and Implementation Strategy

Do not assume exact paths before inspecting the repository.

First:

1. inspect the repository;
2. locate existing Program Execution contracts;
3. locate DPK integration points;
4. locate schema conventions;
5. locate validators;
6. locate policy/profile mechanisms;
7. locate CLI or orchestration entrypoints;
8. locate tests and fixtures.

Then produce the smallest architecture-aligned file plan.

New concepts likely required:

intent schema
intent-resolution schema
autonomy-policy schema or profile
Intent Resolver
Program Synthesizer
official-validator adapter
CLI/front-door entrypoint
fixtures
negative tests
traceability tests

Reuse existing modules whenever their responsibility already matches.

Do not create parallel abstractions with different names for existing concepts.

⸻

18. Mandatory Test Matrix

Implement automated tests covering at least:

Happy path

Minimal goal + resolvable target + complete repo truth:

intent
→ resolution
→ complete Blueprint
→ official validator PASS

Sparse input

User provides only objective and unambiguous repository context.

Expected:

no unnecessary clarification

Evidence-determined fact

Repository declares test command.

Expected:

auto-resolved with evidence provenance

Policy-determined fact

Policy profile declares local-write ceiling.

Expected:

auto-resolved with policy provenance

Authority-bearing architecture choice

Two incompatible architecture approaches exist without accepted authority.

Expected:

decision/Unknown emitted
dependent work blocked
unrelated work remains eligible

Missing ownership

No owner and no governing default policy exists.

Expected:

owner remains unresolved
no invented owner

Unknown scoping

Missing deployment credential affects deployment only.

Expected:

local implementation/testing not globally blocked

Permission widening

Generated task would require push but policy allows local_write only.

Expected:

task cannot gain push authority
authority escalation required

Structural versus runtime evidence

Test command exists but has not executed.

Expected:

test existence != test PASS

Conflicting source authority

README contradicts accepted architecture contract.

Expected:

architecture contract wins
conflict recorded

Existing program

New objective materially changes accepted architecture.

Expected:

supersede
not silent mutation

Malformed synthesis

Generated Blueprint fails official validation.

Expected:

bounded repair attempt if non-authority issue
otherwise explicit blocker

Runtime ownership contamination

Synthesizer attempts to emit attempt/gate runtime state.

Expected:

rejected

⸻

19. Quality Gates

Do not declare completion until all of the following are true.

Gate A — Contract

* program-execution.intent.v1 exists and validates.
* minimal valid input is genuinely minimal.
* user fields describe outcome/authority, not implementation.

Gate B — Resolution

* INTENT_RESOLUTION.yaml or its canonical equivalent exists.
* every material derived requirement has provenance.
* Unknowns are explicit and dependency-scoped.
* authority-bearing choices are never invented.

Gate C — Synthesis

* minimal intent produces the complete required Blueprint v2 source set.
* generated task authorization ceilings are exact and non-widening.
* source traceability is preserved.
* no Controller runtime state is emitted.

Gate D — Validation

* representative generated program passes the official Program Execution Blueprint validator in instantiated mode.
* negative generated programs fail for the expected reasons.

Gate E — UX

A user can initiate program synthesis from a small natural-language goal plus only genuinely necessary target information.

No architecture questionnaire is required on the happy path.

Gate F — Regression

* all pre-existing tests pass;
* all new tests pass;
* existing Program Execution v2 validation passes;
* existing DPK/exemplary validation remains passing where applicable;
* no tests, red-lines, or authority constraints were weakened.

⸻

20. Stop Conditions

Stop the affected branch of work and return an explicit blocker when:

* Program Execution v2 governing contracts conflict materially;
* the target repository cannot be resolved safely;
* implementing the feature requires changing Program Execution runtime authority;
* a required architecture decision has no accepted authority;
* a required permission exceeds the active autonomy profile;
* the solution requires remote mutation;
* official validation cannot pass without weakening governance;
* credentials or secret values would need to be invented;
* a destructive or irreversible operation becomes necessary;
* repository evidence is materially stale and cannot be refreshed safely.

Do not stop globally for an issue that blocks only one dependent branch.

⸻

21. Prohibited Actions

Do not:

* commit;
* push;
* create a pull request;
* merge;
* publish;
* release;
* deploy;
* migrate production state;
* perform destructive operations;
* send external messages;
* invent owners;
* invent credentials;
* invent repository locations;
* invent public contracts;
* weaken validators;
* delete tests to get PASS;
* bypass official Blueprint validation;
* store runtime state in DPK or Intent Compiler artifacts;
* turn conversational inference into authority without provenance.

⸻

22. Autonomous Execution Behavior

Work autonomously through all non-blocked phases.

Do not ask the user for implementation preferences that are:

* discoverable from the repository;
* determined by accepted architecture;
* governed by explicit policy;
* reversible local planning choices.

When uncertainty appears:

classify
→ seek evidence
→ apply authority order
→ resolve if authorized
→ otherwise create scoped blocker
→ continue independent work

Prefer continued verified progress over premature human escalation.

⸻

23. Independent Verification

Do not treat your own implementation claims as sufficient evidence.

After implementation:

1. execute deterministic tests;
2. execute schema validators;
3. execute official Program Execution Blueprint validation;
4. inspect generated fixtures independently from the generation path;
5. inspect final diff for:
    * authority widening;
    * undocumented defaults;
    * runtime responsibility duplication;
    * scope creep;
    * weakened tests;
    * invented infrastructure;
    * accidental remote capabilities.

Record exact commands and results.

⸻

24. Completion Report

Return a concise structured report:

STATUS
PASS | BLOCKED | PARTIAL
IMPLEMENTED
- ...
GENERATED CONTRACTS
- program-execution.intent.v1
- program-execution.intent-resolution.v1
- ...
USER EXPERIENCE
Before:
...
After:
...
VALIDATION
- command → PASS
- official Blueprint validation → PASS
- regression → PASS
AUTHORITY CHECK
- authority widening: none
- runtime ownership moved: no
- undocumented defaults: none
- remote actions performed: none
OPEN UNKNOWNS
- ...
RESIDUAL RISKS
- ...
NEXT ARCHITECTURAL CONTRACT
program-execution.replan.v1
RECOMMENDED NEXT ACTION
<one highest-leverage next action>

Do not declare runtime convergence. Report implementation and verification state only.

⸻

25. Final Success Criterion

This contract is successful when the architecture supports the following without degrading governance:

User:
"Make repository X achieve Y and keep going until verified."
System:
    resolve intent
    → discover authoritative context
    → synthesize program
    → validate Blueprint
    → lock program
    → execute bounded tasks
    → independently verify
    → advance gates
    → return only for a genuine authority boundary or final handoff

The optimization target is:

maximize independently verified useful progress per human intervention while maintaining zero authority widening and no reduction in evidence quality.

Do not optimize merely for number of autonomous agent steps.