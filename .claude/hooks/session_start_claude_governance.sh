#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Governance — Claude Code SessionStart bootstrap (CLI · Web · Mobile).
#
# Mobile-safe by construction: git-tracked, no ~/.cursor dependency, no editor
# machine state. Locates the governance clone, surfaces resume context, injects
# Autonomy Surface Profile doctrine, compiles bounded-autonomy campaign state,
# and emits a Claude Code SessionStart `additionalContext` JSON blob on stdout.
#
# Registered from .claude/settings.json (see settings.template.json). Copy this
# file to <consumer-repo>/.claude/hooks/ and COMMIT it — on Claude Code Web and
# Mobile only committed files survive the clone into the sandbox.
#
# Contract: FAIL-OPEN. A hook must never block a session. Every failure degrades
# to a smaller context blob; the script always exits 0.
#
# Spec: environment/agents/adapters/claude-code/hooks/SESSION_START_SPEC.md
# Profile SSOT: ops/autonomy/surface_profile.yaml
# ---------------------------------------------------------------------------
set -uo pipefail

# Wall clock for the whole hook. Every bounded sub-operation below sizes itself
# against what is LEFT of the registration's `timeout`, not against a constant
# of its own: the repair used to be launched with a fixed 90 s ceiling inside a
# 30 s hook, which is not a long-running operation but an impossible one.
# Inherited by the bounded child (below) so its internal clamps are measured
# from when the HOOK started, not from when the child was forked.
_L9_HOOK_START="${_L9_HOOK_START:-$(date +%s)}"
# Same instant in the UTC form the launcher stamps its skip log with, so the
# skips recorded during THIS SessionStart can be told apart from older ones.
# Inherited by the child for the same reason as _L9_HOOK_START.
_L9_HOOK_START_ISO="${_L9_HOOK_START_ISO:-$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '')}"
# TERM->KILL grace the parent's deadline subtracts (see the deadline-safe
# block). One value, read by both ends, so the child's clamps and the parent's
# deadline cannot drift apart.
_L9_GRACE="${L9_SESSION_START_GRACE:-2}"

# Must agree with the `timeout` on this hook's entry in settings.template.json:
# this value sizes the clamping, that value is where the harness kills the hook,
# and a drift between them computes the clamp against a window that does not
# exist. Nothing renders one from the other — the agreement is held by
# tests/test_session_start_partial_emit.py::BudgetRegistrationLockstepTest, so
# a bump in one place fails there rather than degrading silently in production.
#
# Measured one second INSIDE the parent's deadline (budget - reserve - grace):
# a bounded engine that expires at its own ceiling is then reported by the
# child as TIMED OUT, with the run still completing, rather than being torn
# down together with the child at the same instant and read as PARTIAL.
_l9_budget_left() {
  local total="${L9_SESSION_START_BUDGET:-30}" reserve="${L9_SESSION_START_RESERVE:-4}"
  echo $(( total - ( $(date +%s) - _L9_HOOK_START ) - reserve - _L9_GRACE - 1 ))
}

# Every multi-second sub-engine below runs through this, and the platform
# contract is why it is not optional: Claude Code DISCARDS a hook's output when
# the hook reaches its registration `timeout` (hooks reference, "Timeouts"), so
# the TERM trap armed further down cannot rescue context from a harness kill —
# only finishing inside the budget can. A hosted session measured this hook at
# 29,620 ms against its 30,000 ms ceiling: after the repair had spent its clamp,
# the readiness emitter (90 s internal probe timeout) and the projection engine
# (600 s plugin fallback) still ran with no ceiling at all, 380 ms from losing
# every line accumulated above them.
#
# Returns 125 when fewer than $1 seconds remain, so the caller can NAME the
# deferral instead of starting work that can only be killed; 124 when the
# runner expires. Unbounded only when run_with_timeout is unavailable — the
# same fail-open the repair already takes.
_l9_bounded() {
  local floor="$1" left
  shift
  left="$(_l9_budget_left)"
  [ "$left" -ge "$floor" ] || return 125
  if type run_with_timeout >/dev/null 2>&1; then
    run_with_timeout "$left" "$@"
  else
    "$@"
  fi
}

resolve_governance_dir() {
  local d="$HOME/.cursor-governance"
  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$d" ]; then
    : # ignored — shared contract is always $HOME/.cursor-governance
  fi
  [ -f "$d/CANONICAL_LAW.md" ] && { printf '%s' "$d"; return 0; }
  return 1
}

json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

# Written by the child as the LAST thing it does, on every completion path
# (including the early returns that legitimately emit nothing), and stripped by
# the parent. Its ABSENCE is what "truncated" means.
#
# The child's exit status cannot carry that meaning: once the deadline tears
# down the child's whole process group, the child's own TERM trap runs and it
# exits 0 like any clean finish, so a status check reports a truncated run as
# complete. Completion is a fact about reaching the end, not about how the
# process died — so the child states it, rather than the parent inferring it.
_L9_DONE_MARK="__L9_SESSIONSTART_COMPLETE__"

_L9_EMITTED=0
emit() {
  [ "$_L9_EMITTED" = "1" ] && exit 0
  _L9_EMITTED=1
  # In the bounded child every line is already durable in $_L9_CTX_FILE and the
  # PARENT owns the single JSON write, so the child's job here is only to mark
  # the run complete and stop.
  if [ "${_L9_ROLE:-parent}" = "child" ]; then
    [ -n "$_L9_CTX_FILE" ] && printf '%s\n' "$_L9_DONE_MARK" >>"$_L9_CTX_FILE" 2>/dev/null
    exit 0
  fi
  local ctx
  ctx=$(json_escape "$1")
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
  exit 0
}

# The DEGRADED INLINE path's delivery, and only that path's: when no sidecar
# file could be created, the parent/child split below does not happen, LINES is
# the only record, and this trap is the only thing that can emit it. On the
# normal path the parent owns delivery and this is unreachable for the child
# (which returns early) and unarmed for the parent.
#
# It is kept because the inline path is real, not because it is sufficient: a
# trap cannot run while bash sits in a foreground child, which is why delivery
# does not rest on it any more. See the deadline-safe block below.
#
# FAIL-OPEN is not the same as FAIL-SAFE, and the difference is this function.
# Everything below accumulates into LINES and, on that path, is emitted by ONE
# call on the last line, so the hook is resilient to every failure it
# anticipated (missing SSOT, unreadable profile, absent loader — each degrades
# to a WARN line) and was totally
# fragile to the one it did not: running out of wall clock. A hosted container
# recorded `duration_ms 30008, exit_code 1, aborted true` on this hook and the
# session received NO governance context whatsoever — not a smaller blob, none.
# Emitting what has accumulated restores the contract the header already claims.
_l9_emit_partial() {
  [ "$_L9_EMITTED" = "1" ] && exit 0
  # The child's lines are already durable and the PARENT declares the
  # truncation, because it — unlike the dying child — knows the exit status.
  [ "${_L9_ROLE:-parent}" = "child" ] && exit 0
  say "WARN: SessionStart reached its timeout budget — the context above is PARTIAL."
  say "      Raise this hook's timeout, or run 'make claude-install' for the full report."
  emit "$(printf '%s\n' "${LINES[@]}")"
}

# --- Deadline-safe delivery -------------------------------------------------
# The trap above is correct and was still never given a turn to run. Bash
# dispatches a trap only BETWEEN commands, so a SIGTERM arriving while this
# script is blocked in a FOREGROUND child — a bounded probe, the installer
# repair — is queued behind that child. The harness recorded `hook_cancelled`
# 14 ms after its own 30 s deadline and read nothing, while every line the hook
# had accumulated sat in a bash array that died with the process.
#
# So delivery no longer rests on being signalled politely. It rests on two
# properties that hold no matter how anything dies:
#
#   1. Every line is durable the instant it is produced — `say` appends to
#      $_L9_CTX_FILE — so TERM, KILL, or a wedged grandchild cannot erase what
#      was already accumulated.
#   2. The work runs as a BOUNDED CHILD and the shell that emits is its PARENT.
#      The shell that must speak is therefore never the shell that can run
#      long: it emits by NORMAL EXIT inside the registration timeout, and a
#      hook that exits normally is read where a cancelled one is not.
#
# The trap stays armed for the degraded inline path below (no mktemp, no
# bounder), which is the only path that still depends on it.
# The parent's single delivery path: whatever the child made durable, plus an
# honest note when it did not finish. Used both on the normal return and from
# the parent's signal trap, so there is exactly one way this hook speaks.
_l9_emit_sidecar() {                # optional: child exit status
  [ "$_L9_EMITTED" = "1" ] && exit 0
  local rc="${1:-0}" ctx=""
  # Reap the watchdog before leaving. Orphaned, it would outlive this process
  # and fire `kill` at a PID the kernel may since have handed to someone else.
  [ -n "${_l9_watchdog:-}" ] && kill "$_l9_watchdog" 2>/dev/null
  # Tear down the whole child GROUP, not just the child. Emitting and exiting
  # is not enough on its own: a surviving grandchild inherits this hook's
  # stdout/stderr and holds those pipes open, so a reader waiting for EOF —
  # the harness included — blocks for as long as the orphan lives, which is
  # the original hang wearing a different hat (measured: reader blocked the
  # full 8 s after the parent had already exited). Reached from the trap too,
  # where the child is still running.
  [ -n "${_l9_child:-}" ] && kill -TERM "-${_l9_child}" 2>/dev/null
  [ -n "${_l9_child:-}" ] && kill -KILL "-${_l9_child}" 2>/dev/null
  # The child's diagnostics, replayed onto the parent's stderr now that no
  # descendant can hold it open.
  case "${_l9_errlog:-}" in
    ""|/dev/null) : ;;              # never rm the fallback sink
    *)
      [ -s "$_l9_errlog" ] && cat "$_l9_errlog" >&2 2>/dev/null
      rm -f "$_l9_errlog" 2>/dev/null
      ;;
  esac
  [ -n "$_L9_CTX_FILE" ] && ctx="$(cat "$_L9_CTX_FILE" 2>/dev/null || true)"
  [ -n "$_L9_CTX_FILE" ] && rm -f "$_L9_CTX_FILE" 2>/dev/null
  # Complete iff the child said so, before the marker is stripped from what
  # the model sees.
  local complete=0
  case "$ctx" in *"$_L9_DONE_MARK"*) complete=1 ;; esac
  ctx="$(printf '%s' "$ctx" | grep -vF "$_L9_DONE_MARK" 2>/dev/null || true)"
  if [ "$complete" = "0" ]; then
    ctx="${ctx}
WARN: SessionStart reached its timeout budget — the context above is PARTIAL (child_rc=${rc}).
      Raise this hook's timeout, or run 'make claude-install' for the full report."
  fi
  emit "$ctx"
}

_L9_ROLE="${_L9_ROLE:-parent}"
_L9_CTX_FILE="${_L9_CTX_FILE:-}"
if [ "$_L9_ROLE" = "parent" ]; then
  _L9_CTX_FILE="$(mktemp "${TMPDIR:-/tmp}/l9-sessionstart.XXXXXX" 2>/dev/null || true)"
  if [ -n "$_L9_CTX_FILE" ]; then
    # Armed BEFORE the child is forked. Between the fork and the emit the parent
    # is otherwise a plain shell, so SIGTERM's default action would kill it and
    # throw away the very file the child had been filling — the original bug,
    # relocated one process up.
    trap '_l9_emit_sidecar 143' TERM INT
    # Strictly inside the registration timeout. The TERM->KILL grace is
    # subtracted HERE rather than added after, so the worst case — a child that
    # ignores TERM and has to be killed — still lands at budget-reserve and the
    # reserve stays a reserve. Budget and registration are held in lockstep by
    # tests/test_session_start_partial_emit.py::BudgetRegistrationLockstepTest.
    _l9_grace="$_L9_GRACE"
    _l9_deadline=$(( ${L9_SESSION_START_BUDGET:-30} - ${L9_SESSION_START_RESERVE:-4} - _l9_grace ))
    [ "$_l9_deadline" -lt 1 ] && _l9_deadline=1

    # BACKGROUND + `wait`, deliberately, not `timeout`:
    #   * `wait` is interruptible. Bash dispatches a trap the moment a signal
    #     arrives during `wait`, where a FOREGROUND child defers it until that
    #     child returns — which is exactly how the armed-and-correct trap this
    #     hook already had never got a turn to run.
    #   * `timeout` puts its child in a NEW process group (observed: parent
    #     pgid 4256, child subtree 4260). A group-kill aimed at this hook would
    #     then reach the parent only, leaving the real work orphaned and the
    #     parent blocked on a `timeout` that still waits out its full deadline.
    #   * it removes the dependency on GNU timeout/gtimeout being installed.
    # `set -m` makes the background child lead its OWN process group, so the
    # deadline can tear down the child AND every descendant with one signal.
    # Killing the child alone leaves grandchildren orphaned and holding this
    # hook's inherited pipes (see _l9_emit_sidecar).
    #
    # The child also gets its own stderr sink rather than inheriting the
    # hook's, so no descendant can hold the reader's stderr open either; the
    # parent replays it below, so nothing is lost, only unhooked from the pipe.
    _l9_errlog="$(mktemp "${TMPDIR:-/tmp}/l9-sessionstart-err.XXXXXX" 2>/dev/null || echo /dev/null)"
    set -m
    _L9_ROLE=child _L9_CTX_FILE="$_L9_CTX_FILE" _L9_HOOK_START="$_L9_HOOK_START" \
      _L9_HOOK_START_ISO="$_L9_HOOK_START_ISO" \
      bash "$0" "$@" >/dev/null 2>"$_l9_errlog" &
    _l9_child=$!
    set +m
    # The deadline, enforced without blocking the parent. KILL follows TERM so a
    # child wedged inside a grandchild of its own still cannot outlive the
    # window: this hook's obligation is to have spoken, not to have finished.
    ( sleep "$_l9_deadline";  kill -TERM "-${_l9_child}" 2>/dev/null
      sleep "$_l9_grace";     kill -KILL "-${_l9_child}" 2>/dev/null ) >/dev/null 2>&1 &
    _l9_watchdog=$!
    wait "$_l9_child"; _l9_rc=$?
    _l9_emit_sidecar "$_l9_rc"
  fi
  # No temp file to make context durable: fall through and run inline, exactly
  # as before, with the trap as the only delivery path. Degraded, never silent.
  _L9_CTX_FILE=""
fi

# Cursor also loads projected .claude/settings.json in this repo. This hook is
# Claude Code SessionStart only. Running it under Cursor scores that session
# with cloud account-field drift, broker probes, and never_ran installer
# receipts that cannot pass here. Skip unless surface_detect says Claude.
# Marker SSOT: ops/scripts/lib/surface_detect.sh (twin of surface_detect.py).
# Prefer this checkout's tree (walk up for ops/scripts/lib), then the live SSOT.
_L9_HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_L9_SD_LIB=""
_L9_WALK="$_L9_HOOK_DIR"
while [ -n "$_L9_WALK" ] && [ "$_L9_WALK" != "/" ]; do
  if [ -f "$_L9_WALK/ops/scripts/lib/surface_detect.sh" ]; then
    _L9_SD_LIB="$_L9_WALK/ops/scripts/lib/surface_detect.sh"
    break
  fi
  _L9_WALK="$(dirname "$_L9_WALK")"
done
if [ -z "$_L9_SD_LIB" ] && [ -f "${HOME}/.cursor-governance/ops/scripts/lib/surface_detect.sh" ]; then
  _L9_SD_LIB="${HOME}/.cursor-governance/ops/scripts/lib/surface_detect.sh"
fi
if [ -n "$_L9_SD_LIB" ]; then
  # shellcheck source=../../../../ops/scripts/lib/surface_detect.sh
  . "$_L9_SD_LIB"
  case "$(l9_detect_surface)" in
    claude-code|claude-code-remote) : ;;
    *) emit "" ;;
  esac
else
  # Detector unavailable means surface identity is unknown. This is an
  # observer-class hook, so unknown must not inject Claude context (ADR-0029:
  # no private marker list here either). The detector ships WITH governance,
  # so this is also exactly the shape of a session whose environment was never
  # provisioned — the one case the committed consumer copy exists for, reached
  # through the registration's launcher-missing fallback. Say only the
  # surface-neutral fact: no banner, no doctrine, no identity, just where the
  # SSOT is missing and how to obtain it. A governance tree that is present
  # but lacks its own detector is a foreign or partial tree: stay silent.
  if [ -f "$HOME/.cursor-governance/CANONICAL_LAW.md" ]; then
    emit ""
  fi
  _l9_neutral="$(printf '%s\n' \
    "governance SSOT: NOT FOUND — web/setup.sh must clone GitHub main to \$HOME/.cursor-governance" \
    "remote: https://github.com/Quantum-L9/Cursor-Governance (branch main)" \
    "surface: unknown (governance surface detector unavailable) — no surface-specific context injected")"
  # `say` is not defined yet at this point and the bounded CHILD never prints:
  # its emit only marks completion, and the parent delivers the sidecar. So
  # make the lines durable the same way `say` would, then complete; the
  # degraded inline path (no sidecar) emits them directly.
  if [ "${_L9_ROLE:-parent}" = "child" ] && [ -n "${_L9_CTX_FILE:-}" ]; then
    printf '%s\n' "$_l9_neutral" >>"$_L9_CTX_FILE" 2>/dev/null
    emit ""
  fi
  emit "$_l9_neutral"
fi
unset _L9_SD_LIB _L9_WALK _L9_HOOK_DIR

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"

# The locked interpreter is resolved inside the `resolve_governance_dir` block
# below; this is the fallback for when that block does not run. Without it,
# `emit_bootstrap_status "$PY"` referenced an unset variable under `set -u` and
# the hook died with `PY: unbound variable`, exit 1, having emitted NOTHING —
# so the one message that branch exists to deliver ("governance SSOT: NOT
# FOUND — web/setup.sh must clone ..."), the message that tells an operator
# their environment was never provisioned, could never reach anyone.
PY="python3"

LINES=()

# The single append point for context. Writing to $_L9_CTX_FILE as each line is
# produced is what makes a budget kill survivable: the record is durable before
# anything can go wrong, rather than being assembled at the end by a process
# that may not reach the end. LINES stays for the degraded inline path, where
# the trap is still the delivery route.
say() {
  LINES+=("$@")
  [ -n "$_L9_CTX_FILE" ] && printf '%s\n' "$@" >>"$_L9_CTX_FILE" 2>/dev/null
  return 0
}

# Armed only once LINES exists: under `set -u` a trap that expands an unset
# array would fail exactly when it is most needed. EXIT is included because the
# budget kill is not the only way this script can stop early — an unbound
# variable or a failed builtin ends it just as silently, and the emit guard
# makes the normal path a no-op here.
trap '_l9_emit_partial' TERM INT EXIT
say "L9 Governance — Claude Code session"
say "workspace: $WORKSPACE"

# Hosted/cloud: a raw pre-commit hook is a forbidden install (it runs the
# catalog without the surface-aware SKIP list). Fail-open.
if [ "${SKIP_PLUGIN_MARKETPLACE:-}" = "true" ] || [ -n "${CLAUDE_CODE_REMOTE:-}" ]; then
  gitdir=$(git -C "$WORKSPACE" rev-parse --git-dir 2>/dev/null || true)
  if [ -n "$gitdir" ]; then
    case "$gitdir" in
      /*) ;;
      *) gitdir="$WORKSPACE/$gitdir" ;;
    esac
    hook="$gitdir/hooks/pre-commit"
    if [ -e "$hook" ]; then
      rm -f "$hook" 2>/dev/null || true
      say "cloud hygiene: removed forbidden raw .git/hooks/pre-commit"
    fi
  fi
fi

# --- Cloud-only governance refresh (CLAUDE_CODE_REMOTE=true) -----------------
# Anthropic documents CLAUDE_CODE_REMOTE=true as the supported discriminator
# for cloud-session-only setup. In cloud, the governance clone is an ephemeral
# environment artifact: refresh it from origin/main so every session starts on
# the current tip, and record the exact revision. On a local developer
# checkout (CLI / Desktop) NEVER reset — inspect and report only.
# The receipt is JSON with a UTC timestamp and a TTL (INV-2). It used to be the
# single word `fresh` plus a short SHA — a claim with no expiry, so a receipt
# written at environment-build time still read `fresh 941ab77` days later while
# the clone sat four commits behind main (audit B-05). A receipt that cannot go
# stale is a receipt that always reads healthy. `state` here is the AT-WRITE
# value; every reader recomputes it from refreshed_at + ttl_seconds and from the
# recorded SHAs (see ops/scripts/governance_refresh_receipt.py).
CLOUD_REFRESH_RECEIPT="${L9_GOV_REFRESH_RECEIPT:-$HOME/.l9/claude/gov-refresh.json}"

# Written with printf rather than through python3 on purpose: this hook must
# still leave a trace on a runtime where no interpreter is usable, which is
# precisely the runtime whose staleness we are trying to detect.
# Any value interpolated below is squashed to a single token first. A receipt
# writer must not be able to emit invalid JSON no matter what git hands it.
json_token() { printf '%s' "$1" | tr -d '\n\r\t"\\' | head -c 64; }

write_refresh_receipt() {
  local outcome="$1" local_sha="$2" origin_sha="$3" behind="$4" state="$5" ts
  outcome="$(json_token "$outcome")"
  local_sha="$(json_token "$local_sha")"
  origin_sha="$(json_token "$origin_sha")"
  state="$(json_token "$state")"
  case "$behind" in (''|*[!0-9-]*) behind=-1 ;; esac
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')"
  mkdir -p "$(dirname "$CLOUD_REFRESH_RECEIPT")" 2>/dev/null || return 0
  printf '{\n' > "$CLOUD_REFRESH_RECEIPT"
  printf '  "schema": "l9.governance-refresh.v1",\n' >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "outcome": "%s",\n' "$outcome" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "local_sha": "%s",\n' "$local_sha" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "origin_sha": "%s",\n' "$origin_sha" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "refreshed_at": "%s",\n' "$ts" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "ttl_seconds": %s,\n' "${L9_GOV_REFRESH_TTL:-3600}" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "commits_behind": %s,\n' "$behind" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "state": "%s"\n' "$state" >> "$CLOUD_REFRESH_RECEIPT"
  printf '}\n' >> "$CLOUD_REFRESH_RECEIPT"
}

# A depth-1 clone has no ancestry to walk, so a numeric distance is frequently
# uncomputable. Report -1 for "unknown" rather than 0, which would read as
# up-to-date — the same class of lie this section is removing.
commits_behind() {
  git -C "$1" rev-list --count "$2..$3" 2>/dev/null || echo -1
}

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if GOV=$(resolve_governance_dir); then
    GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
    GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
    # The reset below is `checkout -f`, which DISCARDS uncommitted work and moves
    # HEAD off whatever branch is checked out. That is correct for the ephemeral
    # cloud clone it is written for, and destructive for anything else. It ran
    # unguarded, so a governance checkout carrying in-flight work — reachable
    # here whenever $HOME/.cursor-governance resolves to a working clone rather
    # than the throwaway one — lost that work silently, HEAD included. The reset
    # only ever has something to do on a clean clone, so refusing a dirty one
    # costs the intended path nothing and makes the destructive case impossible.
    # TRACKED changes only. `checkout -f` discards tracked modifications and
    # staged content — what this session actually lost — but leaves untracked
    # files alone, so counting them would refuse a reset that was never
    # dangerous and strand the ephemeral clone (a fresh one legitimately
    # carries untracked bootstrap residue).
    gov_dirty=$(git -C "$GOV" status --porcelain --untracked-files=no 2>/dev/null | head -c 1)
    if [ -n "$gov_dirty" ]; then
      local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
      write_refresh_receipt reset-skipped-dirty "$local_sha" unknown -1 stale
      say "governance refresh: WARN $GOV has uncommitted changes — reset SKIPPED (refusing to discard in-flight work)"
    elif git -C "$GOV" fetch --depth 1 origin "$GOV_BRANCH" >/dev/null 2>&1; then
      remote_sha=$(git -C "$GOV" rev-parse --verify --quiet FETCH_HEAD 2>/dev/null || echo 'unknown')
      if git -C "$GOV" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
        write_refresh_receipt fetched "$local_sha" "$remote_sha" \
          "$(commits_behind "$GOV" HEAD FETCH_HEAD)" fresh
        say "governance refresh: cloud session — reset ephemeral clone to origin/$GOV_BRANCH"
      else
        local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
        write_refresh_receipt reset-failed "$local_sha" "$remote_sha" \
          "$(commits_behind "$GOV" HEAD FETCH_HEAD)" stale
        say "governance refresh: WARN reset to origin/$GOV_BRANCH failed — reusing clone"
      fi
    else
      local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
      # The fetch failed, so origin is genuinely unknown — not "equal to local".
      write_refresh_receipt fetch-failed "$local_sha" unknown -1 unknown
      say "governance refresh: WARN fetch origin/$GOV_BRANCH failed — reusing clone (may be stale)"
    fi
    # Dependency provisioning is NOT run from here. It was, and it is why this
    # hook never finished: `session_deps_cloud.sh` blocks for its own 20 s
    # budget while pip resolves a consumer workspace (one observed run cloned a
    # git dependency and downloaded wheels), so ~25 s of a 30 s hook was spent
    # before the reporting this hook exists for had begun. SessionStart hooks
    # run CONCURRENTLY — the harness spawned indices 0/1/2 within 4 ms of each
    # other — so deps now has its own registration in settings.template.json and
    # its own timeout, and costs this hook nothing instead of costing it
    # everything. See ADR/audit note in SESSION_START_SPEC.md.
    :
  fi
fi

if GOV=$(resolve_governance_dir); then
  # shellcheck source=/dev/null
  [ -f "$GOV/ops/scripts/lib/run_with_timeout.sh" ] && . "$GOV/ops/scripts/lib/run_with_timeout.sh"
  if ! type run_with_timeout >/dev/null 2>&1; then
    _HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    _REL_LIB="$_HOOK_DIR/../../../../ops/scripts/lib/run_with_timeout.sh"
    [ -f "$_REL_LIB" ] && . "$_REL_LIB"
  fi
  say "governance SSOT: $GOV (GitHub Quantum-L9/Cursor-Governance)"
  if [ -d "$GOV/.git" ]; then
    br=$(git -C "$GOV" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
    if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
      # Local/Desktop: this is a developer checkout — SessionStart NEVER resets
      # it. Report revision and drift against origin/main instead.
      say "governance rev: ${br}@${sha} (local checkout — SessionStart never resets it)"
      if [ "$br" != "main" ]; then
        say "WARN: governance checkout is not on main (branch: $br) — drift is expected for in-flight work; report only"
      fi
      if git -C "$GOV" fetch --depth 1 origin main >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
        remote_sha=$(git -C "$GOV" rev-parse --short FETCH_HEAD 2>/dev/null || echo "?")
        if [ "$local_sha" = "$remote_sha" ]; then
          say "governance drift: none (HEAD == origin/main @$local_sha)"
        else
          say "governance drift: local @$local_sha vs origin/main @$remote_sha"
        fi
      fi
    else
      say "governance rev: ${br}@${sha}"
    fi
  fi
  say "authority order: CANONICAL_LAW.md > Autonomy Surface Profile > AGENTS.md > skills > agent-invented contracts"
  if [ -d "$GOV/skills" ]; then
    n=$(find "$GOV/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    # -L is load-bearing: every entry under .claude/skills is a SYMLINK to a
    # directory in the governance clone. Without -L, find refuses to descend and
    # the count reports the handful of real directories -- it printed
    # "skills loadable: 1" against 54 resolvable skills, which is precisely the
    # line an operator reads to conclude that skills failed to load.
    loadable=0
    for d in "$WORKSPACE/.claude/skills" "$HOME/.claude/skills"; do
      if [ -d "$d" ]; then
        c=$(find -L "$d" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
        loadable=$((loadable + c))
      fi
    done
    say "skills available: $n l9-* skills under \$GOV/skills (invoke by name)"
    say "skills loadable: $loadable SKILL.md under .claude/skills discovery paths"
  fi

  # Two-clone topology: workspace checkout vs live SSOT SessionStart loaded.
  if git -C "$WORKSPACE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ws_root=$(git -C "$WORKSPACE" rev-parse --show-toplevel 2>/dev/null || echo "$WORKSPACE")
    ws_abs=$(cd "$ws_root" 2>/dev/null && pwd -P)
    gov_abs=$(cd "$GOV" 2>/dev/null && pwd -P)
    if [ -n "$ws_abs" ] && [ -n "$gov_abs" ] && [ "$ws_abs" != "$gov_abs" ]; then
      ws_sha=$(git -C "$ws_root" rev-parse --short HEAD 2>/dev/null || echo "?")
      gov_sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
      if [ -f "$ws_abs/CANONICAL_LAW.md" ] && [ -f "$ws_abs/AGENTS.md" ]; then
        say "two-clone: workspace $ws_abs @$ws_sha (intentional consumer checkout of Cursor-Governance)"
      else
        say "two-clone: workspace $ws_abs @$ws_sha (leftover or unknown second checkout)"
      fi
      say "two-clone: live SSOT $gov_abs @$gov_sha"
      say "two-clone: rules resolve from live SSOT (not the workspace clone)"
    fi
  fi

  # --- Autonomy Surface Profile doctrine (standing A4) ---------------------
  PROFILE_LOADER="$GOV/ops/autonomy/profile_loader.py"
  if [ -x "$GOV/.venv/bin/python3" ]; then
    PY="$GOV/.venv/bin/python3"
  elif [ -x "$GOV/.venv/bin/python" ]; then
    PY="$GOV/.venv/bin/python"
  else
    PY="python3"
  fi
  # --- Claude projection engine (repair stale managed state; fail-open) ----
  # SessionStart runs the SAME engine as install.sh (setup), so a cached
  # environment whose bootstrap never ran — or ran against an older governance
  # revision — reconciles here: skills/commands symlinks repaired, settings
  # merge-patched, rules mount retargeted, stale managed projections removed.
  # The engine writes ~/.l9/claude/projection-receipt.json. Fail-open: a
  # projection failure degrades to a WARN line, never blocks the session.
  PROJECTION_ENGINE="$GOV/ops/scripts/claude_projection.py"
  if [ "${L9_SKIP_SESSION_PROJECTION:-}" != "1" ] \
     && [ -f "$PROJECTION_ENGINE" ] && command -v "$PY" >/dev/null 2>&1; then
    # Bounded: the engine's own ceilings (30 s classify, 600 s plugin fallback)
    # are sized for install time, not for what is left of this hook.
    PROJECTION_LINE=$(_l9_bounded 5 "$PY" "$PROJECTION_ENGINE" --root "$GOV" --workspace "$WORKSPACE" \
      --summary 2>/dev/null | tail -1)
    _projection_rc=$?
    if [ "$_projection_rc" = 125 ]; then
      say "claude projection: DEFERRED — $(_l9_budget_left)s of hook budget left (needs >=5s); run 'make claude-install' to reconcile"
    elif [ "$_projection_rc" = 124 ]; then
      say "claude projection: TIMED OUT inside the hook budget — see ~/.l9/claude/projection-receipt.json"
    else
      case "${PROJECTION_LINE:-}" in
        projection=ok) say "claude projection: ok (receipt ~/.l9/claude/projection-receipt.json)" ;;
        projection=*)  say "claude projection: WARN ${PROJECTION_LINE#projection=} — see ~/.l9/claude/projection-receipt.json" ;;
        *)             say "claude projection: WARN engine produced no summary — run 'make claude-install'" ;;
      esac
    fi
  fi
  # Projection rewrites managed settings.env from the template. Re-apply the
  # hosted overlay after every SessionStart projection, not only install.sh.
  if [ "${SKIP_PLUGIN_MARKETPLACE:-}" = "true" ] || [ -n "${CLAUDE_CODE_REMOTE:-}" ]; then
    overlay="$GOV/environment/agents/adapters/claude-code/overlay_hosted_settings_env.py"
    if [ -f "$overlay" ] && command -v "$PY" >/dev/null 2>&1; then
      "$PY" "$overlay" --workspace "$WORKSPACE" >/dev/null 2>&1 || true
    fi
  fi

  if [ -f "$PROFILE_LOADER" ] && command -v "$PY" >/dev/null 2>&1; then
    PROFILE_BLOCK=$("$PY" "$PROFILE_LOADER" 2>/dev/null || true)
    if [ -n "$PROFILE_BLOCK" ]; then
      say "--- autonomy surface profile ---"
      while IFS= read -r line || [ -n "$line" ]; do
        say "$line"
      done <<< "$PROFILE_BLOCK"
    else
      say "autonomy profile: unreadable; continue under base governance"
    fi
  else
    say "autonomy profile: loader unavailable; continue under base governance"
  fi

  # --- Bounded-autonomy campaign context (fail-open; read-only probe) ------
  AUTONOMY_BOOTSTRAP="$GOV/environment/program-execution/peer_execution/autonomy/bootstrap.py"
  if [ -f "$AUTONOMY_BOOTSTRAP" ] && command -v "$PY" >/dev/null 2>&1; then
    AUTONOMY_CONTEXT=$(_l9_bounded 2 "$PY" "$AUTONOMY_BOOTSTRAP" --workspace "$WORKSPACE" 2>/dev/null)
    if [ $? = 125 ]; then
      say "bounded autonomy: DEFERRED — hook budget exhausted; continue under base governance"
    elif [ -n "$AUTONOMY_CONTEXT" ]; then
      say "--- bounded autonomy ---" "$AUTONOMY_CONTEXT"
    fi
  else
    say "bounded autonomy: runtime unavailable; continue under base governance"
  fi

  # --- Claude execution profile (surface personality; fail-open) -----------
  # Claude is the unleashed surface, Cursor is the constrained one. Resolve which
  # applies from the runtime — CLAUDE_CODE_REMOTE=true is the cloud discriminator
  # — never from model identity, and name anything that would silently re-impose
  # a ceiling (L9 lane caps, Claude Code's own subagent limits, workflow sizing).
  EXECUTION_PROFILE="$GOV/ops/autonomy/execution_profile.py"
  if [ -f "$EXECUTION_PROFILE" ] && command -v "$PY" >/dev/null 2>&1; then
    PROFILE_TEXT=$(_l9_bounded 2 "$PY" "$EXECUTION_PROFILE" --root "$GOV" --workspace "$WORKSPACE" 2>/dev/null)
    if [ $? = 125 ]; then
      say "claude execution profile: DEFERRED — hook budget exhausted; continue under base governance"
    elif [ -n "$PROFILE_TEXT" ]; then
      say "--- claude execution profile ---"
      while IFS= read -r line || [ -n "$line" ]; do
        say "$line"
      done <<< "$PROFILE_TEXT"
    else
      say "claude execution profile: unresolved; continue under base governance"
    fi
  fi

  # Skill-router readiness hint
  if [ -f "$GOV/ops/generated/skill-registry.json" ]; then
    say "skill-router: ops/generated/skill-registry.json ready (UserPromptSubmit)"
  fi
else
  say "governance SSOT: NOT FOUND — web/setup.sh must clone GitHub main to \$HOME/.cursor-governance"
  say "remote: https://github.com/Quantum-L9/Cursor-Governance (branch main)"
fi

# memory-bank/ retired — resume from Graphiti inject/PICKUP only (no T0 excerpt)

# --- Memory: single front door = Cursor Graphiti (CANONICAL_LAW §8)
say "shared memory: canonical memory control plane only (ops/memory; l9-graphite-memory, memory-control-plane/v1); no provider client, no L9_MEMORY_HTTP side door; memory-bank retired; memory never gates repository writes"

# --- L9 Claude environment status (from the installer receipt) --------------
# The canonical installer writes ~/.l9/claude/bootstrap-state.json
# (schema l9.claude-bootstrap.v1). Project it compactly so the model — and the
# operator on mobile — sees what is actually available instead of discovering
# bootstrap breakage when a later memory or publish operation fails.
emit_bootstrap_status() {
  local py="$1"
  local reader="$GOV/ops/scripts/claude_bootstrap_receipt.py"
  local refresh_reader="$GOV/ops/scripts/governance_refresh_receipt.py"

  # The projection used to parse the receipt inline, with its own idea of what
  # the fields mean. That second parser had no notion of an ABSENT receipt or an
  # EXPIRED one, so it reported silence as nothing-to-say and a stale receipt as
  # current — the same class of defect the receipt rewrite removed one layer
  # down (B-04, B-05). One reader, one set of rules.
  if [ -z "$py" ] || ! command -v "$py" >/dev/null 2>&1 || [ ! -f "$reader" ]; then
    say "L9 Claude environment: receipt reader unavailable — state UNKNOWN"
    return 0
  fi

  # Repair, do not reprint. The receipt carries its own remediation string and
  # SessionStart used to print it and move on, so a DEGRADED verdict was
  # inherited across sessions and days while the fix sat one line away. The
  # attempt is keyed on the GOVERNANCE REVISION, not on wall-clock time: the
  # installer writes a receipt stamped with the current revision, so a
  # successful repair suppresses the next attempt and a revision bump is the
  # only thing that re-arms it. That is what makes this converge instead of
  # re-running every session. Fail-open throughout — a repair that cannot run
  # degrades the session, it never blocks it.
  local state revision marker installer
  state="$("$py" "$reader" --read --json 2>/dev/null \
    | "$py" -c 'import json,sys
try:
    print(json.load(sys.stdin).get("state", ""))
except Exception:
    print("")' 2>/dev/null || true)"
  revision="$(git -C "$GOV" rev-parse HEAD 2>/dev/null || echo unknown)"
  marker="$HOME/.l9/claude/bootstrap-repair-${revision}.attempted"
  installer="$GOV/environment/agents/adapters/claude-code/install.sh"
  # The repair is attempted LAST, below, after every line this function is
  # contractually required to emit. It used to run HERE, ahead of them, and
  # on any runner whose receipt is absent it took its whole clamp and the
  # required reporting was never reached: CI emitted `bootstrap repair:
  # FAILED rc=124` and then PARTIAL, with the environment block and the
  # `governance refresh` projection both missing. Provisioning is explicitly
  # NOT one of the must-emit items (SESSION_START_SPEC), so it must never
  # preempt them.

  # A receipt written for a different directory reports READY for artifacts this
  # session never loads, so compare the wired workspace against this project.
  local wired block prefix
  wired="$("$py" -c 'import json,sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("workspace",""))
except Exception:
    print("")' "$HOME/.l9/claude/bootstrap-state.json" 2>/dev/null || true)"
  prefix=""
  if [ -n "$wired" ] && [ "$wired" != "$WORKSPACE" ]; then
    prefix="STALE: "
    say "STALE: bootstrap receipt workspace $wired != session $WORKSPACE"
  fi
  block="$("$py" "$reader" --read --reprobe 2>/dev/null || true)"
  if [ -n "$block" ]; then
    say "--- L9 Claude environment ---"
    while IFS= read -r line || [ -n "$line" ]; do
      say "${prefix}${line}"
    done <<< "$block"
  else
    say "L9 Claude environment: bootstrap receipt unreadable — run 'make claude-install'"
  fi

  if [ -f "$refresh_reader" ]; then
    local refresh
    refresh="$("$py" "$refresh_reader" --read 2>/dev/null || true)"
    [ -n "$refresh" ] && say "$refresh"
  fi

  case "$state" in
    ready|"") : ;;
    degraded)
      # `degraded` is the ONE non-ready state a re-run cannot change, and the
      # reader has already proved why by the time it says so. Its own ladder
      # returns `unknown` first for a receipt that covers another workspace,
      # carries no parseable stamp, outlived its TTL, or was produced against a
      # superseded governance revision — so `degraded` arriving here means the
      # receipt describes THIS workspace, is inside its TTL, and was written by
      # an installer run against the revision currently checked out. And
      # `degraded` is defined there as "an optional component is unavailable"
      # (`blocked` is the required-component state, and it still arms below).
      #
      # Re-running the installer inside what is left of a 30 s hook cannot make
      # an optional component available. Measured on a hosted container: the
      # provisioning `web/setup.sh` -> `install.sh` run wrote the receipt, this
      # hook read it seconds later, and spent 7 s of its budget reaching the
      # identical verdict. Hosted containers get a fresh clone and a fresh
      # ~/.l9 every session, so the per-revision marker bounds that to once per
      # revision — which on that surface is once per session, forever.
      #
      # Arming stays for every state a re-run can actually move: `never_ran`
      # (no bookkeeping), `failed` (died at a stage), `blocked` (a required
      # component unwired), and `unknown` — which is what an expired receipt or
      # a revision bump becomes, so auto-heal after an environment change is
      # preserved rather than traded away.
      say "bootstrap repair: NOT ARMED — receipt is 'degraded' (an optional component is"
      say "bootstrap repair:   unavailable) at ${revision:0:8}, which is this revision's own"
      say "bootstrap repair:   installer verdict; re-running cannot change it. Components and"
      say "bootstrap repair:   reasons are in the environment block above."
      say "bootstrap repair:   force a re-run with 'make claude-install' once the cause is fixed"
      ;;
    *)
      if [ ! -f "$marker" ] && [ -f "$installer" ]; then
        mkdir -p "$HOME/.l9/claude"
        # Clamp to what is LEFT of this hook's budget. A fixed 90 s ceiling
        # inside a 30 s hook cannot succeed — it can only be killed, and being
        # killed is what kept the receipt `failed` and the marker unwritten.
        _repair_left="$(_l9_budget_left)"
        _repair_cap="${L9_BOOTSTRAP_REPAIR_BUDGET:-90}"
        [ "$_repair_cap" -gt "$_repair_left" ] && _repair_cap="$_repair_left"
        if ! type run_with_timeout >/dev/null 2>&1; then
          say "bootstrap repair: SKIPPED — run_with_timeout.sh missing; installer not started"
        elif [ "$_repair_cap" -lt "${L9_BOOTSTRAP_REPAIR_MIN:-15}" ]; then
          say "bootstrap repair: DEFERRED — ${_repair_left}s of hook budget left, needs >=${L9_BOOTSTRAP_REPAIR_MIN:-15}s"
          say "bootstrap repair:   run 'make claude-install' to repair now (receipt: '$state')"
        else
          # The marker records that this REVISION was attempted, and it is
          # written BEFORE the attempt. Writing it only on success made the
          # repair self-perpetuating: the attempt could not finish inside the
          # budget, so the marker never appeared, so the next session re-armed
          # it and spent the whole budget again — for every session, forever.
          # An attempt that fails is still an attempt; a revision bump re-arms.
          printf '%s attempted state=%s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)" "$state" >"$marker"
          say "bootstrap repair: receipt was '$state' at ${revision:0:8} — running the installer once (${_repair_cap}s)"
          if run_with_timeout "$_repair_cap" \
            env L9_BOOTSTRAP_LOG_PATH="$HOME/.l9/claude/bootstrap-repair-${revision}.log" \
            bash "$installer" \
            >"$HOME/.l9/claude/bootstrap-repair-${revision}.log" 2>&1; then
            printf 'ok\n' >>"$marker"
          else
            _repair_rc=$?
            printf 'failed rc=%s\n' "$_repair_rc" >>"$marker"
            _repair_how="$(head -n 3 "$HOME/.l9/claude/bootstrap-repair-${revision}.log" | tr '\n' ' ')"
            say "bootstrap repair: FAILED rc=${_repair_rc} — ${_repair_how:-no log bytes}"
          fi
        fi
      fi
      ;;
  esac
}

# --- Account-field drift (WS-4.1) -------------------------------------------
# The Setup script and Environment variables fields are copy-pasted and drift
# from main invisibly — there is no way to read a field back from inside the
# sandbox. The stub stamps its revision, so the comparison is possible; doing it
# HERE is what makes it automatic rather than something an operator must
# remember to run (audit B-06, B-07).
emit_account_drift() {
  local py="$1"
  local verifier="$GOV/environment/agents/adapters/claude-code/verify_account_env.py"
  [ -f "$verifier" ] || return 0
  [ -n "$py" ] && command -v "$py" >/dev/null 2>&1 || return 0

  local out
  out="$(_l9_bounded 2 "$py" "$verifier" 2>/dev/null)"
  if [ $? = 125 ]; then
    # Not checked is not the same as matching: say so rather than stay quiet.
    say "account field drift: NOT CHECKED — hook budget exhausted"
    return 0
  fi
  # Report only when something is wrong; a matching environment stays quiet.
  if printf '%s' "$out" | grep -q 'DRIFT:'; then
    say "--- account field drift ---"
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        *DRIFT:*|*"    "*|*Repair:*) say "$line" ;;
      esac
    done <<< "$out"
  fi
}

# --- Capability plane readiness (authenticated; never a secret) -------------
# Graphiti over HTTPS (CLI + MCP). Distinct reasons: connect vs 401 vs 403
# allowlist. Empty hydrate is honest; memory never gates repository writes.
# Capability broker retired 2026-08-29 (never shipped; not probed).
emit_capability_readiness() {
  local py="$1"
  local receipt="$HOME/.l9/claude/readiness-receipt.json"
  [ -f "$receipt" ] || return 0
  [ -n "$py" ] && command -v "$py" >/dev/null 2>&1 || return 0

  # Reuse the receipt from emit_readiness_receipt (one Graphiti probe).
  local parsed
  parsed="$("$py" -c '
import json, os, sys
path = os.path.expanduser("~/.l9/claude/readiness-receipt.json")
try:
    d = json.load(open(path, encoding="utf-8"))
except Exception:
    sys.exit(0)
print("receipt_generated_at=" + str(d.get("generated_at") or "unknown"))
print("memory.cli=" + str(d.get("memory_cli_status", "UNKNOWN")))
print("memory.mcp=" + str(d.get("memory_mcp_status", "UNKNOWN")))
print("memory_control_plane=" + str(d.get("memory_control_plane_status", "UNKNOWN")))
print("memory_transport=" + str(d.get("memory_transport", "UNKNOWN")))
notes = d.get("notes") if isinstance(d.get("notes"), dict) else {}
print("primary_blocker=" + str(notes.get("memory_control_plane_status") or "none"))
' 2>/dev/null || true)"
  [ -n "$parsed" ] || return 0
  say "--- capability plane readiness ---"
  say "capability_broker=retired (never shipped; not probed)"
  say "secret_boundary_status=model-controlled (no broker/Infisical/Graphiti secret in this environment)"
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] && say "$line"
  done <<< "$parsed"
  # .mcp.json is the single authority over the servers GOVERNANCE configures --
  # not over the session's MCP surface. Hosted surfaces inject servers (github,
  # and others) that governance neither configures nor gates, so the unqualified
  # "single MCP authority" claim was false wherever it mattered.
  _mcp_list='
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        servers = sorted((json.load(fh).get("mcpServers") or {}))
except Exception:
    sys.exit(1)
print(", ".join(servers) if servers else "none")
'
  if type run_with_timeout >/dev/null 2>&1; then
    mcp_managed="$(run_with_timeout 10 python3 -c "$_mcp_list" "$WORKSPACE/.mcp.json" 2>/dev/null || echo "unreadable")"
  else
    mcp_managed="$(python3 -c "$_mcp_list" "$WORKSPACE/.mcp.json" 2>/dev/null || echo "unreadable")"
  fi
  say "mcp_configuration=.mcp.json is a projection of mcp.template.json; it is the single authority over GOVERNANCE-MANAGED servers only [$mcp_managed]"
  say "mcp_platform_injected=this surface may also carry platform-injected servers that governance does not configure or gate -- read the live tool surface, not this file, for the full set"
}

# --- Final machine-readable readiness receipt (Phase 7) ---------------------
# One truthful receipt (schema l9.claude-readiness.v1) aggregating projection,
# MCP, Graphiti, Makefile facade, dispatcher, merge-authority posture, secret
# boundary, and governance-SHA freshness. Written to
# ~/.l9/claude/readiness-receipt.json; a compact block is surfaced here so the
# operator sees the real contract, not a symlink-existence guess.
emit_readiness_receipt() {
  local py="$1"
  local emitter="$GOV/ops/scripts/emit_claude_readiness.py"
  [ -f "$emitter" ] || return 0
  [ -n "$py" ] && command -v "$py" >/dev/null 2>&1 || return 0
  # --reuse-fresh: the emitter hands back the on-disk receipt when it is inside
  # its own TTL, describes this workspace, and was built against the governance
  # SHA checked out right now; otherwise it rebuilds. Measured on a hosted
  # container: the rebuild is ~6 s of a ~9 s hook — 5.3 s of it the memory
  # diagnostics probe — re-run on every startup, resume AND compaction to
  # re-measure a receipt that already declares its validity window, while the
  # sibling memory_prefetch hook was crossing the same control plane for this
  # session's real hydration. The block names its source and age either way.
  # Bounded: the emitter's memory probe alone carries a 90 s internal timeout.
  local block rc
  block="$(_l9_bounded 8 "$py" "$emitter" --root "$GOV" --workspace "$WORKSPACE" --read --reuse-fresh 2>/dev/null)"
  rc=$?
  case "$rc" in
    125)
      say "claude readiness: DEFERRED — $(_l9_budget_left)s of hook budget left (needs >=8s); last receipt: ~/.l9/claude/readiness-receipt.json"
      return 0
      ;;
    124)
      say "claude readiness: TIMED OUT inside the hook budget — receipt not rebuilt this session"
      return 0
      ;;
  esac
  [ -n "$block" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    say "$line"
  done <<< "$block"
}

emit_bootstrap_status "$PY"
emit_account_drift "$PY"
emit_readiness_receipt "$PY"
emit_capability_readiness "$PY"

if [ "${SKIP_PLUGIN_MARKETPLACE:-}" = "true" ]; then
  say "Context7 (hosted skip): MCP tools absent — use skill l9-context7-docs"
fi

skill_log="$HOME/.claude/l9/skill-usage.jsonl"
if [ -f "$skill_log" ]; then
  skill_n=$(wc -l < "$skill_log" | tr -d ' ')
  say "skill-usage: $skill_log ($skill_n entries)"
else
  say "skill-usage: $skill_log (absent — logger never wrote)"
fi

# Sibling SessionStart hooks run CONCURRENTLY with this one — the platform
# offers no ordering — so on a cached hosted environment they dispatch against
# the governance revision checked out BEFORE the refresh above landed. A hook
# file that exists only on the new tip is then skipped by the launcher for
# exactly one session: observed as bootstrap_capability_preflight.sh recording
# "hook file absent" 4 s before the refresh receipt was written. The launcher
# logs every such skip; surface the ones from THIS SessionStart so the gap is
# visible in-session rather than discovered in a log afterwards.
_skip_log="${L9_HOOK_SKIP_LOG:-$HOME/.l9/claude/hook-skips.log}"
if [ -n "$_L9_HOOK_START_ISO" ] && [ -f "$_skip_log" ]; then
  _skips="$(awk -v since="$_L9_HOOK_START_ISO" '$1 >= since' "$_skip_log" 2>/dev/null | tail -n 5)"
  if [ -n "$_skips" ]; then
    say "hook skips this SessionStart (sibling hooks the launcher could not run; $_skip_log):"
    while IFS= read -r line || [ -n "$line" ]; do
      say "  $line"
    done <<< "$_skips"
  fi
fi

if [ -f "$GOV/ops/autonomy/breakglass_receipt.py" ]; then
  say "$("$PY" "$GOV/ops/autonomy/breakglass_receipt.py" --status 2>/dev/null || echo "publish-path grant: unread")"
fi
if ! "$PY" -c 'import socket;s=socket.socket();s.settimeout(0.3);s.connect(("127.0.0.1",7687));s.close()' 2>/dev/null; then
  say "itest: unavailable — neo4j absent or 127.0.0.1:7687 refused"
else
  say "itest: neo4j 127.0.0.1:7687 reachable — service-backed integration tests may run"
fi

CONTEXT=$(printf '%s\n' "${LINES[@]}")
emit "$CONTEXT"
