#!/usr/bin/env bash
# Canonical mutating-agent task start (L9 Multi-Agent Main-Bound Execution
# Contract §2, §3; invariants E1, E2).
#
# One mutating agent = one dedicated wired worktree. Default base is
# PR_STACK=auto: unique open-PR chain tip when one exists, else origin/main.
# It fetches that base, pins the SHA, creates a unique agent branch, a wired
# worktree, and the task metadata the publication gate later verifies.
#
# Usage:
#   bash ops/scripts/agent_worktree_start.sh --agent-id claude --task-id T1
#   bash ops/scripts/agent_worktree_start.sh --agent-id claude --task-id T1 \
#        --worktree /path/to/wt --json
#
# Default base follows PR_STACK (same as make pr): unset or auto resolves the
# unique open-PR chain tip. Empty PR_STACK= keeps origin/main. An explicit
# --base is never rewritten. Other non-main --base still needs:
#   L9_TASK_BASE_AUTHORIZED="<reason>" ... --base origin/campaign/foo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

agent_id=""
task_id=""
base_ref="origin/main"
base_explicit=0
resolved_tip_sha=""
worktree=""
emit_json=0

die() { echo "FAIL: $*" >&2; exit 1; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent-id) agent_id="${2:-}"; shift 2 ;;
    --task-id)  task_id="${2:-}";  shift 2 ;;
    --base)     base_ref="${2:-}"; base_explicit=1; shift 2 ;;
    --worktree) worktree="${2:-}"; shift 2 ;;
    --json)     emit_json=1; shift ;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$agent_id" ] || die "--agent-id is required (agent identity is task metadata, §3)"
[ -n "$task_id" ]  || die "--task-id is required (task identity is task metadata, §3)"

# Branch/worktree names are path components: keep them boring.
for value in "$agent_id" "$task_id"; do
  case "$value" in
    *[!A-Za-z0-9._-]*) die "identifiers must match [A-Za-z0-9._-]+ (got: $value)" ;;
  esac
done

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git work tree"
cd "$repo_root"

_resolve_auto_stack_tip() {
  local resolver="${L9_STACK_TIP_RESOLVER:-$SCRIPT_DIR/resolve_stack_tip.py}"
  local out rc tip sha reason
  set +e
  out="$(python3 "$resolver" --workspace "$repo_root" 2>&1)"
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    printf '%s\n' "$out" >&2
    die "PR_STACK=auto could not resolve a unique stack tip (exit ${rc})"
  fi
  tip="$(printf '%s\n' "$out" | sed -n 's/^STACK_TIP=//p' | head -n 1)"
  sha="$(printf '%s\n' "$out" | sed -n 's/^STACK_TIP_SHA=//p' | head -n 1)"
  reason="$(printf '%s\n' "$out" | sed -n 's/^REASON=//p' | head -n 1)"
  [ -n "$tip" ] || die "stack-tip resolver returned no STACK_TIP"
  case "$tip" in
    origin/main|main) base_ref="origin/main" ;;
    origin/*) base_ref="$tip" ;;
    *) base_ref="origin/${tip}" ;;
  esac
  resolved_tip_sha="$sha"
  if [ "$base_ref" != "origin/main" ] && [ -z "${L9_TASK_BASE_AUTHORIZED:-}" ]; then
    export L9_TASK_BASE_AUTHORIZED="resolver stack tip (PR_STACK=auto reason=${reason:-unique_chain_tip})"
  fi
  echo "NOTE: PR_STACK=auto resolved stack tip ${base_ref} (reason=${reason:-unknown})"
}

# Default --base is origin/main. Unset PR_STACK and PR_STACK=auto replace that
# default with the unique chain tip (Makefile default). An explicit --base is
# never rewritten. Empty PR_STACK= keeps origin/main even when a unique open-PR
# chain exists.
if [ "$base_explicit" -eq 0 ] && [ "${PR_STACK-auto}" = "auto" ]; then
  _resolve_auto_stack_tip
fi

# §2: after auto-stack resolution, ancestry is the resolved base (stack tip or
# origin/main). Authorization is an intent question, so settle it BEFORE the
# fetch — otherwise an unauthorized --base fails with a fetch error that hides
# the real reason.
if [ "$base_ref" != "origin/main" ]; then
  if [ -z "${L9_TASK_BASE_AUTHORIZED:-}" ]; then
    die "base '$base_ref' is not origin/main. Ordinary agent tasks MUST branch from
      fetched origin/main (§2). A stacked or campaign workflow is an explicit
      exception: re-run with L9_TASK_BASE_AUTHORIZED=\"<reason>\"."
  fi
  echo "NOTE: non-main ancestry authorized: ${L9_TASK_BASE_AUTHORIZED}"
fi

# A stale local ref is not canonical ancestry: fetch, then pin the exact SHA.
remote_ref="${base_ref#origin/}"
echo "--- fetch origin $remote_ref ---"
git fetch origin "$remote_ref" || die "cannot fetch origin/$remote_ref (ancestry unverifiable)"

base_sha="$(git rev-parse "$base_ref")" || die "cannot resolve $base_ref"
if [ -n "$resolved_tip_sha" ] && [ "$base_sha" != "$resolved_tip_sha" ]; then
  die "resolved tip SHA ${resolved_tip_sha} does not match ${base_ref} (${base_sha})"
fi

branch="agent/${agent_id}/${task_id}"
if git show-ref --verify --quiet "refs/heads/${branch}"; then
  die "branch already exists: $branch (one branch per agent task; pick a new --task-id)"
fi

if [ -z "$worktree" ]; then
  worktree="${L9_AGENT_WORKTREE_HOME:-$HOME/.l9/gov-worktrees}/${agent_id}__${task_id}"
fi
[ ! -e "$worktree" ] || die "worktree path already exists: $worktree"

mkdir -p "$(dirname "$worktree")"

# Wired add (never raw `git worktree add`: the new tree needs its gitignored
# .cursor links — rule 49 — and a real .venv when the repo is a uv project).
echo "--- create wired worktree ($branch @ ${base_sha:0:12}) ---"
bash "$SCRIPT_DIR/worktree_add_wired.sh" -b "$branch" "$worktree" "$base_sha"

# §3: record task metadata. The publication gate reads this to prove ancestry.
meta_dir="${repo_root}/.l9/agent-tasks"
mkdir -p "$meta_dir"
meta_path="${meta_dir}/${agent_id}__${task_id}.json"

AGENT_ID="$agent_id" TASK_ID="$task_id" BRANCH="$branch" WORKTREE="$worktree" \
BASE_REF="$base_ref" BASE_SHA="$base_sha" META_PATH="$meta_path" \
python3 - <<'PY'
import json
import os
import time

doc = {
    "schema": "l9.agent_task.v1",
    "agent_id": os.environ["AGENT_ID"],
    "task_id": os.environ["TASK_ID"],
    "branch": os.environ["BRANCH"],
    "worktree": os.environ["WORKTREE"],
    "base_ref": os.environ["BASE_REF"],
    "base_sha": os.environ["BASE_SHA"],
    "base_authorization": os.environ.get("L9_TASK_BASE_AUTHORIZED", ""),
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
path = os.environ["META_PATH"]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(f"task metadata: {path}")
PY

# Also drop a copy inside the worktree so an agent that only ever sees its own
# tree can still find its own task record.
mkdir -p "${worktree}/.l9/agent-tasks"
cp "$meta_path" "${worktree}/.l9/agent-tasks/$(basename "$meta_path")"

if [ "$emit_json" = "1" ]; then
  cat "$meta_path"
else
  cat <<SUMMARY

RESULT: PASS — agent task started
  agent_id : $agent_id
  task_id  : $task_id
  branch   : $branch
  worktree : $worktree
  base     : $base_ref @ $base_sha

Next: cd "$worktree" && work only there. Publish with 'make pr' (never a raw push).
  venv     : $worktree/.venv  (uv projects only; materialized by worktree_add_wired.sh)
SUMMARY
fi
