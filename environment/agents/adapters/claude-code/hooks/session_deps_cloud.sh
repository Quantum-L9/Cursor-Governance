#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code — cloud-only SessionStart dependency helper.
#
# Owns the per-session, per-repository work that used to live in web/setup.sh:
# the CONSUMER workspace's own language toolchain (uv.lock / pip / node) and
# the pre-commit warm for CANONICAL_LAW §12. The account Setup script is
# environment provisioning — Anthropic caches it and does not re-run it on
# every session — so this helper is invoked from the committed SessionStart
# hook (session_start_claude_governance.sh), which runs on every session and
# resume.
#
# Contract:
#   * Cloud-only: acts only when CLAUDE_CODE_REMOTE=true (CLI/Desktop manage
#     their own toolchains via the repo's normal dev workflow).
#   * Idempotent + fingerprint-cached: a stamp under ~/.l9/claude/ records the
#     hash of the workspace's dependency manifests; an unchanged fingerprint
#     with a present toolchain re-installs nothing.
#   * Fail-open: always exits 0; a dependency failure degrades the session,
#     it never blocks it.
#   * Observing: records the sandbox's own toolchain versions verbatim to
#     ~/.l9/claude/toolchain-observed.json. The fingerprint below always read
#     `uv --version`, but only ever folded it into a SHA-256 nothing can invert,
#     so the one surface whose uv version cannot be checked after the fact left
#     no record of it at all — and `[tool.uv] required-version` was argued from
#     a stale comment instead. The file is the local half; the durable half is
#     the Graphiti write in session_start_claude_governance.sh, because this VM
#     and everything under ~/.l9 are destroyed together.
#   * Bounded: a synchronous run stays within L9_SESSION_DEPS_BUDGET seconds
#     (default 20); if the budget expires the helper re-launches itself
#     detached to finish in the background.
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

# --- Fingerprint: the workspace's own manifests, plus tool presence ---------
file_hash() {
  shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' \
    || md5sum "$1" 2>/dev/null | awk '{print $1}'
}

# Captured verbatim at top level, and deliberately not inside fingerprint():
# that function runs in a command substitution, so a version assigned there
# would not survive into this scope. The expressions are byte-identical to the
# ones fingerprint() used to inline, so recording them changes no cache key and
# invalidates no existing stamp — the values were always read, just discarded.
UV_VERSION="$(uv --version 2>/dev/null || echo none)"
NODE_VERSION="$(node --version 2>/dev/null || echo none)"
PNPM_VERSION="$(pnpm --version 2>/dev/null || echo none)"
NPM_VERSION="$(npm --version 2>/dev/null || echo none)"

# Bare semver, so a consumer comparing against `required-version` does not have
# to parse "uv 0.8.0 (3cdf50e09 2026-06-19 x86_64-unknown-linux-gnu)". Empty
# when uv is absent, which is distinct from a version that is merely old.
UV_SEMVER="$(printf '%s\n' "$UV_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"

fingerprint() {
  local stamp_input=""
  for f in uv.lock pyproject.toml requirements.txt package.json pnpm-lock.yaml package-lock.yaml .pre-commit-config.yaml; do
    if [ -f "$WORKSPACE/$f" ]; then
      stamp_input="$stamp_input|$f:$(file_hash "$WORKSPACE/$f")"
    fi
  done
  stamp_input="$stamp_input|uv:$UV_VERSION"
  stamp_input="$stamp_input|node:$NODE_VERSION"
  stamp_input="$stamp_input|pnpm:$PNPM_VERSION"
  stamp_input="$stamp_input|npm:$NPM_VERSION"
  printf '%s' "$stamp_input" | shasum -a 256 | awk '{print $1}'
}

STAMP_DIR="$HOME/.l9/claude"
mkdir -p "$STAMP_DIR"

# Written before the cache check, not after: the observation is about the
# environment, not about whether an install ran, so a cached toolchain must
# still leave a record of the uv that resolved it.
TOOLCHAIN_OBSERVED="$STAMP_DIR/toolchain-observed.json"
write_toolchain_observation() {
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
  cat >"$TOOLCHAIN_OBSERVED" 2>/dev/null <<EOF || true
{
  "schema": "l9.claude-toolchain-observed.v1",
  "observed_at": "$ts",
  "surface": "claude-code-cloud",
  "uv_version": "$UV_SEMVER",
  "uv_version_raw": "$UV_VERSION",
  "node_version": "$NODE_VERSION",
  "pnpm_version": "$PNPM_VERSION",
  "npm_version": "$NPM_VERSION"
}
EOF
}
write_toolchain_observation
echo "session-deps: observed uv ${UV_SEMVER:-none} (raw: $UV_VERSION) node $NODE_VERSION"

FP="$(fingerprint)"
STAMP="$STAMP_DIR/deps-$FP.stamp"

toolchain_present() {
  if [ -f "$WORKSPACE/uv.lock" ] && [ -f "$WORKSPACE/.venv/bin/python" ]; then
    return 0
  fi
  if { [ -f "$WORKSPACE/package.json" ] && [ -d "$WORKSPACE/node_modules" ]; }; then
    return 0
  fi
  return 1
}

if [ -f "$STAMP" ] && toolchain_present; then
  echo "session-deps: toolchain cached (fingerprint $FP) — nothing to install"
  exit 0
fi

# --- Bounded synchronous run; self-detach on budget expiry -----------------
if [ "${SESSION_DEPS_DETACHED:-}" != "1" ]; then
  (
    # Stamp ONLY on a clean run: the stamp is the cache key that suppresses every
    # future retry, so writing it after a failure caches the failure permanently
    # for this fingerprint.
    if SESSION_DEPS_DETACHED=1 "$BASH" "$0" --workspace "$WORKSPACE" --budget "$BUDGET" \
        >"$STAMP_DIR/deps-$FP.log" 2>&1; then
      touch "$STAMP"
    fi
  ) &
  RUN_PID=$!
  END=$(( $(date +%s) + BUDGET ))
  while kill -0 "$RUN_PID" 2>/dev/null; do
    [ "$(date +%s)" -lt "$END" ] || break
    sleep 1
  done
  if kill -0 "$RUN_PID" 2>/dev/null; then
    echo "session-deps: toolchain install continues in background (budget ${BUDGET}s exceeded) — see $STAMP_DIR/deps-$FP.log"
  else
    wait "$RUN_PID" 2>/dev/null || true
    if [ -f "$STAMP" ]; then
      echo "session-deps: toolchain ready (fingerprint $FP)"
    else
      echo "session-deps: toolchain install incomplete — session runs degraded (see $STAMP_DIR/deps-$FP.log)"
    fi
  fi
  exit 0
fi

# --- Detached run: the actual install (same logic web/setup.sh used to own) -
# DEPS_FAILED is the pass's real exit status. The outer runner stamps the cache
# ONLY on a clean pass, so a failure is retried next session instead of being
# cached as success. Best-effort steps (npm/pnpm, the pip fallback chain) do not
# set it — their last resort is the expected path on flat-layout repos.
DEPS_FAILED=0
echo "session-deps: installing workspace toolchain (fingerprint $FP)" >&2
if [ -f "$WORKSPACE/uv.lock" ] && have uv; then
  if ! ( cd "$WORKSPACE" && uv sync --locked --extra dev 2>/dev/null || uv sync --locked 2>/dev/null ); then
    DEPS_FAILED=1
    echo "WARN: workspace uv sync --locked failed" >&2
  fi
elif [ -f "$WORKSPACE/pyproject.toml" ] || ls "$WORKSPACE"/*.py >/dev/null 2>&1; then
  python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
  if [ -f "$WORKSPACE/pyproject.toml" ]; then
    # NOTE: `--only-binary :all:` is deliberately NOT paired with `-e .` — an
    # editable install must build from source, so that combination can never
    # succeed. Flat-layout multi-package repos cannot be installed editable at
    # all; for those the fallback below is the expected path.
    ( cd "$WORKSPACE" && \
      pip install --prefer-binary -e '.[dev,server]' 2>/dev/null \
      || pip install --prefer-binary -e '.[dev]' 2>/dev/null \
      || pip install --prefer-binary -r requirements.txt 2>/dev/null \
      || pip install --only-binary :all: ruff mypy pytest build 2>/dev/null ) || true
  else
    pip install --only-binary :all: ruff mypy pytest 2>/dev/null || true
  fi
fi
if [ -f "$WORKSPACE/package.json" ]; then
  ( cd "$WORKSPACE" && \
    if have pnpm; then pnpm install --ignore-scripts || true
    elif have npm; then npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts || true
    fi )
fi

# pre-commit — REQUIRED by CANONICAL_LAW §12 (mandatory `make pr` gate).
# Warm the hook environments so the first `make pr` does not pay cold-start.
if [ -f "$WORKSPACE/.pre-commit-config.yaml" ]; then
  if ! have pre-commit; then
    pip install --only-binary :all: pre-commit 2>/dev/null \
      || python3 -m pip install pre-commit 2>/dev/null \
      || { DEPS_FAILED=1; echo "WARN: pre-commit install failed — 'make pr' will fail until installed (allowlist pypi.org)" >&2; }
  fi
  if have pre-commit; then
    # Warm hook environments ONLY. Never `pre-commit install`: this repository has
    # no git commit hook (ops/scripts/run_pr_precommit.sh), and an installed hook
    # runs the catalog without the surface-aware SKIP list, so `git commit` fails
    # on every non-cursor surface via symlinks-check.
    # NOTE: the status is captured from the subshell — a `DEPS_FAILED=1` set inside
    # `( … )` would not reach this scope.
    if ! ( cd "$WORKSPACE" && pre-commit install-hooks 2>/dev/null ); then
      DEPS_FAILED=1
      echo "WARN: pre-commit hook warm-up failed — first 'make pr' will fetch hook repos (allowlist github.com)" >&2
    fi
  fi
fi
echo "session-deps: install pass complete" >&2
exit "$DEPS_FAILED"
