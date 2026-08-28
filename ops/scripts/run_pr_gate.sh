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
#
# The digest must also cover the GATE'S OWN code, which the worktree hash above
# cannot reach. When $WS is a linked worktree the gate executes from $GOV_ROOT —
# a different checkout — so editing run_pr_gate.sh changed nothing the receipt
# could see. A green or red verdict from the previous gate version was then
# reused against the new one, and the only way to validate a gate fix was to
# delete the receipt by hand. Folding these bytes into the content digest
# invalidates the receipt exactly when the verdict could differ.
_GATE_CODE_FILES=(
  "ops/scripts/run_pr_gate.sh"
  "ops/scripts/run_pr_precommit.sh"
  "ops/scripts/run_python_test_suites.py"
  "ops/scripts/pr_overlap_check.py"
  "ops/scripts/pr_gate_failure.py"
  "ops/config/python-contract.json"
  "ops/autonomy/kernel_gate.py"
  ".pre-commit-config.yaml"
)
_gate_code_digest() {
  local rel present=()
  for rel in "${_GATE_CODE_FILES[@]}"; do
    [[ -f "$GOV_ROOT/$rel" ]] && present+=("$GOV_ROOT/$rel")
  done
  if [[ ${#present[@]} -eq 0 ]]; then
    # No gate code readable: do not fabricate a stable digest, or a receipt
    # would survive a change this function failed to observe.
    printf 'unreadable-%s' "$RANDOM"
    return
  fi
  cat "${present[@]}" 2>/dev/null | cksum | awk '{print $1}'
}
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
  content="$(
    {
      xargs -0 -r git hash-object <"$list" 2>/dev/null
      _gate_code_digest
    } | cksum | awk '{print $1}'
  )"
  rm -f "$list"
  printf '%s %s %s' "$paths" "$content" "$PR_BASE"
}

# One seam, so callers never reimplement the algorithm. The lifecycle test used
# to carry its own shell copy of this digest, which is precisely why changing it
# was expensive enough to defer.
if [[ "${1:-}" == "--print-state-digest" ]]; then
  _gate_state_digest
  printf '\n'
  exit 0
fi
_gate_head_sha() {
  # A repository with no commits has no HEAD to record. That is the documented
  # "no head recorded" case, not a failure to swallow: pr_gate_failure.py then
  # falls back to digest-only matching. Handled explicitly rather than with
  # `|| true`, which the swallowed-failure ratchet counts and rightly so.
  local head
  if head="$(git rev-parse HEAD 2>/dev/null)"; then
    printf '%s' "$head"
  fi
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
  python3 "$_GATE_FAILURE_PY" refuse "$_GATE_FAILURE" "$(_gate_state_digest)" \
    --head-sha "$(_gate_head_sha)" || _gate_refuse_rc=$?
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
      --head-sha "$(_gate_head_sha)" \
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
  local stage="${1:-}"
  local rc=0
  set +e
  PR_CHANGED_FILE="$changed_file" PR_PRECOMMIT_STAGE="$stage" \
    bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS" 2>&1 | tee "$precommit_log"
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

echo "=== writers (once) ==="
_gate_run_precommit writers && precommit_rc=0 || precommit_rc=$?

if [[ "$precommit_rc" -ne 0 ]]; then
  if [[ -f "$SCRIPT_DIR/attribute_tree_writers.sh" ]]; then
    bash "$SCRIPT_DIR/attribute_tree_writers.sh" "$WS" "$status_before" "$precommit_log" || true
  fi
  if grep -q '^- exit code: ' "$precommit_log"; then
    echo "FAIL: pre-commit hook(s) failed:"
    _precommit_failing_hooks "$precommit_log"
  elif grep -q 'tracked files dirty after precommit-repo' "$precommit_log"; then
    echo "FAIL: writer rewrote tracked files — commit the rewrite, then re-run make pr."
    echo "      Do not rebase status_before over that dirt. Do not retry hooks."
  else
    echo "FAIL: writers stage exited ${precommit_rc}"
  fi
  exit 1
fi

# Stage 3 — overlap once on make pr only (PR_EARLY_OVERLAP inherited from `pr:`).
if [[ "${PR_EARLY_OVERLAP:-0}" = "1" ]]; then
  echo "--- early overlap (PR_OVERLAP=${PR_OVERLAP:-block}) ---"
  _base_ref="${PR_BASE#origin/}"
  if ! git fetch origin "$_base_ref"; then
    echo "FAIL: cannot fetch origin/${_base_ref} — collision state undeterminable"
    exit 1
  fi
  mkdir -p "$WS/.l9/pr"
  if ! python3 "$SCRIPT_DIR/pr_overlap_check.py" \
    --workspace "$WS" --base "$PR_BASE" \
    --write-receipt "$WS/.l9/pr/overlap-receipt.json"; then
    echo "FAIL: early overlap blocked publish (PR_OVERLAP=${PR_OVERLAP:-block})"
    exit 1
  fi
fi

# Stage 4 — one parallel read-only wave. Jobs do not call each other.
_gate_run_uv_lock() {
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
}

_gate_run_pytest() {
  echo "--- pytest ---"
  # Host publish knobs must not leak into overlap / remediates tests.
  unset PR_OVERLAP PR_OVERLAP_TELEMETRY PR_STACK PR_REMEDIATE
  # run_python_test_suites.py runs the GOVERNANCE suite registry
  # (ops/config/python-contract.json) and derives REPO_ROOT from its own location,
  # so it only ever describes this repository. Handing it a consumer workspace's
  # changed files made the selector emit paths such as src/<consumer_pkg>/ that do
  # not exist under REPO_ROOT, so the repo-root suite matched nothing and pytest
  # exited 4 -- failing the gate before any push, for every consumer repo with a
  # changed .py file. Scope it to the workspaces it actually describes, the same
  # way this file already gates the wiring check below.
  _pytest_ws_kind="$(classify_workspace_kind "$WS")"
  if [[ "${PR_SKIP_PYTEST:-0}" == "1" ]]; then
    echo "OK: skip pytest (PR_SKIP_PYTEST=1)"
  elif [[ "$_pytest_ws_kind" != "ssot" && "$_pytest_ws_kind" != "ssot_checkout" ]]; then
    echo "OK: skip governance pytest registry (workspace kind=$_pytest_ws_kind)"
    echo "NOTE: consumer tests are owned by the consumer repository and its CI;" \
         "this gate did not run them"
  elif grep -Eq '\.py$' "$changed_file"; then
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
    : "${_pytest_ws_kind:=$(classify_workspace_kind "$WS")}"
    _pytest_repo_root_args=()
    if [ "$_pytest_ws_kind" = "ssot" ] || [ "$_pytest_ws_kind" = "ssot_checkout" ]; then
      if [ "$(cd "$WS" && pwd -P)" != "$(cd "$GOV_ROOT" && pwd -P)" ]; then
        _pytest_repo_root_args=(--repo-root "$WS")
        echo "OK: pytest root -> workspace ($_pytest_ws_kind; governance clone, \$GOV differs)"
      fi
    fi
    # `${a[@]+"${a[@]}"}` rather than `"${a[@]}"`: under `set -u`, bash 3.2 calls
    # an empty array unbound and aborts the gate. macOS ships 3.2 as /bin/bash and
    # the Makefile resolves `bash` from PATH, so publishing from a governance
    # checkout there (WS == GOV_ROOT leaves this array empty) never reached pytest.
    "$_pytest_py" "$SCRIPT_DIR/run_python_test_suites.py" \
      --profile local \
      ${_pytest_repo_root_args[@]+"${_pytest_repo_root_args[@]}"} \
      --changed-file "$changed_file" \
      -- "${pytest_args[@]}"
  else
    echo "OK: skip pytest (no changed Python files)"
  fi
}

_gate_run_sync() {
  echo "--- sync-generated-artifacts ---"
  # --pe-manifest reaches environment/program-execution/MANIFEST.json. Without
  # it the PE manifest is never healed on the publish path and
  # `make program-execution-conformance` goes red on every PE edit. The
  # governance-self-check drift job is the other pinned caller.
  python3 "$GOV_ROOT/ops/scripts/sync_generated_artifacts.py" \
    --root "$WS" \
    --changed-file "$changed_file" \
    --pe-manifest \
    --check
  if ! _gate_classify_dirtiness "sync-generated-artifacts"; then
    if [[ -f "$SCRIPT_DIR/attribute_tree_writers.sh" ]]; then
      bash "$SCRIPT_DIR/attribute_tree_writers.sh" "$WS" "$status_before" || true
    fi
    echo "FAIL: unexpected non-generated dirtiness after sync"
    git status --short
    exit 1
  fi
}

_gate_run_root_protect() {
  echo "--- root-file protection ---"
  _root_protect_py="$GOV_ROOT/ops/scripts/validate_root_file_protection.py"
  if [[ -f "$_root_protect_py" && -f "$WS/ops/config/root-file-protection.json" ]]; then
    python3 "$_root_protect_py" --base "$PR_BASE" --head HEAD --repo "$WS"
  else
    echo "OK: skip root-file protection (no ops/config/root-file-protection.json in this workspace)"
  fi
}

_gate_run_skill_activation() {
  echo "--- skill-activation ---"
  if [[ -f "$WS/environment/agents/adapters/claude-code/validate_skill_activation.py" ]]; then
    if grep -Eq '^(skills/|ops/skill_routing/|ops/generated/skill-registry\.json|environment/agents/adapters/claude-code/)' "$changed_file"; then
      python3 "$WS/environment/agents/adapters/claude-code/validate_skill_activation.py"
    else
      echo "OK: skip skill-activation (skills/routing unchanged)"
    fi
  fi
}

_gate_run_projection_check() {
  echo "--- local-activation ---"
  is_local=0
  if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" && -d "${HOME}/.cursor" && -w "${HOME}/.cursor" ]]; then
    is_local=1
  fi
  if [[ "$is_local" -ne 1 || ! -f "$WS/skills/AUTONOMY_MANIFEST.yaml" ]]; then
    echo "OK: skip local-activation (CI or non-writable ~/.cursor)"
    return 0
  fi
  if [[ -f "$GOV_ROOT/ops/scripts/project_llm_rules.py" ]]; then
    if ! python3 "$GOV_ROOT/ops/scripts/project_llm_rules.py" --root "$WS" --check --quiet; then
      echo "FAIL: llm-rules projection drift — re-run: python3 ops/scripts/project_llm_rules.py --root \"$WS\""
      python3 "$GOV_ROOT/ops/scripts/project_llm_rules.py" --root "$WS" --check
      exit 1
    fi
    echo "OK: llm-rules projection matches rules/*.mdc"
  fi
  if ! python3 "$GOV_ROOT/ops/scripts/claude_projection.py" \
    --root "$WS" --workspace "$WS" --domains skills,commands,rules,mcp \
    --check --quiet --no-receipt; then
    echo "FAIL: Claude projection --check drifted — re-run: python3 ops/scripts/claude_projection.py --root \"$WS\" --workspace \"$WS\""
    python3 "$GOV_ROOT/ops/scripts/claude_projection.py" \
      --root "$WS" --workspace "$WS" --domains skills,commands,rules,mcp --check --summary --no-receipt
    exit 1
  fi
  echo "OK: Claude projection (skills, commands, rules) matches SSOT"
}

_gate_run_wiring() {
  echo "--- wiring ---"
  is_local=0
  if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" && -d "${HOME}/.cursor" && -w "${HOME}/.cursor" ]]; then
    is_local=1
  fi
  if [[ "$is_local" -ne 1 || ! -f "$WS/skills/AUTONOMY_MANIFEST.yaml" ]]; then
    echo "OK: skip wiring (CI or non-writable ~/.cursor)"
    return 0
  fi
  # Heal missing gitignored .cursor links under the existing make-pr lock.
  # Not sessionStart — reconcilers skip while this lock is held. Without the
  # heal the wiring check below fail-closes on links the gate could have
  # restored itself.
  if [[ -x "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh" ]]; then
    L9_WIRE_LINKS_ONLY=1 bash "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh" "$WS" \
      || echo "WARN: ensure_workspace_wired failed — wiring check will fail-closed"
  fi
  WS_KIND="$(classify_workspace_kind "$WS")"
  if [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
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
}

_gate_run_security() {
  echo "--- security ---"
  bash "$SCRIPT_DIR/run_pr_security.sh" --mode gate "$WS"
}

_gate_run_readers() {
  echo "--- pre-commit readers (once) ---"
  _gate_run_precommit readers
}

echo "=== reader wave (once, parallel) ==="
_wave_dir="$(mktemp -d)"
_wave_pids=()
_wave_names=()
_wave_start() {
  local name="$1"
  shift
  ( "$@" ) >"$_wave_dir/$name.log" 2>&1 &
  _wave_pids+=("$!")
  _wave_names+=("$name")
}
_wave_start readers _gate_run_readers
_wave_start uv-lock _gate_run_uv_lock
_wave_start pytest _gate_run_pytest
_wave_start sync _gate_run_sync
_wave_start root-protect _gate_run_root_protect
_wave_start skill-activation _gate_run_skill_activation
_wave_start projection _gate_run_projection_check
_wave_start wiring _gate_run_wiring
_wave_start security _gate_run_security
_wave_rc=0
_wave_i=0
while [ "$_wave_i" -lt "${#_wave_pids[@]}" ]; do
  if ! wait "${_wave_pids[$_wave_i]}"; then
    echo "FAIL: reader wave job ${_wave_names[$_wave_i]}"
    _wave_rc=1
  fi
  _wave_i=$((_wave_i + 1))
done
_wave_i=0
while [ "$_wave_i" -lt "${#_wave_names[@]}" ]; do
  echo "=== wave: ${_wave_names[$_wave_i]} ==="
  cat "$_wave_dir/${_wave_names[$_wave_i]}.log"
  cat "$_wave_dir/${_wave_names[$_wave_i]}.log" >>"$_GATE_LOG" || true
  _wave_i=$((_wave_i + 1))
done
rm -rf "$_wave_dir"
if [[ "$_wave_rc" -ne 0 ]]; then
  echo "FAIL: reader wave had a failing job"
  exit 1
fi

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
