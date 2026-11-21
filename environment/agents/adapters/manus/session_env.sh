#!/usr/bin/env bash
# Manus session-environment binding — the host half of the adapter's SessionStart.
#
# Manus exposes no SessionStart hook, so install.sh is the session start. Two
# machine-level facts every later gate assumes cannot be established by a
# per-session project instruction, so this script owns them:
#
#   1. $HOME/.cursor-governance resolves to an authorized governance checkout.
#      resolve_governance_paths.sh refuses anything else, and the
#      `symlinks-check` pre-commit hook is pass_filenames:false — so a missing
#      SSOT fails every `make pr` regardless of the change set, naming a path
#      the session never created.
#   2. L9_GOVERNANCE_SURFACE is declared. Unset makes is_cursor_host_surface()
#      fail closed to Cursor, and that same hook then demands Cursor desktop
#      plugin links on a Manus host.
#
# Provisioning is delegated to ops/scripts/governance_sync.sh, the owner that
# already performs the guarded clone-if-missing and fast-forward. The adapter
# implements no clone of its own and never replaces an existing checkout. A
# symlink is reported, not repointed: it follows whatever branch its target is
# on, so it cannot stay at main while that checkout develops, and the wiring
# check would fail on the first feature branch.
#
# --check is observational: it reports and mutates nothing. Apply mode is
# idempotent. Both are fail-open: the session continues, and the projection
# binding report remains the enforcement point.
#
# Usage:
#   session_env.sh [--governance <dir>] [--check] [--quiet]
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOVERNANCE="$(cd "$SCRIPT_DIR/../../../.." 2>/dev/null && pwd -P)" || GOVERNANCE=""
CHECK=0
QUIET=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --governance) GOVERNANCE="${2:?--governance needs a path}"; shift 2 ;;
    --check) CHECK=1; shift ;;
    --quiet) QUIET=1; shift ;;
    -h|--help)
      sed -n '2,31p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      printf 'session-env: unknown argument %s\n' "$1" >&2
      exit 2
      ;;
  esac
done
say() {
  [ "$QUIET" = "1" ] || printf 'SESSION-ENV: %s\n' "$*" >&2
}
HOME_REAL="$(cd "${HOME:-}" 2>/dev/null && pwd -P)" || {
  printf 'session-env: HOME is not a directory\n' >&2
  exit 1
}
GOVERNANCE="$(cd "$GOVERNANCE" 2>/dev/null && pwd -P)" || GOVERNANCE=""
[ -f "$GOVERNANCE/CANONICAL_LAW.md" ] || {
  printf 'session-env: no governance SSOT at %s\n' "${GOVERNANCE:-<unset>}" >&2
  exit 1
}
SSOT="$HOME_REAL/.cursor-governance"
SYNC="$GOVERNANCE/ops/scripts/governance_sync.sh"
ENV_FILE="$HOME_REAL/.l9/cloud-session.env"
MARKER="# L9 Manus surface binding"
ATTENTION=0
real() {
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1" 2>/dev/null \
    || printf '%s' "$1"
}
valid_checkout() {
  [ -f "$1/CANONICAL_LAW.md" ] && [ -d "$1/skills" ]
}
# --- 1) Machine SSOT path ---------------------------------------------------
if [ -L "$SSOT" ]; then
  say "ssot=SYMLINK path=$SSOT -> $(real "$SSOT"); a link cannot stay on main while its target branches — replace it with a clone"
  ATTENTION=1
elif [ -d "$SSOT" ]; then
  if valid_checkout "$SSOT"; then
    say "ssot=OK path=$SSOT (checkout present; freshness is /ff's job)"
  else
    say "ssot=INVALID path=$SSOT is a directory but not a governance checkout; left unchanged"
    ATTENTION=1
  fi
elif [ "$CHECK" = "1" ]; then
  say "ssot=ABSENT path=$SSOT (apply mode provisions it through governance_sync.sh)"
  ATTENTION=1
elif [ ! -f "$SYNC" ]; then
  say "ssot=ABSENT path=$SSOT (no governance_sync.sh at $SYNC; cannot provision)"
  ATTENTION=1
elif CURSOR_GOVERNANCE_DIR="$SSOT" GOVERNANCE_SYNC_PUSH=0 bash "$SYNC" >/dev/null 2>&1 \
  && valid_checkout "$SSOT"; then
  # The push half is disabled: a session start reads governance, it does not publish.
  say "ssot=PROVISIONED path=$SSOT (via governance_sync.sh)"
else
  say "ssot=FAILED could not provision $SSOT through governance_sync.sh"
  ATTENTION=1
fi
# --- 2) Declared surface ----------------------------------------------------
surface_of() {
  sed -n 's/^export L9_GOVERNANCE_SURFACE=//p' "$1" 2>/dev/null | head -1
}
write_env() {
  local example="$GOVERNANCE/environment/agents/adapters/manus/environment.env.example"
  [ -f "$example" ] || return 1
  mkdir -p "$(dirname "$ENV_FILE")" 2>/dev/null || return 1
  {
    printf '%s\n' "$MARKER (written by the Manus adapter; non-secret only)."
    printf '%s\n' "# Derived from environment.env.example — edit that file, not this one."
    printf '%s\n' "# No credential, bearer, provider URL or capability-broker address belongs here."
    # The example is the one source of truth for the non-secret assignment set;
    # this writer only projects it into a shell file. Secret-shaped keys are
    # filtered even though the example declares none, so a future edit cannot
    # quietly turn this into a credential carrier.
    while IFS= read -r line; do
      case "$line" in
        ''|'#'*) continue ;;
        *=*) ;;
        *) continue ;;
      esac
      key="${line%%=*}"
      value="${line#*=}"
      case "$key" in
        *SECRET*|*TOKEN*|*PASSWORD*|GRAPHITI_MCP_URL|L9_CAPABILITY_BROKER_URL) continue ;;
      esac
      printf 'export %s=%s\n' "$key" "$value"
    done <"$example"
    # The example deliberately omits this: a hosted environment field performs
    # no shell expansion, so $HOME there names a directory that cannot exist.
    # This file is sourced by a shell, so the absolute path is exact.
    printf "export L9_GOVERNANCE_DIR='%s'\n" "$GOVERNANCE"
    printf '%s\n' "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
    printf '%s\n' "unset GRAPHITI_MCP_URL GRAPHITI_MCP_TOKEN"
    printf '%s\n' "unset AUTH0_CLIENT_SECRET L9_MEMORY_OAUTH_CLIENT_SECRET"
    printf '%s\n' "unset L9_MEMORY_OAUTH_ACCESS_TOKEN L9_MEMORY_OAUTH_REFRESH_TOKEN"
    printf '%s\n' "unset INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
    printf '%s\n' "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
    printf '%s\n' "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
  } >"$ENV_FILE"
}
if [ -f "$ENV_FILE" ] && ! grep -qF "$MARKER" "$ENV_FILE" 2>/dev/null; then
  # A file this adapter did not write is an operator's, not ours to replace.
  say "env=FOREIGN path=$ENV_FILE (no adapter marker; left unchanged; surface=$(surface_of "$ENV_FILE"))"
  [ "$(surface_of "$ENV_FILE")" = "manus" ] || ATTENTION=1
elif [ "$CHECK" = "1" ]; then
  if [ -f "$ENV_FILE" ]; then
    say "env=PRESENT path=$ENV_FILE surface=$(surface_of "$ENV_FILE")"
    [ "$(surface_of "$ENV_FILE")" = "manus" ] || ATTENTION=1
  else
    say "env=ABSENT path=$ENV_FILE (apply mode writes it)"
    ATTENTION=1
  fi
elif write_env; then
  say "env=WROTE path=$ENV_FILE surface=manus"
else
  say "env=FAILED could not write $ENV_FILE"
  ATTENTION=1
fi
# --- 3) Non-login shells ----------------------------------------------------
# The agent's Bash tool spawns a non-login, non-interactive shell, which reads
# neither profile. resolve_governance_paths.sh sources the env file directly, so
# this line only serves interactive shells; it is added, never duplicated.
if [ -f "$ENV_FILE" ]; then
  for profile in "$HOME_REAL/.bashrc" "$HOME_REAL/.profile"; do
    [ -f "$profile" ] || : >"$profile" 2>/dev/null
    if grep -qF 'cloud-session.env' "$profile" 2>/dev/null; then
      say "profile=OK path=$profile"
    elif [ "$CHECK" = "1" ]; then
      say "profile=ABSENT path=$profile (apply mode adds the source line)"
      ATTENTION=1
    elif printf '%s\n' '. "$HOME/.l9/cloud-session.env"  # L9 governed session env' >>"$profile" 2>/dev/null; then
      say "profile=SOURCED path=$profile"
    else
      say "profile=FAILED could not update $profile"
      ATTENTION=1
    fi
  done
fi
if [ "$ATTENTION" = "1" ]; then
  say "result=ATTENTION"
else
  say "result=READY"
fi
exit 0
