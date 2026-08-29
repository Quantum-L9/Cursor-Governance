#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code — cloud-only SessionStart dependency helper.
#
# Owns the per-session, per-repository work that used to live in web/setup.sh:
# each REPOSITORY's own language toolchain (uv.lock / pip / node) and the
# pre-commit warm for CANONICAL_LAW §12. The account Setup script is
# environment provisioning — Anthropic caches it and does not re-run it on
# every session — so this helper is invoked from the committed SessionStart
# hook (session_start_claude_governance.sh), which runs on every session and
# resume.
#
# PER REPOSITORY, not per workspace. A cloud container puts several
# repositories side by side and `--workspace` then names the CONTAINER. This
# helper used to fingerprint manifests at that path, find none, install
# nothing, and still report `toolchain ready` — while `toolchain_present()`
# tested `<container>/.venv/bin/python`, which cannot exist, so the cache
# branch was unreachable too. Repository environments consequently never
# received a lock refreshed in the same session. Roots now come from
# ops/scripts/lib/workspace_roots.py, the one place that answers
# container-vs-checkout for the whole bootstrap.
#
# Contract:
#   * Cloud-only: acts only when CLAUDE_CODE_REMOTE=true (CLI/Desktop manage
#     their own toolchains via the repo's normal dev workflow).
#   * Idempotent + fingerprint-cached PER REPOSITORY: a stamp under ~/.l9/claude/
#     records the hash of that repository's dependency manifests; an unchanged
#     fingerprint with a proven toolchain re-installs nothing.
#   * Proof-gated: the stamp records APPLIED state, not attempted state. A
#     repository is only reported ready when its lock is proven applied.
#   * Fail-open: always exits 0; a dependency failure degrades the session,
#     it never blocks it.
#   * Bounded: a synchronous run stays within L9_SESSION_DEPS_BUDGET seconds
#     (default 20) ACROSS ALL REPOSITORIES; if the budget expires the helper
#     re-launches itself detached to finish in the background.
#
# Usage: bash session_deps_cloud.sh [--workspace <dir>] [--budget <seconds>]
# ---------------------------------------------------------------------------
set -uo pipefail

BUDGET="${L9_SESSION_DEPS_BUDGET:-20}"
WORKSPACE="$PWD"

while [ $# -gt 0 ]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --budget)    BUDGET="${2:?--budget needs seconds}"; shift 2 ;;
    *) echo "session_deps_cloud.sh: unknown argument '$1'" >&2; exit 0 ;;
  esac
done

# Cloud-only by construction: the local CLI/Desktop path never needs an
# account-environment dependency install, and this helper must never mutate
# a developer checkout's toolchain as a session side effect.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo "session-deps: not a cloud session (CLAUDE_CODE_REMOTE != true) — skipping"
  exit 0
fi

if [ ! -d "$WORKSPACE" ]; then
  echo "session-deps: workspace '$WORKSPACE' does not exist — skipping"
  exit 0
fi

have() { command -v "$1" >/dev/null 2>&1; }

STAMP_DIR="$HOME/.l9/claude"
mkdir -p "$STAMP_DIR"

# --- Repository roots ------------------------------------------------------
# The shared resolver is authoritative. If it cannot be reached the helper
# degrades to the workspace itself, which is exactly the pre-fix behaviour —
# never worse, and still fail-open.
resolve_roots() {
  local lib script
  script="$(cd "$(dirname "$0")" && pwd)"
  while [ "$script" != "/" ]; do
    lib="$script/ops/scripts/lib/workspace_roots.py"
    if [ -f "$lib" ]; then
      python3 -c "
import sys
sys.path.insert(0, '$script/ops/scripts/lib')
from pathlib import Path
from workspace_roots import workspace_roots
for root in workspace_roots(Path('$WORKSPACE')):
    print(root)
" 2>/dev/null && return 0
      break
    fi
    script="$(dirname "$script")"
  done
  printf '%s\n' "$WORKSPACE"
}

# --- Fingerprint: one repository's own manifests, plus tool presence --------
file_hash() {
  shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' \
    || md5sum "$1" 2>/dev/null | awk '{print $1}'
}

fingerprint() {
  local repo="$1" stamp_input="" f
  for f in uv.lock pyproject.toml requirements.txt package.json pnpm-lock.yaml package-lock.yaml .pre-commit-config.yaml; do
    if [ -f "$repo/$f" ]; then
      stamp_input="$stamp_input|$f:$(file_hash "$repo/$f")"
    fi
  done
  stamp_input="$stamp_input|uv:$(uv --version 2>/dev/null || echo none)"
  stamp_input="$stamp_input|node:$(node --version 2>/dev/null || echo none)"
  stamp_input="$stamp_input|pnpm:$(pnpm --version 2>/dev/null || echo none)"
  stamp_input="$stamp_input|npm:$(npm --version 2>/dev/null || echo none)"
  printf '%s' "$stamp_input" | shasum -a 256 | awk '{print $1}'
}

# --- Applied-state proof (T4) ----------------------------------------------
# The old stamp recorded that an install was ATTEMPTED. That is why a pass which
# installed nothing at all could still report `toolchain ready`. This proves the
# lock is APPLIED, so the readiness claim is falsifiable. A repository with no
# recognised manifest is vacuously proven — there is nothing to apply.
toolchain_proven() {
  local repo="$1" rc
  if [ -f "$repo/uv.lock" ]; then
    [ -x "$repo/.venv/bin/python" ] || return 1
    have uv || return 1
    # `--check` exit codes carry different meanings and must not be collapsed:
    #   0  environment matches the lock under this resolution — proven
    #   1  environment is OUTDATED — NOT proven, and no other resolution may
    #      overrule that. A blanket `|| plain-check` fallback would let the
    #      narrower non-dev resolution pass an environment the dev resolution
    #      just rejected, re-creating the false readiness this proof exists to
    #      prevent.
    #   2  usage error, in practice "extra `dev` is not defined" — the dev
    #      resolution does not apply here, so fall through to the plain one.
    #      This is the ONLY case that may fall through.
    ( cd "$repo" && uv sync --locked --extra dev --check >/dev/null 2>&1 )
    rc=$?
    if [ "$rc" -eq 2 ]; then
      ( cd "$repo" && uv sync --locked --check >/dev/null 2>&1 ) || return 1
    elif [ "$rc" -ne 0 ]; then
      return 1
    fi
  fi
  if [ -f "$repo/package.json" ] && [ ! -d "$repo/node_modules" ]; then
    return 1
  fi
  return 0
}

# --- Per-repository install -------------------------------------------------
install_repo() {
  local repo="$1" failed=0
  echo "session-deps: installing toolchain for $repo" >&2
  if [ -f "$repo/uv.lock" ] && have uv; then
    if ! ( cd "$repo" && { uv sync --locked --extra dev 2>/dev/null || uv sync --locked 2>/dev/null; } ); then
      failed=1
      echo "WARN: $repo uv sync --locked failed" >&2
    fi
  elif [ -f "$repo/pyproject.toml" ] || ls "$repo"/*.py >/dev/null 2>&1; then
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    if [ -f "$repo/pyproject.toml" ]; then
      # NOTE: `--only-binary :all:` is deliberately NOT paired with `-e .` — an
      # editable install must build from source, so that combination can never
      # succeed. Flat-layout multi-package repos cannot be installed editable at
      # all; for those the fallback below is the expected path.
      ( cd "$repo" && \
        pip install --prefer-binary -e '.[dev,server]' 2>/dev/null \
        || pip install --prefer-binary -e '.[dev]' 2>/dev/null \
        || pip install --prefer-binary -r requirements.txt 2>/dev/null \
        || pip install --only-binary :all: ruff mypy pytest build 2>/dev/null ) || true
    else
      pip install --only-binary :all: ruff mypy pytest 2>/dev/null || true
    fi
  fi
  if [ -f "$repo/package.json" ]; then
    ( cd "$repo" && \
      if have pnpm; then pnpm install --ignore-scripts || true
      elif have npm; then npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts || true
      fi )
  fi

  # pre-commit — REQUIRED by CANONICAL_LAW §12 (mandatory `make pr` gate).
  # Warm the hook environments so the first `make pr` does not pay cold-start.
  if [ -f "$repo/.pre-commit-config.yaml" ]; then
    if ! have pre-commit; then
      pip install --only-binary :all: pre-commit 2>/dev/null \
        || python3 -m pip install pre-commit 2>/dev/null \
        || { failed=1; echo "WARN: installing the pre-commit PACKAGE failed — 'make pr' will fail until it is present (allowlist pypi.org). This is pip, not 'pre-commit install', which stays forbidden here." >&2; }
    fi
    if have pre-commit; then
      # Warm hook environments ONLY. Never `pre-commit install`: these repositories
      # have no git commit hook (ops/scripts/run_pr_precommit.sh), and an installed
      # hook runs the catalog without the surface-aware SKIP list, so `git commit`
      # fails on every non-cursor surface via symlinks-check.
      if ! ( cd "$repo" && pre-commit install-hooks 2>/dev/null ); then
        failed=1
        echo "WARN: $repo pre-commit hook warm-up failed — first 'make pr' will fetch hook repos (allowlist github.com)" >&2
      fi
    fi
  fi
  return "$failed"
}

# --- Detached run: install every repository that is not already proven ------
if [ "${SESSION_DEPS_DETACHED:-}" = "1" ]; then
  DEPS_FAILED=0
  while IFS= read -r repo; do
    [ -n "$repo" ] || continue
    install_repo "$repo" || DEPS_FAILED=1
    # Stamp ONLY on proven applied state. Stamping an attempted install is what
    # cached a no-op as success for a whole fingerprint generation.
    if toolchain_proven "$repo"; then
      touch "$STAMP_DIR/deps-$(fingerprint "$repo").stamp"
      echo "session-deps: $repo proven applied" >&2
    else
      DEPS_FAILED=1
      echo "WARN: $repo toolchain not proven applied — no stamp written" >&2
    fi
  done < <(resolve_roots)
  echo "session-deps: install pass complete" >&2
  exit "$DEPS_FAILED"
fi

# --- Synchronous entry: report per repository, work only where needed -------
ROOTS="$(resolve_roots)"
PENDING=""
CACHED=0
TOTAL=0
while IFS= read -r repo; do
  [ -n "$repo" ] || continue
  TOTAL=$((TOTAL + 1))
  fp="$(fingerprint "$repo")"
  if [ -f "$STAMP_DIR/deps-$fp.stamp" ] && toolchain_proven "$repo"; then
    CACHED=$((CACHED + 1))
  else
    PENDING="$PENDING $(basename "$repo")"
  fi
done <<EOF
$ROOTS
EOF

if [ -z "$PENDING" ]; then
  echo "session-deps: $CACHED/$TOTAL repositories cached and proven — nothing to install"
  exit 0
fi

LOG="$STAMP_DIR/deps-session-$(date +%s).log"
(
  SESSION_DEPS_DETACHED=1 "$BASH" "$0" --workspace "$WORKSPACE" --budget "$BUDGET" \
    >"$LOG" 2>&1
) &
RUN_PID=$!
END=$(( $(date +%s) + BUDGET ))
while kill -0 "$RUN_PID" 2>/dev/null; do
  [ "$(date +%s)" -lt "$END" ] || break
  sleep 1
done

if kill -0 "$RUN_PID" 2>/dev/null; then
  echo "session-deps: provisioning$PENDING continues in background (budget ${BUDGET}s exceeded) — see $LOG"
  exit 0
fi
wait "$RUN_PID" 2>/dev/null || true

# Re-report from proof, never from the fact that a pass ran.
READY=""
UNPROVEN=""
while IFS= read -r repo; do
  [ -n "$repo" ] || continue
  if toolchain_proven "$repo"; then
    READY="$READY $(basename "$repo")"
  else
    UNPROVEN="$UNPROVEN $(basename "$repo")"
  fi
done <<EOF
$ROOTS
EOF

if [ -n "$UNPROVEN" ]; then
  echo "session-deps: proven[$READY ] UNPROVEN[$UNPROVEN ] — those repositories run degraded (see $LOG)"
else
  echo "session-deps: all $TOTAL repositories proven applied[$READY ]"
fi
exit 0
