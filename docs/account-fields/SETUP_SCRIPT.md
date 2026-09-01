# Setup script — paste-ready

**Field:** claude.ai/code → environment → **Setup script**
**Revision:** `2026-08-29.1` · **Checksum:** `a435d71d53771d79`
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

Copy **only** the script itself: the first line of the block below is
`#!/usr/bin/env bash`, immediately followed by an `L9-PASTE-BEGIN` marker, and
the last is an `L9-PASTE-END` marker just after `exit 0`. Do **not** include
the triple-backtick fence lines that open and close the block, this heading, or
the prose that follows the block.

Selecting a rendered page accurately is fiddly, so prefer copying the raw file —
it is byte-identical to the block below and carries no fence to catch:

```bash
cat environment/agents/adapters/claude-code/web/setup.bootstrap.sh
```

> **Why the fence lines matter.** A markdown fence is three backticks. Bash reads
> that as an empty command substitution plus one leftover backtick, which opens a
> substitution that swallows the entire stub. Measured on 2026-08-22, pasting the
> fence executed the stub's English comments as shell commands, ran `git clone`
> with an empty target directory, and ended in `exit 127` with the environment
> half-built and no line naming the cause. The stub is now backtick-free and
> detects the contaminated paste itself, refusing with a `FATAL` line that names
> the fence — but the environment still will not build until you re-paste
> without the fence lines.

```bash
#!/usr/bin/env bash
# L9-PASTE-BEGIN — the Setup script field starts at the line above (#!/usr/bin/env bash).
# ---------------------------------------------------------------------------
# L9 Claude Code cloud Setup script — startup stub (Web · Mobile · --cloud).
#
# THIS FILE CONTAINS NO BACKTICKS, DELIBERATELY. Do not add any, and do not
# "restore" markdown quoting to these comments. Reason, measured 2026-08-22:
# docs/account-fields/SETUP_SCRIPT.md presents this stub inside a fenced
# markdown code block. A human who selects the section rather than the fence body
# pastes that fence into the field. A fence is THREE backticks, an odd count, so
# bash opens a command substitution that never closes and swallows the rest of
# the file. Every backtick that used to sit in these comments then closed or
# reopened that substitution, which pushed the following prose out of comment
# position and ran it as shell. The measured result was English executed as
# commands, git clone invoked with an empty target directory, and exit 127 with
# the environment half-built.
#
# With zero backticks in the file the damage is contained: the substitution
# opened by the leading fence now runs to the CLOSING fence and no further, so
# the stub is executed whole, in a subshell, instead of being shredded into
# fragments of executable English. That is still wrong -- a subshell discards
# every export and the exit code -- which is why the paste-integrity guard below
# detects the fence and refuses outright. Both properties are enforced by
# tests/test_account_drift_and_platform_blocks.py.
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
# No set -e: a single failed probe must never abort the environment build.
# The two hard failures are the governance clone and a missing setup.sh, which
# exit non-zero explicitly.
set -uo pipefail

# --- 0) Paste-integrity guard ----------------------------------------------
# Fires when the Setup script field contains the markdown fence lines that wrap
# this stub in docs/account-fields/SETUP_SCRIPT.md, not just the stub itself.
#
# A fence is three backticks. Bash reads that as backtick-pair (an empty command
# substitution) plus one LEFTOVER backtick, which opens a command substitution
# that runs until the closing fence closes it. Everything between the two fences
# -- this entire file -- is then executed inside that substitution instead of at
# top level, so every export, every variable and the exit code are discarded
# into a subshell the environment build never sees, and this stub's own stdout
# is handed back to the parent shell to execute as a command.
#
# Detection is on the CAUSE, not a symptom: read our own source and look for a
# fence line. This file is backtick-free by contract (enforced by
# tests/test_account_drift_and_platform_blocks.py), so a fence in it can only
# have arrived with the paste. That is exact -- it cannot fire on a legitimate
# invocation, however the platform chooses to launch the script.
#
# The fence pattern is built with printf octal escapes because writing three
# literal backticks here would itself break the no-backtick contract above.
#
# BASH_SUBSHELL is the fallback for the case where the running script is not
# readable: it is 0 at top level and non-zero inside a command substitution. It
# is deliberately NOT the primary signal, because a platform that legitimately
# wrapped this script in a subshell would trip it and block a healthy build.
_l9_self="${BASH_SOURCE[0]:-$0}"
_l9_fence="$(printf '\140\140\140')"
if [ -r "$_l9_self" ]; then
  if grep -qF "$_l9_fence" "$_l9_self"; then _l9_contaminated=1; else _l9_contaminated=0; fi
else
  if [ "${BASH_SUBSHELL:-0}" -ne 0 ]; then _l9_contaminated=1; else _l9_contaminated=0; fi
fi
unset _l9_self _l9_fence

# Report to stderr, never stdout: in the contaminated case stdout is the
# substitution's captured value, which the parent shell would then try to run.
if [ "$_l9_contaminated" -ne 0 ]; then
  printf '%s\n' \
    'L9 bootstrap FATAL: the Setup script field contains markdown fence lines.' \
    'L9 bootstrap FATAL:   You copied the code block MARKERS along with the code.' \
    'L9 bootstrap FATAL:   Nothing below this point ran at top level; the environment is NOT built.' \
    'L9 bootstrap FATAL:   Re-paste ONLY the lines from the L9-PASTE-BEGIN marker' \
    'L9 bootstrap FATAL:   through the L9-PASTE-END marker -- no fence lines, no prose.' >&2
  exit 2
fi
unset _l9_contaminated

# Bump on EVERY change to this file. The Setup script field is a copy-paste, not
# a live link, so the pasted stub silently drifts from main and there is no way
# to see it from inside the sandbox. Recording the revision that actually ran
# turns "is the pasted stub current?" from unanswerable into a comparison
# (audit B-06). verify_account_env.py reads it back from cloud-session.env.
L9_STUB_REVISION="2026-08-29.1"

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

# Cloud-only install paths (no-op on local CLI, which wires .claude/ from the repo).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- 1) Normalize the account environment ---------------------------------
# The Environment variables field is literal .env text: Anthropic does NOT
# expand $HOME. A pasted L9_GOVERNANCE_DIR=$HOME/.cursor-governance arrives
# as that literal string, which would clone into a directory named $HOME and
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

# The Autonomy Surface Profile matches on the exact surface id. claude-code-mobile
# is not in the allow-list (ops/autonomy/surface_profile.yaml when:), so a
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
#
# GRAPHITI_MCP_TOKEN and CONTEXT7_API_KEY are deliberately NOT in this list, for
# the same reason GH_TOKEN is not (see the block below): they are MCP transport
# credentials the platform may proxy, and sweeping the announcement disables the
# proxying without removing any secret. Neither is ever pasted into the account
# variables field and neither is exported with a value by this script.
# mcp.template.json references them as ${VAR}, so a proxied value reaches the
# MCP client and nothing else; with no value proxied the servers behave exactly
# as before (Graphiti unauthenticated, Context7 simply absent).
for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
              INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
              AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID \
              AWS_SESSION_TOKEN; do
  leaked_value="${!leaked:-}"
  [ -n "$leaked_value" ] || continue
  # proxy-injected is the platform's sentinel for a credential it proxies, not
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
# So clearing it disabled every gh path on the surface, including the REST
# calls docs/DEGRADED_MODE_CONTRACT.md lists as working and the open-PR telemetry
# ops/scripts/pr_overlap_check.py needs before make pr may push. On a hosted
# session this value is issued by the platform, not pasted by a human.
#
# The contract that still holds is on the FIELD, not the process: never paste a
# PAT into Environment variables. verify_account_env.py reports a prohibited
# credential there. Unsetting at runtime was the wrong lever — it could not tell
# a pasted PAT from the platform's own credential, and destroyed both.
#
# CAVEAT for tools that are NOT gh (observed 2026-08-22): the platform value is
# accepted by gh because the agent proxy is preconfigured for it, and by git
# because the proxy injects credentials. A tool that authenticates DIRECTLY to
# api.github.com with the literal string gets 401. gh auth status also reports
# "the token in GH_TOKEN is invalid" while gh api user succeeds — so treat
# gh auth status as unreliable here and probe with a real REST call instead.
#
# The concrete casualty is zizmor in the l9-ci-sdk pre-commit/pre-push gate: its
# artipacked audit lists tags for actions/checkout over the GitHub API and
# 401s, failing make check on a diff that touches no workflow file at all.
# Running that ONE hook with the variable unset is the correct repair — the hook
# still runs and still fail-closes (AGENTS.md: "local zizmor is fail-closed"):
#
#   env -u GH_TOKEN -u GITHUB_TOKEN git push        # gate runs, and passes
#
# Do NOT reach for --no-verify, and do NOT unset it globally here: gh needs
# it, and ~/.profile sources the durable env unguarded.

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
  # The retired capability-plane URL is deliberately not exported.
  # No GH_TOKEN export and no GH_TOKEN unset: the platform issues it, gh needs
  # it, and ~/.profile sources this file unguarded, so an unset here would strip
  # it from every login shell.
  # ADR-0006 + Infisical plane: keep vault credentials out of every in-session shell.
  # No GRAPHITI_MCP_TOKEN / CONTEXT7_API_KEY export and no unset either, on the
  # same GH_TOKEN reasoning above: they are proxied MCP transport credentials
  # referenced as ${VAR} from mcp.template.json, this file is sourced unguarded
  # by ~/.profile, and an unset here would strip a proxied value from every
  # login shell — disabling the proxying rather than removing a secret.
  echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
  echo "unset INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
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

# --- 4) Memory front door (report, never block) ----------------------------
# Capability broker retired 2026-08-29 (never shipped). Do not probe it.
# Graphiti is GRAPHITI_MCP_URL. Do NOT paste GRAPHITI_MCP_TOKEN, CONTEXT7_API_KEY,
# or an Infisical UA into the variables field. Those two MCP transport credentials
# are proxied: mcp.template.json references them as ${VAR}, so a value reaches the
# MCP client only when the platform proxies one, and never via a pasted secret.
note "memory front door URL: ${GRAPHITI_MCP_URL:-unset} (bearer: ${GRAPHITI_MCP_TOKEN:+proxied}${GRAPHITI_MCP_TOKEN:-none})"
note "context7 mcp key: ${CONTEXT7_API_KEY:+proxied}${CONTEXT7_API_KEY:-none}"
note "capability plane: RETIRED (never shipped)"

if [ "$SETUP_RC" -ne 0 ]; then
  warn "cloud bootstrap FAILED — web/setup.sh exited $SETUP_RC"
  warn "  the adapter is not wired; see ~/.l9/claude/bootstrap-state.json"
  exit "$SETUP_RC"
fi
note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
exit 0
# L9-PASTE-END — the Setup script field ends at the line above (exit 0).
```

## Verify the paste took

Start a NEW session, then:

```bash
grep L9_STUB_REVISION ~/.l9/cloud-session.env      # expect 2026-08-29.1
make claude-env                                    # structural + RUNTIME verdicts
```

If `~/.l9/cloud-session.env` does not exist at all, the stub did not run to
completion. Read the environment's setup log and look for a line beginning
`L9 bootstrap FATAL:` — the paste-integrity guard names the fence contamination
explicitly rather than leaving you to read a wall of "command not found".

The stub records its own revision into `~/.l9/cloud-session.env` on every run, so
a later session can answer "is the pasted stub current?" without reading the field.
