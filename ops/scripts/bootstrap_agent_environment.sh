#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Canonical agent environment bootstrap — SHARED BY EVERY SURFACE.
#
# Claude Code, Codex, Gemini, Manus, the generic adapter, Cursor and CI all call
# this identical script. It owns everything an L9 agent session needs that is
# NOT specific to one vendor's config format:
#
#   1. locked toolchain from uv.lock          (ensure_uv_environment.sh)
#   2. canonical checker binaries             (gitleaks / uvx / pre-commit)
#   3. secret bootstrap                       (ops/secrets/bootstrap_agent_env.sh)
#   4. repository-scoped identity             (Graphiti group, Sonar project)
#   5. shared local git excludes
#   6. readiness preflight                    (gate imports, kernels, L4, holds)
#
#   <any adapter installer>  ->  THIS SCRIPT  ->  ops/*
#
# An adapter is then only responsible for its own vendor wiring — for Claude
# Code that is the settings triad, skill discovery and .mcp.json; for Codex its
# AGENTS block; and so on. If you are about to add something here that names one
# vendor, it belongs in that adapter. If you are about to add something to an
# adapter that every agent would need, it belongs HERE.
#
# Contract: FAIL-OPEN. A degraded component is reported and counted, never
# fatal — a session must still start. Exit is 0 unless arguments are invalid.
#
# Usage:
#   bootstrap_agent_environment.sh --surface <id> [--governance <dir>]
#                                  [--workspace <dir>] [--check] [--quiet]
# ---------------------------------------------------------------------------
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOV_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKSPACE="$PWD"
SURFACE="${L9_GOVERNANCE_SURFACE:-unknown}"
CHECK=0
QUIET=0
GITLEAKS_PIN="8.24.3"

while [ $# -gt 0 ]; do
  case "$1" in
    --governance) GOV_DIR="${2:?--governance needs a path}"; shift 2 ;;
    --workspace)  WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --surface)    SURFACE="${2:?--surface needs an id}"; shift 2 ;;
    --check)      CHECK=1; shift ;;
    --quiet)      QUIET=1; shift ;;
    -h|--help)    sed -n '2,31p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "bootstrap_agent_environment: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

log()  { [ "$QUIET" = "1" ] || printf '\n=== %s ===\n' "$*"; }
say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
warn() { printf 'agent-bootstrap WARN: %s\n' "$*" >&2; }

# An unexpanded literal '$HOME' arrives from .env-format environment fields on
# hosted surfaces, which perform no shell expansion. Refuse it rather than
# creating a directory with that name.
case "$GOV_DIR" in
  *'$HOME'*|*'${HOME}'*)
    warn "governance path '$GOV_DIR' contains an unexpanded \$HOME; using \$HOME/.cursor-governance"
    GOV_DIR="$HOME/.cursor-governance"
    ;;
esac

if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  warn "no governance SSOT at $GOV_DIR — the surface caller must materialize it first"
  exit 1
fi
say "agent bootstrap: surface=$SURFACE governance=$GOV_DIR workspace=$WORKSPACE"

DEGRADED=0

# --- 1) Locked toolchain ----------------------------------------------------
# uv.lock is the SSOT for interpreter and dependency versions;
# ensure_uv_environment.sh is the wrapper that applies it, fingerprint-cached so
# a re-run is a no-op. It yields $GOV_DIR/.venv/bin/python3 — the interpreter
# ops/graphiti, ops/autonomy and the memory bridges already resolve to. Without
# it those imports fall back to whatever system python3 exists, memory gates
# cannot load, and governed writes are denied. Never install a pin by name here.
log "Locked governance toolchain (uv.lock)"
if ! command -v uv >/dev/null 2>&1; then
  say "uv not present — installing from PyPI (no new network host required)"
  python3 -m pip install --quiet uv 2>/dev/null || pip install --quiet uv 2>/dev/null \
    || warn "could not install uv — allowlist pypi.org"
fi
if command -v uv >/dev/null 2>&1; then
  ENSURE="$GOV_DIR/ops/scripts/ensure_uv_environment.sh"
  if [ -f "$ENSURE" ]; then
    if [ "$CHECK" = "1" ]; then
      bash "$ENSURE" "$GOV_DIR" check || warn "locked environment out of sync with uv.lock"
    else
      bash "$ENSURE" "$GOV_DIR" apply || {
        warn "uv sync --locked failed — governed writes will be denied"
        DEGRADED=$((DEGRADED + 1))
      }
    fi
  else
    warn "missing ops/scripts/ensure_uv_environment.sh"
    DEGRADED=$((DEGRADED + 1))
  fi
else
  warn "uv unavailable — cannot apply uv.lock; gates will run degraded"
  DEGRADED=$((DEGRADED + 1))
fi

GOV_PY="$GOV_DIR/.venv/bin/python3"
[ -x "$GOV_PY" ] || GOV_PY="python3"
say "interpreter: $GOV_PY ($("$GOV_PY" --version 2>&1))"

# --- 2) Canonical checker toolchain -----------------------------------------
# No surface reimplements a check. ops/scripts/run_pr_security.sh owns
# gitleaks/bandit/semgrep/pip-audit policy; we only guarantee the binaries it
# reaches for exist. Its policy is to SKIP a checker whose binary is absent,
# which reads as a pass — so provision here and report what is still missing.
log "Canonical checker toolchain"
if ! command -v uvx >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then
  warn "neither uvx nor uv on PATH — bandit/semgrep/pip-audit will SKIP"
  DEGRADED=$((DEGRADED + 1))
fi

if ! command -v gitleaks >/dev/null 2>&1 && [ "$CHECK" != "1" ]; then
  say "installing gitleaks $GITLEAKS_PIN (canonical pin: l9-ci-core security.yml)"
  gl_arch=$(uname -m)
  case "$gl_arch" in
    x86_64|amd64) gl_arch=x64 ;;
    aarch64|arm64) gl_arch=arm64 ;;
    *) gl_arch="" ;;
  esac
  gl_os=$(uname -s | tr '[:upper:]' '[:lower:]')
  if [ -n "$gl_arch" ] && { [ "$gl_os" = "linux" ] || [ "$gl_os" = "darwin" ]; }; then
    gl_url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_PIN}/gitleaks_${GITLEAKS_PIN}_${gl_os}_${gl_arch}.tar.gz"
    gl_tmp=$(mktemp -d)
    if curl -fsSL --proto '=https' --tlsv1.2 "$gl_url" -o "$gl_tmp/gitleaks.tar.gz" 2>/dev/null \
      && tar -xzf "$gl_tmp/gitleaks.tar.gz" -C "$gl_tmp" gitleaks 2>/dev/null; then
      gl_dest="$HOME/.local/bin"
      mkdir -p "$gl_dest"
      install -m 0755 "$gl_tmp/gitleaks" "$gl_dest/gitleaks" 2>/dev/null \
        || cp "$gl_tmp/gitleaks" "$gl_dest/gitleaks"
      chmod +x "$gl_dest/gitleaks" 2>/dev/null || true
      case ":$PATH:" in *":$gl_dest:"*) : ;; *) PATH="$gl_dest:$PATH"; export PATH ;; esac
    else
      warn "gitleaks download failed — secret scanning will SKIP (allowlist github.com)"
    fi
    rm -rf "$gl_tmp"
  else
    warn "no gitleaks build for ${gl_os}/${gl_arch} — secret scanning will SKIP"
  fi
fi

if command -v gitleaks >/dev/null 2>&1; then
  gl_have=$(gitleaks version 2>/dev/null | head -1 | awk '{print $NF}')
  say "gitleaks: ${gl_have:-unknown} (canonical pin $GITLEAKS_PIN)"
  [ -n "$gl_have" ] && [ "$gl_have" != "$GITLEAKS_PIN" ] \
    && warn "gitleaks $gl_have != canonical pin $GITLEAKS_PIN"
else
  warn "gitleaks ABSENT — the canonical gate will SKIP secret scanning (reported, not hidden)"
  DEGRADED=$((DEGRADED + 1))
fi

# pre-commit is the CANONICAL_LAW §12 `make pr` gate, on every surface.
if [ -f "$WORKSPACE/.pre-commit-config.yaml" ] && ! command -v pre-commit >/dev/null 2>&1; then
  if [ "$CHECK" = "1" ]; then
    warn "pre-commit absent — 'make pr' would fail (workspace declares hooks)"
  else
    say "installing pre-commit (make pr gate)"
    python3 -m pip install --quiet pre-commit 2>/dev/null \
      || warn "pre-commit install failed — 'make pr' will fail (allowlist pypi.org)"
  fi
fi

# --- 3) Secret bootstrap ----------------------------------------------------
# Delegated to the shared secret bootstrap; no surface keeps an inventory.
log "Canonical secret bootstrap"
SECRET_BOOTSTRAP="$GOV_DIR/ops/secrets/bootstrap_agent_env.sh"
if [ -f "$SECRET_BOOTSTRAP" ]; then
  bash "$SECRET_BOOTSTRAP" --check --surface "$SURFACE" \
    --require SONAR_TOKEN,SEMGREP_APP_TOKEN 2>&1 \
    || warn "secret provider DEGRADED — authenticated Sonar/Semgrep unavailable"
else
  warn "missing ops/secrets/bootstrap_agent_env.sh — no canonical secret resolution"
fi

# --- 4) Repository-scoped identity ------------------------------------------
# An agent environment is reused across consumer repositories, so anything that
# names ONE repository is resolved from the active workspace and cleared when
# that workspace does not declare it. Credentials are environment-level;
# identities are not.
log "Repository-scoped identity"
if [ -n "${GRAPHITI_GROUP_ID:-}" ]; then
  warn "GRAPHITI_GROUP_ID='$GRAPHITI_GROUP_ID' is set — it outranks repo-aware"
  warn "  resolution for every repository. Remove it from the surface environment."
fi
GRAPHITI_RESOLVE=$(cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/graphiti/graphiti_memory_client.py" resolve 2>/dev/null)
GROUP_RESOLVED=$(printf '%s' "$GRAPHITI_RESOLVE" | sed -n 's/.*"group_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
GROUP_METHOD=$(printf '%s' "$GRAPHITI_RESOLVE" | sed -n 's/.*"method"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
if [ -n "$GROUP_RESOLVED" ]; then
  say "graphiti group for this workspace: $GROUP_RESOLVED (via ${GROUP_METHOD:-unknown})"
else
  warn "graphiti group unresolved for $WORKSPACE — memory writes read-only/aborted"
fi

# Sonar project identity. The canonical consumer
# (skills/l9-pr-remediation/scripts/sonar_fetch.py) takes --project/--organization
# as required arguments, so nothing should inherit these from the environment.
if [ -f "$WORKSPACE/sonar-project.properties" ]; then
  sonar_key=$(sed -n 's/^sonar\.projectKey=//p' "$WORKSPACE/sonar-project.properties" | head -1)
  sonar_org=$(sed -n 's/^sonar\.organization=//p' "$WORKSPACE/sonar-project.properties" | head -1)
  if [ -n "${SONAR_PROJECT_KEY:-}" ] && [ -n "$sonar_key" ] && [ "$SONAR_PROJECT_KEY" != "$sonar_key" ]; then
    warn "inherited SONAR_PROJECT_KEY='$SONAR_PROJECT_KEY' replaced by workspace value '$sonar_key'"
  fi
  export SONAR_PROJECT_KEY="$sonar_key" SONAR_ORG_KEY="$sonar_org"
  say "sonar identity from workspace: project=${sonar_key:-<none>} org=${sonar_org:-<none>}"
else
  if [ -n "${SONAR_PROJECT_KEY:-}" ] || [ -n "${SONAR_ORG_KEY:-}" ]; then
    warn "clearing inherited Sonar identity (project='${SONAR_PROJECT_KEY:-}' org='${SONAR_ORG_KEY:-}')"
    warn "  — this workspace declares no sonar-project.properties"
  fi
  unset SONAR_PROJECT_KEY SONAR_ORG_KEY
  say "sonar identity: none (workspace declares no sonar-project.properties)"
fi

# --- 5) Shared local git excludes -------------------------------------------
# Machine-local activation artifacts that every surface creates. Written to
# .git/info/exclude, which is LOCAL and uncommitted, so a consumer's tracked
# .gitignore is never mutated. Vendor-specific globs stay in that vendor's
# adapter — this list is only what all surfaces share.
if [ "$CHECK" != "1" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  log "Shared local git excludes"
  exclude_file="$(git -C "$WORKSPACE" rev-parse --git-dir)/info/exclude"
  case "$exclude_file" in /*) : ;; *) exclude_file="$WORKSPACE/$exclude_file" ;; esac
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for glob in "/.cursor-commands" "/.cursor/" "/.l9/" "memory-bank/"; do
    grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >> "$exclude_file"
  done
  say "excluded shared activation artifacts via $exclude_file (local, uncommitted)"
fi

# --- 6) Readiness preflight (report only; never blocks) ---------------------
log "Readiness preflight"
"$GOV_PY" -c 'import pydantic, yaml, jsonschema' 2>/dev/null \
  && say "gates importable: pydantic + pyyaml + jsonschema (locked env)" \
  || { warn "gate imports FAILING — phase-lock and governed writes will be denied"
       DEGRADED=$((DEGRADED + 1)); }

if [ "${USER_ID:-}" = "cursor_agent" ] && [ "$SURFACE" != "cursor" ]; then
  warn "memory identity 'cursor_agent' is reserved — surface '$SURFACE' must use its own USER_ID"
fi
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  [ -n "${!retired:-}" ] && warn "$retired set — retired ADR-0006 side door; remove it"
done
if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
  warn "GRAPHITI_MCP_TOKEN unset — hydrate and governed-write phase-lock run DEGRADED"
else
  say "memory front door: ${GRAPHITI_MCP_URL:-https://memory.quantumaipartners.com/graphiti/mcp} (bearer present)"
fi

for kernel in "Recursive Alignment.md" "Validate & Repair.md"; do
  [ -f "$GOV_DIR/kernels/$kernel" ] || warn "missing required L4 kernel: kernels/$kernel"
done

# L4 phase is read-only here: never begin a phase or authorize a release from a
# bootstrap. Mid-execution push/PR stay denied until kernels are recorded.
if [ -f "$GOV_DIR/ops/autonomy/l4_local.py" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/autonomy/l4_local.py" status 2>/dev/null ) \
    || say "L4 phase: not begun (push/PR denied until authorize-release)"
  if [ "$CHECK" != "1" ] && [ -f "$GOV_DIR/ops/scripts/scratch_hold.py" ]; then
    ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/scripts/scratch_hold.py" restore --all 2>/dev/null ) || true
  fi
fi

if [ "$DEGRADED" -gt 0 ]; then
  warn "agent bootstrap completed with $DEGRADED degraded component(s) on surface '$SURFACE'"
else
  log "Agent environment ready — surface=$SURFACE governance=$GOV_DIR"
fi
exit 0
