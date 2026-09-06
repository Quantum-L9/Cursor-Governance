# Claude Code capability + sanctioned finish path — compiled prompt

Compiled prompt added to the workspace on 2026-09-06. Not yet executed, not yet
validated as an `l9-plan` PLAN_DOCUMENT.

| Field | Value |
|---|---|
| Artifact | `claude-code-capability-and-finish-path-convergence.compiled-prompt.yaml` |
| Compiled prompt id | `claude_code_capability_permission_and_sanctioned_publish_convergence` |
| Target repository | `Quantum-L9/Cursor-Governance` |
| Status | **compiled, unexecuted** |

## What it asks for

Converge the Claude Code execution environment so that:

1. bare `git` / `gh` mutation is never the path the model reaches for;
2. Memory write capability and repository scope are acquired in one early
   deterministic preflight rather than mid-execution;
3. publication has exactly one agent-visible route —
   `PR_REMEDIATE=0 make pr` from the governance workspace.

It is a *repair* contract, not an instruction sheet: it requires fixing the
executable settings template, its reconciler, the projected `.claude/settings.json`,
the validator, the PreToolUse harness, the bootstrap, and the agent-facing
doctrine together, so no regeneration resurrects a removed publish route.

## Bindings resolved at placement time

These were established from the live session and are inputs the executing
session should not re-derive from guesswork:

- **Governance workspace** is `$HOME/.cursor-governance` (here: `/root/.cursor-governance`),
  the clone whose remote is `Quantum-L9/Cursor-Governance`. Base at placement
  time: `main@051c63c`. This is the `GOVERNANCE_WORKSPACE` the compiled prompt's
  `phase_6` requires as the publish cwd.
- **Repository scope** for `Quantum-L9/Cursor-Governance` was acquired through
  the supported Add Repo capability with `access: push` — the same capability
  `phase_3` names as the sole sanctioned acquisition owner. No `git clone`
  fallback was used, and none is needed.
- **Do not clone a second governance tree.** The Add Repo result proposes a
  clone at `/home/user/cursor-governance`. Creating it would violate the
  single-SSOT contract (`06-governance-ssot-paths`, `00-global`). The clone that
  already exists at `$HOME/.cursor-governance` is the one to use. This is itself
  an instance of the class of defect the compiled prompt targets: a platform
  affordance steering toward an acquisition path the harness forbids.

## Prerequisite before executing

`phase_0` requires binding a fresh full SHA of the target repository's current
default branch. `051c63c` above is the placement-time base, not that binding —
re-fetch before execution.

## Placement rationale

`docs/plans/claude-code/` is reserved for schema-validated `l9-plan`
PLAN_DOCUMENT pairs (`.plan.json` authoritative + `.plan.md` projection). This
artifact is neither, so filing it there would misrepresent it as validated. It
lives in the dated `WIP/` corpus until it is compiled into a PLAN_DOCUMENT or
a program-execution campaign.
