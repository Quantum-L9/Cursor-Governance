# ADR-0001: Claude Code bounded concurrent autonomy — PR convergence, human-approved merge

## Status

Accepted

## Date

2026-08-02

## Context

The Claude Code environment (`environment/claude-code/`) ran as a single-lane,
prompt-heavy session. Long-running, independent work (e.g. converging several
open PRs to green) required repeated human intervention and could not resume
after a session ended. We want unattended, correct completion of reversible work
without granting unbounded agent freedom, and without moving irreversible
external actions (merge) out of human control.

A packaged runtime (`claude-code-concurrent-autonomy`) introduced an action-graph
scheduler, durable digest-verified state, renewable leases, isolated git-worktree
lanes, a fan-in join barrier, and an exact-SHA merge-eligibility gate. As shipped,
its templates enabled **autonomous merge** (`merge_pull_request` in the allow-list)
by default. That collides with the L9 fail-closed norm for irreversible actions.

## Decision

Adopt the bounded-concurrency runtime under
`environment/agents/adapters/claude-code/autonomy/` (sole live home; the
transitional `environment/claude-code/autonomy` path is extinguished), with this
default posture in the committed `settings.template.json` and
`web/environment.env.example`:

- **Autonomy ENABLED by default.** Completed work opens a PR and is driven to
  green unattended. The scheduler runs only dependency-ready, non-conflicting
  actions (default 4 lanes, 2 mutation lanes).
- **Remediation to green is autonomous**, delegated to the `l9-pr-remediation`
  skill (read CI failures + review-bot comments → scoped fix → push → wait for
  re-run → repeat until green).
- **Autonomous merge is OFF.** `L9_AUTONOMY_AUTONOMOUS_MERGE=false`, and
  `merge_pull_request` is omitted from `permissions.allow` so every merge prompts
  for a human. The runtime *proves* merge eligibility (`merge_coordinator`) but
  does not press merge.
- **Destructive operations denied outright**: `git push --force/-f`,
  `git reset --hard`, `git clean -fd`, `gh pr merge --admin`.
- Authority and maturity are separate axes: `A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE`
  (what is authorized) vs `M4_ASSURANCE_GOVERNED` (proof required).

## Options considered

1. **Adopt with autonomous merge ON** (the pack's original templates). Rejected:
   removes the human gate on the one irreversible external action; contradicts
   fail-closed governance; the in-code exact-SHA gate is advisory, not enforced
   at the permission boundary.
2. **Adopt with merge default-OFF (human-approved) + autonomous remediation**
   (this decision). Chosen: captures the friction-elimination benefit (unattended
   PR convergence) while keeping merge under human control.
3. **Do not adopt; keep single-lane manual operation.** Rejected: does not meet
   the goal of resumable, unattended completion of independent work.

## Consequences

- Consumer repos that copy the templates get autonomous PR creation + CI
  remediation with no prompt; merges still require explicit human approval.
- New `L9_AUTONOMY_*` environment flags; per-workspace durable state under
  `L9_AUTONOMY_STATE_DIR` (default `.l9/autonomy/`, git-ignored). The SessionStart
  probe is read-only; only `init`/run create the state tree.
- **Merge gate (2026-08-06):** enforced at PreToolUse via
  `ops/autonomy/merge_gate.py` (Claude wrap:
  `environment/claude-code/hooks/merge_gate_wrap.py`). Permission omit of
  `merge_pull_request` remains. Standing A4 velocity doctrine is the
  Autonomy Surface Profile (`ops/autonomy/surface_profile.yaml`).
- The state digest is an unkeyed SHA-256: it detects corruption, not malicious
  tampering, and is never authoritative after GitHub/target identity drift.

## Addendum — Autonomy Surface Profile (2026-08-06)

Standing single-lane velocity on adapter surfaces does **not** require
`/autonomy` or auto-init of the Python campaign scheduler. SessionStart injects
the Profile `session_start_block`. Multi-lane fan-out still uses `/autonomy`.
`99-no-auto-commit` / `99-no-auto-commit` are waived on adapter surfaces per
Profile; Cursor is unchanged. See CANONICAL_LAW §6.1.

## Follow-ups

- Distribution-owner sign-off is required before `L9_AUTONOMY_AUTONOMOUS_MERGE`
  is ever set to `true`; that change would supersede this ADR.


## 2026-08-13 supersession note

Shared bounded-autonomy runtime home moves to `environment/program-execution/peer_execution/autonomy/` (see ADR-0017 and ADR-0021). This ADR keeps its title and historical Claude Code concurrent-autonomy decision. Do not retitle this file.

## 2026-08-17 supersession — autonomous merge enabled

Distribution-owner sign-off: `L9_AUTONOMY_AUTONOMOUS_MERGE=true` is the standing
Claude Code default. `ops/autonomy/merge_gate.py` reads that flag and allows
ordinary `gh pr merge --squash`. Force-push, hard-reset, destructive clean, and
`--admin` stay denied. Campaigns and `make pr` still do not merge. Agents still
merge only after `/l9-pr-remediation` reaches green + mergeable + resolved
review threads, oldest first. PE campaign packets still must not declare
`autonomous_merge` (`COMPATIBILITY.yaml`).

## 2026-08-26 supersession — autonomous-merge environment boolean retired

Supersedes the 2026-08-17 note above. `ops/autonomy/merge_gate.py` no longer
reads any environment boolean for merge authority: a standing variable set once
in the account/session configuration must never grant unattended merge. The
`L9_AUTONOMY_AUTONOMOUS_MERGE` flag is retired — it is removed from the Claude
Code settings template and account-field SSOT (`environment.env.example`), and
setting it has no effect. Merge is authorized only by a scoped, expiring receipt
that `/l9-pr-remediation` writes for the target repo (and PR), or by a human
per-session breakglass `L9_MERGE_AUTHORIZED=<reason>`. All other constraints
above (no force-push, no `--admin`, campaigns/`make pr` do not merge, merge only
after green + mergeable + resolved threads, oldest first) are unchanged.
