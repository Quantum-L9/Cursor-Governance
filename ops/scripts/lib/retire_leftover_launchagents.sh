#!/usr/bin/env bash
# C6 leftover retirement: bootout + move retired tenx LaunchAgents to _retired.
# Never delete. Never touch Dropbox or ~/bin shims. Honor L9_LAUNCHAGENTS_DIR
# (tests). launchctl bootout only when the target dir is the real machine plane.
# shellcheck shell=bash

RETIRED_TENX_LAUNCHAGENT_LABELS=(
  com.tenx.cursor-governance
  com.tenx.chat-export
  com.tenx.learning-processor
)

retire_leftover_tenx_launchagents() {
  local la_dir="${L9_LAUNCHAGENTS_DIR:-$HOME/Library/LaunchAgents}"
  local real_la="$HOME/Library/LaunchAgents"
  local retired="$la_dir/_retired"
  local label plist dest ts la_real real_real

  if [ ! -d "$la_dir" ]; then
    echo "OK: LaunchAgents dir absent — skip tenx leftover retirement ($la_dir)"
    return 0
  fi

  la_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$la_dir")"
  real_real="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$real_la")"

  mkdir -p "$retired"
  for label in "${RETIRED_TENX_LAUNCHAGENT_LABELS[@]}"; do
    plist="$la_dir/${label}.plist"
    if [ ! -e "$plist" ] && [ ! -L "$plist" ]; then
      echo "OK: no leftover $label"
      continue
    fi
    if [ "$la_real" = "$real_real" ] && command -v launchctl >/dev/null 2>&1; then
      launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
    fi
    dest="$retired/${label}.plist"
    if [ -e "$dest" ]; then
      ts="$(date +%Y%m%d_%H%M%S)"
      dest="$retired/${label}.plist.${ts}"
    fi
    mv "$plist" "$dest"
    echo "RETIRED: $label -> $dest"
  done
}
