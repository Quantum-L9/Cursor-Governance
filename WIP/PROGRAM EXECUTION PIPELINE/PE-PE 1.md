The most important design decision is this: do not compile this as nine independent bug-fix waves. Compile it as a reconstruction of Program Execution around a single end-to-end authority chain:

Immutable operator intent
        ↓
Semantics-preserving compilation
        ↓
Accepted executable program definition
        ↓
Exact repository generation
        ↓
Exact task authorization
        ↓
Immutable submitted candidate
        ↓
Independent verification of that exact candidate
        ↓
Scoped admissible evidence
        ↓
Authorized promotion into next repository generation
        ↓
Evidence-computed gates
        ↓
Exact integrated program candidate
        ↓
Verified rollback state
        ↓
Advisory convergence handoff
        ↓
Authenticated program-owner verdict

Everything we found is basically a break somewhere in that chain.

The pinned source already intends much of this: operator intent is supposed to remain immutable, Blueprint owns accepted program definition, Controller owns mutable runtime state, promotion requires evidence-backed gates, and the Controller must recommend rather than declare the terminal verdict. The source also explicitly requires append-only evidence, exact revision binding, exact human cutover authority, exact candidate revision, independent verification, rollback proof, and final target revisions in the handoff.

What is missing is a runtime model capable of representing and enforcing those laws without collapsing them into mutable strings, mutable paths, caller assertions, or implicit Git state.

⸻

Campaign-level architecture

I would call this a major contract hardening, not a patch release.

The changes touch Campaign→Blueprint semantics, Source Contracts, evidence meaning, repository state, task state, approvals, principals, gates, receipts, closeout, persistence, and migration. Trying to silently change what existing v2 receipt schemas mean would make old artifacts appear stronger than they actually are.

So I recommend:

program-execution-system.v3
program-execution-blueprint.v3
program-execution-controller.v3
with:
v2 → v3 explicit migration/import
v2 receipts remain v2 forever
v2 evidence is not silently promoted to v3 proof

This is especially important because current v2 receipts permit nullable candidate identities, current approval identity is effectively a free-form string, and current handoff semantics differ from the campaign’s intended closeout semantics.

The bootstrap paradox

There is one subtle operational issue the campaign itself must acknowledge.

We are repairing Program Execution using Program Execution.

And the pinned runtime stores template_root and dynamically reads schemas/code from live paths, meaning the interpreter of the campaign can drift while we change the thing being interpreted. The current Controller also has known semantic gaps in its gate, evidence, lease, admission and closeout mechanisms.

So don’t self-modify the live control plane.

Use two planes:

CONTROL PLANE A
pinned immutable v2 checkout
0db3fed...
        │
        │ orchestrates repair campaign
        ▼
TARGET PLANE B
editable Program Execution implementation
        │
        ▼
new v3 implementation

S0 must freeze A.

S8 proves B.

Only a later activation/promotion operation should replace A with B.

This prevents the campaign from changing the semantics of its own execution halfway through the run.

⸻

S0 — Freeze baseline + executable counterexamples

Purpose

S0 converts everything we’ve discovered from conversational audit findings into reproducible executable evidence.

No behavior should be fixed here.

The desired S0 result is:

"We can prove exactly how v2 behaves,
at exactly 0db3fed...,
and every later stage can prove which counterexamples it closes."

Freeze three different things

Freeze the source revision:

baseline_commit:
  0db3fedf697b263a3b8bd9ea8ce40113f999b67d

Freeze the execution interpreter separately:

orchestrator_checkout:
  detached immutable checkout at baseline_commit

And create a baseline manifest over the relevant PE surfaces:

environment/program-execution/core/**
environment/program-execution/scripts/**
environment/program-execution/conformance/**
environment/program-execution/campaigns/**

The campaign should never silently advance that baseline.

Create a Counterexample Registry

Do not make this prose documentation.

Create a machine-readable fixture such as:

schema: program-execution-hardening.counterexamples.v1
counterexamples:
  - id: CE-COMPILER-001
    invariant: retry_policy_is_preserved
    current_outcome: retry_policy_absent_after_compilation
    required_outcome: semantic_equivalence
  - id: CE-CANDIDATE-001
    invariant: verification_identifies_exact_candidate
    current_outcome: dirty_tree_verified_with_HEAD_as_candidate
    required_outcome: immutable_candidate_identity
  - id: CE-EVIDENCE-001
    invariant: evidence_is_claim_scoped
    current_outcome: unrelated_live_evidence_can_satisfy_claim
    required_outcome: reject
  ...

Then every counterexample gets an executable test.

I would initially mark desired-safe assertions as explicit expected failures:

@pytest.mark.xfail(
    strict=True,
    reason="CE-CANDIDATE-001: v2 lacks dirty candidate identity",
)
def test_dirty_submission_has_immutable_candidate_identity():
    ...

That is better than writing tests that assert the vulnerability as correct behavior.

As each stage repairs an invariant, remove its xfail.

S8 exit criterion: zero hardening xfails remain.

Counterexamples S0 must capture

At minimum capture these families:

Family	Counterexample
Compiler	retry/scheduler/evidence/authority/closeout law disappears
Compiler	first_target misbinds workstream/authority/traceability
Provenance	source traceability stores algorithm name instead of source digest
Admission	accepted tree without required acceptance receipt bootstraps
Admission	removing MANIFEST or README bypasses instantiated validation
Candidate	dirty worktree PASS produces HEAD as candidate
Candidate	submitted state changes before verify
Candidate	verified state changes before completion/integration
Repository	wrong repo/branch/SHA reconciles under correct symbolic ID
Repository	reconcile advances baseline while lease uses old generation
Evidence	FAIL evidence can satisfy positive obligation
Evidence	unrelated evidence can satisfy another claim
Evidence	old verification artifact overwritten by retry
Authority	arbitrary approved_by/actor unlocks authority operation
Lease	expired-but-unrecovered lease remains usable
Approval	expired approval after claim remains operational
Gate	caller supplies PASS/method/evidence
Replan	active replan corruption falls back to locked plan
Replan	active task can become affected “future” task
Retry	recovered worktree/branch makes retry non-repeatable
Ledger	tamper detectable but not execution-fencing
Closeout	INCONCLUSIVE produced but rejected as terminal
Closeout	Controller handoff recommendation can drive completion
Closeout	final target revision absent
Closeout	GATE-006/handoff dependency is circular

Current v2 explicitly allows dirty or committed task worktrees and says integration happens later, while the Verification Receipt carries only a nullable candidate_sha. That makes the candidate counterexample particularly important.

S0 gate

GATE-S0-BASELINE-CHARACTERIZED

Pass only when:

baseline commit frozen
orchestrator frozen independently
all counterexamples have IDs
all counterexamples reproduce
all relevant files are digest-manifested
no implementation behavior changed

⸻

S1 — Semantic-conservation contract for compiler/projections

This should be the architectural foundation of the campaign.

The current compiler writes many Blueprint projections directly. It also uses shortcuts such as first_target for authority/workstream/traceability placement and currently sets source traceability revision from digest_algorithm, producing "sha256" rather than the source revision digest. The campaign source, meanwhile, carries richer authority, retry, scheduler, evidence and closeout semantics.

That shape makes semantic drift inevitable.

Stop compiling Source directly into 15 unrelated files

Introduce one canonical intermediate model:

CAMPAIGN_SOURCE
      │
      ▼
SourceSemantics
      │
      ▼
Canonical Semantic Model
      │
      ├────────► PROGRAM.yaml
      ├────────► TASK_CARDS.yaml
      ├────────► AUTHORITY_REGISTRY.yaml
      ├────────► DECISION_REGISTER.yaml
      ├────────► UNKNOWN_REGISTER.yaml
      ├────────► EXECUTION_WAVES.yaml
      ├────────► DEPENDENCY_GRAPH.yaml
      ├────────► ...
      │
      ▼
Program Lock

Call it something like:

PROGRAM_SEMANTICS.yaml

or:

SEMANTIC_MODEL.yaml

inside the accepted Blueprint.

The important property is:

Blueprint projections are derived from SemanticModel.
SemanticModel is NOT reconstructed by guessing
meaning from independently edited projections.

Define semantic conservation

Compilation should not mean:

"output validates against schema"

It should mean:

∀ governing source law L:
representable(L)
AND
meaning(project(L)) == meaning(L)

Anything governing that cannot be represented becomes a compile error, not a warning and not silent omission.

That catches precisely the things we’ve found.

Semantic classes that must survive

The conservation checker should explicitly cover:

target identity
target revision
repository binding
authority type
authority scope
delegability
required authority evidence
decision locks
Unknown blocking
task dependencies
task acceptance claims
writable scope
authorization ceiling
scheduler constraints
retry policy
Source Contract reissue triggers
evidence policy
gate obligations
stop conditions
rollback conditions
cutover preconditions
closeout authority
terminal verdict vocabulary
traceability

Fix type mistakes at this layer

This is where we stop confusing semantic concepts with path strings.

The current campaign’s prohibited_paths entries are actually statements such as “Do not widen authority downstream” and “Do not treat worker completion as independent verification.” Those are semantic laws, not filesystem glob patterns.

v3 should split:

prohibitions:
  - id: ...
    rule: authority_may_only_narrow
filesystem_scope:
  forbidden_paths:
    - environment/foo/**

Similarly, don’t infer writable paths from human-facing task output descriptions.

Current source outputs include values such as:

"IB-Odoo_19/plasticos_gate config diff"

which are artifact descriptions, not filesystem paths.

Add an explicit task field:

execution_scope:
  writable_paths:
    - plasticos_gate/**

outputs remains outputs.

Make validation typed

The current source can say:

method: command
command_or_inspection: "seed ... is 0; ... defaults to false"

which isn’t necessarily an executable shell command.

v3 should have distinct types:

validation:
  - method: command
    command:
      argv: [...]
      cwd: .
      environment_profile: isolated_local
      timeout_seconds: 300

versus:

validation:
  - method: inspection
    inspection:
      assertion: ...

No overloaded command_or_inspection.

Canonicalize blocker relations

Do not maintain:

decision.blocks TASK-X

and:

TASK-X.required_decisions includes decision

as independent authorities.

The semantic model should hold one canonical edge:

- kind: decision_blocks_task
  from: DEC-001
  to: TASK-007

Then derive both human-readable projections.

Same for Unknowns.

Admission becomes receipt-backed

Acceptance should not be inferred from:

PROGRAM.definition_status == accepted

The acceptance receipt itself must become part of the accepted object.

Bootstrap should require:

valid Blueprint manifest
+
valid acceptance receipt
+
acceptance receipt digest matches exact Blueprint
+
accepting principal has required authority

Current bootstrap only conditionally runs the instantiated validator depending on MANIFEST/README presence, which is exactly the kind of conditional fail-open S1 should remove.

Make validation unconditional.

Missing required Blueprint artifacts must mean:

INVALID

not:

validator skipped

Acceptance should be idempotent and crash-safe

Do not mutate definition_status first.

Conceptually:

validate candidate Blueprint
        ↓
construct acceptance receipt
        ↓
construct final manifest
        ↓
validate complete accepted bundle
        ↓
atomically publish accepted bundle

And bootstrap trusts the receipt, not a mutable status bit.

Source integrity becomes real provenance

The source’s integrity section already defines SHA-256 and a receipt location.

Compile should verify that receipt.

Then:

SOURCE_TRACEABILITY:
  source_digest: <actual sha256>
  digest_algorithm: sha256

Never:

revision: sha256

S1 gate

GATE-S1-SEMANTIC-CONSERVATION

Pass when a round-trip test does:

Campaign Source
      ↓
Semantic Model
      ↓
Blueprint projections
      ↓
reconstructed semantics

and proves:

semantic_diff == ∅

for a fixture containing every governing field.

⸻

S2 — Immutable content identity + repository-generation genealogy

This is the missing spine.

Today there is:

repository.head_sha
lease.base_sha
verification.candidate_sha

but no first-class generation graph. The repository row is mutable and reconciliation overwrites head_sha; leases copy that SHA at claim.

The real campaign separately declares an integration branch and permits local commits while forbidding mid-execution push.

Introduce RepositoryGeneration

Stop treating “current repository SHA” as a scalar.

Represent it as an immutable generation:

generation_id: GEN-...
repository_id: Quantum-L9/Cursor-Governance
parent_generation_id: GEN-...
commit_sha: ...
tree_sha: ...
branch: campaign/...
remote_identity: ...
source:
  type: reconcile | promotion | migration
promotion_receipt_id: ...
created_at: ...
program_digest: ...

Database shape:

repository_generations(
    generation_id PRIMARY KEY,
    repository_id,
    parent_generation_id,
    commit_sha,
    tree_sha,
    branch,
    remote_identity,
    source_kind,
    promotion_receipt_id,
    program_digest,
    created_at
)

Then repository runtime state contains only:

current_generation_id

No destructive overwrite of genealogy.

Reconciliation creates a generation

Initial reconcile should prove:

observed remote matches expected target identity
observed branch matches allowed branch
observed revision satisfies expected baseline rule
worktree is clean

Only then:

TargetExpectation → GEN-000

If expected SHA is exact, initial reconciliation must match it exactly.

If policy permits descendants, encode that explicitly rather than silently accepting any HEAD.

Leases bind to generations

Replace:

lease.base_sha

as the primary authority coordinate with:

lease.base_generation_id

The SHA remains available, but generation identity is authoritative.

Now a task means:

TASK-X is authorized against GEN-004

not merely:

TASK-X happens to mention SHA abc123.

Create immutable candidate snapshots

This is the key solution to dirty-worktree identity.

At submission, Controller freezes exact candidate content.

For a dirty worktree, one robust Git technique is:

temporary index
    ↓
read base tree
    ↓
add exact worktree state into temporary index
    ↓
git write-tree
    ↓
create synthetic snapshot commit with git commit-tree

No branch movement is required.

The resulting object gives dirty content an immutable Git identity.

Conceptually:

candidate_id: CAND-...
task_id: TASK-X
attempt: 1
base_generation_id: GEN-004
snapshot:
  tree_sha: ...
  snapshot_commit_sha: ...
  working_tree_was_dirty: true
declared_paths_digest: ...
observed_paths_digest: ...
created_at: ...

Pin it under an internal ref so Git GC cannot discard it.

For example conceptually:

refs/pec/candidates/<task>/<attempt>

Now:

dirty content

has an exact immutable identifier without forcing the worker to create a human-facing task commit.

Verification must verify the snapshot

Do not verify the worker’s mutable worktree.

Submission freezes S.

Then Controller verifies S in a fresh verifier checkout/worktree:

worker worktree
      │ submit
      ▼
immutable snapshot S
      │
      ▼
fresh verifier environment
      │
      ▼
verified snapshot V

And enforce:

S == V

by construction.

That eliminates the submit→verify TOCTOU.

Add promotion

Repo-local task success should no longer mean merely:

PASSED_LOCAL

Add an explicit state:

PASSED_LOCAL
    ↓
PROMOTED
    ↓
COMPLETED

A Promotion Receipt states:

promotion_id: PROM-...
task_id: TASK-X
candidate_id: CAND-...
from_generation_id: GEN-004
to_generation_id: GEN-005
strategy: fast_forward
integration_branch: ...
result_commit_sha: ...
result_tree_sha: ...

For the first implementation, I would deliberately keep repository genealogy linear:

GEN0 → GEN1 → GEN2 → GEN3

because the PE campaign itself already uses one writer per repository.

Do not solve arbitrary N-way distributed merge composition in this campaign.

Successors inherit promoted generations

Readiness for TASK-B must mean not only:

TASK-A COMPLETED

but:

TASK-A promotion is an ancestor of TASK-B.base_generation

That closes the “dependency order without state inheritance” hole.

Reconciliation cannot race active leases

Normal reconcile should refuse to advance:

repository.current_generation_id

while a lease against that repository is live.

An exceptional recovery reconcile must explicitly supersede stale leases and record the relationship.

Source Contracts bind to baseline generation

The source campaign already requires a new Source Contract when the base revision changes.

Make that enforceable:

source_contract_id: SC-...
task_id: TASK-X
base_generation_id: GEN-004
plan_revision: PLAN-...
authority_grant_ids: [...]
...

Then:

GEN-004 → GEN-005

automatically invalidates a Source Contract bound to GEN-004 where campaign policy says reissue is required.

S2 gate

GATE-S2-EXACT-LINEAGE

Must prove:

TargetExpectation
 → BaselineGeneration
 → SubmittedCandidate
 → VerifiedCandidate
 → Promotion
 → SuccessorGeneration

for both:

committed candidate
dirty candidate

with immutable identities at every edge.

⸻

S3 — Evidence/proof algebra + immutable artifacts

Current _evidence_valid() effectively asks whether evidence exists, is not in a few stale statuses and has not expired. It does not establish that the evidence proves the claim consuming it.

Current persistence also uses replacement semantics for evidence:

INSERT OR REPLACE INTO evidence

and similarly for waivers.

That must change fundamentally.

Separate requirement from artifact

Today a logical ID such as EVID-002 is being asked to serve two roles.

Separate them.

EvidenceRequirement

Program definition:

requirement_id: EREQ-002
claim_type: repository_fact
subject:
  target_id: TARGET-001
required_types:
  - repository_inspection
required_result: supports
revision_binding: exact
producer_authority: AUTH-...
freshness_policy: collect_at_admission

EvidenceArtifact

Runtime immutable fact:

evidence_artifact_id: EV-7db...
requirement_id: EREQ-002
subject:
  target_id: TARGET-001
content_identity:
  generation_id: GEN-004
result: PASS
collection:
  method: repository_inspection
  environment_digest: ...
  producer_principal_id: PRINCIPAL-...
  collected_at: ...
payload_digest: ...
receipt_path: ...

A logical requirement can have multiple artifacts over time.

Artifacts never change.

Introduce evidence admissibility

Replace:

_evidence_valid(db, id)

with something conceptually like:

admit_evidence(
    artifact,
    requirement,
    claim,
    now,
    authority_context,
)

The test is:

integrity valid
AND artifact subject matches claim
AND content identity matches claim
AND evidence class matches requirement
AND result polarity satisfies requirement
AND collection method matches
AND producer authority is valid
AND freshness semantics are satisfied
AND artifact has not been revoked for integrity

This eliminates cross-claim substitution.

Result polarity matters

A failed test is useful evidence.

It just isn’t evidence of success.

So:

FAIL test

may satisfy:

"prove the negative path currently fails"

but cannot satisfy:

"prove completion gate passes"

Evidence validity and evidence admissibility are different concepts.

Make freshness typed

Not all evidence should expire the same way.

Use categories such as:

immutable_historical
current_observation
time_bounded_authorization_support
locked_decision_input
remote_state_observation

Then derived facts know how revocation propagates.

Example:

Verification of immutable CAND-001

should remain historically true forever unless integrity is invalidated.

But:

"remote system is healthy now"

may have a 15-minute freshness window.

Similarly:

approval
lease

are authorizations, not historical facts, and must expire.

Acceptance becomes executable proof

Task acceptance currently carries useful statements and required evidence types in source.

Compile each into a formal runtime claim:

acceptance_claim_id: AC-003
task_id: TASK-002
statement: ...
required_evidence_types:
  - test_result
  - diff
content_binding: task_promoted_candidate

complete_task() may proceed only when every acceptance claim has admissible evidence.

No more “acceptance metadata was transported, therefore completion is okay.”

Make authority artifacts immutable too

These should also become append-only:

evidence
approvals
waivers
gate evaluations
decision resolutions
Unknown resolutions
Source Contracts
Rendered Contracts
verification receipts
handoffs

Don’t overwrite historical files.

Use paths such as:

receipts/verification/TASK-002/attempt-001/VER-7ad....json
contracts/source/TASK-002/SC-a813....json
contracts/rendered/TASK-002/RC-b622....json

A human convenience projection may exist:

runtime/projection/latest-verification-TASK-002.json

but that file is explicitly non-authoritative.

Current evidence policy already says attempts and verification receipts are to be preserved and the ledger is append-only.

S3 gate

GATE-S3-PROOF-ADMISSIBILITY

Must demonstrate:

unrelated evidence → rejected
FAIL evidence for positive claim → rejected
wrong candidate evidence → rejected
wrong target evidence → rejected
expired temporal evidence → rejected
historical immutable proof → remains historically valid
replacement of evidence ID → impossible
old retry artifacts → still retrievable and digest-valid

⸻

S4 — Principal binding + authority/revocation model

This fixes the distinction between:

"the receipt says Igor/operator/verifier"

and:

"the control plane established this principal had authority."

Current approval schema accepts approved_by as any nonempty string, and Controller records it as ledger actor.

Meanwhile the Campaign Source has actual authority semantics such as human_owner, whole_program, may_delegate: false, and required evidence.

Preserve authority faithfully from S1

Runtime must have actual authority records:

authority_id: AUTH-001
responsibility: program_terminal_verdict
authority_type: human_owner
scope:
  - whole_program
may_delegate: false
required_evidence:
  - controller_handoff_receipt

Don’t reduce that to generic:

allowed_roles: authority

Introduce PrincipalContext

No privileged Controller function should receive authorization from:

actor: str

alone.

Instead:

principal_context:
  principal_id: PRINCIPAL-...
  principal_type: human | controller | worker | skill | adapter
  provenance:
    entrypoint: ...
    invocation_id: ...
  authority_grant_ids:
    - GRANT-...

actor may remain as display metadata.

It is never authority.

Be precise about authentication

Don’t pretend the local CLI cryptographically authenticates a human if it doesn’t.

The architecture should support different assurance levels:

attested_local_operator
authenticated_platform_identity
controller_service_identity
lease_bound_worker_identity
authorized_skill_invocation

Then policies can require a minimum assurance.

That is much stronger than fabricating certainty.

Grants are immutable

grant_id: GRANT-...
authority_id: AUTH-001
principal_id: PRINCIPAL-...
actions:
  - terminal_verdict
scope:
  program_id: ...
issued_at: ...
expires_at: ...
delegation_parent: null

If:

may_delegate: false

no delegation chain is accepted.

Revocation is a new immutable event, not mutation of the original grant.

Worker authority comes from the lease

The worker principal should be:

worker principal
    +
lease ID
    +
fencing token

No lease = no worker authority.

Controller/verifier authority is separate

Verification should carry:

principal_type: controller_verifier

and cannot impersonate task worker or program owner.

Decisions become revisions, not mutable status bits

Current decisions can change status with no meaningful transition semantics.

Instead:

DEC-001 definition
       │
       ├── resolution revision R1
       │      selected OPTION-B
       │      evidence...
       │      AUTH-001
       │
       └── supersession R2

The current accepted projection is derived.

A source-locked decision cannot simply be flipped to pending/rejected by generic runtime mutation.

Same architecture for Unknowns.

T4/destructive approvals become exact capability grants

Approval must bind:

principal
authority
program digest
task
target
repository generation
candidate if relevant
permitted capability
required recovery evidence
expiry

And remain immutable.

S4 gate

GATE-S4-AUTHORITY-BOUND

Pass when:

spoofed actor string cannot authorize
nondelegable authority cannot be delegated
wrong authority scope cannot approve
expired grant cannot authorize
T4 approval without required recovery evidence fails
worker without valid lease/fence fails
controller cannot act as program owner

⸻

S5 — Transaction/fencing/hard-stop runtime semantics

Only now do we have enough semantic clarity to choose transaction boundaries.

The current state layer commits individual operations independently, including repository updates, task updates, gates, evidence, leases and attempts. Leases use an active bit and active_lease_for_task() does not incorporate expiry. Attempt numbering is also separate from insertion.

Introduce a Unit of Work

One logical operation gets one DB transaction.

For example claim:

BEGIN IMMEDIATE
evaluate hard stops
evaluate readiness
expire/revoke stale lease state
check generation
allocate fencing token
create lease
transition task
append canonical runtime event
COMMIT

Not:

create lease COMMIT
update task COMMIT
transition COMMIT
ledger append

Put canonical events inside the DB transaction

I would now make the transactional event table canonical:

runtime_events(
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    operation_id TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    principal_id TEXT,
    previous_state_version INTEGER,
    new_state_version INTEGER,
    payload_json TEXT NOT NULL,
    previous_digest TEXT,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL
);

Prevent mutation:

CREATE TRIGGER no_event_update ...
CREATE TRIGGER no_event_delete ...

JSONL becomes a projection/export of this canonical event chain.

That removes the dual-commit problem while retaining the audit-friendly ledger file.

Safe artifact commit ordering

For immutable receipts:

1. serialize artifact
2. write temp file
3. fsync temp
4. atomic rename to immutable final path
5. fsync parent dir
6. BEGIN DB transaction
7. register artifact digest/path
8. mutate state
9. append event
10. COMMIT

Crash after 4 but before 10:

orphan immutable artifact

Safe and garbage-collectable.

Crash after 10:

DB always references an already durable artifact

Version state and use compare-and-swap

Every mutable aggregate:

task
repository current-generation pointer
gate projection
campaign state

gets:

state_version

Transitions use:

UPDATE tasks
SET state=?, state_version=state_version+1
WHERE id=?
  AND state=?
  AND state_version=?;

rowcount != 1 means concurrency conflict.

Add idempotency keys

Every authority-bearing command gets:

operation_id

A retry after network/process failure either:

returns the previously committed result

or:

performs the operation exactly once

No duplicate approvals/attempt allocations/promotions.

Lease fencing

Each repository/resource gets a monotonically increasing fence:

fence 41
fence 42
fence 43

Lease:

lease_id: ...
fencing_token: 43
base_generation_id: GEN-005
expires_at: ...

Every worker-originated mutation must carry 43.

Worker holding 42 is permanently stale even if it wakes up later.

Expiry is enforced at use time

The stop policy already treats lease expiry and expired/mismatched approval as hard stops.

Therefore every relevant boundary checks temporal authority:

prepare
render
start
submit
verify
promote
complete

Not just claim/recovery.

Same for approvals.

Centralize hard-stop evaluation

Create one conceptual function:

SafetyKernel.evaluate(operation_context)

It checks as applicable:

Program Lock valid
semantic model valid
ledger valid
global halt
generation current
lease current
fence current
approval current
principal authority current
replan current
required stop conditions

Don’t scatter partial checks across twenty functions.

Define halt semantics

I recommend:

global halt blocks:
  new execution
  new authority grants
  verification that could confer PASS
  promotion
  completion
  closeout
global halt permits:
  read-only inspection
  status
  diagnostics
  evidence preservation
  recovery/quarantine

Submission arriving during halt may be preserved as quarantined evidence, but must not advance success state.

Ledger failure fences immediately

Current stop policy explicitly names ledger integrity failure as hard safety.

So:

ledger invalid
      ↓
SafetyKernel = HARD_STOP
      ↓
no claim/start/verify/promote/complete/close

S5 gate

GATE-S5-LINEARIZABLE-RUNTIME

Run a deterministic crash/fault matrix at every side-effect boundary plus concurrency tests:

two claims
two state transitions
two attempt submissions
lease expiration while worker is running
approval expiration while worker is running
global halt during execution
process death after artifact write
process death before event commit
process death after event commit
ledger corruption before claim
reconcile while lease active

All resulting states must be either:

committed

or:

detectably recoverable

Never ambiguous.

⸻

S6 — Gate + replan + retry + integration semantics

This is where the lifecycle begins using the stronger primitives.

Gates compute results

Current evaluate_gate() accepts a caller-provided result, method, and evidence IDs after checking those IDs are broadly valid.

Invert that API.

Caller should request:

evaluate GATE-X

The Controller determines:

method
required proof
result

from the gate definition.

Conceptually:

evaluation = gate_engine.evaluate(
    gate_definition,
    program_state,
    evidence_store,
    principal_context,
)

No caller-supplied PASS.

Gate methods must be typed

Examples:

schema_validation
validation_result
evidence_set
repository_state
manual_attestation
composite_all
composite_any

For machine-executable methods, Controller computes the result.

For inherently human criteria:

manual_attestation

requires evidence from the declared authority.

That is much safer than pretending arbitrary prose has executable semantics.

Validation commands get a constrained adapter

The verifier currently runs:

bash -lc <command>

with nearly the inherited process environment.

Don’t let Source Contracts inject unrestricted shell behavior into an independent verifier.

v3 command validation should use a typed command specification and a controlled environment:

explicit argv
explicit working directory
explicit timeout
minimal allowlisted environment
no inherited credential environment
no Git prompts
explicit network capability
explicit write capability

Ideally verification executes against the immutable candidate snapshot in an isolated verifier worktree, not the worker worktree.

And after validation:

candidate tree identity must remain the frozen candidate identity

Fix path semantics here

Define one path grammar:

*   = one path segment only
**  = recursive segments

Reject:

absolute paths
..
empty/root widening
ambiguous normalization

Use one matcher everywhere.

Then specifically test Git rename/copy porcelain cases:

allowed/a.py → forbidden/a.py

must be evaluated against the destination, not lost or replaced with the source path.

Replan becomes generation-aware

Replan activation may affect only tasks that have not crossed an authorization boundary.

A clean rule would be:

May directly affect:
BLOCKED
ELIGIBLE
FAILED
STALE
May not silently affect:
LEASED
PREPARED
CONTRACTED
EXECUTING
SUBMITTED
VERIFYING
PASSED_LOCAL
PROMOTED
COMPLETED

If an in-flight task must be affected:

explicit revoke/cancel
preserve evidence
release/fence lease
issue new plan revision
issue new Source Contract

And if an active plan revision is missing/corrupt:

HARD STOP

never fallback to the locked plan.

Contracts bind plan revision

Every Source and Rendered Contract gets:

semantic_model_digest
plan_revision
base_generation_id
authority_grant_digest

Verification rechecks those coordinates.

Retry policy becomes executable

The source already has exactly the kind of policy needed: max_attempts: 2, retryable and non-retryable classifications, preserve-every-attempt, and Source Contract renewal triggers.

Preserve that through S1 and enforce it now.

Failure produces:

failure:
  class: temporary_adapter_failure
  retryability: retryable

Then:

attempts < max_attempts
AND failure class retryable
AND no hard safety stop

allows retry.

A scope violation must never be silently retried as though it were a transient process crash.

Controller owns retry cleanup

Remove the manual runbook instruction requiring the operator to manually delete the worktree and branch.

Controller should:

preserve recovery artifact
remove Git worktree correctly
prune Git worktree registration
delete/recreate task branch as appropriate
release old fence
allocate new attempt
issue new baseline-bound contract if required

The current runbook explicitly requires manual worktree/branch cleanup on retry, demonstrating that this lifecycle is not currently closed by Controller.

Operationalize promotion

S2 created the lineage model.

S6 actually wires it into scheduling:

verify exact candidate
      ↓
PASSED_LOCAL
      ↓
promotion into current integration generation
      ↓
PROMOTED
      ↓
completion gate evaluation
      ↓
COMPLETED
      ↓
next task bases on new generation

For repo-local mutation tasks:

COMPLETED must imply PROMOTED

This is the key semantic change.

A completed task now means:

Its accepted, independently verified candidate is actually part of the program’s current integrated state.

Not merely:

Some isolated task worktree once passed tests.

Scheduler limits become runtime laws

The source explicitly carries worker limits and one-writer semantics.

S6 consumes them.

No more relying on repository uniqueness to accidentally approximate scheduler policy.

S6 gate

GATE-S6-EXECUTION-SEMANTICS

Prove:

caller cannot force gate PASS
wrong gate method cannot be substituted
validation cannot mutate/escape candidate scope
replan cannot silently change in-flight task
corrupt active plan fails closed
retryable failure retries within max
nonretryable failure does not
retry artifacts remain immutable
retry cleanup is automatic
predecessor promoted state is inherited by successor
scheduler max-workers enforced

⸻

S7 — Handoff/convergence/rollback/terminal-owner model

This stage fixes the final authority boundary.

The current source says the Controller may not declare terminal verdict and assigns that authority to AUTH-001. It also requires final target revisions, PR/merge identifiers, gate evaluations, risks/Unknowns/waivers and rollback state in the handoff.

Current Controller handoff instead computes a recommendation from task/gate state and its schema does not require that complete final-revision lineage. It does include INCONCLUSIVE, while Controller’s terminal-verdict set omits it.

First settle INCONCLUSIVE

Make it a legitimate terminal program outcome.

Semantics:

INCONCLUSIVE =
execution terminated without enough evidence
to claim convergence or non-convergence safely

It is terminal in the campaign-lifecycle sense:

we stop this program execution

but not a success/failure claim.

So:

CONVERGED
CONVERGED_WITH_NON_BLOCKING_RISKS
NOT_CONVERGED
INCONCLUSIVE

all terminalize execution.

Split handoff into two phases

This solves GATE-006’s closeout cycle.

Provisional Convergence Report

Controller emits:

CONVERGENCE_REPORT

before final task completion.

It contains:

exact current program candidate
task results
gate results
evidence inventory
risks
Unknowns
waivers
rollback proof
ledger root
recommended verdict

This is admissible evidence for the closeout/convergence gate.

Then:

GATE-006 evaluates provisional report

TASK-007 may complete.

Final Handoff Receipt

After all task/gate accounting is final:

FINAL_HANDOFF

contains final immutable state.

The final handoff is still advisory.

It does not complete the campaign.

Owner verdict is a separate receipt

program_verdict_receipt:
  verdict_id: ...
  handoff_digest: ...
  final_program_candidate_id: ...
  verdict: CONVERGED_WITH_NON_BLOCKING_RISKS
  authority_id: AUTH-001
  principal_assertion_id: ...
  decided_at: ...

Then:

complete_campaign()

accepts a verdict receipt, not:

--actor "whatever" --verdict CONVERGED

complete_campaign recomputes invariants

It should verify:

verdict authority valid
handoff exact
final generations exact
ledger valid
rollback proof current
required gates satisfied
program lock valid
no unresolved hard safety stop
verdict is allowed by Program semantics
handoff digest matches owner decision

It must never blindly trust the caller’s claimed terminal verdict.

Final handoff must include lineage

Required fields should include:

campaign_source_digest: ...
blueprint_digest: ...
semantic_model_digest: ...
program_lock_digest: ...
final_targets:
  - target_id: TARGET-001
    repository_id: ...
    generation_id: GEN-...
    commit_sha: ...
    tree_sha: ...
    remote_identity: ...
    integration_branch: ...
task_outcomes:
  - task_id: ...
    candidate_id: ...
    verification_id: ...
    promotion_id: ...
gate_evaluations: [...]
decisions: [...]
unknowns: [...]
waivers: [...]
residual_risks: [...]
rollback_proof:
  evidence_artifact_id: ...
  candidate_generation_id: ...
ledger:
  final_sequence: ...
  root_digest: ...
recommended_program_verdict: ...

Rollback proof must be observed

Don’t write:

worktree_isolation = true

and call that rollback state.

Rollback evidence must be an actual proof object bound to:

exact final generation

For example:

known pre-campaign generation
+
reversal strategy
+
tested restoration procedure
+
evidence

Whether rollback is “reset integration branch locally”, “reverse commits”, or another strategy is campaign-specific.

The important property is:

rollback proof candidate == terminal candidate

Controller cannot auto-terminalize

The pinned runbook itself says the handoff recommends a verdict but never declares it authoritative.

Encode that in runtime rather than comments.

S7 gate

GATE-S7-OWNER-CLOSEOUT

Must prove:

Controller cannot close program alone
spoofed owner cannot close
handoff recommendation does not alter campaign status
INCONCLUSIVE terminalizes correctly
final handoff contains exact generations
broken ledger blocks closeout
stale rollback proof blocks closeout
wrong-candidate rollback proof blocks closeout
owner decision bound to different handoff fails
GATE-006 no longer has circular dependency

⸻

S8 — Cross-layer adversarial conformance + migration

S8 proves that v3 is a system rather than a collection of locally correct subsystems.

Do not mutate v2 historical artifacts into v3

Migration should be:

read v2
      ↓
produce new v3 runtime

not:

rewrite v2 in place

Particularly:

v2 evidence
v2 approval
v2 verification
v2 handoff

cannot automatically become stronger v3 proof.

Import them as:

provenance_class: legacy_v2
v3_admissibility: requires_reverification

where appropriate.

Migration creates a new runtime

Something conceptually like:

pec-v3 migrate \
   --from old-runtime \
   --to new-runtime

The old runtime remains preserved.

Migration emits:

MIGRATION_RECEIPT

containing:

source runtime digest
source Program Lock
source DB hash
source ledger root
mapping decisions
unmigrated artifacts
reverification obligations
target v3 runtime digest

Full vertical conformance fixture

Build one synthetic campaign containing every important semantic feature:

multiple targets
nondelegable authority
decision blocker
Unknown blocker
T4 approval
expiring evidence
retryable failure
nonretryable failure
dirty candidate
committed candidate
replan
promotion
gate
waiver
rollback
residual risk
INCONCLUSIVE path
successful convergence path

Run:

Campaign Source
 → compile
 → accept
 → Program Lock
 → reconcile
 → contract
 → claim
 → submit
 → verify
 → promote
 → retry/replan
 → gate
 → provisional handoff
 → final handoff
 → owner verdict

This is the cross-layer test the current system lacks.

Add fault injection

Kill the process at every transactional boundary:

artifact persisted
transaction begun
lease allocated
task transitioned
event inserted
attempt allocated
verification recorded
promotion recorded
gate evaluated
handoff stored

Restart must always produce:

one deterministic state

Add property/concurrency testing

Especially for:

one active fence per conflicting resource
one task state winner per version
one attempt number per task
append-only evidence
append-only events
monotonic generations
no successor from stale generation
no gate PASS without complete proof
no terminal verdict without owner authority

Shadow self-hosting

Finally instantiate the new Controller from a clean checkout and have v3 execute a small, non-destructive Program Execution campaign against a fixture repository.

Do not make v3’s first real production act be upgrading itself.

Sequence:

v2 orchestrator
     ↓
build + prove v3
     ↓
v3 shadow execution
     ↓
v3 self-host fixture
     ↓
GATE-S8
     ↓
separate activation campaign

S8 gate

GATE-S8-V3-CONFORMANCE

Pass only when:

zero hardening xfails
all v2 counterexamples blocked
semantic conservation = 100%
fault matrix passes
concurrency tests pass
migration is repeatable
legacy evidence cannot privilege-escalate
shadow campaign converges
self-host fixture converges
docs/runbook/schema agree with implementation

⸻

Concrete task decomposition for the Campaign Source

I would turn your nine stages into nine sequential waves, but use multiple tasks inside each wave so responsibilities remain small enough to verify independently.

Wave	Task	Objective	Main dependency
S0	T000	Freeze exact baseline/orchestrator	—
S0	T001	Create counterexample registry + failing-safe tests	T000
S0	T002	Produce baseline integrity/evidence report	T001
S1	T101	Define v3 Canonical Semantic Model/schema	S0
S1	T102	Refactor compiler through semantic IR	T101
S1	T103	Add semantic-conservation validator	T102
S1	T104	Harden source integrity + Blueprint acceptance	T102
S1	T105	Normalize blockers/types/target/authority projections	T102
S2	T201	Implement repository generations	S1
S2	T202	Implement immutable candidate snapshots	T201
S2	T203	Implement promotion receipts and generation advance	T202
S2	T204	Bind reconcile/lease/contracts to generations	T203
S3	T301	Split evidence requirements from artifacts	S2
S3	T302	Implement claim-scoped admissibility engine	T301
S3	T303	Make receipts/contracts/evidence append-only	T301
S3	T304	Enforce acceptance claims as proof obligations	T302
S4	T401	Preserve/import executable authority registry	S1
S4	T402	Add principal contexts and immutable grants	T401
S4	T403	Rebuild approvals/decisions/Unknowns around authority	T402
S5	T501	Add transactional Unit of Work + canonical event table	S2-S4
S5	T502	Add CAS versions/idempotency	T501
S5	T503	Add lease fencing + temporal revocation	T502
S5	T504	Centralize hard-stop evaluator	T503
S5	T505	Crash/concurrency recovery suite	T501-T504
S6	T601	Build executable gate/evidence evaluator	S3-S5
S6	T602	Harden validation adapter + path semantics	T601
S6	T603	Make replan generation/contract-aware	S2/S4/S5
S6	T604	Make retry policy executable + automatic cleanup	S2/S5
S6	T605	Wire promotion into scheduler/task completion	T203/S5
S7	T701	Introduce provisional convergence report	S6
S7	T702	Define final handoff v3 with lineage/rollback	T701
S7	T703	Add owner verdict receipt + principal enforcement	S4/T702
S7	T704	Fix INCONCLUSIVE + terminal state semantics	T703
S8	T801	Implement v2→v3 migration	S7
S8	T802	Run full adversarial vertical conformance	T801
S8	T803	Run shadow/self-host fixture	T802
S8	T804	Final documentation/spec/runtime parity audit	T803

That is large enough to be comprehensive, but each task has a single proofable responsibility.

⸻

The canonical invariant registry

I would put an invariant registry at the heart of the campaign and make every task reference one or more of these IDs.

INV-SEM-001
Every governing source law has exactly one canonical executable representation.
INV-SEM-002
Projections may duplicate presentation, never semantic authority.
INV-ID-001
Every verified candidate has an immutable content identity.
INV-ID-002
Submitted, verified, promoted and terminal content are either identical
or linked by an explicit evidence-backed transformation.
INV-GEN-001
Repository generations form a complete immutable genealogy.
INV-GEN-002
A successor task cannot execute against a generation that excludes
required predecessor promotions.
INV-EVID-001
Evidence artifacts are immutable.
INV-EVID-002
Evidence is admissible only for the exact claim, subject and content
identity it proves.
INV-EVID-003
Evidence polarity, collection method, producer and freshness are semantic.
INV-AUTH-001
Actor labels never confer authority.
INV-AUTH-002
Every privileged transition names an authorized principal and grant.
INV-AUTH-003
Nondelegable authority cannot be projected or impersonated.
INV-TXN-001
Every authoritative runtime transition is atomic with its canonical event.
INV-TXN-002
Retries of an operation are idempotent.
INV-LEASE-001
Expired or superseded leases lose authority immediately at use boundaries.
INV-LEASE-002
A stale worker can never commit state after a newer fencing token exists.
INV-STOP-001
Every declared hard-safety condition is evaluated before every
authority-bearing transition.
INV-GATE-001
Gate results are computed from the gate definition and admissible evidence,
never accepted from caller assertion.
INV-REPLAN-001
A plan revision cannot silently change authorization already issued to
in-flight work.
INV-RETRY-001
Retries obey the accepted retry taxonomy and attempt ceiling.
INV-PROM-001
Repo-local completion means exact verified candidate has been promoted
into the program generation.
INV-HANDOFF-001
Handoff identifies exact final target generations.
INV-HANDOFF-002
Rollback proof is observed and bound to the final candidate.
INV-TERM-001
Controller may recommend but never exercise program-owner terminal authority.
INV-TERM-002
INCONCLUSIVE is a legitimate terminal execution outcome.
INV-MIG-001
Legacy v2 artifacts never silently acquire stronger v3 proof semantics.

This registry is what prevents the campaign from degenerating back into local patches.

⸻

What the repair campaign itself should not depend on

Because it’s repairing the control plane, give this campaign an unusually narrow execution envelope.

I would set the campaign’s own operational law to:

one worker maximum
one writer per repository
local mutation only
local commits allowed if useful
no push during execution
no PR/merge/publish/deploy from Controller
no destructive runtime migration until S8
no reliance on automatic retry before S6
no reliance on v2 gate PASS for safety
no switching orchestrator implementation mid-campaign

That mirrors the conservative campaign binding style already present in the repo, where one writer is required and merge is disabled.

The campaign should end at:

v3 implementation green
+
cross-layer conformance green
+
migration green
+
shadow self-host green
+
activation-ready

not at “v3 has automatically replaced v2.”

Activation deserves its own small follow-on campaign.

⸻

The deepest design rule

If I had to put one sentence at the top of the Campaign Source, it would be this:

No authority-bearing program transition may depend on a semantic fact that lacks one immutable identity, one canonical meaning, one authorized principal, and one executable proof path.

And the companion rule:

A projection may summarize authority, evidence, state, or intent, but a projection must never become an independent source of any of them.

Those two rules unify almost everything we found.

The current system already has many excellent pieces—Program Lock, Source/Rendered Contracts, independent verification, append-only intent, gates, leases, decisions, Unknowns, approvals and handoffs. The problem isn’t that the architecture lacks concepts. The problem is that their identities and meanings weaken as they cross boundaries: source semantics become approximate projections; revisions become mutable HEAD pointers; evidence becomes a globally reusable ID; authority becomes an actor string; a gate definition becomes caller-supplied PASS; verification becomes a moment in a mutable worktree; task completion becomes disconnected from integration; handoff becomes disconnected from the final repository generation.

This campaign makes those concepts composable.

And that is the real fix:

semantic conservation
        +
immutable identity
        +
proof admissibility
        +
principal authority
        +
linearizable state
        +
generation-aware execution
        +
owner-bound convergence
        =
Program Execution whose receipts actually mean
what the architecture says they mean
