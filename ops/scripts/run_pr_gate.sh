#!/usr/bin/env bash
# Changed-files local PR gate. Full-tree = nightly CI / make pr-full / make precommit.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WS:-$(pwd)}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"
PR_SECURITY_ADVISORY="${PR_SECURITY_ADVISORY:-0}"
PR_MYPY_STRICT="${PR_MYPY_STRICT:-0}"

cd "$WS"
export WS PR_BASE PR_SECURITY_ADVISORY

_GATE_RECEIPT="$WS/.l9/pr/gate-receipt.json"
_GATE_FAILURE="$WS/.l9/pr/gate-failure.json"
_GATE_LOG="$WS/.l9/pr/last-gate.log"
_GATE_FAILURE_PY="$SCRIPT_DIR/pr_gate_failure.py"
_gate_failed=0
# Key the receipt on tree CONTENT, not on history.
#
# The old digest was HEAD + `git status --porcelain`. Both change when you
# stage and commit, while the bytes the gate just validated do not — so the
# one sequence every operator actually runs (pr-check -> add -> commit -> pr)
# was guaranteed to miss its own cache and re-run the full suite, twice.
# Hashing the worktree instead is invariant across `git add` and `git commit`
# and changes the moment a file's content does. Costs ~0.7s over ~3.7k files
# against the ~5.5 minutes it saves.
_gate_state_digest() {
  local list paths content
  list="$(mktemp)"
  {
    git ls-files -z
    git ls-files --others --exclude-standard -z
  } >"$list" 2>/dev/null || true
  # Paths and contents are digested separately: a rename that preserves both
  # content and sort position would otherwise slip through as unchanged.
  paths="$(cksum <"$list" | awk '{print $1}')"
  content="$(xargs -0 -r git hash-object <"$list" 2>/dev/null | cksum | awk '{print $1}')"
  rm -f "$list"
  printf '%s %s %s' "$paths" "$content" "$PR_BASE"
}
_gate_receipt_matches() {
  [[ -f "$_GATE_RECEIPT" ]] || return 1
  python3 - "$_GATE_RECEIPT" "$(_gate_state_digest)" <<'PY'
import json, sys
path, current = sys.argv[1], sys.argv[2]
try:
    doc = json.loads(open(path, encoding="utf-8").read())
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
want = f"{doc.get('paths_digest', '')} {doc.get('content_digest', '')} {doc.get('pr_base', '')}"
raise SystemExit(0 if want == current else 1)
PY
}

# PASS skip first. A matching FAIL receipt then refuses a second full gate
# (STOP LOOPING) so agents cannot wait through the same red tree again.
if _gate_receipt_matches; then
  echo "OK: gate receipt matches unchanged state — skipping full validation"
  echo "RESULT: PASS — local PR gate clean (receipt reuse)"
  exit 0
fi
if [[ -f "$_GATE_FAILURE_PY" ]]; then
  _gate_refuse_rc=0
  python3 "$_GATE_FAILURE_PY" refuse "$_GATE_FAILURE" "$(_gate_state_digest)" || _gate_refuse_rc=$?
  if [[ "$_gate_refuse_rc" -eq 2 ]]; then
    exit 2
  fi
fi

# Isolates are not a uv project. Bind PATH/UV_PROJECT to the donor or
# $HOME/.cursor-governance locked venv before any uv run/sync.
_isolate_venv_existed=0
if is_l9_isolate_workspace "$WS"; then
  [[ -d "$WS/.venv" ]] && _isolate_venv_existed=1
  bind_isolate_toolchain "$WS" "$HOME/.cursor-governance"
fi

# The governance generators and validators target the locked project interpreter
# (3.12+, `from datetime import UTC`). A bare `python3` can be Homebrew/system
# and lack yaml/pydantic/jsonschema. Fail closed — never fall through.
bash "$GOV_ROOT/ops/scripts/ensure_gov_python.sh" "$GOV_ROOT"
export PATH="$GOV_ROOT/.venv/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$GOV_ROOT/.venv"
export UV_LOCKED=1

# Never-lose: restore open/legacy holds around the gate; fail closed if still open.
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

_scratch_hold_restore

# Repo-write lock held for the whole gate. pre-commit blames "files were
# modified by this hook" on whichever hook was running when the tree changed
# (pre_commit/commands/run.py _run_single_hook), so backgrounded reconcilers
# must not write during the run. Advisory: a missed lock warns, never blocks.
# shellcheck source=lib/repo_write_lock.sh
. "$GOV_ROOT/ops/scripts/lib/repo_write_lock.sh"
export L9_REPO_WRITE_LOCK_LABEL="make-pr-gate"
if repo_write_lock_acquire "$WS" "${PR_LOCK_WAIT_S:-30}"; then
  echo "repo-write lock: held for this gate run"
else
  echo "WARN: $(repo_write_lock_skip_note "$WS") — continuing; concurrent writes may be misattributed"
fi
_gate_failed=1
_gate_on_exit() {
  if [[ "${_gate_failed:-0}" = "1" && -f "$_GATE_FAILURE_PY" ]]; then
    mkdir -p "$WS/.l9/pr"
    python3 "$_GATE_FAILURE_PY" write "$_GATE_FAILURE" "$(_gate_state_digest)" \
      --log "$_GATE_LOG" \
      --precommit "${precommit_log:-}" \
      --pytest "$GOV_ROOT/.venv/bin/pytest" || true
  fi
  rm -f "${status_before:-}" "${changed_file:-}" "${precommit_log:-}" "${py_list:-}"
  repo_write_lock_release
}
trap '_gate_on_exit' EXIT

# P2-12 corpus scans on every make pr are retired. Markdown-only mutations
# no longer pay full-tree residue/pin/contract-surface scans on the velocity
# path. Corpus ownership is make pr-full / make precommit. Do not restore a
# changed-file-independent validator block — that is the velocity contract,
# not a missing check. Domain-gated validators run after resolve (below).

echo "=== make pr (changed files vs ${PR_BASE}; full-tree = make pr-full / nightly) ==="

status_before="$(mktemp)"
changed_file="$(mktemp)"
precommit_log="$(mktemp)"
py_list="$(mktemp)"
mkdir -p "$WS/.l9/pr"
: >"$_GATE_LOG"
trap '_gate_on_exit' EXIT
git status --porcelain >"$status_before"

_gate_write_receipt() {
  _gate_failed=0
  rm -f "$_GATE_FAILURE"
  mkdir -p "$WS/.l9/pr"
  python3 - "$_GATE_RECEIPT" "$(_gate_state_digest)" <<'PY'
import json, sys
from datetime import datetime, timezone

path = sys.argv[1]
paths, content, pr_base = sys.argv[2].split(" ", 2)
doc = {
    "schema": "l9.pr_gate_receipt.v2",
    "paths_digest": paths,
    "content_digest": content,
    "pr_base": pr_base,
    "passed_at": datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z"),
}
open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=2) + "\n")
print(f"gate receipt written: {path}")
PY
}

# Two dirtiness domains, deliberately reported apart:
#   tracked   — git diff, exactly what pre-commit compares (run.py _get_diff)
#   worktree  — git status --porcelain, which also sees untracked files
_tracked_diff_digest() {
  # cksum, not shasum/sha1sum: POSIX and present on every runner. This only
  # needs to detect change, not resist collision attacks.
  git diff --no-ext-diff --no-textconv --ignore-submodules | cksum | awk '{print $1}'
}
tracked_before="$(_tracked_diff_digest)"

# shellcheck source=lib/precommit_log.sh
. "$GOV_ROOT/ops/scripts/lib/precommit_log.sh"

# Print "<hook-id> (exit <n>)" for every hook that genuinely returned non-zero.
# A hook that only tripped the modified-files check prints no exit-code line.
_precommit_failing_hooks() {
  precommit_failed_hooks "$1" | while read -r hook_id code; do
    printf '  %s (exit %s)\n' "$hook_id" "$code"
  done
}

# Compare the current worktree against $status_before. 0 = clean or only
# generated/scratch churn (WARN), 1 = non-generated dirt the caller must handle.
_gate_classify_dirtiness() {
  local phase="$1" after rc=0
  after="$(mktemp)"
  git status --porcelain >"$after"
  if diff -q "$status_before" "$after" >/dev/null; then
    rm -f "$after"
    return 0
  fi
  if bash "$SCRIPT_DIR/classify_generated_dirtiness.sh" "$WS" "$status_before" "$after"; then
    echo "WARN: generated/scratch artifacts changed during ${phase} — stage them with your commit:"
    git status --short
  else
    rc=1
  fi
  rm -f "$after"
  return "$rc"
}

_gate_run_precommit() {
  local rc=0
  set +e
  PR_CHANGED_FILE="$changed_file" bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS" 2>&1 | tee "$precommit_log"
  rc="${PIPESTATUS[0]}"
  set -e
  if [[ -f "$precommit_log" ]]; then
    cat "$precommit_log" >>"$_GATE_LOG" || true
  fi
  return "$rc"
}

# Resolve once, before pre-commit. Soft-empty: nothing to gate is PASS.
PR_ALLOW_EMPTY=1 PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
  >"$changed_file" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)
if [[ ! -s "$changed_file" ]]; then
  echo "OK: nothing to gate vs $PR_BASE (no committed or working-tree changes outside scratch)"
  _gate_write_receipt
  echo "RESULT: PASS — local PR gate clean (nothing to gate)"
  exit 0
fi

echo "=== governance validators (domain-gated) ==="
if grep -Eq '^\.github/workflows/|^ops/scripts/validate_workflow_action_pins\.py$' "$changed_file"; then
  python3 "$GOV_ROOT/ops/scripts/validate_workflow_action_pins.py"
else
  echo "OK: skip workflow pins (workflows unchanged)"
fi
if grep -Eq '^(ops/secrets/|environment/agents/)' "$changed_file"; then
  python3 "$GOV_ROOT/ops/secrets/validate_capability_contract.py"
else
  echo "OK: skip capability-contract (ops/secrets and environment/agents unchanged)"
fi
echo "OK: skip doctrine residue / contract surface / git-denial (make pr-full owns corpus)"

_gate_run_precommit && precommit_rc=0 || precommit_rc=$?

if [[ "${L9_GATE_STRICT_LEGACY:-0}" = "1" && "$precommit_rc" -ne 0 ]]; then
  echo "FAIL: pre-commit exited ${precommit_rc} (L9_GATE_STRICT_LEGACY=1 — no classification)"
  exit "$precommit_rc"
fi

# pre-commit returns non-zero for `files_modified or bool(retcode)` (run.py).
# Only a real hook exit code is a validator failure; a modified tree is
# dirtiness this gate can classify, attribute, and often heal.
if [[ "$precommit_rc" -ne 0 ]] && grep -q '^- exit code: ' "$precommit_log"; then
  echo "FAIL: pre-commit hook(s) failed:"
  _precommit_failing_hooks "$precommit_log"
  exit 1
fi

if [[ "$precommit_rc" -ne 0 ]]; then
  echo "NOTE: pre-commit exited ${precommit_rc} solely because the worktree changed during a hook."
  echo "      That names the hook's time window, not the writer — classifying below."
fi

if ! _gate_classify_dirtiness "pre-commit"; then
  if [[ -f "$SCRIPT_DIR/attribute_tree_writers.sh" ]]; then
    bash "$SCRIPT_DIR/attribute_tree_writers.sh" "$WS" "$status_before" "$precommit_log" || true
  fi

  if [[ "${PR_GATE_RETRY:-1}" = "1" ]]; then
    echo "--- quiescing and retrying pre-commit once ---"
    repo_write_lock_acquire "$WS" "${PR_LOCK_WAIT_S:-30}" \
      || echo "WARN: $(repo_write_lock_skip_note "$WS") — retrying anyway"
    git status --porcelain >"$status_before"
    tracked_before="$(_tracked_diff_digest)"
    _gate_run_precommit && precommit_rc=0 || precommit_rc=$?
    if [[ "$precommit_rc" -ne 0 ]] && grep -q '^- exit code: ' "$precommit_log"; then
      echo "FAIL: pre-commit hook(s) failed on retry:"
      _precommit_failing_hooks "$precommit_log"
      exit 1
    fi
  fi

  if ! _gate_classify_dirtiness "pre-commit retry"; then
    echo "FAIL: non-generated files changed during the gate and persisted through a retry."
    echo "      Review the attribution above; stage intended edits, or stop the writer, then re-run make pr."
    if [[ "$(_tracked_diff_digest)" != "$tracked_before" ]]; then
      echo "      tracked-file changes present (this is what pre-commit compares)"
    else
      echo "      untracked-only churn (never triggers pre-commit's modified-files check)"
    fi
    git status --short
    exit 1
  fi
fi

echo "--- uv lock ---"
if grep -Eq '^(uv\.lock|pyproject\.toml|requirements.*\.txt|constraints\.txt)$' "$changed_file"; then
  if [[ -f uv.lock ]]; then
    uv lock --check
  else
    echo "OK: no uv.lock present, skipping"
  fi
else
  echo "OK: skip uv-lock-check (dependency manifests unchanged)"
fi

echo "--- pytest ---"
if [[ "${PR_SKIP_PYTEST:-0}" == "1" ]]; then
  echo "OK: skip pytest (PR_SKIP_PYTEST=1)"
elif grep -Eq '\.py$' "$changed_file"; then
  # Local pr-check never passes repo-root '.' (SP-04 / SP-05). Full catalog
  # remains make test / make pr-full / CI via run_pytest_suites.sh.
  pytest_args=(--tb=short -q)
  if ! grep -Eq '^(tests/ops/secrets/|ops/secrets/)' "$changed_file"; then
    pytest_args+=(--ignore=tests/ops/secrets)
    echo "OK: skip secrets capability suite (ops/secrets unchanged)"
  fi
  _pytest_py="${GOV_TOOLCHAIN_ROOT:-$GOV_ROOT}/.venv/bin/python"
  if [[ ! -x "$_pytest_py" ]]; then
    _pytest_py="$(command -v python3)"
  fi
  if [[ ! -x "$_pytest_py" ]]; then
    echo "FAIL: no python interpreter for scoped pytest"
    exit 1
  fi
  # Selection above read $WS; execution must name the same tree. Publishing from
  # a second governance clone (rule 49 §7) runs this Makefile from $GOV while the
  # changed files and their tests live in $WS, so a test added in the workspace
  # collects as "no tests ran" and the gate fails exit 4 on work that is present
  # and passing. Measured 2026-08-27.
  #
  # `:=` rather than a fresh assignment: PR #323 declares _pytest_ws_kind above
  # the if/elif chain to skip this registry for consumer workspaces. Where that
  # has landed this reuses its value; where it has not, this computes it. Either
  # way there is one value and one declaration.
  #
  # Consumers keep $GOV as their root, byte for byte as before: they do not own
  # these suites.
  : "${_pytest_ws_kind:=$(classify_workspace_kind "$WS")}"
  _pytest_repo_root_args=()
  if [ "$_pytest_ws_kind" = "ssot" ] || [ "$_pytest_ws_kind" = "ssot_checkout" ]; then
    if [ "$(cd "$WS" && pwd -P)" != "$(cd "$GOV_ROOT" && pwd -P)" ]; then
      _pytest_repo_root_args=(--repo-root "$WS")
      echo "OK: pytest root -> workspace ($_pytest_ws_kind; governance clone, \$GOV differs)"
    fi
  fi
  "$_pytest_py" "$SCRIPT_DIR/run_python_test_suites.py" \
    --profile local \
    "${_pytest_repo_root_args[@]}" \
    --changed-file "$changed_file" \
    -- "${pytest_args[@]}"
else
  echo "OK: skip pytest (no changed Python files)"
fi

echo "--- sync-generated-artifacts ---"
python3 "$GOV_ROOT/ops/scripts/sync_generated_artifacts.py" \
  --root "$WS" \
  --changed-file "$changed_file" \
  --check
if ! _gate_classify_dirtiness "sync-generated-artifacts"; then
  if [[ -f "$SCRIPT_DIR/attribute_tree_writers.sh" ]]; then
    bash "$SCRIPT_DIR/attribute_tree_writers.sh" "$WS" "$status_before" || true
  fi
  echo "FAIL: unexpected non-generated dirtiness after sync"
  git status --short
  exit 1
fi

echo "--- root-file protection ---"
# Ran only in CI until now, which meant an additive_only violation on a root
# file (Makefile, AGENTS.md, ...) was undiscoverable until after the PR was
# already open — costing a fix commit and a second full publish cycle. It is a
# ~0.7s git-diff analysis; there was never a reason for it to be remote-only.
# The policy lives with the repo it protects, so the check applies exactly
# where that config exists — consumer workspaces have no root inventory to
# reconcile and must not be failed against the governance one.
_root_protect_py="$GOV_ROOT/ops/scripts/validate_root_file_protection.py"
if [[ -f "$_root_protect_py" && -f "$WS/ops/config/root-file-protection.json" ]]; then
  python3 "$_root_protect_py" --base "$PR_BASE" --head HEAD --repo "$WS"
else
  echo "OK: skip root-file protection (no ops/config/root-file-protection.json in this workspace)"
fi

echo "--- skill-activation ---"
if [[ -f "$WS/environment/agents/adapters/claude-code/validate_skill_activation.py" ]]; then
  if grep -Eq '^(skills/|ops/skill_routing/|ops/generated/skill-registry\.json|environment/agents/adapters/claude-code/)' "$changed_file"; then
    python3 "$WS/environment/agents/adapters/claude-code/validate_skill_activation.py"
  else
    echo "OK: skip skill-activation (skills/routing unchanged)"
  fi
fi

echo "--- local-activation ---"
is_local=0
if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" && -d "${HOME}/.cursor" && -w "${HOME}/.cursor" ]]; then
  is_local=1
fi
if [[ "$is_local" -eq 1 && -f "$WS/skills/AUTONOMY_MANIFEST.yaml" ]]; then
  if [[ -f "$GOV_ROOT/ops/scripts/project_llm_rules.py" ]]; then
    if ! python3 "$GOV_ROOT/ops/scripts/project_llm_rules.py" --root "$WS" --check --quiet; then
      echo "FAIL: llm-rules projection drift — re-run: python3 ops/scripts/project_llm_rules.py --root \"$WS\""
      python3 "$GOV_ROOT/ops/scripts/project_llm_rules.py" --root "$WS" --check
      exit 1
    fi
    echo "OK: llm-rules projection matches rules/*.mdc"
  fi
  # One projection entrypoint: apply skills/commands/rules, then verify clean.
  python3 "$GOV_ROOT/ops/scripts/claude_projection.py" \
    --root "$WS" --workspace "$WS" --domains skills,commands,rules,mcp \
    --quiet --no-receipt || true
  if ! python3 "$GOV_ROOT/ops/scripts/claude_projection.py" \
    --root "$WS" --workspace "$WS" --domains skills,commands,rules,mcp \
    --check --quiet --no-receipt; then
    echo "FAIL: Claude projection --check drifted — re-run: python3 ops/scripts/claude_projection.py --root \"$WS\" --workspace \"$WS\""
    python3 "$GOV_ROOT/ops/scripts/claude_projection.py" \
      --root "$WS" --workspace "$WS" --domains skills,commands,rules,mcp --check --summary --no-receipt
    exit 1
  fi
  echo "OK: Claude projection (skills, commands, rules) reconciled to SSOT"
  # check_governance_wiring.sh asserts Cursor DESKTOP activation (plugin symlink,
  # .cursor-commands, .cursor/plans, ~/.cursor/hooks.json). The enclosing guard uses
  # "~/.cursor exists and is writable" as a proxy for "this is a Cursor machine", but
  # Graphiti's own state dir (~/.cursor/graphiti-state) creates that path on EVERY
  # surface — so the proxy silently became true for headless adapters. Gate the
  # desktop-wiring assertion on the surface id instead. The reconcile checks above
  # stay unconditional: they are surface-independent and must keep running here.
  # Heal missing gitignored .cursor links under the existing make-pr lock.
  # Not sessionStart — reconcilers skip while this lock is held.
  if [[ -x "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh" ]]; then
    L9_WIRE_LINKS_ONLY=1 bash "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh" "$WS" \
      || echo "WARN: ensure_workspace_wired failed — wiring check will fail-closed"
  fi
  # PAIRED PREDICATE: run_pr_precommit.sh skips symlinks-check the same way.
  # Isolates skip consumer repo symlinks; machine sessionEnd/Graphiti still run.
  WS_KIND="$(classify_workspace_kind "$WS")"
  if [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
    # Apply the surface gate the comment above specifies. This branch used to run
    # the FULL check unconditionally, so a headless adapter on an identity
    # checkout asserted the Cursor DESKTOP hook plane (~/.cursor/hooks.json and
    # its sessionEnd/skill-router entries) — artifacts the cloud installer
    # deliberately never creates, making `make pr` unrunnable off Cursor. The
    # correct predicate already existed one branch below and already returns
    # "skip" for any surface != cursor; it was simply evaluated second.
    # Scope to --workspace rather than skipping wholesale: every
    # surface-independent check (SSOT freshness, merge drivers, slash-command
    # drift, symlink health) still runs. Only the --machine desktop assertions
    # are dropped, and only where policy already says they do not apply.
    wiring_args=("$WS")
    if ! is_cursor_host_surface; then
      wiring_args=(--workspace "$WS")
    fi
    if ! bash "$SCRIPT_DIR/check_governance_wiring.sh" "${wiring_args[@]}"; then
      echo "FAIL: governance wiring incomplete — see FAIL lines above"
      exit 1
    fi
    if [ "${#wiring_args[@]}" -eq 2 ]; then
      echo "OK: ssot-family workspace ($WS_KIND) — consumer links not required;" \
           "Cursor desktop wiring skipped by surface=${L9_GOVERNANCE_SURFACE}"
    else
      echo "OK: ssot-family workspace ($WS_KIND) — consumer links not required"
    fi
  elif should_skip_consumer_symlink_checks "$WS"; then
    if is_l9_isolate_workspace "$WS"; then
      if ! bash "$SCRIPT_DIR/check_governance_wiring.sh" --machine "$WS"; then
        echo "FAIL: check_governance_wiring.sh failed — see FAIL lines above"
        exit 1
      fi
      echo "OK: skip consumer workspace wiring (isolate under \$HOME/.l9)"
    else
      echo "OK: skip Cursor desktop wiring (CI, partial clone, or surface=${L9_GOVERNANCE_SURFACE:-unset})"
    fi
  else
    if ! bash "$SCRIPT_DIR/check_governance_wiring.sh" "$WS"; then
      echo "FAIL: governance wiring incomplete — see FAIL lines above"
      exit 1
    fi
  fi
else
  echo "OK: skip local-activation (CI or non-writable ~/.cursor)"
fi

echo "--- security ---"
# Gate mode: on the publish path a missing scanner binary is a failure, not
# a SKIP that reads as a pass (INV-5).
bash "$SCRIPT_DIR/run_pr_security.sh" --mode gate "$WS"

if [[ "$PR_MYPY_STRICT" = "1" ]]; then
  _mypy="$GOV_ROOT/.venv/bin/mypy"
  if [[ ! -x "$_mypy" && -n "${GOV_TOOLCHAIN_ROOT:-}" && -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/mypy" ]]; then
    _mypy="$GOV_TOOLCHAIN_ROOT/.venv/bin/mypy"
  fi
  if [[ ! -x "$_mypy" ]]; then
    echo "FAIL: locked mypy missing at $GOV_ROOT/.venv/bin/mypy (run: make venv)"
    exit 1
  fi
  "$_mypy" . --show-error-codes --pretty --ignore-missing-imports
else
  echo "mypy: advisory on PR gate (set PR_MYPY_STRICT=1 to fail; full check is make lint / nightly)"
fi

if is_l9_isolate_workspace "$WS" && [[ -d "$WS/.venv" && "$_isolate_venv_existed" -eq 0 ]]; then
  echo "FAIL: isolate must not create $WS/.venv; use ${GOV_TOOLCHAIN_ROOT:-$HOME/.cursor-governance}"
  exit 1
fi

_scratch_hold_restore
if ! _scratch_hold_status; then
  echo "FAIL: open scratch hold(s) after gate — restore before shipping"
  exit 1
fi

_gate_write_receipt
echo "RESULT: PASS — local PR gate clean (changed files only)"
