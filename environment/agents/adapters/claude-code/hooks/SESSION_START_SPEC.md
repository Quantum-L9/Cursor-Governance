# SESSION_START_SPEC — Claude Code governance bootstrap

**Status:** authoritative contract for `session_start_claude_governance.sh`
**Profile SSOT:** `ops/autonomy/surface_profile.yaml`
**Install:** `ops/scripts/reconcile_claude_settings.py` copies this script into
`<repo>/.claude/hooks/` as a **committed file** (Mobile/Web survival).

## Hard constraints

1. **Fail-open** — always exit 0; never block a session. Fail-open is not the
   same as fail-safe: a hook that runs past its budget still delivers the
   context it had accumulated, flagged `PARTIAL`. Every bounded sub-operation
   sizes itself from what is LEFT of the registration's `timeout`
   (`_l9_budget_left`), never from a constant of its own, and declines outright
   when too little remains.

1a. **Delivery MUST NOT depend on a signal handler.** This was specified as a
    trap armed on `TERM`/`INT`/`EXIT`, and it failed twice in production
    (`duration_ms 30008, exit_code 1, aborted true`; then `durationMs 30014,
    timedOut true`) with the session receiving NO governance context at all —
    not a smaller blob, none. The trap was armed and correct both times. Bash
    dispatches a trap only BETWEEN commands, so a signal arriving while the
    hook is blocked in a FOREGROUND child (a bounded probe, the installer
    repair) is queued behind that child and never gets a turn; the harness
    records the cancellation ~14 ms later and reads nothing. The trap survives
    only as the backstop for the degraded inline path.

    Delivery instead rests on two properties that hold however anything dies:

    - **Durable-on-write.** Every context line is appended to `$_L9_CTX_FILE`
      by `say` the instant it is produced, so no death of any kind — `TERM`,
      `KILL`, a wedged grandchild — can erase what was accumulated. Nothing is
      assembled at the end by a process that may not reach the end.
    - **The emitter is the parent.** The work runs as a child; the shell that
      emits is its parent, so the shell that must speak is never the shell that
      can run long. It emits by NORMAL EXIT strictly inside the registration
      `timeout` (budget − reserve, then `+2s` before `KILL`), and a hook that
      exits normally is read where a cancelled one is not. The parent arms its
      own `TERM`/`INT` trap BEFORE forking, so a group-kill aimed at the child
      cannot take the parent's default-action death with it.

    The child MUST be backgrounded and awaited (`cmd & wait $!`), never run
    under `timeout`. `wait` is interruptible, so the parent stays responsive;
    `timeout` both blocks the parent and puts its child in a NEW process group
    (observed: parent pgid 4256, child subtree 4260), which hides the real work
    from any group-kill and leaves the parent waiting out the full deadline.
    The deadline is enforced by a watchdog subshell instead, which needs no
    external binary.

    Two further properties are load-bearing, and each was found by a test
    rather than by reasoning:

    - **Tear down the child's process GROUP, not the child.** Emitting and
      exiting does not end the hook's obligation: a surviving grandchild
      inherits the hook's stdout/stderr and holds those pipes open, so a reader
      waiting for EOF blocks for as long as the orphan lives (measured: a
      reader blocked the full 8 s after the parent had already exited — the
      original hang wearing a different hat). The child is therefore launched
      under `set -m` so it leads its own group, the deadline signals `-$pid`,
      and the child also gets its own stderr sink instead of inheriting the
      hook's.
    - **Completion is declared, never inferred from exit status.** Once the
      deadline tears down the group, the child's own `TERM` trap runs and it
      exits 0 exactly like a clean finish, so `rc` reports a truncated run as
      complete. The child instead appends `__L9_SESSIONSTART_COMPLETE__` to the
      context file as the last thing it does on every completion path; the
      parent strips the marker and declares `PARTIAL` when it is absent.
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
- a hook stopped by its timeout still emits, with a `PARTIAL` warning line —
  and emits it BEFORE the registration `timeout`, on its own, rather than
  relying on being signalled politely at it
- a group-kill mid-run still emits (the parent trap), and the emitted context
  contains the lines accumulated before the kill
- When gov present, context contains `Autonomy Velocity Doctrine` (from Profile)
- Profile block sha256 matches `profile_loader.block_sha256()`
- When a bootstrap receipt exists, context contains the `L9 Claude environment`
  block with the receipt's per-step statuses; when absent, the absence is named

## Non-goals

- Skill scoring / Graphiti client / plugin classify / autonomy scheduler
- Blocking a session on a dependency install: the cloud session-deps helper is
  fingerprint-cached, budget-bounded, and registered separately, so it cannot
  consume this hook's budget at all
