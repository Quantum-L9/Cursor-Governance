#!/usr/bin/env bash
# After a successful local PR gate: push, open/reuse PR, subscribe, emit remediation handoff.
# Invoked by `make pr` (any capitalization). Skip open: OPEN_PR=0. Skip remediate: PR_REMEDIATE=0.
# Gate-only: `make pr-check`.
set -euo pipefail

WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"
BASE_REF="${PR_BASE#origin/}"
PR_REMEDIATE="${PR_REMEDIATE:-1}"
GOV_ROOT="${GOV_ROOT:-}"
if [[ -z "$GOV_ROOT" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

cd "$WS"

if ! command -v gh >/dev/null 2>&1; then
  echo "FAIL: gh CLI required to open a PR (https://cli.github.com/)"
  exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" == "HEAD" ]]; then
  echo "FAIL: detached HEAD — check out a branch before opening a PR"
  exit 1
fi
if [[ "$branch" == "main" || "$branch" == "master" ]]; then
  echo "FAIL: on '$branch' — create/checkout a feature branch, commit, then re-run make pr"
  exit 1
fi

if ! git rev-parse --verify "$PR_BASE" >/dev/null 2>&1; then
  echo "FAIL: missing base ref $PR_BASE (fetch or set PR_BASE)"
  exit 1
fi

ahead="$(git rev-list --count "${PR_BASE}..HEAD" 2>/dev/null || echo 0)"
if [[ "${ahead:-0}" -eq 0 ]]; then
  echo "FAIL: no commits on '$branch' ahead of $PR_BASE — commit your work first, then re-run make pr"
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "WARN: working tree is dirty — PR will only include committed changes on '$branch'"
  git status --short
fi

echo "--- open PR (branch=$branch base=$BASE_REF; $ahead commit(s) ahead) ---"
git push -u origin HEAD

pr_url="$(gh pr view --json url -q .url 2>/dev/null || true)"
pr_number="$(gh pr view --json number -q .number 2>/dev/null || true)"

if [[ -z "$pr_url" || -z "$pr_number" ]]; then
  title="$(git log "${PR_BASE}..HEAD" --format='%s' --reverse | head -1)"
  if [[ -z "$title" ]]; then
    title="$branch"
  fi
  body="$(
    cat <<EOF
## Summary
$(git log "${PR_BASE}..HEAD" --format='- %s' --reverse)

## Test plan
- [x] \`make pr-check\` (local changed-files gate) PASS before open
- [ ] CI green; agent PR remediation subscribed after open
EOF
  )"
  pr_url="$(gh pr create --base "$BASE_REF" --title "$title" --body "$body")"
  pr_number="$(gh pr view --json number -q .number)"
  echo "Opened: $pr_url"
else
  echo "PR already open: $pr_url"
fi

repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
owner="${repo%/*}"
name="${repo#*/}"

echo "--- subscribe (GitHub notifications for PR #$pr_number) ---"
if gh api -X PUT "repos/${owner}/${name}/issues/${pr_number}/subscription" \
  -f subscribed=true -f ignored=false >/dev/null; then
  echo "Subscribed to PR #$pr_number ($repo)"
else
  echo "WARN: could not subscribe to PR #$pr_number (continuing)"
fi

handoff_dir="$WS/.l9/pr"
mkdir -p "$handoff_dir"

# Patch C: typed PRRemediationAssignment via runtime_paths (authoritative); .l9/pr remains pointer/handoff.
l9_emit_pr_assignment() {
  local root py aid
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  if [ -x "$root/.venv/bin/python3" ]; then py="$root/.venv/bin/python3"; else py="$(command -v python3)"; fi
  aid="pr-${pr_number:-0}-${packet_id:-local}"
  ( cd "$root" && ASSIGNMENT_ID="$aid" PR_NUMBER="${pr_number:-0}" BRANCH="${head_branch:-}" PACKET_ID="${packet_id:-local}"       "$py" -c "import os,sys; sys.path.insert(0,'.'); from environment.agents.lifecycle import receipts; receipts.write_pr_remediation_assignment({'assignment_id':os.environ['ASSIGNMENT_ID'],'pr_number':int(os.environ.get('PR_NUMBER') or 0),'branch':os.environ.get('BRANCH',''),'packet_id':os.environ.get('PACKET_ID',''),'max_cycles':3})" ) || true
}


handoff_path="$handoff_dir/pr-remediation-handoff.json"
packet_id="make-pr-${pr_number}-$(date -u +%Y%m%dT%H%M%SZ)"
created_by="${USER:-agent}"

python3 - "$handoff_path" <<PY
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = {
    "schema": "l9.pr_remediation_handoff.v1",
    "packet_id": "${packet_id}",
    "authority": "A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE",
    "profile": "pr-convergence",
    "autonomous_merge": False,
    "skill": "l9-pr-remediation",
    "max_cycles": 3,
    "pr_number": int("${pr_number}"),
    "pr_url": "${pr_url}",
    "branch": "${branch}",
    "repo": "${repo}",
    "base": "${BASE_REF}",
    "workspace": "${WS}",
    "governance_root": "${GOV_ROOT}",
    "created_by": "${created_by}",
    "agent_action": "spawn_background_poll_remediate",
    "prompt_template": "skills/l9-bounded-autonomy/references/prompt-templates.md#poll_worker",
}
path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(f"Handoff written: {path}")
PY
l9_emit_pr_assignment || true

if [[ "$PR_REMEDIATE" == "1" ]]; then
  cat <<EOF

=== L9_AGENT_REQUIRED ===
ACTION: spawn_background_task
SKILL: l9-pr-remediation (+ babysit / poll_worker)
PR: ${pr_number}
URL: ${pr_url}
BRANCH: ${branch}
REPO: ${repo}
HANDOFF: ${handoff_path}
PACKET_ID: ${packet_id}
INSTRUCTIONS:
  1. Read skills/l9-pr-remediation/SKILL.md and skills/l9-bounded-autonomy/references/pr-poll-subagent.md
  2. Spawn Task(run_in_background=true, subagent_type=generalPurpose, description="PR #${pr_number} poll/remediate")
     using poll_worker template with packet fields from the handoff JSON
  3. Main agent MUST continue (do not AwaitShell / block on CI for this PR)
  4. Cap 3 fix-push cycles; never merge; never force-push
=== END L9_AGENT_REQUIRED ===

EOF
  echo "RESULT: PASS — PR open + subscribed; agent must spawn l9-pr-remediation"
else
  echo "PR_REMEDIATE=0 — skipped remediation handoff marker (PR still open/subscribed)"
  echo "RESULT: PASS — PR open + subscribed"
fi
