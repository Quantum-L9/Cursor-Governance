#!/usr/bin/env bash
# L9 Claude Code cloud Setup — the steps the Setup stub hands to web/setup.sh.
#
# Sourced by web/setup.sh only on the stub's hand-off (L9_GOVERNANCE_BOOTSTRAPPED=1).
# Until stub revision 2026-11-20.4 these steps ran inside the pasted stub itself;
# they moved here, unchanged and in the same order, so the stub fits the Setup
# field's 100-line limit and these steps are versioned with governance instead of
# drifting in a copy-pasted field. web/setup.sh calls l9_bootstrap_prelude before
# its own first step, and l9_bootstrap_epilogue from its EXIT trap with its exit
# code, which the epilogue then exits with. The move is proven line for line by
# environment/agents/adapters/claude-code/tests/test_setup_field_render.py.
#
# No set -e here: a single failed probe must never abort the environment build.

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

# --- 1) Normalize the account environment (ran in the stub before the clone) --
l9_bootstrap_prelude() {
  # The Environment variables field is literal .env text: Anthropic does NOT
  # expand $HOME. A pasted L9_GOVERNANCE_DIR=$HOME/.cursor-governance arrives
  # as that literal string, which would clone into a directory named $HOME and
  # hand every consumer (skill router, oversight, Graphiti bridge) a path that
  # does not exist. The cloud SSOT is always the real $HOME path — pin it here
  # and re-export the expanded value.
  GOV_DIR="$HOME/.cursor-governance"
  GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "$L9_GOVERNANCE_DIR" != "$GOV_DIR" ]; then
    warn "ignoring L9_GOVERNANCE_DIR='${L9_GOVERNANCE_DIR}' — cloud SSOT is always $GOV_DIR"
    case "$L9_GOVERNANCE_DIR" in
      *'$HOME'*)
        warn "  that value is an UNEXPANDED \$HOME — delete L9_GOVERNANCE_DIR from the variables field"
        ;;
    esac
  fi
  export L9_GOVERNANCE_DIR="$GOV_DIR"

  # L9_GOVERNANCE_SURFACE is the governance-profile selector the Autonomy Surface
  # Profile matches on (ops/autonomy/surface_profile.yaml when:). Its value is the
  # canonical ACTOR id claude-code (Quantum-L9/.github actor_registry), not a
  # canonical surface id: the surface (claude-code-mobile, -web, -cli, ...) is
  # derived per host from runtime markers by ops/memory/agent_identity.py. A
  # surface-flavoured value such as claude-code-mobile is not a selector and would
  # silently drop the session out of standing A4.
  if [ -n "${L9_GOVERNANCE_SURFACE:-}" ] && [ "$L9_GOVERNANCE_SURFACE" != "claude-code" ]; then
    warn "L9_GOVERNANCE_SURFACE='${L9_GOVERNANCE_SURFACE}' is not the governance-profile selector; using claude-code"
  fi
  export L9_GOVERNANCE_SURFACE="claude-code"

  # ADR-0006: the static HTTP memory side door is retired. Memory 3.0 OAuth is
  # the account connector and the Cursor native client, not this process.
  # Unsetting cleans this process — deleting the vars from the account field is
  # the real fix. The durable env below also unsets them for in-session Bash.
  for retired in L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
    if [ -n "${!retired:-}" ]; then
      warn "$retired is set — retired ADR-0006 side door; delete it from the variables field"
      unset "$retired"
    fi
  done
  for oauth_secret in AUTH0_CLIENT_SECRET L9_MEMORY_OAUTH_CLIENT_SECRET \
    L9_MEMORY_OAUTH_ACCESS_TOKEN L9_MEMORY_OAUTH_REFRESH_TOKEN; do
    if [ -n "${!oauth_secret:-}" ]; then
      warn "$oauth_secret is set — Memory OAuth credentials stay out of hosted sessions; unsetting"
      unset "$oauth_secret"
    fi
  done

  # Secrets plane (docs/DEGRADED_MODE_CONTRACT.md "Secrets plane, 2026-09-24";
  # same contract as ops/scripts/bootstrap_agent_environment.sh). This surface
  # holds exactly ONE bootstrap secret: its Infisical machine identity,
  # L9_INFISICAL_CLIENT_SECRET plus the non-secret L9_INFISICAL_CLIENT_ID, set
  # once in the Environment variables field. Every other secret is bound from
  # Infisical in-process (ops/secrets/capability_bind.py) and never exported.
  # The pair is deliberately NOT swept, here or in the unset list below. Any other
  # credential pasted into the field (a raw INFISICAL_CLIENT_SECRET, an Infisical
  # password or token, a downstream token, AWS keys) is stripped. The capability
  # broker is retired (never shipped) and plays no part.
  #
  # CONTEXT7_API_KEY is deliberately NOT in this list and never pasted into the
  # field: Context7 is a governed vault bridge (mcp.template.json runs
  # ops/secrets/run_vault_mcp_bridge.sh context7), which binds the key from
  # Infisical inside the bridge process. The key is never in this environment,
  # argv, .mcp.json or a file. Memory holds no transport credential on this
  # surface at all: Memory 3.0 is the account-managed OAuth connector, not a
  # project MCP entry and not a secret in this environment (memory ADR-016).
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

}

# --- 3) Durable exports, 4) memory control plane, and the verdict ------------
# (ran in the stub after web/setup.sh returned; now web/setup.sh's EXIT trap)
l9_bootstrap_epilogue() {
  SETUP_RC="$1"
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
    # No provider URL is exported (stage C8): memory is the canonical control
    # plane, bound per checkout (ops/config/memory-binding.json), never a URL.
    # The retired capability-plane URL is deliberately not exported.
    # No GH_TOKEN export and no GH_TOKEN unset: the platform issues it, gh needs
    # it, and ~/.profile sources this file unguarded, so an unset here would strip
    # it from every login shell.
    # ADR-0006 + Infisical plane: keep vault credentials out of every in-session shell.
    # No CONTEXT7_API_KEY line at all: the Context7 vault bridge binds its key
    # inside its own process, so this environment never carries one to export
    # or to strip.
    echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
    echo "unset GRAPHITI_MCP_URL GRAPHITI_MCP_TOKEN"
    echo "unset AUTH0_CLIENT_SECRET L9_MEMORY_OAUTH_CLIENT_SECRET"
    echo "unset L9_MEMORY_OAUTH_ACCESS_TOKEN L9_MEMORY_OAUTH_REFRESH_TOKEN"
    echo "unset INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
    echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
    echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
    if [ -f "$GOV_DIR/ops/scripts/lib/bind_memory_interpreter.sh" ] \
       && [ -x "$GOV_DIR/.venv/bin/python3" ]; then
      # shellcheck source=/dev/null
      . "$GOV_DIR/ops/scripts/lib/bind_memory_interpreter.sh"
      bind_l9_memory_interpreter "$GOV_DIR/.venv/bin/python3" "$GOV_DIR"
      if [ -n "${L9_MEMORY_INTERPRETER:-}" ]; then
        echo "export L9_MEMORY_INTERPRETER=$(printf %q "$L9_MEMORY_INTERPRETER")"
      fi
    fi
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

  # --- 4) Memory control plane (report, never block) --------------------------
  # Capability broker retired 2026-08-29 (never shipped). Do not probe it.
  # The only memory plane is the canonical l9-graphite-memory server
  # (memory-control-plane/v1). This hosted process does not receive a project
  # Memory MCP entry, an Auth0 client secret, or an access token. Native OAuth
  # belongs to the Claude account connector. A stdio package is not installed
  # from here. Never paste CONTEXT7_API_KEY or any downstream token into the
  # variables field; the only credential that belongs there is the Infisical
  # machine identity pair above. Status lines report names and sources only,
  # never a value.
  note "memory control plane: l9-graphite-memory (interpreter: ${L9_MEMORY_INTERPRETER:-unbound; make memory-readiness})"
  note "context7 mcp: vault bridge (ops/secrets/run_vault_mcp_bridge.sh context7; key bound from Infisical in-process)"
  if [ -n "${L9_INFISICAL_CLIENT_ID:-}" ] && [ -n "${L9_INFISICAL_CLIENT_SECRET:-}" ]; then
    note "infisical machine identity: configured"
  else
    warn "infisical machine identity: ABSENT — set L9_INFISICAL_CLIENT_ID and L9_INFISICAL_CLIENT_SECRET in Environment variables"
  fi
  note "capability plane: RETIRED (never shipped)"

  if [ "$SETUP_RC" -ne 0 ]; then
    warn "cloud bootstrap FAILED — web/setup.sh exited $SETUP_RC"
    warn "  the adapter is not wired; see ~/.l9/claude/bootstrap-state.json"
    exit "$SETUP_RC"
  fi
  note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
  exit 0
}
