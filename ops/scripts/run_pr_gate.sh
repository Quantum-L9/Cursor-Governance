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

# Always-run governance contract surface: cheap, changed-file-INDEPENDENT.
# A Markdown/YAML/config-only mutation must never bypass the checks that prove
# its semantics (P2-12). These validate the governance repo (GOV_ROOT).
echo "=== governance contract surface (always-run) ==="
if [[ -f "$GOV_ROOT/ops/scripts/validate_governance_contract_surface.py" ]]; then
  python3 "$GOV_ROOT/ops/scripts/validate_governance_contract_surface.py"
fi
if [[ -f "$GOV_ROOT/ops/scripts/validate_legacy_doctrine_residue.py" ]]; then
  python3 "$GOV_ROOT/ops/scripts/validate_legacy_doctrine_residue.py"
fi
if [[ -f "$GOV_ROOT/ops/scripts/validate_workflow_action_pins.py" ]]; then
  python3 "$GOV_ROOT/ops/scripts/validate_workflow_action_pins.py"
fi

echo "=== make pr (changed files vs ${PR_BASE}; full-tree = make pr-full / nightly) ==="

status_before="$(mktemp)"
changed_file="$(mktemp)"
precommit_log="$(mktemp)"
py_list="$(mktemp)"
trap 'rm -f "$status_before" "$changed_file" "$precommit_log" "$py_list"; repo_write_lock_release' EXIT
git status --porcelain >"$status_before"

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
  bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS" 2>&1 | tee "$precommit_log"
  rc="${PIPESTATUS[0]}"
  set -e
  return "$rc"
}

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

PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
  >"$changed_file" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)

echo "--- ruff (changed Python) ---"
py_count=0
grep -E '\.(py|pyi)$' "$changed_file" >"$py_list" || true
py_count="$(grep -c . "$py_list" || true)"
if [[ "${py_count:-0}" -eq 0 ]]; then
  echo "OK: no changed Python files for ruff"
else
  echo "ruff (changed): ${py_count} file(s)"
  _ruff="$GOV_ROOT/.venv/bin/ruff"
  if [[ ! -x "$_ruff" && -n "${GOV_TOOLCHAIN_ROOT:-}" && -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff" ]]; then
    _ruff="$GOV_TOOLCHAIN_ROOT/.venv/bin/ruff"
  fi
  if [[ ! -x "$_ruff" ]]; then
    echo "FAIL: locked ruff missing at $GOV_ROOT/.venv/bin/ruff (run: make venv)"
    exit 1
  fi
  xargs "$_ruff" check <"$py_list"
  xargs "$_ruff" format --check <"$py_list"
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
if grep -Eq '\.py$' "$changed_file"; then
  # Changed-files gate: only collect the secrets capability suite when that
  # plane changed. Full-tree remains make pr-full / nightly. Avoids a host
  # miniconda cryptography ABI break aborting unrelated PE/ops PRs.
  pytest_args=(--tb=short -q)
  if ! grep -Eq '^(tests/ops/secrets/|ops/secrets/)' "$changed_file"; then
    pytest_args+=(--ignore=tests/ops/secrets)
    echo "OK: skip secrets capability suite (ops/secrets unchanged)"
  fi
  bash "$SCRIPT_DIR/run_pytest_suites.sh" "${pytest_args[@]}"
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
  python3 "$GOV_ROOT/ops/scripts/reconcile_llm_skill_adapters.py" \
    --root "$WS" --workspace "$WS" --quiet || true
  if ! python3 "$GOV_ROOT/ops/scripts/reconcile_llm_skill_adapters.py" \
    --root "$WS" --workspace "$WS" --check --quiet; then
    echo "FAIL: LLM skill adapter reconcile --check drifted — re-run sync_generated_artifacts / reconcile_llm_skill_adapters"
    python3 "$GOV_ROOT/ops/scripts/reconcile_llm_skill_adapters.py" \
      --root "$WS" --workspace "$WS" --check
    exit 1
  fi
  echo "OK: LLM skill adapters reconciled to skills/ SSOT"
  if [[ -f "$GOV_ROOT/ops/scripts/reconcile_llm_rule_adapters.py" ]]; then
    if ! python3 "$GOV_ROOT/ops/scripts/reconcile_llm_rule_adapters.py" \
      --root "$WS" --workspace "$WS" --check --quiet; then
      echo "FAIL: LLM rule adapter reconcile --check drifted — re-run reconcile_llm_rule_adapters"
      python3 "$GOV_ROOT/ops/scripts/reconcile_llm_rule_adapters.py" \
        --root "$WS" --workspace "$WS" --check
      exit 1
    fi
    echo "OK: LLM rule adapters reconciled to environment/generated/llm-rules/"
  fi
  # check_governance_wiring.sh asserts Cursor DESKTOP activation (plugin symlink,
  # .cursor-commands, .cursor/plans, ~/.cursor/hooks.json). The enclosing guard uses
  # "~/.cursor exists and is writable" as a proxy for "this is a Cursor machine", but
  # Graphiti's own state dir (~/.cursor/graphiti-state) creates that path on EVERY
  # surface — so the proxy silently became true for headless adapters. Gate the
  # desktop-wiring assertion on the surface id instead. The reconcile checks above
  # stay unconditional: they are surface-independent and must keep running here.
  # PAIRED PREDICATE: run_pr_precommit.sh skips symlinks-check the same way.
  # Isolates skip consumer repo symlinks; machine sessionEnd/Graphiti still run.
  WS_KIND="$(classify_workspace_kind "$WS")"
  if [ "$WS_KIND" = "ssot" ] || [ "$WS_KIND" = "ssot_checkout" ]; then
    if ! bash "$SCRIPT_DIR/check_governance_wiring.sh" "$WS"; then
      echo "FAIL: governance wiring incomplete — see FAIL lines above"
      exit 1
    fi
    echo "OK: ssot-family workspace ($WS_KIND) — consumer links not required"
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
bash "$SCRIPT_DIR/run_pr_security.sh" "$WS"

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

echo "RESULT: PASS — local PR gate clean (changed files only)"
