#!/usr/bin/env bash
# Resolve PR_STACK=auto onto the unique open-PR chain tip for the publish path.
# shellcheck shell=bash
#
# Same topology as ops/scripts/resolve_stack_tip.py (start and publish).
# This lib is the *when*: Makefile default PR_STACK=auto must bind PR_BASE
# before pr-check selects changed files, not only after the gate in
# open_pr_after_gate.sh.
#
# Usage:
#   source ops/scripts/lib/resolve_pr_stack.sh
#   pr_stack_apply_publish_base "$WS" || exit $?
#   # PR_BASE is exported
#
# Env:
#   PR_STACK                 auto → resolve; empty → keep PR_BASE
#   PR_BASE                  default origin/main; a non-main value is explicit
#   PR_STACK_BASE_EXPLICIT=1 never rewrite even when PR_BASE is origin/main
#   L9_STACK_TIP_RESOLVER    override python resolver (tests)
#   STACK_BASE_RECEIPT_TTL_S max age for .l9/pr/stack-base.json (default 60)
#
# Telemetry (gh missing / api fail): WARN and keep PR_BASE (fail-open).
# Sibling / unreadable topology: FAIL (exit 2). Empty PR_STACK never calls gh.

STACK_BASE_RECEIPT_TTL_S="${STACK_BASE_RECEIPT_TTL_S:-60}"
STACK_BASE_RECEIPT_REL=".l9/pr/stack-base.json"

_PR_STACK_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

pr_stack_is_main_base() {
  case "${1#origin/}" in
    main|master) return 0 ;;
    *) return 1 ;;
  esac
}

pr_stack_normalize_ref() {
  local tip="$1"
  case "$tip" in
    origin/main|main) printf '%s' "origin/main" ;;
    origin/*) printf '%s' "$tip" ;;
    "") printf '%s' "origin/main" ;;
    *) printf '%s' "origin/${tip}" ;;
  esac
}

pr_stack_receipt_path() {
  printf '%s/%s' "$1" "$STACK_BASE_RECEIPT_REL"
}

pr_stack_receipt_write() {
  local ws="$1" base="$2" reason="$3" sha="$4" path
  path="$(pr_stack_receipt_path "$ws")"
  mkdir -p "$(dirname "$path")"
  python3 - "$path" "$base" "$reason" "$sha" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, base, reason, sha = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
doc = {
    "schema": "l9.stack_base.v1",
    "pr_stack": "auto",
    "pr_base": base,
    "reason": reason,
    "tip_sha": sha,
    "resolved_at": datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z"),
}
with open(path, "w", encoding="utf-8") as handle:
    handle.write(json.dumps(doc, indent=2) + "\n")
print(f"stack-base receipt written: {path}")
PY
}

# Exit 0 when publish may reuse a still-fresh unique-tip receipt.
pr_stack_receipt_reusable() {
  local ws="$1" path live ttl
  path="$(pr_stack_receipt_path "$ws")"
  [[ -f "$path" ]] || return 1
  ttl="${STACK_BASE_RECEIPT_TTL_S:-60}"
  live="$(
    python3 - "$path" "$ttl" "$ws" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

path, ttl_s, ws = sys.argv[1], int(sys.argv[2]), sys.argv[3]
try:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
if doc.get("schema") != "l9.stack_base.v1":
    raise SystemExit(1)
if doc.get("pr_stack") != "auto":
    raise SystemExit(1)
base = str(doc.get("pr_base") or "")
if not base:
    raise SystemExit(1)
raw = str(doc.get("resolved_at") or "")
try:
    stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
except ValueError:
    raise SystemExit(1)
age = (datetime.now(timezone.utc) - stamp).total_seconds()
if not (0 <= age <= ttl_s):
    raise SystemExit(1)
probe = subprocess.run(
    ["git", "-C", ws, "rev-parse", "--verify", base],
    capture_output=True,
    text=True,
    check=False,
)
sha = (probe.stdout or "").strip()
want = str(doc.get("tip_sha") or "")
if want and probe.returncode == 0 and sha != want:
    raise SystemExit(1)
print(base)
PY
  )" || return 1
  [[ -n "$live" ]] || return 1
  PR_STACK_RECEIPT_BASE="$live"
  return 0
}

pr_stack_invoke_resolver() {
  local workspace="$1"
  local resolver="${L9_STACK_TIP_RESOLVER:-$_PR_STACK_SCRIPTS_DIR/resolve_stack_tip.py}"
  python3 "$resolver" --workspace "$workspace"
}

pr_stack_is_telemetry_fail() {
  local text="$1"
  case "$text" in
    *"gh CLI unavailable"*|*"could not enumerate open PRs"*|*"cannot resolve repository identity"*)
      return 0
      ;;
    *) return 1 ;;
  esac
}

# Bind PR_BASE for make pr / pr-check / pr-preflight / open_pr_after_gate.
# Does not rewrite an explicit non-main PR_BASE. Empty PR_STACK is a no-op.
pr_stack_apply_publish_base() {
  local workspace="$1" out rc tip sha reason base
  workspace="$(cd "$workspace" && pwd)"
  PR_BASE="${PR_BASE:-origin/main}"

  if [ "${PR_STACK:-}" != "auto" ]; then
    return 0
  fi
  if [ "${PR_STACK_BASE_EXPLICIT:-0}" = "1" ]; then
    return 0
  fi
  if ! pr_stack_is_main_base "$PR_BASE"; then
    echo "NOTE: PR_STACK=auto left explicit PR_BASE=$PR_BASE"
    return 0
  fi

  PR_STACK_RECEIPT_BASE=""
  if pr_stack_receipt_reusable "$workspace"; then
    PR_BASE="$PR_STACK_RECEIPT_BASE"
    export PR_BASE
    echo "OK: reuse stack-base receipt (age < ${STACK_BASE_RECEIPT_TTL_S}s): $PR_BASE"
    return 0
  fi

  set +e
  out="$(pr_stack_invoke_resolver "$workspace" 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    if pr_stack_is_telemetry_fail "$out"; then
      printf '%s\n' "$out" >&2
      echo "WARN: PR_STACK=auto could not read open PRs — keeping PR_BASE=$PR_BASE" >&2
      return 0
    fi
    printf '%s\n' "$out" >&2
    echo "FAIL: PR_STACK=auto could not resolve a unique stack tip (exit ${rc})" >&2
    return "$rc"
  fi

  tip="$(printf '%s\n' "$out" | sed -n 's/^STACK_TIP=//p' | head -n 1)"
  sha="$(printf '%s\n' "$out" | sed -n 's/^STACK_TIP_SHA=//p' | head -n 1)"
  reason="$(printf '%s\n' "$out" | sed -n 's/^REASON=//p' | head -n 1)"
  if [ -z "$tip" ]; then
    echo "FAIL: stack-tip resolver returned no STACK_TIP" >&2
    return 2
  fi
  base="$(pr_stack_normalize_ref "$tip")"
  if [ "$base" != "origin/main" ]; then
    if ! git -C "$workspace" rev-parse --verify "$base" >/dev/null 2>&1; then
      if ! git -C "$workspace" fetch origin "${base#origin/}"; then
        echo "FAIL: cannot fetch $base — stack tip unverifiable" >&2
        return 1
      fi
    fi
    if type fetch_receipt_write >/dev/null 2>&1; then
      fetch_receipt_write "$workspace" "${base#origin/}" \
        "$(git -C "$workspace" rev-parse "$base")" || true
    fi
  fi
  PR_BASE="$base"
  export PR_BASE
  echo "NOTE: PR_STACK=auto resolved stack tip ${PR_BASE} (reason=${reason:-unknown})"
  printf '%s\n' "$out"
  pr_stack_receipt_write "$workspace" "$PR_BASE" "${reason:-unknown}" "$sha" || true
  return 0
}
