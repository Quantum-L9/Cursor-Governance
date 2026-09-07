#!/usr/bin/env bash
# Claude Code SessionStart capability preflight.
#
# Purpose: remove capability-plane ambiguity before an agent starts work.
# This hook does not grant platform permissions and does not mutate GitHub. It
# emits the exact transport/ownership doctrine the agent must follow, plus a
# read-only repository-scope probe when the workspace is a GitHub checkout.
#
# L9 ownership boundaries:
# - filesystem governance SSOT: $HOME/.cursor-governance
# - durable memory: L9 Graphiti memory plane, not Claude's Add Memory helper
# - PR convergence: make pr -> l9-pr-remediation, not Send Later
# - GitHub publication: make pr only
# - Claude hosted GitHub transport: repository-scoped REST, never a GraphQL probe
set -uo pipefail

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
GOV="$HOME/.cursor-governance"
LINES=()
LINES+=("L9 Claude bootstrap remediation mode: ENABLED")
LINES+=("governance SSOT: $GOV")
LINES+=("Do not invoke Register Repo Root to create or attach a second governance clone; use $GOV locally.")
LINES+=("Do not invoke Add Memory; durable memory is owned by the L9 Graphiti memory plane and its writeback hooks.")
LINES+=("Do not invoke Send Later for PR watching; make pr handoff + l9-pr-remediation own convergence/polling.")
LINES+=("Do not publish with raw git push, gh pr create, MCP create_pull_request, or push_files; publication is make pr only.")

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  LINES+=("GitHub transport: REST_ONLY. Never probe gh pr view/list/checks/create/merge or gh repo view; use gh api --method GET for read-only GitHub inspection.")
fi

repo_slug=""
if git -C "$WORKSPACE" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  remote="$(git -C "$WORKSPACE" remote get-url origin 2>/dev/null || true)"
  case "$remote" in
    git@github.com:*) repo_slug="${remote#git@github.com:}" ;;
    ssh://git@github.com/*) repo_slug="${remote#ssh://git@github.com/}" ;;
    https://github.com/*) repo_slug="${remote#https://github.com/}" ;;
    http://github.com/*) repo_slug="${remote#http://github.com/}" ;;
  esac
  repo_slug="${repo_slug%.git}"
fi

if [ -n "$repo_slug" ]; then
  LINES+=("workspace GitHub repository: $repo_slug")
  # The probe is deliberately GET-only. A scope failure is evidence that the
  # platform session has not enabled this repository, not a reason to retry a
  # different GitHub command or to clone another copy.
  if command -v gh >/dev/null 2>&1; then
    err="$(mktemp "${TMPDIR:-/tmp}/l9-repo-scope.XXXXXX")"
    if gh api --method GET "repos/$repo_slug" --jq .full_name >/dev/null 2>"$err"; then
      LINES+=("GitHub repository scope: AVAILABLE for $repo_slug.")
    elif grep -qiE 'not enabled for this session|use add_repo|repository access.*not enabled' "$err"; then
      LINES+=("GitHub repository scope: REQUIRED for $repo_slug. Before the first GitHub write, invoke Add Repo once with access=push for exactly $repo_slug. Add Repo is a platform session capability; do not use it to create a second clone.")
    else
      LINES+=("GitHub repository scope: UNKNOWN for $repo_slug. Do not guess. First GitHub inspection must be repository-scoped REST GET; classify its exact failure.")
    fi
    rm -f "$err"
  else
    LINES+=("GitHub repository scope: UNKNOWN because gh is unavailable.")
  fi
else
  LINES+=("workspace GitHub repository: UNKNOWN from local origin; do not invent repository scope.")
fi

# Claude SessionStart hook output. Escape through Python only if available;
# otherwise use a small shell escaper so bootstrap remains stdlib/runtime-free.
ctx="$(printf '%s\n' "${LINES[@]}")"
if command -v python3 >/dev/null 2>&1; then
  CTX="$ctx" python3 - <<'PY'
import json, os
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": os.environ["CTX"]}}))
PY
else
  ctx=${ctx//\\/\\\\}
  ctx=${ctx//\"/\\\"}
  ctx=${ctx//$'\n'/\\n}
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
fi

exit 0
