# L9 Claude Code cloud environment variables (Web · Mobile · --cloud)
#
# Paste into claude.ai/code -> environment -> Environment variables (.env format).
# Anthropic stores these in plaintext for anyone who can use the environment —
# use a dedicated bot PAT + Graphiti bearer; rotate if ever pasted in chat.
# Changes apply to NEW sessions only.
#
# Replace every REPLACE_WITH_* in the UI. Do not commit live secrets.
#
# THIS FIELD IS LITERAL TEXT — no shell expansion. `FOO=$HOME/x` is stored as the
# characters `$HOME/x`, not your home directory. Never reference $HOME, $PWD, or
# any other variable here; paths that need expanding are resolved by setup.sh.
#
# Companions: web/setup.bootstrap.sh (Setup script) · web/network-policy.md (Network access)

# --- GitHub (required for gh, make pr, PR remediation) ------------------------
# Dedicated bot-user fine-grained PAT so pushes trigger Actions.
# SSOT for the value is AWS Secrets Manager (CANONICAL_LAW §14), ref
# `openclaw-igorbot/github#token` — resolve and paste, do not mint a second PAT.
# The ref stays in this comment on purpose: its `#` would be read as a
# start-of-comment by .env parsers, truncating the value to a wrong ref.
GH_TOKEN=REPLACE_WITH_BOT_USER_FINE_GRAINED_PAT

# --- Governance SSOT ----------------------------------------------------------
# L9_GOVERNANCE_DIR is deliberately ABSENT. The cloud SSOT is always
# $HOME/.cursor-governance, hard-pinned by setup.sh and the SessionStart hook.
# Setting it here can only feed consumers an unexpanded literal '$HOME' path.
L9_GOVERNANCE_REMOTE=https://github.com/Quantum-L9/Cursor-Governance.git
L9_GOVERNANCE_BRANCH=main

# --- Surface + memory identity (distinct writer, shared group_id) --------------
# L9_GOVERNANCE_SURFACE must be exactly `claude-code`: the Autonomy Surface
# Profile allow-list (ops/autonomy/surface_profile.yaml `when:`) and
# rules/99-no-auto-commit.mdc match on that id. A `claude-code-mobile` variant
# drops the session out of standing A4 velocity. Web and Mobile share this id.
L9_GOVERNANCE_SURFACE=claude-code
USER_ID=claude_code_agent
L9_MEMORY_AGENT_ID=claude-code
L9_MEMORY_SOURCE=claude-code
L9_AGENT_ROLE=implementation-agent

# --- Graphiti memory front door (ADR-0006 / ADR-0007) -------------------------
# The ONLY memory plane. Same Neo4j as Cursor's tunnel :8100, via C1 Caddy
# /graphiti/*. Without GRAPHITI_MCP_TOKEN the SessionStart hydrate returns an
# empty PICKUP and every governed write is denied for want of a phase-lock.
GRAPHITI_MEMORY_ENABLED=1
GRAPHITI_WRITE_GATES=1
GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp
GRAPHITI_MCP_TOKEN=REPLACE_WITH_GRAPHITI_MCP_BEARER_TOKEN
#
# GRAPHITI_GROUP_ID is deliberately ABSENT. This account environment is reused
# across consumer repositories, and group_registry.yaml resolves in the order
# [explicit_env, git_remote_match, path_hint_match] — so an env value here wins
# over repo-aware resolution and would file every repo's memory under one group.
# Transport and auth are environment-level; the namespace is per-repository.
# Legitimate one-off override: export GRAPHITI_GROUP_ID for that shell only.
# Declarative posture markers. Enforcement is the PreToolUse memory gate
# (hooks/memory_gate.py), which fails closed by construction.
L9_MEMORY_REQUIRED=true
L9_MEMORY_FAIL_CLOSED=true
#
# RETIRED — do NOT set. The HTTP side door was removed by ADR-0006; if these are
# still in your environment, delete them:
#   L9_MEMORY_HTTP_URL
#   L9_MEMORY_CLIENT_TOKEN

# --- Bounded autonomy (A4 + M4; merge stays human) ----------------------------
L9_AUTONOMY_ENABLED=true
L9_AUTONOMY_AUTHORITY=A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
L9_AUTONOMY_MATURITY=M4_ASSURANCE_GOVERNED
L9_AUTONOMY_PROFILE=pr-convergence
L9_AUTONOMY_AUTONOMOUS_MERGE=false
L9_AUTONOMY_REMEDIATION_SKILL=l9-pr-remediation
L9_AUTONOMY_MAX_PARALLEL=4
L9_AUTONOMY_MAX_MUTATION_LANES=2
L9_AUTONOMY_STATE_DIR=.l9/autonomy
L9_DISCOVER_BEFORE_ASK=true
L9_REQUIRE_EXACT_SHA_GREEN=true

# --- L4 local autonomy + worktree isolation (all surfaces; default ON) --------
# Local commits on a stacked branch are free; push / gh pr create / make pr stay
# denied by ops/autonomy/local_execution_gate.py until the kernels are recorded
# and .l9/autonomy/l4-release-receipt.json authorizes release. Both flags are ON
# by default — set here explicitly so the posture is visible in the environment.
L9_L4_LOCAL_AUTONOMY=1
L9_WORKTREE_ISOLATION=1

# --- Publish path (PR_REMEDIATE=0 make pr) ------------------------------------
# `make pr` runs the Makefile checkers, then pushes and opens the PR. Remediation
# is a separate, bounded step via the l9-pr-remediation skill.
PR_REMEDIATE=0
# PR_BASE — set ONLY for Program Execution campaign work, to that campaign's
# integration branch (campaign/<campaign_id>). Campaign PRs must not target main.
# PR_BASE=campaign/<campaign_id>

# --- Breakglass keys — human/ops only; leave UNSET -----------------------------
# Listed so they are recognizable, never so they are pasted. Setting any of these
# in the account environment makes the bypass permanent for every session.
#   L9_MERGE_AUTHORIZED               merge gate (ops/autonomy/merge_gate.py)
#   L9_MERGE_AUTHORIZATION_FILE       one-shot ~/.l9/autonomy/merge-authorization.json
#   L9_LOCAL_PUSH_AUTHORIZED          mid-execution push
#   L9_GIT_REVERT_AUTHORIZED          worktree isolation: revert
#   L9_GIT_RESET_AUTHORIZED           worktree isolation: reset
#   L9_GIT_SWITCH_AUTHORIZED          worktree isolation: branch switch
#   L9_GIT_BROAD_ADD_AUTHORIZED       worktree isolation: git add -A/./-u
#   L9_MEMORY_ENFORCEMENT_BREAKGLASS  PreToolUse memory gate

# --- Proactive governance / skill execution -----------------------------------
L9_PROACTIVE_SKILLS=true
L9_SKILL_USAGE_LOGGING=true

# --- SonarCloud: credential only, never project identity ----------------------
# SONAR_PROJECT_KEY / SONAR_ORG_KEY are deliberately ABSENT. They identify ONE
# repository; this environment is reused across many. install.sh derives them
# from the active repo's sonar-project.properties and actively unsets them when
# the repo declares no Sonar project, so Cursor-Governance's identity can never
# leak into a consumer repo and mis-file its analysis.
#
# The token is a credential, not identity, so it may live at environment level —
# but prefer resolving it from the canonical secret provider below (SONAR_TOKEN
# is already registered there). Set it here only if you are not using Infisical.
# SONAR_TOKEN=REPLACE_WITH_ROTATED_SONAR_TOKEN

# --- Canonical secret provider (ops/secrets) ----------------------------------
# Bootstrap credentials ONLY. Everything else (SONAR_TOKEN, SEMGREP_APP_TOKEN,
# and the rest of the openclaw-igorbot inventory) resolves through the provider
# at run time — do not copy downstream secrets into this field.
# Universal Auth identity for the Infisical project `cursor-governance`; the
# machine identity is registered in ops/secrets/infisical-cursor-governance.yaml.
INFISICAL_CLIENT_ID=REPLACE_WITH_INFISICAL_UA_CLIENT_ID
INFISICAL_CLIENT_SECRET=REPLACE_WITH_INFISICAL_UA_CLIENT_SECRET
INFISICAL_PROJECT_ID=REPLACE_WITH_INFISICAL_PROJECT_ID
INFISICAL_ENV=prod
INFISICAL_SITE_URL=https://app.infisical.com
INFISICAL_SECRET_PATH=/

# --- Toolchain hygiene --------------------------------------------------------
PYTHONDONTWRITEBYTECODE=1
PIP_DISABLE_PIP_VERSION_CHECK=1
PYTHONUNBUFFERED=1
NPM_CONFIG_FUND=false
NPM_CONFIG_AUDIT=false
