#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Claude Code adapter — THE installer. One file, every surface.
#
# CLI, Desktop, Web, Mobile and `claude --cloud` all wire the adapter through
# this script. Surface entrypoints are thin callers that only do what their
# surface uniquely needs, then delegate here:
#
#   Web / Mobile / --cloud : web/setup.bootstrap.sh -> web/setup.sh -> install.sh
#   CLI / Desktop          : make claude-install    ->               install.sh
#
# Everything surface-neutral lives here and nowhere else: the locked toolchain,
# the settings triad, skill discovery, the MCP front door, local git excludes,
# and the readiness preflight. Add adapter wiring HERE, not in a surface caller.
#
# This script never clones governance and never touches credentials — acquiring
# the SSOT and authenticating are the caller's job, because they differ per
# surface. It is idempotent and safe to re-run.
#
# Dependency policy: this script does NOT install packages by name. The
# governance repo's own uv.lock is the single source of truth for interpreter
# and dependency versions; ops/scripts/ensure_uv_environment.sh is the wrapper
# that applies it. Never re-declare a pin here.
#
# Usage:
#   install.sh [--governance <dir>] [--workspace <dir>] [--check] [--quiet]
# ---------------------------------------------------------------------------
set -uo pipefail

GOV_DIR="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
WORKSPACE="$PWD"
CHECK=0
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --governance) GOV_DIR="${2:?--governance needs a path}"; shift 2 ;;
    --workspace)  WORKSPACE="${2:?--workspace needs a path}"; shift 2 ;;
    --check)      CHECK=1; shift ;;
    --quiet)      QUIET=1; shift ;;
    -h|--help)    sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "install.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

log()  { [ "$QUIET" = "1" ] || printf '\n=== %s ===\n' "$*"; }
say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
warn() { printf 'adapter WARN: %s\n' "$*" >&2; }

# An unexpanded literal '$HOME' reaches us from .env-format environment fields,
# which perform no shell expansion. Refuse it rather than creating that directory.
case "$GOV_DIR" in
  *'$HOME'*|*'${HOME}'*)
    warn "governance path '$GOV_DIR' contains an unexpanded \$HOME; using $HOME/.cursor-governance"
    GOV_DIR="$HOME/.cursor-governance"
    ;;
esac

if [ ! -f "$GOV_DIR/CANONICAL_LAW.md" ]; then
  warn "no governance SSOT at $GOV_DIR — the surface caller must clone it first"
  exit 1
fi
say "adapter: governance=$GOV_DIR workspace=$WORKSPACE"

FAILURES=0

# --- 1) Locked toolchain (interpreter + dependencies) ----------------------
# uv.lock is the SSOT for every version. ensure_uv_environment.sh is the wrapper
# that applies it (`uv sync --locked --extra dev`), fingerprint-cached so a
# re-run is a no-op. It produces $GOV_DIR/.venv/bin/python3 — the interpreter
# ops/graphiti, ops/autonomy and the memory bridge already resolve to. Without
# it those imports fall back to whatever system python3 happens to be, the
# PreToolUse memory gate cannot load its brain, and governed writes are denied.
log "Locked governance toolchain (uv.lock)"
if ! command -v uv >/dev/null 2>&1; then
  say "uv not present — installing from PyPI (no new network host required)"
  python3 -m pip install --quiet uv 2>/dev/null \
    || pip install --quiet uv 2>/dev/null \
    || warn "could not install uv — allowlist pypi.org"
fi
if command -v uv >/dev/null 2>&1; then
  ENSURE="$GOV_DIR/ops/scripts/ensure_uv_environment.sh"
  if [ -f "$ENSURE" ]; then
    if [ "$CHECK" = "1" ]; then
      bash "$ENSURE" "$GOV_DIR" check || warn "locked environment is out of sync with uv.lock"
    else
      bash "$ENSURE" "$GOV_DIR" apply || {
        warn "uv sync --locked failed — governed writes will be denied"
        FAILURES=$((FAILURES + 1))
      }
    fi
  else
    warn "missing ops/scripts/ensure_uv_environment.sh in the governance clone"
    FAILURES=$((FAILURES + 1))
  fi
else
  warn "uv unavailable — cannot apply uv.lock; adapter gates will run degraded"
  FAILURES=$((FAILURES + 1))
fi

GOV_PY="$GOV_DIR/.venv/bin/python3"
[ -x "$GOV_PY" ] || GOV_PY="python3"
say "adapter interpreter: $GOV_PY ($("$GOV_PY" --version 2>&1))"

# --- 2) Settings triad -----------------------------------------------------
# reconcile_claude_settings.py is the SSOT reconciler: it syncs the governance
# copy, merge-patches ~/.claude/settings.json without clobbering user keys, and
# installs the consumer workspace triad as real files. Same call on every
# surface — do not hand-roll `cp settings.template.json` anywhere.
log "Settings triad"
RECONCILE_SETTINGS="$GOV_DIR/ops/scripts/reconcile_claude_settings.py"
if [ -f "$RECONCILE_SETTINGS" ]; then
  settings_args=(--root "$GOV_DIR" --workspace "$WORKSPACE")
  [ "$CHECK" = "1" ] && settings_args+=(--check)
  python3 "$RECONCILE_SETTINGS" "${settings_args[@]}" || {
    warn "settings triad reconciliation reported drift"
    FAILURES=$((FAILURES + 1))
  }
else
  warn "missing ops/scripts/reconcile_claude_settings.py"
  FAILURES=$((FAILURES + 1))
fi

# --- 3) Skill discovery ----------------------------------------------------
log "L9 skill discovery"
RECONCILE_SKILLS="$GOV_DIR/ops/scripts/reconcile_claude_l9_skills.py"
if [ -f "$RECONCILE_SKILLS" ]; then
  skills_args=(--root "$GOV_DIR" --scope project --workspace "$WORKSPACE" --quiet)
  [ "$CHECK" = "1" ] && skills_args+=(--check)
  python3 "$RECONCILE_SKILLS" "${skills_args[@]}" \
    || warn "skill reconciliation reported drift or a local name conflict"
else
  warn "missing ops/scripts/reconcile_claude_l9_skills.py"
fi

# --- 4) Memory MCP front door ----------------------------------------------
# ADR-0006: graphiti-memory is the only memory plane. The template carries
# ${GRAPHITI_MCP_URL} / ${GRAPHITI_MCP_TOKEN} references, never a literal token.
log "Memory MCP front door"
MCP_TEMPLATE="$GOV_DIR/environment/agents/adapters/claude-code/mcp.template.json"
if [ -f "$WORKSPACE/.mcp.json" ]; then
  say ".mcp.json already present — left as the repo committed it"
elif [ "$CHECK" = "1" ]; then
  warn ".mcp.json missing (check mode: not writing)"
elif [ -f "$MCP_TEMPLATE" ]; then
  cp "$MCP_TEMPLATE" "$WORKSPACE/.mcp.json" && say "installed .mcp.json from mcp.template.json"
else
  warn "missing mcp.template.json — memory front door not wired"
fi

# --- 5) Local git excludes -------------------------------------------------
# Activation artifacts (symlinks into the SSOT, generated mirrors, per-workspace
# state) are machine-local and must never be committed. Written to
# .git/info/exclude, which is LOCAL and uncommitted, so a consumer's tracked
# .gitignore is never mutated. Only the GENERATED .claude mirrors are excluded —
# .claude/settings.json and .claude/hooks/ are committable consumer wiring.
if [ "$CHECK" != "1" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  log "Local git excludes"
  exclude_file="$(git -C "$WORKSPACE" rev-parse --git-dir)/info/exclude"
  case "$exclude_file" in /*) : ;; *) exclude_file="$WORKSPACE/$exclude_file" ;; esac
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  for glob in "/.cursor-commands" "/.cursor/" ".claude/skills/" ".claude/rules/" "/.l9/" "memory-bank/"; do
    grep -qxF "$glob" "$exclude_file" 2>/dev/null || printf '%s\n' "$glob" >> "$exclude_file"
  done
  say "excluded activation artifacts via $exclude_file (local, uncommitted)"
fi

# --- 5.2) Canonical security/checker toolchain ------------------------------
# The adapter NEVER reimplements a check. ops/scripts/run_pr_security.sh owns
# gitleaks/bandit/semgrep/pip-audit policy; all we do is make sure the binaries
# it reaches for actually exist, so a missing tool cannot masquerade as a pass.
#
# Ownership per the canonical runner:
#   bandit / semgrep / pip-audit -> pinned, executed through uvx / uv tool run
#   gitleaks                     -> machine CLI on PATH, pin 8.24.3
# Its policy is to SKIP a checker whose binary is absent. That keeps the gate
# non-blocking on a bare machine, but it also means a skip reads as a pass, so
# provision the binaries here and report anything still missing as DEGRADED.
log "Canonical checker toolchain"
GITLEAKS_PIN="8.24.3"

if ! command -v uvx >/dev/null 2>&1 && ! command -v uv >/dev/null 2>&1; then
  warn "neither uvx nor uv on PATH — bandit/semgrep/pip-audit will SKIP in the security gate"
  FAILURES=$((FAILURES + 1))
fi

if ! command -v gitleaks >/dev/null 2>&1; then
  if [ "$CHECK" = "1" ]; then
    warn "gitleaks absent — canonical security gate would SKIP secret scanning"
  else
    say "installing gitleaks $GITLEAKS_PIN (canonical pin: l9-ci-core security.yml)"
    gl_arch=$(uname -m)
    case "$gl_arch" in
      x86_64|amd64) gl_arch=x64 ;;
      aarch64|arm64) gl_arch=arm64 ;;
      *) gl_arch="" ;;
    esac
    gl_os=$(uname -s | tr '[:upper:]' '[:lower:]')
    if [ -n "$gl_arch" ] && [ "$gl_os" = "linux" ]; then
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
fi

if command -v gitleaks >/dev/null 2>&1; then
  gl_have=$(gitleaks version 2>/dev/null | head -1 | awk '{print $NF}')
  say "gitleaks: ${gl_have:-unknown} (canonical pin $GITLEAKS_PIN)"
  [ -n "$gl_have" ] && [ "$gl_have" != "$GITLEAKS_PIN" ] \
    && warn "gitleaks $gl_have != canonical pin $GITLEAKS_PIN"
else
  warn "gitleaks STILL ABSENT — the canonical gate will SKIP secret scanning (reported, not hidden)"
  FAILURES=$((FAILURES + 1))
fi

# pre-commit is the CANONICAL_LAW §12 `make pr` gate; provision it wherever the
# workspace declares hooks, on every surface rather than only in the cloud.
if [ -f "$WORKSPACE/.pre-commit-config.yaml" ] && ! command -v pre-commit >/dev/null 2>&1; then
  if [ "$CHECK" = "1" ]; then
    warn "pre-commit absent — 'make pr' would fail (workspace declares hooks)"
  else
    say "installing pre-commit (make pr gate)"
    python3 -m pip install --quiet pre-commit 2>/dev/null \
      || warn "pre-commit install failed — 'make pr' will fail (allowlist pypi.org)"
  fi
fi

# --- 5.3) Canonical secret provider -----------------------------------------
# ops/secrets is the SSOT inventory. The adapter resolves through it and keeps
# NO inventory of its own: the account environment carries bootstrap credentials
# only, and every downstream token (SONAR_TOKEN, SEMGREP_APP_TOKEN, ...) is
# fetched at run time. Values are never printed, here or by the resolver.
log "Canonical secret provider"
HYDRATE="$GOV_DIR/ops/secrets/hydrate_infisical.py"
if [ -f "$HYDRATE" ]; then
  if "$GOV_PY" "$HYDRATE" --check --require SONAR_TOKEN,SEMGREP_APP_TOKEN 2>&1; then
    say "secret provider: ENABLED"
  else
    warn "secret provider DEGRADED — authenticated Sonar/Semgrep unavailable this session"
    warn "  set INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET, or configure the AWS CLI"
  fi
else
  warn "missing ops/secrets/hydrate_infisical.py — no canonical secret resolution"
fi

# --- 5.5) Repository-scoped identity (never account-global) ----------------
# This adapter's account environment is reused across consumer repositories, so
# anything that names ONE repository must be resolved from the active workspace
# and cleared when that workspace does not declare it. Credentials are
# environment-level; identities are not.
log "Repository-scoped identity"

# Graphiti namespace. group_registry.yaml resolves in the order
# [explicit_env, git_remote_match, path_hint_match], so an inherited
# GRAPHITI_GROUP_ID outranks repo-aware resolution for every repo. Report what
# the canonical resolver returns for THIS workspace; never pin it here.
if [ -n "${GRAPHITI_GROUP_ID:-}" ]; then
  warn "GRAPHITI_GROUP_ID='$GRAPHITI_GROUP_ID' is set — this outranks repo-aware"
  warn "  resolution for every repository. Remove it from the account environment."
fi
GRAPHITI_RESOLVE=$(cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/graphiti/graphiti_memory_client.py" resolve 2>/dev/null)
GROUP_RESOLVED=$(printf '%s' "$GRAPHITI_RESOLVE" | sed -n 's/.*"group_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
GROUP_METHOD=$(printf '%s' "$GRAPHITI_RESOLVE" | sed -n 's/.*"method"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
if [ -n "$GROUP_RESOLVED" ]; then
  say "graphiti group for this workspace: $GROUP_RESOLVED (via ${GROUP_METHOD:-unknown})"
else
  warn "graphiti group unresolved for $WORKSPACE — memory writes will be read-only/aborted"
fi

# Sonar project identity. The canonical consumer
# (skills/l9-pr-remediation/scripts/sonar_fetch.py) takes --project/--organization
# as required arguments, so nothing should inherit these from the environment.
# Derive them from the workspace when it declares a project; clear them when it
# does not, so one repo's identity can never mis-file another repo's analysis.
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

# --- 6) Readiness preflight (report only; never blocks a session) ----------
log "Adapter preflight"
"$GOV_PY" -c 'import pydantic, yaml, jsonschema' 2>/dev/null \
  && say "gates importable: pydantic + pyyaml + jsonschema (locked env)" \
  || warn "gate imports FAILING — Graphiti phase-lock and governed writes will be denied"

if [ "${USER_ID:-}" = "cursor_agent" ] || [ "${L9_MEMORY_AGENT_ID:-}" = "cursor_agent" ]; then
  warn "memory identity 'cursor_agent' is reserved — use USER_ID=claude_code_agent / L9_MEMORY_AGENT_ID=claude-code"
fi
for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
  [ -n "${!retired:-}" ] && warn "$retired set — retired ADR-0006 side door; remove it from the environment"
done
if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
  warn "GRAPHITI_MCP_TOKEN unset — SessionStart hydrate and governed-write phase-lock run DEGRADED"
else
  say "memory front door: ${GRAPHITI_MCP_URL:-https://memory.quantumaipartners.com/graphiti/mcp} (bearer present)"
fi

for kernel in "Recursive Alignment.md" "Validate & Repair.md"; do
  [ -f "$GOV_DIR/kernels/$kernel" ] || warn "missing required L4 kernel: kernels/$kernel"
done

# L4 phase is read-only here: never begin a phase or authorize a release from an
# installer. Mid-execution push/PR stay denied until the kernels are recorded.
if [ -f "$GOV_DIR/ops/autonomy/l4_local.py" ] && git -C "$WORKSPACE" rev-parse --git-dir >/dev/null 2>&1; then
  ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/autonomy/l4_local.py" status 2>/dev/null ) \
    || say "L4 phase: not begun (push/PR denied until authorize-release)"
  if [ "$CHECK" != "1" ] && [ -f "$GOV_DIR/ops/scripts/scratch_hold.py" ]; then
    ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/scripts/scratch_hold.py" restore --all 2>/dev/null ) || true
  fi
fi

if [ "$FAILURES" -gt 0 ]; then
  warn "adapter install completed with $FAILURES degraded component(s)"
  exit 0   # fail-open: a degraded adapter must still let the session start
fi
log "Adapter ready — governance $GOV_DIR"
exit 0
