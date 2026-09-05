#!/usr/bin/env bash
# Option B: session excludes hide injected mirrors without a tracked .gitignore
# and without a blanket .claude/ (Option A).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib/session_git_excludes.sh
source "$HERE/../lib/session_git_excludes.sh"

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export GIT_CONFIG_GLOBAL="$tmp/gitconfig"
export GIT_CONFIG_SYSTEM=/dev/null
git config --global user.email t@t
git config --global user.name t
ws="$tmp/consumer"
mkdir -p "$ws"
git -C "$ws" init -q

apply_session_git_excludes "$ws"
exclude="$(session_exclude_file "$ws")"
body="$(cat "$exclude")"

for glob in $(session_shared_exclude_globs) $(session_claude_mirror_exclude_globs); do
  grep -qxF "$glob" "$exclude" || fail "missing $glob in $exclude"
done
if grep -qxF '.claude/' "$exclude"; then fail "blanket .claude/ must not be written"; fi
if grep -qxF '/.claude/' "$exclude"; then fail "blanket /.claude/ must not be written"; fi
if grep -qxF '.claude' "$exclude"; then fail "blanket .claude must not be written"; fi

session_append_exclude_globs "$exclude" ".claude/"
if grep -qxF '.claude/' "$exclude"; then fail "helper accepted blanket .claude/"; fi

mkdir -p "$ws/.claude/skills" "$ws/.claude/rules"
printf '{}\n' >"$ws/.mcp.json"
printf 'local\n' >"$ws/.claude/settings.local.json"
for path in .claude/skills .claude/rules .claude/commands .mcp.json .claude/settings.local.json; do
  git -C "$ws" check-ignore -q "$path" || fail "git does not honour $path"
done

# Tracked .mcp.json stays visible — exclude does not hide repo content.
printf '{"tracked":true}\n' >"$ws/.mcp.json"
git -C "$ws" add -f .mcp.json
git -C "$ws" commit -qm 'track mcp'
git -C "$ws" check-ignore -q .mcp.json && fail "tracked .mcp.json must not be hidden by exclude"
status="$(git -C "$ws" status --porcelain -- .mcp.json)"
[ -z "$status" ] || fail "clean tracked .mcp.json should be empty porcelain, got: $status"

# Linked worktree reads $GIT_COMMON_DIR/info/exclude.
git -C "$ws" commit -q --allow-empty -m base
linked="$tmp/linked"
git -C "$ws" worktree add -q -b wt "$linked"
apply_session_git_excludes "$linked"
git -C "$linked" check-ignore -q .claude/skills || fail "linked worktree does not honour .claude/skills"

# Machine list is never-owned only. .mcp.json stays session-local so
# `git add .mcp.json` still works for Web/Mobile adoption.
gi="$tmp/gitignore_global"
printf '%s\n' 'memory-bank/' '.mcp.json' '.claude/skills' >"$gi"
apply_machine_session_excludes "$gi" || fail "apply_machine_session_excludes on a writable file"
grep -qxF 'memory-bank/' "$gi" || fail "machine excludes dropped memory-bank/"
grep -qxF '.claude/settings.local.json' "$gi" || fail "machine excludes missing settings.local.json"
if grep -qxF '.mcp.json' "$gi"; then fail "machine excludes must not contain .mcp.json"; fi
if grep -qxF '.claude/skills' "$gi"; then fail "machine excludes must not contain .claude/skills"; fi
if grep -qxF '.claude/' "$gi"; then fail "machine excludes wrote blanket .claude/"; fi

blocked="$tmp/not-a-dir"
printf 'x\n' >"$blocked"
apply_machine_session_excludes "$blocked/gitignore" && fail "unwritable machine excludes must fail"

pass "session_git_excludes Option B (no Option A blanket)"
