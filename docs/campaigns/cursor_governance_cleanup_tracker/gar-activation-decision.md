# GAR Activation Decision

## Decision

Cursor may keep GAR enabled all the time.

The correct model is:

- **always available to routing**
- **not always executing**
- **not fully hydrated**
- **load specialist context only when the prompt crosses GAR's activation boundary**

This is compatible with GAR v1.6.1 because the current pack is built around bounded context hydration through its context index rather than loading the full architecture corpus up front.

## Why current Cursor config says explicit-only

At the observed Cursor-Governance revision, `skills/AUTONOMY_MANIFEST.yaml` still describes the repository GAR as an experimental v0.8.2 bootloader and places it in `explicit_only` to prevent its broad old description from hijacking normal routing.

That is evidence about the **old GAR integration**, not a reason the new GAR must remain explicit-only.

## Target behavior

Move GAR from explicit-only to model-invocable / auto-selectable after the v1.6.1 supersession.

Do not create an always-run hook that invokes architectural reasoning on every Cursor prompt. That would defeat lazy loading and turn GAR into routing gravity.

Recommended semantic distinction:

```text
GAR enabled       = Cursor may select GAR when its trigger matches
GAR activated     = GAR entrypoint is handling this request
GAR hydrated      = only the required concern modules are loaded
GAR deep reasoning= only when task scope actually requires it
```

## Companion skills

Assumption for this tracker: "the two GAR siblings" refers to `l9-authority-resolver` and `l9-work-state-router`.

Keep both in Cursor's capability plane, but lazy-load them.

- Authority Resolver is needed when exact L9 semantic authority must be bound.
- Work State Router is useful for durable continuation and capability routing across multi-stage work.
- Neither should be permanently hydrated merely because GAR is enabled.

The four-skill Cursor routing family for this cleanup is now:

- `l9-global-architect`
- `l9-coding-agent`
- `l9-authority-resolver`
- `l9-work-state-router`

Coding Agent should no longer remain permanently explicit-only. It may be model-selected in Agent Mode when the prompt actually asks for bounded code implementation/repair/refactor. Agent Mode itself is not mutation authority and is not enough to fire Coding Agent on read-only or architecture-only work.

GAR should be the non-trivial architecture/advisory fallback in Ask Mode, not the unconditional owner of every Ask prompt. Narrower domain specialists still outrank it.

Authority Resolver and Work State Router remain narrow lazy companions. The existing route limit of one primary plus at most two supporting skills is preserved, so the four-skill family is coordinated rather than preloaded.

GAR v1.6.1 also declares `evidence.review` as a required capability. The exact current provider must be verified before execution because this runtime did not expose a top-level installed `evidence-review-engine` skill. See `gar-sibling-routing.md` for the detailed routing decision.
