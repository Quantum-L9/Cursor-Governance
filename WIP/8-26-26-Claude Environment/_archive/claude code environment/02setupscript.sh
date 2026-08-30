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

# Bump on EVERY change to this file. The Setup script field is a copy-paste, not
# a live link, so the pasted stub silently drifts from main and there is no way
# to see it from inside the sandbox. Recording the revision that actually ran
# turns "is the pasted stub current?" from unanswerable into a comparison
# (audit B-06). verify_account_env.py reads it back from cloud-session.env.
L9_STUB_REVISION="2026-08-21.2"

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
# front door. Unsetting cleans this process only. Deleting the vars from the
# account field is the real fix — and the ONLY one that reaches agent commands
# (see the durable-env scope note in section 3).
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  if [ -n "${!retired:-}" ]; then
    warn "$retired is set — retired ADR-0006 side door; delete it from the variables field"
    unset "$retired"
  fi
done

# Infisical / capability plane (same contract as ops/scripts/bootstrap_agent_environment.sh).
# Model-controlled surfaces never hold UA, password, PAT, or downstream tokens.
# Credentials stay in Infisical behind the broker. A pasted "Infisical password"
# configuration here is a master key — strip it.
# Names only, never values. Unsetting a leaked variable here makes it invisible
# to every later check — the stub runs at environment build, the agent runs days
# later in a different process, and by then `prohibited_present()` sees a clean
# environment for a field that still contains a credential. Recording the NAME
# keeps the finding alive without carrying the secret forward.
L9_LEAKED_NAMES=""
for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
              INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
              GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID \
              AWS_SESSION_TOKEN GITHUB_TOKEN; do
  leaked_value="${!leaked:-}"
  [ -n "$leaked_value" ] || continue
  # `proxy-injected` is the platform's sentinel for a credential it proxies, not
  # a credential. Unsetting it would break the very proxying it announces.
  if [ "$leaked_value" = "proxy-injected" ]; then
    note "$leaked holds the platform proxy sentinel (no credential material) — leaving it"
    continue
  fi
  warn "$leaked is set — PROHIBITED on this surface (Infisical/capability plane); unsetting"
  L9_LEAKED_NAMES="${L9_LEAKED_NAMES:+$L9_LEAKED_NAMES }$leaked"
  unset "$leaked"
done
if [ -n "${GH_TOKEN:-}" ] && [ "$GH_TOKEN" != "proxy-injected" ]; then
  warn "GH_TOKEN is a real credential — PROHIBITED; unsetting (platform proxy authenticates)"
  L9_LEAKED_NAMES="${L9_LEAKED_NAMES:+$L9_LEAKED_NAMES }GH_TOKEN"
  unset GH_TOKEN
fi
if [ -n "$L9_LEAKED_NAMES" ]; then
  warn "REMOVE these from the Environment variables field — unsetting them here fixes"
  warn "  only this process, and the field keeps the credential for every future session:"
  warn "  $L9_LEAKED_NAMES"
fi
# Variables file contract: never a PAT. Anthropic's git proxy authenticates and
# injects its own credential; this environment exports no GH_TOKEN at all. If a
# self-hosted deployment supplies a real token under a different trust policy,
# that is a separate mode and must not be persisted by this cloud bootstrap.

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

# Post-condition, not intention. Every branch above can end with the clone on a
# ref nobody asked for: a fetch that fails warns and REUSES the old tree, and a
# checkout that fails warns and falls through. The audit found this clone pinned
# 40 commits behind main with the environment reported as a successful build,
# because nothing between "warn" and "exit 0" ever compared HEAD to the ref it
# was supposed to be on. Resolve it once, here, and carry it forward.
L9_GOVERNANCE_REVISION="$(git -C "$GOV_DIR" rev-parse --verify --quiet HEAD 2>/dev/null || echo unknown)"
L9_GOVERNANCE_REF_STATE=unknown
gov_origin="$(git -C "$GOV_DIR" rev-parse --verify --quiet "origin/$GOV_BRANCH" 2>/dev/null || echo unknown)"
if [ "$L9_GOVERNANCE_REVISION" = "unknown" ]; then
  warn "governance clone has no resolvable HEAD — the tree is not a usable checkout"
elif [ "$gov_origin" = "unknown" ]; then
  L9_GOVERNANCE_REF_STATE=unverified
  warn "governance clone is at $L9_GOVERNANCE_REVISION but origin/$GOV_BRANCH is unresolvable"
  warn "  freshness is UNVERIFIED — treat this build as potentially stale"
elif [ "$L9_GOVERNANCE_REVISION" = "$gov_origin" ]; then
  L9_GOVERNANCE_REF_STATE=current
  note "governance clone at $L9_GOVERNANCE_REVISION (matches origin/$GOV_BRANCH)"
else
  L9_GOVERNANCE_REF_STATE=stale
  warn "governance clone is STALE: HEAD $L9_GOVERNANCE_REVISION != origin/$GOV_BRANCH $gov_origin"
  warn "  the adapter, hooks and gates below come from the STALE tree"
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
SETUP_RC=$?
# The canonical setup's exit code is part of the contract. It used to be
# discarded, so "adapter NOT wired in ANY workspace" still ended with
# "cloud bootstrap complete" and exit 0 — Anthropic then cached that
# environment as a successful build (audit B-02). The durable env below is
# still written, because a half-built environment is easier to diagnose with
# its variables in place than without them; the exit code carries the verdict.

# --- 3) Durable exports for in-session Bash --------------------------------
# CLAUDE_ENV_FILE is not present in every cloud runtime, so write our own env
# file and source it from the shell profile when it is absent. Both paths are
# idempotent — this stub re-runs on every environment rebuild.
L9_ENV_FILE="$HOME/.l9/cloud-session.env"
mkdir -p "$(dirname "$L9_ENV_FILE")"
{
  echo "# Written by L9 setup.bootstrap.sh — do not edit by hand."
  echo "export L9_STUB_REVISION=$(printf %q "$L9_STUB_REVISION")"
  echo "export L9_GOVERNANCE_DIR=$(printf %q "$GOV_DIR")"
  echo "export L9_GOVERNANCE_SURFACE=claude-code"
  echo "export L9_GOVERNANCE_REVISION=$(printf %q "$L9_GOVERNANCE_REVISION")"
  echo "export L9_GOVERNANCE_REF_STATE=$(printf %q "$L9_GOVERNANCE_REF_STATE")"
  # Names only. Lets an in-session check report a credential the stub already
  # unset in its own process — otherwise the leak is invisible after build.
  echo "export L9_ACCOUNT_FIELD_LEAKS=$(printf %q "$L9_LEAKED_NAMES")"
  echo "export GRAPHITI_MCP_URL=$(printf %q "$GRAPHITI_MCP_URL")"
  if [ -n "${L9_CAPABILITY_BROKER_URL:-}" ]; then
    echo "export L9_CAPABILITY_BROKER_URL=$(printf %q "$L9_CAPABILITY_BROKER_URL")"
  fi
  # No GH_TOKEN export: the platform proxy injects its own credential.
  # ADR-0006 + Infisical plane. SCOPE: these unsets reach interactive and login
  # shells only. Non-interactive `bash -c` — which is how an agent runs every
  # command — does not read .bashrc or .profile at any position; bash consults
  # $BASH_ENV instead, and a setup script cannot set that for a shell the
  # harness spawns later. Treat this as hygiene for human shells, NEVER as the
  # control that keeps credentials out of agent commands. That control is the
  # account field containing no credential, which is why the names are recorded
  # above rather than silently unset.
  echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
  echo "unset GRAPHITI_MCP_TOKEN INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
  echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
  echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN GITHUB_TOKEN GH_TOKEN"
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

# --- 4) Capability plane readiness (report, never block) -------------------
# Same check every surface runs after install.sh -> bootstrap_agent_environment.sh.
# Do NOT paste GRAPHITI_MCP_TOKEN / Infisical UA / password to turn this green.
# A URL being SET is not a broker being THERE. The previous line printed a
# reassuring note for any non-empty string, so a broker host that does not
# resolve produced the same green output as a working one, and the capability
# plane's own remediation text ("configure L9_CAPABILITY_BROKER_URL") pointed at
# a variable that was already configured. Resolve the name; report what is true.
broker_host() {
  # scheme:// stripped, then everything up to the first / or : — no subshell loop.
  printf '%s' "${1#*://}" | cut -d/ -f1 | cut -d: -f1
}
resolves() {
  if command -v getent >/dev/null 2>&1; then
    getent hosts "$1" >/dev/null 2>&1 && return 0
    return 1
  fi
  python3 -c 'import socket,sys; socket.getaddrinfo(sys.argv[1],443)' "$1" >/dev/null 2>&1
}
if [ -n "${L9_CAPABILITY_BROKER_URL:-}" ]; then
  bh="$(broker_host "$L9_CAPABILITY_BROKER_URL")"
  if [ -z "$bh" ]; then
    warn "L9_CAPABILITY_BROKER_URL is set but names no host: $L9_CAPABILITY_BROKER_URL"
  elif resolves "$bh"; then
    note "capability broker: $L9_CAPABILITY_BROKER_URL (host resolves; credentials stay on the broker)"
    note "  reachability beyond DNS is probed by: python3 ops/secrets/probe_broker.py"
  else
    warn "capability broker host '$bh' DOES NOT RESOLVE — capabilities stay DEGRADED"
    warn "  the variable is configured; the endpoint is not reachable. Pasting it again"
    warn "  will not change this. Fix broker delivery or correct the URL; never paste a"
    warn "  credential to route around a missing broker."
    warn "  If least-privilege egress is in force, also confirm '$bh' is in the"
    warn "  Network access custom host list (web/network-policy.md)."
  fi
else
  warn "L9_CAPABILITY_BROKER_URL unset — Sonar/Semgrep/Graphiti capabilities DEGRADED"
  warn "  Honest posture. Fix broker delivery; do not paste Infisical or Graphiti secrets."
fi
note "memory front door URL: $GRAPHITI_MCP_URL (no bearer in this process)"

if [ "$SETUP_RC" -ne 0 ]; then
  warn "cloud bootstrap FAILED — web/setup.sh exited $SETUP_RC"
  warn "  the adapter is not wired; see ~/.l9/claude/bootstrap-state.json"
  exit "$SETUP_RC"
fi
note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
exit 0
