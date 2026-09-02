#!/usr/bin/env bash
# GraphQL updateSubscription is the subscribe path; PUT issues/subscription is not.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="$SCRIPTS_DIR/lib/gh_subscribe_pr.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-gh-subscribe.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

mkdir -p "$TMP_ROOT/bin"

# gh --jq is applied by real gh. The stub prints JSON; the helper passes --jq
# to gh. Reproduce jq locally when the stub sees --jq.
cat > "$TMP_ROOT/bin/gh" <<'STUB'
#!/usr/bin/env bash
jq_expr=""
args=("$@")
i=0
while [ "$i" -lt "$#" ]; do
  if [ "${args[$i]}" = "--jq" ]; then
    jq_expr="${args[$((i + 1))]}"
  fi
  i=$((i + 1))
done
if [[ "$1" == "api" && "$2" == "repos/o/n/pulls/81" ]]; then
  raw='{"node_id":"PR_kwDOtest"}'
  if [ -n "$jq_expr" ]; then
    python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d['node_id'])" "$raw"
  else
    printf '%s' "$raw"
  fi
  exit 0
fi
if [[ "$1" == "api" && "$2" == "graphql" ]]; then
  raw='{"data":{"updateSubscription":{"subscribable":{"number":81,"viewerSubscription":"SUBSCRIBED"}}}}'
  if [ -n "$jq_expr" ]; then
    python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d['data']['updateSubscription']['subscribable']['viewerSubscription'])" "$raw"
  else
    printf '%s' "$raw"
  fi
  exit 0
fi
exit 1
STUB
chmod +x "$TMP_ROOT/bin/gh"

out="$(
  PATH="$TMP_ROOT/bin:$PATH"
  # shellcheck source=../lib/gh_subscribe_pr.sh
  source "$LIB"
  gh_subscribe_pr o n 81
)"
grep -q 'Subscribed to PR #81 (o/n)' <<<"$out" || fail "success path did not print Subscribed: $out"
pass "updateSubscription SUBSCRIBED is reported"

# GraphQL 403 is classified skip, not a fake issues/subscription 404.
cat > "$TMP_ROOT/bin/gh-gql403" <<'STUB'
#!/usr/bin/env bash
if [[ "$1" == "api" && "$2" == "repos/o/n/pulls/81" ]]; then
  echo "PR_kwDOtest"
  exit 0
fi
echo "HTTP 403: This GraphQL query is not enabled for this session" >&2
exit 1
STUB
chmod +x "$TMP_ROOT/bin/gh-gql403"

out="$(
  PATH="$TMP_ROOT/bin:$PATH"
  source "$LIB"
  gh() { "$TMP_ROOT/bin/gh-gql403" "$@"; }
  GH_GRAPHQL_UNSUPPORTED=0
  GH_GRAPHQL_NOTED=0
  gh_subscribe_pr o n 81
  echo "rc=$?"
) 2>&1"
grep -q 'SURFACE_UNSUPPORTED_GRAPHQL\|skip subscribe' <<<"$out" \
  || fail "GraphQL 403 was not classified: $out"
grep -q 'rc=0' <<<"$out" || fail "classified GraphQL refusal must exit 0"
pass "GraphQL 403 skip-subscribes instead of PUT 404"

if grep -qE 'gh api -X PUT' "$LIB"; then
  fail "helper still contains PUT issues/subscription"
fi
pass "helper does not call PUT issues/subscription"

echo "OK: $PASS assertions"
