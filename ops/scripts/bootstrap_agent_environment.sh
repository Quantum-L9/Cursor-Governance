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
# Contract: FAIL-OPEN for optional components. Locked-interpreter imports
# (pydantic / yaml) are FAIL-CLOSED — a missing .venv must not silently
# degrade into system python3. Other degraded components are reported and
# counted; exit is 0 unless arguments are invalid or the locked venv cannot
# import the gate modules.
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
# `make pr` is the ONLY sanctioned route to GitHub and ops/scripts/run_pr_precommit.sh
# hard-exits when the binary is absent, so a surface without pre-commit cannot publish
# at all. That makes this the one checker whose absence is never quietly tolerable:
# retry it (activation runs seconds after container boot, before egress is warm),
# report the real installer error instead of discarding it, and count DEGRADED loudly.
if [ -f "$WORKSPACE/.pre-commit-config.yaml" ] || [ -f "$GOV_DIR/.pre-commit-config.yaml" ]; then
  if ! command -v pre-commit >/dev/null 2>&1 && [ "$CHECK" != "1" ]; then
    say "installing pre-commit (make pr gate)"
    pc_dest="$HOME/.local/bin"
    mkdir -p "$pc_dest"
    case ":$PATH:" in *":$pc_dest:"*) : ;; *) PATH="$pc_dest:$PATH"; export PATH ;; esac
    pc_err=""
    for pc_attempt in 1 2 3; do
      # uv is guaranteed by section 1 and installs into an isolated tool env, which
      # sidesteps PEP 668 externally-managed interpreters; pip --user is the fallback.
      if command -v uv >/dev/null 2>&1 && pc_err="$(uv tool install pre-commit 2>&1)"; then
        break
      fi
      pc_err="$(python3 -m pip install --user pre-commit 2>&1)" && break
      [ "$pc_attempt" = "3" ] || sleep $((pc_attempt * 3))
    done
    hash -r 2>/dev/null || true
  fi
  if command -v pre-commit >/dev/null 2>&1; then
    say "pre-commit: $(pre-commit --version 2>/dev/null | awk '{print $NF}') (make pr gate)"
  else
    warn "pre-commit ABSENT — 'make pr' WILL FAIL, so this surface cannot reach GitHub at all"
    warn "  run_pr_precommit.sh hard-exits without it; allowlist pypi.org, then re-run this bootstrap"
    [ -n "${pc_err:-}" ] && warn "  installer said: $(printf '%s' "$pc_err" | tail -3 | tr '\n' ' ')"
    DEGRADED=$((DEGRADED + 1))
  fi
fi

# --- 2.5) Publish-path enforcement (verified, not assumed) ------------------
# `make pr` is the only sanctioned way to reach GitHub. That is enforced by
# ops/autonomy/local_execution_gate.py, which both the Claude PreToolUse hook
# and the Cursor beforeShellExecution hook route through. A policy nobody
# probes is a policy that silently stops working, so PROVE it here.
#
# The invariant is about the PATH rule, not about timing. Two distinct gates
# can deny `make pr`, and only one of them is a fault:
#
#   PATH rule  (local_execution_gate) — "this is the wrong way to reach GitHub"
#   PHASE gate (l4_local)             — "not yet; finish locally and authorize"
#
# On a fresh session L4 phase is null, so `make pr` is CORRECTLY denied for a
# phase reason. Asserting a bare allow here made every activation report
# "publish path NOT ENFORCED" — the exact opposite of the truth, since the
# surface was more restricted, not less. So assert on the REASON: raw push must
# be denied by the path rule, and `make pr` must never be denied by it.
log "Publish-path enforcement"
GATE="$GOV_DIR/ops/autonomy/local_execution_gate.py"
if [ -f "$GATE" ]; then
  # Empty output == allowed; otherwise the permissionDecisionReason text.
  _gate_deny_reason() {
    printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
      | "$GOV_PY" "$GATE" claude 2>/dev/null \
      | grep -o '"permissionDecisionReason": *"[^"]*"' \
      | head -1
  }
  # ops/autonomy/local_execution_gate.py:137 — the path-rule denial marker.
  PATH_RULE_MARKER='Publish path'
  raw_reason="$(_gate_deny_reason 'git push origin main')"
  make_reason="$(_gate_deny_reason 'make pr')"

  raw_blocked_by_path=0
  case "$raw_reason" in *"$PATH_RULE_MARKER"*) raw_blocked_by_path=1 ;; esac
  make_blocked_by_path=0
  case "$make_reason" in *"$PATH_RULE_MARKER"*) make_blocked_by_path=1 ;; esac

  if [ "$raw_blocked_by_path" = "1" ] && [ "$make_blocked_by_path" = "0" ]; then
    if [ -n "$make_reason" ]; then
      say "publish path ENFORCED: raw 'git push' denied; 'make pr' is the open route"
      say "  (currently phase-gated by L4 until authorize-release — expected, not a fault)"
    else
      say "publish path ENFORCED: raw 'git push' denied, 'make pr' allowed"
    fi
  else
    if [ "$raw_blocked_by_path" = "0" ]; then
      warn "publish path NOT ENFORCED: raw 'git push' is not denied by the path rule"
      warn "  agents on surface '$SURFACE' could reach GitHub without the Makefile checkers"
    fi
    if [ "$make_blocked_by_path" = "1" ]; then
      warn "publish path BROKEN: 'make pr' is denied by the path rule itself"
      warn "  the only sanctioned route to GitHub is closed on surface '$SURFACE'"
    fi
    DEGRADED=$((DEGRADED + 1))
  fi
  if [ -n "${L9_PUBLISH_PATH_OVERRIDE:-}" ]; then
    warn "L9_PUBLISH_PATH_OVERRIDE is set — publish-path enforcement is BYPASSED"
    warn "  this is a human/ops breakglass; it must not be set in a surface environment"
  fi
else
  warn "missing ops/autonomy/local_execution_gate.py — publish path UNENFORCED"
  DEGRADED=$((DEGRADED + 1))
fi

# --- 3) Capability bootstrap ------------------------------------------------
# This section used to ask whether SONAR_TOKEN and SEMGREP_APP_TOKEN were
# available as environment credentials. That question is now the wrong one: a
# raw secret must never be available to this process, so a surface where those
# names resolve is a surface that FAILED the security contract, not one that
# passed it.
#
# What a session actually needs to know is which named CAPABILITIES it can use.
# Those resolve through the shared capability plane, where the credential stays
# on the far side of the trust boundary. This step reports ENABLED / DEGRADED /
# UNAVAILABLE / BLOCKED and hydrates nothing.
log "Canonical capability bootstrap"
CAP_BOOTSTRAP="$GOV_DIR/ops/secrets/bootstrap_agent_env.sh"
if [ -f "$CAP_BOOTSTRAP" ]; then
  bash "$CAP_BOOTSTRAP" --check --surface "$SURFACE" \
    --require-capabilities sonar.read_issues,semgrep.appsec_scan,graphiti.query 2>&1 \
    || warn "capability plane DEGRADED — authenticated Sonar/Semgrep/Graphiti unavailable"
else
  warn "missing ops/secrets/bootstrap_agent_env.sh — no canonical capability resolution"
fi

# A surface that still carries raw downstream secrets has not been migrated.
# Report it loudly here: this is the check that would have caught the old
# posture, and it must fail visibly rather than be quietly tolerated.
for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN INFISICAL_CLIENT_SECRET \
              INFISICAL_TOKEN GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY; do
  if [ -n "${!leaked:-}" ]; then
    warn "$leaked is present in this model-controlled surface — PROHIBITED (contract S2/S3)"
    warn "  remove it from the surface environment; capabilities replace it"
    DEGRADED=$((DEGRADED + 1))
  fi
done

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
if ! "$GOV_PY" -c 'import pydantic, yaml' 2>/dev/null; then
  warn "locked .venv cannot import pydantic/yaml — fail-closed (do not fall through to system python3)"
  exit 1
fi
"$GOV_PY" -c 'import jsonschema' 2>/dev/null \
  && say "gates importable: pydantic + pyyaml + jsonschema (locked env)" \
  || { warn "jsonschema import FAILING — phase-lock and governed writes will be denied"
       DEGRADED=$((DEGRADED + 1)); }

if [ "${USER_ID:-}" = "cursor_agent" ] && [ "$SURFACE" != "cursor" ]; then
  warn "memory identity 'cursor_agent' is reserved — surface '$SURFACE' must use its own USER_ID"
fi
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  [ -n "${!retired:-}" ] && warn "$retired set — retired ADR-0006 side door; remove it"
done
# Memory front door. A bearer in this process is a contract violation, not a
# readiness signal — the brokered graphiti.* capabilities carry the credential
# on the trusted side, so an agent surface needs no token at all.
if [ -n "${GRAPHITI_MCP_TOKEN:-}" ]; then
  warn "GRAPHITI_MCP_TOKEN present in a model-controlled surface — PROHIBITED (contract S3)"
  warn "  remove it; memory resolves through the graphiti.query / graphiti.write_governed"
  warn "  capabilities, which keep the bearer beyond the model boundary"
else
  say "memory front door: brokered (no bearer in this process; graphiti.* capabilities)"
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

# Runtime readiness receipt — last-write-wins; never prints secret values.
if [ -f "$GOV_DIR/ops/scripts/write_runtime_readiness_receipt.py" ]; then
  "$GOV_PY" "$GOV_DIR/ops/scripts/write_runtime_readiness_receipt.py" \
    --surface "$SURFACE" \
    --workspace "$WORKSPACE" \
    --governance "$GOV_DIR" \
    --degraded-count "$DEGRADED" \
    >/dev/null 2>&1 || warn "runtime readiness receipt write failed"
fi
exit 0
