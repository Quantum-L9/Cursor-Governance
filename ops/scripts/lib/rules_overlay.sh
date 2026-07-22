#!/usr/bin/env bash
# Contract for the repository-owned Cursor project-rule surface.
# shellcheck shell=bash

if ! declare -F path_realpath >/dev/null 2>&1; then
  echo "ERROR: rules_overlay.sh requires path_contracts.sh" >&2
  return 1 2>/dev/null || exit 1
fi

ensure_repo_rules_overlay() {
  local rules_path=$1
  local legacy_target=$2
  local actual expected

  mkdir -p "$(dirname "$rules_path")"

  if [ -L "$rules_path" ]; then
    actual="$(path_realpath "$rules_path")"
    expected="$(path_realpath "$legacy_target")"
    if [ "$actual" != "$expected" ]; then
      echo "ERROR: unexpected .cursor/rules symlink target: $actual" >&2
      echo "EXPECTED LEGACY TARGET: $expected" >&2
      return 1
    fi

    rm "$rules_path"
    mkdir -p "$rules_path"
    echo "REPAIRED: replaced legacy global-rules symlink with local overlay directory"
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
