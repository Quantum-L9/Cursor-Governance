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
# from main on every edit. This stub is stable and does one job: obtain the
# governance clone and hand off to the canonical web/setup.sh from it, so
# setup.sh edits reach every new session with no re-paste. Everything else it
# once did (account-environment normalization, secret and retired-variable
# scrubbing, the durable cloud-session.env, the memory-interpreter binding and
# the status notes) runs from web/setup.bootstrap_steps.sh, which setup.sh
# sources on this hand-off, so the stub fits the Setup field (at most 100
# lines of at most 200 bytes once comments are stripped; the paste text is
# docs/account-fields/SETUP_FIELD.txt).
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
L9_STUB_REVISION="2026-11-20.4"
export L9_STUB_REVISION

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

# Cloud-only install paths (no-op on local CLI, which wires .claude/ from the repo).
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- 1) Governance SSOT location -------------------------------------------
# The cloud SSOT is always the real $HOME path; a pasted L9_GOVERNANCE_DIR is
# normalized (with a warning) by web/setup.bootstrap_steps.sh.
GOV_DIR="$HOME/.cursor-governance"

# True when the checkout at $1 has origin $2, compared case-insensitively and
# without a trailing slash or ".git". A directory's name is not its identity:
# only a checkout whose origin IS the expected repository may supply
# governance code that this stub will execute.
l9_origin_is() {
  local url
  url="$(git -C "$1" remote get-url origin 2>/dev/null)"
  url="$(printf '%s' "$url" | tr '[:upper:]' '[:lower:]')"
  url="${url%/}"
  url="${url%.git}"
  [ "$url" = "$2" ]
}
L9_GOV_ORIGIN="https://github.com/quantum-l9/cursor-governance"

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
  if ! git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR"; then
    rm -rf "$GOV_DIR"
    warn "governance clone FAILED — $GOV_REMOTE could not be read"
    # Since 2026-11-16 Quantum-L9/Cursor-Governance is PRIVATE, and the Setup
    # script runs with NO GitHub credential: the platform does not hand Setup
    # the environment's secrets, and its git proxy authenticates only after the
    # session starts. Measured 2026-11-20 in a session that listed the repository
    # under Repositories AND had it as a session source: the network clone still
    # failed ("could not read Username"). What Setup does have is every session
    # source already checked out under the working directory, so clone from that.
    _l9_local=""
    for _l9_c in Cursor-Governance cursor-governance; do
      if [ -d "$PWD/$_l9_c/.git" ] && l9_origin_is "$PWD/$_l9_c" "$L9_GOV_ORIGIN"; then
        _l9_local="$PWD/$_l9_c"
        break
      fi
    done
    if [ -n "$_l9_local" ] && git clone --depth 1 --branch "$GOV_BRANCH" "file://$_l9_local" "$GOV_DIR"; then
      git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE"
      note "governance cloned from the session checkout $_l9_local"
    else
      rm -rf "$GOV_DIR"
      warn "  add Quantum-L9/Cursor-Governance AND Quantum-L9/.github under Repositories in"
      warn "  this environment's settings (session title bar -> environment -> Edit), then"
      warn "  start a NEW session; also confirm the network allows github.com"
      exit 1
    fi
  fi
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
# web/setup.sh writes the durable env and the status notes on exit (its EXIT
# trap, web/setup.bootstrap_steps.sh) and exits with its own verdict; the
# stub propagates that code so a failed build is never cached as a success
# (audit B-02).
exit "$SETUP_RC"
# L9-PASTE-END — the Setup script field ends at the line above (exit "$SETUP_RC").
