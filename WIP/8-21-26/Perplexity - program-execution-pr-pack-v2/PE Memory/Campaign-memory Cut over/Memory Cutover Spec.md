Using the shared CLI is the right boundary:

l9-memory-mcp hydrate
l9-memory-mcp claim acquire
l9-memory-mcp claim verify
l9-memory-mcp conflicts check
l9-memory-mcp ingest

That removes the need for a Claude-specific transport client while preserving deterministic lifecycle enforcement. The convergence plan should therefore delete Claude’s private memory semantics, but retain thin hooks that invoke this CLI and interpret stable machine-readable results. PLAN-unify-claude-code-memory-to-mcp.md

Hardened target design

Claude Code lifecycle event
        │
        ▼
Thin surface hook
  - classify operation
  - collect repository context
  - invoke shared CLI
  - enforce exit/result policy
        │
        ▼
l9-memory-mcp
  - MCP transport
  - authentication
  - retries/timeouts
  - protocol negotiation
        │
        ▼
Shared memory service
  - hydration
  - claims and leases
  - conflict detection
  - ingestion
  - audit

The hooks must not contain:

* memory HTTP calls;
* MCP protocol code;
* conflict algorithms;
* lock-state interpretation beyond documented result codes;
* token manipulation;
* duplicated request schemas;
* independent identity selection.

Their responsibility should be limited to lifecycle translation and enforcement.

⸻

1. Make the CLI contract automation-grade

Before migrating the hooks, I would formalize the CLI as a versioned interface.

Every command needs:

--output json
--non-interactive
--timeout <seconds>
--request-id <uuid>
--agent-id claude-code
--session-id <uuid>

Prefer configuration-derived identity over passing identity on every invocation, but always make the effective identity visible in output.

Example:

l9-memory-mcp hydrate \
  --output json \
  --non-interactive \
  --session-id "$L9_SESSION_ID" \
  --repo "$L9_REPOSITORY" \
  --branch "$L9_BRANCH" \
  --base-sha "$L9_BASE_SHA"

A successful response should have a stable envelope:

{
  "schema_version": "1.0",
  "command": "hydrate",
  "status": "ok",
  "request_id": "req-123",
  "agent": {
    "id": "claude-code",
    "user_id": "claude_code_agent",
    "source": "claude-code"
  },
  "result": {
    "hydration_id": "hyd-123",
    "expires_at": "2026-08-04T23:00:00Z",
    "context": {}
  },
  "error": null
}

Failures should have typed codes rather than requiring hooks to parse text:

{
  "schema_version": "1.0",
  "command": "claim.verify",
  "status": "error",
  "result": null,
  "error": {
    "code": "CLAIM_EXPIRED",
    "retryable": false,
    "message": "The claim lease has expired."
  }
}

Required error taxonomy

At minimum:

AUTHENTICATION_FAILED
IDENTITY_MISMATCH
PERMISSION_DENIED
CONFIGURATION_INVALID
PROTOCOL_INCOMPATIBLE
SERVICE_UNAVAILABLE
DEADLINE_EXCEEDED
RATE_LIMITED
HYDRATION_NOT_FOUND
CLAIM_NOT_FOUND
CLAIM_EXPIRED
CLAIM_SCOPE_MISMATCH
CLAIM_OWNERSHIP_MISMATCH
CONFLICT_DETECTED
INGEST_REJECTED
SCHEMA_INVALID
DUPLICATE_ACCEPTED

Hooks should branch only on documented codes and process exit status.

⸻

2. Define stable exit codes

Do not use one generic nonzero exit code.

For example:

Exit	Meaning	Hook behavior
0	Success	Continue
10	Conflict or claim denial	Deny governed operation
11	Authentication/identity failure	Deny and raise security alert
12	Invalid configuration	Deny and show operator remediation
13	Service unavailable/timeout	Apply operation-class failure policy
14	Protocol/schema incompatibility	Deny; deployment regression
15	Invalid CLI invocation	Deny; implementation defect
20	Ingest queued locally	Allow shutdown, retain journal
21	Duplicate ingest accepted	Treat as success

This prevents a transport timeout from being confused with an actual conflict.

⸻

3. Add capabilities.yaml

I would make the file both declarative and enforceable.

schema_version: 1
agent:
  id: claude-code
  user_id: claude_code_agent
  source: claude-code
  registry_ref: environment/agents/agent_registry.yaml#claude-code
memory:
  provider: l9-shared-memory
  transport: mcp
  client: l9-memory-mcp
  minimum_cli_version: "1.4.0"
  required_protocol_version: "2026-06"
commands:
  hydrate:
    required: true
    lifecycle: session_start
    timeout_seconds: 15
    failure_mode: degraded_read_only
  conflicts_check:
    required: true
    lifecycle: before_governed_mutation
    timeout_seconds: 10
    failure_mode: fail_closed
  claim_acquire:
    required: true
    lifecycle: before_governed_mutation
    timeout_seconds: 10
    failure_mode: fail_closed
  claim_verify:
    required: true
    lifecycle: before_each_governed_boundary
    timeout_seconds: 5
    failure_mode: fail_closed
  ingest:
    required: true
    lifecycle: session_end
    timeout_seconds: 15
    failure_mode: durable_queue
enforcement:
  profile: implementer
  governed_operations:
    - protected_root_edit
    - canonical_policy_edit
    - git_commit
    - git_push
    - git_merge
    - pull_request_create
    - pull_request_merge
    - memory_namespace_promotion
    - destructive_memory_operation
  ungoverned_operations:
    - read
    - search
    - test
    - local_analysis
    - non_protected_source_edit
  break_glass:
    enabled: true
    human_only: true
    requires_reason: true
    emits_audit_event: true
    maximum_duration_seconds: 900
identity:
  token_env: L9_MEMORY_TOKEN__CLAUDE_CODE
  runtime_token_env: L9_MEMORY_CLIENT_TOKEN
  reject_header_principal_mismatch: true
session:
  receipt_schema: environment/agents/contracts/memory-session-receipt.schema.json
  receipt_contains_memory_content: false
writeback:
  idempotency_key: session_id
  durable_journal: true
  retry_on_next_start: true
  retention_hours: 72
  redact_secrets: true
observability:
  structured_logs: true
  audit_required: true
  include_request_id: true
  include_session_id: true
  include_claim_id: true

Then extend validate_agents.py to validate this file against a schema rather than merely checking that it exists.

The repository already relies on structured rules and explicit session workflows, so the capability declaration should become part of that governance model rather than documentation only. 

⸻

4. Pin and verify the shared CLI

A shared CLI becomes a new supply-chain boundary.

I would require:

* an exact or bounded compatible version;
* checksum or signature verification during installation;
* provenance from the approved release pipeline;
* no implicit “download latest” behavior;
* CLI version output in diagnostic logs;
* protocol compatibility check before lifecycle use.

At setup:

l9-memory-mcp version --output json
l9-memory-mcp doctor --output json

The adapter validator should assert:

installed CLI version >= minimum_cli_version
installed CLI major version is supported
MCP protocol version is supported
configured endpoint matches the approved environment
authenticated principal resolves to claude-code
required commands are discoverable

A breaking CLI release must fail in setup or CI, not during a commit hook.

⸻

5. Prevent identity spoofing

The most important security check is that headers and configuration cannot override the bearer principal.

The memory service should derive the principal from the token and reject:

token principal = claude-code
X-L9-Agent-Id = codex

The CLI should expose the server-confirmed principal:

{
  "authenticated_principal": "claude-code",
  "declared_principal": "claude-code",
  "identity_verified": true
}

The hook should fail closed when identity_verified is not exactly true.

Also test:

* token for another agent;
* missing token;
* expired token;
* token with insufficient role;
* valid token with forged headers;
* valid Claude token attempting another namespace;
* token loaded from an unexpected environment variable;
* secret accidentally passed through command-line arguments.

Tokens should be read from the environment or secure store, never emitted in:

* command arguments visible through process inspection;
* logs;
* hook error messages;
* receipts;
* ingest payloads.

⸻

6. Use server-issued claims, not local lock state

The existing Claude pipeline appears to maintain local state around hydration, locks, and enforcement. The unified implementation should replace that with opaque server-issued identifiers. PLAN-unify-claude-code-memory-to-mcp.md

Recommended claim flow:

l9-memory-mcp conflicts check \
  --repo "$REPO" \
  --branch "$BRANCH" \
  --scope-file "$SCOPE_FILE" \
  --output json
l9-memory-mcp claim acquire \
  --repo "$REPO" \
  --branch "$BRANCH" \
  --scope-file "$SCOPE_FILE" \
  --lease-seconds 900 \
  --output json

Persist only:

{
  "schema_version": "1.0",
  "session_id": "session-123",
  "hydration_id": "hyd-123",
  "claim_id": "claim-123",
  "agent_id": "claude-code",
  "repository": "Quantum-L9/Cursor-Governance",
  "branch": "feature/mcp-memory",
  "scope_digest": "sha256:...",
  "issued_at": "...",
  "expires_at": "..."
}

Do not cache a local Boolean such as:

{"lock_valid": true}

Before every irreversible boundary:

l9-memory-mcp claim verify \
  --claim-id "$CLAIM_ID" \
  --repo "$REPO" \
  --branch "$BRANCH" \
  --scope-digest "$SCOPE_DIGEST" \
  --output json

That prevents stale local state from granting authority.

⸻

7. Bind claims to actual Git state

A claim should not merely say “Claude owns Environment.”

Bind it to:

* repository canonical identity;
* branch;
* base commit;
* scope digest;
* agent principal;
* operation class;
* lease expiry.

Before commit or push, verify that the current state still matches.

For example:

claim.base_sha == merge-base(origin/main, HEAD)
claim.branch == current branch
claim.scope includes every changed governed path
claim.agent_id == authenticated principal
claim.expires_at > server time

If a new protected file enters the diff after claim acquisition, verification should fail with CLAIM_SCOPE_MISMATCH.

This closes a common time-of-check/time-of-use gap:

claim acquired for files A and B
agent later modifies protected file C
old claim incorrectly authorizes commit

⸻

8. Separate operation classification from enforcement

Create one deterministic classifier shared by tests and hooks.

For example:

environment/agents/policy/classify_operation.py

Input:

{
  "tool": "Bash",
  "command": "git push origin feature/foo",
  "changed_paths": [
    "environment/agents/adapters/claude-code/capabilities.yaml"
  ]
}

Output:

{
  "classification": "governed",
  "operation": "git_push",
  "required_controls": [
    "hydration",
    "conflicts_check",
    "claim_verify"
  ],
  "matched_rules": [
    "implementer.git_push",
    "environment.adapter_change"
  ]
}

Do not duplicate command matching across:

* Claude settings;
* shell hooks;
* tests;
* documentation.

Test the classifier independently with a large command corpus.

Include evasive variants:

git -C /repo push
env FOO=bar git push
bash -lc 'git push'
command git push
/usr/bin/git push
git push && echo done
make publish
gh pr create
gh pr merge

Also handle non-shell mutation tools such as direct file editing and GitHub MCP operations.

⸻

9. Harden the lifecycle hooks

The replacement hooks should use secure subprocess execution:

* argument arrays, never shell interpolation;
* sanitized environment;
* fixed executable resolution;
* bounded stdout/stderr;
* hard timeout plus process-group termination;
* restrictive receipt permissions;
* atomic writes;
* no following symlinks;
* deterministic working directory;
* structured error output.

Conceptually:

subprocess.run(
    [
        cli_path,
        "claim",
        "verify",
        "--claim-id",
        claim_id,
        "--repo",
        repo,
        "--branch",
        branch,
        "--output",
        "json",
        "--non-interactive",
    ],
    shell=False,
    check=False,
    capture_output=True,
    text=True,
    timeout=5,
    env=sanitized_env,
)

Validate the returned JSON against a local response-envelope schema before trusting fields.

The schema describes transport shape only. It must not duplicate memory-domain rules.

⸻

10. Make session receipts tamper-evident

A local receipt can otherwise be forged by the agent process.

Preferred options, in order:

1. Server-signed receipt or capability.
2. Receipt containing an opaque server ID that is always reverified.
3. OS-protected state written by a trusted wrapper outside the model-controlled workspace.

The hook should never trust a user-editable file as final authority.

Minimum protection:

* store outside the repository;
* permissions 0600;
* atomic write;
* owner validation;
* reject symlinks;
* validate schema;
* verify through the CLI before governed actions.

Example location:

${XDG_STATE_HOME}/l9-memory/sessions/<session-id>.json

Not:

repo/.claude/memory_state.json

⸻

11. Add durable, idempotent writeback

l9-memory-mcp ingest should support:

--idempotency-key "$SESSION_ID"
--payload-file "$ENVELOPE"

The session-end hook should:

1. Build the episode envelope.
2. Redact secrets.
3. Write it atomically to the local delivery journal.
4. Call ingest.
5. Validate the acknowledgement.
6. Mark the entry delivered.
7. Remove it after a retention window.

On the next session start:

retry pending ingest entries
then hydrate current session

That ordering ensures the new session can hydrate from the previous session’s final state.

Test termination cases:

* normal stop;
* SIGTERM;
* CLI timeout;
* laptop sleep;
* network loss;
* duplicate stop hook;
* process crash after server acceptance but before local acknowledgement.

The last case is why idempotency is mandatory.

⸻

12. Add semantic payload validation

Do not permit arbitrary model-generated JSON to be ingested.

Define an episode schema with strict limits:

additionalProperties: false
max payload size: 256 KiB
summary max length: 8 KiB
decision count max: 100
changed path count max: 5000

Separate trusted and untrusted fields:

{
  "provenance": {
    "generated_by": "harness",
    "agent_id": "claude-code",
    "repository": "...",
    "branch": "...",
    "base_sha": "...",
    "final_sha": "...",
    "commits": []
  },
  "semantic_summary": {
    "generated_by": "model",
    "summary": "...",
    "decisions": [],
    "risks": [],
    "next_steps": []
  }
}

The model must not be able to invent provenance fields.

Add redaction for:

* bearer tokens;
* API keys;
* private keys;
* credentials embedded in URLs;
* known secret environment-variable values;
* .env contents;
* large binary or generated data.

⸻

13. Use contract tests against the actual CLI

Unit-testing hooks with mocked subprocesses is necessary but insufficient.

Build a CLI contract test suite that executes the real binary against a controlled MCP test server.

Contract scenarios

Hydrate

* succeeds with valid identity;
* returns empty context cleanly;
* handles large but valid context;
* rejects malformed response;
* rejects unsupported schema version;
* times out predictably;
* does not leak token in logs.

Conflicts

* no conflict;
* exact path conflict;
* ancestor-directory conflict;
* overlapping namespace conflict;
* expired competing claim;
* same-agent reentrant claim;
* cross-branch policy;
* conflict service unavailable.

Claim acquire

* success;
* denied due to active conflict;
* denied due to role;
* lease bounded by server maximum;
* idempotent retry with same request ID;
* duplicate request returns same claim;
* scope normalization prevents path traversal.

Claim verify

* valid;
* expired;
* revoked;
* wrong agent;
* wrong repository;
* wrong branch;
* scope widened after acquisition;
* server clock skew;
* unknown claim.

Ingest

* accepted;
* duplicate accepted;
* malformed schema rejected;
* oversized payload rejected;
* secret-bearing payload rejected or redacted;
* partial service failure;
* retry after timeout;
* server accepted but client lost acknowledgement.

⸻

14. Add full end-to-end scenarios

Create an isolated test repository and run the actual hooks, CLI, and test MCP service.

E2E 1 — Happy path

start session
→ hydrate
→ check conflicts
→ acquire claim
→ edit governed path
→ verify claim
→ commit
→ verify claim
→ push to test remote
→ ingest session
→ start next session
→ previous episode appears in hydration

This proves continuity, not merely command success.

E2E 2 — Competing agents

Run two isolated identities:

Claude acquires Environment/**
Codex attempts overlapping claim
Codex receives conflict
Claude non-overlapping change remains allowed
Claude releases/expires claim
Codex can then acquire

E2E 3 — Stale claim

Claude acquires claim
lease expires
Claude attempts commit
hook denies commit
working tree remains intact
new claim acquired
commit succeeds

E2E 4 — Scope expansion

claim covers adapter directory
Claude additionally modifies CANONICAL_LAW.md
commit verification detects new governed scope
commit denied

E2E 5 — Memory outage

hydration unavailable
session enters DEGRADED_READ_ONLY
reads and analysis continue
protected edit/commit/push denied
ingest is queued
service restored
queued ingest succeeds

E2E 6 — Identity attack

Claude token + Codex identity header
server rejects
hook records identity security event
governed action denied

E2E 7 — Crash recovery

session modifies files
stop ingest accepted
process dies before acknowledgement
next session retries same idempotency key
one episode exists, not two

E2E 8 — CLI incompatibility

install unsupported CLI major version
doctor check fails
adapter setup fails before session begins

E2E 9 — Bypass attempts

Attempt governed operations through:

* direct git;
* absolute Git path;
* bash -c;
* Makefile target;
* GitHub CLI;
* alternative editing tool;
* nested shell;
* aliases;
* direct GitHub API integration.

The enforcement boundary must classify effects, not only match one literal command.

⸻

15. Add fault injection

Test the ugly paths deliberately:

* 100 ms to 30 s latency;
* TCP reset;
* HTTP 429;
* HTTP 500/502/503;
* malformed JSON;
* truncated output;
* CLI process hang;
* CLI exits zero with invalid response;
* server clock ahead/behind;
* DNS failure;
* token rotation during session;
* claim revoked between check and commit;
* concurrent ingest;
* disk full while writing journal;
* corrupted local receipt;
* symlink attack against state path.

Assertions should cover both safety and operator experience:

* no unauthorized operation proceeds;
* no local work is lost;
* errors identify remediation;
* retries do not create duplicate memory;
* secrets are not printed.

⸻

16. Add regression fixtures from the old pipeline

Before deleting the bespoke implementation, capture its externally meaningful behavior as fixtures.

Create golden cases for:

* action classification;
* protected path detection;
* lock requirement logic;
* break-glass behavior;
* writer identity;
* session metadata;
* writeback contents;
* denial messages where operationally important.

Run old and new implementations against the same fixtures.

Classify differences:

INTENDED
COMPATIBLE
BREAKING
UNKNOWN

No UNKNOWN difference should reach cutover.

The original plan proposed deleting test_memory_writer_identity.py and test_memory_enforcement.py; I would not simply remove them. Rewrite their behavioral assertions against the CLI-backed implementation first. PLAN-unify-claude-code-memory-to-mcp.md

⸻

17. Run shadow mode with measurable equivalence

Support:

L9_MEMORY_PIPELINE_MODE=legacy
L9_MEMORY_PIPELINE_MODE=mcp-shadow
L9_MEMORY_PIPELINE_MODE=mcp-enforced

During mcp-shadow:

* legacy logic remains authoritative;
* shared CLI runs in parallel;
* no duplicate claims or writes are created—use dry-run, read-only comparison, or shared request IDs;
* results are compared structurally;
* differences emit metrics and audit events.

Track:

hydrate_equivalence_rate
conflict_equivalence_rate
claim_decision_equivalence_rate
writer_identity_equivalence_rate
ingest_payload_equivalence_rate
mcp_cli_failure_rate
mcp_cli_p95_latency

Suggested promotion requirements:

* 100% identity agreement;
* 100% governed-action decision agreement;
* zero unauthorized allows;
* zero lost ingests;
* duplicate ingest rate effectively zero through idempotency;
* acceptable lifecycle latency;
* all fault-injection tests green.

Do not promote based only on “CI passed.”

⸻

18. Add canary enforcement

Before enabling for every Claude environment:

1. Enable MCP shadow mode in CI.
2. Enable enforced mode in one controlled developer environment.
3. Enable for protected-root operations only.
4. Extend to commit and push.
5. Extend to all declared governed operations.
6. Remove the legacy implementation after the observation window.

The observation window should be based on scenario coverage, not only elapsed time:

* at least one conflict;
* at least one expiry;
* at least one outage/retry;
* at least one protected-root change;
* at least one end-to-end handoff.

⸻

19. Strengthen CI

I would add these jobs.

adapter-schema

Validates:

* registry;
* adapter layout;
* capabilities.yaml;
* identity consistency;
* no committed secret;
* no unsupported capability value.

cli-contract

Runs real l9-memory-mcp against a fake MCP server.

memory-e2e

Runs a temporary Git repository, two agent identities, hooks, CLI, and test server.

memory-fault-injection

Runs timeout, malformed response, revocation, duplicate and outage cases.

memory-no-bypass

Scans and tests for:

* old memory HTTP clients;
* direct memory endpoint use;
* obsolete hook names;
* duplicate auth header construction;
* alternate Claude-only memory state;
* banned imports.

memory-doc-consistency

Checks that:

* old pipeline paths are not referenced;
* ADR supersession links resolve;
* root documents match the active architecture;
* setup docs use the same CLI commands and environment names.

memory-migration-diff

Runs legacy fixtures and new fixtures until final deletion.

⸻

20. Add repository-level architecture tests

Use static checks to make regression harder.

Examples:

Only l9-memory-mcp may communicate with the memory endpoint.
No Python file under environment/surfaces may import HTTP clients for memory.
No adapter may define memory conflict or lock schemas.
No token may be read from more than the approved runtime variable.
No agent adapter may override authenticated identity.

This can be implemented with a combination of:

* grep-based forbidden-pattern checks;
* AST checks for Python imports;
* schema validation;
* dependency allowlists;
* test-time network denial.

A useful E2E safeguard is to block direct network access from hook processes and allow only the shared CLI subprocess to reach the test MCP server. That proves the hooks cannot quietly recreate the old transport path.

⸻

21. Observability and audit

Emit structured events for every lifecycle action:

{
  "event": "memory_claim_verify",
  "timestamp": "...",
  "request_id": "...",
  "session_id": "...",
  "agent_id": "claude-code",
  "repository": "Quantum-L9/Cursor-Governance",
  "branch": "...",
  "claim_id": "...",
  "operation": "git_push",
  "decision": "deny",
  "reason_code": "CLAIM_EXPIRED",
  "cli_version": "1.4.0",
  "duration_ms": 142
}

Do not include:

* token;
* hydrated content;
* full prompts;
* arbitrary environment variables;
* sensitive ingest payloads.

Minimum metrics:

memory_cli_invocations_total{command,status}
memory_cli_latency_seconds{command}
memory_hydration_failures_total{reason}
memory_conflicts_total{scope}
memory_claim_denials_total{reason}
memory_identity_mismatch_total
memory_governed_actions_denied_total{operation,reason}
memory_break_glass_total{operator}
memory_ingest_queued_total
memory_ingest_retry_total
memory_ingest_oldest_pending_seconds
memory_schema_incompatibility_total

Alert on:

* any identity mismatch;
* any unsupported schema;
* any break-glass activation;
* pending ingestion beyond threshold;
* sudden fall in hydration success;
* unexpected absence of claim verification before governed actions.

⸻

22. Preserve break-glass, but make it expensive and visible

Break-glass should require:

* explicit human action;
* reason;
* expiry;
* operator identity;
* affected scope;
* audit event;
* follow-up reconciliation.

Example:

l9-memory-mcp claim acquire \
  --break-glass \
  --reason "Memory service outage during production rollback" \
  --scope-file /tmp/scope.json \
  --lease-seconds 600

The model must not be able to initiate this autonomously.

After break-glass use:

* force ingest/audit reconciliation;
* open a governance finding;
* invalidate the emergency claim;
* review affected commits.

⸻

23. Test installation and upgrade paths

E2E should include more than runtime behavior.

Test:

* clean installation;
* upgrade from legacy Claude pipeline;
* downgrade during rollback;
* token already configured;
* token missing;
* stale .mcp.json;
* stale old hook files;
* partial installation;
* interrupted installer;
* repeated installer execution;
* uninstallation;
* unsupported OS/shell behavior;
* path containing spaces;
* multiple repository worktrees.

Installer operations should be idempotent.

Running setup twice should produce the same configuration, not duplicate hooks or overwrite operator-managed settings.

⸻

24. Define cutover gates

I would not delete the old pipeline until:

* the real shared CLI passes contract tests;
* capabilities.yaml is schema-validated;
* identity mismatch is rejected server-side;
* claims are bound to repository, branch, scope and principal;
* all irreversible boundaries reverify claims;
* session ingest is durable and idempotent;
* two-agent conflict E2E passes;
* outage mode E2E passes;
* crash-recovery E2E passes;
* bypass tests pass;
* legacy/new fixtures show no unexplained differences;
* shadow mode shows zero unsafe divergences;
* rollback has been exercised;
* stale references and direct memory clients are absent;
* the next session successfully hydrates the previous session’s episode.

Recommended implementation delta

Relative to the original plan, I would make these changes:

ADD
  environment/agents/adapters/claude-code/capabilities.yaml
  environment/agents/contracts/adapter-capabilities.schema.json
  environment/agents/contracts/memory-session-receipt.schema.json
  environment/surfaces/claude-code/hooks/session_start.*
  environment/surfaces/claude-code/hooks/governance_verify.*
  environment/surfaces/claude-code/hooks/session_stop.*
  environment/agents/tests/cli_contract/
  environment/agents/tests/memory_e2e/
  environment/agents/tests/fault_injection/
  environment/agents/tests/legacy_fixtures/
USE
  l9-memory-mcp hydrate
  l9-memory-mcp conflicts check
  l9-memory-mcp claim acquire
  l9-memory-mcp claim verify
  l9-memory-mcp ingest
REMOVE AFTER CUTOVER
  Claude-specific HTTP client
  Claude-specific memory schemas
  Claude-specific conflict algorithms
  locally authoritative lock state
  duplicate identity logic

The key hardening principle is:

The shared CLI owns transport and protocol behavior; the server owns memory truth and authorization; the Claude hook owns only lifecycle classification and enforcement.

That gives you one memory implementation, preserves deterministic safeguards, and creates enough contract, regression, adversarial, and E2E coverage to prove that convergence did not silently weaken governance.


Architectural objective

Build one reusable integration framework with five clear ownership boundaries:

Agent surface
    ↓
Standard lifecycle adapter
    ↓
Shared l9-memory-mcp CLI
    ↓
Shared MCP protocol
    ↓
Shared memory service

Each layer must have exactly one responsibility.

Layer	Responsibility
Agent surface	Emit lifecycle events and provide native context
Lifecycle adapter	Normalize events, classify actions, enforce policy
Shared CLI	MCP transport, protocol, authentication, retries
MCP server	Memory truth, authorization, claims, conflicts, ingestion
Registry and contracts	Identity, capabilities, policy profile, compatibility

The reference implementation should establish reusable behavior, not reusable Claude scripts.

⸻

1. Create a canonical adapter specification

Do not make claude-code/capabilities.yaml the standard by example alone.

Create a formal contract:

environment/agents/contracts/
├── adapter-capabilities.schema.json
├── adapter-manifest.schema.json
├── lifecycle-event.schema.json
├── lifecycle-result.schema.json
├── operation-classification.schema.json
├── memory-session-receipt.schema.json
├── memory-episode.schema.json
├── delivery-journal-entry.schema.json
└── cli-response-envelope.schema.json

Every peer adapter must validate against the same schemas.

The reference adapter contract should define:

* identity;
* supported lifecycle events;
* memory commands;
* enforcement profile;
* failure behavior;
* state storage;
* writeback guarantees;
* break-glass behavior;
* observability requirements;
* compatibility versions;
* platform-specific integration mechanism.

This avoids future adapters inventing their own interpretations.

⸻

2. Separate manifest from capabilities

I would use two files for each adapter.

adapter.yaml

Describes what the adapter is.

schema_version: 1
adapter:
  id: claude-code
  display_name: Claude Code
  surface: cli-agent
  status: active
identity:
  agent_id: claude-code
  user_id: claude_code_agent
  source: claude-code
  registry_key: claude-code
runtime:
  platforms:
    - linux
    - macos
  integration:
    type: native-hooks
  installer: setup.sh
memory:
  provider: l9-shared-memory
  client: l9-memory-mcp
  protocol: mcp

capabilities.yaml

Describes what the adapter can enforce and guarantee.

schema_version: 1
lifecycle:
  session_start:
    supported: true
    mode: native-hook
  before_mutation:
    supported: true
    mode: native-hook
  session_end:
    supported: true
    mode: native-hook
enforcement:
  profile: implementer
  strength: deterministic
writeback:
  automatic: true
  durable: true
  idempotent: true
coordination:
  conflicts_check: true
  claim_acquire: true
  claim_verify: true

This distinction is important:

* manifest = identity and integration;
* capabilities = behavioral guarantees.

Future peers can share the same capabilities even if their integration mechanism differs.

⸻

3. Define a peer-neutral lifecycle model

The framework must not expose Claude-specific events such as PreToolUse as the canonical abstraction.

Define normalized lifecycle events:

SESSION_INITIALIZING
SESSION_READY
OPERATION_PROPOSED
GOVERNED_MUTATION_PROPOSED
GOVERNED_BOUNDARY_PROPOSED
SESSION_FINALIZING
SESSION_ABORTED
DELIVERY_RETRY

Claude Code then maps native events into the normalized model:

SessionStart → SESSION_INITIALIZING
PreToolUse(Edit) → OPERATION_PROPOSED
PreToolUse(Bash git commit) → GOVERNED_BOUNDARY_PROPOSED
Stop → SESSION_FINALIZING

A future Codex adapter may map a wrapper command or process event into the same normalized events.

This is what makes the foundation reusable.

⸻

4. Build one shared lifecycle runner

Avoid implementing independent hook scripts per adapter.

Create a generic runner:

environment/agents/runtime/
├── lifecycle_runner.py
├── operation_classifier.py
├── policy_engine.py
├── context_collector.py
├── receipt_store.py
├── delivery_journal.py
├── cli_gateway.py
├── redaction.py
└── diagnostics.py

Surface-specific hooks should be extremely small:

from l9_adapter_runtime import handle_event
handle_event(
    adapter_id="claude-code",
    event="GOVERNED_BOUNDARY_PROPOSED",
    native_payload=payload,
)

The shared runner should own:

* schema validation;
* repository discovery;
* Git context;
* operation classification;
* policy lookup;
* CLI invocation;
* receipt handling;
* claim verification;
* durable ingestion;
* structured logging;
* failure-mode decisions.

A new peer should only need to provide:

1. manifest;
2. capabilities;
3. lifecycle-event mapping;
4. native installer;
5. bootstrap block.

⸻

5. Establish a strict adapter package layout

Use the same structure for every peer:

environment/agents/adapters/<adapter-id>/
├── adapter.yaml
├── capabilities.yaml
├── mcp.template.json
├── environment.env.example
├── agents-block.md
├── setup.md
├── README.md
├── mappings/
│   ├── lifecycle.yaml
│   └── operations.yaml
├── hooks/
│   └── native entrypoints only
└── tests/
    ├── manifest_test.*
    ├── mapping_test.*
    └── smoke_test.*

For Claude:

environment/agents/adapters/claude-code/

For peers:

environment/agents/adapters/codex/
environment/agents/adapters/gemini/
environment/agents/adapters/manus/
environment/agents/adapters/generic/

No peer should need its own memory/ implementation directory.

⸻

6. Treat l9-memory-mcp as a platform API

The CLI must be governed like a public internal API.

Required properties

* stable JSON output;
* versioned schemas;
* documented exit codes;
* non-interactive mode;
* request IDs;
* idempotency keys;
* hard timeouts;
* bounded output;
* explicit protocol negotiation;
* backward compatibility policy;
* machine-readable version command;
* machine-readable health check;
* deterministic configuration precedence.

Recommended command surface:

l9-memory-mcp hydrate
l9-memory-mcp conflicts check
l9-memory-mcp claim acquire
l9-memory-mcp claim verify
l9-memory-mcp claim release
l9-memory-mcp ingest
l9-memory-mcp doctor
l9-memory-mcp capabilities
l9-memory-mcp version

I would add claim release, doctor, and capabilities.

claim release prevents adapters from inventing implicit release behavior.

doctor validates connectivity, identity, protocol, and permissions.

capabilities allows the adapter runtime to verify that the deployed service supports required commands.

⸻

7. Make configuration precedence canonical

Every adapter must resolve configuration the same way.

Recommended precedence:

1. Explicit invocation override, where permitted
2. Adapter runtime environment
3. Rendered adapter configuration
4. Registry-derived defaults
5. Platform defaults

Identity should not be freely overrideable.

For example:

agent_id
user_id
source

must come from the registry-rendered adapter configuration and be confirmed by the authenticated server principal.

The runtime should reject inconsistent identity across:

* registry;
* manifest;
* environment;
* MCP template;
* CLI response;
* server principal.

⸻

8. Create policy profiles rather than per-agent policy

Do not encode policy under claude-code.

Define reusable profiles:

observer
reviewer
implementer
maintainer
orchestrator
administrator

Example:

profiles:
  implementer:
    hydration:
      required: true
    governed_operations:
      protected_root_edit:
        conflicts_check: required
        claim: required
        failure_mode: fail_closed
      git_commit:
        claim_verify: required
        failure_mode: fail_closed
      git_push:
        claim_verify: required
        failure_mode: fail_closed
      session_ingest:
        required: true
        failure_mode: durable_queue

Adapters reference a profile:

enforcement:
  profile: implementer

The registry can assign or constrain the profile.

This allows multiple peers to use identical governance without duplicating rules.

⸻

9. Make operation classification a first-class contract

This is a major regression risk.

The framework must classify effects, not just tool names.

Canonical categories:

READ_ONLY
LOCAL_NON_GOVERNED_MUTATION
GOVERNED_FILE_MUTATION
VERSION_CONTROL_COMMIT
VERSION_CONTROL_PUSH
VERSION_CONTROL_MERGE
PULL_REQUEST_CREATE
PULL_REQUEST_MERGE
AUTHORITY_PROMOTION
DESTRUCTIVE_MEMORY_OPERATION
UNKNOWN_POTENTIALLY_MUTATING

Each native surface maps commands and tool calls into these categories.

Unknown potentially mutating operations should not default to allowed.

For strict profiles:

UNKNOWN_POTENTIALLY_MUTATING → fail closed

The classifier should receive:

* tool type;
* command;
* arguments;
* current diff;
* target paths;
* repository state;
* native metadata.

It should return:

* classification;
* required controls;
* matched rules;
* confidence;
* unknown indicators.

⸻

10. Use a common session state machine

Define the state machine explicitly:

UNINITIALIZED
    ↓ hydrate
HYDRATED
    ↓ conflicts check
COORDINATED
    ↓ claim acquire
CLAIMED
    ↓ governed work
ACTIVE
    ↓ session finalizing
INGEST_PENDING
    ↓ ingest acknowledged
COMPLETE

Failure states:

DEGRADED_READ_ONLY
COORDINATION_UNAVAILABLE
CLAIM_EXPIRED
IDENTITY_INVALID
PROTOCOL_INCOMPATIBLE
INGEST_QUEUED
BREAK_GLASS

Every adapter must expose the same semantic states even if native UI differs.

State transitions should be validated. For example:

* UNINITIALIZED → CLAIMED is invalid.
* CLAIM_EXPIRED → git_push allowed is invalid.
* INGEST_QUEUED → COMPLETE requires acknowledgement.

⸻

11. Preserve only minimal local state

Local state should never become an alternate source of memory truth.

Allowed local state:

* session ID;
* hydration ID;
* claim ID;
* server-issued expiry;
* scope digest;
* repository and branch identity;
* pending ingest envelopes;
* acknowledgement records.

Disallowed locally authoritative state:

* conflict truth;
* “lock valid” Boolean;
* memory graph contents;
* local namespace ownership;
* independent claim interpretation;
* local authorization decisions not derived from policy.

All authority must be reverified through the shared CLI.

⸻

12. Define a portable state directory contract

All peers should use a standard state layout:

${L9_STATE_HOME:-${XDG_STATE_HOME}/l9}/
├── sessions/
│   └── <agent-id>/<session-id>.json
├── journal/
│   ├── pending/
│   ├── acknowledged/
│   └── failed/
├── audit/
└── locks/

Requirements:

* outside the repository;
* restrictive permissions;
* atomic writes;
* symlink rejection;
* bounded retention;
* cross-platform path abstraction;
* no token persistence;
* no hydrated memory contents by default.

This prevents each adapter from choosing its own unsafe location.

⸻

13. Build a reusable adapter SDK

The shared runtime should be packaged as an internal SDK.

Potential API:

from l9_agent_adapter import AdapterRuntime
runtime = AdapterRuntime.load("claude-code")
result = runtime.handle(
    event="GOVERNED_BOUNDARY_PROPOSED",
    payload=native_event,
)
raise SystemExit(result.exit_code)

Core interfaces:

class NativeEventMapper:
    def normalize(self, native_payload) -> LifecycleEvent: ...
class ContextProvider:
    def collect(self, event) -> RepositoryContext: ...
class OperationClassifier:
    def classify(self, event, context) -> OperationDecision: ...
class MemoryGateway:
    def hydrate(self, request) -> HydrationResult: ...
    def check_conflicts(self, request) -> ConflictResult: ...
    def acquire_claim(self, request) -> ClaimResult: ...
    def verify_claim(self, request) -> VerificationResult: ...
    def ingest(self, request) -> IngestResult: ...
class StateStore:
    def load_session(self, session_id): ...
    def persist_receipt(self, receipt): ...
    def enqueue_ingest(self, envelope): ...
class PolicyEngine:
    def evaluate(self, operation, capabilities, profile) -> PolicyDecision: ...

The MemoryGateway implementation invokes l9-memory-mcp; it does not implement MCP itself.

⸻

14. Build a reference conformance suite

Every adapter should be required to pass the same test kit.

environment/agents/conformance/
├── adapter_manifest_tests
├── identity_tests
├── lifecycle_tests
├── policy_tests
├── cli_contract_tests
├── state_machine_tests
├── security_tests
├── resilience_tests
├── observability_tests
└── end_to_end_tests

An adapter declares its supported capabilities, and the conformance suite derives mandatory tests.

Example:

capabilities.session_end.supported = true
capabilities.writeback.durable = true

automatically requires:

* stop ingestion test;
* timeout queue test;
* crash recovery test;
* duplicate ingestion test;
* next-session replay test.

This prevents adapters from claiming capabilities without proving them.

⸻

15. Create a reusable E2E harness

The E2E harness should be peer-neutral.

It should provision:

temporary Git repository
temporary bare remote
fake or ephemeral MCP service
two or more agent identities
real l9-memory-mcp CLI
real adapter runtime
surface simulator
structured event collector
fault injector

A scenario should be declared as data:

scenario: competing_implementers
agents:
  - id: claude-code
    profile: implementer
  - id: codex
    profile: implementer
steps:
  - agent: claude-code
    action: hydrate
  - agent: claude-code
    action: acquire_claim
    scope:
      - environment/**
  - agent: codex
    action: acquire_claim
    scope:
      - environment/agents/**
  - assert:
      agent: codex
      result: conflict
  - agent: claude-code
    action: release_claim
  - agent: codex
    action: acquire_claim
    expect: success

The same scenario must run against every adapter that claims implementer capability.

⸻

16. Test matrices, not isolated cases

Adapter matrix

Adapter	Hydration	Claims	Enforcement	Durable ingest
Claude Code	Required	Required	Native hook	Required
Codex	Required	Required	Wrapper/native	Required
Gemini	Required	By profile	Surface-specific	Required
Manus	Required	By profile	Surface-specific	Required
Generic	Required	Optional	Wrapper	Required

Platform matrix

* Linux;
* macOS;
* supported shells;
* repository path with spaces;
* worktrees;
* detached HEAD;
* shallow clone;
* no upstream branch;
* offline startup;
* token rotation.

Failure matrix

* authentication failure;
* identity mismatch;
* protocol mismatch;
* timeout;
* service outage;
* rate limit;
* malformed response;
* claim conflict;
* claim expiry;
* claim revocation;
* journal disk failure;
* corrupted receipt;
* duplicate event;
* process termination.

⸻

17. Add compatibility governance

You need explicit version compatibility across four things:

adapter contract version
adapter runtime version
l9-memory-mcp CLI version
memory service protocol version

Example manifest:

compatibility:
  adapter_contract: "1.x"
  runtime: ">=1.0.0 <2.0.0"
  cli: ">=1.4.0 <2.0.0"
  mcp_protocol:
    - "2026-06"
  memory_api:
    - "v1"

CI should test the minimum and current supported CLI versions.

Do not only test the newest version. That misses backward compatibility regressions.

⸻

18. Add architecture fitness functions

The repository should continuously enforce the intended architecture.

Examples:

AF-001: Only the shared CLI may access the memory endpoint.
AF-002: No adapter may implement an HTTP memory client.
AF-003: Every active adapter has adapter.yaml and capabilities.yaml.
AF-004: Every declared capability has required conformance tests.
AF-005: Identity must match across registry, adapter, and rendered config.
AF-006: No receipt stores hydrated content.
AF-007: No local state grants authority without server verification.
AF-008: Every ingest path supplies an idempotency key.
AF-009: Every governed boundary has an explicit failure mode.
AF-010: Unknown mutating operations fail according to profile policy.

These should be executable CI checks, not architecture prose.

⸻

19. Provide a generator for new adapters

To make the platform easily leverageable, add scaffolding:

make adapter-new ID=<adapter-id> SURFACE=<surface-type>

or:

python environment/agents/tools/create_adapter.py \
  --id new-agent \
  --surface cli-agent \
  --profile implementer

It should generate:

adapter.yaml
capabilities.yaml
mcp.template.json
environment.env.example
README.md
setup.md
agents-block.md
lifecycle mappings
operation mappings
baseline tests

The generated adapter should pass schema and structural validation immediately, while behavioral tests remain marked incomplete until implemented.

This reduces copy-paste divergence.

⸻

20. Publish a reference implementation guide

Create:

environment/agents/docs/REFERENCE_ADAPTER_ARCHITECTURE.md
environment/agents/docs/ADAPTER_IMPLEMENTATION_GUIDE.md
environment/agents/docs/ADAPTER_TESTING_STANDARD.md
environment/agents/docs/MEMORY_FAILURE_SEMANTICS.md
environment/agents/docs/IDENTITY_AND_AUTHORIZATION.md
environment/agents/docs/CLI_CONTRACT.md

The documentation should clearly distinguish:

* mandatory contract;
* recommended implementation;
* optional native capabilities;
* unsupported shortcuts;
* migration guidance;
* security considerations;
* E2E requirements.

⸻

21. Recommended repository structure

environment/agents/
├── agent_registry.yaml
│
├── contracts/
│   ├── adapter-manifest.schema.json
│   ├── adapter-capabilities.schema.json
│   ├── lifecycle-event.schema.json
│   ├── lifecycle-result.schema.json
│   ├── operation-classification.schema.json
│   ├── memory-session-receipt.schema.json
│   ├── memory-episode.schema.json
│   ├── delivery-journal-entry.schema.json
│   └── cli-response-envelope.schema.json
│
├── policy/
│   ├── profiles.yaml
│   ├── operations.yaml
│   └── protected-scopes.yaml
│
├── runtime/
│   ├── lifecycle_runner.py
│   ├── operation_classifier.py
│   ├── policy_engine.py
│   ├── context_collector.py
│   ├── cli_gateway.py
│   ├── receipt_store.py
│   ├── delivery_journal.py
│   ├── redaction.py
│   └── diagnostics.py
│
├── adapters/
│   ├── claude-code/
│   ├── codex/
│   ├── gemini/
│   ├── manus/
│   └── generic/
│
├── conformance/
│   ├── schemas/
│   ├── identity/
│   ├── lifecycle/
│   ├── policy/
│   ├── security/
│   ├── resilience/
│   └── e2e/
│
├── tools/
│   ├── validate_agents.py
│   ├── create_adapter.py
│   ├── render_adapter.py
│   └── adapter_doctor.py
│
└── docs/
    ├── REFERENCE_ADAPTER_ARCHITECTURE.md
    ├── ADAPTER_CONTRACT.md
    ├── ADAPTER_IMPLEMENTATION_GUIDE.md
    ├── ADAPTER_TESTING_STANDARD.md
    ├── CLI_CONTRACT.md
    ├── MEMORY_FAILURE_SEMANTICS.md
    └── IDENTITY_AND_AUTHORIZATION.md

⸻

22. Delivery plan

I would split delivery into four architectural milestones.

Milestone 1 — Platform contracts

Deliver:

* schemas;
* lifecycle model;
* capability model;
* policy profiles;
* CLI contract;
* failure taxonomy;
* identity rules;
* architecture fitness functions.

No adapter cutover yet.

Milestone 2 — Shared runtime

Deliver:

* lifecycle runner;
* CLI gateway;
* state machine;
* journal;
* policy engine;
* classifier;
* conformance harness;
* E2E infrastructure.

Run against a synthetic test adapter.

Milestone 3 — Claude reference adapter

Deliver:

* Claude manifest and capabilities;
* native event mappings;
* hook entrypoints;
* shadow migration;
* regression fixtures;
* production canary;
* operational rollback.

Only after this passes should Claude’s bespoke pipeline be deleted.

Milestone 4 — Peer adoption

Migrate peers one at a time using the same framework.

For each peer:

declare capabilities
map native events
run conformance suite
run shared E2E scenarios
shadow where possible
enable enforcement profile
remove divergent integration

⸻

23. Definition of done

This foundation is complete only when:

* a new adapter can be generated without copying another adapter;
* the adapter contract is schema-defined;
* declared capabilities automatically select required tests;
* all adapters invoke the same shared CLI;
* no adapter implements memory transport;
* no adapter implements conflict or claim semantics;
* policy profiles are shared;
* lifecycle events are normalized;
* identity is server-bound and registry-consistent;
* claims are reverified at irreversible boundaries;
* writeback is durable and idempotent;
* all failure modes are explicit;
* the E2E harness supports multiple identities and adapters;
* architecture fitness functions prevent divergence;
* Claude passes the reference conformance suite;
* at least one second peer can be integrated without modifying the core runtime.

That final criterion is essential:

The platform is not proven reusable until a second adapter is implemented without changing the shared runtime or schemas.

Claude Code should be the first certification target, not the shape of the platform.
——