#!/usr/bin/env bash
# Claude Code SessionStart capability preflight.
#
# Purpose: remove capability-plane ambiguity before an agent starts work.
# This hook does not grant platform permissions and does not mutate GitHub.
# It identifies the already-selected primary checkout and emits the exact
# transport/ownership doctrine the agent must follow.
#
# L9 ownership boundaries:
# - filesystem governance SSOT: $HOME/.cursor-governance
# - durable memory: l9-graphite-memory -> MemoryService
# - interactive memory write: memory.phase_lock -> memory.write_governed
# - PR convergence: make pr -> l9-pr-remediation, not Send Later
# - GitHub publication: make pr only
# - Claude hosted GitHub transport: repository-scoped REST, never a known-bad GraphQL probe
set -uo pipefail

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
GOV="$HOME/.cursor-governance"
LINES=()
LINES+=("L9 Claude bootstrap remediation mode: ENABLED")
LINES+=("governance SSOT: $GOV")
LINES+=("Do not invoke Register Repo Root to create or attach a second governance clone; use $GOV locally.")
LINES+=("Durable agent memory: canonical l9-graphite-memory control plane terminating at MemoryService.")
LINES+=("Interactive durable write: memory.phase_lock then memory.write_governed. The memory phase lock governs memory-write consistency only; it is not repository-write authority.")
LINES+=("Do not invoke retired graphiti-memory provider tools, provider aliases, or generic memory.ingest as an autonomous-write bypass.")
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
  LINES+=("primary workspace GitHub repository: $repo_slug")
  LINES+=("Repository scope: PRIMARY_CHECKOUT. Do not invoke Add Repo for this repository at SessionStart; the selected checkout is the initial task scope.")
  LINES+=("If execution later requires a genuinely different repository and the hosted platform reports that exact repository unavailable, request scope once for only that newly required repository; never clone around the platform boundary.")
else
  LINES+=("primary workspace GitHub repository: UNKNOWN from local origin; do not invent repository scope or invoke Add Repo speculatively.")
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
