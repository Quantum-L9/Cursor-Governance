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
# Contract: FAIL-OPEN for optional components — a degraded component never
# blocks the session. Locked-interpreter imports (pydantic / yaml) are
# FAIL-CLOSED: a missing .venv must not silently degrade into system python3.
#
# Exit codes are three-valued, so "usable but degraded" is machine-detectable
# without being mistaken for a hard failure:
#   0  every component satisfied
#   6  session usable, one or more components DEGRADED (never the ready banner)
#   1  arguments invalid, or the locked venv cannot import the gate modules
#   2  unknown argument
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

# Every one of these is a HUMAN diagnostic, so all three write to stderr. This
# script's stdout belongs to whatever machine payload the caller is composing —
# for sessionStart that is a single JSON document (F-08). Making the channel
# structural rather than conditional means a caller that forgets --quiet cannot
# corrupt the payload; --quiet now controls verbosity only, not correctness.
log()  { [ "$QUIET" = "1" ] || printf '\n=== %s ===\n' "$*" >&2; }
say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*" >&2; }
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
#: Publish-path diagnostic: ENFORCED | NOT_ENFORCED | PROBE_ERROR (F-09).
PUBLISH_PATH_STATE="PROBE_ERROR"

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

# The locked interpreter is verified, not assumed. This used to fall through to
# whatever system python3 existed with no warning — on the audited runtime that
# was 3.11.15 against a .python-version pin of 3.12, and the .venv was absent
# entirely, so every hook's interpreter guard tripped in silence (B-03, B-22).
GOV_PY="$GOV_DIR/.venv/bin/python3"
[ -x "$GOV_PY" ] || GOV_PY="$GOV_DIR/.venv/bin/python"
if [ -x "$GOV_PY" ]; then
  say "locked interpreter: $GOV_PY ($("$GOV_PY" --version 2>&1))"
  GOV_PY_PIN_FILE="$GOV_DIR/.python-version"
  if [ -f "$GOV_PY_PIN_FILE" ]; then
    gov_py_pin="$(tr -d '[:space:]' < "$GOV_PY_PIN_FILE")"
    gov_py_have="$("$GOV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
    case "$gov_py_have" in
      "$gov_py_pin"*) : ;;
      *)
        warn "locked interpreter is $gov_py_have but .python-version pins $gov_py_pin"
        warn "  uv fetches the pinned CPython from astral.sh on first sync — allowlist it"
        DEGRADED=$((DEGRADED + 1))
        ;;
    esac
  fi
else
  warn "locked interpreter ABSENT under $GOV_DIR/.venv — every governed gate will fail closed"
  warn "  repair: uv sync --locked in $GOV_DIR (needs pypi.org and astral.sh egress)"
  DEGRADED=$((DEGRADED + 1))
  GOV_PY="python3"
  say "interpreter: $GOV_PY ($("$GOV_PY" --version 2>&1)) — UNLOCKED FALLBACK, reported not hidden"
fi

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
#
# CI-008 governance-always: the publish gate binds the GOVERNANCE pre-commit
# config ($GOV_DIR/.pre-commit-config.yaml), not the workspace's own, so
# pre-commit is required whenever the governance config exists — independent of
# whether the consumer workspace ships a .pre-commit-config.yaml. The workspace
# copy is no longer consulted for the gate.
if [ -f "$GOV_DIR/.pre-commit-config.yaml" ]; then
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
  # Three states, never two. The old probe read "no deny text" as ALLOW, so a
  # crashed probe was indistinguishable from a disabled gate and reported the
  # gate OFF while it was on (F-09). Absence of a denial is not permission.
  #
  #   DENY        gate returned a valid denial       -> ENFORCED
  #   ALLOW       gate returned cleanly, no denial   -> NOT_ENFORCED
  #   PROBE_ERROR probe could not reach a verdict    -> PROBE_ERROR (never ALLOW)
  #
  # The synthetic event carries `cwd`, because the gate resolves a workspace
  # before evaluating policy. Without it the gate falls back to process cwd and
  # a non-repository cwd made every probe crash — the probe was accidentally
  # testing malformed-input handling instead of policy (F-09/§10).
  _gate_probe() {
    _gp_out=""
    _gp_rc=0
    _gp_out="$(
      printf '{"tool_name":"Bash","tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$WORKSPACE" \
        | "$GOV_PY" "$GATE" claude 2>/dev/null
    )" || _gp_rc=$?

    if [ "$_gp_rc" -ne 0 ]; then
      printf 'PROBE_ERROR:gate exited %s\n' "$_gp_rc"
      return 0
    fi
    if [ -z "$_gp_out" ]; then
      # Clean exit, no payload: the gate's documented "allowed" encoding.
      printf 'ALLOW:\n'
      return 0
    fi
    case "$_gp_out" in
      *'"permissionDecision"'*'"deny"'*)
        printf 'DENY:%s\n' "$(printf '%s' "$_gp_out" \
          | grep -o '"permissionDecisionReason": *"[^"]*"' | head -1)"
        ;;
      *)
        printf 'PROBE_ERROR:gate returned a response with no decision\n'
        ;;
    esac
  }

  # ops/autonomy/local_execution_gate.py — the path-rule denial marker.
  PATH_RULE_MARKER='Publish path'
  raw_probe="$(_gate_probe 'git push origin main')"
  make_probe="$(_gate_probe 'make pr')"
  raw_state="${raw_probe%%:*}"
  make_state="${make_probe%%:*}"

  # A probe failure on EITHER call means the diagnostic is unusable. Reporting
  # ENFORCED or NOT_ENFORCED from it would be a fabricated verdict.
  if [ "$raw_state" = "PROBE_ERROR" ] || [ "$make_state" = "PROBE_ERROR" ]; then
    PUBLISH_PATH_STATE="PROBE_ERROR"
    warn "publish path PROBE_ERROR: the enforcement self-test could not reach a verdict"
    [ "$raw_state" = "PROBE_ERROR" ] && warn "  raw push probe: ${raw_probe#PROBE_ERROR:}"
    [ "$make_state" = "PROBE_ERROR" ] && warn "  make pr probe: ${make_probe#PROBE_ERROR:}"
    warn "  this is NOT a statement that the gate is off — enforcement is unverified"
    DEGRADED=$((DEGRADED + 1))
  else
    raw_blocked_by_path=0
    case "$raw_probe" in *"$PATH_RULE_MARKER"*) raw_blocked_by_path=1 ;; esac
    make_blocked_by_path=0
    case "$make_probe" in *"$PATH_RULE_MARKER"*) make_blocked_by_path=1 ;; esac

    if [ "$raw_blocked_by_path" = "1" ] && [ "$make_blocked_by_path" = "0" ]; then
      PUBLISH_PATH_STATE="ENFORCED"
      if [ "$make_state" = "DENY" ]; then
        say "publish path ENFORCED: raw 'git push' denied; 'make pr' is the open route"
        say "  (currently phase-gated by L4 until authorize-release — expected, not a fault)"
      else
        say "publish path ENFORCED: raw 'git push' denied, 'make pr' allowed"
      fi
    else
      PUBLISH_PATH_STATE="NOT_ENFORCED"
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
  fi
  say "publish_path_gate=$PUBLISH_PATH_STATE"
  if [ -n "${L9_PUBLISH_PATH_OVERRIDE:-}" ]; then
    warn "L9_PUBLISH_PATH_OVERRIDE is set — publish-path enforcement is BYPASSED"
    warn "  this is a human/ops breakglass; it must not be set in a surface environment"
  fi
else
  PUBLISH_PATH_STATE="PROBE_ERROR"
  warn "missing ops/autonomy/local_execution_gate.py — publish path UNVERIFIABLE"
  say "publish_path_gate=$PUBLISH_PATH_STATE"
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
  # `2>&1` used to fold this report into stdout, which is the sessionStart JSON
  # payload upstream. `>&2` redirects stdout to stderr; the script's own stderr
  # already lands there, so both streams stay diagnostic (F-08).
  bash "$CAP_BOOTSTRAP" --check --surface "$SURFACE" \
    --require-capabilities sonar.read_issues,semgrep.appsec_scan,graphiti.query >&2
  cap_rc=$?
  # INV-3: a capability-plane failure is a DEGRADED COMPONENT, not a warning the
  # receipt may ignore. This section used to `|| warn` and move on, so a session
  # with a totally dead capability plane still printed "Agent environment ready"
  # and wrote --degraded-count 0 (audit B-08). Every other section in this file
  # increments; this one now does too.
  if [ "$cap_rc" -ne 0 ]; then
    # Exit 4 is the platform-blocked class and is NOT a configuration error
    # (INV-4). Reporting it as "no broker configured" misdirects the operator
    # toward the account environment field, which cannot fix it (audit B-10).
    if [ "$cap_rc" -eq 4 ]; then
      warn "capability plane BLOCKED_BY_PLATFORM — this surface issues no broker-verifiable identity"
      warn "  not repairable from the environment field; see docs/DEGRADED_MODE_CONTRACT.md"
    else
      warn "capability plane DEGRADED — authenticated Sonar/Semgrep/Graphiti unavailable"
    fi
    DEGRADED=$((DEGRADED + 1))
  fi
else
  warn "missing ops/secrets/bootstrap_agent_env.sh — no canonical capability resolution"
  DEGRADED=$((DEGRADED + 1))
fi

# A surface that still carries raw downstream secrets has not been migrated.
# Report it loudly here: this is the check that would have caught the old
# posture, and it must fail visibly rather than be quietly tolerated.
# The platform injects the literal string `proxy-injected` for credentials it
# proxies on the session's behalf (GH_TOKEN, and on some runtimes the AWS names
# too). That sentinel is the ABSENCE of credential material, not the presence of
# it — `gh api user` succeeds through the proxy while the variable holds no
# secret. Counting it as a leak produces a false DEGRADED, which is the same
# class of lie as a false READY and just as expensive to chase. setup.sh already
# made this exact carve-out for GH_TOKEN; the other names never got it.
PROXY_SENTINEL="proxy-injected"
for leaked in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN INFISICAL_CLIENT_SECRET \
              INFISICAL_TOKEN INFISICAL_PASSWORD GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY \
              AWS_ACCESS_KEY_ID; do
  leaked_value="${!leaked:-}"
  [ -n "$leaked_value" ] || continue
  if [ "$leaked_value" = "$PROXY_SENTINEL" ]; then
    say "$leaked holds the platform proxy sentinel (no credential material) — not a leak"
    continue
  fi
  warn "$leaked is present in this model-controlled surface — PROHIBITED (contract S2/S3)"
  warn "  remove it from the surface environment; capabilities replace it"
  DEGRADED=$((DEGRADED + 1))
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

  # Stale remote-tracking refs make every "unpushed commits" count wrong, in
  # both directions. A branch deleted upstream on merge leaves refs/remotes/
  # origin/<branch> behind, so a checker that resolves origin/$current_branch
  # finds a dead ref and counts <last-pushed-tip>..HEAD -- every commit that
  # landed on main since the merge, reported as this branch's unpushed work.
  # Measured: 16 reported where 2 were real.
  #
  # Pruning alone converts that overcount into silence: the fallback is
  # origin/HEAD, which a fetch-only checkout never sets, so rev-list fails and
  # the count reads 0 with genuinely unpushed commits in the tree. A false
  # negative on a real condition is worse than an inflated one, so the two
  # halves ship together and neither is optional.
  #
  # Both are fail-soft: they need the remote, and a session with no network is
  # not a reason to abort activation.
  if git -C "$WORKSPACE" remote get-url origin >/dev/null 2>&1; then
    if git -C "$WORKSPACE" remote prune origin >/dev/null 2>&1; then
      say "pruned remote-tracking refs for branches deleted upstream"
    else
      warn "could not prune stale remote-tracking refs (remote unreachable) — unpushed counts may overcount"
    fi
    if git -C "$WORKSPACE" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1; then
      say "origin/HEAD -> $(git -C "$WORKSPACE" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)"
    elif git -C "$WORKSPACE" remote set-head origin -a >/dev/null 2>&1; then
      say "set origin/HEAD -> $(git -C "$WORKSPACE" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)"
    else
      warn "origin/HEAD unset and could not be resolved — a deleted branch leaves unpushed counts unreportable"
    fi
  fi
fi

# --- 6) Readiness preflight (report only; never blocks) ---------------------
log "Readiness preflight"
if ! "$GOV_PY" -c 'import pydantic, yaml' 2>/dev/null; then
  warn "locked .venv cannot import pydantic/yaml — fail-closed (do not fall through to system python3)"
  exit 1
fi
"$GOV_PY" -c 'import jsonschema' 2>/dev/null \
  && say "gates importable: pydantic + pyyaml + jsonschema (locked env)" \
  || { warn "jsonschema import FAILING — governed writes will be denied"
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
  # Both of these print their own report on stdout — l4_local emits a whole JSON
  # document, which would make the chain's stdout TWO JSON documents and break
  # the renderer just as surely as a warning line would (F-08). Neither is a
  # machine result for this chain, so both go to stderr.
  ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/autonomy/l4_local.py" status 2>/dev/null >&2 ) \
    || say "L4 phase: not begun (push/PR denied until authorize-release)"
  if [ "$CHECK" != "1" ] && [ -f "$GOV_DIR/ops/scripts/scratch_hold.py" ]; then
    ( cd "$WORKSPACE" && "$GOV_PY" "$GOV_DIR/ops/scripts/scratch_hold.py" restore --all \
        2>/dev/null >&2 ) || true
  fi
fi

# Exit code contract (three states, not two):
#
#   0  every component satisfied            -> "Agent environment ready"
#   6  session usable, components degraded  -> never the ready banner
#   1  arguments invalid, or the locked venv cannot import the gate modules
#
# 6 exists to resolve a real tension. T-01 requires a degraded capability plane
# to exit non-zero, but install.sh maps ANY non-zero shared-bootstrap exit to
# STATUS_SHARED=BLOCKED — and on a hosted surface the capability plane is
# permanently BLOCKED_BY_PLATFORM, which INV-4 says must stay distinct from a
# failure. Collapsing the two would mark every install BLOCKED forever and erase
# exactly the distinction WS-5 exists to draw. A dedicated code keeps the
# session fail-open, keeps the degradation machine-detectable, and lets the
# caller classify it as DEGRADED rather than BLOCKED.
BOOTSTRAP_EXIT=0
if [ "$DEGRADED" -gt 0 ]; then
  warn "agent bootstrap completed with $DEGRADED degraded component(s) on surface '$SURFACE'"
  BOOTSTRAP_EXIT=6
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
exit "$BOOTSTRAP_EXIT"
