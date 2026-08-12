#!/usr/bin/env bash
# Activate GitHub-tip governance at $HOME/.cursor-governance for sessionStart.
#
# Contracts (CANONICAL_LAW / plan fresh_governance_activate):
#   C1 tip authority — HEAD == remote tip after success
#   C2 tip vs wiring split — Dropbox rewire does not require clone
#   C3 ff-first when clean+behind; else shallow clone + atomic swap
#   C4 pre-swap backup_to_github when dirty/ahead
#   C5 staging verify before mv; fail leaves live untouched
#   C6 bak retention (newest 2; keep extra if unpushed)
#   C7 always exit 0; last stdout line STATUS action=... sha=... detail=...
#   C10 no SSOT self-alias .cursor-commands
#   C11 sessionStart uses this script only (not governance_sync pull-half)
set -uo pipefail

CLONE="${CURSOR_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"
REMOTE="${GOVERNANCE_GITHUB_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
REPO="${CURSOR_PROJECT_DIR:-${REPO:-}}"
LOCK="$HOME/.cursor/governance-sync.lock"
RECEIPT="$HOME/.cursor/governance-activate.last"
STAGING="${CLONE}.activating"
DEADLINE_SECS="${GOVERNANCE_ACTIVATE_DEADLINE_SECS:-50}"
LOCK_WAIT_SECS="${GOVERNANCE_ACTIVATE_LOCK_WAIT_SECS:-10}"
START_TS="$(date +%s)"

ACTION="degraded"
DETAIL="init"
REMOTE_SHA=""
LOCAL_SHA=""
BAK_UNPUSHED=0

emit_status() {
  local sha="${LOCAL_SHA:-unknown}"
  local detail="$DETAIL"
  [ "$BAK_UNPUSHED" = "1" ] && detail="${detail};bak_unpushed"
  # Machine-parseable last line for sessionStart bootstrap.
  echo "STATUS action=${ACTION} sha=${sha} remote_sha=${REMOTE_SHA:-unknown} detail=${detail}"
}

write_receipt() {
  mkdir -p "$(dirname "$RECEIPT")" 2>/dev/null || true
  cat >"$RECEIPT" 2>/dev/null <<EOF || true
{
  "ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "action": "${ACTION}",
  "remote_sha": "${REMOTE_SHA}",
  "local_sha": "${LOCAL_SHA}",
  "repo": "${REPO}",
  "detail": "${DETAIL}",
  "bak_unpushed": ${BAK_UNPUSHED}
}
EOF
}

deadline_exceeded() {
  local now
  now="$(date +%s)"
  [ $((now - START_TS)) -ge "$DEADLINE_SECS" ]
}

realpath_py() {
  python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1" 2>/dev/null || echo ""
}

layout_ok() {
  local root="$1"
  [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]
}

expected_remote_ok() {
  # Accept https/ssh forms of Quantum-L9/Cursor-Governance
  local url="$1"
  echo "$url" | grep -qiE 'github\.com[:/]+Quantum-L9/Cursor-Governance(\.git)?/?$' 
}

acquire_lock() {
  mkdir -p "$(dirname "$LOCK")" 2>/dev/null || true
  local lockdir="${LOCK}.d"
  local waited=0
  while true; do
    if mkdir "$lockdir" 2>/dev/null; then
      date +%s >"$lockdir/ts" 2>/dev/null || true
      trap 'rm -rf "'"$lockdir"'" 2>/dev/null || true' EXIT
      return 0
    fi
    local _now _ts
    _now=$(date +%s 2>/dev/null || echo 0)
    _ts=$(cat "$lockdir/ts" 2>/dev/null || echo 0)
    if [ "$_now" -gt 0 ] && [ $((_now - _ts)) -gt 300 ]; then
      rm -rf "$lockdir" 2>/dev/null || true
      continue
    fi
    if [ "$waited" -ge "$LOCK_WAIT_SECS" ]; then
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
}

ls_remote_sha() {
  git ls-remote "$REMOTE" "refs/heads/${BRANCH}" 2>/dev/null | awk '{print $1; exit}'
}

heal_wiring() {
  local ssot_real
  ssot_real="$(realpath_py "$CLONE")"
  mkdir -p "$HOME/.cursor/plugins/local" 2>/dev/null || true
  ln -sfn "$CLONE" "$HOME/.cursor/plugins/local/l9-governance" 2>/dev/null || true
  rm -f "$CLONE/.cursor-commands" 2>/dev/null || true
  if [ -n "$REPO" ] && [ -d "$REPO" ]; then
    local repo_real
    repo_real="$(realpath_py "$REPO")"
    if [ -n "$repo_real" ] && [ "$repo_real" != "$ssot_real" ]; then
      mkdir -p "$REPO" 2>/dev/null || true
      ln -sfn "$CLONE" "$REPO/.cursor-commands" 2>/dev/null || true
    fi
  fi
  # Self-heal installed bootstrap + activator sidecar from live SSOT when present.
  if [ -f "$CLONE/ops/hooks/session_start_bootstrap.sh" ]; then
    mkdir -p "$HOME/.cursor/hooks" 2>/dev/null || true
    cp -f "$CLONE/ops/hooks/session_start_bootstrap.sh" \
      "$HOME/.cursor/hooks/session-start-bootstrap.sh" 2>/dev/null || true
    chmod +x "$HOME/.cursor/hooks/session-start-bootstrap.sh" 2>/dev/null || true
  fi
  if [ -f "$CLONE/ops/scripts/governance_activate_fresh.sh" ]; then
    mkdir -p "$HOME/.cursor/hooks" 2>/dev/null || true
    cp -f "$CLONE/ops/scripts/governance_activate_fresh.sh" \
      "$HOME/.cursor/hooks/governance-activate-fresh.sh" 2>/dev/null || true
    chmod +x "$HOME/.cursor/hooks/governance-activate-fresh.sh" 2>/dev/null || true
  fi
}

wiring_stale() {
  [ -z "$REPO" ] && return 1
  [ ! -e "$REPO/.cursor-commands" ] && return 0
  local want have
  want="$(realpath_py "$CLONE")"
  have="$(realpath_py "$REPO/.cursor-commands")"
  [ -z "$have" ] || [ "$have" != "$want" ]
}

ssot_valid() {
  layout_ok "$CLONE" && [ -d "$CLONE/.git" ]
}

local_head() {
  git -C "$CLONE" rev-parse HEAD 2>/dev/null || echo ""
}

tree_clean() {
  git -C "$CLONE" diff --quiet 2>/dev/null && git -C "$CLONE" diff --cached --quiet 2>/dev/null
}

only_behind() {
  # HEAD is ancestor of REMOTE_SHA and not equal
  local head="$1"
  [ -n "$head" ] && [ -n "$REMOTE_SHA" ] && [ "$head" != "$REMOTE_SHA" ] || return 1
  git -C "$CLONE" merge-base --is-ancestor "$head" "$REMOTE_SHA" 2>/dev/null
}

remote_url_ok() {
  local url
  url="$(git -C "$CLONE" remote get-url origin 2>/dev/null || echo "")"
  expected_remote_ok "$url"
}

pre_swap_backup() {
  local push="$CLONE/ops/scripts/backup_to_github.sh"
  if [ -x "$push" ]; then
    if ! bash "$push" "chore(governance): pre-activate backup $(date +%Y-%m-%d\ %H:%M)" >/dev/null 2>&1; then
      BAK_UNPUSHED=1
      echo "WARNING: governance_activate_fresh: pre-swap backup failed — preserving bak" >&2
    fi
  else
    # Detect ahead/dirty without backup script
    if ! tree_clean; then
      BAK_UNPUSHED=1
    else
      local ahead
      ahead="$(git -C "$CLONE" rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo 0)"
      [ "${ahead:-0}" -gt 0 ] && BAK_UNPUSHED=1
    fi
  fi
}

prune_baks() {
  # Keep newest 2 bak dirs; keep a 3rd if it still has unpushed commits.
  local -a baks=()
  local d
  while IFS= read -r d; do
    [ -n "$d" ] && baks+=("$d")
  done < <(ls -1dt "$HOME"/.cursor-governance.bak.* 2>/dev/null || true)
  local i=0
  for d in "${baks[@]:-}"; do
    i=$((i + 1))
    if [ "$i" -le 2 ]; then
      continue
    fi
    local keep=0
    if [ -d "$d/.git" ]; then
      local ahead
      ahead="$(git -C "$d" rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo 0)"
      if [ "${ahead:-0}" -gt 0 ]; then
        keep=1
        DETAIL="${DETAIL};bak_kept_unpushed"
      elif ! git -C "$d" diff --quiet 2>/dev/null || ! git -C "$d" diff --cached --quiet 2>/dev/null; then
        keep=1
        DETAIL="${DETAIL};bak_kept_dirty"
      fi
    fi
    if [ "$keep" = "0" ] && [ "$i" -gt 2 ]; then
      rm -rf "$d" 2>/dev/null || true
    fi
  done
}

do_ff() {
  git -C "$CLONE" fetch --quiet origin "$BRANCH" 2>/dev/null || return 1
  git -C "$CLONE" merge --ff-only --quiet "origin/${BRANCH}" 2>/dev/null || return 1
  LOCAL_SHA="$(local_head)"
  [ "$LOCAL_SHA" = "$REMOTE_SHA" ]
}

do_swap() {
  if deadline_exceeded; then
    DETAIL="deadline_before_clone"
    return 1
  fi
  rm -rf "$STAGING" 2>/dev/null || true
  if ! git clone --depth 1 --branch "$BRANCH" --quiet "$REMOTE" "$STAGING" 2>/dev/null; then
    DETAIL="clone_failed"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  if deadline_exceeded; then
    DETAIL="deadline_during_clone"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  local staged
  staged="$(git -C "$STAGING" rev-parse HEAD 2>/dev/null || echo "")"
  if [ -z "$staged" ] || ! layout_ok "$STAGING"; then
    DETAIL="staging_invalid"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  # Tip may have moved; accept staged if it matches ls-remote now, else one refresh.
  if [ "$staged" != "$REMOTE_SHA" ]; then
    local again
    again="$(ls_remote_sha)"
    if [ -n "$again" ] && [ "$staged" = "$again" ]; then
      REMOTE_SHA="$again"
    else
      # Still activate staged tip if it's on the expected branch (race); record mismatch.
      DETAIL="tip_race_activated_${staged:0:7}"
      REMOTE_SHA="${again:-$REMOTE_SHA}"
    fi
  fi
  if ssot_valid; then
    pre_swap_backup
    local bak="${CLONE}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
    if ! mv "$CLONE" "$bak" 2>/dev/null; then
      DETAIL="mv_live_to_bak_failed"
      rm -rf "$STAGING" 2>/dev/null || true
      return 1
    fi
  fi
  if ! mv "$STAGING" "$CLONE" 2>/dev/null; then
    DETAIL="mv_staging_to_live_failed"
    # Best-effort: leave staging for manual recovery; do not delete last bak.
    return 1
  fi
  LOCAL_SHA="$(local_head)"
  prune_baks
  return 0
}

bootstrap_missing() {
  if deadline_exceeded; then
    DETAIL="deadline_bootstrap"
    return 1
  fi
  rm -rf "$STAGING" 2>/dev/null || true
  if ! git clone --depth 1 --branch "$BRANCH" --quiet "$REMOTE" "$STAGING" 2>/dev/null; then
    DETAIL="bootstrap_clone_failed"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  if ! layout_ok "$STAGING"; then
    DETAIL="bootstrap_layout_invalid"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  LOCAL_SHA="$(git -C "$STAGING" rev-parse HEAD 2>/dev/null || echo "")"
  if [ -e "$CLONE" ]; then
    DETAIL="bootstrap_target_exists"
    rm -rf "$STAGING" 2>/dev/null || true
    return 1
  fi
  mv "$STAGING" "$CLONE" 2>/dev/null || {
    DETAIL="bootstrap_mv_failed"
    return 1
  }
  return 0
}

# ── main ─────────────────────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || {
  ACTION="degraded"
  DETAIL="git_missing"
  write_receipt
  emit_status
  exit 0
}

if ! expected_remote_ok "$REMOTE"; then
  ACTION="degraded"
  DETAIL="unexpected_remote_url"
  write_receipt
  emit_status
  exit 0
fi

if ! acquire_lock; then
  # Another activator holds the lock. If receipt already at tip, treat as fresh.
  if [ -f "$RECEIPT" ] && ssot_valid; then
    LOCAL_SHA="$(local_head)"
    REMOTE_SHA="$(ls_remote_sha)"
    if [ -n "$REMOTE_SHA" ] && [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
      ACTION="fresh"
      DETAIL="lock_busy_but_tip_ok"
      heal_wiring
      write_receipt
      emit_status
      exit 0
    fi
  fi
  ACTION="degraded"
  DETAIL="lock_busy"
  LOCAL_SHA="$(local_head)"
  write_receipt
  emit_status
  exit 0
fi

REMOTE_SHA="$(ls_remote_sha)"
if [ -z "$REMOTE_SHA" ]; then
  ACTION="degraded"
  DETAIL="ls_remote_failed"
  if ssot_valid; then
    LOCAL_SHA="$(local_head)"
    heal_wiring
  fi
  write_receipt
  emit_status
  exit 0
fi

if ! ssot_valid; then
  if bootstrap_missing; then
    ACTION="swapped"
    DETAIL="bootstrap_clone"
    LOCAL_SHA="$(local_head)"
    heal_wiring
    write_receipt
    emit_status
    exit 0
  fi
  ACTION="degraded"
  write_receipt
  emit_status
  exit 0
fi

LOCAL_SHA="$(local_head)"

# Tip already good → wiring heal only if needed.
# C1 tip authority is SHA equality against authorized REMOTE (already validated).
# Origin URL string may be a fixture insteadOf/file path — heal it when tip matches.
if [ -n "$LOCAL_SHA" ] && [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  if ! remote_url_ok; then
    git -C "$CLONE" remote set-url origin "$REMOTE" 2>/dev/null || true
  fi
  if wiring_stale; then
    heal_wiring
    ACTION="wire_only"
    DETAIL="consumer_or_plugin_rewired"
  else
    heal_wiring
    ACTION="fresh"
    DETAIL="at_tip"
  fi
  write_receipt
  emit_status
  exit 0
fi

# Clean + only behind + correct remote → ff
if remote_url_ok && tree_clean && only_behind "$LOCAL_SHA"; then
  if do_ff; then
    heal_wiring
    ACTION="ff"
    DETAIL="ff_only"
    write_receipt
    emit_status
    exit 0
  fi
  DETAIL="ff_failed"
fi

# Otherwise swap
if do_swap; then
  heal_wiring
  ACTION="swapped"
  DETAIL="${DETAIL:-shallow_clone_swap}"
  # Normalize detail when tip matched
  [ "$LOCAL_SHA" = "$REMOTE_SHA" ] && DETAIL="shallow_clone_swap"
  write_receipt
  emit_status
  exit 0
fi

ACTION="degraded"
LOCAL_SHA="$(local_head)"
heal_wiring
write_receipt
emit_status
exit 0
