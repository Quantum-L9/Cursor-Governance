#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENSURE="$SCRIPT_DIR/../ensure_uv_environment.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/uv-fingerprint.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
ROOT="$TMP_ROOT/governance"
BIN="$TMP_ROOT/bin"
COUNT="$TMP_ROOT/sync-count"
mkdir -p "$ROOT" "$BIN"
printf '%s\n' '[project]' 'name="fixture"' > "$ROOT/pyproject.toml"
printf '%s\n' 'version = 1' > "$ROOT/uv.lock"
printf '0\n' > "$COUNT"

cat > "$BIN/uv" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "--version" ]; then
  echo "uv 9.9.9-fixture"
  exit 0
fi
if [ "${1:-}" = "sync" ]; then
  count_file=${UV_TEST_COUNT:?}
  root=${UV_TEST_ROOT:?}
  n=$(cat "$count_file")
  n=$((n + 1))
  printf '%s\n' "$n" > "$count_file"
  mkdir -p "$root/.venv/bin"
  # Absolute, not `python3`: the venv interpreter must not follow the caller's
  # PATH, or the PATH-shadow case below would shadow it as well.
  printf '#!/usr/bin/env bash\nexec %q "$@"\n' "${UV_TEST_REAL_PY:?}" > "$root/.venv/bin/python3"
  chmod +x "$root/.venv/bin/python3"
  exit 0
fi
exit 2
SH
chmod +x "$BIN/uv"

UV_TEST_REAL_PY="$(command -v python3)"
export UV_TEST_REAL_PY
export PATH="$BIN:$PATH"
export UV_TEST_COUNT="$COUNT"
export UV_TEST_ROOT="$ROOT"

bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "1" ]
bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "1" ]
printf '%s\n' 'version = 2' > "$ROOT/uv.lock"
bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "2" ]
rm "$ROOT/.venv/bin/python3"
if bash "$ENSURE" "$ROOT" check >/dev/null 2>&1; then
  echo "FAIL: invalid venv passed check mode" >&2
  exit 1
fi
bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "3" ]

# A caller whose PATH resolves `python3` to a different interpreter (inside the
# venv, or outside it) is the same environment. Fingerprinting the caller's
# python3 made every crossing re-sync and force-reinstall the memory wheel.
SHADOW="$TMP_ROOT/shadow"
mkdir -p "$SHADOW/site"
printf '%s\n' 'import platform' 'platform.python_version = lambda: "0.0.0-shadow"' \
  > "$SHADOW/site/sitecustomize.py"
printf '#!/usr/bin/env bash\nPYTHONPATH=%q exec %q "$@"\n' "$SHADOW/site" "$UV_TEST_REAL_PY" \
  > "$SHADOW/python3"
chmod +x "$SHADOW/python3"
[ "$(PATH="$SHADOW:$PATH" python3 -c 'import platform; print(platform.python_version())')" = "0.0.0-shadow" ]
PATH="$SHADOW:$PATH" bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "3" ] || { echo "FAIL: PATH python3 shadow forced a re-sync" >&2; exit 1; }
PATH="$SHADOW:$PATH" bash "$ENSURE" "$ROOT" check >/dev/null
bash "$ENSURE" "$ROOT" >/dev/null
[ "$(cat "$COUNT")" = "3" ] || { echo "FAIL: leaving the PATH shadow forced a re-sync" >&2; exit 1; }

echo "RESULT: PASS (fingerprint cache, input change, invalid venv, PATH python3 shadow)"
