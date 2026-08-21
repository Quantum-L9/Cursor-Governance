#!/usr/bin/env bash
# Fail-closed locked interpreter for Make and bash gates.
#
# Materializes $(GOV_ROOT)/.venv from pyproject.toml + uv.lock, then proves:
#   * .venv/bin/python and python3 exist and are executable
#   * sys.prefix is that venv (not Homebrew / system / miniconda base)
#   * PATH python3 resolves to .venv/bin/python3
#   * runtime imports declared in pyproject / python-contract import_map load
#
# Usage: ensure_gov_python.sh [GOV_ROOT]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# pwd -P: /tmp is a symlink to /private/tmp on macOS. uv/sys.prefix
# report the real path; a lexical compare would fail a valid worktree venv.
GOV_ROOT="$(cd "${1:-$SCRIPT_DIR/../..}" && pwd -P)"
VENV="$GOV_ROOT/.venv"
PYTHON="$VENV/bin/python"
PYTHON3="$VENV/bin/python3"

# Caller PATH= must not hide uv. Prefer PATH, then well-known install locations.
if ! command -v uv >/dev/null 2>&1; then
  for _uv in \
    "${HOME}/.local/bin/uv" \
    "${HOME}/.cargo/bin/uv" \
    /opt/homebrew/bin/uv \
    /usr/local/bin/uv
  do
    if [ -x "$_uv" ]; then
      PATH="$(dirname "$_uv"):${PATH}"
      export PATH
      break
    fi
  done
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "FAIL: uv is required to materialize $VENV (https://docs.astral.sh/uv/)" >&2
  exit 2
fi
if [ ! -f "$GOV_ROOT/pyproject.toml" ] || [ ! -f "$GOV_ROOT/uv.lock" ]; then
  echo "FAIL: pyproject.toml or uv.lock missing under $GOV_ROOT" >&2
  exit 2
fi

bash "$SCRIPT_DIR/ensure_uv_environment.sh" "$GOV_ROOT"

if [ ! -x "$PYTHON" ] || [ ! -x "$PYTHON3" ]; then
  echo "FAIL: locked interpreter missing after sync ($PYTHON)" >&2
  exit 2
fi

prefix="$("$PYTHON" -c 'import sys; print(sys.prefix)')"
if [ "$prefix" != "$VENV" ]; then
  echo "FAIL: $PYTHON sys.prefix=$prefix, expected $VENV" >&2
  exit 2
fi

export PATH="$VENV/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$VENV"
export UV_LOCKED=1
on_path="$(command -v python3)"
if [ "$on_path" != "$PYTHON3" ]; then
  echo "FAIL: python3 on PATH is $on_path, expected $PYTHON3" >&2
  exit 2
fi

"$PYTHON" - "$GOV_ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
required = ["yaml", "pydantic", "jsonschema", "structlog", "cryptography"]
contract = root / "ops" / "config" / "python-contract.json"
if contract.is_file():
    data = json.loads(contract.read_text(encoding="utf-8"))
    skip = {"pytest", "xdist", "pytest_timeout"}
    for name in data.get("import_map", {}):
        if name not in skip:
            required.append(name)
seen: list[str] = []
for name in required:
    if name not in seen:
        seen.append(name)
missing: list[str] = []
for name in seen:
    try:
        __import__(name)
    except Exception as exc:  # noqa: BLE001 — probe must name the exact import failure
        missing.append(f"{name}: {type(exc).__name__}: {exc}")
if missing:
    print("FAIL: locked .venv missing required imports (pyproject.toml / uv.lock):", file=sys.stderr)
    for row in missing:
        print(f"  {row}", file=sys.stderr)
    print("Fix: uv sync --locked --extra dev", file=sys.stderr)
    raise SystemExit(2)
print(f"OK: gov-python {sys.executable}")
PY
