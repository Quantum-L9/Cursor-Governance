Deep audit verdict

The system is now close enough that the remaining work should be treated as boundary convergence, not another redesign.

The strongest correction to both the peer plan and my previous plan is this:

The agent-facing capability plane should terminate at l9-graphiti-memory, not at upstream Graphiti MCP.

That is the cleanest architecture because l9-graphiti-memory explicitly owns canonical memory persistence, authorization, normalization, idempotency, retrieval planning, typed receipts, and projection integration. Graphiti is downstream projection infrastructure, not the memory API agents should conceptually depend on. 

My previous plan still let the capability broker become a Graphiti MCP transport implementation. That would work mechanically, but it would duplicate transport semantics and preserve the wrong dependency direction:

Agent
  ↓
Capability Broker
  ↓
Graphiti MCP

The better end state is:

Agent
  ↓
L9 capability
  ↓
trusted capability broker / runtime gateway
  ↓
l9-graphiti-memory MCP/API
  ↓
MemoryPrincipal
  ↓
MemoryService
  ↓
RecordStore
  ↓
durable projection outbox
  ↓
Graphiti / Zep

That gives you one canonical memory API and one secret boundary.

l9-graphiti-memory already documents exactly this flow: all CLI/MCP/importer inputs go through MemoryPrincipal → MemoryService, and MemoryService owns authorization, normalization, validation, idempotency, atomic commit, typed receipts, and the canonical RecordStore; Graphiti/Zep sit after a durable outbox as optional projections. 

That architectural change simplifies almost every remaining problem.

⸻

What the deeper audit changes

Area	Previous plan	Hardened conclusion
Agent memory capability	graphiti.query	Canonical capability should be memory-level, backed by l9-graphiti-memory
Graphiti MCP handshake	Capability broker implements it	Projection adapter/service owns it, not agent runtime
Graphiti bearer	Broker may possess	Prefer projection worker / memory service possession only
Hydration planner	Replace in Cursor-Governance	Reuse l9-graphiti-memory retrieval + budget primitives
ResumeCapsule	Possibly memory-package-owned	Runtime owns schema/lifecycle; MemoryService persists it
Governance ingestion	Good direction	Keep; make source-preserving publication primary
Governance distillation	Optional	Keep strictly derivative/non-authoritative
Context digest equality	Same across agents	Canonical HydrationManifest digest same; rendered model projection may differ by surface
Session readiness	One READY flag	Separate interactive, governed, autonomous readiness
Enforcement	Rules through memory	Memory makes policy available; capability/runtime gates enforce it
Graphiti health	Required for memory correctness	Projection health separate from canonical-memory health
Close pipeline	Async distillation	Also make canonical checkpoint commit the acknowledgment boundary

There are also two places where the system already has more than the plan credited it for.

First, l9-graphiti-memory already has a token-budget allocator. It class-prioritizes constraints and decisions, estimates tokens, packs complete atomic records, tracks token budget/use, and emits a deterministic hydration digest.  So building another context-budget implementation inside Cursor-Governance would be duplicate ownership.

Second, ProfileIngestor.behavior() already maps policy into MemoryClass.CONSTRAINT with a stable policy_id, provenance, evidence, metadata, and deterministic idempotency key.  That is almost exactly the primitive needed for distilled/structured governance rules.

The architecture-alignment and execution kernels both strongly favor correcting duplicated ownership at the authoritative boundary rather than layering another local implementation over it. 

⸻

Remaining verified defects

The legacy Cursor-Governance hydration path is definitely still bypassing the canonical architecture. compile_session_packet.py directly imports graphiti_memory_client, calls gmc.load_env(), searches Graphiti itself, semantically guesses PICKUP, suppresses reads when the repo is readonly, and uses a character budget. 

The direct client also still obtains GRAPHITI_MCP_TOKEN from process environment and constructs the upstream Authorization header itself. 

The desktop loader is an explicit secret side door: it can retrieve the graphiti-mcp-token macOS Keychain entry and place the result into os.environ["GRAPHITI_MCP_TOKEN"]. 

The old Graphiti client also proves why the broker should not generically proxy Graphiti: the deployed provider requires MCP initialize, Mcp-Session-Id, then session-bound tools/call, and can return SSE rather than simple JSON.  That protocol complexity belongs behind the memory-control-plane boundary.

Session close remains the other major bypass. It directly imports graphiti_memory_client, constructs timestamp-named episodes, calls add_memory, and then performs inline Phase-B LLM work.  This contradicts the more mature MemoryService → canonical RecordStore → outbox → projections architecture.

So the root problem is not merely “the broker isn’t wired.”

It is:

Cursor-Governance still contains an older complete memory lifecycle
while
l9-graphiti-memory now owns the canonical memory lifecycle.

That duplicated responsibility is the actual convergence target.

⸻

Hardened target architecture

┌──────────────────────────────────────────────────────────────┐
│                    AUTHORITATIVE SOURCES                     │
│                                                              │
│ Cursor-Governance                    Runtime/PE control plane │
│ ├─ CANONICAL_LAW.md                  ├─ Program state         │
│ ├─ ORG_INVARIANTS                    ├─ ResumeCapsule schema  │
│ ├─ RULES-MANIFEST                    ├─ repo identity         │
│ └─ manifest-member rules             └─ autonomy state        │
└───────────────────┬──────────────────────────┬───────────────┘
                    │                          │
            governance ingest          session checkpoint
                    │                          │
                    ▼                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  l9-graphiti-memory                          │
│                                                              │
│ MemoryPrincipal                                              │
│       ↓                                                      │
│ MemoryService                                                │
│ ├─ authz                                                     │
│ ├─ normalization                                             │
│ ├─ validation                                                │
│ ├─ provenance                                                │
│ ├─ idempotency                                               │
│ ├─ canonical search                                          │
│ ├─ hydration                                                 │
│ └─ atomic commit                                             │
│       ↓                                                      │
│ RecordStore  ← CANONICAL MEMORY                              │
│       │                                                      │
│       └── durable projection outbox                          │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    ▼
             Graphiti / Zep
          rebuildable projection

Runtime:

Agent session
    │
    ▼
trusted bootstrap / broker identity
    │
    ▼
memory.query / memory.hydrate
    │
    ▼
l9-graphiti-memory
    │
    ├── governance namespace
    ├── exact ResumeCapsule
    ├── repository namespace
    └── episodic context
    │
    ▼
HydrationManifest
    │
    ├── Operator HydrationReceipt
    │
    └── Surface ModelProjection
                │
                ▼
        SessionReadinessReceipt
                │
                ▼
             PE Gate 0

The important boundary is that governance accessibility and governance enforcement remain separate.

Memory supplies:

what the agent needs to know

Capability/runtime/PE gates enforce:

what the agent is actually allowed to do

An agent forgetting a rule must never create authority to bypass the rule.

⸻

Build-ready convergence program

I would reduce the previous ten milestones into seven dependency-ordered releases. This is safer, simpler, and produces usable checkpoints after every stage.

1. Release A — Prove canonical memory and freeze legacy behavior

Bind exact SHAs for both repositories and run baseline validation before changing anything.

For l9-graphiti-memory, prove standalone canonical operation with the projection disabled:

uv sync --frozen --no-install-project --no-build --extra dev --extra server
source .venv/bin/activate
export L9_MEMORY_PROJECTION_BACKEND=none
l9-memory resolve
l9-memory health
l9-memory write \
  'L9 canonical memory baseline marker' \
  --kind observation \
  --group-id l9-memory-baseline \
  --source operator
l9-memory search \
  'L9 canonical memory baseline marker' \
  --group-id l9-memory-baseline
bash scripts/validate_release.sh

The runbook explicitly says standalone mode requires no external credentials and that a partial result means canonical success with an optional strategy failure; a failed result means canonical failure. It also warns never to treat those as an empty successful result. 

For Cursor-Governance:

make rules-stabilize
make pr-check
make rules-stabilize

The second stabilization must produce no new material diff.

Release A exits only when canonical memory and the governance rule publication inputs are proven green.

⸻

2. Release B — Establish one canonical agent-memory capability

This is where I would improve most strongly on the other plan.

Do not make the broker itself implement upstream Graphiti MCP.

Define the canonical capability contract conceptually as:

memory.search
memory.hydrate
memory.write_governed
memory.close
memory.health

If graphiti.query and graphiti.write_governed already have high-fanout consumers, retain them temporarily as compatibility aliases:

graphiti.query
    → memory.search
graphiti.write_governed
    → memory.write_governed

They must terminate at l9-graphiti-memory, not directly at Graphiti.

The runtime trust boundary becomes:

model process
   │
   │ no downstream credential
   ▼
broker / trusted runtime
   │
   │ authenticated memory principal
   ▼
l9-graphiti-memory

Graphiti provider credentials live downstream of this boundary.

Acceptance:

model_has_graphiti_bearer: false
model_can_read_keychain_graphiti_token: false
memory_service_authentication: PASS
memory_search: PASS
memory_hydrate: PASS
memory_write_governed: PASS
provider_projection_optional: true

Only once this works do you remove model-side direct Graphiti access.

⸻

3. Release C — Governance publication

Add GovernanceBootstrapper to l9-graphiti-memory.

Its input authority is:

Cursor-Governance exact Git SHA
CANONICAL_LAW.md
ORG_INVARIANTS if current contract says applicable
RULES-MANIFEST.json
manifest-member rules only

The publication compiler must not define membership by scanning rules/*.mdc.

For every manifest rule:

manifest entry
   ↓
exact source path
   ↓
path containment
   ↓
frontmatter/schema parse
   ↓
manifest id == rule id
   ↓
manifest digest == source digest
   ↓
source-preserving record
   ↓
MemoryService.write()

The global namespace should be:

l9-governance

and its permission matrix should be:

governance-publisher:
    read/write l9-governance
Cursor:
    read l9-governance
    no write l9-governance
Claude:
    read l9-governance
    no write l9-governance
Codex/Gemini/Manus:
    read l9-governance
    no write l9-governance

Use source-preserving ingestion as the normative representation.

Optional searchable atoms may then reuse ProfileIngestor.behavior() / SourceDistiller; ProfileIngestor.behavior() already expresses policy as a CONSTRAINT with stable policy identity and deterministic idempotency, while SourceDistiller already submits evidence-bound derived candidates through MemoryService. 

Derived atoms must carry:

derived_from = canonical source record
authoritative = false

They cannot supersede the underlying policy text.

Controlled rollout:

CANONICAL_LAW
+
Graphiti/memory rule
+
memory-write rule
+
git-mutation rule

Dry-run twice, require equality, publish twice, require idempotent second receipts.

Only then permit full-corpus publication.

⸻

4. Release D — Replace Cursor-Governance hydration with canonical hydration

Do not write a new retrieval engine in compile_session_packet.py.

Move the actual memory search/budget work to l9-graphiti-memory, where the architecture already says retrieval planning belongs. 

It already has a ContextBudgetAllocator with class-aware ordering, token estimates, complete-record packing, token accounting, and a deterministic result digest. 

Cursor-Governance should own session composition, not memory retrieval algorithms.

The desired separation is:

Cursor-Governance
    identify:
      agent
      repo
      program
      campaign
      current task
      desired namespaces
          ↓ request
l9-graphiti-memory
    authorize namespaces
    retrieve
    classify
    budget
    return HydrationResult + receipts
          ↓ compose
Cursor-Governance
    bind ResumeCapsule
    bind runtime-env receipt
    create ContextManifest
    create SessionReadinessReceipt

This removes:

gmc.load_env()
direct Graphiti call_tool()
fuzzy PICKUP queries
readonly read suppression
character budget
Graphiti-specific parsing

from compile_session_packet.py.

Readonly becomes:

write policy only

Memory reads remain governed by namespace claims.

⸻

5. Release E — Exact continuation + context/telemetry separation

This release introduces the missing deterministic continuity contract.

The ResumeCapsule should be owned by Cursor-Governance/runtime, because l9-graphiti-memory explicitly says it does not own full agent checkpoint persistence. 

But the capsule should be persisted through MemoryService.

A capsule should have deterministic identity derived from at least:

repository identity
session lineage
program/campaign identity
source-head/transcript digest
schema version

It should contain only continuity essentials:

objective
next_action
blockers
critical working-state anchors
repo identity
program identity
producing agent
created_at
source digest

SessionStart must select the latest valid capsule through exact typed identity/state—not semantic retrieval.

Semantic search becomes supplemental context only.

Then produce two different outputs:

HydrationReceipt
    operator/control-plane diagnostics
ModelProjection
    cognition

The model sees:

objective
next action
blockers
essential governance constraints
high-value repository facts
selected episodic facts

It does not see:

packet IDs
backend names
query counts
provider error telemetry
budget internals
receipt JSON
duplicate stats

unless explicitly debugging memory.

A canonical HydrationManifest should be identical across agents.

A surface rendering may differ:

canonical_manifest_digest = identical
cursor_model_projection_digest
claude_model_projection_digest
codex_model_projection_digest
    = allowed to differ

That is stronger than requiring byte-identical model context across heterogeneous surfaces.

⸻

6. Release F — Session readiness and deterministic close

Create one session-admission state machine:

ExecutablePeerReadiness
+
RuntimeEnvironmentReceipt
+
HydrationReceipt
+
HydrationManifest
+
ResumeCapsule status
+
repo identity
+
governance freshness
+
capability state
+
autonomy state
=
SessionReadinessReceipt

Use explicit readiness classes:

READY_INTERACTIVE
READY_GOVERNED
READY_PE_AUTONOMOUS
DEGRADED
BLOCKED

That is better than a single binary readiness bit.

READY_PE_AUTONOMOUS requires all of:

exact repo identity
current governance publication
fresh ResumeCapsule or explicit fresh-start state
required memory namespaces readable
all campaign-required capabilities available
context manifest valid
autonomy profile valid
peer-execution binding valid
receipt within TTL

A failed memory projection does not automatically block if canonical memory is healthy and the retrieval plan still succeeds.

A failed canonical memory lane does.

Plain Anthropic-hosted Web/Mobile without broker identity cannot receive READY_PE_AUTONOMOUS. The system should honestly report degraded/interactive rather than reintroducing static secrets.

Session close then becomes:

sessionEnd
   ↓
build deterministic ResumeCapsule
   ↓
canonical MemoryService commit
   +
durable async-work obligation
   ↓
receipt
   ↓
return

Afterward:

worker
   ├── SourceDistiller / session distillation
   ├── lesson promotion
   ├── semantic enrichment
   └── Graphiti/Zep projection

This eliminates the current synchronous direct add_memory path and inline Phase-B dependency. Today close_session.py still performs direct Graphiti writes and synchronous LLM work, so this is a real architecture repair rather than optimization. 

The acknowledgment invariant is:

If session close reports success, the exact continuation state is already canonical and replayable.

Not:

The provider happened to accept two Graphiti episodes.

⸻

7. Release G — Multi-agent acceptance and full governance activation

Only after A–F pass do you run the complete cross-surface matrix.

The canonical fixture is:

repo = G
governance publication = R
program = P
resume capsule = C
hydration manifest = H

Every surface eligible for governed autonomous execution must prove:

same G
same R
same P
same C
same H digest
valid surface-specific model projection
valid required capabilities
fresh SessionReadinessReceipt
governance write denied
repo write allowed only as policy permits

Then run the continuity loop:

Cursor starts from C1
    ↓
works
    ↓
close creates C2
Claude starts
    ↓
must consume exact C2
    ↓
works
    ↓
close creates C3
Codex starts
    ↓
must consume exact C3

No semantic PICKUP search can satisfy that gate.

After that succeeds, publish the complete validated governance corpus.

Then ingest consumer-repository policy to the repo namespace:

consumer CANONICAL_LAW binding
INVARIANTS.md
repo-specific constraints
selected authoritative repo knowledge

Global policy stays in l9-governance.

⸻

Contracts I would add or tighten

Contract	Owner	Purpose
GovernancePublicationReceipt	l9-graphiti-memory	binds governance Git SHA, law digest, manifest digest, rules
GovernanceSourceSet	l9-graphiti-memory	immutable manifest-driven publication input
ResumeCapsule	Cursor-Governance runtime	exact cross-session continuation
HydrationManifest	shared boundary	canonical selected-context identity
HydrationReceipt	l9-memory + runtime composition	retrieval and lane evidence
ModelProjection	adapter renderer	token-bounded cognition only
RuntimeEnvironmentReceipt	Cursor-Governance	runtime/capability environment
SessionReadinessReceipt	Cursor-Governance	authoritative admission result
CloseReceipt	runtime/memory boundary	proves capsule canonical before close returns

Do not create parallel variants for Cursor, Claude, and Codex.

Adapters should render shared contracts.

⸻

Lane model

I would formalize hydration into five lanes rather than four:

Lane	Source	Required for autonomous PE?
governance	l9-governance	yes
continuity	exact ResumeCapsule	yes unless explicit fresh session
repository	repo law/invariants/architecture	yes
episodic	repo memory	profile-dependent
program	PE/program execution state	yes for PE

Each lane returns exactly one of:

PASS
EMPTY
FALLBACK
FAILED
BLOCKED
NOT_APPLICABLE

Do not overload degraded=true with every possible condition.

⸻

Freshness model

A session should not merely say “memory was found.”

It should prove temporal consistency across three independent epochs:

governance_epoch
    Cursor-Governance source revision/publication
continuity_epoch
    ResumeCapsule generation
runtime_epoch
    environment/capability/bootstrap receipt

Then:

hydration_epoch =
hash(
  governance publication,
  resume capsule,
  repo identity,
  required namespaces,
  program state,
  capability state
)

If a relevant input changes after admission, the autonomous-readiness receipt becomes stale.

That gives PE Gate 0 a rigorous invalidation model.

⸻

Capability naming

I would avoid making graphiti.* the long-term agent abstraction.

Prefer:

memory.search
memory.hydrate
memory.write
memory.write_governed
memory.close
memory.health

because Graphiti is now an implementation detail of projection.

If the current registry has durable consumers on:

graphiti.query
graphiti.write_governed

migrate safely:

graphiti.query
    compatibility alias → memory.search
graphiti.write_governed
    compatibility alias → memory.write_governed

Retire only when active consumers are zero.

This avoids repeating the same identity-migration mistake you were preventing in the rules corpus.

⸻

Model-context policy

The model context should be assembled by value, not by repository-document completeness.

A good target split is:

governance constraints      30–40%
continuity                   20–30%
repo/program facts           20–30%
episodic memory              remainder

Those are policy weights, not fixed quotas.

The allocator should retain complete atomic records and prioritize constraint/decision classes. l9-graphiti-memory already does class-aware ordering with constraints first and exposes deterministic hydration result digests. 

Do not inject all 63 rules merely because all 63 are available.

That would solve distribution while recreating context bloat.

⸻

Governance policy projection rule

For every governance item preserve three separate concepts:

SOURCE
    actual canonical text
STRUCTURED POLICY
    stable machine representation
SEARCH DERIVATIVE
    distilled/search-friendly atom

Authority is:

SOURCE > STRUCTURED POLICY > SEARCH DERIVATIVE

If structured or distilled content disagrees with source, it is stale/invalid.

Agents cannot promote a search derivative into policy.

This should be enforced by namespace authorization, not merely prompt instructions.

⸻

Provider-projection health

Do not let Graphiti availability collapse the whole system into “memory unavailable.”

Track separately:

canonical_store
projection_outbox
graphiti_projection
zep_projection
semantic_strategy

The runbook already distinguishes canonical success from optional-strategy failure and explicitly says partial/failed results must not masquerade as empty success. 

Session readiness should consume that distinction.

For example:

canonical store healthy
Graphiti down
canonical retrieval sufficient
    → READY_GOVERNED may still be possible
canonical store unavailable
    → governance/session continuity cannot be trusted
    → autonomous PE BLOCKED

That is much more resilient than tying cognitive readiness directly to Graphiti uptime.

⸻

Release-blocking acceptance properties

ID	Requirement
A-01	No model-controlled process possesses downstream provider secrets
A-02	Agent memory calls terminate at l9-graphiti-memory, not upstream Graphiti
A-03	All canonical writes pass through MemoryService
A-04	Governance publication is exact-SHA, manifest-driven and digest-verified
A-05	Ordinary agents cannot write l9-governance
A-06	Governance publisher is idempotent
A-07	Exact ResumeCapsule replaces semantic PICKUP as continuity authority
A-08	Readonly repos can still hydrate authorized memory
A-09	Hydration uses shared memory retrieval/budget machinery
A-10	Successful empty and backend failure remain distinguishable
A-11	Operator telemetry is outside ordinary model projection
A-12	HydrationManifest is deterministic
A-13	Governance, repo, program, continuity and episodic lanes are typed
A-14	Session readiness is freshness-bound
A-15	PE cannot autonomously dispatch without READY_PE_AUTONOMOUS
A-16	Session close is canonically durable before it returns success
A-17	Close succeeds when Graphiti projection is unavailable
A-18	Close does not depend on an inline LLM call
A-19	Distillation/projection retries are idempotent
A-20	Cursor→Claude→other-agent exact continuation passes
A-21	Same HydrationManifest is observed across eligible surfaces
A-22	Plain hosted Web/Mobile proves its expected degraded state without secrets
A-23	Full governance corpus publishes only after controlled-canary acceptance
A-24	No legacy direct Graphiti lifecycle remains reachable from model SessionStart/Stop

⸻

What to delete only after replacement proves green

The final cleanup should not be premature.

After the canonical path passes acceptance, retire active dependence on:

Cursor-Governance graphiti_memory_client direct lifecycle access
graphiti_env_loader secret loading in model process
direct credential-bearing MCP templates
semantic PICKUP selection
character-budget SessionStart compiler
Graphiti-specific fact parsing
synchronous Graphiti session-close writes
inline close-time Phase-B LLM
duplicated retrieval/ranking logic

A compatibility wrapper may remain only if it delegates to the new canonical memory service and cannot retrieve raw provider credentials.

⸻

Program ordering

The execution order I would hold is:

1. Baseline proof and exact revision bind
2. Canonical memory.* capability to l9-graphiti-memory
3. Zero model-side secret closure
4. GovernanceBootstrapper + l9-governance authz
5. Controlled governance publication
6. Replace SessionStart with canonical hydrate + exact ResumeCapsule
7. Split HydrationReceipt / ModelProjection
8. SessionReadinessReceipt + PE Gate 0
9. Deterministic close + asynchronous distillation/projection
10. Cross-surface acceptance
11. Full governance publication
12. Legacy-path removal and final convergence

That is the one list I would execute against.

⸻

Final architectural judgment

The system does not need another major abstraction.

It already has the key primitives:

* a canonical memory service and store;
* authorization;
* canonical receipts;
* retrieval planning;
* a token-aware budget allocator;
* source ingestion;
* policy-class ingestion;
* evidence-preserving distillation;
* idempotency;
* an outbox;
* provider projections;
* a strengthened governance rule manifest/control plane. 

The remaining problem is that Cursor-Governance is still exercising an older direct-Graphiti memory implementation beside the newer canonical memory package.

So the best program objective is not:

Build a better Graphiti integration.

It is:

Collapse every agent-facing memory lifecycle onto l9-graphiti-memory, publish governance through that canonical plane, make exact hydrated cognitive state an explicit session-readiness contract, and reduce Graphiti to the projection responsibility the memory architecture already assigns it.

That is the point at which L9 becomes genuinely agent-neutral: Cursor, Claude, Codex, Gemini, Manus, and future agents differ only in adapter/rendering/runtime identity—not in governance source, memory authority, continuation state, or admission semantics.

I would consider that the exemplary convergence target.