#!/usr/bin/env bash
# Machine-local paths that survive activate_fresh swap and /ff catch-up.
# Same contract as .venv: never delete, never print contents, never use as
# overwrite fodder when origin starts tracking a colliding name.
# shellcheck shell=bash

# Secret / legal WIP paths are never corpus-keep (gitignore + shelf skip).
ssot_ff_corpus_skip_rel() {
  local rel="${1#./}"
  case "$rel" in
    WIP/Legal\ Defense/*|WIP/Legal\ Defense) return 0 ;;
    WIP/*oauth*.json|WIP/*credentials*.json|WIP/*client_secret*.json) return 0 ;;
  esac
  return 1
}

# Tracked or untracked corpus bytes that /ff must not clobber (like .venv).
# SSOT: ops/config/wip-corpus.yaml skip_dir_names + secret_globs.
ssot_is_ff_corpus_keep() {
  local rel="${1#./}"
  if ssot_ff_corpus_skip_rel "$rel"; then
    return 1
  fi
  case "$rel" in
    TODO.md|WIP/*|docs/plans/*|environment/program-execution/campaigns/*)
      return 0
      ;;
  esac
  return 1
}

ssot_is_machine_local_keep() {
  local rel="${1#./}"
  case "$rel" in
    .venv|.venv/*|.env.local|env.local|.claude/settings.local.json|.env.*.local)
      return 0
      ;;
  esac
  return 1
}

# Carry keep-list from a just-moved bak (or any donor) onto dest.
# .venv is moved (do not duplicate). Secret files are copied (bak keeps a copy).
# Dest wins if the path already exists. Never prints file contents.
ssot_carry_machine_local() {
  local src="${1:-}" dest="${2:-}"
  local rel base f dest_dir
  [ -n "$src" ] && [ -d "$src" ] || return 0
  [ -n "$dest" ] && [ -d "$dest" ] || return 0

  if [ -e "$src/.venv" ] && [ ! -e "$dest/.venv" ]; then
    if mv "$src/.venv" "$dest/.venv" 2>/dev/null; then
      echo "OK: carried .venv from bak"
    elif cp -a "$src/.venv" "$dest/.venv" 2>/dev/null; then
      echo "OK: copied .venv from bak"
    else
      echo "WARNING: failed to carry .venv from bak" >&2
    fi
  fi

  for rel in .env.local env.local .claude/settings.local.json; do
    if { [ -e "$src/$rel" ] || [ -L "$src/$rel" ]; } && [ ! -e "$dest/$rel" ]; then
      dest_dir="$(dirname "$dest/$rel")"
      mkdir -p "$dest_dir" 2>/dev/null || true
      if cp -p "$src/$rel" "$dest/$rel" 2>/dev/null; then
        chmod go-rwx "$dest/$rel" 2>/dev/null || true
        echo "OK: carried $rel from bak"
      else
        echo "WARNING: failed to carry $rel from bak" >&2
      fi
    fi
  done

  for f in "$src"/.env.*.local; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    if [ ! -e "$dest/$base" ]; then
      if cp -p "$f" "$dest/$base" 2>/dev/null; then
        chmod go-rwx "$dest/$base" 2>/dev/null || true
        echo "OK: carried $base from bak"
      else
        echo "WARNING: failed to carry $base from bak" >&2
      fi
    fi
  done
}
