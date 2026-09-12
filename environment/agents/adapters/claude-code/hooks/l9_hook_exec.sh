#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code hook launcher — the single place that decides what happens
# when a hook cannot run.
#
# Every L9 hook registration in the settings triad routes through this file so
# the fail-open / fail-closed decision is made ONCE, in reviewable shell, rather
# than being re-typed inside eight `bash -c '...'` one-liners where a copy-paste
# slip silently disables a gate.
#
# THE DISTINCTION THIS FILE EXISTS TO ENFORCE (INV-1):
#
#   --class gate      A hook that DECIDES whether a tool call may proceed.
#                     merge_gate_wrap, local_execution_gate_wrap, memory_gate.
#                     If it cannot evaluate — no launcher, no hook file, no
#                     locked interpreter — it exits 2 and the tool call is
#                     BLOCKED. A gate that cannot evaluate has not passed;
#                     it has failed to run, and those are not the same thing.
#
#   --class observer  A hook that RECORDS or ENRICHES but decides nothing.
#                     skill_usage_logger, user_prompt_skill_router,
#                     context7_stack_pretool, memory_prefetch, memory_writeback.
#                     If it cannot run it exits 0 — but it appends a timestamped
#                     line to ~/.l9/claude/hook-skips.log first, so the skip is
#                     auditable rather than invisible.
#
# The audit that produced this file found all eight hooks exiting 0 on a missing
# $GOV/.venv, printing one stderr line that nothing on Mobile surfaces. Three of
# those eight were gates. A memory gate, a merge gate and a publish-path gate
# that all fail open are indistinguishable from gates that passed (finding B-03).
#
# Exit codes are Claude Code's hook contract, not ours:
#   0  proceed
#   2  block the tool call and surface stderr to the model
#
# Usage (from settings.json):
#   l9_hook_exec.sh --class gate     merge_gate_wrap.py
#   l9_hook_exec.sh --class observer skill_usage_logger.py
# ---------------------------------------------------------------------------
set -uo pipefail

HOOK_CLASS=""
HOOK_NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --class) HOOK_CLASS="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) HOOK_NAME="$1"; shift ;;
  esac
done

# A malformed registration must not be tolerated into a silent pass. We do not
# know whether the caller meant a gate, so we assume the stricter reading.
if [ -z "$HOOK_CLASS" ] || [ -z "$HOOK_NAME" ]; then
  printf 'l9-hook: malformed registration (class=%q name=%q) — refusing to guess\n' \
    "$HOOK_CLASS" "$HOOK_NAME" >&2
  exit 2
fi
case "$HOOK_CLASS" in
  gate|observer) : ;;
  *)
    printf 'l9-hook: unknown hook class %q (want gate|observer)\n' "$HOOK_CLASS" >&2
    exit 2
    ;;
esac

# INV-1b: the class is a property of the HOOK, not of the caller.
#
# This file exists so the fail-open/fail-closed decision is made once rather
# than re-typed inside eight `bash -c '...'` one-liners where a copy-paste slip
# silently disables a gate. It took --class on trust, so the slip it was built
# to prevent still worked: `--class observer memory_gate.py` exits 0 and the
# gate never evaluates, which is indistinguishable from a gate that passed.
#
# The table below is the authority. A registration that disagrees with it is a
# malformed registration, and malformed registrations already refuse to guess.
# A hook absent from the table keeps the caller's class, so adding an observer
# needs no edit here; every GATE is named, because that is the direction where
# being wrong is silent.
l9_required_class() {
  case "$1" in
    merge_gate_wrap.py|local_execution_gate_wrap.py|memory_gate.py|session_debt_wrap.py)
      printf 'gate' ;;
    *) printf '' ;;
  esac
}

_L9_REQUIRED="$(l9_required_class "$HOOK_NAME")"
if [ -n "$_L9_REQUIRED" ] && [ "$_L9_REQUIRED" != "$HOOK_CLASS" ]; then
  printf 'l9-hook: %s is registered --class %s but is a %s — refusing to downgrade it\n' \
    "$HOOK_NAME" "$HOOK_CLASS" "$_L9_REQUIRED" >&2
  exit 2
fi
unset _L9_REQUIRED

# ---------------------------------------------------------------------------
# Protocol version and launcher identification (hardening against launcher-absent).
#
# These exports let the SessionStart hook distinguish:
#   - Direct invocation (not launched through l9_hook_exec.sh at all)
#   - Pre-protocol launcher (old version without refresh code)
#   - Launcher crash mid-refresh (started but didn't complete)
#   - Normal operation (protocol version matches, attempt ID or outcome set)
#
# L9_LAUNCHER_PROTOCOL_VERSION: incremented when the launcher/hook contract changes.
#   v1 = original launcher, no cloud refresh
#   v2 = PR #548, cloud refresh with attempt ID binding
# L9_LAUNCHER_PID: this launcher's PID, for crash detection and diagnostics.
# L9_LAUNCHER_HOOK_START_EPOCH: when this launcher invocation started.
# ---------------------------------------------------------------------------
export L9_LAUNCHER_PROTOCOL_VERSION=2
export L9_LAUNCHER_PID=$$
export L9_LAUNCHER_HOOK_START_EPOCH
L9_LAUNCHER_HOOK_START_EPOCH=$(date +%s 2>/dev/null || echo 0)

# INV-1c: the governance tree this launcher dispatches out of is $HOME/.cursor-governance
# and nothing else. SESSION_START_SPEC hard constraint 2 states it for the
# SessionStart hook; it holds a fortiori for every gate, because what the
# launcher resolves here is BOTH the policy code it execs and the locked
# interpreter it execs that code on.
#
# This used to honour a divergent L9_GOVERNANCE_DIR whenever the named directory
# held a CANONICAL_LAW.md, guarding only the unexpanded literal '$HOME' case.
# The comment above the guard claimed the opposite — "honoured only when it
# agrees ... can never redirect a gate at its policy" — and the audit that
# replaced it demonstrated the gap by execution: with L9_GOVERNANCE_DIR pointed
# at a throwaway directory containing a stub CANONICAL_LAW.md, the launcher ran
# that directory's session_start_claude_governance.sh (injecting arbitrary
# additionalContext into the session) and then ran its memory_gate.py, as a
# gate, on its .venv interpreter, exiting 0. A gate whose policy and interpreter
# both come from an environment variable is not a gate.
#
# The sanctioned configuration never needed the redirect: ~/.l9/cloud-session.env
# exports L9_GOVERNANCE_DIR=$HOME/.cursor-governance, i.e. the value this line
# already computes. Tests that need the launcher pointed elsewhere move HOME,
# which is how the sibling launcher suites have always done it.
GOV_DIR="$HOME/.cursor-governance"

# Surface guard (INV-2): one canonical detector decides which host owns each
# hook. All observers are Claude adapter observers, so they skip on every
# non-Claude surface, including unknown. Gates keep the existing named-hook
# policy: only local_execution_gate_wrap.py and memory_gate.py are Claude-only;
# merge_gate_wrap.py and session_debt_wrap.py stay active. Unknown gates still
# run, fail-toward-closed. L9_SURFACE_GUARD=0 restores pre-guard behavior.
#
# Hoist the walk-up once so observers and gates use the same detector rather
# than reimplementing host identity independently.
if [ "${L9_SURFACE_GUARD:-1}" != "0" ]; then
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
  if [ -z "$_L9_SD_LIB" ] && [ -f "$GOV_DIR/ops/scripts/lib/surface_detect.sh" ]; then
    _L9_SD_LIB="$GOV_DIR/ops/scripts/lib/surface_detect.sh"
  fi

  if [ -n "$_L9_SD_LIB" ] && [ -f "$_L9_SD_LIB" ]; then
    # shellcheck source=../../../../ops/scripts/lib/surface_detect.sh
    . "$_L9_SD_LIB"
    _L9_SURFACE="$(l9_detect_surface)"

    if [ "$HOOK_CLASS" = "observer" ]; then
      if ! l9_is_claude_gate_surface; then
        printf 'l9-hook: observer %s skipped (surface=%s; Claude observer)\n' \
          "$HOOK_NAME" "$_L9_SURFACE" >&2
        unset _L9_SURFACE _L9_SD_LIB _L9_WALK _L9_HOOK_DIR
        exit 0
      fi
    else
      # Named gate table is deliberately unchanged. Only these two gates are
      # Claude-only. merge_gate_wrap.py and session_debt_wrap.py remain active.
      case "$_L9_SURFACE" in
        claude-code|claude-code-remote|unknown) : ;;
        *)
          case "$HOOK_NAME" in
            local_execution_gate_wrap.py|memory_gate.py)
              printf 'l9-hook: gate %s skipped (surface=%s; Claude-only gate)\n' \
                "$HOOK_NAME" "$_L9_SURFACE" >&2
              unset _L9_SURFACE _L9_SD_LIB _L9_WALK _L9_HOOK_DIR
              exit 0
              ;;
          esac
          ;;
      esac
    fi
    unset _L9_SURFACE
  elif [ "$HOOK_CLASS" = "observer" ]; then
    # No detector means identity is unknown. Unknown observers must not inject
    # Claude identity into another host; unknown gates still continue below.
    printf 'l9-hook: observer %s skipped (surface=unknown; detector unavailable)\n' \
      "$HOOK_NAME" >&2
    unset _L9_SD_LIB _L9_WALK _L9_HOOK_DIR
    exit 0
  fi
  unset _L9_SD_LIB _L9_WALK _L9_HOOK_DIR
fi

SKIP_LOG="${L9_HOOK_SKIP_LOG:-$HOME/.l9/claude/hook-skips.log}"

# Every skip is timestamped in UTC. An undated skip log cannot answer the only
# question worth asking of it: was this hook skipped during the run I am
# investigating, or six weeks ago?
# The skip log answers one question: was this hook skipped during the run I am
# investigating? It used to `return 0` when its directory could not be created,
# so the record vanished in exactly the broken-environment case it exists for —
# a wrong or unwritable HOME is what makes hooks skip in the first place. It now
# falls back to TMPDIR and says on stderr where the line actually went.
record_skip() {
  local reason="$1" ts target
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown-time')"
  target="$SKIP_LOG"
  if ! mkdir -p "$(dirname "$target")" 2>/dev/null; then
    target="${TMPDIR:-/tmp}/l9-hook-skips.log"
    printf 'l9-hook: skip log unwritable at %s — recording to %s\n' "$SKIP_LOG" "$target" >&2
  fi
  if ! printf '%s observer %s %s\n' "$ts" "$HOOK_NAME" "$reason" >> "$target" 2>/dev/null; then
    printf 'l9-hook: could not record skip of %s (%s) anywhere\n' "$HOOK_NAME" "$reason" >&2
  fi
}

# One exit path for "this hook cannot run", so a gate can never accidentally
# take the observer branch.
cannot_run() {
  local reason="$1"
  if [ "$HOOK_CLASS" = "gate" ]; then
    printf 'l9-gate: %s cannot evaluate (%s) — BLOCKING (INV-1: gates fail closed)\n' \
      "$HOOK_NAME" "$reason" >&2
    printf 'l9-gate:   repair with: bash %s/environment/agents/adapters/claude-code/install.sh\n' \
      "$GOV_DIR" >&2
    exit 2
  fi
  printf 'l9-hook: observer %s did NOT run (%s); logged to %s\n' \
    "$HOOK_NAME" "$reason" "$SKIP_LOG" >&2
  record_skip "$reason"
  exit 0
}

[ -f "$GOV_DIR/CANONICAL_LAW.md" ] || cannot_run "no governance SSOT at $GOV_DIR"

# ---------------------------------------------------------------------------
# Cloud SessionStart governance refresh (PR #548 review; F-548-001/002/003).
#
# On CLAUDE_CODE_REMOTE=true the governance clone is an ephemeral environment
# artifact. SessionStart siblings run concurrently with no ordering, so the
# refresh happens HERE, before HOOK_PATH resolves, and tip-only hooks exist
# for every sibling of this session. Three properties are load-bearing:
#
#   SCOPE   Only SessionStart hooks refresh. This launcher is the choke point
#           for UserPromptSubmit, PreToolUse, PostToolUse and Stop as well
#           (SURFACE_BOOTSTRAP_CONTRACT), and a network fetch plus forced
#           checkout before every 5 s gate spends the gate's budget and can
#           change the governance revision mid-session. Non-SessionStart
#           invocations perform no fetch, no checkout and no receipt write.
#
#   TRUST   The fetch goes to the clone's configured `origin`, and only when
#           that origin IS the canonical Quantum-L9/Cursor-Governance remote.
#           L9_GOVERNANCE_REMOTE is never applied: the first version rewrote
#           origin to whatever the account field said and then exec'd hooks
#           out of the refilled tree, so a poisoned field turned the trusted
#           entrypoint into execution of foreign policy inside the canonical
#           directory (INV-1c holds for the bytes, not only the path). Test
#           fixtures use one separately admitted seam, L9_GOV_REFRESH_LOCAL_ORIGIN:
#           an existing local directory that must ALSO equal the configured
#           origin. It admits a fixture's own bare repo; it cannot redirect.
#
#   LEASE   The lock is a directory lease with a recorded owner. A launcher
#           killed mid-fetch (SessionStart timeouts are 15-90 s) leaves its
#           lock behind; the next launcher reclaims a lease whose owner PID is
#           dead or whose age exceeds L9_GOV_REFRESH_LEASE (60 s), so one
#           interrupted refresh can never strand the environment stale. A live
#           lease is waited on briefly and its receipt adopted when it was
#           written since this launcher started; otherwise the outcome is
#           reported as lock-busy and the SessionStart hook's own fallback runs.
#
# Every attempt is bound to the hook it launches through the environment:
#   L9_GOV_REFRESH_ATTEMPT_ID   id of the receipt THIS launcher run wrote or
#                               adopted from a sibling of this session
#   L9_GOV_REFRESH_OUTCOME      fetched | fetch-failed | reset-failed |
#                               reset-skipped-dirty | lock-busy | origin-untrusted
# The receipt carries the same attempt_id and a refreshed_epoch, so the
# SessionStart hook suppresses its fallback only on a receipt proven to belong
# to the current attempt — never on an older receipt that merely says fresh.
#
# Fail-open throughout: no refresh outcome blocks a hook. Dirty tracked trees
# are never force-reset (same guard as session_start_claude_governance.sh).
# ---------------------------------------------------------------------------
L9_GOV_CANONICAL_REMOTE="https://github.com/Quantum-L9/Cursor-Governance"

# The SessionStart registrations in settings.template.json. A hook absent from
# this table is a gate or a later-event observer and must never refresh.
l9_is_session_start_hook() {
  case "$1" in
    session_start_claude_governance.sh|bootstrap_capability_preflight.sh|memory_prefetch.py|session_deps_cloud.sh)
      return 0 ;;
    *) return 1 ;;
  esac
}

# 0 when $1 is a remote this launcher may fetch policy from.
l9_gov_origin_trusted() {
  local url="$1" seam="${L9_GOV_REFRESH_LOCAL_ORIGIN:-}"
  case "$url" in
    "$L9_GOV_CANONICAL_REMOTE"|"$L9_GOV_CANONICAL_REMOTE.git") return 0 ;;
    git@github.com:Quantum-L9/Cursor-Governance|git@github.com:Quantum-L9/Cursor-Governance.git) return 0 ;;
    ssh://git@github.com/Quantum-L9/Cursor-Governance|ssh://git@github.com/Quantum-L9/Cursor-Governance.git) return 0 ;;
  esac
  # Test seam: an existing local directory, admitted only when it is ALSO the
  # configured origin. It can admit a fixture; it cannot point anywhere.
  if [ -n "$seam" ] && [ -d "$seam" ] && [ "$url" = "$seam" ]; then
    return 0
  fi
  return 1
}

l9_gov_json_token() { printf '%s' "$1" | tr -d '\n\r\t"\\' | head -c 96; }

# Receipt writer. Same schema the SessionStart hook writes (every reader
# recomputes freshness from refreshed_at + ttl); attempt_id / refreshed_epoch /
# owner_hook are the current-attempt binding described above.
l9_gov_write_receipt() {
  local receipt="$1" outcome="$2" local_sha="$3" origin_sha="$4" state="$5" attempt="$6"
  printf '{\n  "schema": "l9.governance-refresh.v1",\n  "outcome": "%s",\n  "local_sha": "%s",\n  "origin_sha": "%s",\n  "refreshed_at": "%s",\n  "refreshed_epoch": %s,\n  "attempt_id": "%s",\n  "owner_hook": "%s",\n  "ttl_seconds": %s,\n  "commits_behind": -1,\n  "state": "%s"\n}\n' \
    "$(l9_gov_json_token "$outcome")" \
    "$(l9_gov_json_token "$local_sha")" \
    "$(l9_gov_json_token "$origin_sha")" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)" \
    "$(date +%s 2>/dev/null || echo 0)" \
    "$(l9_gov_json_token "$attempt")" \
    "$(l9_gov_json_token "$HOOK_NAME")" \
    "${L9_GOV_REFRESH_TTL:-3600}" \
    "$(l9_gov_json_token "$state")" > "$receipt.tmp.$$" 2>/dev/null \
    && mv -f "$receipt.tmp.$$" "$receipt" 2>/dev/null
}

# Directory lease. Returns 0 holding the lock (fresh or reclaimed). A holder
# whose PID is dead, or whose lease is older than $2 seconds, is reclaimed.
l9_gov_lock_acquire() {
  local lockdir="$1" lease="$2" owner_pid="" owner_epoch="" now age dead=0
  if mkdir "$lockdir" 2>/dev/null; then
    printf '%s %s %s\n' "$$" "$(date +%s)" "$HOOK_NAME" > "$lockdir/owner" 2>/dev/null
    return 0
  fi
  now=$(date +%s 2>/dev/null || echo 0)
  if [ -f "$lockdir/owner" ]; then
    read -r owner_pid owner_epoch _ < "$lockdir/owner" 2>/dev/null || :
  fi
  case "$owner_epoch" in ''|*[!0-9]*)
    # No parseable lease: the holder died between mkdir and the owner write,
    # or a pre-lease lock directory was left behind. Age it from the directory.
    owner_epoch=$(stat -c %Y "$lockdir" 2>/dev/null || stat -f %m "$lockdir" 2>/dev/null || echo 0)
    case "$owner_epoch" in ''|*[!0-9]*) owner_epoch=0 ;; esac
    ;;
  esac
  age=$((now - owner_epoch))
  case "$owner_pid" in
    ''|*[!0-9]*) dead=1 ;;
    *) kill -0 "$owner_pid" 2>/dev/null || dead=1 ;;
  esac
  if [ "$dead" = 1 ] || [ "$age" -gt "$lease" ]; then
    rm -rf "$lockdir" 2>/dev/null
    if mkdir "$lockdir" 2>/dev/null; then
      printf '%s %s %s\n' "$$" "$(date +%s)" "$HOOK_NAME" > "$lockdir/owner" 2>/dev/null
      printf 'l9-hook: governance refresh reclaimed an abandoned lock (owner pid=%s age=%ss)\n' \
        "${owner_pid:-none}" "$age" >&2
      return 0
    fi
  fi
  return 1
}

# Release only a lease this process still owns; a reclaimed lock is not ours.
l9_gov_lock_release() {
  local lockdir="$1" owner_pid=""
  [ -f "$lockdir/owner" ] && read -r owner_pid _ < "$lockdir/owner" 2>/dev/null
  [ "$owner_pid" = "$$" ] && rm -rf "$lockdir" 2>/dev/null
  return 0
}

# Adopt a sibling's receipt when it was written at or after this launcher
# started (small tolerance: siblings spawn within milliseconds). Exports the
# binding and returns 0; returns 1 when no such receipt exists.
l9_gov_adopt_receipt() {
  local receipt="$1" since="$2" epoch="" attempt="" outcome=""
  [ -f "$receipt" ] || return 1
  epoch=$(sed -n 's/.*"refreshed_epoch": \([0-9][0-9]*\).*/\1/p' "$receipt" 2>/dev/null | head -n 1)
  attempt=$(sed -n 's/.*"attempt_id": "\([^"]*\)".*/\1/p' "$receipt" 2>/dev/null | head -n 1)
  outcome=$(sed -n 's/.*"outcome": "\([^"]*\)".*/\1/p' "$receipt" 2>/dev/null | head -n 1)
  case "$epoch" in ''|*[!0-9]*) return 1 ;; esac
  [ -n "$attempt" ] && [ -n "$outcome" ] || return 1
  [ "$epoch" -ge "$since" ] || return 1
  export L9_GOV_REFRESH_ATTEMPT_ID="$attempt"
  export L9_GOV_REFRESH_OUTCOME="$outcome"
  return 0
}

l9_cloud_refresh_gov() {
  # Never inherited: a value in the account environment must not pre-seed the
  # binding the SessionStart hook keys its fallback on.
  unset L9_GOV_REFRESH_ATTEMPT_ID L9_GOV_REFRESH_OUTCOME L9_GOV_REFRESH_STARTED
  [ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || return 0
  l9_is_session_start_hook "$HOOK_NAME" || return 0
  [ -d "$GOV_DIR/.git" ] || return 0

  # Mark that we entered the refresh path. If the hook sees this marker but no
  # attempt ID and no outcome, the launcher crashed mid-refresh. This catches
  # kill -9, OOM, or any failure between here and the export at the end.
  export L9_GOV_REFRESH_STARTED=1
  local lockdir="${L9_GOV_REFRESH_LOCKDIR:-$HOME/.l9/claude/gov-refresh.lock.d}"
  local receipt="${L9_GOV_REFRESH_RECEIPT:-$HOME/.l9/claude/gov-refresh.json}"
  local branch="main"
  local lease="${L9_GOV_REFRESH_LEASE:-60}"
  local wait_ticks="${L9_GOV_REFRESH_WAIT_TICKS:-80}"
  local fetch_timeout="${L9_GOV_REFRESH_FETCH_TIMEOUT:-20}"
  local start_epoch waited=0 acquired=0 attempt local_sha remote_sha gov_dirty origin_url
  local -a fetch_cmd
  start_epoch=$(date +%s 2>/dev/null || echo 0)
  case "$lease" in ''|*[!0-9]*) lease=60 ;; esac
  case "$wait_ticks" in ''|*[!0-9]*) wait_ticks=80 ;; esac
  case "$fetch_timeout" in ''|*[!0-9]*) fetch_timeout=20 ;; esac
  # A ref name only: no option-shaped or traversal-shaped value reaches git.
  case "$branch" in ''|-*|*..*|*[[:space:]]*|*/) branch=main ;; esac

  if [ -n "${L9_GOVERNANCE_REMOTE:-}" ] && ! l9_gov_origin_trusted "$L9_GOVERNANCE_REMOTE"; then
    printf 'l9-hook: L9_GOVERNANCE_REMOTE is not the canonical governance remote — ignored (refresh uses origin)\n' >&2
  fi
  origin_url=$(git -C "$GOV_DIR" remote get-url origin 2>/dev/null || echo '')
  if ! l9_gov_origin_trusted "$origin_url"; then
    printf 'l9-hook: governance refresh refused — origin is not the canonical remote (%s)\n' \
      "${origin_url:-none}" >&2
    export L9_GOV_REFRESH_OUTCOME="origin-untrusted"
    return 0
  fi
  mkdir -p "$(dirname "$lockdir")" "$(dirname "$receipt")" 2>/dev/null || return 0

  while :; do
    # A sibling of this session already refreshed: same revision, no second fetch.
    l9_gov_adopt_receipt "$receipt" "$((start_epoch - ${L9_GOV_REFRESH_ADOPT_WINDOW:-5}))" && return 0
    if l9_gov_lock_acquire "$lockdir" "$lease"; then
      acquired=1
      break
    fi
    [ "$waited" -lt "$wait_ticks" ] || break
    sleep 0.1 2>/dev/null || sleep 1
    waited=$((waited + 1))
  done
  if [ "$acquired" != 1 ]; then
    l9_gov_adopt_receipt "$receipt" "$((start_epoch - ${L9_GOV_REFRESH_ADOPT_WINDOW:-5}))" && return 0
    printf 'l9-hook: governance refresh lock busy after %s ticks — proceeding with the existing clone\n' \
      "$waited" >&2
    export L9_GOV_REFRESH_OUTCOME="lock-busy"
    return 0
  fi

  attempt="$$-$start_epoch-$RANDOM"
  gov_dirty=$(git -C "$GOV_DIR" status --porcelain --untracked-files=no 2>/dev/null | head -c 1)
  local_sha=$(git -C "$GOV_DIR" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
  if [ -n "$gov_dirty" ]; then
    printf 'l9-hook: governance refresh skipped — dirty tracked clone\n' >&2
    l9_gov_write_receipt "$receipt" reset-skipped-dirty "$local_sha" unknown stale "$attempt"
    export L9_GOV_REFRESH_OUTCOME="reset-skipped-dirty"
  else
    fetch_cmd=(git -C "$GOV_DIR" fetch --depth 1 origin "$branch")
    if command -v timeout >/dev/null 2>&1; then
      fetch_cmd=(timeout "$fetch_timeout" "${fetch_cmd[@]}")
    fi
    if "${fetch_cmd[@]}" >/dev/null 2>&1; then
      remote_sha=$(git -C "$GOV_DIR" rev-parse --verify --quiet FETCH_HEAD 2>/dev/null || echo 'unknown')
      if git -C "$GOV_DIR" checkout -f -B "$branch" "origin/$branch" >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV_DIR" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
        l9_gov_write_receipt "$receipt" fetched "$local_sha" "$remote_sha" fresh "$attempt"
        export L9_GOV_REFRESH_OUTCOME="fetched"
      else
        l9_gov_write_receipt "$receipt" reset-failed "$local_sha" "$remote_sha" stale "$attempt"
        export L9_GOV_REFRESH_OUTCOME="reset-failed"
      fi
    else
      l9_gov_write_receipt "$receipt" fetch-failed "$local_sha" unknown unknown "$attempt"
      export L9_GOV_REFRESH_OUTCOME="fetch-failed"
    fi
  fi
  export L9_GOV_REFRESH_ATTEMPT_ID="$attempt"
  l9_gov_lock_release "$lockdir"
}

l9_cloud_refresh_gov

HOOK_PATH="$GOV_DIR/environment/agents/adapters/claude-code/hooks/$HOOK_NAME"
[ -f "$HOOK_PATH" ] || cannot_run "hook file absent at $HOOK_PATH"

# Shell hooks carry no locked-dependency requirement, so they are dispatched
# before the interpreter check — demanding a .venv from a bash hook would fail
# it closed for a reason that does not apply to it.
case "$HOOK_NAME" in
  *.sh) exec bash "$HOOK_PATH" ;;
esac

# The locked interpreter, never the sandbox's system python3. The gate modules
# import pydantic/yaml/jsonschema from uv.lock; running them on whatever python
# happens to be on PATH is how a gate starts throwing instead of deciding.
PY="$GOV_DIR/.venv/bin/python3"
[ -x "$PY" ] || PY="$GOV_DIR/.venv/bin/python"
[ -x "$PY" ] || cannot_run "locked interpreter missing under $GOV_DIR/.venv"

exec "$PY" "$HOOK_PATH"
