#!/usr/bin/env bash
# After a successful local PR gate: push, open/reuse PR, subscribe, emit remediation handoff.
# Invoked by `make pr` (any capitalization). Skip open: OPEN_PR=0. Skip remediate: PR_REMEDIATE=0.
# PUSH_ONLY=1: still run L4 + push (make pr checkers already ran); do not open a PR.
# Do not run a separate gate-only pass before `make pr`.
set -euo pipefail

WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"
BASE_REF="${PR_BASE#origin/}"
PR_REMEDIATE="${PR_REMEDIATE:-0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
GOV_ROOT="${GOV_ROOT:-}"
if [[ -z "$GOV_ROOT" ]]; then
  GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
if is_l9_isolate_workspace "$WS"; then
  bind_isolate_toolchain "$WS" "$HOME/.cursor-governance"
fi

cd "$WS"

# Same reason as run_pr_gate.sh: l4_local.py and friends need the project
# interpreter (3.11+). Under the system 3.9 the L4 check dies on an import and
# is read as "release not authorized", blocking a PR that is in fact cleared.
if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
  export PATH="$GOV_ROOT/.venv/bin:$PATH"
fi

# Never-lose restore + soft dirty WARN (WIP/reports/.l9 scratch do not force cleanup).
_scratch_hold_cli="$GOV_ROOT/ops/scripts/scratch_hold.py"
_scratch_hold_restore() {
  if [[ -f "$_scratch_hold_cli" ]]; then
    python3 "$_scratch_hold_cli" --workspace "$WS" restore --all || true
  fi
}
_scratch_hold_status() {
  if [[ -f "$_scratch_hold_cli" ]]; then
    python3 "$_scratch_hold_cli" --workspace "$WS" status
  fi
}
_meaningful_dirty() {
  # Paths that should still WARN — exclude sacred/scratch prefixes.
  git status --porcelain | while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    path="${line:3}"
    path="${path#\"}"
    path="${path%\"}"
    case "$path" in
      WIP|WIP/*|reports/*|current_work/*|C_GOV_FILES/*|.l9/*|.l9) ;;
      *) printf '%s\n' "$line" ;;
    esac
  done
}

_scratch_hold_restore

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

# Pre-publication base refresh (L9 Multi-Agent Main-Bound Execution Contract
# §11 / invariant E5). The branch must be evaluated against the CURRENT
# origin/main, not against the SHA the task started from — other agents merge
# while this one works. Fetch failure means the collision state cannot be
# determined, which denies publication (§14 / E6) without touching local work.
echo "--- refresh base ($PR_BASE) ---"
if ! git fetch origin "$BASE_REF"; then
  echo "FAIL: cannot fetch origin/$BASE_REF — current-main collision state is"
  echo "      undeterminable, so publication is denied. Local work is unaffected."
  exit 1
fi

if ! git rev-parse --verify "$PR_BASE" >/dev/null 2>&1; then
  echo "FAIL: missing base ref $PR_BASE (fetch or set PR_BASE)"
  exit 1
fi

# Main-bound execution gate (E2/E3/E4): ancestry, no direct main push, PR
# targets main unless an exception is explicitly authorized.
_MAIN_BOUND_GATE="$GOV_ROOT/ops/scripts/main_bound_check.py"
if [[ -f "$_MAIN_BOUND_GATE" ]]; then
  echo "--- main-bound execution gate ---"
  if ! python3 "$_MAIN_BOUND_GATE" --workspace "$WS" --base "$PR_BASE"; then
    echo "FAIL: main-bound execution gate blocked publication"
    exit 1
  fi
fi

ahead="$(git rev-list --count "${PR_BASE}..HEAD" 2>/dev/null || echo 0)"
if [[ "${ahead:-0}" -eq 0 ]]; then
  echo "FAIL: no commits on '$branch' ahead of $PR_BASE — commit your work first, then re-run make pr"
  exit 1
fi

meaningful="$(_meaningful_dirty || true)"
if [[ -n "$meaningful" ]]; then
  echo "WARN: working tree has non-scratch dirty paths — PR will only include committed changes on '$branch'"
  printf '%s\n' "$meaningful"
elif [[ -n "$(git status --porcelain)" ]]; then
  echo "OK: dirty tree is only WIP/reports/.l9 scratch — no cleanup needed for make pr"
fi

# L4 local autonomy — no mid-execution push; require release receipt.
L4_CLI="${GOV_ROOT}/ops/autonomy/l4_local.py"
if [[ -f "$L4_CLI" && "${L9_L4_LOCAL_AUTONOMY:-1}" != "0" ]]; then
  echo "--- L4 local autonomy remote check ---"
  if ! python3 "$L4_CLI" --workspace "$WS" check-remote; then
    echo "FAIL: L4 blocks push/PR until kernels + authorize-release."
    echo "      pr-preflight should have caught this — drift if you reached here via make pr."
    echo "  1) make improve"
    echo "  2) Apply kernels/Recursive Alignment.md then kernels/Validate & Repair.md"
    echo "  3) make improve IMPROVE_RECORD=1"
    echo "  4) make pr-check && make pr"
    exit 1
  fi
fi

# PR overlap guardrail (PR_OVERLAP_GUARDRAIL_V1) — fail-closed pre-push check
# against already-open PRs, evaluated against the base just refreshed above.
# Absent on older governance tips (consumer repos): skip silently. Under
# autonomous publication an undeterminable collision state (gh/network loss)
# now DENIES rather than warning (§14 / E6); an interactive operator still gets
# the WARN. A detected non-generated textual conflict blocks. PR_STACK=auto
# re-resolves the base to the overlapping open PR's head (never main).
_OVERLAP_GATE="$GOV_ROOT/ops/scripts/pr_overlap_check.py"
if [[ -f "$_OVERLAP_GATE" ]]; then
  echo "--- PR overlap gate (PR_OVERLAP=${PR_OVERLAP:-block}) ---"
  if ! _overlap_out="$(python3 "$_OVERLAP_GATE" --workspace "$WS" --base "$PR_BASE" 2>&1)"; then
    printf '%s\n' "$_overlap_out"
    echo "FAIL: PR overlap gate blocked push (PR_OVERLAP=${PR_OVERLAP:-block})"
    exit 1
  fi
  printf '%s\n' "$_overlap_out"
  _stack_base="$(printf '%s\n' "$_overlap_out" | sed -n 's/^STACK_BASE=//p' | tail -1)"
  if [[ -n "$_stack_base" ]]; then
    PR_BASE="origin/$_stack_base"
    BASE_REF="$_stack_base"
    echo "NOTE: stacked base re-resolved to open PR head (PR_STACK=auto): $PR_BASE"
  fi
fi

echo "--- open PR (branch=$branch base=$BASE_REF; $ahead commit(s) ahead) ---"
git push -u origin HEAD

if [[ "${PUSH_ONLY:-0}" == "1" ]]; then
  echo "PUSH_ONLY=1 — pushed '$branch'; skipped GitHub PR open"
  exit 0
fi

# `gh pr view/create/repo view --json` go through GitHub's GraphQL endpoint,
# which some environments do not serve (restricted proxies, REST-scoped tokens).
# `make pr` is the ONLY sanctioned publish path, so it must not depend on an
# endpoint that can be switched off — every GraphQL call below keeps a REST
# fallback via `gh api repos/...`. GraphQL stays primary so behaviour is
# unchanged wherever it works.
# `|| true` between a failing gh call and a decision hides WHY the call failed
# (INV-7). The audited surface answers every GraphQL query with HTTP 403 — a
# fixed property of the session gateway, not a transient error — and the old
# form turned that into a silently empty variable. Classify it once, name it,
# and let the REST fallback take over deliberately rather than by accident.
# shellcheck source=lib/gh_graphql.sh
source "$GOV_ROOT/ops/scripts/lib/gh_graphql.sh"

resolve_repo_slug() {
  local slug url
  slug="$(gh_graphql repo view --json nameWithOwner -q .nameWithOwner || true)"
  if [[ -n "$slug" ]]; then
    printf '%s' "$slug"
    return 0
  fi
  url="$(git remote get-url origin 2>/dev/null || true)"
  url="${url%.git}"
  case "$url" in
    git@*:*) printf '%s' "${url#*:}" ;;
    http://*|https://*) printf '%s' "$url" | sed -E 's#^https?://[^/]+/##' ;;
    *) printf '' ;;
  esac
}

# Read a field out of a GitHub REST pull-request payload on stdin. `[]` (no
# open PR for this head) yields an empty string rather than an error.
_pr_field() {
  python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)
if isinstance(data, list):
    data = data[0] if data else {}
value = data.get(sys.argv[1], "") if isinstance(data, dict) else ""
print(value if value is not None else "")
' "$1" 2>/dev/null || true
}

repo="$(resolve_repo_slug)"
owner="${repo%/*}"
name="${repo#*/}"

pr_url="$(gh_graphql pr view --json url -q .url || true)"
pr_number="$(gh_graphql pr view --json number -q .number || true)"

if [[ -z "$pr_url" && -n "$owner" && -n "$name" ]]; then
  _existing="$(gh api "repos/${owner}/${name}/pulls?head=${owner}:${branch}&state=open" 2>/dev/null || true)"
  pr_url="$(printf '%s' "$_existing" | _pr_field html_url)"
  pr_number="$(printf '%s' "$_existing" | _pr_field number)"
fi

# The head-branch lookup above can surface a PR that already landed: once a
# PR is MERGED (or CLOSED) it can never carry new branch commits, so treating
# it as "already open" strands the work on the branch. Re-check the resolved
# PR state over REST (this gateway may refuse GraphQL). A merged PR means the
# branch name is spent (AGENTS.md §17: a branch name is never reused after its
# PR merges — reused_after_merge), so fail with move-to-a-new-branch
# instructions; only a closed-but-unmerged PR falls through to fresh creation.
if [[ -n "$pr_url" && -n "$pr_number" && -n "$owner" && -n "$name" ]]; then
  # REST returns the state lowercase ("open"/"closed") — match case-insensitively
  # so an actually-open PR is kept. merged_at distinguishes merged from closed.
  pr_state_row="$(gh api "repos/${owner}/${name}/pulls/${pr_number}" \
    --jq '[.state, (.merged_at // "")] | @tsv' 2>/dev/null || true)"
  pr_state="${pr_state_row%%$'\t'*}"
  pr_merged_at="${pr_state_row#*$'\t'}"
  case "$pr_state" in
    open | OPEN) ;; # genuinely open — keep it
    *)
      if [[ -n "$pr_state" && -n "$pr_merged_at" ]]; then
        echo "FAIL: PR #${pr_number} for branch ${branch} is MERGED — a branch name is never reused after its PR merges (reused_after_merge)." >&2
        echo "Move the new commits to a fresh branch and publish from there:" >&2
        echo "  git checkout -b ${branch}-followup && PR_REMEDIATE=0 make pr" >&2
        exit 1
      elif [[ -n "$pr_state" ]]; then
        echo "NOTE: PR #${pr_number} for this branch is ${pr_state} (closed, not merged) — opening a new PR"
        pr_url=""
        pr_number=""
      fi
      ;;
  esac
fi

if [[ -z "$pr_url" || -z "$pr_number" ]]; then
  title="$(git log "${PR_BASE}..HEAD" --format='%s' --reverse | head -1)"
  if [[ -z "$title" ]]; then
    title="$branch"
  fi
  campaign_copy=""
  campaign_body=""
  _campaign_copy_py="$GOV_ROOT/environment/program-execution/scripts/campaign_pr_copy.py"
  if [[ -f "$_campaign_copy_py" ]]; then
    campaign_copy="$(
      python3 "$_campaign_copy_py" \
        --pr-base "$PR_BASE" \
        --branch "$branch" \
        ${CAMPAIGN_ID:+--campaign-id "$CAMPAIGN_ID"} \
        --activate \
        --json 2>/dev/null || true
    )"
    if [[ -n "$campaign_copy" ]]; then
      campaign_title="$(printf '%s' "$campaign_copy" | python3 -c 'import json,sys; print(json.load(sys.stdin)["title"])' 2>/dev/null || true)"
      campaign_body="$(printf '%s' "$campaign_copy" | python3 -c 'import json,sys; print(json.load(sys.stdin)["body"])' 2>/dev/null || true)"
      if [[ -n "$campaign_title" ]]; then
        title="$campaign_title"
      fi
    fi
  fi
  template_file=""
  _root_protect_py="$GOV_ROOT/ops/scripts/validate_root_file_protection.py"
  _gov_python="${GOV_ROOT}/.venv/bin/python"
  [[ -x "$_gov_python" ]] || _gov_python="python3"
  _touched_additive=""
  if [[ -f "$_root_protect_py" ]]; then
    _touched_additive="$(
      "$_gov_python" "$_root_protect_py" \
        --list-touched-additive-only --base "$PR_BASE" --head HEAD --repo "$WS" \
        2>/dev/null || true
    )"
  fi
  if [[ -n "$_touched_additive" ]]; then
    for candidate in \
      "$WS/.github/PULL_REQUEST_TEMPLATE/protected-root.md" \
      "$GOV_ROOT/.github/PULL_REQUEST_TEMPLATE/protected-root.md"; do
      if [[ -f "$candidate" ]]; then
        template_file="$candidate"
        break
      fi
    done
    if [[ -z "$template_file" ]]; then
      echo "ERROR: PR touches additive_only root files but .github/PULL_REQUEST_TEMPLATE/protected-root.md is missing" >&2
      printf '%s\n' "$_touched_additive" >&2
      exit 1
    fi
    echo "NOTE: additive_only root files in this PR — using protected-root template:"
    printf '%s\n' "$_touched_additive"
  fi
  if [[ -z "$template_file" ]]; then
    for candidate in \
      "$WS/PULL_REQUEST_TEMPLATE.md" \
      "$WS/.github/PULL_REQUEST_TEMPLATE.md" \
      "$GOV_ROOT/PULL_REQUEST_TEMPLATE.md"; do
      if [[ -f "$candidate" ]]; then
        template_file="$candidate"
        break
      fi
    done
  fi
  compose_py="$SCRIPT_DIR/compose_pr_body.py"
  if [[ -x "$GOV_ROOT/.venv/bin/python" ]]; then
    compose_python="$GOV_ROOT/.venv/bin/python"
  else
    compose_python="python3"
  fi
  mkdir -p "$WS/.l9/pr"
  compose_handoff="$WS/.l9/pr/pr-body-completion.json"
  compose_args=(--workspace "$WS" --pr-base "$PR_BASE" --handoff "$compose_handoff")
  if [[ -n "$template_file" ]]; then
    compose_args+=(--template "$template_file")
  fi
  if [[ -n "${campaign_body:-}" ]]; then
    printf '%s\n' "$campaign_body" > "$WS/.l9/pr/campaign-body.md"
    compose_args+=(--campaign-body-file "$WS/.l9/pr/campaign-body.md")
  fi
  body="$("$compose_python" "$compose_py" "${compose_args[@]}")"
  # Prove the body satisfies the protected-root contract BEFORE the PR exists.
  # The stamp check is CI-enforced (`--require-pr-body` / GITHUB_ACTIONS), so a
  # body missing it used to be discovered only after the PR was open — a red
  # check on a PR that had to be edited or republished. Checking the body we
  # are about to send costs nothing and keeps the failure local.
  if [[ -n "$_touched_additive" && -f "$_root_protect_py" ]]; then
    printf '%s' "$body" > "$WS/.l9/pr/pr-body.md"
    if ! "$_gov_python" "$_root_protect_py" \
        --base "$PR_BASE" --head HEAD --repo "$WS" \
        --pr-body-file "$WS/.l9/pr/pr-body.md" --require-pr-body; then
      echo "FAIL: composed PR body does not satisfy the protected-root contract" >&2
      echo "      body draft: $WS/.l9/pr/pr-body.md" >&2
      echo "      nothing was opened; fix the body or the template, then re-run make pr" >&2
      exit 1
    fi
  fi
  # Explicit --head: gh otherwise aborts with "must first push the current
  # branch" in worktree/CI contexts where upstream tracking is not visible
  # (2026-08-15 factory repair).
  head_branch="$(git rev-parse --abbrev-ref HEAD)"
  if pr_url="$(gh pr create --head "$head_branch" --base "$BASE_REF" \
      --title "$title" --body "$body" 2>/dev/null)" && [[ -n "$pr_url" ]]; then
    pr_number="$(gh_graphql pr view --json number -q .number || true)"
    if [[ -z "$pr_number" && -n "$owner" && -n "$name" ]]; then
      pr_number="$(gh api "repos/${owner}/${name}/pulls?head=${owner}:${head_branch}&state=open" \
        2>/dev/null | _pr_field number)"
    fi
  else
    # GraphQL unavailable — open the PR over REST instead of failing the gate.
    if [[ -z "$owner" || -z "$name" ]]; then
      echo "ERROR: cannot resolve owner/repo to open a PR over REST" >&2
      exit 1
    fi
    echo "NOTE: gh pr create unavailable; opening via REST repos/${owner}/${name}/pulls"
    _created="$(gh api -X POST "repos/${owner}/${name}/pulls" \
      -f title="$title" -f head="$head_branch" -f base="$BASE_REF" -f body="$body" \
      2>/dev/null || true)"
    pr_url="$(printf '%s' "$_created" | _pr_field html_url)"
    pr_number="$(printf '%s' "$_created" | _pr_field number)"
    if [[ -z "$pr_url" ]]; then
      echo "ERROR: PR creation failed over both GraphQL and REST" >&2
      exit 1
    fi
  fi
  echo "Opened: $pr_url"
  if [[ -f "${compose_handoff:-}" ]]; then
    "$compose_python" - "$compose_handoff" "${pr_number:-0}" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
doc = json.loads(path.read_text(encoding="utf-8"))
number = int(sys.argv[2] or 0)
doc["pr_number"] = number or None
path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
needs = doc.get("needs_completion") or []
if needs:
    print("PR body requires completion: " + "; ".join(needs))
print(f"Handoff: {path}")
PY
  fi
else
  echo "PR already open: $pr_url"
  # The protected-root contract is proven when the PR is CREATED, from the diff
  # as it stood then. A later push can add an additive_only root file to a PR
  # whose body was composed from the default template, and nothing re-checks it
  # -- the Root-file append-only gate then fails on a body no one was told to
  # update. Re-check here and name the remedy, rather than letting CI discover it.
  #
  # A warning, not a failure: the body of an open PR may be human-authored, and
  # refusing to push someone's work over a template stamp would be worse than
  # the red check this prevents.
  _reopen_protect_py="$GOV_ROOT/ops/scripts/validate_root_file_protection.py"
  _reopen_python="${GOV_ROOT}/.venv/bin/python"
  [[ -x "$_reopen_python" ]] || _reopen_python="python3"
  if [[ -f "$_reopen_protect_py" && -n "${owner:-}" && -n "${name:-}" ]]; then
    _reopen_touched="$(
      "$_reopen_python" "$_reopen_protect_py" \
        --list-touched-additive-only --base "$PR_BASE" --head HEAD --repo "$WS" \
        2>/dev/null || true
    )"
    if [[ -n "$_reopen_touched" ]]; then
      _reopen_body="$(gh api "repos/${owner}/${name}/pulls/${pr_number}" --jq .body 2>/dev/null || true)"
      if [[ "$_reopen_body" != *"<!-- L9_PROTECTED_ROOT_PR -->"* ]]; then
        echo "WARN: this PR now touches additive_only root file(s):"
        printf '  %s\n' $_reopen_touched
        echo "      but its body predates them and lacks <!-- L9_PROTECTED_ROOT_PR -->."
        echo "      The Root-file append-only gate WILL fail until the body uses"
        echo "      .github/PULL_REQUEST_TEMPLATE/protected-root.md."
        echo "      A rewrite (not append-only) additionally needs a commit line:"
        echo "        ALLOW-ROOT-DELETION: <path> — <reason>"
      fi
    fi
  fi
fi

# owner/name already resolved above via resolve_repo_slug (GraphQL, then remote).
if [[ -z "$owner" || -z "$name" ]]; then
  echo "WARN: could not resolve owner/repo — skipping PR subscription"
  exit 0
fi

# Neither GraphQL nor REST produced a PR number. Continuing would build
# `repos/o/n/issues//subscription` and report a warning that reads like a minor
# notification problem, when in fact the publish path never established what it
# opened (INV-7).
if [[ -z "$pr_number" ]]; then
  echo "ERROR: PR number unresolved after GraphQL and REST" >&2
  if [[ "$GH_GRAPHQL_UNSUPPORTED" == "1" ]]; then
    echo "ERROR:   classification=$GH_GRAPHQL_CLASSIFICATION (gateway refuses GitHub GraphQL)" >&2
    echo "ERROR:   the REST fallback also failed — this is not a GraphQL-only outage" >&2
  fi
  echo "ERROR:   PR URL was: ${pr_url:-<none>}" >&2
  exit 1
fi

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
  # GOV_ROOT is absolutized at the top of this file. Re-deriving the root from a
  # relative BASH_SOURCE broke whenever the caller invoked this script by a
  # relative path from another working directory -- every `make -C "$GOV" pr
  # WS=<consumer>` run -- so the cd failed and this receipt was silently lost to
  # the `|| true`.
  root="$GOV_ROOT"
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

_scratch_hold_restore
if ! _scratch_hold_status; then
  echo "FAIL: open scratch hold(s) after open-pr — restore before finishing"
  exit 1
fi
