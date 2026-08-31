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
# Full Semgrep packs: PR_SECURITY_PROFILE=full make pr-security
#                     (or make pr-security-full)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GOV_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# --mode decides what a MISSING SCANNER BINARY means (INV-5).
#
#   advisory  a missing binary SKIPs with a warning. Correct for local dev,
#             where not every contributor has every scanner installed.
#   gate      a missing binary FAILS, naming the tool and how to provision it.
#
# The default stays advisory so existing direct callers are unaffected; the
# publish path (run_pr_gate.sh) opts in to gate. This distinction exists because
# the policy "SKIP a checker whose binary is absent" reads as a pass in the
# summary — the audit found gitleaks absent from the runtime entirely, which
# meant secret scanning silently did not run at all (finding B-11).
PR_SECURITY_MODE="${PR_SECURITY_MODE:-advisory}"
_ws_arg=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) PR_SECURITY_MODE="${2:?--mode needs gate|advisory}"; shift 2 ;;
    --) shift ;;
    *) _ws_arg="$1"; shift ;;
  esac
done
case "$PR_SECURITY_MODE" in
  gate|advisory) : ;;
  *) echo "run_pr_security: unknown --mode '$PR_SECURITY_MODE' (want gate|advisory)" >&2; exit 2 ;;
esac

PR_SECURITY_PROFILE="${PR_SECURITY_PROFILE:-velocity}"
case "$PR_SECURITY_PROFILE" in
  velocity|full) : ;;
  *) echo "run_pr_security: unknown PR_SECURITY_PROFILE '$PR_SECURITY_PROFILE' (want velocity|full)" >&2; exit 2 ;;
esac

WS="${_ws_arg:-${WS:-$(pwd)}}"
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
_LOCAL_SEMGREP_RULES="$GOV_ROOT/.semgrep/l9-pr.yml"
# SEMGREP_CONFIGS override wins when the caller sets the variable (even empty).
if [[ "${SEMGREP_CONFIGS+set}" != "set" ]]; then
  if [[ "$PR_SECURITY_PROFILE" = "full" ]]; then
    SEMGREP_CONFIGS="p/python p/secrets"
  else
    SEMGREP_CONFIGS="p/secrets"
  fi
  if [[ -f "$_LOCAL_SEMGREP_RULES" ]]; then
    SEMGREP_CONFIGS="$SEMGREP_CONFIGS $_LOCAL_SEMGREP_RULES"
  fi
fi

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

# A scanner that is ABSENT is categorically different from a scanner that had
# nothing to scan. Only the former is a gate failure; "no changed .py files"
# stays a skip in both modes.
missing_tool() { # $1=tool  $2=provisioning hint
  if [ "$PR_SECURITY_MODE" = "gate" ]; then
    fail "$1 is NOT INSTALLED — gate mode requires it (provision: $2)"
  else
    skip "$1 not available ($2)"
  fi
}

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

_replay_scanner_log() {
  local log="$1" line
  [[ -f "$log" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    note "$line"
    case "$line" in
      "PASS: "*) PASS=$((PASS + 1)) ;;
      "FAIL: "*) FAIL=$((FAIL + 1)); FAILURES+=("${line#FAIL: }") ;;
      "SKIP: "*) SKIP=$((SKIP + 1)) ;;
    esac
  done <"$log"
}

note "=== PR security gate (changed files only) ==="
note "Governance: $GOV_ROOT"
note "Workspace:  $WS"
note "Advisory:   $PR_SECURITY_ADVISORY"
note "Profile:    $PR_SECURITY_PROFILE"
note "Pins: gitleaks@$GITLEAKS_PIN bandit==$BANDIT_PIN pip-audit==$PIP_AUDIT_PIN"

_all_tmp="$(mktemp)"
_chg_tmp="$(mktemp)"
_scan_tmp=""
_wave_dir=""
_cleanup() {
  rm -f "$_all_tmp" "$_chg_tmp"
  [[ -n "$_scan_tmp" && -d "$_scan_tmp" ]] && rm -rf "$_scan_tmp"
  [[ -n "$_wave_dir" && -d "$_wave_dir" ]] && rm -rf "$_wave_dir"
  # An EXIT trap's status replaces the script's. The two [[ ]] tests above are
  # false on the early "nothing in scope" exit (neither temp dir is created
  # yet), so without this the trap returned 1 and turned `exit 0` -- printed as
  # "RESULT: PASS" -- into a gate failure for any change set that filters to
  # empty (a WIP-only or docs-only PR).
  return 0
}
trap _cleanup EXIT
if [[ -n "${PR_CHANGED_FILE:-}" && -f "$PR_CHANGED_FILE" ]]; then
  note "OK: skip resolve_changed_files.sh (PR_CHANGED_FILE)"
  cat "$PR_CHANGED_FILE" >"$_all_tmp"
else
  PR_BASE="$PR_BASE" WS="$WS" bash "$SCRIPT_DIR/resolve_changed_files.sh" \
    >"$_all_tmp" 2> >(while IFS= read -r line; do note "$line"; done)
fi
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
# One process over a temp tree of the changed set. `gitleaks dir a b` ignores
# extra args and can walk the cwd (measured: two files → 141 MB). Never default
# `detect` without --no-git (that scans git history).
run_gitleaks() {
  if ! have gitleaks; then
    missing_tool gitleaks "bash ops/scripts/bootstrap_agent_environment.sh --surface local"
    return 0
  fi
  local ver
  # Output looks like "gitleaks version 8.24.3" — take the last token, not a space-stripped blob.
  ver="$(gitleaks version 2>/dev/null | head -1 | awk '{print $NF}' || true)"
  if [[ -n "$ver" && "$ver" != "$GITLEAKS_PIN" ]]; then
    note "WARN: gitleaks $ver on PATH (expected $GITLEAKS_PIN from l9-ci-core security.yml; sdk has no gitleaks pin)"
  fi
  local cfg_args=()
  [[ -f "$GITLEAKS_CONFIG" ]] && cfg_args=(-c "$GITLEAKS_CONFIG")
  _scan_tmp="$(mktemp -d "${TMPDIR:-/tmp}/l9-gitleaks-changed.XXXXXX")"
  local f dest
  for f in "${CHANGED[@]}"; do
    dest="$_scan_tmp/$f"
    mkdir -p "$(dirname "$dest")"
    if ! ln "$WS/$f" "$dest" 2>/dev/null; then
      cp "$WS/$f" "$dest"
    fi
  done
  local status=0
  local -a extra=(--redact --exit-code=1)
  extra+=(--no-banner)
  extra+=("${cfg_args[@]}")
  if gitleaks dir --help >/dev/null 2>&1; then
    if ! gitleaks dir "${extra[@]}" "$_scan_tmp"; then
      status=1
    fi
  else
    if ! gitleaks detect --no-git "${extra[@]}" --source "$_scan_tmp"; then
      status=1
    fi
  fi
  rm -rf "$_scan_tmp"
  _scan_tmp=""
  if [[ "$status" -eq 0 ]]; then
    ok "gitleaks (${#CHANGED[@]} changed path(s), one process)"
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
  if ! have uvx && ! have uv; then
    missing_tool bandit "install uv (https://astral.sh/uv)"
    return 0
  fi
  if run_uvx_pkg "bandit==${BANDIT_PIN}" bandit "${py[@]}" "$sev_flag" -q; then
    ok "bandit==$BANDIT_PIN (${#py[@]} file(s), severity>=$BANDIT_SEVERITY)"
  else
    fail "bandit reported issues in changed Python files"
  fi
}

# ── semgrep ────────────────────────────────────────────────────────────────
# LOCAL COMMUNITY EDITION ONLY. CE needs no credential, and this gate must never
# acquire one: an authenticated run from a model-controlled process would ship
# findings to the vendor under a token the model can read.
#
# SEMGREP_APP_TOKEN is therefore scrubbed from the child environment rather than
# merely "not set" — an inherited token would otherwise silently upgrade this to
# an authenticated scan. Authenticated Semgrep AppSec runs through the
# `semgrep.appsec_scan` capability, inside the trusted worker (contract §14).
#
# Nothing else about this checker's PASS/FAIL/SKIP behaviour changes here; that
# semantic is a separate governance concern (contract §27).
run_semgrep() {
  local SEMGREP_APP_TOKEN=""
  unset SEMGREP_APP_TOKEN
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
  # Prefer PATH semgrep; else uvx / uv tool run (never assume uvx when only uv exists).
  local ver=""
  local -a configs=()
  local c
  # shellcheck disable=SC2086
  for c in $SEMGREP_CONFIGS; do
    configs+=(--config "$c")
  done
  note "semgrep configs: $SEMGREP_CONFIGS"
  if have semgrep; then
    ver="$(semgrep --version 2>/dev/null | head -1 || true)"
    note "semgrep: $ver (SDK supported range >=1.100.0,<2.0.0)"
    if semgrep --error --quiet --metrics=off "${configs[@]}" "${targets[@]}"; then
      ok "semgrep (${#targets[@]} file(s))"
    else
      fail "semgrep found issues in changed files"
    fi
  elif have uvx || have uv; then
    ver="$(run_uvx_pkg "semgrep>=1.100.0,<2" semgrep --version 2>/dev/null | head -1 || true)"
    note "semgrep: $ver (SDK supported range >=1.100.0,<2.0.0)"
    if run_uvx_pkg "semgrep>=1.100.0,<2" semgrep --error --quiet --metrics=off "${configs[@]}" "${targets[@]}"; then
      ok "semgrep (${#targets[@]} file(s))"
    else
      fail "semgrep found issues in changed files"
    fi
  else
    missing_tool semgrep "install uv/uvx, or pip install semgrep"
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
    missing_tool pip-audit "install uv (https://astral.sh/uv)"
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

_wave_dir="$(mktemp -d "${TMPDIR:-/tmp}/l9-pr-security-wave.XXXXXX")"
_run_wave_job() {
  local name="$1"
  local fn="run_${name}"
  (
    trap - EXIT
    set +e
    "$fn"
    echo $? >"$_wave_dir/${name}.rc"
  ) >"$_wave_dir/${name}.log" 2>&1 &
}
_run_wave_job gitleaks
_run_wave_job bandit
_run_wave_job semgrep
wait
_replay_scanner_log "$_wave_dir/gitleaks.log"
_replay_scanner_log "$_wave_dir/bandit.log"
_replay_scanner_log "$_wave_dir/semgrep.log"

run_pip_audit

note ""
note "Summary: pass=$PASS fail=$FAIL skip=$SKIP mode=$PR_SECURITY_MODE profile=$PR_SECURITY_PROFILE"
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
