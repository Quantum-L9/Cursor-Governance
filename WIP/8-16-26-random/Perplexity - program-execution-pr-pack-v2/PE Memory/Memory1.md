Yes. I would move it from “Graphiti retrieval glued to session hooks” to a small memory control plane with a hydration compiler.

The architectural principle would be:

Durable memory is large and historical. Prompt memory is small, typed, current, and task-specific. Never hydrate the durable store directly into the context window.

The patch you have is a good recovery step because it restores reads on dependency-poor surfaces and recognizes that readonly should gate writes rather than reads. README.md But I would treat that as fixing L1 transport reliability, not as the final memory architecture.

1. Introduce a first-class ResumeCapsule

Today session start searches Graphiti with several PICKUP-oriented queries, scans results for pickup-like text, parses loosely structured prose/JSON, then appends several facts. 

I would stop discovering the latest session state semantically.

Make continuity an exact lookup, while knowledge remains semantic retrieval.

Conceptually:

Graphiti durable memory
│
├── ResumeCapsule        ← exact retrieval
├── Decisions            ← semantic/structured retrieval
├── Lessons              ← semantic retrieval
├── Constraints          ← structured retrieval
├── Artifact knowledge   ← path/symbol-aware retrieval
└── Historical episodes  ← cold/on-demand

A ResumeCapsule v2 should look approximately like:

{
  "schema": 2,
  "scope": {
    "repo": "Cursor-Governance",
    "branch": "feature/foo",
    "task_id": "optional-stable-task"
  },
  "objective": "Finish memory hydration redesign",
  "next_action": "Implement typed hydration lanes",
  "blockers": [
    "Web close path still depends on pydantic"
  ],
  "decisions": [
    {
      "summary": "Graphiti remains durable memory SSOT",
      "ref": "m:abc123"
    }
  ],
  "artifacts": [
    {
      "path": "ops/graphiti/hydration/compile_session_packet.py",
      "state": "modified"
    }
  ],
  "verification": [
    "stdlib transport tests 8/8"
  ],
  "failed_approaches": [],
  "source_commit": "abc123",
  "captured_at": "...",
  "sequence": 47
}

Then add an MCP operation roughly equivalent to:

get_latest_checkpoint(repo, branch, task_id?)

No vector similarity. No PICKUP|objective= regex. No three attempts. No accidentally choosing some related old fact.

Graphiti remains a sensible durable temporal store because its model already supports grouped data, provenance and temporal knowledge; the MCP layer also exposes group-aware searches. 

⸻

2. Turn compile_session_packet into a real Hydration Compiler

The current compiler has the beginnings of this idea, but it still largely concatenates retrieval output. It builds a context slice from the pickup plus up to five fact strings and cuts it according to a character budget. 

I would introduce:

               HydrationRequest
                      │
                      ▼
          ┌───────────────────────┐
          │ Hydration Planner     │
          │                       │
          │ identity              │
          │ active repo           │
          │ branch / HEAD         │
          │ task hint             │
          │ available token budget│
          └──────────┬────────────┘
                     │
              parallel typed reads
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   CONTINUITY     REPO MEMORY    WORKSPACE
   exact          selective      selective
       │             │             │
       └─────────────┼─────────────┘
                     ▼
              Candidate scorer
                     │
                     ▼
          redundancy / stale filter
                     │
                     ▼
             Token-budget packer
                     │
              ┌──────┴──────┐
              ▼             ▼
        Model Projection   Receipt
        400–800 tokens     full metadata

This separation is extremely important.

Graphiti returns candidates. The hydration compiler decides what deserves prompt space.

⸻

3. Separate machine state from model context

This is probably the easiest immediate context-window win.

Current format_additional_context() exposes:

* identifiers,
* objective,
* next action,
* hydration statistics,
* fact previews,
* context facts,
* then another JSON representation of much of the same information. 

That mixes two consumers.

The agent needs:

MEMORY RESUME
Objective: Finish memory hydration architecture.
Next: Implement typed read lanes.
Blocker: Web enqueue is not dependency-safe.
Relevant decision: Graphiti remains durable SSOT.
Relevant artifact: ops/graphiti/hydration/compile_session_packet.py

The control plane needs:

{
  "packet_id": "...",
  "groups_queried": [],
  "latencies_ms": {},
  "candidate_count": 18,
  "selected_count": 4,
  "cache_hit": false,
  "degraded_lanes": [],
  "source_ids": [],
  "budget": {},
  "compiler_version": "2"
}

Do not put the second object in the model context.

Store it as the hydration receipt.

That alone removes duplicated serialization and makes observability essentially free in terms of prompt tokens.

⸻

4. Use four typed memory lanes rather than flattened groups

I would replace:

repo A
repo B
cursor-governance
igor-workspace
     │
     ▼
flat facts[]

with:

Lane	Purpose	Startup behavior	Can determine next_action?
Continuity	Current task checkpoint	Always	Yes
Repo knowledge	Decisions, lessons, constraints	Selectively	No
Workspace	Cross-project coordination/preferences	Very selectively	No
Governance delta	Recent governance state not already loaded statically	Only when relevant	No

This solves an important issue in the proposed child-repository search. The uploaded pack currently proposes reading the active checkout plus child checkouts, governance, and workspace groups. PR_BODY.md That improves recall but can decrease precision.

Only the continuity lane gets authority to resume work.

Other lanes can inform the resumed task but cannot replace it.

And I would stop hydrating cursor-governance memory indiscriminately. The repository already loads governance through its canonical plugin/rules mechanism, while Graphiti is separately defined as the memory layer.  Reinjecting static governance doctrine from memory risks both duplication and stale authority.

Graphiti governance memory should carry dynamic governance deltas:

active migration
recent decision
known unresolved issue
temporary compatibility constraint
recently changed architecture

Not copies of CANONICAL_LAW.md.

⸻

5. Make hydration progressive

This is the largest long-term context optimization.

Do not answer every possible future question at sessionStart.

Use:

H0 — Bootstrap
     exact ResumeCapsule
     ~250–500 tokens
H1 — Initial task
     retrieve memories relevant to current user intent
     ~200–400 additional tokens
H2 — Execution-triggered
     retrieve file/symbol/error/decision memories on demand
H3 — Deep recall
     historical episodes only when explicitly useful

The initial context might therefore be only 400–800 tokens, even if the repository has hundreds of thousands of stored facts.

If the first task is:

Fix compile_session_packet.py

the retrieval planner can query:

artifact = compile_session_packet.py
kind ∈ {decision, failure, constraint, lesson}
scope = active repo

If the agent later encounters an MCP auth failure, retrieve memories associated with that error fingerprint.

If it starts modifying CI, retrieve CI-related decisions.

This is far more efficient than predicting everything it may need when the session starts.

⸻

6. Rank memories by value-per-token

I would give the compiler an explicit scoring function.

Conceptually:

utility =
    task_relevance
  × authority
  × freshness
  × confidence
  × scope_match
  × novelty
  - redundancy_penalty
  - stale_code_penalty
  - token_cost_penalty

A 40-token precise decision should beat a 350-token transcript fragment even if both are semantically relevant.

The important part is not the exact coefficients. It is making token cost a first-class retrieval property.

Then implement a token-budget packer:

bootstrap budget:       600
continuity reserve:     250
blockers/decisions:     180
artifact anchors:       100
workspace/governance:    70

Unused budget does not have to be filled.

That’s important. Retrieval systems tend to think:

“I have room for eight facts, therefore return eight facts.”

A good hydration system should think:

“There are two facts worth spending context on, therefore return two.”

⸻

7. Add code-aware memory invalidation

Agent memory for software engineering has a property normal conversational memory does not:

the repository itself can invalidate the memory.

Every significant technical memory should optionally carry:

repo
branch
source_commit
artifact paths
symbols
config keys
dependency versions
valid_from
superseded_by

Then the hydration compiler can detect:

memory says:
    auth.py uses JWT middleware X
current HEAD:
    auth.py changed significantly since source_commit

Result:

stale_code_penalty = high

or:

status = requires_revalidation

For architectural decisions, branch ancestry and supersession matter.

For user preferences, commits do not.

For governance rules, the authoritative file version matters.

That means freshness should be memory-type specific, not just timestamp based.

⸻

8. Replace “fail open to empty facts” with typed degradation

An empty list is dangerously ambiguous:

[]

Could mean:

store healthy + nothing found
network timeout
bad credentials
group unresolved
parser failure
MCP protocol failure
dependency import failure

The current client/compiler frequently catches broad exceptions and falls back to empty results. 

Instead make the response:

{
  "lane": "continuity",
  "status": "unavailable",
  "reason": "transport_timeout",
  "facts": [],
  "stale_cache_available": true
}

versus:

{
  "lane": "repo_memory",
  "status": "ok",
  "facts": []
}

Then the model receives only something compact when it matters:

Memory continuity unavailable; proceeding without prior-session state.

No false “nothing happened previously.”

⸻

9. Add a stale-while-revalidate local cache

You already have a natural role for a local fallback cache; canonical law explicitly recognizes local session data as fallback rather than SSOT. 

Use it aggressively—but only for compiled capsules, not as another memory system.

Cache key:

repo_identity
branch
HEAD
memory_generation
compiler_version

Cache content:

last valid ResumeCapsule
last compact hydration projection
source IDs
created_at
TTL

Startup behavior:

Graphiti healthy
    → compile fresh
    → update cache
Graphiti temporarily unavailable
    → use cached ResumeCapsule
    → mark STALE
    → never pretend it is fresh

This makes a network outage a reduction in freshness rather than complete amnesia.

⸻

10. Collapse remote reads into one hydration operation

I would add a higher-level MCP operation:

hydrate_session

Request:

{
  "repo_group": "cursor-governance",
  "workspace_group": "igor-workspace",
  "branch": "...",
  "head": "...",
  "task_hint": "...",
  "limits": {
    "continuity": 1,
    "decisions": 3,
    "lessons": 2
  }
}

Server result:

{
  "checkpoint": {},
  "repo_candidates": [],
  "workspace_candidates": [],
  "freshness": {}
}

Then the client-side Hydration Compiler does final policy and packing.

This turns:

connect
query
query
query
possibly reconnect
parse each

into:

connect
one request
compile

while preserving the canonical front door mandated by the repo. The law currently identifies graphiti_memory_client.py as that MCP interface and explicitly prohibits adapter-specific second memory planes. 

The stdlib MCP transport should therefore live under this client API.

⸻

11. Split session close into checkpointing and cognition

This is where I would most significantly change your write architecture.

SESSION
   │
   │ lightweight local working-state journal
   ▼
session boundary
   │
   ├──────────> FAST CHECKPOINT PIPELINE
   │             no LLM
   │             deterministic
   │             idempotent
   │             seconds-level freshness
   │                   │
   │                   ▼
   │             ResumeCapsule
   │
   └──────────> SLOW MEMORY PIPELINE
                 LLM distillation
                 salience
                 dedupe
                 contradiction
                 promotion
                       │
                       ▼
                 durable knowledge

The current worker combines creation of a richer pickup and promotion of lessons/insights/decisions into the same processing flow. 

Those have very different latency requirements.

Continuity is operational state.

Lessons are cognition.

Do not make continuity wait for cognition.

A fast worker should project:

objective
next action
blockers
modified artifacts
git HEAD
tests
known failures

without an LLM.

The slow worker can later decide:

What did we learn?
What is durable?
What supersedes previous knowledge?
What deserves graph promotion?

⸻

12. Maintain a working-state journal during the session

This would dramatically improve close reliability.

Instead of deriving the entire pickup from the last few transcript lines—as current close_session.py does for its heuristic checkpoint—maintain a tiny machine-readable working state throughout execution. Current main takes the last eight non-empty transcript lines and derives the objective/next action heuristically. 

For example:

{
  "objective": "...",
  "last_completed": "...",
  "next_action": "...",
  "blockers": [],
  "changed_files": [],
  "tests": [],
  "decision_refs": [],
  "git_head": "...",
  "sequence": 19
}

Updates are cheap and deterministic.

This is not long-term memory.

It’s runtime state.

At close:

runtime state
   +
git state
   +
small transcript tail
   ↓
ResumeCapsule

That is substantially more robust than reconstructing the agent’s mental state from transcript prose.

It also gives you crash recovery.

⸻

13. Use a real delivery queue for write processing

Your current architecture describes S3 pending jobs and a GitHub Actions batch processor. 

For archives, object storage is excellent.

For work delivery, I would eventually use a queue with:

visibility leases
retry count
dead-letter handling
ordering key
idempotency key
event wakeup
back-pressure

A cloud queue such as SQS/FIFO would fit your existing infrastructure, but the architecture should depend on the semantics, not on the vendor.

Then:

session close
     │
     ▼
durable queue
     │
     ├─ checkpoint projector
     └─ distillation worker

Object storage can retain immutable job bodies and full transcripts, while the queue carries work pointers.

⸻

14. Make everything idempotent by construction

Every memory event should have deterministic identity.

For example:

checkpoint_id =
  hash(repo + branch + session_id + sequence + payload_hash)
promotion_id =
  hash(job_id + memory_kind + canonical_body)

Then retries become harmless.

The current worker writes Graphiti and marks the queue item done afterward.  That means at-least-once execution needs deterministic memory identities to prevent duplicate semantic episodes.

I would explicitly design for:

at-least-once delivery
+
idempotent projection
=
effectively-once memory state

rather than attempting distributed exactly-once behavior.

⸻

15. Add memory admission control

Not every remembered thing deserves durable graph state.

The slow distiller should classify candidate memory as approximately:

discard
session-only
repo-short-term
repo-durable
workspace-durable
governance-durable

Promotion criteria should strongly favor:

decision
constraint
verified lesson
failed approach worth avoiding
architectural rationale
user preference
cross-session blocker
stable artifact relationship

and reject:

routine tool output
transient errors
repeated facts
conversation filler
facts derivable cheaply from current source

One especially important rule:

Do not memorize what can be cheaply and authoritatively re-read from the repository.

For example, remembering:

"The timeout is currently 15 seconds"

is usually inferior to reading the config.

Remember instead:

"Timeout intentionally changed from 5s to 15s because upstream service has a documented 8–12s cold start; do not reduce without revisiting issue X."

That’s memory that contributes reasoning rather than duplicating source code.

⸻

16. Add a Context ROI telemetry loop

I would measure the memory subsystem on usefulness per token, not facts retrieved.

Key runtime numbers:

Metric	What I would optimize
Hydration p95	Low and bounded
Bootstrap tokens	~400–800 target
Correct-resume rate	Very high
Degraded hydration rate	Near zero
Retrieved → injected ratio	Low
Injected → actually useful ratio	High
Duplicate-context tokens	Near zero
Stale-memory injection rate	Near zero
Wrong-repo resume rate	Zero
Checkpoint freshness	Seconds after close
Distillation freshness	Eventual
Memory contradictions	Detectable / traceable

Then create replay evaluations.

Take 100 real session boundaries and ask:

Given only this hydration packet:
1. What task are we doing?
2. What should happen next?
3. What must not be repeated?
4. What files matter?
5. What known blocker exists?

If the model consistently answers those five questions correctly with 500 tokens, adding another 2,000 memory tokens is a regression, not an improvement.

⸻

The resulting L9 architecture

                         ┌──────────────────────┐
                         │   GRAPHITI           │
                         │ Durable knowledge    │
                         │ Temporal/provenance  │
                         └──────────┬───────────┘
                                    │
                         canonical MCP interface
                                    │
                         ┌──────────▼───────────┐
                         │ MEMORY CONTROL PLANE │
                         │                      │
                         │ exact checkpoint     │
                         │ structured retrieval │
                         │ semantic retrieval   │
                         │ health/cache         │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │ HYDRATION COMPILER   │
                         │                      │
                         │ authority lanes      │
                         │ stale filtering      │
                         │ dedupe               │
                         │ value/token ranking  │
                         │ token packing        │
                         └──────┬────────┬──────┘
                                │        │
                    ┌───────────▼──┐   ┌─▼────────────────┐
                    │ Model packet │   │ Machine receipt   │
                    │ 400–800 tok  │   │ full observability│
                    └──────────────┘   └──────────────────┘
SESSION EXECUTION
       │
       ▼
Working State Journal
       │
       ▼
Durable Event Queue
       │
       ├───────────────┐
       ▼               ▼
Fast checkpoint     Slow distiller
projector            / salience
no LLM                  LLM
       │               │
       └───────┬───────┘
               ▼
            Graphiti

What I would do first

If I were sequencing this for Cursor-Governance, my order would be:

1. Create ResumeCapsule v2 and exact latest-checkpoint retrieval.
2. Split machine hydration receipt from model context.
3. Replace character slicing with token-aware, value-per-token packing.
4. Replace flattened read groups with continuity/repo/workspace/governance lanes.
5. Put stdlib MCP transport underneath the canonical memory client.
6. Add the session working-state journal.
7. Split fast checkpoint projection from slow LLM distillation.
8. Introduce a proper durable work queue + deterministic event IDs.
9. Add artifact/commit-aware staleness filtering.
10. Build replay-based “correct resume per token” evaluation.

Those changes would turn L9 memory from a persistent retrieval feature into something closer to a stateful agent runtime: Graphiti owns history, the checkpoint owns continuity, the compiler owns prompt economics, and the queue/distiller owns learning.

That separation is what I think will give you the biggest gains in stability, context-window efficiency, cross-surface reliability, and correct session resumption.