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

echo "=== make pr (changed files vs ${PR_BASE}; full-tree = make pr-full / nightly) ==="

status_before="$(mktemp)"
changed_file="$(mktemp)"
trap 'rm -f "$status_before" "$changed_file"' EXIT
git status --porcelain >"$status_before"

bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS"

if ! git status --porcelain | diff -q "$status_before" - >/dev/null; then
  echo "FAIL: pre-commit autofixed files — review, stage, and re-run make pr"
  git status --short
  exit 1
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
  # xargs -n batch to stay under ARG_MAX; paths are repo-relative.
  # --no-build: do not execute package build/setup scripts (Sonar shell:S8541).
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
  status=0
  TESTING=true PYTHONPATH=. uv run --no-build pytest . --tb=short -q || status=$?
  if [[ "$status" -eq 5 ]]; then
    echo "OK: pytest collected zero tests (exit 5)"
  elif [[ "$status" -ne 0 ]]; then
    exit "$status"
  fi
else
  echo "OK: skip pytest (no changed Python files)"
fi

echo "--- rules-validate ---"
if grep -Eq '^rules/' "$changed_file"; then
  python3 "$GOV_ROOT/ops/scripts/validate_rules_manifest.py" --root "$WS"
else
  echo "OK: skip rules-validate (rules/ unchanged)"
fi

echo "--- security ---"
bash "$SCRIPT_DIR/run_pr_security.sh" "$WS"

if [[ "$PR_MYPY_STRICT" = "1" ]]; then
  uv run --no-build mypy . --show-error-codes --pretty --ignore-missing-imports
else
  echo "mypy: advisory on PR gate (set PR_MYPY_STRICT=1 to fail; full check is make lint / nightly)"
fi

echo "RESULT: PASS — local PR gate clean (changed files only)"
