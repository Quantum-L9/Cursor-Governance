#!/bin/bash
# l9-mac-storage-triage / scripts/mode-run.sh
# purpose: orchestrate diagnose | repair | autonomy modes
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos

MODE="${1:-diagnose}"
BIN="$ROOT_DIR/bin/mac-storage-triage"
ENV_FILE="${MAC_STORAGE_TRIAGE_ENV:-$ROOT_DIR/.env}"

select_safe_actions() {
  local findings="$ROOT_DIR/handoffs/current/findings.json"
  if [ -f "$findings" ]; then
    python3 - "$findings" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
actions = doc.get("repair", {}).get("phase_a_actions") or []
print(",".join(a for a in actions if a))
PY
    return 0
  fi
  local inv
  inv="$(cat "$(state_dir)/noise-inventory-path")"
  [ -f "$inv" ] || die "Noise inventory missing. Run diagnose first."
  # shellcheck disable=SC1090
  . "$inv"
  CACHE_TOTAL_KIB="${CACHE_TOTAL_KIB:-0}"
  DOCKER_STOPPED_CONTAINERS="${DOCKER_STOPPED_CONTAINERS:-0}"
  DOCKER_DANGLING_IMAGES="${DOCKER_DANGLING_IMAGES:-0}"
  TRASH_KIB="${TRASH_KIB:-0}"
  [ -n "$CACHE_TOTAL_KIB" ] || CACHE_TOTAL_KIB=0
  [ -n "$DOCKER_STOPPED_CONTAINERS" ] || DOCKER_STOPPED_CONTAINERS=0
  [ -n "$DOCKER_DANGLING_IMAGES" ] || DOCKER_DANGLING_IMAGES=0
  [ -n "$TRASH_KIB" ] || TRASH_KIB=0
  local actions=()
  if [ "${CACHE_TOTAL_KIB:-0}" -gt 0 ]; then
    actions+=(purge_stale_caches)
  fi
  if [ "${DOCKER_AVAILABLE:-false}" = true ] && {
    [ "${DOCKER_STOPPED_CONTAINERS:-0}" -gt 0 ] || [ "${DOCKER_DANGLING_IMAGES:-0}" -gt 0 ]
  }; then
    actions+=(docker_prune_unused)
  fi
  if [ "${TRASH_KIB:-0}" -gt 0 ]; then
    actions+=(empty_trash)
  fi
  if [ "${#actions[@]}" -eq 0 ]; then
    printf '\n'
    return 0
  fi
  local IFS=','
  printf '%s' "${actions[*]}"
}

upsert_env_kv() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  if grep -q "^${key}=" "$ENV_FILE"; then
    awk -v k="$key" -v v="$value" 'BEGIN{q="'\''"} $0 ~ "^"k"=" {print k"=" q v q; next} {print}' "$ENV_FILE" > "$tmp"
    mv "$tmp" "$ENV_FILE"
  else
    printf "%s='%s'\n" "$key" "$value" >> "$ENV_FILE"
    rm -f "$tmp"
  fi
}

apply_safe_env_flags() {
  local actions="$1"
  local apply_conf="$2"
  local autonomy_conf="$3"
  local mode="$4"
  upsert_env_kv TRIAGE_MODE "$mode"
  upsert_env_kv APPROVED_ACTIONS "$actions"
  upsert_env_kv APPLY_CONFIRMATION "$apply_conf"
  upsert_env_kv AUTONOMY_CONFIRMATION "$autonomy_conf"
  case ",$actions," in
    *,purge_stale_caches,*) upsert_env_kv PURGE_STALE_CACHES_APPROVED true ;;
    *) upsert_env_kv PURGE_STALE_CACHES_APPROVED false ;;
  esac
  case ",$actions," in
    *,docker_prune_unused,*) upsert_env_kv DOCKER_PRUNE_UNUSED_APPROVED true ;;
    *) upsert_env_kv DOCKER_PRUNE_UNUSED_APPROVED false ;;
  esac
  case ",$actions," in
    *,empty_trash,*) upsert_env_kv EMPTY_TRASH_APPROVED true ;;
    *) upsert_env_kv EMPTY_TRASH_APPROVED false ;;
  esac
  upsert_env_kv MAIL_CACHE_REMOVE_APPROVED false
  upsert_env_kv OFFLOAD_APPROVED false
  upsert_env_kv DELETE_OFFLOADED_SOURCE_APPROVED false
  upsert_env_kv SPOTLIGHT_REINDEX_APPROVED false
  chmod 600 "$ENV_FILE"
}

run_diagnose() {
  "$ROOT_DIR/scripts/00-diagnose.sh"
  "$ROOT_DIR/scripts/07-inventory-noise.sh"
  "$ROOT_DIR/scripts/08-focus-layout.sh"
  "$ROOT_DIR/scripts/01-summarize.sh"
  "$ROOT_DIR/scripts/09-emit-findings.sh"
  log "Mode diagnose complete. No write remediation was performed."
  printf 'Human report:  %s\n' "$ROOT_DIR/handoffs/current/FINDINGS.txt"
  printf 'Machine copy:  %s\n' "$ROOT_DIR/handoffs/current/findings.json"
  printf 'HITL: read FINDINGS.txt, then run: %s run repair\n' "$BIN"
}

ensure_env() {
  if [ ! -f "$ENV_FILE" ]; then
    "$ROOT_DIR/scripts/02-initialize-env.sh"
  fi
}

run_repair_plan() {
  require_diagnosis
  [ -f "$(state_dir)/noise-inventory-path" ] || "$ROOT_DIR/scripts/07-inventory-noise.sh"
  ensure_env
  local actions
  actions="$(select_safe_actions)"
  if [ -z "$actions" ]; then
    log "No allowlisted reclaimable noise found. Repair has nothing to apply."
    apply_safe_env_flags "" NOT_APPROVED NOT_AUTHORIZED repair
    printf 'NO_SAFE_NOISE=true\n'
    return 0
  fi
  apply_safe_env_flags "$actions" NOT_APPROVED NOT_AUTHORIZED repair
  "$ROOT_DIR/scripts/03-validate-env.sh"
  "$ROOT_DIR/scripts/04-plan.sh"
  log "Repair plan ready. HITL required: review the plan, then confirm APPLY_CONFIRMATION."
  printf 'HITL_REQUIRED=true\nAPPROVED_ACTIONS=%s\nPLAN=%s\n' "$actions" "$(cat "$(state_dir)/approved-plan-path")"
  printf 'After explicit yes: set APPLY_CONFIRMATION, re-validate, then apply + verify.\n'
}

run_autonomy() {
  if [ ! -f "$(state_dir)/diagnosis.complete" ]; then
    run_diagnose
  elif [ ! -f "$(state_dir)/noise-inventory-path" ]; then
    "$ROOT_DIR/scripts/07-inventory-noise.sh"
    "$ROOT_DIR/scripts/01-summarize.sh"
  fi
  ensure_env
  local actions
  actions="$(select_safe_actions)"
  if [ -z "$actions" ]; then
    log "Autonomy: no allowlisted reclaimable noise found. Nothing applied."
    return 0
  fi
  apply_safe_env_flags "$actions" I_APPROVE_THIS_PLAN I_AUTHORIZE_SAFE_NOISE_PURGE autonomy
  "$ROOT_DIR/scripts/03-validate-env.sh"
  "$ROOT_DIR/scripts/04-plan.sh"
  "$ROOT_DIR/scripts/05-apply.sh"
  "$ROOT_DIR/scripts/06-verify.sh"
}

case "$MODE" in
  diagnose) run_diagnose ;;
  repair) run_repair_plan ;;
  autonomy) run_autonomy ;;
  *) die "Unknown mode: $MODE (diagnose|repair|autonomy)" ;;
esac
