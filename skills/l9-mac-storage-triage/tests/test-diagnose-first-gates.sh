#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

grep -q 'require_diagnosis' "$ROOT_DIR/scripts/03-validate-env.sh"
grep -q 'require_diagnosis' "$ROOT_DIR/scripts/04-plan.sh"
grep -q 'require_diagnosis' "$ROOT_DIR/scripts/05-apply.sh"
grep -q 'require_plan' "$ROOT_DIR/scripts/05-apply.sh"
grep -q 'I_APPROVE_THIS_PLAN' "$ROOT_DIR/scripts/05-apply.sh"
grep -q 'I_AUTHORIZE_SAFE_NOISE_PURGE' "$ROOT_DIR/scripts/05-apply.sh"
grep -q 'approved-config.sha256' "$ROOT_DIR/scripts/05-apply.sh"
grep -q 'rclone copy' "$ROOT_DIR/scripts/actions/offload-rclone.sh"
grep -q 'rclone check' "$ROOT_DIR/scripts/actions/offload-rclone.sh"
grep -q 'OFFLOAD_VERIFICATION_RECEIPT' "$ROOT_DIR/scripts/actions/delete-verified-source.sh"
grep -q 'container prune' "$ROOT_DIR/scripts/actions/docker-prune-unused.sh"
grep -q 'SKIP volumes' "$ROOT_DIR/scripts/actions/docker-prune-unused.sh"
grep -q 'purge_stale_caches' "$ROOT_DIR/scripts/mode-run.sh"
grep -q 'uv cache clean --force' "$ROOT_DIR/scripts/actions/purge-stale-caches.sh"
grep -q 'Library/Caches/Google' "$ROOT_DIR/scripts/actions/purge-stale-caches.sh"
grep -q 'not an allowlisted cache leaf' "$ROOT_DIR/scripts/actions/purge-stale-caches.sh"
grep -q 'Library/Caches/Homebrew' "$ROOT_DIR/scripts/actions/purge-stale-caches.sh"
if grep -E '^[^#]*brew[[:space:]]+cleanup' "$ROOT_DIR/scripts/actions/purge-stale-caches.sh"; then
  printf 'brew_cleanup_touches_prefix=fail\n' >&2
  exit 1
fi
if grep -E 'actions\+\=\((mail_cache_remove|offload_rclone|delete_verified_source)\)' "$ROOT_DIR/scripts/mode-run.sh"; then
  printf 'mode_run_auto_selects_non_allowlisted=fail\n' >&2
  exit 1
fi
if grep -R -nE '^[[:space:]]*(sudo[[:space:]]+)?mdutil[[:space:]]+-E' "$ROOT_DIR/scripts" >/dev/null 2>&1; then
  printf 'unsafe_mdutil_reindex=fail\n' >&2
  exit 1
fi
if grep -R -nE 'docker (system prune -a|volume prune -f)' "$ROOT_DIR/scripts/actions" >/dev/null 2>&1; then
  printf 'unsafe_docker_prune=fail\n' >&2
  exit 1
fi
printf 'diagnose_first_gates=pass\n'
