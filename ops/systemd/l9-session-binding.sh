#!/usr/bin/env bash
# L9 session-binding precondition for l9-governance.service.
# Refreshes the authority checkout, computes the Manus projection binding,
# and logs the result. Non-fatal by default so the tool surface stays up
# even when the authority checkout is unreachable; set L9_BINDING_STRICT=1
# to make a failed binding fail the unit instead.
set -uo pipefail
ROOT=/home/l9/Cursor-Governance
PY="$ROOT/.venv/bin/python"
export HOME=/home/l9
export L9_AUTHORITY_ROOT=/home/l9/.github
export PATH=/usr/local/bin:/usr/bin:/bin
if [ ! -x "$PY" ]; then echo "l9-session-binding: interpreter missing at $PY"; exit 0; fi
timeout 60 bash "$ROOT/ops/scripts/ensure_authority_checkout.sh" >/dev/null 2>&1 || echo "l9-session-binding: authority refresh failed (continuing)"
out=$("$PY" "$ROOT/ops/autonomy/host_binding.py" --host manus --format line 2>&1) || true
printf "%s\n" "$out" | head -3
first=$(printf "%s\n" "$out" | head -1)
if printf "%s" "$first" | grep -q "NOT BOUND"; then status="NOT BOUND"; elif printf "%s" "$first" | grep -q "BOUND"; then status="BOUND"; else status="UNKNOWN"; fi
authority=$(git -C "$L9_AUTHORITY_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)
echo "l9-session-binding: status=$status authority=$authority at $(date -u +%FT%TZ)"
if [ "${L9_BINDING_STRICT:-0}" = "1" ] && [ "$status" != "BOUND" ]; then exit 1; fi
exit 0
