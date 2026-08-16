#!/usr/bin/env bash
# IDE-profile adapter: Cursor (and VS Code-compatible editors).
#
# Two reconciliations, at two different scopes — the split is load-bearing:
#
#   1. Extensions, MACHINE scope. Installed via `cursor --install-extension`,
#      stamped in $HOME/.cursor/.l9-ide-desired-hash. One stamp for the whole
#      machine, because extensions are not per-repo.
#   2. Workspace settings, REPO scope. Merged into <workspace>/.vscode/settings.json,
#      stamped in <workspace>/.vscode/.l9-ide-desired-hash. One stamp per repo,
#      because the merge has to remember which keys it owns in THAT repo.
#
# Collapsing these into one stamp would either reinstall extensions on every new
# repo or forget managed keys, so the two stamps stay separate.
#
# Per-language formatter bindings are rendered from environment/ide/policy.json
# (ownership) through environment/ide/render.cursor.json (extension IDs). The
# settings.*.json payloads carry only keys with no ownership semantics.
#
# Usage:
#   bash adapters/cursor.sh WORKSPACE CLASS [--dry-run] [--force] [--quiet]
#
# Contract with the dispatcher:
#   stdout: "ext=<state> settings=<state>"
#   exit 0 on success; nonzero on a real error (the dispatcher decides fail-open).

set -euo pipefail

WORKSPACE="${1:-}"
WS_CLASS="${2:-}"
shift 2 2>/dev/null || true

DRY_RUN=0
FORCE=0
QUIET=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --quiet|-q) QUIET=1 ;;
  esac
done

[ -n "$WORKSPACE" ] && [ -n "$WS_CLASS" ] || {
  echo "usage: cursor.sh WORKSPACE CLASS [--dry-run] [--force] [--quiet]" >&2
  exit 2
}
[ -d "$WORKSPACE" ] || { echo "not a directory: $WORKSPACE" >&2; exit 2; }

# Adapter chatter goes to stderr: stdout carries the state line the dispatcher parses.
log() { [ "$QUIET" -eq 0 ] && echo "$@" >&2; return 0; }
die() { echo "ERROR: $1" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=../resolve_governance_paths.sh
. "$SCRIPT_DIR/../resolve_governance_paths.sh"
resolve_governance_paths || die "governance root not found at \$HOME/.cursor-governance"

IDE_DIR="${L9_IDE_DIR:-$GLOBAL_COMMANDS/environment/ide}"
[ -d "$IDE_DIR" ] || die "IDE profile SSOT missing: $IDE_DIR"
command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH"

# --- Extensions (machine scope) ------------------------------------------------

EXT_FILES="$IDE_DIR/extensions.core.json"
[ "$WS_CLASS" = "eslint_owned" ] && EXT_FILES="$EXT_FILES $IDE_DIR/extensions.eslint_owned.json"

# shellcheck disable=SC2086
DESIRED_EXTS="$(python3 - $EXT_FILES <<'PY'
import json, sys
seen, out = set(), []
for path in sys.argv[1:]:
    with open(path) as fh:
        for ext in json.load(fh).get("extensions", []):
            key = ext.lower()
            if key not in seen:
                seen.add(key)
                out.append(ext)
print("\n".join(out))
PY
)"

# `cursor --install-extension --force` updates the desired set but does not
# uninstall a second marketplace Ruff ID someone installed by hand. Leftover
# *version folders* of charliermarsh.ruff itself are a one-shot operator
# cleanup (not sessionStart): pruning them every boot would race the editor.
prune_foreign_ruff_extensions() {
  command -v cursor >/dev/null 2>&1 || return 0
  local installed id lowered
  installed="$(cursor --list-extensions 2>/dev/null || true)"
  [ -n "$installed" ] || return 0
  while IFS= read -r id; do
    [ -n "$id" ] || continue
    lowered="$(printf '%s' "$id" | tr '[:upper:]' '[:lower:]')"
    case "$lowered" in
      *ruff*)
        if [ "$lowered" != "charliermarsh.ruff" ]; then
          if [ "$DRY_RUN" -eq 1 ]; then
            log "Would uninstall foreign Ruff extension: $id"
          else
            log "Uninstalling foreign Ruff extension: $id"
            cursor --uninstall-extension "$id" >/dev/null 2>&1 || \
              echo "WARN: uninstall failed: $id" >&2
          fi
        fi
        ;;
    esac
  done <<EOF
$installed
EOF
}

EXT_STAMP="$HOME/.cursor/.l9-ide-desired-hash"
EXT_HASH="$(printf '%s\n' "$DESIRED_EXTS" | shasum -a 256 | awk '{print $1}')"
EXT_STATE="skipped"

if [ "$DRY_RUN" -eq 1 ]; then
  log "Extensions (dry-run):"
  log "$DESIRED_EXTS"
  EXT_STATE="dry-run"
elif ! command -v cursor >/dev/null 2>&1; then
  log "WARN: 'cursor' CLI not on PATH — skipping extension install"
  EXT_STATE="no-cli"
elif [ "$FORCE" -eq 0 ] && [ -f "$EXT_STAMP" ] && [ "$(cat "$EXT_STAMP" 2>/dev/null || true)" = "$EXT_HASH" ]; then
  log "Extensions already match desired state"
  EXT_STATE="current"
else
  ext_failed=0
  while IFS= read -r ext; do
    [ -n "$ext" ] || continue
    log "Extension: $ext"
    if ! cursor --install-extension "$ext" --force >/dev/null 2>&1; then
      echo "WARN: extension install failed: $ext" >&2
      ext_failed=1
    fi
  done <<EOF
$DESIRED_EXTS
EOF
  mkdir -p "$(dirname "$EXT_STAMP")"
  if [ "$ext_failed" -eq 0 ]; then
    printf '%s\n' "$EXT_HASH" > "$EXT_STAMP"
    EXT_STATE="installed"
  else
    # No stamp on partial failure — next session retries.
    rm -f "$EXT_STAMP" 2>/dev/null || true
    EXT_STATE="partial"
  fi
fi

prune_foreign_ruff_extensions

# --- Workspace settings (managed-key merge, repo scope) ------------------------

SETTINGS_FILES="$IDE_DIR/settings.base.json $IDE_DIR/settings.python.json"
POLICY_FILE="$IDE_DIR/policy.json"
RENDER_MAP="$IDE_DIR/render.cursor.json"
[ -f "$POLICY_FILE" ] || die "ownership policy missing: $POLICY_FILE"
[ -f "$RENDER_MAP" ] || die "Cursor render map missing: $RENDER_MAP"

# shellcheck disable=SC2086
if ! SET_STATE="$(
  L9_WORKSPACE="$WORKSPACE" \
  L9_CLASS="$WS_CLASS" \
  L9_DRY_RUN="$DRY_RUN" \
  L9_FORCE="$FORCE" \
  L9_POLICY="$POLICY_FILE" \
  L9_RENDER_MAP="$RENDER_MAP" \
  python3 - $SETTINGS_FILES <<'PY'
"""Managed-key merge into <workspace>/.vscode/settings.json.

A key is adopted or updated only when it is absent from the target, or when the
previous stamp records it as managed by this profile. Keys we managed before but
no longer declare are removed. Everything else is left untouched.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

workspace = Path(os.environ["L9_WORKSPACE"])
dry_run = os.environ.get("L9_DRY_RUN") == "1"
force = os.environ.get("L9_FORCE") == "1"
ws_class = os.environ["L9_CLASS"]


def render_ownership(class_name: str) -> dict[str, object]:
    """policy.json ownership -> Cursor per-language formatter blocks.

    Entries whose authority is not "governance" render nothing: that is formatter
    exclusivity, and it is why eslint_owned workspaces get no JS/TS binding.
    """
    policy = json.loads(Path(os.environ["L9_POLICY"]).read_text())
    tools = json.loads(Path(os.environ["L9_RENDER_MAP"]).read_text())["tools"]
    try:
        ownership = policy["classes"][class_name]["ownership"]
    except KeyError:
        msg = f"policy.json declares no ownership for class {class_name!r}"
        raise SystemExit(msg) from None

    blocks: dict[str, object] = {}
    for entry in ownership:
        if entry.get("authority") != "governance":
            continue
        tool_name = entry["tool"]
        if tool_name not in tools:
            msg = f"{tool_name!r} owns {entry['languages']} in policy.json but is absent from the render map"
            raise SystemExit(msg)
        tool = tools[tool_name]
        on_save = entry.get("on_save") or {}
        block: dict[str, object] = {"editor.defaultFormatter": tool["format_extension"]}
        if "format" in on_save:
            block["editor.formatOnSave"] = bool(on_save["format"])
        actions = {
            tool.get("code_actions", {})[action]: mode
            for action, mode in on_save.items()
            if action != "format" and action in tool.get("code_actions", {})
        }
        if actions:
            block["editor.codeActionsOnSave"] = actions
        for language in entry["languages"]:
            blocks[f"[{language}]"] = dict(block)
    return blocks


desired: dict[str, object] = {}
for path in sys.argv[1:]:
    desired.update(json.loads(Path(path).read_text()))
desired.update(render_ownership(ws_class))

payload = json.dumps(
    {"class": os.environ["L9_CLASS"], "settings": desired},
    sort_keys=True,
    separators=(",", ":"),
)
desired_hash = hashlib.sha256(payload.encode()).hexdigest()

vscode_dir = workspace / ".vscode"
settings_path = vscode_dir / "settings.json"
stamp_path = vscode_dir / ".l9-ide-desired-hash"

prior_managed: list[str] = []
prior_hash = ""
if stamp_path.is_file():
    try:
        stamp = json.loads(stamp_path.read_text())
        prior_managed = list(stamp.get("managed_keys", []))
        prior_hash = str(stamp.get("hash", ""))
    except (json.JSONDecodeError, OSError):
        pass

current: dict[str, object] = {}
if settings_path.is_file():
    try:
        current = json.loads(settings_path.read_text() or "{}")
    except json.JSONDecodeError:
        # Comment-bearing JSONC we cannot safely rewrite — leave it alone.
        print("jsonc-skip")
        raise SystemExit(0)

if prior_hash == desired_hash and not force and settings_path.is_file():
    if all(key in current for key in desired):
        print("current")
        raise SystemExit(0)

merged = dict(current)
for key, value in desired.items():
    if key not in merged or key in prior_managed:
        merged[key] = value

for key in prior_managed:
    if key not in desired and key in merged:
        del merged[key]

managed_now = sorted(key for key in desired if merged.get(key) == desired[key])

if dry_run:
    print("dry-run")
    raise SystemExit(0)

vscode_dir.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
stamp_path.write_text(
    json.dumps(
        {"hash": desired_hash, "class": os.environ["L9_CLASS"], "managed_keys": managed_now},
        indent=2,
    )
    + "\n"
)
print("written")
PY
)"; then
  die "settings render failed for class $WS_CLASS (see stderr above)"
fi

log "Settings:  $SET_STATE"
echo "ext=$EXT_STATE settings=$SET_STATE"
