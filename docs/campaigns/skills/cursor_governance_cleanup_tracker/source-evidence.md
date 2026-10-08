# Source Evidence Snapshot

Repository observed: `Quantum-L9/Cursor-Governance`
Main revision observed: `3384e7546a9aee002d9e99df868ffcd70e74f786`
Commit message: `Merge pull request #695 from Quantum-L9/agent/claude-code/identity-consumer-convergence`

## Observed current repository facts used by this tracker

- `skills/l9-global-architect/SKILL.md` reports repository GAR version `0.8.2`.
- `skills/AUTONOMY_MANIFEST.yaml` currently places `l9-global-architect` in `explicit_only` and describes it as an experimental GAR runtime bootloader.
- The same autonomy manifest uses a virtual Cursor skill gateway and distinguishes auto-invoke from explicit-only skills.
- `workflows/` contains active-looking DAG/runtime/executor material including plan-simple, GMP, harvest, PR train, refactoring, slash-command update, test-pipeline and wire DAGs.
- `skills/l9-ci-ops` and `skills/l9-setting-up-ci` are separate active CI entrypoints with overlapping CI ownership.
- `skills/l9-coding-agent` explicitly describes itself as GAR's realization sibling and uses lazy-by-stage context.

## New GAR package facts

Current available GAR package metadata reports version `1.6.1`.
It requires capability `l9.authority.resolve`, requires `evidence.review`, and names `l9.work-state.route` as a downstream capability.
Its operating contract explicitly uses lazy projection/context resolution and bounded concern hydration.

## Evidence caution

This tracker is advisory and revision-bound to the observed repository state above. Before execution, refresh the target revision and re-run the disposition/reference census so stale paths are not treated as current reality.
## Cursor mode-routing evidence

- Cursor-Governance `rules/05-ask-mode.mdc` already distinguishes Ask Mode from Agent Mode behavior.
- `ops/hooks/before_submit_skill_router.py` currently sends only prompt text into `route_prompt(...)`; it does not consume composer mode.
- `ops/skill_routing/route_prompt.py` is the declared single scoring authority and currently supports one primary plus at most two supporting skills.
- Current Cursor hook documentation exposes `composer_mode` on `sessionStart` and permits `sessionStart` to export environment variables to subsequent hooks. The documented `beforeSubmitPrompt` payload exposes prompt/attachments plus common fields but not composer mode.
- This supports a session-mode routing prior without creating a second routing authority; because mode may become stale if changed after session start, prompt semantics must remain decisive.

