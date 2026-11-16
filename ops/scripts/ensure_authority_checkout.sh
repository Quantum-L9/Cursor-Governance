#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: ops/scripts/ensure_authority_checkout.sh
#   layer: ops
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-11-14
#
# Provision the governance-managed Quantum-L9/.github checkout that the default
# projection binding resolves in EVERY workspace (ops/autonomy/host_binding.py ->
# ops/scripts/coding_projection_status.py managed_authority_root()).
#
# Before this, the authority checkout was found only by `--authority-root`,
# L9_AUTHORITY_ROOT, or a `.github` clone inside or beside the workspace, so the
# operating plane bound in one repository and reported
# CANONICAL_AUTHORITY_CHECKOUT_NOT_AVAILABLE in the next.
#
# Contract:
#   - L9_AUTHORITY_ROOT set: the operator chose the checkout; nothing is touched.
#   - Absent: staged as a FULL checkout (never shallow — the verifiers refuse one),
#     then moved into place in one rename. A killed run resumes the staging dir.
#   - Present: fetch origin/main at most every L9_AUTHORITY_FETCH_TTL_S (900 s),
#     unshallow if shallow, fast-forward `main` only when HEAD is `main` and clean.
#   - Never resets, deletes, force-checks-out, or edits a checkout it did not
#     create cleanly. A checkout it cannot safely move is reported as is; the
#     binding then reports STALE/UNVERIFIED honestly.
#   - Prints one `AUTHORITY:` line. Always exits 0 (SessionStart is fail-open).
set -uo pipefail

# Trust boundary: the authority source is a constant, never an inherited value.
AUTHORITY_REMOTE="https://github.com/Quantum-L9/.github.git"
ROOT="${L9_AUTHORITY_MANAGED_ROOT:-$HOME/.l9/authority/.github}"
STAGING="${ROOT}.partial"
TTL="${L9_AUTHORITY_FETCH_TTL_S:-900}"

say() { printf 'AUTHORITY: %s\n' "$*"; }
g() { git -C "$1" "${@:2}"; }
short() { g "$1" rev-parse --short=7 "$2" 2>/dev/null || echo "?"; }

origin_ok() {
  case "$(g "$1" config --get remote.origin.url 2>/dev/null)" in
    https://github.com/Quantum-L9/.github | https://github.com/Quantum-L9/.github.git \
      | git@github.com:Quantum-L9/.github.git | git@github.com:Quantum-L9/.github \
      | ssh://git@github.com/Quantum-L9/.github.git | ssh://git@github.com/Quantum-L9/.github) return 0 ;;
  esac
  return 1
}

# Quantum-L9/.github is private (2026-11-16): an anonymous fetch fails. gh's
# credential is offered after any helper the user configured (never instead of
# one), the same transport ops/scripts/org_dotgithub.py uses.
AUTH=()
if command -v gh >/dev/null 2>&1; then
  AUTH=(-c "credential.helper=!gh auth git-credential")
fi
# Why a fetch can fail, named once for both messages below.
FETCH_CAUSE="offline, no GitHub credential for the private repository, or a Claude Code cloud session not started with Quantum-L9/.github selected"

fetch_main() {
  # A full fetch of main; unshallows a shallow checkout in the same call.
  if [ "$(g "$1" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
    GIT_TERMINAL_PROMPT=0 git ${AUTH[@]+"${AUTH[@]}"} -C "$1" fetch --quiet --unshallow origin "+refs/heads/main:refs/remotes/origin/main"
  else
    GIT_TERMINAL_PROMPT=0 git ${AUTH[@]+"${AUTH[@]}"} -C "$1" fetch --quiet origin "+refs/heads/main:refs/remotes/origin/main"
  fi
}

if [ -n "${L9_AUTHORITY_ROOT:-}" ]; then
  say "operator path L9_AUTHORITY_ROOT=${L9_AUTHORITY_ROOT} (managed checkout not used)"
  exit 0
fi

if [ ! -e "$ROOT" ]; then
  mkdir -p "$(dirname "$ROOT")" 2>/dev/null || { say "UNAVAILABLE cannot create $(dirname "$ROOT")"; exit 0; }
  if [ -e "$STAGING" ] && ! { [ -d "$STAGING/.git" ] && origin_ok "$STAGING"; }; then
    say "UNAVAILABLE staging path $STAGING exists and is not an authority checkout — inspect and remove it"
    exit 0
  fi
  if [ ! -d "$STAGING/.git" ]; then
    if ! { git init --quiet "$STAGING" && g "$STAGING" remote add origin "$AUTHORITY_REMOTE"; }; then
      say "UNAVAILABLE git init failed at $STAGING"
      exit 0
    fi
  fi
  if ! fetch_main "$STAGING"; then
    say "UNAVAILABLE first fetch of $AUTHORITY_REMOTE failed ($FETCH_CAUSE) — staged at $STAGING, resumes next session"
    exit 0
  fi
  if ! { g "$STAGING" checkout --quiet -B main refs/remotes/origin/main \
    && g "$STAGING" branch --quiet --set-upstream-to=origin/main main \
    && mv "$STAGING" "$ROOT"; }; then
    say "UNAVAILABLE could not finish staging $STAGING"
    exit 0
  fi
  say "PROVISIONED path=$ROOT main=$(short "$ROOT" refs/remotes/origin/main)"
  exit 0
fi

if [ ! -d "$ROOT/.git" ] || ! origin_ok "$ROOT"; then
  say "UNAVAILABLE $ROOT is not a Quantum-L9/.github checkout — left untouched"
  exit 0
fi

fetched="cached"
age=999999
if [ -f "$ROOT/.git/FETCH_HEAD" ]; then
  age=$(( $(date +%s) - $(stat -c %Y "$ROOT/.git/FETCH_HEAD" 2>/dev/null || stat -f %m "$ROOT/.git/FETCH_HEAD" 2>/dev/null || echo 0) ))
fi
if [ "$age" -ge "$TTL" ] || [ "$(g "$ROOT" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
  if fetch_main "$ROOT"; then fetched="fetched"; else fetched="fetch-failed($FETCH_CAUSE)"; fi
fi

branch="$(g "$ROOT" symbolic-ref --quiet --short HEAD 2>/dev/null || echo DETACHED)"
note=""
if [ "$branch" != "main" ]; then
  note=" — HEAD is $branch, not main; left as is (domains report STALE until it is main)"
elif [ -n "$(g "$ROOT" status --porcelain 2>/dev/null)" ]; then
  note=" — working tree dirty; left as is"
elif ! g "$ROOT" merge --quiet --ff-only refs/remotes/origin/main >/dev/null 2>&1; then
  note=" — main cannot fast-forward to origin/main; left as is"
fi
say "READY path=$ROOT head=$(short "$ROOT" HEAD) main=$(short "$ROOT" refs/remotes/origin/main) ${fetched}${note}"
exit 0
