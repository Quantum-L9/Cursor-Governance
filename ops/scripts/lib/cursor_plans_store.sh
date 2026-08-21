#!/usr/bin/env bash
# Machine-global Cursor plans live in the governance repo at docs/plans/.
# ~/.cursor/plans is a symlink to that directory so every workspace writes here.
# shellcheck shell=bash

_cursor_plans_stamp() {
  printf '%s\n' "${HOME}/.cursor/l9-plans-store"
}

resolve_cursor_plans_store() {
  local stamp store kind
  stamp="$(_cursor_plans_stamp)"
  if [ -f "$stamp" ]; then
    store="$(tr -d '\n' <"$stamp")"
    if [ -n "$store" ]; then
      mkdir -p "$store"
      printf '%s\n' "$store"
      return 0
    fi
  fi
  if declare -F classify_workspace_kind >/dev/null 2>&1; then
    kind="$(classify_workspace_kind "${WORKSPACE_DIR:-${WORKSPACE:-$(pwd)}}")"
  else
    kind="consumer"
  fi
  if [ "$kind" = "ssot" ] || [ "$kind" = "ssot_checkout" ]; then
    store="${WORKSPACE_DIR:-${WORKSPACE:-$(pwd)}}/docs/plans"
  else
    store="${GLOBAL_COMMANDS:-${GOV_ROOT:-$HOME/.cursor-governance}}/docs/plans"
  fi
  mkdir -p "$(dirname "$stamp")"
  mkdir -p "$store"
  printf '%s\n' "$store" >"$stamp"
  printf '%s\n' "$store"
}

_copy_plans_tree() {
  local src=$1 dest=$2
  python3 - "$src" "$dest" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)
skip = {".DS_Store"}
if src.is_dir():
    for item in src.iterdir():
        if item.name in skip:
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
PY
}

ensure_machine_cursor_plans_store() {
  local store home_plans bak want have
  store="$(resolve_cursor_plans_store)"
  home_plans="${HOME}/.cursor/plans"
  mkdir -p "$store"
  mkdir -p "${HOME}/.cursor"
  if [ -L "$home_plans" ]; then
    have="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$home_plans")"
    want="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$store")"
    if [ "$have" = "$want" ]; then
      echo "OK: ~/.cursor/plans -> $store"
      return 0
    fi
    ln -sfn "$store" "$home_plans"
    echo "LINKED: ~/.cursor/plans -> $store"
    return 0
  fi
  if [ -d "$home_plans" ]; then
    _copy_plans_tree "$home_plans" "$store"
    bak="${HOME}/.cursor/plans.pre-repo-store.$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$home_plans" "$bak"
    ln -sfn "$store" "$home_plans"
    echo "MIGRATED: ~/.cursor/plans -> $store (backup $bak)"
    return 0
  fi
  if [ -e "$home_plans" ]; then
    bak="${HOME}/.cursor/plans.pre-repo-store.$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$home_plans" "$bak"
  fi
  ln -sfn "$store" "$home_plans"
  echo "LINKED: ~/.cursor/plans -> $store"
}
