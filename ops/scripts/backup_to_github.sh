#!/usr/bin/env bash
# Push the governance SSOT (GlobalCommands + CANONICAL_LAW) up to the GitHub remote.
# SSOT: GitHub (the ~/.cursor-governance clone). This is the push side; session start
# pulls via ops/scripts/governance_sync.sh. Remote is overridable via GOVERNANCE_GITHUB_REMOTE.
#
# Usage:
#   bash .cursor-commands/ops/scripts/backup_to_github.sh
#   bash .cursor-commands/ops/scripts/backup_to_github.sh "chore(governance): session sync"
#
# Env:
#   GOVERNANCE_GITHUB_REMOTE  default https://github.com/Quantum-L9/Cursor-Governance.git
#   GOVERNANCE_BACKUP_DRY_RUN=1   stage/commit only, no push
#   GOVERNANCE_BACKUP_SKIP=1      exit 0 immediately
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=resolve_governance_paths.sh
source "$SCRIPT_DIR/resolve_governance_paths.sh"

if [ "${GOVERNANCE_BACKUP_SKIP:-0}" = "1" ]; then
  echo "SKIP: GOVERNANCE_BACKUP_SKIP=1"
  exit 0
fi

resolve_governance_paths_or_exit

REMOTE="${GOVERNANCE_GITHUB_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
BRANCH="${GOVERNANCE_GITHUB_BRANCH:-main}"
MSG="${1:-chore(governance): sync SSOT $(date +%Y-%m-%d\ %H:%M)}"

cd "$GLOBAL_COMMANDS"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "WARN: gh not installed — push may fail if credentials are missing" >&2
fi

if [ ! -d .git ]; then
  echo "INIT: git repo in GlobalCommands"
  git init -b "$BRANCH"
  git remote add origin "$REMOTE" 2>/dev/null || git remote set-url origin "$REMOTE"
  git fetch origin "$BRANCH" 2>/dev/null || true
  if git rev-parse "origin/$BRANCH" >/dev/null 2>&1; then
    git reset --soft "origin/$BRANCH" 2>/dev/null || git checkout -B "$BRANCH"
  fi
else
  git remote set-url origin "$REMOTE" 2>/dev/null || git remote add origin "$REMOTE"
fi

# Pre-flight: refuse to blindly stage a tree that already has unresolved conflict
# markers / unmerged paths (e.g. left behind by a governance_sync.sh stash-pop
# conflict). `git add -A` has no way to tell literal <<<<<<< markers apart from
# intentional text, so without this guard they get committed as if resolved.
if git status --porcelain | grep -qE '^(UU|AA|DD|AU|UA|UD|DU) '; then
  echo "ERROR: unmerged paths detected in $GLOBAL_COMMANDS — refusing to stage/commit over an unresolved conflict:" >&2
  git status --porcelain | grep -E '^(UU|AA|DD|AU|UA|UD|DU) ' >&2
  echo "Resolve manually (see $GLOBAL_COMMANDS/.sync-conflict if present), then re-run." >&2
  exit 1
fi

git add -A

if git diff --cached --quiet; then
  echo "OK: nothing to commit — GitHub SSOT clone matches index"
  if git rev-parse "origin/$BRANCH" >/dev/null 2>&1; then
    git push origin "HEAD:$BRANCH" 2>/dev/null && echo "OK: remote already up to date" || true
  fi
  exit 0
fi

git commit -m "$MSG"

if [ "${GOVERNANCE_BACKUP_DRY_RUN:-0}" = "1" ]; then
  echo "DRY_RUN: committed locally; push skipped"
  exit 0
fi

git fetch origin "$BRANCH" 2>/dev/null || true
if git rev-parse "origin/$BRANCH" >/dev/null 2>&1; then
  if ! git rebase "origin/$BRANCH"; then
    echo "WARN: rebase failed — trying merge" >&2
    git rebase --abort 2>/dev/null || true
    if ! git merge "origin/$BRANCH" -m "chore(governance): merge remote before push"; then
      # Never fall through to `git push` after a failed merge — that would either
      # push a tree with literal conflict markers, or (with an incomplete merge)
      # fail outright leaving a half-merged state. Restore a clean tree and stop.
      echo "ERROR: merge with origin/$BRANCH failed — aborting merge to restore a clean tree. Resolve manually and re-run; NOT pushing." >&2
      git merge --abort 2>/dev/null || true
      exit 1
    fi
  fi
fi

git push -u origin "HEAD:$BRANCH"
echo "OK: pushed governance backup to $REMOTE ($BRANCH)"
