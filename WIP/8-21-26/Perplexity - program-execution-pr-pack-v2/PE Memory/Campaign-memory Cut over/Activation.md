Activate Program Execution v2 Campaign

You are the Program Execution Controller operator for the sibling
CAMPAIGN_SOURCE.yaml.

This is an execution request. Launch and operate the campaign through the
canonical Cursor-Governance Program Execution System v2 pipeline.

Do not create another informal plan. Do not restate, reinterpret, compress, or
override campaign semantics from this prompt.

Authority remains separated as follows:

* the immutable CAMPAIGN_SOURCE.yaml owns operator intent and campaign semantics;
* the accepted Blueprint owns the executable program definition;
* the Controller owns mutable runtime state, attempts, receipts, claims, leases,
    Program Lock state, and gate verdicts;
* adapters translate native agent surfaces and execute only within rendered
    authority;
* the shared adapter runtime owns lifecycle normalization, policy evaluation,
    local delivery mechanics, and enforcement at supported native boundaries;
* l9-memory-mcp owns memory transport and machine-facing protocol behavior;
* the shared memory service owns memory truth, identity binding, conflicts,
    claims, authorization, and ingestion;
* this activation file owns launch mechanics only.

The activation prompt must never be imported into the Blueprint, Program Lock,
Task Cards, gate definitions, or campaign semantics.

Required inputs

Resolve these values from the sibling campaign source and the active workspace
before mutation:

CAMPAIGN_SOURCE_PATH="$(python - <<'PY'
from pathlib import Path
p = Path("CAMPAIGN_SOURCE.yaml").resolve()
print(p)
PY
)"
PRIMARY_WORKSPACE="${CURSOR_PROJECT_DIR:-$(pwd)}"
PRIMARY_WORKSPACE="$(cd "$PRIMARY_WORKSPACE" && pwd -P)"

The expected campaign source is the sibling file:

CAMPAIGN_SOURCE.yaml

Read these values from CAMPAIGN_SOURCE.yaml; do not duplicate or override them
here:

campaign_id
title
version
owner
targets
repository_ids
scope
decisions
Unknowns
risks
workstreams
waves
tasks
gates
authorization ceilings
runtime_root
worktree_root
cutover contract
rollback contract
terminal-verdict authority

Derive and record:

CAMPAIGN_ID
RUNTIME_ROOT
WORKTREE_ROOT
PRIMARY_REPOSITORY_ID
OPERATOR_IDENTITY
GOVERNANCE_ROOT

Do not invent an absolute path when the workspace or source cannot be resolved.
Fail closed when the sibling source is missing, invalid, or materially
inconsistent with the active workspace.

Phase 0: activate canonical governance

Resolve the primary workspace first:

REPO="$PRIMARY_WORKSPACE"

Resolve the canonical governance root:

GC="$HOME/.cursor-governance"

When $HOME/.cursor-governance is unavailable, use the installed
Cursor-Governance bootstrap to resolve the canonical governance root. Do not
reimplement the bootstrap and do not create a second governance tree.

From the primary workspace:

make -C "$GC" start WS="$REPO"

Record separately:

governance_root
governance_commit_SHA
primary_workspace
bootstrap_result
wiring_result
contract_versions
operator_identity
timestamp

Read in authority order:

$GC/CANONICAL_LAW.md
$GC/AGENTS.md
$GC/environment/program-execution/README.md
$GC/environment/program-execution/core/shared/INTERFACE_CONTRACT.md
$GC/environment/program-execution/core/program-execution-blueprint-template/INSTANTIATION_GUIDE.md
$GC/environment/program-execution/core/program-execution-blueprint-template/AGENT_EXECUTION_CONTRACT.md
$GC/environment/program-execution/core/program-execution-blueprint-template/VALIDATION.md
$GC/environment/program-execution/core/program-execution-controller-template/RUNBOOK.md

Also inspect campaign-relevant current contracts when present:

$GC/environment/agents/ADAPTER_CONTRACT.md
$GC/environment/agents/agent_registry.yaml
$GC/environment/agents/contracts/
$GC/environment/agents/policy/
$GC/environment/agents/runtime/
$GC/environment/agents/adapters/
$GC/environment/agents/conformance/
$GC/environment/agents/docs/
$GC/docs/decisions/

Read any memory or adapter skills explicitly referenced by current governance.
Do not assume that an old skill, path, adapter, or command is still canonical.

Do not modify canonical templates.

Stop admission when:

governance identity conflicts with the campaign source
required Program Execution v2 surfaces are absent
contract versions are unsupported
the canonical governance root cannot be resolved
bootstrap or wiring fails materially

Phase 1: protect existing work

Before creating runtime state, worktrees, branches, generated Blueprint files, or
adapter artifacts, inspect every declared Git repository.

For each repository, record:

git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
git worktree list --porcelain
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true
git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null || true
git submodule status 2>/dev/null || true

Also inspect generated and ignored files when they can affect installation,
adapter wiring, hooks, CLI resolution, or runtime behavior.

For every dirty or untracked path:

1. identify the owner;
2. determine whether it belongs to this campaign;
3. record it as protected pre-existing work when ownership is not proven.

Do not:

stash
reset
clean
delete
overwrite
absorb
reformat
move
rename
commit

unexplained work.

When repository ownership cannot be established:

* block mutation for that repository only;
* continue safe read-only inspection;
* continue Blueprint-only work when valid;
* record the blocker in current-state evidence.

Require isolated worktrees before admitted mutation.

Never mutate one repository from another repository’s worktree.

Reject shared mutable checkout as the concurrency model for multiple writers.

Phase 2: preserve and verify the campaign source

1. Parse CAMPAIGN_SOURCE.yaml.
2. Verify:
    * schema: l9.program-execution.campaign-source.v2
    * schema_version: 2.0.0
    * required Program Execution v2 contract identifiers.
3. Validate UTF-8 encoding and LF line endings.
4. Resolve runtime_root and worktree_root from the source.
5. Verify that neither path resolves inside:
    * Cursor-Governance source directories;
    * any declared target repository;
    * any target worktree.
6. Create the campaign runtime outside every target worktree.
7. Copy the final source byte-for-byte into the admission directory as:
    * CAMPAIGN_SOURCE.yaml
8. Compute SHA-256 over the preserved bytes.
9. Write an external source-integrity receipt containing:
    * source path;
    * admitted copy path;
    * source size;
    * SHA-256;
    * canonical encoding;
    * canonical line endings;
    * timestamp;
    * operator identity;
    * source repository revision when applicable.
10. Make the admitted source non-editable through normal campaign execution.
11. Never hand-edit the source digest or generated counts.

If a runtime already exists for the same campaign ID:

* inspect its preserved source;
* compare source digest and campaign identity;
* recover only when identity and digest are compatible;
* stop on campaign ID collision with different source bytes;
* never overwrite a conflicting runtime.

Write a source-traceability receipt connecting the final sibling source to the
admitted immutable copy.

The activation prompt is not authority and must not be imported into the
Blueprint or Program Lock.

Phase 3: instantiate the native Program Execution v2 pair

Resolve:

BP_TEMPLATE="$GC/environment/program-execution/core/program-execution-blueprint-template"
CTRL_TEMPLATE="$GC/environment/program-execution/core/program-execution-controller-template"

Before invoking any repository-owned interface, inspect current help:

python "$BP_TEMPLATE/scripts/instantiate.py" --help
python "$BP_TEMPLATE/scripts/validate_blueprint.py" --help
python "$CTRL_TEMPLATE/scripts/instantiate.py" --help
python "$CTRL_TEMPLATE/scripts/validate_controller.py" --help
python "$CTRL_TEMPLATE/scripts/pec.py" --help

Do not invent arguments.

Record:

template paths
template revisions
template digests
supported schema versions
supported controller versions
invocation commands
stdout
stderr
exit codes
working directories
timestamps

Confirm:

Blueprint and Controller contracts are compatible
campaign ID matches in both
owner matches the source
runtime root matches the source
worktree root matches the source
output directories are empty or recoverable
mutable runtime state remains outside target worktrees

Instantiate exactly one Blueprint and one compatible Controller.

Stop when current interfaces differ materially from the activation contract and
cannot be resolved through the current runbooks.

Phase 4: compile the complete Blueprint

Compile the immutable source into every native file required by the current
EXECUTION_INDEX.yaml, including at minimum:

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

Also complete every supporting Markdown, schema reference, manifest, and indexed
file required by the instantiated Blueprint.

Compilation requirements:

* preserve campaign semantics exactly;
* transform records into native Program Execution v2 schemas;
* use stable IDs from the source;
* preserve one authority per durable responsibility;
* preserve one target per mutating Task Card;
* keep dependencies only in the dependency graph;
* assign every task to exactly one wave;
* include every authorization-ceiling key on every task;
* keep task runtime status out of Task Cards;
* keep gate verdicts out of the Blueprint;
* keep leases, claims, attempts, and receipts out of the Blueprint;
* preserve exclusions as exclusions;
* never silently remove difficult scope;
* never add beneficial-looking scope;
* preserve evidence classifications;
* preserve exact rollback and negative-case obligations;
* preserve independent verification requirements.

Keep:

program:
  definition_status: draft

during compilation and evidence collection.

Campaign-specific compilation hardening

Ensure the compiled Blueprint preserves separate ownership for:

governance
identity and authorization
claims and conflicts
shared CLI transport
shared runtime enforcement
semantic memory
durable ingestion
evidence and receipts
adapter translation
Program Execution control

Ensure the Blueprint contains:

adapter.yaml contract
capabilities.yaml contract
shared lifecycle model
operation classification
policy profiles
CLI compatibility
identity binding
claim verification
degraded-mode behavior
durable delivery journal
real-CLI contract testing
multi-agent E2E
fault injection
shadow migration
canary
rollback rehearsal
legacy removal gate
second-peer reuse certification
architecture fitness functions

Do not describe cooperative-only behavior as hard enforcement.

Do not describe local receipt state as authority.

Do not describe model instructions as equivalent to deterministic mutation
enforcement.

Phase 5: collect current-state evidence

Inspect every declared target and external surface using read-only methods.

Replace source assumptions with exact current evidence when verification is
possible. Preserve UNKNOWN when it is not.

Repository evidence

For every repository target, bind:

canonical remote
repository_id
default branch
current branch
HEAD SHA
upstream SHA
divergence
clean or dirty state
dirty paths
active worktrees
repository aliases
governance files
architecture files
ADRs
source roots
build system
validation commands
CI workflows
required checks
rulesets
open pull requests
tags
releases
packages
environments

Shared CLI evidence

Inspect the actual installed or pinned CLI before using it:

l9-memory-mcp version
l9-memory-mcp doctor
l9-memory-mcp capabilities
l9-memory-mcp hydrate --help
l9-memory-mcp conflicts check --help
l9-memory-mcp claim acquire --help
l9-memory-mcp claim verify --help
l9-memory-mcp claim release --help
l9-memory-mcp ingest --help

Only invoke commands that exist in the verified CLI.

Record:

binary path
version
release provenance
checksum or signature status
protocol version
supported commands
supported output modes
supported timeout behavior
supported request identifiers
supported idempotency behavior
supported error taxonomy

Do not invent missing commands or flags.

MCP and memory-service evidence

Verify through controlled, non-production-safe probes:

endpoint
transport
protocol compatibility
authenticated principal
declared principal
identity match result
authorization scope
claim behavior
conflict behavior
ingestion behavior
idempotency behavior
rate-limit behavior
timeout behavior
audit behavior

Test that:

token principal == registry agent_id
token principal == adapter manifest identity
token principal == server-confirmed identity

Reject any configuration in which mutable headers or workspace files can select
another authenticated principal.

Adapter evidence

For each active adapter, collect:

adapter.yaml
capabilities.yaml
registry identity
token source mapping
runtime token projection
native lifecycle mechanism
declared enforcement strength
supported commands
unsupported commands
degraded-mode behavior
conformance status
E2E status

A declared capability without implementation and passing conformance evidence is
not supported.

Foundation-freeze evidence

Before implementation waves begin, compute external digests for the accepted
candidate versions of:

adapter schemas
capabilities schema
lifecycle schema
operation classification schema
CLI response envelope schema
policy profiles
shared runtime interface
reference adapter contract

Record them as a foundation-freeze evidence set.

The freeze does not prevent accepted changes. Any material change requires:

* a new source contract;
* renewed validation;
* updated digests;
* stale-runtime handling;
* re-evaluation of dependent tasks.

Runtime topology evidence

Produce an evidence-backed topology showing only:

Native Adapter
    -> Shared Adapter Runtime
    -> l9-memory-mcp
    -> MCP
    -> Shared Memory Service

Prove that no alternate adapter memory transport exists.

Legacy regression evidence

Scan for:

legacy memory client
legacy memory transport
legacy memory schema
legacy local lock authority
legacy hook wiring
legacy validator
legacy identity projection
duplicate conflict semantics
duplicate ingestion semantics

Do not block on intentionally retained migration fixtures, but classify every
match.

Conversation history and documentation are not execution evidence unless the
campaign source explicitly classifies them as documented intent.

Phase 6: validate and accept the Blueprint

While the Blueprint remains draft:

1. remove every placeholder;
2. resolve every cross-file reference;
3. prove task IDs equal dependency-graph nodes;
4. prove the graph is acyclic;
5. prove every task belongs to exactly one wave;
6. prove every task belongs to exactly one workstream;
7. prove every task has exactly one target;
8. prove repository IDs are complete and stable;
9. prove one durable responsibility has one authority;
10. prove accepted decisions have selected options and evidence;
11. prove resolved Unknowns have evidence;
12. prove active waivers have owner, scope, evidence, and expiry or revisit rule;
13. prove all authorization-ceiling keys are present;
14. prove every task has:
    * exact actions;
    * durable outputs;
    * observable acceptance;
    * validation;
    * negative cases;
    * rollback;
    * risk;
    * completion gates;
15. prove every gate has:
    * owner;
    * tasks;
    * required evidence;
    * pass criteria;
    * independent verification;
    * failure effect;
16. validate local links;
17. regenerate manifests using repository-owned logic;
18. verify source-to-Blueprint semantic parity;
19. verify no activation-only instruction entered campaign semantics;
20. verify no runtime state entered immutable files;
21. run native template-mode validation.

Also verify:

shared CLI is the sole adapter memory transport
identity binding is explicit
claim verification covers irreversible boundaries
degraded modes are explicit
durable ingestion is required
legacy deletion depends on shadow, canary, and rollback proof
second-peer reuse is required for platform-level convergence
remote actions remain exactly approval-gated

Do not suppress validator failures.

Do not accept:

empty-target success
skipped validation as pass
worker self-verification
file-presence checks as runtime proof
unsupported CLI behavior
unresolved blocking Unknowns

Only after the complete draft reflects verified current state may the named
authority:

1. accept required decisions;
2. resolve evidence-backed Unknowns;
3. set program.definition_status: accepted;
4. regenerate the Blueprint manifest;
5. run instantiated validation.

The Blueprint is not executable until instantiated validation passes.

Phase 7: bootstrap and validate the Controller

Validate the instantiated Controller using the current repository-owned
interface.

Bootstrap the Controller from the accepted Blueprint using the current supported
pec.py interface discovered through --help.

The Controller must:

* import every indexed source;
* compute immutable SHA-256 bindings;
* validate every cross-reference;
* create the Program Lock;
* reject unknown contract versions;
* bind the governance revision;
* bind the campaign-source digest;
* bind the Blueprint digest;
* bind target repository IDs;
* bind runtime and worktree roots;
* mark runtime stale when an accepted source changes;
* begin with no fabricated leases, claims, attempts, receipts, or gate results;
* preserve all task authorization ceilings;
* prevent downstream authority widening;
* preserve human ownership of the terminal verdict.

Never hand-edit the Program Lock.

After bootstrap, do not informally edit the accepted Blueprint.

When accepted source changes:

* stop new admission;
* record exact changed file and digest mismatch;
* use the canonical superseding Blueprint or relock workflow;
* never bypass stale-lock detection.

Phase 8: validate adapters and reconcile exact targets

Before task admission, inspect current Make targets and supported interfaces.

Run the current repository-owned equivalents of:

make -C "$GC" program-execution-core-validate
make -C "$GC" program-execution-adapters
make -C "$GC" program-execution-conformance
make -C "$GC" program-execution-probe

Do not invent target names when they differ. Discover current targets from the
repository.

Adapter admission checks

For every active adapter:

1. validate adapter.yaml;
2. validate capabilities.yaml;
3. verify registry identity parity;
4. verify secret-source mapping;
5. verify runtime token projection;
6. verify native lifecycle mapping;
7. verify operation mapping;
8. verify declared enforcement strength;
9. verify degraded-mode behavior;
10. verify every declared capability has:
    * implementation;
    * unit coverage;
    * conformance coverage;
    * supported CLI behavior where applicable;
11. verify unsupported capabilities are absent;
12. verify no direct memory transport exists;
13. verify no local conflict or claim authority exists.

Reference adapter certification

Before Claude Code may be treated as the reference adapter, require passing
evidence for:

schema
identity
capabilities
lifecycle mapping
operation classification
shared CLI contract
hydrate
conflicts check
claim acquire
claim verify
claim release when supported
ingest
durable recovery
degraded modes
bypass resistance
multi-agent concurrency
fault injection
shadow equivalence
canary
rollback rehearsal

Second-peer certification

Do not claim platform-wide adapter reuse until one second peer:

* is generated or materialized from canonical contracts;
* uses unchanged foundational schemas;
* uses unchanged shared runtime;
* provides only native mappings and thin entrypoints;
* passes capability-derived conformance;
* passes supported common E2E scenarios.

Exact target reconciliation

Reconcile each repository using the exact repository_id from
EXECUTION_TARGETS.yaml.

Bind:

canonical remote
repository fingerprint
repository aliases
baseline SHA
current worktree
campaign worktree
branch
upstream
writable scope
adapter

Reject repository identity based only on local filesystem path.

Use separate:

worktrees
branches
tasks
Source Contracts
attempts
pull requests

for separate repositories.

Never mutate one repository from another repository’s worktree.

Phase 9: launch the first ready wave

Run Controller validation, status, and next-task inspection.

Begin the first ready wave immediately and continue through reversible,
admitted, non-blocked work.

For each ready task:

1. revalidate the Program Lock;
2. verify exact task readiness;
3. resolve only evidence-backed decisions and Unknowns;
4. generate the exact Source Contract;
5. bind:
    * task ID;
    * work item ID;
    * repository ID;
    * baseline SHA;
    * workspace ID;
    * worktree path;
    * writable paths;
    * excluded paths;
    * role binding;
    * allowed operations;
    * validations;
    * evidence outputs;
    * expiration;
    * rollback boundary;
6. register the Source Contract;
7. run the required conflict check;
8. acquire the required claim;
9. record:
    * claim ID;
    * lease or expiry;
    * repository;
    * branch;
    * baseline revision;
    * scope digest;
    * operation classes;
10. prepare the task;
11. render the exact worker contract;
12. route through an adapter whose verified capabilities fit within effective
    authority;
13. execute only inside the admitted worktree and writable paths;
14. re-evaluate scope whenever the candidate diff changes;
15. stop on:
    * base drift;
    * scope drift;
    * identity mismatch;
    * claim expiry;
    * claim revocation;
    * approval mismatch;
    * stale Program Lock;
    * unsupported adapter capability;
16. verify the claim before every governed or irreversible boundary;
17. record a truthful Attempt Receipt;
18. verify independently against the exact candidate state;
19. record a Verification Receipt;
20. evaluate gates using evidence only;
21. preserve every:
    * attempt;
    * failure;
    * warning;
    * denial;
    * scope deviation;
    * degraded transition;
    * recovery;
    * rollback result.

A worker never independently verifies its own completion.

A local state receipt never independently grants mutation authority.

A successful local command never proves:

remote push
pull-request creation
merge
tag
release
publication
deployment
migration
external message
durable server ingestion

MCP memory lifecycle during task execution

For adapters declaring the required capabilities, the shared runtime must use the
verified CLI contract for:

l9-memory-mcp hydrate
l9-memory-mcp conflicts check
l9-memory-mcp claim acquire
l9-memory-mcp claim verify
l9-memory-mcp claim release
l9-memory-mcp ingest

Use only verified flags and output modes.

At session start:

1. reconcile pending prior-session ingestion;
2. hydrate;
3. record the hydration ID;
4. inject context without persisting hydrated contents.

Before governed work:

1. classify the proposed operation;
2. check conflicts;
3. acquire or verify the exact claim;
4. bind claim evidence to the session and candidate state.

At irreversible boundaries:

1. recompute branch, baseline, candidate diff, and scope digest;
2. verify the claim;
3. deny on mismatch or expiry.

At session end:

1. create the episode envelope;
2. separate harness provenance from model semantic summary;
3. redact secrets;
4. persist to the durable journal;
5. ingest with the session idempotency key;
6. retain the entry until acknowledgement.

Memory-service or CLI failure must not silently widen authority.

Exact approval boundaries

Continue automatically only through work explicitly authorized by the campaign
source, accepted Blueprint, Program Lock, Task Card, and rendered Source
Contract.

Stop immediately before any action lacking exact current authority, including:

* branch push;
* pull-request creation;
* pull-request readiness transition;
* merge;
* tag creation;
* tag push;
* package publication;
* artifact publication;
* GitHub Release creation;
* repository ruleset mutation;
* repository environment mutation;
* secret mutation;
* service-account or principal mutation;
* package-access change;
* lifecycle promotion;
* coordination-store cutover;
* memory-namespace migration;
* deployment;
* database migration;
* production traffic change;
* public endpoint change;
* destructive action;
* issue closure;
* pull-request closure;
* external stakeholder message.

Each approval request must bind:

exact action
exact target
exact candidate SHA or immutable revision
exact paths or settings
prerequisite evidence
expected effect
risk
reversibility
rollback
authorization expiration

Never request vague approval to “continue the campaign.”

Never reuse approval for:

another candidate revision
another branch
another scope
another target
another operation
an expired authorization

Prior conversation does not imply current remote authority.

Activation-only certification responsibilities

Before broad execution or cutover, perform these activation certifications.

1. CLI compatibility certification

Verify and record:

installed binary
version
provenance
checksum or signature
protocol version
required commands
structured output
error taxonomy
timeout behavior
idempotency behavior

Block CLI-dependent tasks on incompatibility.

2. Capability declaration parity

For each capability declared in capabilities.yaml, prove:

declared
implemented
reachable
covered by tests
supported by current CLI or native surface
represented in conformance

Reject declaration-only capability.

3. Identity-chain certification

Prove consistency across:

agent_registry.yaml
adapter.yaml
capabilities.yaml
rendered environment
MCP configuration
authenticated token principal
server-confirmed principal
claim owner
audit event

Any mismatch is a security failure.

4. Runtime-topology certification

Prove the allowed path is:

Native Adapter
  -> Shared Adapter Runtime
  -> l9-memory-mcp
  -> MCP
  -> Shared Memory Service

Block activation when an alternate memory transport or duplicate memory-domain
implementation exists.

5. Foundation freeze

Before the first implementation wave, record external SHA-256 values for the
accepted foundational contracts and runtime interfaces.

Material changes after the freeze require:

* stale Program Lock;
* new source contract;
* revalidation;
* updated foundation digest set;
* dependent-task re-evaluation.

6. Golden reference comparison

Compare the Claude Code reference adapter against the canonical adapter contract.

Only native-surface differences are allowed.

Shared runtime, identity, claim, memory, delivery, and policy behavior must not
fork.

7. Legacy regression scan

Run recursive scans for:

direct memory HTTP client
Claude-only MCP client
duplicate claim schema
duplicate conflict algorithm
local authoritative lock state
duplicate identity mapping
obsolete memory hooks
obsolete validation target
obsolete setup reference
obsolete ADR or topology statement

Classify every match as:

active violation
migration fixture
historical documentation
approved exception

No active violation may remain at convergence.

8. Full recovery drill

Before legacy removal, simulate:

hydrate
claim
governed mutation
process crash
restart
pending-journal replay
claim reconciliation
ingest
next-session hydration
rollback to legacy mode

The drill must preserve local work, prevent duplicate episodes, and restore
operational safety.

9. Platform invariants

At admission and before convergence, verify:

adapters translate only
shared runtime normalizes and enforces
shared CLI transports
memory service owns identity claims conflicts and ingestion truth
local receipts do not grant authority
memory outages do not silently grant mutation authority
ingestion is durable and idempotent
declared capabilities require evidence
legacy deletion follows proven replacement
second-peer reuse proves the platform claim

10. Future-adapter readiness

Generate or inspect a new adapter scaffold and prove that a future adapter can
reach structural validity through:

generator
schema validation
identity registration
capability declaration
native mapping
conformance selection
E2E certification

without modifying foundational schemas or the shared runtime.

Migration sequence

The allowed pipeline modes are:

legacy
mcp_shadow
mcp_enforced_canary
mcp_enforced

Progress only in this order.

Legacy mode

* existing pipeline remains authoritative;
* new contracts and tests may be built;
* no shared-path result grants production authority.

MCP shadow mode

* legacy path remains authoritative;
* shared path runs only in non-authoritative comparison mode;
* prevent duplicate claims and duplicate ingestion;
* record structured equivalence results;
* classify every difference.

MCP-enforced canary

* enable for a controlled Claude Code environment;
* monitor:
    * unauthorized allows;
    * false denials;
    * identity mismatch;
    * pending ingestion;
    * latency;
    * service failures;
    * rollback readiness;
* stop on any unsafe divergence.

MCP-enforced mode

Enable only after:

contract gates pass
identity gates pass
claim gates pass
ingestion gates pass
E2E passes
fault injection passes
shadow equivalence passes
canary passes
rollback rehearsal passes
exact cutover authority exists

Legacy removal

Delete the old Claude-specific memory implementation only after the Controller
records all predecessor gates as passed and exact human cutover approval is
current.

Recovery

On interruption, inconsistency, or failed execution:

1. run the canonical Controller recovery interface;
2. run Controller validation;
3. inspect Controller status;
4. inspect the Program Lock;
5. detect source, Blueprint, governance, target, and contract digest drift;
6. stop new admission when stale;
7. preserve every attempt and receipt.

Recover:

abandoned worktrees
expired claims
revoked claims
pending ingestion
accepted-but-unacknowledged ingestion
partially rendered adapter configuration
interrupted installer state
failed canary state

Reject stale claims and stale local receipts.

Do not bypass Program Lock validation.

Do not manually edit Controller runtime state.

Do not replay an external side effect with unknown outcome until independent
reconciliation or idempotency proves safety.

When semantic memory is unavailable:

* permit only declared safe degraded behavior;
* queue ingestion;
* fail governed mutation closed when required.

When coordination or claim verification is unavailable:

* stop governed mutation and integration.

When identity verification is unavailable:

* stop claims and protected writes.

When rollback is required:

* restore operational safety;
* restore prior wiring when applicable;
* preserve pending episodes;
* reconcile active claims;
* record the exact rollback result.

Remote promotion

The campaign may prepare local commits when explicitly authorized by the Task
Card and Source Contract.

Stop before push unless exact push approval exists.

After push:

* independently observe the remote branch SHA;
* independently observe required CI;
* do not treat the local command exit code as remote proof.

Stop before pull-request creation unless exact approval exists.

Stop before merge unless separate exact merge approval exists.

Keep separate evidence for:

local commit
remote branch
pull request
CI
review
merge commit
release
publication
deployment

Closeout

After every admitted task and gate is processed, export the canonical Controller
Handoff Receipt.

Include all campaign-relevant evidence for:

campaign source
Blueprint
Program Lock
governance revision
foundation digests
CLI version and protocol
memory-service identity
target revisions
adapter manifests
capabilities
conformance
E2E
fault injection
shadow comparison
canary
rollback rehearsal
legacy removal
second-peer reuse
pull requests
CI
reviews
merge commits
tags
releases
publications
deployments
tasks
attempts
verification receipts
gates
decisions
Unknowns
risks
waivers
claims
lease or expiry history
pending ingestion
recovery
rollback

The Controller may recommend but never declare:

CONVERGED
CONVERGED_WITH_NON_BLOCKING_RISKS
NOT_CONVERGED
INCONCLUSIVE

Present the recommendation and complete evidence to the named human program
owner.

Progress reporting

At every material step report:

PROGRAM:
CURRENT WAVE:
CURRENT TASK:
CONTROLLER STATUS:
PROGRAM LOCK DIGEST:
TARGET REVISIONS:
CANDIDATE REVISION:
ADAPTER:
PIPELINE MODE:
CLI VERSION:
PROTOCOL VERSION:
SESSION ID:
CLAIM ID:
CLAIM STATUS:
SCOPE DIGEST:
EVIDENCE ADDED:
COMMANDS EXECUTED:
VALIDATION RESULT:
DECISIONS RESOLVED:
UNKNOWNS REMAINING:
RISKS CHANGED:
PENDING INGEST:
SHADOW EQUIVALENCE:
CANARY STATUS:
ROLLBACK READINESS:
NEXT READY TASK:
APPROVAL REQUIRED:

Report actual observed results.

Do not:

* hide failed commands;
* report skipped validation as passed;
* report future work as complete;
* mark a task complete before independent verification;
* claim remote events without observation;
* claim durable ingestion without acknowledgement or retained queue evidence.

Your first response after receiving this activation request must report actual
launch results, including:

resolved campaign source path
resolved primary workspace
resolved governance root
bootstrap result
source validation result
existing-work protection result
current admission blocker
next executable action

Do not restate this prompt in the first response.