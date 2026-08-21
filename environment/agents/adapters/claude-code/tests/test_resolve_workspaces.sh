#!/usr/bin/env bash
# Workspace resolution handles N repositories, and failing to wire is fatal.
#
# Covers audit findings B-02, B-21 and acceptance tests T-16, T-17, T-18.
#
# The audited sandbox held five sibling repositories under a non-repository
# parent (/home/user), plus a sixth (.github) that the old `./*/` glob could not
# even see. resolve_workspace() accepted exactly one repo and returned failure
# otherwise, so the entire adapter went unwired while setup.sh still exited 0.
#
# resolve_workspaces() is exercised by extracting it from the real setup.sh
# rather than by re-implementing it here — a copy would test the copy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SETUP="$ADAPTER_DIR/web/setup.sh"
BOOTSTRAP_STUB="$ADAPTER_DIR/web/setup.bootstrap.sh"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/l9-resolve-ws.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
pass() { PASS=$((PASS + 1)); echo "PASS T$PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

# Extract the real function body so this test cannot drift from the shipped one.
FUNC_FILE="$TMP_ROOT/resolve.sh"
awk '/^resolve_workspaces\(\) \{/,/^\}/' "$SETUP" > "$FUNC_FILE"
[ -s "$FUNC_FILE" ] || fail "could not extract resolve_workspaces() from setup.sh"

make_repo() { mkdir -p "$1" && git init -q "$1"; }

resolve_in() { # $1=cwd -> prints resolved paths, one per line
  ( cd "$1" && unset CLAUDE_PROJECT_DIR && source "$FUNC_FILE" && resolve_workspaces )
}

# T1 — zero repositories: resolution fails.
zero="$TMP_ROOT/zero"
mkdir -p "$zero/notarepo"
set +e
out="$(resolve_in "$zero")"
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "zero repositories must fail resolution (got: $out)"
pass "zero repositories returns failure"

# T2 — exactly one repository: unchanged behaviour (regression guard).
one="$TMP_ROOT/one"
make_repo "$one/only"
out="$(resolve_in "$one")"
[ "$(wc -l <<<"$out")" -eq 1 ] || fail "one repo should resolve to one path, got: $out"
grep -q "/only$" <<<"$out" || fail "resolved the wrong path: $out"
pass "single repository resolves exactly as before"

# T3 — the audited shape: five siblings plus a dotfile repo under a non-repo parent.
many="$TMP_ROOT/many"
mkdir -p "$many"
for r in Cursor-Governance LLM-Router SEO-Bot Website-Bot l9-graphiti-memory .github; do
  make_repo "$many/$r"
done
mkdir -p "$many/not-a-repo"
out="$(resolve_in "$many")"
count="$(wc -l <<<"$out")"
[ "$count" -eq 6 ] || fail "expected 6 repositories, resolved $count: $out"
for r in Cursor-Governance LLM-Router SEO-Bot Website-Bot l9-graphiti-memory .github; do
  grep -q "/$r$" <<<"$out" || fail "$r missing from resolution"
done
grep -q "not-a-repo" <<<"$out" && fail "a non-repository was resolved"
pass "six repositories including .github all resolve"

# T4 — the dotfile repository specifically (the old ./*/ glob could not see it).
dotonly="$TMP_ROOT/dotonly"
make_repo "$dotonly/.github"
out="$(resolve_in "$dotonly")"
grep -q "/.github$" <<<"$out" || fail ".github repository not resolved"
pass "a dotfile-named repository is visible to the resolver"

# T5 — CLAUDE_PROJECT_DIR still wins when it names a repository.
proj="$TMP_ROOT/proj"
make_repo "$proj/chosen"
make_repo "$proj/other"
out="$( cd "$proj" && CLAUDE_PROJECT_DIR="$proj/chosen" bash -c "source '$FUNC_FILE'; resolve_workspaces" )"
[ "$(wc -l <<<"$out")" -eq 1 ] || fail "CLAUDE_PROJECT_DIR must win outright"
grep -q "/chosen$" <<<"$out" || fail "CLAUDE_PROJECT_DIR not honoured"
pass "CLAUDE_PROJECT_DIR takes precedence"

# T6 — cwd inside a repository resolves to its toplevel.
inside="$TMP_ROOT/inside"
make_repo "$inside/repo"
mkdir -p "$inside/repo/deep/nested"
out="$(resolve_in "$inside/repo/deep/nested")"
[ "$(wc -l <<<"$out")" -eq 1 ] || fail "inside a repo must resolve to one toplevel"
pass "cwd inside a repository resolves to its toplevel"

# T7 — an unwirable environment is FATAL, not a warning followed by exit 0.
grep -q 'adapter NOT wired in ANY workspace' "$SETUP" \
  || fail "setup.sh must fail when nothing could be wired"
grep -q 'ERROR: no git repository at or under' "$SETUP" \
  || fail "setup.sh must report the no-repository case as an error"
if grep -q 'WARN: no git workspace resolvable' "$SETUP"; then
  fail "setup.sh still downgrades an unwirable environment to a warning"
fi
pass "unwirable environment is reported as an error"

# T8 — the stub propagates the failure instead of printing 'complete'.
grep -q 'SETUP_RC=\$?' "$BOOTSTRAP_STUB" || fail "stub must capture setup.sh's exit code"
grep -q 'exit "\$SETUP_RC"' "$BOOTSTRAP_STUB" || fail "stub must propagate a failing exit code"
pass "bootstrap stub propagates a failed environment build"

echo "OK: $PASS assertions"
