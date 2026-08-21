#!/usr/bin/env bash
# Shared SSOT path resolution — source from any governance script.
#
# SSOT: the local GitHub clone at $HOME/.cursor-governance, and ONLY that clone.
# Dropbox is NOT a fallback and is NOT consulted. The clone is created once via
# `git clone https://github.com/Quantum-L9/Cursor-Governance.git ~/.cursor-governance`
# and kept fast-forward-synced every session start by governance_sync.sh. If the
# clone is missing, the fix is to (re-)clone it — never to read from Dropbox.
#
# Layout: repo-root layout only. skills/ commands/ rules/ ops/ + CANONICAL_LAW.md
# live at the clone root, so GLOBAL_COMMANDS == GOV_ROOT == $HOME/.cursor-governance
# (no nested GlobalCommands/ subfolder).
# resolve_governance_paths() exports GOV_ROOT + GLOBAL_COMMANDS.

# --- Session env for NON-LOGIN shells --------------------------------------
# setup.bootstrap.sh writes ~/.l9/cloud-session.env and appends a source line to
# ~/.bashrc and ~/.profile. Neither is read by a non-interactive, non-login
# shell — which is exactly what an agent's Bash tool spawns — so
# L9_GOVERNANCE_DIR resolved in a login shell and was unset in the tool's own
# (audit B-18). BASH_ENV cannot fix it: it has to be present in the ALREADY
# RUNNING agent process, and a setup script that ran at environment-build time
# cannot reach back into it.
#
# This lives here, in the file that already owns "where is governance", rather
# than in a second helper — two resolvers for one decision is a competing source
# of truth, and the next drift between them would be silent.
L9_DEFAULT_GOVERNANCE_DIR="$HOME/.cursor-governance"

l9_load_session_env() {
  if [ -z "${L9_GOVERNANCE_DIR:-}" ]; then
    local env_file="${L9_SESSION_ENV_FILE:-$HOME/.l9/cloud-session.env}"
    # shellcheck disable=SC1090
    [ -f "$env_file" ] && . "$env_file"
  fi
  # An unexpanded literal '$HOME' arrives from .env-format fields, which perform
  # no shell expansion. It names a directory that does not exist; refuse it.
  case "${L9_GOVERNANCE_DIR:-}" in
    *'$HOME'*|*'${HOME}'*) L9_GOVERNANCE_DIR="" ;;
  esac
  : "${L9_GOVERNANCE_DIR:=$L9_DEFAULT_GOVERNANCE_DIR}"
  export L9_GOVERNANCE_DIR
}

l9_governance_dir() {
  l9_load_session_env
  printf '%s' "$L9_GOVERNANCE_DIR"
}

resolve_governance_paths() {
  GOV_ROOT=""
  GLOBAL_COMMANDS=""
  l9_load_session_env
  local root="$HOME/.cursor-governance"
  if [ -d "$root/skills" ] && [ -f "$root/CANONICAL_LAW.md" ]; then
    GOV_ROOT="$root"
    GLOBAL_COMMANDS="$root"
    export GOV_ROOT GLOBAL_COMMANDS
    return 0
  fi
  return 1
}

resolve_governance_paths_or_exit() {
  if resolve_governance_paths; then
    return 0
  fi
  echo "ERROR: governance root not found at \$HOME/.cursor-governance." >&2
  echo "  Fix: git clone https://github.com/Quantum-L9/Cursor-Governance.git \"\$HOME/.cursor-governance\"" >&2
  echo "  Dropbox is not a fallback for this repo; do not read/write governance state there." >&2
  exit 1
}

# ssot | ssot_checkout | consumer — identity files, not $HOME/.l9 path prefix.
# shellcheck source=lib/workspace_kind.sh
_WK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$_WK_DIR/lib/workspace_kind.sh" ]; then
  # shellcheck source=lib/workspace_kind.sh
  source "$_WK_DIR/lib/workspace_kind.sh"
fi

# PE/gov isolates are git checkouts, not Cursor consumer workspaces.
# $HOME/.l9/gov-worktrees/<id> and $HOME/.l9/programs/<id>[/worktrees/...]
is_l9_isolate_workspace() {
  local ws="${1:-}"
  [ -n "$ws" ] || return 1
  python3 -c '
import os
import sys

ws = os.path.realpath(sys.argv[1])
l9 = os.path.realpath(os.path.expanduser("~/.l9"))
if ws != l9 and not ws.startswith(l9 + os.sep):
    raise SystemExit(1)
parts = os.path.relpath(ws, l9).split(os.sep)
if parts[0] == "gov-worktrees" and len(parts) >= 2:
    raise SystemExit(0)
if parts[0] == "programs" and len(parts) >= 2:
    raise SystemExit(0)
raise SystemExit(1)
' "$ws"
}

# PAIRED PREDICATE: run_pr_precommit.sh + run_pr_gate.sh. Skip consumer
# .cursor-commands / .cursor/plans / .cursor/governance on CI, partial clones,
# non-cursor surfaces, and $HOME/.l9 isolates. Machine sessionEnd/Graphiti
# checks are not covered by this skip.
# Is this machine a Cursor DESKTOP host, i.e. may we assert Cursor-only host
# artifacts (~/.cursor/hooks.json, ~/.cursor/plugins/local/l9-governance)?
#
# "~/.cursor exists and is writable" is NOT evidence: Graphiti's state directory
# creates that path on every surface, so the old proxy silently became true for
# headless adapters and made those assertions unsatisfiable off Cursor. Decide on
# the declared surface id instead. Absent a declared surface, fail closed to the
# stricter answer so a genuine Cursor machine is never let off.
#
# One definition, shared by every caller that gates a Cursor-host assertion
# (run_pr_gate.sh, validate_governance_symlinks.sh). Do not re-inline it.
is_cursor_host_surface() {
  [ -z "${L9_GOVERNANCE_SURFACE:-}" ] || [ "${L9_GOVERNANCE_SURFACE}" = "cursor" ]
}

should_skip_consumer_symlink_checks() {
  local ws="${1:-}"
  if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    return 0
  fi
  if [ ! -f "$ws/skills/AUTONOMY_MANIFEST.yaml" ] || [ ! -f "$ws/rules/RULES-MANIFEST.yaml" ]; then
    return 0
  fi
  if [ -n "${L9_GOVERNANCE_SURFACE:-}" ] && [ "${L9_GOVERNANCE_SURFACE}" != "cursor" ]; then
    return 0
  fi
  if is_l9_isolate_workspace "$ws"; then
    return 0
  fi
  return 1
}

resolve_gov_toolchain_root() {
  local ws="${1:-$(pwd)}"
  local fallback="${2:-}"
  if is_l9_isolate_workspace "$ws"; then
    local donor
    donor="$(python3 -c '
import os
import subprocess
import sys

ws = sys.argv[1]
try:
    common = subprocess.check_output(
        ["git", "-C", ws, "rev-parse", "--git-common-dir"],
        text=True,
    ).strip()
except (subprocess.CalledProcessError, FileNotFoundError):
    raise SystemExit(0)
if not common:
    raise SystemExit(0)
if not os.path.isabs(common):
    common = os.path.join(ws, common)
common = os.path.realpath(common)
donor = os.path.dirname(common) if os.path.basename(common) == ".git" else common
print(donor)
' "$ws")"
    if [ -n "$donor" ] && { [ -x "$donor/.venv/bin/python" ] || [ -x "$donor/.venv/bin/python3" ]; }; then
      printf '%s\n' "$donor"
      return 0
    fi
    if [ -x "$HOME/.cursor-governance/.venv/bin/python" ] || [ -x "$HOME/.cursor-governance/.venv/bin/python3" ]; then
      printf '%s\n' "$HOME/.cursor-governance"
      return 0
    fi
  fi
  if [ -n "$fallback" ]; then
    printf '%s\n' "$fallback"
    return 0
  fi
  printf '%s\n' "$ws"
}

bind_isolate_toolchain() {
  local ws="${1:-}"
  local fallback="${2:-}"
  if ! is_l9_isolate_workspace "$ws"; then
    return 0
  fi
  GOV_TOOLCHAIN_ROOT="$(resolve_gov_toolchain_root "$ws" "$fallback")"
  export GOV_TOOLCHAIN_ROOT
  export UV_PROJECT="$GOV_TOOLCHAIN_ROOT"
  if [ -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/python" ]; then
    export PATH="$GOV_TOOLCHAIN_ROOT/.venv/bin:$PATH"
  elif [ -x "$GOV_TOOLCHAIN_ROOT/.venv/bin/python3" ]; then
    export PATH="$GOV_TOOLCHAIN_ROOT/.venv/bin:$PATH"
  fi
  echo "OK: isolate toolchain bound to $GOV_TOOLCHAIN_ROOT (UV_PROJECT)"
}
