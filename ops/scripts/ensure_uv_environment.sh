#!/usr/bin/env bash
# Synchronize the locked governance environment only when its input fingerprint changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
STATE_FILE="$GOV_ROOT/.venv/.l9-uv-fingerprint"
MODE="${2:-apply}"

if ! command -v uv >/dev/null 2>&1; then
  echo "UV: unavailable; locked governance environment not activated" >&2
  exit 2
fi
if [ ! -f "$GOV_ROOT/pyproject.toml" ] || [ ! -f "$GOV_ROOT/uv.lock" ]; then
  echo "UV: pyproject.toml or uv.lock missing under $GOV_ROOT" >&2
  exit 2
fi

fingerprint() {
  python3 - "$GOV_ROOT" "$(uv --version 2>/dev/null || true)" <<'PY'
import hashlib
import platform
import sys
from pathlib import Path

root = Path(sys.argv[1])
uv_version = sys.argv[2]
h = hashlib.sha256()
for name in ("pyproject.toml", "uv.lock"):
    path = root / name
    h.update(name.encode())
    h.update(b"\0")
    h.update(path.read_bytes())
    h.update(b"\0")
for value in (
    platform.python_version(),
    platform.python_implementation(),
    platform.system(),
    platform.machine(),
    uv_version,
):
    h.update(value.encode())
    h.update(b"\0")
print(h.hexdigest())
PY
}

expected="$(fingerprint)"
current=""
[ -f "$STATE_FILE" ] && current="$(cat "$STATE_FILE")"

# One interpreter predicate for the whole script: the cached-environment guard,
# the post-sync check and the seal all name this binary. A venv that ships only
# a python3 shim (no python alias) passes the guard and must seal with it too.
VENV_PYTHON="$GOV_ROOT/.venv/bin/python3"

_seal_memory_artifact() {
  # Fail-open, never silent: an offline or unsealed venv stays
  # compatible/unproven rather than taking SessionStart down, and the binder
  # still reports the gap — but the reason is printed, not swallowed. The
  # module bounds its own subprocesses (timeouts, no prompts).
  if [ ! -f "$GOV_ROOT/ops/memory/seal_artifact_provenance.py" ]; then
    return 0
  fi
  local rc=0
  PYTHONPATH="$GOV_ROOT" "$VENV_PYTHON" \
    -m ops.memory.seal_artifact_provenance \
    --root "$GOV_ROOT" --interpreter "$VENV_PYTHON" >&2 || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "UV: memory artifact seal did not complete (rc=$rc); binding stays compatible/unproved" >&2
  fi
  return 0
}

if [ "$current" = "$expected" ] && [ -x "$VENV_PYTHON" ]; then
  # Diagnostic, not a machine result: stdout in this chain is the sessionStart
  # JSON payload, so every human-readable line must go to stderr (F-08).
  echo "UV: cached locked environment" >&2
  if [ "$MODE" != "check" ]; then
    _seal_memory_artifact
  fi
  exit 0
fi

if [ "$MODE" = "check" ]; then
  echo "UV: environment synchronization required" >&2
  exit 1
fi

(
  cd "$GOV_ROOT"
  # uv writes its resolution report to stdout; that stream is the machine
  # payload upstream, so hand its human output to stderr (F-08).
  #
  # --no-build refuses source distributions. Installing a dependency must not be
  # able to execute it: a sdist's setup.py runs arbitrary code at install time,
  # on every machine that bootstraps this governance environment. Every package
  # in uv.lock resolves to a wheel, so this costs nothing today and fails loudly
  # rather than silently building if that ever stops being true.
  uv sync --locked --no-build --extra dev >&2
)

if [ ! -x "$VENV_PYTHON" ]; then
  echo "UV: sync completed without a usable .venv/bin/python3" >&2
  exit 1
fi

mkdir -p "$(dirname "$STATE_FILE")"
tmp="${STATE_FILE}.tmp.$$"
printf '%s\n' "$expected" > "$tmp"
mv "$tmp" "$STATE_FILE"
echo "UV: synchronized locked environment" >&2
_seal_memory_artifact
