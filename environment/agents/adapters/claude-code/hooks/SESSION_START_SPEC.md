# SESSION_START_SPEC — Claude Code governance bootstrap

**Status:** authoritative contract for `session_start_claude_governance.sh`
**Profile SSOT:** `ops/autonomy/surface_profile.yaml`
**Install:** `ops/scripts/reconcile_claude_settings.py` copies this script into
`<repo>/.claude/hooks/` as a **committed file** (Mobile/Web survival).

## Hard constraints

1. **Fail-open** — always exit 0; never block a session. Fail-open is not the
   same as fail-safe: the emit is armed on `TERM`/`INT`/`EXIT`, so a hook killed
   at its `timeout` still delivers the context it had accumulated, flagged
   `PARTIAL`. A hosted container recorded `duration_ms 30008, exit_code 1,
   aborted true` on this hook and the session received NO governance context at
   all — not a smaller blob, none. Every bounded sub-operation sizes itself from
   what is LEFT of the registration's `timeout` (`_l9_budget_left`), never from
   a constant of its own, and declines outright when too little remains.
1a. **Claude Code runtime only.** If none of `CLAUDE_CODE_REMOTE=true`,
    `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, or `CLAUDE_CODE_SESSION_ID` is set,
    emit empty `additionalContext` and return. Cursor loads projected
    `.claude/settings.json` in this repo; scoring a Cursor session with cloud
    account-field drift or broker probes is forbidden.
2. Resolve governance only at `$HOME/.cursor-governance` (ignore other `L9_GOVERNANCE_DIR`).
3. Emit Claude SessionStart JSON envelope with `additionalContext`.
4. **Mobile-safe** — committed consumer copy must not require `~/.cursor`.
5. **No new brains** under `environment/agents/adapters/claude-code/` — call `ops/autonomy/*` and
   `environment/program-execution/peer_execution/autonomy/bootstrap.py` only.
6. Reconcile (`reconcile_claude_settings`) is **install-time**, not SessionStart-critical.

## Must emit when governance found

1. Governance rev (branch@sha) — on `CLAUDE_CODE_REMOTE=true` the ephemeral
   governance clone is refreshed from `origin/main` first (fetch, reset, record
   exact revision); on local/Desktop the checkout is **never reset** — report
   revision + drift against origin/main only.
2. Authority order including Autonomy Surface Profile
3. Verbatim Profile `session_start_block` via `ops/autonomy/profile_loader.py` (stdlib-only extract; no PyYAML required on SessionStart path)
4. Read-only autonomy `bootstrap.py` context when available
5. Skill-router readiness hint (`ops/generated/skill-registry.json`)
6. **L9 Claude environment status block** projected from
   `~/.l9/claude/bootstrap-state.json` (schema `l9.claude-bootstrap.v1`, written
   by `install.sh`): surface, execution (anthropic-cloud / local), governance
   rev, bootstrap, settings, capability broker, memory, skills, rules. An
   absent receipt is stated as such ("run `make claude-install` once"), never
   invented.

(Dependency provisioning is NOT one of these — see below.)

## Dependency provisioning is a sibling hook, not a subroutine

`hooks/session_deps_cloud.sh` (fingerprint-cached toolchain PER REPOSITORY +
pre-commit warm) carries its **own** SessionStart registration in
`settings.template.json`, with its own `timeout`. It used to be invoked from
inside this hook, which is why this hook could not finish: deps blocks for its
own budget while pip resolves a consumer workspace, so most of a 30 s window was
spent before the reporting this hook exists for had begun. SessionStart hooks
run **concurrently**, so a separate registration costs this hook nothing.

Consequences of that split, both load-bearing:

- This hook emits no `session deps:` line. Read the deps hook's own stdout.
- The detached worker runs under `setsid`, in its own process session, so it
  outlives the hook rather than being reaped with the hook's process group when
  the harness times it out. Its "continues in background" message was true only
  when it was not needed. Where `setsid` is unavailable the message says so
  instead of promising survival.
- The synchronous side waits on a `.done` file, not on `kill -0 $!`: the worker
  is no longer a child of the waiter.

## Bootstrap repair convergence

The installer repair launched from this hook is clamped to the remaining budget
and is **deferred**, with a named remediation, when less than
`L9_BOOTSTRAP_REPAIR_MIN` (15 s) is left. Its marker records the **attempt**,
written before the installer runs, with the outcome appended. Writing it only on
success made an unfinishable repair re-arm every session forever, spending the
whole budget each time to achieve nothing. Re-arming stays keyed on the
governance revision, which the marker path carries.

## Acceptance

- stdout is one JSON object with `hookSpecificOutput.hookEventName=SessionStart`
- exit code 0 even when gov missing, and the `governance SSOT: NOT FOUND` line
  is actually delivered on that path (it was not: `PY` was assigned only inside
  the governance-found branch, so `set -u` killed the hook with `PY: unbound
  variable` before it emitted anything)
- a hook stopped by its timeout still emits, with a `PARTIAL` warning line
- When gov present, context contains `Autonomy Velocity Doctrine` (from Profile)
- Profile block sha256 matches `profile_loader.block_sha256()`
- When a bootstrap receipt exists, context contains the `L9 Claude environment`
  block with the receipt's per-step statuses; when absent, the absence is named

## Non-goals

- Skill scoring / Graphiti client / plugin classify / autonomy scheduler
- Blocking a session on a dependency install: the cloud session-deps helper is
  fingerprint-cached, budget-bounded, and registered separately, so it cannot
  consume this hook's budget at all
