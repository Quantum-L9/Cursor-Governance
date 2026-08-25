#!/usr/bin/env bash
# Declarative, idempotent Claude Code (the `claude` CLI) plugin setup.
#
# Portability note: Claude Code plugin state lives in $HOME/.claude/ (user scope),
# which sits outside any git repo and is NOT portable — ~/.claude.json also carries
# a live OAuth session (oauthAccount, machineID, userID) that must never be checked
# into git. ~/.claude/plugins/ is a local cache of full marketplace clones (100s of
# MB) and is likewise not something to vendor here. What IS portable and safe to
# version-control is the small *declaration* of desired state below.
#
# Enablement is now per-class, not uniformly user-scoped (environment/plugins/,
# see rules/84-cursor-governance-wiring.mdc v3.0.0 + README.md in that dir). Only
# the marketplace clone cache under ~/.claude/plugins/ stays purely local/user-scope
# for every repo — CORE_PLUGINS below install at `-s user` (every governed repo gets
# them), while CLASS_PLUGINS install at `-s project`, writing to
# <workspace>/.claude/settings.json, and only for the workspace class each entry
# is gated to (per environment/plugins/exceptions.yaml classification).
#
# Activation: Cursor-Governance sessionStart + setup_workspace_symlinks.sh call this
# in --quiet mode whenever a workspace is wired, passing --workspace explicitly so
# project-scope installs land in the right repo (sessionStart's cwd is the hooks
# dir, not the open workspace — see session_start_bootstrap.sh's CURSOR_PROJECT_DIR).
#
# Usage:
#   bash ops/scripts/setup_claude_code_plugins.sh                        # cwd = workspace
#   bash ops/scripts/setup_claude_code_plugins.sh --workspace /path/repo # explicit workspace
#   bash ops/scripts/setup_claude_code_plugins.sh --quiet                # hook-safe: no update, fail-open
#   bash ops/scripts/setup_claude_code_plugins.sh --update               # force claude update first
#
# Requires: `claude` (Claude Code CLI) already installed and reachable on PATH.
# Install docs: https://docs.claude.com/en/docs/claude-code
# Note: marketplace schemas advance with the CLI — keep Claude Code current.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLASSIFIER="$SCRIPT_DIR/../hooks/workspace_open_plugin_loader.py"

QUIET=0
FORCE_UPDATE=0
WORKSPACE_DIR="$(pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --quiet|-q) QUIET=1; shift ;;
    --update) FORCE_UPDATE=1; shift ;;
    --workspace)
      WORKSPACE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,32p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done

log() {
  if [ "$QUIET" -eq 0 ]; then
    echo "$@"
  fi
}

# Project-scope installs write <workspace>/.claude/settings.json. Writing that
# while `make pr` runs lands inside a pre-commit hook's window and is reported
# as "files were modified by this hook" against a hook that never wrote. Yield
# to the repo-write lock: a --quiet (hook-driven) run skips, an explicit run
# warns and proceeds.
LOCK_LIB="$SCRIPT_DIR/lib/repo_write_lock.sh"
if [ -d "$WORKSPACE_DIR" ]; then
  WORKSPACE_DIR="$(cd "$WORKSPACE_DIR" && pwd)"
fi
if [ -f "$LOCK_LIB" ]; then
  # shellcheck source=lib/repo_write_lock.sh
  . "$LOCK_LIB"
  export L9_REPO_WRITE_LOCK_LABEL="setup_claude_code_plugins"
  if ! repo_write_lock_acquire "$WORKSPACE_DIR" "${L9_PLUGINS_LOCK_WAIT_S:-45}"; then
    if [ "$QUIET" -eq 1 ]; then
      echo "claude-plugins: skipped ($(repo_write_lock_skip_note "$WORKSPACE_DIR"))"
      exit 0
    fi
    echo "WARN: $(repo_write_lock_skip_note "$WORKSPACE_DIR") — reconciling anyway (explicit run)" >&2
  else
    trap 'repo_write_lock_release' EXIT
  fi
fi

# Prefer the native install (~/.local/bin) over a stale npm-global copy.
if [ -x "$HOME/.local/bin/claude" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# --- Classification: which capabilities does this workspace get? -----------
# Single source of truth for odoo_plasticos/aws_infra/zep_memory/core_default
# lives in workspace_open_plugin_loader.py (shared with the Cursor workspaceOpen
# hook) — not re-implemented here. Fails open to core_default on any error.
classify_workspace_class() {
  local ws="$1"
  if [ -f "$CLASSIFIER" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$CLASSIFIER" --classify "$ws" 2>/dev/null || echo "core_default"
  else
    echo "core_default"
  fi
}

WORKSPACE_CLASS="$(classify_workspace_class "$WORKSPACE_DIR")"

# --- Desired state (declarative SSOT) ---------------------------------------
# The desired plugin state is DECLARED in plugins.desired.json (schema
# l9.claude-plugins-desired.v1) next to the Claude adapter — this script is the
# imperative fallback that converges the machine onto that declaration. Do not
# add plugin ids here; edit the JSON. Parallel arrays (not associative — macOS
# ships bash 3.2, no `declare -A` support).
DESIRED_JSON="$SCRIPT_DIR/../../environment/agents/adapters/claude-code/plugins.desired.json"

read_desired() {
  # Emits sections separated by markers so bash 3.2 can split them.
  python3 - "$DESIRED_JSON" "$WORKSPACE_CLASS" <<'PYEOF'
import json, sys
path, cls = sys.argv[1], sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
core = data.get("core") or {}
class_cfg = (data.get("classes") or {}).get(cls) or {}
def emit(tag, values):
    print(f"##{tag}")
    for value in values:
        print(value)
emit("CORE_MARKETPLACES", core.get("marketplaces") or [])
emit("CORE_PLUGINS", core.get("plugins") or [])
emit("CLASS_MARKETPLACES", class_cfg.get("marketplaces") or [])
emit("CLASS_PLUGINS", class_cfg.get("plugins") or [])
emit("RETIRED_USER_SCOPE", data.get("retired_user_scope") or [])
PYEOF
}

if [ ! -f "$DESIRED_JSON" ] || ! command -v python3 >/dev/null 2>&1; then
  if [ "$QUIET" -eq 1 ]; then
    echo "claude-plugins: skipped (plugins.desired.json or python3 unavailable)"
    exit 0
  fi
  echo "ERROR: cannot read plugin desired state: $DESIRED_JSON" >&2
  exit 1
fi

CORE_MARKETPLACE_REPOS=()
CORE_PLUGINS=()
CLASS_MARKETPLACES=()
CLASS_PLUGINS=()
RETIRED_USER_SCOPE_PLUGINS=()
section=""
while IFS= read -r line; do
  case "$line" in
    "##"*) section="${line##\#\#}" ;;
    "") ;;
    *)
      case "$section" in
        CORE_MARKETPLACES) CORE_MARKETPLACE_REPOS+=("$line") ;;
        CORE_PLUGINS) CORE_PLUGINS+=("$line") ;;
        CLASS_MARKETPLACES) CLASS_MARKETPLACES+=("$line") ;;
        CLASS_PLUGINS) CLASS_PLUGINS+=("$line") ;;
        RETIRED_USER_SCOPE) RETIRED_USER_SCOPE_PLUGINS+=("$line") ;;
      esac
      ;;
  esac
done <<EOF
$(read_desired)
EOF

if [ "${#CORE_PLUGINS[@]}" -eq 0 ]; then
  if [ "$QUIET" -eq 1 ]; then
    echo "claude-plugins: skipped (empty desired state)"
    exit 0
  fi
  echo "ERROR: plugin desired state parsed empty from $DESIRED_JSON" >&2
  exit 1
fi
# -----------------------------------------------------------------------------

# marketplace short name (last path segment) for `marketplace update`
marketplace_name() {
  echo "${1##*/}"
}

plugin_name() {
  # building-with-zep@zep → building-with-zep
  echo "${1%%@*}"
}

# Resolve the marketplaces actually desired for WORKSPACE_CLASS (class plugins
# were already filtered by read_desired).
MARKETPLACE_REPOS=("${CORE_MARKETPLACE_REPOS[@]}")
if [ "${#CLASS_MARKETPLACES[@]}" -gt 0 ]; then
  for mp in "${CLASS_MARKETPLACES[@]}"; do
    known=0
    for existing in "${MARKETPLACE_REPOS[@]}"; do
      [ "$existing" = "$mp" ] && known=1
    done
    [ "$known" -eq 0 ] && MARKETPLACE_REPOS+=("$mp")
  done
fi
# bash 3.2 (macOS default) treats "${empty_array[@]}" as unbound under `set -u`,
# so CLASS_PLUGINS (often empty, e.g. core_default) is appended conditionally.
PLUGINS=("${CORE_PLUGINS[@]}")
if [ "${#CLASS_PLUGINS[@]}" -gt 0 ]; then
  PLUGINS+=("${CLASS_PLUGINS[@]}")
fi

STAMP_DIR="$HOME/.claude/plugins"
# Per-class stamp: switching between two differently-classed workspaces on the
# same machine must re-check (different desired state), but repeated runs on
# the *same* workspace class stay a no-op — this is what Phase 7 requires.
STAMP_FILE="$STAMP_DIR/.l9-plugin-desired-hash-${WORKSPACE_CLASS}"
DESIRED_HASH="$(printf '%s\n' "${MARKETPLACE_REPOS[@]}" "${PLUGINS[@]}" | shasum -a 256 | awk '{print $1}')"

list_installed() {
  claude plugin list 2>/dev/null || true
}

marketplace_known() {
  local name="$1"
  claude plugin marketplace list 2>/dev/null | grep -Fqi "$name"
}

all_desired_installed() {
  local installed name plugin
  installed="$(list_installed)"
  # "No plugins installed" or empty → not satisfied
  if [ -z "$installed" ] || echo "$installed" | grep -qi 'No plugins installed'; then
    return 1
  fi
  for plugin in "${PLUGINS[@]}"; do
    name="$(plugin_name "$plugin")"
    if ! echo "$installed" | grep -Fqi "$name"; then
      return 1
    fi
  done
  return 0
}

ensure_marketplace() {
  local repo="$1"
  local name
  name="$(marketplace_name "$repo")"
  if marketplace_known "$name"; then
    log "Marketplace update: $name"
    claude plugin marketplace update "$name" || {
      echo "WARN: marketplace update failed: $name" >&2
      return 0
    }
    return 0
  fi
  log "Marketplace add: $repo"
  if ! claude plugin marketplace add "$repo"; then
    echo "WARN: marketplace add failed: $repo" >&2
    return 0
  fi
}

if ! command -v claude >/dev/null 2>&1; then
  if [ "$QUIET" -eq 1 ]; then
    # sessionStart must not fail closed on missing Claude CLI
    exit 0
  fi
  echo "ERROR: 'claude' CLI not found on PATH." >&2
  echo "  Install: https://docs.claude.com/en/docs/claude-code" >&2
  echo "  (If installed via nvm-managed Node, add that Node's bin/ dir to PATH.)" >&2
  exit 1
fi

log "Claude Code CLI: $(command -v claude) ($(claude --version 2>/dev/null || echo unknown))"
log "Workspace: $WORKSPACE_DIR (class: $WORKSPACE_CLASS)"


# Skill projection is owned by the claude_projection engine
# (ops/scripts/claude_projection.py) — this script converges plugins only.

# Migration cleanup runs unconditionally, ahead of the per-class stamp fast path
# below, so a stamped/already-correct workspace can't mask a stale user-scope
# install left over from before Phase 7 forever.
for plugin in "${RETIRED_USER_SCOPE_PLUGINS[@]}"; do
  name="$(plugin_name "$plugin")"
  if list_installed | grep -Fqi "$name"; then
    log "Migration cleanup: removing stale user-scope install: $plugin"
    claude plugin uninstall -s user -y "$name" 2>/dev/null \
      || echo "WARN: migration cleanup uninstall failed (may not be at user scope): $plugin" >&2
  fi
done

# Fast path: desired set already present and stamp matches → nothing to do.
mkdir -p "$STAMP_DIR"
if [ -f "$STAMP_FILE" ] && [ "$(cat "$STAMP_FILE" 2>/dev/null || true)" = "$DESIRED_HASH" ] && all_desired_installed; then
  log "OK: Claude Code plugins already match Cursor-Governance desired state (class: $WORKSPACE_CLASS)"
  [ "$QUIET" -eq 1 ] || claude plugin list
  exit 0
fi

# Self-heal: old Claude Code versions ship stale/retired default model IDs and
# reject newer marketplace schemas. Keep CLI current on interactive/--update runs.
# Skip on --quiet (sessionStart) unless --update; network update is too slow for hooks.
if [ "$QUIET" -eq 0 ] || [ "$FORCE_UPDATE" -eq 1 ]; then
  log "Checking for Claude Code updates..."
  claude update || echo "WARN: 'claude update' failed — continuing with current version" >&2
  log ""
fi

for repo in "${MARKETPLACE_REPOS[@]}"; do
  ensure_marketplace "$repo"
done

log ""
for plugin in "${CORE_PLUGINS[@]}"; do
  log "Plugin (user scope): $plugin"
  if ! claude plugin install -s user "$plugin"; then
    echo "WARN: plugin install failed: $plugin" >&2
  fi
done

if [ "${#CLASS_PLUGINS[@]}" -gt 0 ]; then
  log ""
  log "Class-gated plugins for '$WORKSPACE_CLASS' (project scope -> $WORKSPACE_DIR/.claude/settings.json):"
  for plugin in "${CLASS_PLUGINS[@]}"; do
    log "Plugin (project scope): $plugin"
    if ! (cd "$WORKSPACE_DIR" && claude plugin install -s project "$plugin"); then
      echo "WARN: plugin install failed: $plugin" >&2
    fi
  done
fi

if all_desired_installed; then
  printf '%s\n' "$DESIRED_HASH" > "$STAMP_FILE"
  log ""
  log "=== Installed plugins ==="
  [ "$QUIET" -eq 1 ] || claude plugin list
  exit 0
fi

if [ "$QUIET" -eq 1 ]; then
  # Fail-open for sessionStart — stamp absent so next session retries
  rm -f "$STAMP_FILE" 2>/dev/null || true
  exit 0
fi

echo "ERROR: Claude Code plugins still missing after reconcile." >&2
claude plugin list >&2 || true
exit 1
