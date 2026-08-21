#!/usr/bin/env bash
# gh auth is reported by capability, not by sentinel inspection.
#
# Covers audit finding B-20 and acceptance test T-15.
#
# The audited surface exports GH_TOKEN=proxy-injected. `gh auth status` calls
# that token invalid; `gh api user` returns the real account. The setup log
# believed the former and announced "gh unauthenticated" on a session where
# every REST call worked. The stubs below reproduce exactly that split.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="$(cd "$SCRIPT_DIR/.." && pwd)/lib/gh_auth_probe.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-gh-auth.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$TMP_ROOT/bin"
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

make_gh() { # $1=api rc  $2=auth-status rc
  cat > "$TMP_ROOT/bin/gh" <<STUB
#!/usr/bin/env bash
case "\$1 \$2" in
  "api user") exit $1 ;;
  "auth status") exit $2 ;;
esac
exit 1
STUB
  chmod +x "$TMP_ROOT/bin/gh"
}

probe() { ( PATH="$TMP_ROOT/bin:$PATH"; source "$LIB"; gh_auth_probe ); }

# T1 — the audited shape: REST works, auth status lies.
make_gh 0 1
out="$(probe)" || fail "probe returned non-zero while gh api user succeeds"
grep -q "authenticated via platform proxy" <<<"$out" \
  || fail "did not report proxy authentication; got: $out"
pass "REST success outranks a failing gh auth status"

# T2 — a surface where auth status is the working signal.
make_gh 1 0
out="$(probe)" || fail "probe returned non-zero while gh auth status succeeds"
grep -q "authenticated (gh auth status)" <<<"$out" || fail "fallback branch not taken"
pass "gh auth status is honoured when REST is unavailable"

# T3 — genuinely unauthenticated is still reported as such.
make_gh 1 1
set +e; out="$(probe)"; rc=$?; set -e
[ "$rc" -ne 0 ] || fail "unauthenticated gh must return non-zero"
grep -q "NOTE: gh unauthenticated" <<<"$out" || fail "did not report unauthenticated"
pass "a genuinely unauthenticated gh is reported"

# T4 — gh absent is distinct from gh unauthenticated.
# An empty PATH, not a trimmed one: gh lives in /usr/bin on this image, so
# "/usr/bin:/bin" would still find it and the case would silently not run.
mkdir -p "$TMP_ROOT/empty"
set +e
out="$(PATH="$TMP_ROOT/empty"; source "$LIB"; gh_auth_probe)"; rc=$?
set -e
[ "$rc" -ne 0 ] || fail "absent gh must return non-zero"
grep -q "NOT INSTALLED" <<<"$out" || fail "absent gh not distinguished from unauthenticated"
pass "absent gh is distinguished from unauthenticated gh"

# T5 — setup.sh no longer decides from gh auth status alone.
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SETUP="$REPO/environment/agents/adapters/claude-code/web/setup.sh"
grep -q 'gh_auth_probe' "$SETUP" || fail "setup.sh must use the shared probe"
if grep -q 'gh auth status 2>/dev/null || echo' "$SETUP"; then
  fail "setup.sh still carries the false-negative probe"
fi
pass "setup.sh uses the capability probe"

echo "OK: $PASS assertions"
