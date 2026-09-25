#!/usr/bin/env bash
# Synchronize the locked governance environment only when its input fingerprint changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "$0")"
GOV_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
STATE_FILE="$GOV_ROOT/.venv/.l9-uv-fingerprint"
MODE="${2:-apply}"

# Writer side of the venv readiness contract; the reader is
# ops/memory/venv_ready.py and names the same two paths.
#
# Claude Code starts every SessionStart hook at once, with no ordering. One
# hook ran this script (uv sync + the seal's force-reinstall of
# l9_graphite_memory) while another spawned l9-memory from the same .venv; the
# runtime imported a half-replaced package and died with ModuleNotFoundError
# (2026-09-24, 23:48:55Z hydrate vs 23:48:57Z reinstall). So:
#   LOCK_FILE    held EXCLUSIVE for the whole mutation; readers take it SHARED
#                and wait, so neither side runs under the other.
#   IN_PROGRESS  written before the mutation, removed only once the result is
#                verified importable. Present with the lock free means the
#                install died part-way: readers refuse it and the next apply
#                re-synchronizes from scratch.
LOCK_FILE="$GOV_ROOT/.l9/uv-environment.lock"
IN_PROGRESS="$GOV_ROOT/.l9/uv-environment.installing"

if ! command -v uv >/dev/null 2>&1; then
  echo "UV: unavailable; locked governance environment not activated" >&2
  exit 2
fi
if [ ! -f "$GOV_ROOT/pyproject.toml" ] || [ ! -f "$GOV_ROOT/uv.lock" ]; then
  echo "UV: pyproject.toml or uv.lock missing under $GOV_ROOT" >&2
  exit 2
fi

# One interpreter predicate for the whole script: the cached-environment guard,
# the post-sync check and the seal all name this binary. A venv that ships only
# a python3 shim (no python alias) passes the guard and must seal with it too.
VENV_PYTHON="$GOV_ROOT/.venv/bin/python3"

# The interpreter whose identity the fingerprint records: the venv's own, never
# the caller's `python3`. Callers inside the venv (pytest, the gate's reader
# wave) resolve `python3` to .venv/bin (3.12 here) while callers outside it
# resolve the system one (3.11): the same tree then fingerprinted two ways, so
# every crossing between the two ran `uv sync` and the seal's force-reinstall of
# the memory wheel — mid-pytest, under other xdist workers importing it. Before
# the first sync there is no venv, the fallback cannot match any stored value,
# and the post-sync fingerprint is recomputed with the venv interpreter.
_fingerprint_python() {
  if [ -x "$VENV_PYTHON" ]; then
    printf '%s\n' "$VENV_PYTHON"
  else
    printf '%s\n' python3
  fi
}

fingerprint() {
  "$(_fingerprint_python)" - "$GOV_ROOT" "$(uv --version 2>/dev/null || true)" <<'PY'
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

if [ "$MODE" = "check" ] && [ -e "$IN_PROGRESS" ]; then
  echo "UV: previous install did not complete ($IN_PROGRESS); synchronization required" >&2
  exit 1
fi

# Apply runs under the lock, in its OWN session. A SessionStart hook that
# reaches its deadline tears down its whole process group (the installer's
# run_with_timeout, the governance hook's watchdog); a uv sync or pip
# force-reinstall killed there leaves site-packages half-written. setsid puts
# the mutation outside that group so it always finishes and releases the lock,
# and its output goes to a file, not the caller's pipes, so an outliving
# child can never hold the hook's stdout open. The caller waits for it and
# replays the log; if the caller is killed first, the work completes anyway.
if [ "$MODE" != "check" ] && [ -z "${_L9_UV_ENV_LOCKED:-}" ]; then
  if command -v flock >/dev/null 2>&1 && command -v setsid >/dev/null 2>&1 \
     && mkdir -p "$GOV_ROOT/.l9" 2>/dev/null; then
    _log="$GOV_ROOT/.l9/uv-environment.$$.log"
    _rc=0
    _L9_UV_ENV_LOCKED=1 setsid --wait \
      flock -E 75 -w "${L9_UV_ENV_LOCK_WAIT_S:-600}" "$LOCK_FILE" \
      bash "$SCRIPT_PATH" "$GOV_ROOT" "$MODE" </dev/null >"$_log" 2>&1 || _rc=$?
    cat "$_log" >&2 2>/dev/null || true
    rm -f "$_log"
    if [ "$_rc" -eq 75 ]; then
      echo "UV: $LOCK_FILE still held after ${L9_UV_ENV_LOCK_WAIT_S:-600}s; another sync owns this environment" >&2
    fi
    exit "$_rc"
  fi
  echo "UV: flock/setsid unavailable; synchronizing without the environment lock" >&2
fi

_verify_environment() {
  # The venv is installed only when its interpreter imports what memory needs.
  local probe='import sys'
  if grep -q '^name = "l9-graphite-memory"$' "$GOV_ROOT/uv.lock" 2>/dev/null; then
    probe='import l9_graphite_memory'
  fi
  if [ -x "$VENV_PYTHON" ] && "$VENV_PYTHON" -c "$probe" >/dev/null 2>&1; then
    rm -f "$IN_PROGRESS"
    return 0
  fi
  echo "UV: environment verification failed ($probe); $IN_PROGRESS kept so memory refuses this .venv" >&2
  return 1
}

_begin_mutation() {
  mkdir -p "$(dirname "$IN_PROGRESS")"
  printf '%s %s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$IN_PROGRESS"
}

if [ -e "$IN_PROGRESS" ]; then
  echo "UV: previous install did not complete ($(cat "$IN_PROGRESS" 2>/dev/null)); re-synchronizing" >&2
  rm -f "$STATE_FILE"
fi

expected="$(fingerprint)"
current=""
[ -f "$STATE_FILE" ] && current="$(cat "$STATE_FILE")"

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
    # The seal may force-reinstall the memory wheel: a mutation like any other.
    _begin_mutation
    _seal_memory_artifact
    _verify_environment
  fi
  exit 0
fi

if [ "$MODE" = "check" ]; then
  echo "UV: environment synchronization required" >&2
  exit 1
fi

_begin_mutation
_sync_rc=0
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
) || _sync_rc=$?
if [ "$_sync_rc" -ne 0 ]; then
  # A refused sync (offline, lock mismatch) usually never touched the old
  # environment; clear the marker only if that environment still imports.
  echo "UV: uv sync failed (rc=$_sync_rc)" >&2
  _verify_environment || true
  exit "$_sync_rc"
fi

if [ ! -x "$VENV_PYTHON" ]; then
  echo "UV: sync completed without a usable .venv/bin/python3" >&2
  exit 1
fi

# Recorded as the NEXT caller will compute it: with the venv interpreter the
# sync just produced, not the fallback that computed the pre-sync value.
expected="$(fingerprint)"
mkdir -p "$(dirname "$STATE_FILE")"
tmp="${STATE_FILE}.tmp.$$"
printf '%s\n' "$expected" > "$tmp"
mv "$tmp" "$STATE_FILE"
echo "UV: synchronized locked environment" >&2
_seal_memory_artifact
_verify_environment
