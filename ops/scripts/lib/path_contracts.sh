#!/usr/bin/env bash
# Typed filesystem contracts used by governance wiring.
# shellcheck shell=bash

path_realpath() {
  python3 - "$1" <<'PY'
import os
import sys

print(os.path.realpath(os.path.expanduser(sys.argv[1])))
PY
}

ensure_required_symlink() {
  local link=$1
  local target=$2
  local label=$3
  local actual expected backup

  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    actual="$(path_realpath "$link")"
    expected="$(path_realpath "$target")"
    if [ "$actual" = "$expected" ]; then
      echo "OK: $label"
      return 0
    fi
    rm "$link"
  elif [ -e "$link" ]; then
    backup="${link}.backup.$(date +%Y%m%d_%H%M%S)"
    mv "$link" "$backup"
    echo "BACKED UP: $label -> $backup"
  fi

  ln -s "$target" "$link"
  echo "LINKED: $label -> $target"
}
