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

# T6 — CG-10: one verdict per transport. The split that hid an unreadable PR
# template: REST user works, the org template read is refused, GraphQL 403s.
cat > "$TMP_ROOT/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$*" in
  "api user") exit 0 ;;
  "api repos/Quantum-L9/.github/contents/.github/pull_request_template.md") exit 1 ;;
  "api graphql -f query={viewer{login}}") exit 1 ;;
esac
exit 1
STUB
chmod +x "$TMP_ROOT/bin/gh"
cat > "$TMP_ROOT/bin/curl" <<'STUB'
#!/usr/bin/env bash
header="$(cat)"
case "$header" in "Authorization: Bearer proxy-injected") printf '200' ;; *) printf '401' ;; esac
STUB
chmod +x "$TMP_ROOT/bin/curl"
caps="$(PATH="$TMP_ROOT/bin:$PATH" GH_TOKEN=proxy-injected bash -c "source '$LIB'; gh_capability_probe Quantum-L9")"
for want in rest_user=OK org_template_read=DENIED graphql=DENIED direct_api=OK; do
  grep -qx "$want" <<<"$caps" || fail "expected $want; got: $caps"
done
pass "each GitHub transport gets its own verdict"

# T7 — what cannot be asked is UNKNOWN, never OK: no owner, no token, no gh.
caps="$(PATH="$TMP_ROOT/empty" GH_TOKEN="" GITHUB_TOKEN="" /bin/bash -c "source '$LIB'; gh_capability_probe")"
for want in rest_user=UNKNOWN org_template_read=UNKNOWN graphql=UNKNOWN direct_api=UNKNOWN; do
  grep -qx "$want" <<<"$caps" || fail "expected $want; got: $caps"
done
pass "an unaskable capability is UNKNOWN, not OK"

# T8 — the token never reaches curl's argv.
grep -q 'H @-' "$LIB" || fail "direct_api must pass its header on stdin"
if grep -Eq 'curl[^|]*Bearer' "$LIB"; then
  fail "the bearer token is on a curl command line"
fi
pass "the direct API probe keeps the token out of argv"

echo "OK: $PASS assertions"
