#!/usr/bin/env bash
# Native publish route (ops/config/publish-authority.json).
#
# `make pr` / `l9 pr` resolved this workspace's origin to a repository that owns
# its own publication ceremony (today github.com/cryptoxdog/ib-odoo_19 → its own
# `make pr`, base Staging; CANONICAL_LAW §13). Governance delegates to that
# target exactly once. The resolver is re-run here with a real exit code, so a
# parse-time mis-resolution in publish.mk can never widen the publish plane.
#
#   run_native_publish.sh <WS>     env: OPEN_PR (1|0), PR_BASE (explicit only)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# The checkout this script runs from is authoritative (a sibling clone's
# resolver would not carry the same registry): derive GOV_ROOT from here.
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
OPEN_PR="${OPEN_PR:-1}"
PR_BASE="${PR_BASE:-}"

if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
  PY="$GOV_ROOT/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

resolver=("$PY" "$GOV_ROOT/ops/autonomy/publish_authority.py" --workspace "$WS" --format json --expect native)
if [[ -n "$PR_BASE" ]]; then
  resolver+=(--pr-base "$PR_BASE")
fi
decision="$("${resolver[@]}")"   # exit 2/3 propagates (set -e)

field() { printf '%s' "$decision" | "$PY" -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print("" if v is None else v)' "$1"; }
origin="$(field origin)"
native_target="$(field native_target)"
check_target="$(field native_check_target)"
declared_base="$(field declared_base)"

if [[ "$OPEN_PR" = "1" ]]; then
  target="$native_target"
else
  target="$check_target"
  if [[ -z "$target" ]]; then
    echo "NATIVE_GATE_ONLY_UNSUPPORTED: $origin declares no native_check_target; OPEN_PR=0 has no native equivalent" >&2
    exit 2
  fi
fi

# The consumer Makefile must actually declare the target we are about to run
# (database read only; the goal is never built here).
targets="$(make -C "$WS" --no-print-directory -rRpn help 2>/dev/null || true)"
if ! grep -q "^${target}:" <<<"$targets"; then
  echo "NATIVE_TARGET_MISSING: $WS/Makefile declares no '${target}' target (registry says route=native for $origin)" >&2
  exit 2
fi

mkdir -p "$WS/.l9/pr"
head_sha="$(git -C "$WS" rev-parse HEAD 2>/dev/null || echo "")"
"$PY" - "$WS/.l9/pr/publish-route.json" "$origin" "$target" "$declared_base" "$head_sha" "$OPEN_PR" <<'PY'
import datetime as dt
import json
import sys

out, origin, target, base, head, open_pr = sys.argv[1:7]
with open(out, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "schema": "l9.publish_route.v1",
            "route": "native",
            "origin": origin,
            "target": target,
            "declared_base": base,
            "head": head,
            "open_pr": open_pr == "1",
            "registry": "ops/config/publish-authority.json",
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        },
        handle,
        indent=2,
    )
PY

echo "publish-authority: $origin → native make $target (base $declared_base) in $WS"
# Scrub governance make state so the consumer recipe runs exactly as a human's
# `make <target>` would: no inherited MAKEFLAGS/MAKEOVERRIDES, no governance
# PYTHON, no PR_EARLY_OVERLAP, and none of the governance-only knobs the
# publish.mk recipe exported into this script (WS, OPEN_PR, PR_BASE — an
# exported empty PR_BASE would override a consumer's own `PR_BASE ?=`).
# "$WS" is expanded by this shell before env runs, so -u WS is safe.
exec env -u MAKEFLAGS -u MFLAGS -u MAKELEVEL -u MAKEOVERRIDES -u PYTHON -u PR_EARLY_OVERLAP \
  -u WS -u OPEN_PR -u PR_BASE \
  make -C "$WS" "$target" base="$declared_base"
