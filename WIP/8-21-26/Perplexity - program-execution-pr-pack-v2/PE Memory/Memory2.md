Yes. I would make that a first-class part of the hydration architecture: every session-start hydration produces a structured receipt, and optionally renders a compact human status report.

The key is that the status report should not consume model context unless explicitly requested. It is operator telemetry, not memory.

I would expose something like:

L9 MEMORY · SESSION HYDRATION
────────────────────────────────────────────────────
Status        DEGRADED · usable
Duration      412 ms
Active scope  Cursor-Governance · branch feature/memory-v2
HEAD          7ebf331
CONTINUITY
  ✓ Resume capsule       loaded · 143 ms · fresh
    Objective            Agent memory wiring
    Next action          Review hydration architecture
    Checkpoint age       18m
    Source               Graphiti
REPO MEMORY
  ✓ Decisions            3 selected / 17 candidates
  ✓ Lessons              2 selected / 11 candidates
  ○ Historical episodes  not loaded · on-demand
GOVERNANCE
  ✓ Static governance    active · local canonical files
  ✓ Memory deltas        1 loaded
  ○ Full governance      suppressed · already available locally
WORKSPACE
  ✓ Cross-repo context   1 selected
  ○ Other repositories   not hydrated
FALLBACKS
  ! Graphiti MCP         primary transport failed: timeout
  ✓ Local capsule cache  used · age 6m
  ✓ Session continuity   preserved
CONTEXT
  Budget                 700 tokens
  Injected               463 tokens
  Candidates             31
  Selected               7
  Deduplicated           9
  Stale rejected         4
Health        CONTINUITY OK · KNOWLEDGE DEGRADED
────────────────────────────────────────────────────

That tells you almost everything an operator needs without dumping implementation noise.

I would separate three outputs

Internally, hydration should always produce a full HydrationReceipt. This is the machine record and should contain timings, selected memory IDs, failures, fallbacks, cache decisions, group resolution, token counts, freshness, etc.

Then derive two projections:

HydrationReceipt
     │
     ├──> ModelContext
     │     tiny, curated
     │     only information useful to reasoning
     │
     └──> OperatorStatus
           diagnostics
           never consumes context tokens

This keeps observability from competing with the context window.

Give every lane an explicit state

Avoid vague global degraded=true.

Every subsystem should report one of a small state vocabulary:

ACTIVE
LOADED
EMPTY
SKIPPED
FALLBACK
STALE
DEGRADED
FAILED
DISABLED

For example:

{
  "continuity": {
    "status": "loaded",
    "source": "graphiti",
    "freshness_seconds": 842,
    "items_selected": 1
  },
  "repo_memory": {
    "status": "degraded",
    "source": "local_cache",
    "failure": "mcp_timeout",
    "items_selected": 4
  },
  "workspace": {
    "status": "skipped",
    "reason": "no_relevant_candidates"
  }
}

That distinction matters enormously.

EMPTY means:

I successfully checked and there was nothing relevant.

FAILED means:

I could not check.

FALLBACK means:

Primary failed, but another source supplied usable state.

Those should never be conflated.

Show authority and freshness

I would always make these visible because they answer the two questions that matter when debugging agent behavior:

“Where did this come from?”

and

“How much should I trust it?”

Example:

✓ Resume       Graphiti       fresh       18m
✓ Decisions    Graphiti       fresh       2h
! Workspace    local cache    stale       7h
○ Governance   canonical FS   authoritative

Even better, distinguish authority from freshness:

SOURCE          AUTHORITY      FRESHNESS
Graphiti        durable        fresh
Local cache     fallback       8m old
Repo files      canonical      HEAD
Memory delta    advisory       2d old

Make the normal view compact

I would not print the big report every startup by default.

Default:

L9 Memory: ✓ hydrated · Cursor-Governance · 463 tok · 412ms
           resume ✓ · repo ✓ · governance ✓ · workspace fallback

If something goes wrong:

L9 Memory: ! degraded · usable
           resume ✓ Graphiti
           repo ! local-cache fallback (MCP timeout)
           governance ✓
           workspace ○ skipped
           Run: l9 memory-status

Then a command such as:

l9 memory-status

or:

l9 memory-status --verbose

shows the detailed receipt.

That gives you visibility without startup spam.

I would support three verbosity levels

MEMORY_STATUS=off
MEMORY_STATUS=compact       # recommended default
MEMORY_STATUS=verbose

And probably:

MEMORY_STATUS_ON_FAILURE=verbose

So a healthy session gets one line, while a degraded session automatically tells you what happened.

Include why something was not loaded

This is surprisingly valuable.

You don’t just want:

Workspace: 0

You want:

Workspace:
  ○ not loaded
    reason: no candidates exceeded relevance threshold

versus:

Workspace:
  ! unavailable
    reason: Graphiti MCP authentication failure

versus:

Workspace:
  ○ suppressed
    reason: startup token budget exhausted

These represent completely different system behaviors.

Also report what actually entered model context

Retrieval and injection are different phases.

The report should show both:

Repo decisions        retrieved 14 → selected 3 → injected 3
Lessons               retrieved 12 → selected 2 → injected 1
Workspace             retrieved 8  → selected 1 → injected 0
Governance deltas     retrieved 2  → selected 1 → injected 1

Then when an agent appears unaware of something, you can determine whether it was:

1. never retrieved,
2. retrieved but filtered,
3. selected but excluded by budget,
4. actually injected and ignored by the model.

That is the observability you want for debugging memory quality.

Add rejection reasons

For verbose mode:

Rejected candidates
  m:f7831   stale artifact      source commit no longer ancestor
  m:a1092   duplicate           equivalent to selected m:b8211
  m:c9123   low relevance       score .31 < .55
  m:f7774   wrong scope         website-bot
  m:a8881   budget pressure     marginal value/token too low

This makes the hydration compiler explainable rather than magical.

Failure reporting should identify the exact fallback chain

For example:

CONTINUITY
  Graphiti exact checkpoint
       ↓ timeout
  compiled capsule cache
       ↓ HIT
  local session journal
       ↓ not required
Result: FALLBACK · continuity preserved

Or:

REPO MEMORY
  Graphiti semantic query
       ↓ auth failure
  local compiled cache
       ↓ stale > TTL
  no source remaining
Result: FAILED · repo knowledge unavailable

No flying blind.

I would also surface memory generation IDs

A really useful debugging feature:

Hydration packet   hp_01J...
Checkpoint         cp_01J...
Memory generation  1842
Compiler           hydration-v2.3

Then if an agent behaves strangely halfway through a session, you can immediately correlate:

Which exact hydration packet did this session receive?

That makes replay and incident analysis much easier.

Architecturally

I would therefore make the startup path:

sessionStart
     │
     ▼
Hydration Planner
     │
     ▼
Typed reads
     │
     ▼
Hydration Compiler
     │
     ├───────────────> ModelContext
     │                   400–800 tokens
     │
     └───────────────> HydrationReceipt
                         │
                         ├── local receipt/log
                         ├── compact terminal status
                         └── verbose memory-status

And critically:

Generating or rendering the status report must never be capable of failing hydration.

Telemetry is fail-open. Hydration is the functional path.

I would actually consider this part of the contract rather than optional debugging sugar. The display can be optional; the receipt should always exist.

That gives you the equivalent of a boot report for the agent’s cognitive state: what brain state was restored, from where, how fresh it is, what was omitted, and which safety nets fired.