#!/usr/bin/env bash
# Changed-files local PR gate. Full-tree = nightly CI / make pr-full / make precommit.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${WS:-$(pwd)}"
WS="$(cd "$WS" && pwd)"
PR_BASE="${PR_BASE:-origin/main}"
PR_SECURITY_ADVISORY="${PR_SECURITY_ADVISORY:-0}"
PR_MYPY_STRICT="${PR_MYPY_STRICT:-0}"

cd "$WS"
export WS PR_BASE PR_SECURITY_ADVISORY

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

echo "=== make pr (changed files vs ${PR_BASE}; full-tree = make pr-full / nightly) ==="

status_before="$(mktemp)"
changed_file="$(mktemp)"
trap 'rm -f "$status_before" "$changed_file"' EXIT
git status --porcelain >"$status_before"

bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS"

if ! git status --porcelain | diff -q "$status_before" - >/dev/null; then
  if bash "$SCRIPT_DIR/classify_generated_dirtiness.sh" "$WS" "$status_before"; then
    echo "WARN: generated artifacts updated by pre-commit — stage them with your commit:"
    git status --short
  else
    echo "FAIL: pre-commit autofixed non-generated files — review, stage, and re-run make pr"
    git status --short
    exit 1
  fi
fi

PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
  >"$changed_file" 2> >(grep -E '^(SOURCE:|ERROR:)' >&2 || true)

echo "--- ruff (changed Python) ---"
py_count=0
py_list="$(mktemp)"
trap 'rm -f "$status_before" "$changed_file" "$py_list"' EXIT
grep -E '\.(py|pyi)$' "$changed_file" >"$py_list" || true
py_count="$(grep -c . "$py_list" || true)"
if [[ "${py_count:-0}" -eq 0 ]]; then
  echo "OK: no changed Python files for ruff"
else
  echo "ruff (changed): ${py_count} file(s)"
  xargs uv run --no-build ruff check <"$py_list"
  xargs uv run --no-build ruff format --check <"$py_list"
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
  bash "$SCRIPT_DIR/run_pytest_suites.sh" --tb=short -q
else
  echo "OK: skip pytest (no changed Python files)"
fi

echo "--- sync-generated-artifacts ---"
python3 "$GOV_ROOT/ops/scripts/sync_generated_artifacts.py" \
  --root "$WS" \
  --changed-file "$changed_file" \
  --check
if ! git status --porcelain | diff -q "$status_before" - >/dev/null; then
  if bash "$SCRIPT_DIR/classify_generated_dirtiness.sh" "$WS" "$status_before"; then
    echo "WARN: stage generated files with your commit (validators PASS):"
    git status --short
  else
    echo "FAIL: unexpected non-generated dirtiness after sync"
    git status --short
    exit 1
  fi
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
  if ! bash "$GOV_ROOT/ops/scripts/check_governance_wiring.sh" "$WS"; then
    echo "FAIL: governance wiring incomplete — run: bash ops/scripts/setup_workspace_symlinks.sh"
    exit 1
  fi
else
  echo "OK: skip local-activation (CI or non-writable ~/.cursor)"
fi

echo "--- security ---"
bash "$SCRIPT_DIR/run_pr_security.sh" "$WS"

if [[ "$PR_MYPY_STRICT" = "1" ]]; then
  uv run --no-build mypy . --show-error-codes --pretty --ignore-missing-imports
else
  echo "mypy: advisory on PR gate (set PR_MYPY_STRICT=1 to fail; full check is make lint / nightly)"
fi

_scratch_hold_restore
if ! _scratch_hold_status; then
  echo "FAIL: open scratch hold(s) after gate — restore before shipping"
  exit 1
fi

echo "RESULT: PASS — local PR gate clean (changed files only)"
