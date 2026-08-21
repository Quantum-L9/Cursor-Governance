#!/usr/bin/env bash
# A GraphQL 403 is classified, not swallowed (INV-7).
#
# Covers audit finding B-12 and acceptance test T-13.
#
# The audited session gateway answers every GitHub GraphQL query with HTTP 403
# while serving REST normally. The publish path wrote `... 2>/dev/null || true`
# around those calls, so a hard refusal and "no PR is open" produced the same
# empty string. Every case here drives a STUB gh that reproduces the real 403
# text, because the failure only exists on a surface we cannot ask CI to have.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="$SCRIPTS_DIR/lib/gh_graphql.sh"
PR_GATE="$SCRIPTS_DIR/open_pr_after_gate.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-gh-graphql.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

mkdir -p "$TMP_ROOT/bin"

# The verbatim shape the audited gateway returns.
cat > "$TMP_ROOT/bin/gh" <<'STUB'
#!/usr/bin/env bash
case "$1" in
  pr|repo)
    echo "HTTP 403: This GraphQL query (PullRequestList, sent by gh pr list) is not enabled for this session — only the pinned set of PR-review operations is served. Use REST via \`gh api repos/{owner}/{repo}/...\` instead. (https://api.github.com/graphql)" >&2
    exit 1
    ;;
  api) echo '[{"number":42,"html_url":"https://github.com/o/n/pull/42"}]' ;;
  *) exit 1 ;;
esac
STUB
chmod +x "$TMP_ROOT/bin/gh"

# A gh that is simply unauthenticated — a DIFFERENT failure that must not be
# misclassified as a GraphQL refusal.
cat > "$TMP_ROOT/bin/gh-unauth" <<'STUB'
#!/usr/bin/env bash
echo "gh: To get started with GitHub CLI, please run: gh auth login" >&2
exit 4
STUB
chmod +x "$TMP_ROOT/bin/gh-unauth"

# T1 — a GraphQL 403 sets the flag and names the classification.
out="$(
  PATH="$TMP_ROOT/bin:$PATH"
  # shellcheck source=../lib/gh_graphql.sh
  source "$LIB"
  gh_graphql pr view --json url -q .url >/dev/null 2>"$TMP_ROOT/err" || true
  echo "flag=$GH_GRAPHQL_UNSUPPORTED"
)"
grep -q 'flag=1' <<<"$out" || fail "GraphQL 403 did not set GH_GRAPHQL_UNSUPPORTED"
grep -q 'SURFACE_UNSUPPORTED_GRAPHQL' "$TMP_ROOT/err" \
  || fail "classification string not emitted"
pass "GraphQL 403 is classified as SURFACE_UNSUPPORTED_GRAPHQL"

# T2 — the note is emitted once, not once per call.
count="$(
  PATH="$TMP_ROOT/bin:$PATH"
  source "$LIB"
  { gh_graphql pr view --json url || true
    gh_graphql pr view --json number || true
    gh_graphql repo view --json nameWithOwner || true
  } >/dev/null 2>"$TMP_ROOT/err2"
  grep -c 'SURFACE_UNSUPPORTED_GRAPHQL' "$TMP_ROOT/err2"
)"
[ "$count" = "1" ] || fail "classification noted $count times, expected once"
pass "classification is noted once per process, not per call"

# T3 — an unrelated gh failure is NOT misclassified.
out="$(
  PATH="$TMP_ROOT/bin:$PATH"
  source "$LIB"
  gh() { "$TMP_ROOT/bin/gh-unauth" "$@"; }
  gh_graphql pr view --json url >/dev/null 2>/dev/null || true
  echo "flag=$GH_GRAPHQL_UNSUPPORTED"
)"
grep -q 'flag=0' <<<"$out" || fail "an auth failure was misclassified as a GraphQL refusal"
pass "non-GraphQL failures are not misclassified"

# T4 — gh's exit code reaches the caller instead of being erased by `|| true`.
set +e
(
  PATH="$TMP_ROOT/bin:$PATH"
  source "$LIB"
  gh_graphql pr view --json url >/dev/null 2>/dev/null
)
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "gh_graphql must propagate a non-zero exit code"
pass "failing exit code propagates to the caller"

# T5 — the publish path exits non-zero when the PR number never resolves,
#      rather than warning about a subscription it could not make.
grep -q 'ERROR: PR number unresolved after GraphQL and REST' "$PR_GATE" \
  || fail "open_pr_after_gate.sh must fail when pr_number is unresolved"
grep -q 'GH_GRAPHQL_CLASSIFICATION' "$PR_GATE" \
  || fail "open_pr_after_gate.sh must report the classification"
pass "publish path fails loudly on an unresolved PR number"

# T6 — no bare `|| true` remains between a GraphQL call and a decision.
if grep -nE 'gh (pr|repo) [a-z].*\|\| true' "$PR_GATE" | grep -v gh_graphql; then
  fail "a raw gh GraphQL call still ends in '|| true'"
fi
pass "no unclassified GraphQL call remains on the publish path"

echo "OK: $PASS assertions"
