# Delta Log

Use this file to record only newly introduced or changed decisions.

## 2026-10-07 - Initial consolidated tracker

NEW:
- Idea lifecycle skills belong in IdeaOS.
- PE/program execution and the PE-aware plan belong in a new l9-campaign-execution repository.
- l9-plan-simple capability becomes the single canonical l9-plan after restoration/normalization.
- workflows/** legacy DAG attempts are archived and fully unwired.
- PR Audit remains but needs a refresh.
- repository GAR v0.8.2 is superseded by GAR v1.6.1.
- GAR should be always available to Cursor routing while remaining lazily hydrated.
- Authority Resolver and Work State Router remain available as lazy GAR companion capabilities.
- evidence.review provider must be verified before GAR integration can be called complete.
- CI fragmentation should collapse into one lazy-loaded l9-ci owner after ownership review.

Conversation discipline:
- Future chat replies should only state deltas/refinements rather than repeat this inventory.

## 2026-10-07 - OpenAI compatibility baseline

NEW:
- Every active skill touched by the cleanup must be OpenAI-compatible.
- Add `agents/openai.yaml` to each skill as the OpenAI/ChatGPT metadata sidecar.
- Preserve other platform sidecars when they still have a consumer; OpenAI support is additive, not a rename of `agents/meta.yaml`.
- Normalize `SKILL.md` frontmatter for OpenAI compatibility to `name` + `description`; move platform routing metadata out of the frontmatter.
- Validate each exact final skill package rather than inferring compatibility from neighboring skills.
## 2026-10-07 - GAR sibling mode-aware auto-routing

CHANGED:
- Treat the coordinated four-skill Cursor family as GAR, Coding Agent, Authority Resolver, and Work State Router.
- GAR should be model-invocable and become the non-trivial architecture/advisory fallback in Ask Mode, not an unconditional owner of every Ask prompt.
- Coding Agent should become model-invocable and become the bounded implementation fallback in Agent Mode only when mutation/implementation intent is present.
- Authority Resolver auto-loads when exact L9 semantic authority/currentness is material.
- Work State Router auto-loads for resume/continuity/handoff/next-transition work.
- Preserve one-primary + max-two-supporting routing; the four skills compose sequentially/lazily rather than all loading together.
- Cursor `sessionStart` can expose starting `composer_mode`; `beforeSubmitPrompt` currently does not. Carry mode forward as a session routing prior, never as the sole predicate.
- Coding Agent is no longer planned as permanently explicit-only; its auto-route must retain a hard mutation-intent gate and cannot derive authorization from Agent Mode alone.

