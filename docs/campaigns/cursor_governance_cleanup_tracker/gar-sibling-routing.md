# GAR Sibling Auto-Routing Decision

## Scope

Treat this four-skill family as the coordinated GAR operating set for Cursor routing:

1. `l9-global-architect`
2. `l9-coding-agent`
3. `l9-authority-resolver`
4. `l9-work-state-router`

`evidence.review` remains a separate required capability/provider verification item for GAR 1.6.1 and is not silently counted as one of these four.

## Core decision

Wire the four skills into the existing Virtual Skill Plane. Do not create a second router or a permanent four-skill context bundle.

The operating model is:

- all four are discoverable by the canonical registry;
- one primary skill is selected per prompt;
- at most two siblings are loaded as supporting skills;
- deeper skill resources remain lazy and stage/concern loaded;
- mode is a routing prior, not semantic authority;
- task intent can override the mode prior.

## Mode defaults

### Ask Mode

Use `l9-global-architect` as the **non-trivial L9/software architecture advisory fallback**, not as the unconditional owner of every Ask Mode prompt.

GAR should win when the request is primarily architecture, design, reconciliation, tradeoffs, system boundaries, deployment convergence, or architecture audit and no narrower domain skill owns the task.

Do not route trivial questions, documentation lookup, CI-specific work, PR audit, or other narrower specialist tasks to GAR merely because the composer is in Ask Mode.

### Agent Mode

Use `l9-coding-agent` as the **bounded implementation fallback when the prompt actually requests code mutation/repair/refactor/implementation** and no narrower mutation specialist owns the task.

Agent Mode alone does not authorize mutation and does not make Coding Agent the owner of read-only investigation, architecture invention, PR audit, deployment, merge, or unrelated operational work.

If Agent Mode prompt semantics are architectural rather than implementation-oriented, GAR may still be primary.

## Companion activation

### Authority Resolver

Auto-select as supporting capability when the current task materially depends on exact L9 semantic authority, canonical owner, contract/schema/invariant currentness, or historical-vs-current law.

It may also become primary when the user's actual question is simply "what authority applies?".

### Work State Router

Auto-select when the task is a continuation/resume/handoff/next-transition problem across multi-stage work, especially when valid prior receipts/state should be reused instead of redoing work.

It may become primary when continuity/routing is the actual task. It should not become ambient state machinery on ordinary single-turn work.

## Cursor mode transport

Current Cursor hook documentation exposes `composer_mode` on `sessionStart` (`agent | ask | edit`) and allows `sessionStart` to export environment variables to later hooks. The current `beforeSubmitPrompt` input does not expose `composer_mode`.

Therefore the smallest implementation is:

1. `sessionStart` captures `composer_mode` and exports a session-scoped value such as `L9_CURSOR_COMPOSER_MODE`.
2. `before_submit_skill_router.py` reads that value and passes a routing context to the shared scorer.
3. `route_prompt.py` applies a bounded mode prior only after normal prompt/domain scoring.
4. Prompt semantics remain capable of overriding the prior.
5. Because the documented mode is the mode at session start, never let this field become the sole routing predicate. This avoids stale routing if Cursor mode changes later in the conversation.

Do not duplicate mode routing in rules/05, the gateway, and the scorer. The scorer remains the single selection authority.

## Registry changes

The current repository marks GAR and Coding Agent `explicit_only`. To support automatic selection:

- move GAR to `model_allowed` / `auto_invoke` with strong architecture triggers and negative signals for implementation-only and specialist-owned tasks;
- move Coding Agent to `model_allowed` / `auto_invoke` with a hard implementation/mutation-intent gate and negative signals for architecture-only/read-only/audit-only/deploy-only work;
- register Authority Resolver and Work State Router as model-allowed capabilities with narrow activation descriptions/routes;
- preserve the existing one-primary / max-two-supporting composition limit.

Do not treat auto-selection as push, merge, deploy, destructive-action, or other consequential authorization.

## Acceptance tests

Minimum routing cases:

- Ask + architecture question -> GAR primary.
- Ask + CI failure -> CI specialist, not GAR.
- Ask + trivial typo/explanation -> no forced GAR route.
- Agent + explicit bounded implementation -> Coding Agent primary.
- Agent + architecture/design request -> GAR primary, not Coding Agent.
- Agent + read-only PR audit -> PR Audit primary.
- GAR request requiring current L9 law -> GAR primary + Authority Resolver support.
- Resume prior multi-stage architecture campaign -> Work State Router primary or support as appropriate.
- Explicit "what authority governs X?" -> Authority Resolver primary.
- No route ever loads more than one primary plus two supporting skills.
- Lazy package resources remain unloaded until their concern/stage is reached.

## Stop condition

This routing slice is complete when the four capabilities auto-select correctly under the above cases without making mode the sole predicate and without widening mutation authority.
