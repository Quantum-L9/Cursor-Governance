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

if [ "$current" = "$expected" ] && [ -x "$GOV_ROOT/.venv/bin/python3" ]; then
  echo "UV: cached locked environment"
  exit 0
fi

if [ "$MODE" = "check" ]; then
  echo "UV: environment synchronization required" >&2
  exit 1
fi

(
  cd "$GOV_ROOT"
  uv sync --locked --extra dev
)

if [ ! -x "$GOV_ROOT/.venv/bin/python3" ]; then
  echo "UV: sync completed without a usable .venv/bin/python3" >&2
  exit 1
fi

mkdir -p "$(dirname "$STATE_FILE")"
tmp="${STATE_FILE}.tmp.$$"
printf '%s\n' "$expected" > "$tmp"
mv "$tmp" "$STATE_FILE"
echo "UV: synchronized locked environment"
