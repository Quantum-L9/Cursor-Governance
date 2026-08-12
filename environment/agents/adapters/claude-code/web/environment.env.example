# L9 Claude Code cloud environment variables (Web · Mobile · --cloud)
#
# Paste into claude.ai/code → environment → Environment variables (.env format).
# Anthropic stores these in plaintext for anyone who can use the environment —
# use a dedicated bot PAT + Graphiti bearer; rotate if ever pasted in chat.
# Changes apply to NEW sessions only.
#
# Replace every REPLACE_WITH_* in the UI. Do not commit live secrets.

# --- GitHub (required for gh / PR remediation) --------------------------------
GH_TOKEN=REPLACE_WITH_BOT_USER_FINE_GRAINED_PAT

# --- Governance SSOT ----------------------------------------------------------
L9_GOVERNANCE_DIR=$HOME/.cursor-governance
L9_GOVERNANCE_REMOTE=https://github.com/Quantum-L9/Cursor-Governance.git
L9_GOVERNANCE_BRANCH=main

# --- Claude Code Mobile / Web identity (distinct writer, shared group_id) -----
USER_ID=claude_code_agent
L9_MEMORY_AGENT_ID=claude-code
L9_MEMORY_SOURCE=claude-code
L9_GOVERNANCE_SURFACE=claude-code-mobile
L9_AGENT_ROLE=implementation-agent

# --- Graphiti memory (HTTPS reachability to Cursor's store) -------------------
# Same Neo4j as Cursor tunnel :8100 via C1 Caddy /graphiti/* — NOT L9_MEMORY_HTTP_*.
GRAPHITI_MEMORY_ENABLED=1
GRAPHITI_WRITE_GATES=1
GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp
GRAPHITI_MCP_TOKEN=REPLACE_WITH_GRAPHITI_MCP_BEARER_TOKEN
L9_MEMORY_REQUIRED=true
L9_MEMORY_FAIL_CLOSED=true

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

# --- Proactive governance / skill execution -----------------------------------
L9_PROACTIVE_SKILLS=true
L9_SKILL_USAGE_LOGGING=true

# --- Optional SonarCloud (Cursor-Governance defaults; overridden per repo) ----
SONAR_TOKEN=REPLACE_WITH_ROTATED_SONAR_TOKEN
SONAR_ORG_KEY=quantum-l9
SONAR_PROJECT_KEY=Quantum-L9_Cursor-Governance

# --- Toolchain hygiene --------------------------------------------------------
PYTHONDONTWRITEBYTECODE=1
PIP_DISABLE_PIP_VERSION_CHECK=1
PYTHONUNBUFFERED=1
NPM_CONFIG_FUND=false
NPM_CONFIG_AUDIT=false
