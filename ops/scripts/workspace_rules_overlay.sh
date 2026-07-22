#!/usr/bin/env bash
# Shared contract for repository-owned Cursor rules overlays.
# A consumer repository's .cursor/rules path must be a real directory.

RULES_OVERLAY_ERROR=""

_rules_realpath() {
  python3 - "$1" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
}

validate_repo_rules_overlay() {
  local workspace=$1
  local rules_path="$workspace/.cursor/rules"
  RULES_OVERLAY_ERROR=""

  if [ -L "$rules_path" ]; then
    RULES_OVERLAY_ERROR=".cursor/rules must be a real repository overlay directory, not a symlink ($(_rules_realpath "$rules_path"))"
    return 1
  fi
  if [ -d "$rules_path" ]; then
    return 0
  fi
  if [ -e "$rules_path" ]; then
    RULES_OVERLAY_ERROR=".cursor/rules exists but is not a directory"
    return 1
  fi

  RULES_OVERLAY_ERROR=".cursor/rules local overlay is missing"
  return 1
}

ensure_repo_rules_overlay() {
  local workspace=$1
  local global_rules=$2
  local cursor_dir="$workspace/.cursor"
  local rules_path="$cursor_dir/rules"

  mkdir -p "$cursor_dir"

  if [ -L "$rules_path" ]; then
    local actual expected
    actual="$(_rules_realpath "$rules_path")"
    expected="$(_rules_realpath "$global_rules")"

    if [ "$actual" != "$expected" ]; then
      echo "ERROR: unexpected .cursor/rules symlink target: $actual" >&2
      return 1
    fi

    rm "$rules_path"
    mkdir -p "$rules_path"
    echo "REPAIRED: replaced legacy global-rules symlink with local .cursor/rules overlay"
    return 0
  fi

  if [ -d "$rules_path" ]; then
    echo "OK: .cursor/rules local overlay preserved"
    return 0
  fi

  if [ -e "$rules_path" ]; then
    echo "ERROR: .cursor/rules exists but is not a directory or supported symlink" >&2
    return 1
  fi

  mkdir -p "$rules_path"
  echo "CREATED: .cursor/rules local overlay"
}
