#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code environment — Setup *bootstrap* (Web & Mobile).
#
# PASTE THIS ONCE into: claude.ai/code -> your environment -> Setup script.
# It is intentionally STABLE — you should almost never need to re-paste it.
#
# Why this exists: the account Setup-script field is a copy, not a live link to
# the repo. Pasting the full setup.sh means every edit to that file drifts from
# the running copy until someone re-pastes it. This bootstrap breaks that
# coupling: it clones/refreshes the governance SSOT, then executes the CANONICAL
# environment/claude-code/web/setup.sh from it. From then on, edits to setup.sh
# on `main` propagate to every NEW session automatically — no re-paste.
#
# Trust model: this runs whatever setup.sh is on the tracked branch at session
# start. `main` is branch-protected and is the SSOT — that is the intended trust
# boundary. For controlled rollout, pin L9_GOVERNANCE_BRANCH to a tag or commit.
#
# Env vars (from the Environment variables field) are passed straight through to
# setup.sh: GH_TOKEN, L9_GOVERNANCE_REMOTE/_BRANCH, L9_MEMORY_*, USER_ID, etc.
# See environment.env.example and network-policy.md (allowlist github.com).
# ---------------------------------------------------------------------------
set -uo pipefail

GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
GOV_DIR="$HOME/.cursor-governance"

echo "=== L9 setup bootstrap: governance @ ${GOV_BRANCH} -> ${GOV_DIR} ==="

if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR" \
    || { echo "FATAL: governance clone failed — allowlist github.com in Network access"; exit 0; }
else
  git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE" 2>/dev/null || true
  if git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" 2>/dev/null; then
    git -C "$GOV_DIR" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" 2>/dev/null \
      || git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" 2>/dev/null \
      || echo "WARN: could not reset to origin/${GOV_BRANCH} — using existing clone"
  else
    echo "WARN: fetch origin/${GOV_BRANCH} failed — using existing clone (may be stale)"
  fi
fi

SETUP="$GOV_DIR/environment/claude-code/web/setup.sh"
if [ -f "$SETUP" ]; then
  echo "=== Delegating to canonical setup.sh @ $(git -C "$GOV_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown) ==="
  # Do NOT cd — setup.sh must run in the workspace cwd, exactly as a direct paste would.
  bash "$SETUP"
else
  echo "FATAL: $SETUP missing after clone/sync — governance layout changed or clone incomplete."
  exit 0
fi
