#!/usr/bin/env bash
# Local PR security gate — changed-files only (gitleaks + bandit + semgrep + pip-audit).
# Full-tree scans belong to nightly CI, not make pr / pre-commit.
#
# Version authority: requirements.txt (l9-ci-sdk wins over l9-ci-core on
# disagreement). bandit/pip-audit come from that file; gitleaks is core-only
# (sdk does not pin it). Semgrep: SDK policy >=1.100.0,<2.0.0.
#
# Consumer usage (no per-repo Makefile copy required):
#   make -C "$HOME/.cursor-governance" pr-security WS="$(pwd)"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WS="${1:-${WS:-$(pwd)}}"
WS="$(cd "$WS" && pwd)"

PR_SECURITY_ADVISORY="${PR_SECURITY_ADVISORY:-0}"
PR_BASE="${PR_BASE:-}"
GITLEAKS_CONFIG="${GITLEAKS_CONFIG:-$GOV_ROOT/.gitleaks.toml}"
# Pins: Python tools from requirements.txt (sdk wins over core). gitleaks is a
# machine CLI — only pinned in l9-ci-core security.yml (sdk has no gitleaks pin).
REQ_FILE="${REQ_FILE:-$GOV_ROOT/requirements.txt}"
pin_from_req() {
  local name="$1"
  awk -F== -v n="$name" '$1==n {print $2; exit}' "$REQ_FILE"
}
GITLEAKS_PIN="8.24.3"
BANDIT_PIN="$(pin_from_req bandit)"
PIP_AUDIT_PIN="$(pin_from_req pip-audit)"
BANDIT_PIN="${BANDIT_PIN:-1.8.6}"
PIP_AUDIT_PIN="${PIP_AUDIT_PIN:-2.9.0}"
BANDIT_SEVERITY="${BANDIT_SEVERITY:-high}"
SEMGREP_CONFIGS="${SEMGREP_CONFIGS:-p/python p/secrets}"

EXCLUDE_PREFIXES=(
  _archived/ _archive/ archive/ archived/
  WIP/ current_work/ C_GOV_FILES/
  .venv/ node_modules/ reports/ workflows/
)

PASS=0
FAIL=0
SKIP=0
FAILURES=()

note() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); note "PASS: $*"; }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$*"); note "FAIL: $*"; }
skip() { SKIP=$((SKIP + 1)); note "SKIP: $*"; }
have() { command -v "$1" >/dev/null 2>&1; }

run_uvx_pkg() {
  # run_uvx_pkg <pkg==ver> <bin> [args...]
  local spec="$1" bin="$2"
  shift 2
  if have uvx; then
    uvx --from "$spec" "$bin" "$@"
  elif have uv; then
    uv tool run --from "$spec" "$bin" "$@"
  else
    return 127
  fi
}

is_excluded() {
  local f="$1" p
  for p in "${EXCLUDE_PREFIXES[@]}"; do
    [[ "$f" == "$p"* ]] && return 0
  done
  return 1
}

filter_existing() {
  local f
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    is_excluded "$f" && continue
    [[ -f "$WS/$f" ]] || continue
    printf '%s\n' "$f"
  done
}

note "=== PR security gate (changed files only) ==="
note "Governance: $GOV_ROOT"
note "Workspace:  $WS"
note "Advisory:   $PR_SECURITY_ADVISORY"
note "Pins: gitleaks@$GITLEAKS_PIN bandit==$BANDIT_PIN pip-audit==$PIP_AUDIT_PIN"

_all_tmp="$(mktemp)"
_chg_tmp="$(mktemp)"
trap 'rm -f "$_all_tmp" "$_chg_tmp"' EXIT
PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
  >"$_all_tmp" 2> >(while IFS= read -r line; do note "$line"; done)
filter_existing <"$_all_tmp" >"$_chg_tmp"

CHANGED=()
while IFS= read -r _f; do
  [[ -n "$_f" ]] && CHANGED+=("$_f")
done <"$_chg_tmp"

note "Changed (gated): ${#CHANGED[@]} file(s)"
if [[ ${#CHANGED[@]} -eq 0 ]]; then
  skip "no scannable changed files after exclusions"
  note "RESULT: PASS — security gate (nothing in scope)"
  exit 0
fi

# ── gitleaks ───────────────────────────────────────────────────────────────
run_gitleaks() {
  if ! have gitleaks; then
    skip "gitleaks not on PATH (brew install gitleaks@$GITLEAKS_PIN)"
    return 0
  fi
  local ver
  ver="$(gitleaks version 2>/dev/null | head -1 | tr -d '[:space:]' || true)"
  if [[ -n "$ver" && "$ver" != "$GITLEAKS_PIN" ]]; then
    note "WARN: gitleaks $ver on PATH (expected $GITLEAKS_PIN from l9-ci-core security.yml; sdk has no gitleaks pin)"
  fi
  local cfg_args=()
  [[ -f "$GITLEAKS_CONFIG" ]] && cfg_args=(-c "$GITLEAKS_CONFIG")
  local status=0
  local f
  # Scan only changed paths (not the whole tree / history).
  for f in "${CHANGED[@]}"; do
    if ! (
      cd "$WS"
      gitleaks detect --no-git --redact --exit-code=1 "${cfg_args[@]}" --source "$f"
    ); then
      status=1
    fi
  done
  if [[ "$status" -eq 0 ]]; then
    ok "gitleaks (${#CHANGED[@]} changed path(s))"
  else
    fail "gitleaks found secrets in changed files"
  fi
}

# ── bandit ─────────────────────────────────────────────────────────────────
run_bandit() {
  local -a py=()
  local f
  for f in "${CHANGED[@]}"; do
    [[ "$f" == *.py ]] && py+=("$WS/$f")
  done
  if [[ ${#py[@]} -eq 0 ]]; then
    skip "bandit (no changed .py files)"
    return 0
  fi
  local sev_flag="-lll"
  case "$BANDIT_SEVERITY" in
    high) sev_flag="-lll" ;;
    medium) sev_flag="-ll" ;;
    low) sev_flag="-l" ;;
  esac
  if run_uvx_pkg "bandit==${BANDIT_PIN}" bandit "${py[@]}" "$sev_flag" -q; then
    ok "bandit==$BANDIT_PIN (${#py[@]} file(s), severity>=$BANDIT_SEVERITY)"
  else
    fail "bandit reported issues in changed Python files"
  fi
}

# ── semgrep ────────────────────────────────────────────────────────────────
run_semgrep() {
  local -a targets=()
  local f
  for f in "${CHANGED[@]}"; do
    case "$f" in
      *.py|*.pyi|*.ts|*.tsx|*.js|*.jsx) targets+=("$WS/$f") ;;
    esac
  done
  if [[ ${#targets[@]} -eq 0 ]]; then
    skip "semgrep (no changed source files)"
    return 0
  fi
  local -a cmd=()
  if have semgrep; then
    cmd=(semgrep)
  elif have uvx || have uv; then
    cmd=(run_uvx_pkg "semgrep>=1.100.0,<2" semgrep)
  else
    skip "semgrep not available"
    return 0
  fi
  # Flatten function+args for version / run when using run_uvx_pkg wrapper is awkward;
  # prefer PATH semgrep, else uvx --from.
  if ! have semgrep; then
    cmd=(uvx --from "semgrep>=1.100.0,<2" semgrep)
  fi
  local ver
  ver="$("${cmd[@]}" --version 2>/dev/null | head -1 || true)"
  note "semgrep: $ver (SDK supported range >=1.100.0,<2.0.0)"
  local -a configs=()
  local c
  # shellcheck disable=SC2086
  for c in $SEMGREP_CONFIGS; do
    configs+=(--config "$c")
  done
  if "${cmd[@]}" --error --quiet "${configs[@]}" "${targets[@]}"; then
    ok "semgrep (${#targets[@]} file(s))"
  else
    fail "semgrep found issues in changed files"
  fi
}

# ── pip-audit ──────────────────────────────────────────────────────────────
run_pip_audit() {
  local need=0 f
  for f in "${CHANGED[@]}"; do
    case "$f" in
      uv.lock|pyproject.toml|requirements.txt|requirements-*.txt|constraints.txt) need=1 ;;
    esac
  done
  if [[ "$need" -ne 1 ]]; then
    skip "pip-audit (dependency manifests unchanged)"
    return 0
  fi
  if ! have uv; then
    skip "pip-audit (uv required)"
    return 0
  fi
  (
    cd "$WS"
    if [[ -f uv.lock ]]; then
      uv run --with "pip-audit==${PIP_AUDIT_PIN}" pip-audit --progress-spinner off
    elif [[ -f requirements.txt ]]; then
      run_uvx_pkg "pip-audit==${PIP_AUDIT_PIN}" pip-audit -r requirements.txt --progress-spinner off
    else
      uv run --with "pip-audit==${PIP_AUDIT_PIN}" pip-audit --progress-spinner off
    fi
  ) && ok "pip-audit==$PIP_AUDIT_PIN" || fail "pip-audit found vulnerabilities"
}

run_gitleaks
run_bandit
run_semgrep
run_pip_audit

note ""
note "Summary: pass=$PASS fail=$FAIL skip=$SKIP"
if [[ "$FAIL" -gt 0 ]]; then
  for f in "${FAILURES[@]}"; do
    note "  - $f"
  done
  if [[ "$PR_SECURITY_ADVISORY" = "1" ]]; then
    note "RESULT: ADVISORY FAIL (not blocking — PR_SECURITY_ADVISORY=1)"
    exit 0
  fi
  note "RESULT: FAIL — security gate"
  exit 1
fi
note "RESULT: PASS — security gate"
exit 0
