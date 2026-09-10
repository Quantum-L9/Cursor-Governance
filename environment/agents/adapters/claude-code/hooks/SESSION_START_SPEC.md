# SESSION_START_SPEC — Claude Code governance bootstrap

**Status:** authoritative contract for `session_start_claude_governance.sh`
**Profile SSOT:** `ops/autonomy/surface_profile.yaml`
**Install:** `ops/scripts/reconcile_claude_settings.py` copies this script into
`<repo>/.claude/hooks/` as a **committed file** (Mobile/Web survival). The
registration in `settings.template.json` dispatches through
`l9_hook_exec.sh` in `$HOME/.cursor-governance` and **falls back to that
committed copy** when the launcher is absent — which is the same condition as
governance being absent — so the `governance SSOT: NOT FOUND` line below can
actually reach a session whose environment was never provisioned. Before the
fallback the registration exited 0 silently on that path and the committed
copy was written, drift-checked and never executed. It is the only consumer
hook copy: a fail-open copy of the merge gate wrapper was projected beside it
and retired (gates dispatch only through the launcher, INV-1).

## Hard constraints

1. **Fail-open** — always exit 0; never block a session. Fail-open is not the
   same as fail-safe. Every bounded sub-operation sizes itself from what is
   LEFT of the registration's `timeout` (`_l9_budget_left`, via `_l9_bounded`),
   never from a constant of its own, and declines outright — with a named
   `DEFERRED` line — when too little remains. This is the only guarantee that
   works under the harness: the Claude Code hooks contract states that a
   `command` hook which reaches its `timeout` is cancelled **and its output
   discarded**, so nothing emitted after the ceiling reaches the session. A
   hosted container recorded `duration_ms 30008, exit_code 1, aborted true` on
   this hook and the session received NO governance context at all; a later
   one recorded `29620` ms against the 30000 ms ceiling with the readiness
   emitter (90 s internal probe timeout) and the projection engine (600 s
   plugin fallback) running unbounded after the repair had spent its clamp.
   The emit is additionally armed on `TERM`/`INT`/`EXIT`, so a hook stopped
   early by a signal or a failed builtin still delivers what it accumulated,
   flagged `PARTIAL` — a last resort for those paths, not a defence against
   the timeout.
1a. **Claude Code runtime only.** Surface identity comes from the canonical
    detector (`ops/scripts/lib/surface_detect.sh`, ADR-0029) — never from a
    private marker list in this hook. Any surface other than `claude-code` /
    `claude-code-remote` emits empty `additionalContext` and returns. Cursor
    loads projected `.claude/settings.json` in this repo; scoring a Cursor
    session with cloud account-field drift or broker probes is forbidden.
    When the detector itself is unavailable the surface is unknown and no
    surface-specific context is injected; because the detector ships with
    governance, that state is also an unprovisioned environment, and the hook
    then emits only the surface-neutral `governance SSOT: NOT FOUND` lines
    (no banner, no doctrine, no identity). A governance tree that is present
    but carries no detector is a foreign or partial tree and stays silent.
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

## Sibling ordering is not available; skips are surfaced

SessionStart hooks run concurrently and the platform offers no ordering, so
on a cached hosted environment the siblings (preflight, memory prefetch, deps)
dispatch against the governance revision checked out **before** this hook's
cloud refresh lands. A hook file that exists only on the new tip is skipped by
the launcher for exactly one session — observed as
`bootstrap_capability_preflight.sh hook file absent` recorded 4 s before the
refresh receipt. The launcher records every such skip in
`~/.l9/claude/hook-skips.log`; this hook reads the entries stamped at or after
its own start and emits them as `hook skips this SessionStart`, so the gap is
visible in-session. Recombining the siblings to force an order is not the fix
(see the dependency section below).

## Readiness receipt: reuse when fresh, rebuild otherwise

`ops/scripts/emit_claude_readiness.py --read --reuse-fresh` hands back the
on-disk `~/.l9/claude/readiness-receipt.json` when it is inside its own
`ttl_seconds`, describes this workspace, and carries the governance SHA
currently checked out; any other state rebuilds. Measured on a hosted
container the rebuild is ~6 s of a ~9 s hook — 5.3 s of it the memory
diagnostics probe — re-run on every startup, resume and compaction while the
sibling `memory_prefetch.py` was crossing the same control plane for the
session's real hydration. The block prints `receipt_source=reused|rebuilt`
beside `receipt_freshness`, and `make claude-readiness` always rebuilds.

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
- a hook stopped by a signal before its timeout still emits, with a `PARTIAL`
  warning line; a sub-engine that cannot fit in the remaining budget is named
  `DEFERRED` (or `TIMED OUT`) rather than started and killed
- when governance is absent AND the committed copy is present, the registered
  command itself still delivers the `governance SSOT: NOT FOUND` line
- When gov present, context contains `Autonomy Velocity Doctrine` (from Profile)
- Profile block sha256 matches `profile_loader.block_sha256()`
- When a bootstrap receipt exists, context contains the `L9 Claude environment`
  block with the receipt's per-step statuses; when absent, the absence is named

## Non-goals

- Skill scoring / Graphiti client / plugin classify / autonomy scheduler
- Blocking a session on a dependency install: the cloud session-deps helper is
  fingerprint-cached, budget-bounded, and registered separately, so it cannot
  consume this hook's budget at all
