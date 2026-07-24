#!/usr/bin/env bash
# Declarative, idempotent Cursor IDE profile installer.
#
# Two halves, both driven by environment/ide/ as the single source of truth:
#
#   1. Extensions (machine scope) — installed via `cursor --install-extension`.
#      Stamped in $HOME/.cursor/.l9-ide-desired-hash so repeat sessions are a no-op.
#   2. Workspace settings (repo scope) — merged into <workspace>/.vscode/settings.json
#      using a MANAGED-KEY merge: a key is written only if it is absent, or if this
#      profile wrote it on a previous run. Keys the user or the repo owns are never
#      clobbered. Keys we previously managed but no longer declare are removed.
#
# Workspace classification decides which settings apply:
#   biome_default  — Biome is editor.defaultFormatter for JS/TS/JSON
#   eslint_owned   — no formatter keys written at all; ESLint/Prettier config in the
#                    repo stays authoritative (formatter exclusivity)
# Classification rules live in environment/ide/exceptions.yaml.
#
# Usage:
#   bash ops/scripts/install_ide_profile.sh [WORKSPACE]           # default: $PWD
#   bash ops/scripts/install_ide_profile.sh --quiet [WORKSPACE]   # hook-safe, fail-open
#   bash ops/scripts/install_ide_profile.sh --force [WORKSPACE]   # ignore stamps
#   bash ops/scripts/install_ide_profile.sh --dry-run [WORKSPACE] # print, write nothing
#
# Requires: python3 (JSON merge). `cursor` CLI optional — settings still merge without it.

set -euo pipefail

QUIET=0
FORCE=0
DRY_RUN=0
WORKSPACE=""

for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=1 ;;
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,27p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    -*) echo "WARN: unknown flag: $arg" >&2 ;;
    *) WORKSPACE="$arg" ;;
  esac
done

log() { [ "$QUIET" -eq 0 ] && echo "$@"; return 0; }

fail_open() {
  # sessionStart must never break a session over IDE cosmetics.
  if [ "$QUIET" -eq 1 ]; then
    echo "ide-profile: skipped ($1)"
    exit 0
  fi
  echo "ERROR: $1" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
. "$SCRIPT_DIR/resolve_governance_paths.sh"
resolve_governance_paths || fail_open "governance root not found at \$HOME/.cursor-governance"

IDE_DIR="${L9_IDE_DIR:-$GLOBAL_COMMANDS/environment/ide}"
[ -d "$IDE_DIR" ] || fail_open "IDE profile SSOT missing: $IDE_DIR"

command -v python3 >/dev/null 2>&1 || fail_open "python3 not found on PATH"

WORKSPACE="${WORKSPACE:-$PWD}"
[ -d "$WORKSPACE" ] || fail_open "workspace not a directory: $WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

# --- Classification -----------------------------------------------------------
# 1) basename match  2) any path-segment match  3) eslint markers without biome markers

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

ESLINT_REPOS="$(
  awk '
    /^eslint_owned_repos:/ { grab = 1; next }
    grab && /^[[:space:]]*-[[:space:]]*/ { sub(/^[[:space:]]*-[[:space:]]*/, ""); print; next }
    grab && /^[^[:space:]#]/ { grab = 0 }
  ' "$IDE_DIR/exceptions.yaml" 2>/dev/null || true
)"

classify() {
  local ws="$1" repo seg base
  base="$(lower "$(basename "$ws")")"
  while IFS= read -r repo; do
    [ -n "$repo" ] || continue
    repo="$(lower "$repo")"
    [ "$base" = "$repo" ] && { echo eslint_owned; return; }
    # shellcheck disable=SC2001
    for seg in $(echo "$(lower "$ws")" | tr '/' ' '); do
      [ "$seg" = "$repo" ] && { echo eslint_owned; return; }
    done
  done <<EOF
$ESLINT_REPOS
EOF

  local has_eslint=0 has_biome=0
  if find "$ws" -maxdepth 2 \( -name 'eslint.config.*' -o -name '.eslintrc*' \) \
       -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
    has_eslint=1
  fi
  if find "$ws" -maxdepth 2 \( -name 'biome.json' -o -name 'biome.jsonc' \) \
       -not -path '*/node_modules/*' -print -quit 2>/dev/null | grep -q .; then
    has_biome=1
  fi
  if [ "$has_eslint" -eq 1 ] && [ "$has_biome" -eq 0 ]; then
    echo eslint_owned
  else
    echo biome_default
  fi
}

WS_CLASS="$(classify "$WORKSPACE")"
log "Workspace: $WORKSPACE"
log "Class:     $WS_CLASS"

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

# --- Workspace settings (managed-key merge) ------------------------------------

SETTINGS_FILES="$IDE_DIR/settings.base.json $IDE_DIR/settings.python.json"
[ "$WS_CLASS" = "biome_default" ] && SETTINGS_FILES="$SETTINGS_FILES $IDE_DIR/settings.node.json"

SET_STATE="$(
  L9_WORKSPACE="$WORKSPACE" \
  L9_CLASS="$WS_CLASS" \
  L9_DRY_RUN="$DRY_RUN" \
  L9_FORCE="$FORCE" \
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

desired: dict[str, object] = {}
for path in sys.argv[1:]:
    desired.update(json.loads(Path(path).read_text()))

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
)"

log "Settings:  $SET_STATE"
[ "$QUIET" -eq 1 ] && echo "ide-profile: $WS_CLASS ext=$EXT_STATE settings=$SET_STATE"
exit 0
