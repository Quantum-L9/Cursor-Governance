#!/usr/bin/env bash
# Backups leave the plugin directory; siblings of l9-governance are a fault.
#
# Cursor treats every child of ~/.cursor/plugins/local/ as a plugin. The wiring
# scripts used to park a displaced link as <link>.backup.<stamp> beside the
# live one, so a stale copy of the whole governance tree kept loading its
# rules/ as always-apply — a 2026-08-14 backup taught one session the retired
# graphiti client and the bare `record-kernels` form for a month.
#
# Two rules, one place:
#   l9_backup_aside <path>        move a displaced path OUT to
#                                 $L9_BACKUP_ROOT/<category>/<stamp>/<basename>
#                                 (default root ~/.cursor/l9/backups). Never rm.
#   l9_plugin_siblings            print every ~/.cursor/plugins/local/l9-governance*
#                                 entry that is not the live link itself.
#   l9_relocate_plugin_siblings   move each of those aside; print RELOCATED lines.
#
# $HOME and L9_BACKUP_ROOT are honoured so tests can run under a temp HOME.
# shellcheck shell=bash

l9_backup_root() {
  printf '%s\n' "${L9_BACKUP_ROOT:-$HOME/.cursor/l9/backups}"
}

l9_plugins_local_dir() {
  printf '%s\n' "$HOME/.cursor/plugins/local"
}

l9_backup_stamp() {
  date +%Y%m%d_%H%M%S
}

# Move $1 out of its directory into the backup root. Category is "plugins" for
# anything under ~/.cursor/plugins/local, "paths" otherwise. Prints the
# destination. A collision on the same second appends a counter; nothing is
# ever overwritten or deleted.
l9_backup_aside() {
  local src=$1
  [ -e "$src" ] || [ -L "$src" ] || return 0
  local category=paths
  case "$src" in
    "$(l9_plugins_local_dir)"/*) category=plugins ;;
  esac
  local dest_dir dest base n
  dest_dir="$(l9_backup_root)/$category/$(l9_backup_stamp)"
  mkdir -p "$dest_dir"
  base="$(basename "$src")"
  dest="$dest_dir/$base"
  n=1
  while [ -e "$dest" ] || [ -L "$dest" ]; do
    dest="$dest_dir/$base.$n"
    n=$((n + 1))
  done
  mv "$src" "$dest"
  printf '%s\n' "$dest"
}

# Every entry in ~/.cursor/plugins/local whose name starts with l9-governance
# and is not exactly l9-governance. One per line. Empty when clean.
l9_plugin_siblings() {
  local dir
  dir="$(l9_plugins_local_dir)"
  [ -d "$dir" ] || return 0
  local entry name
  for entry in "$dir"/l9-governance*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    name="$(basename "$entry")"
    [ "$name" = "l9-governance" ] && continue
    printf '%s\n' "$entry"
  done
}

# The one-line remedy the wiring check prints. Bound to this checkout so it is
# runnable from a consumer tree.
l9_relocate_plugin_siblings_command() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  printf 'bash %s/relocate_plugin_siblings.sh\n' "$here"
}

l9_relocate_plugin_siblings() {
  local entry dest moved=0
  while IFS= read -r entry; do
    [ -n "$entry" ] || continue
    dest="$(l9_backup_aside "$entry")"
    echo "RELOCATED: $entry -> $dest"
    moved=$((moved + 1))
  done < <(l9_plugin_siblings)
  if [ "$moved" -eq 0 ]; then
    echo "OK: no l9-governance siblings under $(l9_plugins_local_dir)"
  fi
}
