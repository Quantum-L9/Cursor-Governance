#!/usr/bin/env bash
# Velocity security gate: one gitleaks process, fail-closed parallel scanners,
# and Semgrep configs that omit p/python unless PROFILE=full.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY="$SCRIPTS_DIR/run_pr_security.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-pr-security-speed.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

FAKE="$TMP_ROOT/fakebin"
mkdir -p "$FAKE"
COUNT="$TMP_ROOT/gitleaks.count"
ARGS="$TMP_ROOT/semgrep.args"
: >"$COUNT"
: >"$ARGS"

cat >"$FAKE/gitleaks" <<'EOF'
#!/bin/sh
echo 1 >>"${L9_GITLEAKS_COUNT:?}"
if [ "${1:-}" = "version" ]; then
  echo "gitleaks version 8.30.0"
  exit 0
fi
if [ "${1:-}" = "dir" ] && [ "${2:-}" = "--help" ]; then
  echo "scan directories or files for secrets"
  exit 0
fi
if [ "${L9_GITLEAKS_FAIL:-0}" = "1" ]; then
  exit 1
fi
exit 0
EOF
cat >"$FAKE/semgrep" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >>"${L9_SEMGREP_ARGS:?}"
for arg in "$@"; do
  if [ "$arg" = "--version" ]; then
    echo "1.172.0"
    exit 0
  fi
done
exit 0
EOF
chmod +x "$FAKE/gitleaks" "$FAKE/semgrep"

ws="$TMP_ROOT/ws"
mkdir -p "$ws"
git init -q "$ws"
git -C "$ws" config user.email l9@example.com
git -C "$ws" config user.name L9
printf 'base\n' >"$ws/base.txt"
git -C "$ws" add base.txt
git -C "$ws" commit -qm "base"
printf 'one\n' >"$ws/one.txt"
printf 'two\n' >"$ws/two.txt"
git -C "$ws" add one.txt two.txt

export HOME="$TMP_ROOT"
export L9_GITLEAKS_COUNT="$COUNT"
export L9_SEMGREP_ARGS="$ARGS"
# Keep git/uv so bandit can run when a .py file is in scope; gitleaks/semgrep
# are the fakes under $FAKE.
SPEED_PATH="$FAKE:/usr/bin:/bin"
if command -v uv >/dev/null 2>&1; then
  SPEED_PATH="$FAKE:$(dirname "$(command -v uv)"):$SPEED_PATH"
fi
if command -v uvx >/dev/null 2>&1; then
  SPEED_PATH="$FAKE:$(dirname "$(command -v uvx)"):$SPEED_PATH"
fi

# `env -i` below scrubs the environment so the gate cannot read stray L9 vars.
# That scrub also removed the proxy and CA settings uv needs to reach the index,
# so on a sandboxed runner bandit could not be PROVISIONED at all — and the test
# then failed for want of network rather than for anything the gate did. Keeping
# uv on PATH while removing the only way it can fetch is a fixture that deletes
# the state it requires. Pass through just the network/TLS variables, by name,
# when the outer environment actually has them.
SPEED_NET_ENV=""
for _var in HTTPS_PROXY HTTP_PROXY ALL_PROXY NO_PROXY \
  https_proxy http_proxy all_proxy no_proxy \
  SSL_CERT_FILE SSL_CERT_DIR REQUESTS_CA_BUNDLE CURL_CA_BUNDLE \
  UV_CACHE_DIR UV_NATIVE_TLS UV_INSECURE_HOST; do
  if [ -n "${!_var:-}" ]; then
    SPEED_NET_ENV="$SPEED_NET_ENV $_var=${!_var}"
  fi
done
unset _var

run_gate() {
  local extra_env="$1"
  set +e
  env -i HOME="$TMP_ROOT" PATH="$SPEED_PATH" \
    L9_GITLEAKS_COUNT="$COUNT" L9_SEMGREP_ARGS="$ARGS" \
    L9_GITLEAKS_FAIL="${L9_GITLEAKS_FAIL:-0}" \
    $SPEED_NET_ENV \
    $extra_env \
    bash "$SECURITY" --mode gate "$ws" 2>&1
  local rc=$?
  set -e
  return $rc
}

: >"$COUNT"
set +e
out="$(run_gate "")"
rc=$?
set -e
[ "$rc" -eq 0 ] || fail "two-file gate should pass (rc=$rc): $out"
invocations="$(wc -l <"$COUNT" | tr -d ' ')"
# version + dir --help + one scan (never per-file detect)
[ "$invocations" -le 3 ] || fail "gitleaks invoked $invocations times (want <=3): $out"
grep -q "one process" <<<"$out" || fail "gitleaks did not report one process: $out"
grep -q "RESULT: PASS" <<<"$out" || fail "two-file gate did not PASS: $out"
pass "gitleaks scans the changed set in one process"

: >"$COUNT"
export L9_GITLEAKS_FAIL=1
set +e
fail_out="$(run_gate "")"
fail_rc=$?
set -e
unset L9_GITLEAKS_FAIL
[ "$fail_rc" -ne 0 ] || fail "a failing parallel scanner must FAIL the gate: $fail_out"
grep -q "RESULT: FAIL" <<<"$fail_out" || fail "failing scanner did not report FAIL: $fail_out"
pass "one failing parallel scanner fails the gate"

py_ws="$TMP_ROOT/pyws"
mkdir -p "$py_ws"
git init -q "$py_ws"
git -C "$py_ws" config user.email l9@example.com
git -C "$py_ws" config user.name L9
printf 'print("base")\n' >"$py_ws/base.py"
git -C "$py_ws" add base.py
git -C "$py_ws" commit -qm "base"
printf 'print("changed")\n' >"$py_ws/changed.py"
git -C "$py_ws" add changed.py

run_py() {
  local profile="$1"
  : >"$ARGS"
  set +e
  env -i HOME="$TMP_ROOT" PATH="$SPEED_PATH" \
    L9_GITLEAKS_COUNT="$COUNT" L9_SEMGREP_ARGS="$ARGS" \
    PR_SECURITY_PROFILE="$profile" \
    $SPEED_NET_ENV \
    bash "$SECURITY" --mode gate "$py_ws" 2>&1
  local rc=$?
  set -e
  return $rc
}

set +e
vel_out="$(run_py velocity)"
vel_rc=$?
set -e
[ "$vel_rc" -eq 0 ] || fail "velocity profile should pass (rc=$vel_rc): $vel_out"
grep -q "p/python" "$ARGS" && fail "velocity Semgrep argv included p/python: $(cat "$ARGS")"
grep -q "p/secrets" "$ARGS" || fail "velocity Semgrep argv omitted p/secrets: $(cat "$ARGS")"
grep -q "l9-pr.yml" "$ARGS" || fail "velocity Semgrep argv omitted local rules: $(cat "$ARGS")"
grep -q "profile=velocity" <<<"$vel_out" || fail "velocity summary omitted profile: $vel_out"
pass "velocity Semgrep is p/secrets + local rules (no p/python)"

set +e
full_out="$(run_py full)"
full_rc=$?
set -e
[ "$full_rc" -eq 0 ] || fail "full profile should pass (rc=$full_rc): $full_out"
grep -q "p/python" "$ARGS" || fail "full Semgrep argv omitted p/python: $(cat "$ARGS")"
grep -q "p/secrets" "$ARGS" || fail "full Semgrep argv omitted p/secrets: $(cat "$ARGS")"
pass "full Semgrep keeps p/python p/secrets"

echo "OK: $PASS assertions"
