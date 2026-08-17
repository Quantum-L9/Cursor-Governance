#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code cloud Setup script — startup stub (Web · Mobile · --cloud).
#
# Paste THIS into claude.ai/code -> environment -> Setup script. Do not paste
# web/setup.sh: the field is a copy, not a live link, so the full script drifts
# from main on every edit. This stub is stable — it normalizes the account
# environment, materializes the governance SSOT, and hands off to the canonical
# web/setup.sh from that clone, so setup.sh edits reach every new session with
# no re-paste.
#
# Companion fields:
#   Environment variables -> web/environment.env.example
#   Network access        -> web/network-policy.md
#
# Anthropic snapshots the VM after the first successful run — keep this stub
# small and put heavy probes in setup.sh / SessionStart hooks.
#
# Docs: https://code.claude.com/docs/en/cloud-environments
# ---------------------------------------------------------------------------
# No `set -e`: a single failed probe must never abort the environment build.
# The two hard failures are the governance clone and a missing setup.sh, which
# exit non-zero explicitly.
set -uo pipefail

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

# Cloud-only install paths (no-op on local CLI, which wires .claude/ from the repo).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- 1) Normalize the account environment ---------------------------------
# The Environment variables field is literal .env text: Anthropic does NOT
# expand `$HOME`. A pasted `L9_GOVERNANCE_DIR=$HOME/.cursor-governance` arrives
# as that literal string, which would clone into a directory named `$HOME` and
# hand every consumer (skill router, oversight, Graphiti bridge) a path that
# does not exist. The cloud SSOT is always the real $HOME path — pin it here
# and re-export the expanded value.
GOV_DIR="$HOME/.cursor-governance"
if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "$L9_GOVERNANCE_DIR" != "$GOV_DIR" ]; then
  warn "ignoring L9_GOVERNANCE_DIR='${L9_GOVERNANCE_DIR}' — cloud SSOT is always $GOV_DIR"
  case "$L9_GOVERNANCE_DIR" in
    *'$HOME'*)
      warn "  that value is an UNEXPANDED \$HOME — delete L9_GOVERNANCE_DIR from the variables field"
      ;;
  esac
fi
export L9_GOVERNANCE_DIR="$GOV_DIR"

# The Autonomy Surface Profile matches on the exact surface id. `claude-code-mobile`
# is not in the allow-list (ops/autonomy/surface_profile.yaml `when:`), so a
# mobile-flavoured value silently drops the session out of standing A4.
if [ -n "${L9_GOVERNANCE_SURFACE:-}" ] && [ "$L9_GOVERNANCE_SURFACE" != "claude-code" ]; then
  warn "L9_GOVERNANCE_SURFACE='${L9_GOVERNANCE_SURFACE}' is not the profile surface id; using claude-code"
fi
export L9_GOVERNANCE_SURFACE="claude-code"

# ADR-0006: the HTTP memory side door is retired; Cursor Graphiti is the only
# front door. Unsetting cleans this process — deleting the vars from the account
# field is the real fix. The durable env below also unsets them for in-session Bash.
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  if [ -n "${!retired:-}" ]; then
    warn "$retired is set — retired ADR-0006 side door; delete it from the variables field"
    unset "$retired"
  fi
done

: "${GRAPHITI_MCP_URL:=https://memory.quantumaipartners.com/graphiti/mcp}"
export GRAPHITI_MCP_URL

# --- 2) Governance SSOT ----------------------------------------------------
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"

mkdir -p "$(dirname "$GOV_DIR")"
if [ -d "$GOV_DIR/.git" ]; then
  git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE" 2>/dev/null || true
  if git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" 2>/dev/null; then
    git -C "$GOV_DIR" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" 2>/dev/null \
      || git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" 2>/dev/null \
      || warn "could not reset governance clone to origin/$GOV_BRANCH"
  else
    warn "governance fetch failed — reusing existing clone (may be stale)"
  fi
else
  rm -rf "$GOV_DIR"
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR" || {
    warn "governance clone FAILED — allowlist github.com (see web/network-policy.md)"
    exit 1
  }
fi

SETUP="$GOV_DIR/environment/agents/adapters/claude-code/web/setup.sh"
if [ ! -f "$SETUP" ]; then
  warn "missing web/setup.sh in the governance clone — adapter tree incomplete"
  exit 1
fi

# Preserve consumer workspace cwd (Anthropic runs setup before Claude starts).
# Signal that this stub already materialized and checked out the governance tree
# so canonical setup does not fetch/reset the very same clone a second time. The
# marker is a claim, not an authorization: setup.sh re-validates the tree
# (git repo, canonical files present, ref matches) and falls back to its own
# synchronization if any check fails.
L9_GOVERNANCE_BOOTSTRAPPED=1 bash "$SETUP"

# --- 3) Durable exports for in-session Bash --------------------------------
# CLAUDE_ENV_FILE is not present in every cloud runtime, so write our own env
# file and source it from the shell profile when it is absent. Both paths are
# idempotent — this stub re-runs on every environment rebuild.
L9_ENV_FILE="$HOME/.l9/cloud-session.env"
mkdir -p "$(dirname "$L9_ENV_FILE")"
{
  echo "# Written by L9 setup.bootstrap.sh — do not edit by hand."
  echo "export L9_GOVERNANCE_DIR=$(printf %q "$GOV_DIR")"
  echo "export L9_GOVERNANCE_SURFACE=claude-code"
  echo "export GRAPHITI_MCP_URL=$(printf %q "$GRAPHITI_MCP_URL")"
  # ADR-0006: keep the retired side door out of every in-session shell.
  echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
} > "$L9_ENV_FILE"

# NOTE: Sonar project identity is deliberately NOT written here. It is
# per-repository, this env file is per-session and outlives a cd into another
# repo, and the canonical consumer (skills/l9-pr-remediation/scripts/sonar_fetch.py)
# takes --project/--organization as required arguments rather than reading env.
# install.sh resolves it from the active workspace instead.

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  cat "$L9_ENV_FILE" >> "$CLAUDE_ENV_FILE"
  note "durable env appended to CLAUDE_ENV_FILE"
else
  for profile in "$HOME/.bashrc" "$HOME/.profile"; do
    [ -f "$profile" ] || touch "$profile"
    grep -qF 'cloud-session.env' "$profile" 2>/dev/null \
      || printf '%s\n' '. "$HOME/.l9/cloud-session.env"  # L9 governed session env' >> "$profile"
  done
  note "CLAUDE_ENV_FILE unset — sourcing $L9_ENV_FILE from the shell profile instead"
fi

# --- 4) Memory front-door readiness (report, never block) ------------------
# An unset GRAPHITI_MCP_TOKEN is a common root cause of a DEGRADED SessionStart
# hydrate ("empty PICKUP search"), so name it here rather than at prompt time.
if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
  note "memory front door: $GRAPHITI_MCP_URL (no bearer here — expected posture)"
  note "  web/environment.env.example (S3/S7) forbids pasting a bearer into the"
  note "  variables field: that environment is model-readable. The token belongs"
  note "  behind the capability broker (L9_CAPABILITY_BROKER_URL). Broker unset =="
  note "  DEGRADED capabilities — the honest posture, not a defect to paste around."
else
  note "memory front door: $GRAPHITI_MCP_URL (bearer present)"
fi

note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
exit 0
