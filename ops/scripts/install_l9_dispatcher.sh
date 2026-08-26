#!/usr/bin/env bash
# install_l9_dispatcher.sh — install/reconcile the thin l9 dispatcher.
#
# The repo-owned source is the single dispatcher authority:
#   environment/agents/adapters/claude-code/bin/l9
# It is installed to the first-on-PATH user bin so `l9` resolves without a
# per-repo wrapper:
#   $HOME/.local/bin/l9  (override L9_DISPATCHER_DEST)
#
# Idempotent: re-running reconciles the destination to the current source. Safe
# in setup.sh, install.sh, and SessionStart. Never installs a copy of the
# Makefile and never creates a second dispatcher.
set -euo pipefail

GOV="${L9_GOV_ROOT:-$HOME/.cursor-governance}"
# Allow running from a workspace clone (this repo) as well as the runtime clone.
# This script lives at <repo>/ops/scripts/, so the repo root is two levels up.
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_REL="environment/agents/adapters/claude-code/bin/l9"

# Resolve the source: prefer the governance runtime clone, fall back to the
# clone this script lives in (so `make l9-dispatcher-install` works anywhere).
if [ -f "$GOV/$SRC_REL" ]; then
	SRC="$GOV/$SRC_REL"
elif [ -f "$SELF_DIR/$SRC_REL" ]; then
	SRC="$SELF_DIR/$SRC_REL"
else
	printf 'install_l9_dispatcher: dispatcher source %s not found under %s or %s\n' \
		"$SRC_REL" "$GOV" "$SELF_DIR" >&2
	exit 1
fi

DEST="${L9_DISPATCHER_DEST:-$HOME/.local/bin/l9}"
DEST_DIR="$(dirname "$DEST")"
mkdir -p "$DEST_DIR"

MODE="${1:-install}"

if [ "$MODE" = "--check" ]; then
	if [ ! -e "$DEST" ]; then
		printf 'l9 dispatcher: MISSING at %s (run: make l9-dispatcher-install)\n' "$DEST"
		exit 1
	fi
	# Compare content so a stale copy is reported as drift.
	if cmp -s "$SRC" "$DEST" 2>/dev/null || { [ -L "$DEST" ] && [ "$(readlink -f "$DEST")" = "$(readlink -f "$SRC")" ]; }; then
		printf 'l9 dispatcher: OK at %s\n' "$DEST"
		exit 0
	fi
	printf 'l9 dispatcher: DRIFT at %s (differs from %s)\n' "$DEST" "$SRC"
	exit 1
fi

# Install: copy the source content and mark executable. A real file (not a
# symlink into an ephemeral clone) survives a clone refresh mid-session.
install -m 0755 "$SRC" "$DEST"
printf 'l9 dispatcher: installed %s -> %s\n' "$SRC" "$DEST"

case ":$PATH:" in
*":$DEST_DIR:"*) : ;;
*) printf 'l9 dispatcher: NOTE %s is not on PATH; add it to use `l9` directly\n' "$DEST_DIR" >&2 ;;
esac
