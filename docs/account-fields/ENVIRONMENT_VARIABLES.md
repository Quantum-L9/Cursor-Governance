# Environment variables — paste-ready

**Field:** claude.ai/code → environment → **Environment variables**
**Format:** literal `.env` text. Nothing here is shell-expanded: `FOO=$HOME/x`
is stored as the characters `$HOME/x`.
**Applies to:** NEW sessions only. Anthropic caches the environment after the
first successful build, so a stale paste survives until a rebuild.
**Checksum:** `749b74840720a42d` (31 variables)

Generated from `environment/agents/adapters/claude-code/web/environment.env.example`
by `verify_account_env.py --emit-fields`. Do not hand-edit this file; edit the
example and regenerate, or the two disagree and the drift check trusts the example.

## Carries no credentials, by contract

No PAT, no Graphiti bearer, no Sonar or Semgrep token, no Infisical client
secret, no AWS key. Everything in this field is readable by anything the model
can run. A capability reporting DEGRADED is a broker-delivery problem; pasting a
secret here to turn it green is a permanent compromise (contract S1/S2/S3).

`verify_account_env.py` now reports a prohibited credential it finds in the live
runtime, so a paste of one does not pass silently.

## Paste this

```dotenv
CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=480
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=3
GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp
GRAPHITI_MEMORY_ENABLED=1
L9_AGENT_ROLE=implementation-agent
L9_AUTONOMY_AUTHORITY=A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
L9_AUTONOMY_ENABLED=true
L9_AUTONOMY_MATURITY=M4_ASSURANCE_GOVERNED
L9_AUTONOMY_MAX_MUTATION_LANES=128
L9_AUTONOMY_MAX_PARALLEL=480
L9_AUTONOMY_PROFILE=pr-convergence
L9_AUTONOMY_REMEDIATION_SKILL=l9-pr-remediation
L9_AUTONOMY_STATE_DIR=.l9/autonomy
L9_DISCOVER_BEFORE_ASK=true
L9_GOVERNANCE_BRANCH=main
L9_GOVERNANCE_REMOTE=https://github.com/Quantum-L9/Cursor-Governance.git
L9_GOVERNANCE_SURFACE=claude-code
L9_L4_LOCAL_AUTONOMY=1
L9_MEMORY_AGENT_ID=claude-code
L9_MEMORY_SOURCE=claude-code
L9_PROACTIVE_SKILLS=true
L9_REQUIRE_EXACT_SHA_GREEN=true
L9_SKILL_USAGE_LOGGING=true
L9_WORKTREE_ISOLATION=1
NPM_CONFIG_AUDIT=false
NPM_CONFIG_FUND=false
PIP_DISABLE_PIP_VERSION_CHECK=1
PR_REMEDIATE=0
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
USER_ID=claude_code_agent
```

## Verify the paste took

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py
```

`OK: all 31 expected variables match` means the field matches HEAD.
Any `DRIFT:` line names the variable, what is set, and what was expected.
