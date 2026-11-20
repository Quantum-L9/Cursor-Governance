# Battle Plan

This is the cumulative execution order. It is not execution authorization.

## Wave 0 - Freeze census

Create the complete disposition inventory using:

`KEEP | REFRESH | CONSOLIDATE | EVICT | ARCHIVE_DISABLE | REVIEW | VERIFY`

No file movement until active references/consumers for each target are known.

## Wave 1 - Disable legacy DAG plane

Archive `workflows/**` and remove every active reachability edge.

Acceptance is not "files moved". Acceptance is "nothing live can route, import, initialize, advertise, test-as-supported, or depend on the archived DAG plane."

## Wave 2 - Normalize core reasoning surfaces

1. Supersede repository GAR v0.8.2 with GAR v1.6.1.
2. Change GAR from explicit-only to always-available/model-invocable while preserving lazy hydration.
3. Wire GAR, Coding Agent, Authority Resolver, and Work State Router as one mode-aware/lazy routing family through the existing Virtual Skill Plane.
4. In Ask Mode, bias non-trivial architecture/advisory work toward GAR while allowing narrower domain skills to win.
5. In Agent Mode, bias bounded implementation work toward Coding Agent only when the prompt carries mutation/implementation intent; Agent Mode alone grants no mutation authority.
6. Auto-load Authority Resolver only when exact L9 authority/currentness is material; auto-load Work State Router only for continuity/resume/handoff/next-transition work.
7. Preserve one primary plus at most two supporting skills; do not preload the four-skill family.
8. Verify the provider for `evidence.review` before declaring GAR integration complete.
9. Restore lightweight planning and make it the single canonical `l9-plan`.
10. Remove the PE-aware plan implementation from Cursor-Governance with the PE corpus.

## Wave 3 - Refresh / consolidate governance specialists

1. Refresh `l9-pr-audit` in place. No parallel PR-audit replacement.
2. Create one lazy-loaded `l9-ci` owner from confirmed CI-owned capabilities.
3. Fold only capabilities whose semantic owner is actually CI. Do not absorb generic pipeline/infra skills by proximity.

## Wave 4 - Domain eviction

1. Move idea-owned skills/history to IdeaOS.
2. Create `Quantum-L9/l9-campaign-execution`.
3. Move Program Execution, PE skills, PE-specific planning/execution support, and only their true owned dependencies.

## Wave 5 - Wire cleanup

For each moved, renamed, archived, or superseded identity, inspect:

- autonomy/skill registries
- generated registries/projections
- commands
- hooks
- bootstrap/session wiring
- tests
- CI
- docs
- imports
- adapters
- capability references

Every reference must finish as one of:

`REWIRED | ARCHIVED | DELETED | INTENTIONALLY_RETAINED`

No dangling names and no compatibility shims without a current consumer.

## Wave 6 - Final ownership census

For every surviving top-level skill, answer:

> Is governing or operating the coding/agent environment the primary responsibility this skill owns?

If no, assign a destination or REVIEW disposition.

## Completion criteria

- Cursor-Governance has one ordinary Plan identity.
- GAR current version is the only active GAR.
- GAR is model-invocable but lazy.
- required GAR companion capabilities are reachable without being preloaded.
- old DAG workflow plane is unreachable.
- PR Audit has one current owner.
- CI has one routing surface with lazy concern loading.
- IdeaOS owns idea lifecycle capabilities.
- l9-campaign-execution owns campaign/program execution capabilities.
- no active registry, command, hook, test, or adapter points at a retired identity.


## Cross-cutting portability pass

Apply one portability gate to every surviving, moved, renamed, or consolidated skill:

1. Keep `SKILL.md` as the canonical skill entrypoint.
2. Add `agents/openai.yaml`.
3. Preserve any still-live Cursor/Claude metadata sidecars.
4. Keep OpenAI-facing `SKILL.md` frontmatter to `name` + `description`; relocate platform-specific routing metadata.
5. Validate the exact final package after its move/rename/consolidation.

Do this as part of each skill's owning move/refresh rather than as an unrelated architecture project.
