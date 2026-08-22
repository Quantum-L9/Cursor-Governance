Yes. I would lock this down as an executable Session Admission Protocol, not documentation.

The repo is already structurally close to supporting it: Peer Execution Core is defined as the shared owner of context manifests, capability-receipt freshness, lifecycle mechanics, budgets and readiness evaluation, while provider adapters are explicitly forbidden from owning memory, context policy, autonomy or Program state.  That is exactly where this should attach.

The missing piece is:

No session or autonomous PE worker is considered execution-ready until a canonical, machine-verifiable Session Readiness Receipt exists.

Target architecture

                   L9 SESSION ADMISSION CONTROL PLANE
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  Cursor / Claude / Codex / Gemini / Manus / future LLM              │
│                    thin surface carrier                               │
│                            │                                          │
│                            ▼                                          │
│                  Canonical Session Boot Core                          │
│                   stdlib-only critical path                           │
│                            │                                          │
│       ┌────────────────────┼────────────────────────┐                 │
│       ▼                    ▼                        ▼                 │
│  Identity/Repo        Governance State         Capability Probe       │
│       │                    │                        │                 │
│       ├─────────────┬──────┴───────┬────────────────┤                │
│       ▼             ▼              ▼                ▼                │
│  PE Program      Continuity     Repo Memory      Workspace           │
│  State           Capsule        / Decisions      Context             │
│  AUTHORITATIVE   EXACT           SELECTIVE        SELECTIVE          │
│       │             │              │                │                │
│       └─────────────┴──────────────┴────────────────┘                │
│                            │                                          │
│                            ▼                                          │
│                  Hydration / Context Compiler                         │
│                            │                                          │
│             ┌──────────────┼──────────────┐                           │
│             ▼              ▼              ▼                           │
│       Model Context   Operator Status   Machine Receipt               │
│       ~400-800 tok    optional display  mandatory JSON                │
│                            │                                          │
└────────────────────────────┼───────────────────────────────────────────┘
                             ▼
                    SESSION READINESS GATE
                             │
                 ┌───────────┴────────────┐
                 ▼                        ▼
          interactive session       PE autonomous admission
                                         │
                                         ▼
                                  Program Controller
                                         │
                                  Peer Execution Core
                                         │
                                   thin provider

The important change is that native sessionStart hooks become carriers, not authorities.

Today session_start_bootstrap.sh directly accumulates textual status fragments, runs Graphiti health/memory orchestration and finally emits env plus additional_context; the memory orchestrator similarly turns hydration results into markdown/text.  I would reduce those scripts to thin wrappers around one canonical boot executable.

⸻

1. Create a first-class Session Contract family

I would add:

environment/contracts/session/
├── MANIFEST.yaml
├── schemas/
│   ├── session_boot_request.schema.json
│   ├── hydration_receipt.schema.json
│   ├── context_manifest.schema.json
│   ├── session_readiness_receipt.schema.json
│   └── surface_boot_capability.schema.json
├── policies/
│   └── readiness-policy.json
└── fixtures/
    ├── healthy/
    ├── memory-timeout/
    ├── stale-cache/
    ├── ambiguous-repo/
    ├── provider-blocked/
    └── autonomy-blocked/

And canonical implementation:

ops/session_runtime/
├── cli.py
├── boot.py
├── identity.py
├── probes.py
├── hydration.py
├── context_compiler.py
├── readiness.py
├── receipts.py
├── status_renderer.py
├── cache.py
└── tests/

Critical boot code should be stdlib-only.

No mandatory:

pydantic
PyYAML
uv
langgraph
provider SDK

Those can exist elsewhere, but an unavailable development venv must never make the agent cognitively blind again.

⸻

2. Make the receipt mandatory; display optional

Every startup produces:

$L9_RUNTIME_ROOT/sessions/<session_id>/
├── boot-request.json
├── hydration-receipt.json
├── context-manifest.json
├── model-context.md
└── session-readiness.json

The human status report can be:

off
compact
verbose
failure-only

But session-readiness.json always exists.

Example:

{
  "schema": "l9.session-readiness.v1",
  "session_id": "01J...",
  "created_at": "2026-08-15T16:20:00Z",
  "expires_at": "2026-08-15T16:50:00Z",
  "identity": {
    "agent_ref": "claude-code",
    "surface": "claude-web",
    "provider_ref": "claude-code-direct"
  },
  "workspace": {
    "repository": "Quantum-L9/Cursor-Governance",
    "group_id": "cursor-governance",
    "branch": "feature/memory-v2",
    "head_at_boot": "7ebf331..."
  },
  "governance": {
    "status": "PASS",
    "commit": "abc...",
    "law_digest": "sha256:...",
    "agent_registry_digest": "sha256:...",
    "runtime_bindings_digest": "sha256:..."
  },
  "hydration": {
    "status": "PASS",
    "receipt_ref": "hydration-receipt.json",
    "context_manifest_ref": "context-manifest.json",
    "context_digest": "sha256:...",
    "tokens_injected": 537
  },
  "peer_execution": {
    "binding": "READY",
    "autonomous_execution": true,
    "capability_receipt_ref": "...",
    "execution_profile": "worker-default"
  },
  "autonomy": {
    "status": "READY",
    "profile": "l4_local_autonomy",
    "profile_digest": "sha256:...",
    "remote_write": "DENY_UNTIL_RELEASE_AUTHORIZED"
  },
  "fallbacks": [],
  "decision": "READY_PE_AUTONOMOUS",
  "receipt_digest": "sha256:..."
}

No provider gets to invent this receipt.

The shared core authors it, consistent with the existing law that canonical receipts and readiness belong above the provider layer. 

⸻

3. Define hydration completeness mechanically

I would define required lanes:

LANE 0  repository_identity
LANE 1  governance_runtime
LANE 2  program_execution_state
LANE 3  continuity
LANE 4  repo_knowledge
LANE 5  workspace_context
LANE 6  governance_memory_delta
LANE 7  provider_capabilities
LANE 8  autonomy_state

Every lane must finish in exactly one state:

PASS
EMPTY
SKIPPED_POLICY
FALLBACK_FRESH
FALLBACK_STALE
DEGRADED
FAILED
BLOCKED

Therefore:

facts = []

is no longer an acceptable result by itself.

You get:

{
  "lane": "repo_knowledge",
  "state": "EMPTY",
  "source": "graphiti",
  "reason": "query_succeeded_no_relevant_candidates"
}

versus:

{
  "lane": "repo_knowledge",
  "state": "FALLBACK_FRESH",
  "primary_failure": "mcp_timeout",
  "source": "compiled_cache",
  "age_seconds": 181
}

That gives you the visibility you want and makes completeness machine-testable.

⸻

4. PE state must outrank memory state

This is especially important for autonomous execution.

An active Program must hydrate from the Program Controller, not from semantic memory.

Program Controller
    ↓
active program
Program Lock
ready tasks
leases
current wave
verification state
Graphiti
    ↓
why we made decisions
recent lessons
prior session continuity
historical context

Your executable-plan contract already explicitly says Graphiti PICKUP is observability and must never become a competing task claim. 

So the model should see something like:

EXECUTION STATE · authoritative
Program: pes-memory-runtime
Lock: 81f2…
Wave: W1
Ready task: TASK-004
Lease: unclaimed
SESSION CONTINUITY · memory
Previous objective: Harden hydration
Previous next action: Add receipt contracts

A stale PICKUP can never override the PE Controller.

⸻

5. Add Gate 0: Session Admission to PE

PE currently already has binding readiness and exact Program-Lock-bound provider capability readiness. 

Make the sequence:

GATE 0 — SESSION READY
    ↓
GATE A — BINDING READY
    ↓
GATE B — EXACT PROGRAM CONTRACT READY
    ↓
PROGRAM CLAIM
    ↓
DISPATCH

Gate 0 validates:

✓ identity resolved
✓ repository unambiguous
✓ governance integrity valid
✓ required hydration lanes accounted for
✓ context manifest valid
✓ autonomous execution allowed on this surface
✓ autonomy profile valid
✓ receipt fresh
✓ no forbidden fallback

Then PE admission becomes roughly:

receipt = load_session_readiness(session_id)
validate_digest(receipt)
validate_freshness(receipt)
if receipt["decision"] != "READY_PE_AUTONOMOUS":
    raise AdmissionBlocked(
        code="SESSION_NOT_AUTONOMY_READY",
        receipt_ref=receipt_path,
    )

The LLM cannot talk its way around this.

⸻

6. Never depend on native SessionStart for autonomous PE

This is what gives you true cross-platform uniformity.

Some platforms have excellent lifecycle hooks. Others have limited or evolving lifecycle support. Your own current registry/topology already distinguishes required execution bindings: Cursor and Claude are currently required while Codex, Gemini and Manus bindings are presently not required. 

So use two entry paths into the same boot core:

Interactive user session
native SessionStart
        │
        ▼
canonical boot()
PE autonomous worker
Peer Execution Core
        │
        ▼
canonical ensure_ready()

For an autonomous worker:

receipt = ensure_session_ready(
    agent_ref=agent_ref,
    surface=surface,
    workspace=worktree,
    required_mode="pe_autonomous",
)

If a provider never fired a SessionStart hook:

no problem

PE invokes boot before admission.

If the hook already ran:

fresh receipt → cache hit → milliseconds

Thus autonomous correctness is independent of host hook behavior.

⸻

7. Give autonomous workers a smaller context than operator sessions

Do not send every PE worker the entire interactive session.

The worker gets:

Rendered Contract
+ Worker Brief
+ exact PE state
+ task-specific memory
+ necessary repository anchors

Not:

entire transcript
all recent memories
all governance prose
all workspace facts

The existing PE architecture already makes context-manifest construction a Peer Execution Core concern. 

I would introduce:

{
  "schema": "l9.context-manifest.v1",
  "budget_tokens": 1800,
  "items": [
    {
      "kind": "rendered_contract",
      "authority": 100,
      "tokens": 620,
      "required": true
    },
    {
      "kind": "program_state",
      "authority": 100,
      "tokens": 160,
      "required": true
    },
    {
      "kind": "continuity",
      "authority": 60,
      "tokens": 110,
      "required": false
    },
    {
      "kind": "decision",
      "memory_id": "m:...",
      "tokens": 75,
      "score": 0.91
    }
  ],
  "selected_tokens": 965,
  "context_digest": "sha256:..."
}

Machine validation rejects a manifest that exceeds the execution profile’s budget.

⸻

8. Enforce semantic parity across LLMs

Uniform does not mean every provider receives byte-identical host syntax.

It means:

Given identical canonical inputs, every adapter receives the same semantic execution context.

Test it.

Fixture:

repo = Cursor-Governance
HEAD = X
agent capability set = Y
memory snapshot = Z
Program state = P

Compile for:

cursor-ide
claude-cli
claude-web
claude-mobile
codex-cli
codex-cloud
gemini-cli
manus-cloud

Normalize the carrier output.

Then assert:

context_manifest_digest is identical
required authority items are identical
Program state is identical
memory selection is identical
autonomy decision is identical

Provider-specific formatting may differ.

Semantic digest may not.

That is how you prevent “Claude knew it but Codex didn’t.”

⸻

9. Extend runtime bindings with autonomous capability requirements

Do not merely say an agent is active.

Declare what execution level it must prove:

claude-code:
  execution:
    required: true
    required_modes:
      - interactive
      - pe_worker
      - pe_autonomous
codex:
  execution:
    required: true
    required_modes:
      - pe_worker
      - pe_autonomous
gemini:
  execution:
    required: true
    required_modes:
      - verification
      - pe_autonomous
manus:
  execution:
    required: true
    required_modes:
      - research
      - pe_autonomous

But autonomous capability does not widen authority.

For example:

Gemini reviewer
    PE autonomous = YES
    repository write authority = NO
Claude implementer
    PE autonomous = YES
    scoped mutation under lease = YES
Manus researcher
    PE autonomous = YES
    deploy authority = NO

Your current identity registry already separates orchestrator, implementer, researcher-builder, reviewer and observer authority. 

Uniform runtime ≠ uniform permissions.

⸻

10. Bind the autonomy profile into the receipt

The current autonomy surface profile already governs Claude, Codex, Gemini and Manus, while L4 local autonomy mechanically denies remote actions until release authorization. 

Do not merely inject that as prose.

Hash it:

autonomy_profile_digest = sha256(canonical profile)

Then put that digest into:

SessionReadinessReceipt
CanonicalExecutionRequest
AttemptReceipt

Now you can prove:

This execution ran under exactly this autonomy contract.

If the autonomy profile changes:

old readiness receipt → invalid

Refresh required.

⸻

11. The operator status becomes trivial

Because it renders from the receipt:

L9 SESSION · READY_PE_AUTONOMOUS
──────────────────────────────────────────
Agent          claude-code
Surface        claude-web
Repo           Cursor-Governance
Branch         feature/memory-v2
Governance     ✓ PASS
Memory         ✓ PASS
PE binding     ✓ READY · claude-code-direct
Autonomy       ✓ READY · L4 local
Program        ✓ pes-memory-v2 · W1
Continuity     ✓ ResumeCapsule · fresh 12m
Repo memory    ✓ 4 selected / 23 candidates
Workspace      ! cache fallback · 3m old
Context        ✓ 537 / 800 tokens
Fallbacks      1
Receipt        sr_01J... · valid 27m
──────────────────────────────────────────
Autonomous PE  ✓ ADMITTED
Remote writes  ✗ denied until release_authorized

And:

l9 session status
l9 session status --json
l9 session status --verbose

The pretty output is optional.

The JSON is law.

⸻

12. Add hard machine gates

I would add these Make targets:

session-contracts-validate:
	python3 -B ops/session_runtime/validate_contracts.py
session-tests:
	python3 -B -m unittest discover ops/session_runtime/tests
session-conformance:
	python3 -B ops/session_runtime/run_conformance.py
session-probe:
	python3 -B -m ops.session_runtime.cli probe --workspace "$(WS)"
session-status:
	python3 -B -m ops.session_runtime.cli status --workspace "$(WS)"
session-autonomy-ready:
	python3 -B -m ops.session_runtime.cli gate \
		--workspace "$(WS)" \
		--require pe-autonomous

Then change:

peer-execution-conformance:

to depend on:

session-contracts-validate
session-conformance
agents-env
agents-runtime-bindings-validate
program-execution-adapters
program-execution-conformance
peer-execution-validate
peer-execution-probe

The repo already composes agent identity, runtime bindings, PE adapter/conformance, readiness probes and autonomy validation through Make targets, so this extends the existing executable-governance pattern rather than creating a separate testing philosophy. 

⸻

13. Conformance rules I would make merge-blocking

At least these:

SESSION-001  every active surface has a canonical boot carrier
SESSION-002  carrier calls shared core; no copied boot brain
SESSION-003  boot critical path succeeds without pydantic/PyYAML
SESSION-004  repository identity is deterministic
SESSION-005  every hydration lane reports explicit state
SESSION-006  EMPTY cannot represent transport failure
SESSION-007  fallback source + age are always recorded
SESSION-008  context respects token budget
SESSION-009  operator telemetry is excluded from model context
SESSION-010  identical fixture → identical semantic context digest
SESSION-011  PE state outranks Graphiti continuity
SESSION-012  autonomous PE requires fresh readiness receipt
SESSION-013  provider cannot author readiness receipt
SESSION-014  autonomy profile digest binds execution
SESSION-015  missing required capability → BLOCKED, never emulated
SESSION-016  ambiguous repo → autonomous PE BLOCKED
SESSION-017  failed memory + no approved fallback → autonomy BLOCKED
SESSION-018  stale receipt → automatic rebootstrap
SESSION-019  adapter can be removed without changing core
SESSION-020  all required PE surfaces prove autonomous mode

The existing thin-adapter law already requires declared/probed capabilities and says missing capabilities must degrade to unsupported or blocked rather than hidden emulation. 

⸻

14. Run fault-injection, not just happy-path tests

Every surface should pass the same scenario matrix:

Graphiti healthy
Graphiti timeout
Graphiti 401
malformed MCP response
no pydantic
no PyYAML
no .venv
stale ResumeCapsule
ambiguous repository
wrong memory group
provider unavailable
provider capability drift
autonomy profile drift
Program Lock stale
dirty worktree overlap
receipt expired
cache corrupt
network disconnected

Expected output must be machine asserted:

READY_PE_AUTONOMOUS
READY_INTERACTIVE
DEGRADED_SAFE
BLOCKED_PE
BLOCKED_SESSION

Never:

"probably okay"

⸻

15. Also hydrate on compaction/re-entry

SessionStart alone is insufficient for long autonomous sessions.

Use the same compiler at:

SessionStart
PreCompact / equivalent
post-compaction
provider reconnect
PE dispatch
Program Lock refresh
explicit `l9 session refresh`

Every refresh increments:

hydration_epoch

So the receipt might say:

{
  "session_id": "abc",
  "hydration_epoch": 4,
  "previous_receipt_digest": "sha256:...",
  "reason": "precompact"
}

You get a receipt chain rather than silently losing state after context compression.

⸻

The invariant I would put in Canonical Law

Conceptually:

No autonomous Program Execution admission without a fresh canonical Session Readiness Receipt. Every active execution surface MUST consume the same adapter-neutral session boot, hydration, context-compilation, capability, and autonomy contracts. Surface adapters MAY translate transport and presentation only; they MUST NOT own or fork session semantics. All required hydration lanes MUST terminate in machine-readable states, all fallbacks MUST be explicit, and the operator-status projection MUST derive exclusively from the canonical receipt.

That aligns with the repository’s existing “one Program Controller, one peer execution substrate, thin adapters, zero copied brains” model. 

End state

What you ultimately want is:

Open Cursor
→ READY_PE_AUTONOMOUS
Open Claude CLI
→ READY_PE_AUTONOMOUS
Open Claude Web
→ READY_PE_AUTONOMOUS
Open Claude Mobile
→ READY_PE_AUTONOMOUS
Start Codex
→ READY_PE_AUTONOMOUS
Start Gemini
→ READY_PE_AUTONOMOUS within reviewer authority
Start Manus
→ READY_PE_AUTONOMOUS within researcher authority

And if any one of them is not equivalent:

L9 SESSION · BLOCKED_PE
FAIL: hydration.continuity
  Graphiti: timeout
  cache: expired
PASS: governance
PASS: Program Controller
PASS: autonomy
PASS: provider
Autonomous PE admission: DENIED
Interactive session: ALLOWED
Receipt: ~/.l9/.../session-readiness.json

No blindness, no implicit fallback, no provider-specific memory behavior, no prose-only enforcement, and no autonomous execution from a half-hydrated cognitive state.

That is the architecture I would make the next layer above the current memory patch.