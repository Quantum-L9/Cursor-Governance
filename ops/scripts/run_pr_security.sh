#!/usr/bin/env bash
# Local PR security gate — changed-files only (gitleaks + bandit + semgrep + pip-audit).
# Full-tree scans belong to nightly CI, not make pr / pre-commit.
#
# Version authority: l9-ci-core's toolchain lock
# (.github/actions/install-consumer-ci/toolchain-lock.json) owns every CI tool
# version it lists, including bandit, pip-audit and gitleaks; the SDK does not
# override it. requirements.txt mirrors that lock and this script reads the
# bandit/pip-audit pins from it. Semgrep: SDK policy >=1.100.0,<2.0.0.
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
# Pins: Python tools from requirements.txt (a mirror of Core's lock). gitleaks is a
# machine CLI pinned once, by the bootstrap that installs it
# (bootstrap_agent_environment.sh, mirroring l9-ci-core security.yml). Read the
# pin from there instead of keeping a second literal that can drift.
REQ_FILE="${REQ_FILE:-$GOV_ROOT/requirements.txt}"
pin_from_req() {
  local name="$1"
  awk -F== -v n="$name" '$1==n {print $2; exit}' "$REQ_FILE"
}
GITLEAKS_PIN="$(sed -nE 's/^GITLEAKS_PIN="([^"]+)".*/\1/p' \
  "$SCRIPT_DIR/bootstrap_agent_environment.sh" 2>/dev/null | head -1)"
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
  current_work/ C_GOV_FILES/
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

uvx_failed_to_provision() { # $1 = captured uvx output
  # True when uv could not FETCH/RESOLVE/INSTALL the package, as opposed to the
  # tool running and reporting findings. uv exits 1 for both, so a scanner that
  # never ran would otherwise be published as a security finding — inventing a
  # vulnerability out of a network fault and teaching readers to discount the
  # next real one. Matched on uv's own diagnostics, which name the failure.
  case "$1" in
    *"Failed to fetch"* | *"Failed to download"* | *"Failed to install"* | \
      *"error sending request"* | *"No solution found"* | *"Failed to resolve"* | \
      *"invalid peer certificate"*)
      return 0
      ;;
  esac
  return 1
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
  # empty (a scratch-only or docs-only PR).
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
# The bootstrap installs gitleaks into ~/.local/bin and puts that directory on
# PATH only for its own process, so a later gate shell whose PATH lacks it
# reported an installed binary as NOT INSTALLED. Resolve the install location
# directly when PATH does not carry it.
resolve_gitleaks() {
  if have gitleaks; then
    command -v gitleaks
  elif [[ -x "$HOME/.local/bin/gitleaks" ]]; then
    printf '%s\n' "$HOME/.local/bin/gitleaks"
  else
    return 1
  fi
}

run_gitleaks() {
  local gitleaks_bin
  if ! gitleaks_bin="$(resolve_gitleaks)"; then
    missing_tool gitleaks "bash ops/scripts/bootstrap_agent_environment.sh --surface local"
    return 0
  fi
  local ver
  # Output looks like "gitleaks version 8.24.3" — take the last token, not a space-stripped blob.
  ver="$("$gitleaks_bin" version 2>/dev/null | head -1 | awk '{print $NF}' || true)"
  if [[ -z "$GITLEAKS_PIN" ]]; then
    note "WARN: gitleaks pin unreadable from bootstrap_agent_environment.sh; version $ver not checked"
  elif [[ -n "$ver" && "$ver" != "$GITLEAKS_PIN" ]]; then
    note "WARN: gitleaks $ver at $gitleaks_bin (expected $GITLEAKS_PIN, pinned in bootstrap_agent_environment.sh)"
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
  if "$gitleaks_bin" dir --help >/dev/null 2>&1; then
    if ! "$gitleaks_bin" dir "${extra[@]}" "$_scan_tmp"; then
      status=1
    fi
  else
    if ! "$gitleaks_bin" detect --no-git "${extra[@]}" --source "$_scan_tmp"; then
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
  local -a py=() py_rel=() fixture_rel=()
  local f fixture_out
  for f in "${CHANGED[@]}"; do
    [[ "$f" == *.py ]] && py_rel+=("$f")
  done
  if [[ ${#py_rel[@]} -eq 0 ]]; then
    skip "bandit (no changed .py files)"
    return 0
  fi
  # Declared expect-fail fixtures (ops/ci_parity/expect_fail_fixtures.json):
  # their named rules must fire and do not block; everything else is judged as
  # before. An unreadable manifest fails closed.
  if ! fixture_out="$(python3 "$GOV_ROOT/ops/ci_parity/fixtures.py" split --repo "$WS" "${py_rel[@]}")"; then
    fail "bandit: the expect-fail fixture manifest could not be read"
    return 0
  fi
  # A read loop, not mapfile: stock macOS Bash 3.2 has no mapfile, and a failed
  # mapfile under `set +e` would leave the list empty and scan fixtures as ordinary files.
  while IFS= read -r f; do
    [[ -n "$f" ]] && fixture_rel+=("$f")
  done <<<"$fixture_out"
  for f in "${py_rel[@]}"; do
    [[ " ${fixture_rel[*]} " == *" $f "* ]] || py+=("$WS/$f")
  done
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
  # bandit's exit codes separate the two outcomes this gate must never conflate:
  # 0 = ran, clean. 1 = ran, found issues. Anything else = it did not run — and
  # run_uvx_pkg adds its own non-zero when uvx cannot fetch the pinned package
  # at all. Reporting that as "bandit reported issues" invents a security
  # finding out of a network fault, sends the reader hunting for a
  # vulnerability that does not exist, and teaches them to discount the next
  # real bandit failure. A scanner that could not run is missing_tool, which is
  # still a gate failure in gate mode but says the true reason.
  local bandit_out bandit_rc=0
  if [[ ${#py[@]} -gt 0 ]]; then
    bandit_out="$(run_uvx_pkg "bandit==${BANDIT_PIN}" bandit "${py[@]}" "$sev_flag" -q 2>&1)" \
      || bandit_rc=$?
    [ -n "$bandit_out" ] && printf '%s\n' "$bandit_out"
    if [[ "$bandit_rc" -eq 0 ]]; then
      ok "bandit==$BANDIT_PIN (${#py[@]} file(s), severity>=$BANDIT_SEVERITY)"
    elif uvx_failed_to_provision "$bandit_out"; then
      # uv exits 1 when it cannot fetch or resolve the package — the SAME code
      # bandit uses for "issues found". Exit status alone cannot tell them apart,
      # so the provisioning signature in uv's own output is what separates them.
      missing_tool "bandit==$BANDIT_PIN" \
        "uvx could not provision the pinned package — check network/TLS to PyPI"
      return 0
    else
      fail "bandit reported issues in changed Python files"
    fi
  fi
  [[ ${#fixture_rel[@]} -eq 0 ]] && return 0
  run_bandit_fixtures "$sev_flag" "${fixture_rel[@]}"
}

# Bandit on declared expect-fail fixture files, judged by ops/ci_parity/fixtures.py:
# every named rule must fire (else FAIL), a named rule never blocks, and any
# other finding blocks as it would anywhere else.
run_bandit_fixtures() {
  local sev_flag="$1"
  shift
  local -a abs=()
  local f report fx_out fx_rc=0 bandit_out bandit_rc=0
  for f in "$@"; do abs+=("$WS/$f"); done
  report="$(mktemp)"
  bandit_out="$(run_uvx_pkg "bandit==${BANDIT_PIN}" bandit "${abs[@]}" "$sev_flag" -q -f json -o "$report" 2>&1)" \
    || bandit_rc=$?
  if [[ "$bandit_rc" -ne 0 && "$bandit_rc" -ne 1 ]] || uvx_failed_to_provision "$bandit_out"; then
    [ -n "$bandit_out" ] && printf '%s\n' "$bandit_out"
    rm -f "$report"
    missing_tool "bandit==$BANDIT_PIN" "bandit did not run on the declared fixtures (exit $bandit_rc)"
    return 0
  fi
  fx_out="$(python3 "$GOV_ROOT/ops/ci_parity/fixtures.py" bandit --repo "$WS" --report "$report" "$@" 2>&1)" \
    || fx_rc=$?
  rm -f "$report"
  [ -n "$fx_out" ] && printf '%s\n' "$fx_out"
  if [[ "$fx_rc" -eq 0 ]]; then
    ok "bandit==$BANDIT_PIN declared expect-fail fixtures (${#abs[@]} file(s)): every named rule fired, nothing else"
  else
    fail "bandit: declared expect-fail fixtures — a named rule did not fire or an undeclared finding is present"
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
  # Resolve one explicit binary path before running, never the mutable PATH
  # link: the make pr reader wave runs the ci-parity job beside this one, and
  # it re-points ~/.local/bin/semgrep when the pin moves. First the ci-parity
  # pinned binary (state.json path, its own per-version environment); else the
  # PATH semgrep, resolved to its real path once.
  local semgrep_bin="" gov_py="$GOV_ROOT/.venv/bin/python"
  if [[ -x "$gov_py" && -f "$GOV_ROOT/ops/ci_parity/install.py" ]]; then
    # Exit 1 means no pinned binary is installed: an answer, so fall through.
    if ! semgrep_bin="$("$gov_py" "$GOV_ROOT/ops/ci_parity/install.py" --resolve semgrep 2>/dev/null)"; then
      semgrep_bin=""
    fi
  fi
  if [[ -z "$semgrep_bin" ]] && have semgrep; then
    # Portable realpath (BSD readlink has no -f); the path is passed as argv.
    semgrep_bin="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$(command -v semgrep)")"
  fi
  if [[ -n "$semgrep_bin" && -x "$semgrep_bin" ]]; then
    ver="$("$semgrep_bin" --version 2>/dev/null | head -1 || true)"
    note "semgrep: $ver at $semgrep_bin (SDK supported range >=1.100.0,<2.0.0)"
    if "$semgrep_bin" --error --quiet --metrics=off "${configs[@]}" "${targets[@]}"; then
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
      uv.lock|pyproject.toml|requirements.txt|requirements.lock|requirements-*.txt|constraints.txt) need=1 ;;
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
  local audit_rc=0
  (
    cd "$WS"
    if [[ -f uv.lock ]]; then
      # Audit this workspace lock. Do not sync the project environment:
      # UV_PROJECT_ENVIRONMENT is the governance venv, and a sync reinstalls
      # the sealed memory wheel. `uv export --frozen` reads the lock only.
      # run_pr_gate.sh exports UV_LOCKED=1, which uv refuses beside --frozen,
      # so the export drops it; the gate's uv-lock wave already checked the lock.
      req="$(mktemp "${TMPDIR:-/tmp}/l9-pip-audit-req.XXXXXX")"
      trap 'rm -f "$req"' EXIT
      if ! env -u UV_LOCKED uv export --frozen --no-emit-project --no-hashes \
        --format requirements.txt -o "$req"; then
        echo "pip-audit: uv export failed for $WS/uv.lock" >&2
        exit 2
      fi
      run_uvx_pkg "pip-audit==${PIP_AUDIT_PIN}" pip-audit -r "$req" --progress-spinner off
    elif [[ -f requirements.txt ]]; then
      run_uvx_pkg "pip-audit==${PIP_AUDIT_PIN}" pip-audit -r requirements.txt --progress-spinner off
    elif [[ -f requirements.lock ]]; then
      run_uvx_pkg "pip-audit==${PIP_AUDIT_PIN}" pip-audit -r requirements.lock --progress-spinner off
    elif [[ -f requirements-ci.txt ]]; then
      run_uvx_pkg "pip-audit==${PIP_AUDIT_PIN}" pip-audit -r requirements-ci.txt --progress-spinner off
    else
      echo "pip-audit: no uv.lock, requirements.txt, requirements.lock, or requirements-ci.txt in $WS" >&2
      exit 2
    fi
  ) && audit_rc=0 || audit_rc=$?
  if [[ "$audit_rc" -eq 0 ]]; then
    ok "pip-audit==$PIP_AUDIT_PIN"
  elif [[ "$audit_rc" -eq 2 ]]; then
    fail "pip-audit could not run (no supported lockfile)"
  else
    fail "pip-audit found vulnerabilities"
  fi
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
