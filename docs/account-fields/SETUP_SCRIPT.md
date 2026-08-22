# Setup script — paste-ready

**Field:** claude.ai/code → environment → **Setup script**
**Revision:** `2026-08-21.3` · **Checksum:** `e0702860d71168ef`
**Applies to:** NEW sessions only.

Source of truth: `environment/agents/adapters/claude-code/web/setup.bootstrap.sh`.
Paste the stub, never `web/setup.sh`. The field is a copy, not a live link, so a
full script pasted into it drifts from `main` on every edit; the stub is stable
and hands off to `web/setup.sh` from the governance clone, which means setup.sh
changes reach every new session with no re-paste.

## Before you paste — copy the current field out first

A field cannot be read back from inside the sandbox, so whatever is in it now is
the only copy. If `verify_account_env.py` reports the field is **ahead** of HEAD,
it is running bootstrap code that exists in no commit: copy it out, diff it
against the stub below, and commit anything it added. Pasting over an ahead field
destroys that code silently.

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py   # names the direction
```

## Paste this

```bash
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
L9_STUB_REVISION="2026-08-21.3"

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

# Infisical / capability plane (same contract as ops/scripts/bootstrap_agent_environment.sh).
# Model-controlled surfaces never hold UA, password, PAT, or downstream tokens.
# Credentials stay in Infisical behind the broker. A pasted "Infisical password"
# configuration here is a master key — strip it.
for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
              INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
              GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID \
              AWS_SESSION_TOKEN; do
  leaked_value="${!leaked:-}"
  [ -n "$leaked_value" ] || continue
  # `proxy-injected` is the platform's sentinel for a credential it proxies, not
  # a credential. Unsetting it would break the very proxying it announces.
  if [ "$leaked_value" = "proxy-injected" ]; then
    note "$leaked holds the platform proxy sentinel (no credential material) — leaving it"
    continue
  fi
  warn "$leaked is set — PROHIBITED on this surface (Infisical/capability plane); unsetting"
  unset "$leaked"
done
# GH_TOKEN / GITHUB_TOKEN are NOT swept, and must not be. The earlier sweep read
# "the platform proxy authenticates" as covering both tools. It does not:
#
#   git ls-remote  with no GH_TOKEN -> works   (the proxy authenticates git)
#   gh api /user   with no GH_TOKEN -> refuses ("please run gh auth login")
#
# So clearing it disabled every `gh` path on the surface, including the REST
# calls docs/DEGRADED_MODE_CONTRACT.md lists as working and the open-PR telemetry
# ops/scripts/pr_overlap_check.py needs before `make pr` may push. On a hosted
# session this value is issued by the platform, not pasted by a human.
#
# The contract that still holds is on the FIELD, not the process: never paste a
# PAT into Environment variables. verify_account_env.py reports a prohibited
# credential there. Unsetting at runtime was the wrong lever — it could not tell
# a pasted PAT from the platform's own credential, and destroyed both.

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
  echo "export GRAPHITI_MCP_URL=$(printf %q "$GRAPHITI_MCP_URL")"
  if [ -n "${L9_CAPABILITY_BROKER_URL:-}" ]; then
    echo "export L9_CAPABILITY_BROKER_URL=$(printf %q "$L9_CAPABILITY_BROKER_URL")"
  fi
  # No GH_TOKEN export and no GH_TOKEN unset: the platform issues it, `gh` needs
  # it, and ~/.profile sources this file unguarded, so an unset here would strip
  # it from every login shell.
  # ADR-0006 + Infisical plane: keep vault credentials out of every in-session shell.
  echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
  echo "unset GRAPHITI_MCP_TOKEN INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
  echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
  echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
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
if [ -n "${L9_CAPABILITY_BROKER_URL:-}" ]; then
  note "capability broker: $L9_CAPABILITY_BROKER_URL (credentials stay on the broker)"
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
```

## Verify the paste took

Start a NEW session, then:

```bash
grep L9_STUB_REVISION ~/.l9/cloud-session.env      # expect 2026-08-21.3
make claude-env                                    # structural + RUNTIME verdicts
```

The stub records its own revision into `~/.l9/cloud-session.env` on every run, so
a later session can answer "is the pasted stub current?" without reading the field.
