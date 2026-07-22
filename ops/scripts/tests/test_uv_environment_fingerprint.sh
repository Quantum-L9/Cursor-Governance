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
  cat > "$root/.venv/bin/python3" <<'PY'
#!/usr/bin/env bash
exec python3 "$@"
PY
  chmod +x "$root/.venv/bin/python3"
  exit 0
fi
exit 2
SH
chmod +x "$BIN/uv"

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

echo "RESULT: PASS (fingerprint cache, input change, invalid venv)"
