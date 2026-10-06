---
name: Claude Agent SDK adapter for Cursor-Governance
overview: "Add a thin Claude Agent SDK harness under environment/agents/adapters/claude-agent-sdk/ that consumes committed project governance (CLAUDE.md, .claude/settings.json, .mcp.json) via setting_sources=[project], owns only SDK runtime mechanics (budget, turns, structured report, checkpointing, MCP status), and authors no permission, hook, invariant or MCP policy of its own. Do NOT touch CANONICAL_LAW.md, INVARIANTS.md, ORG_INVARIANTS.yaml, rulesets/, policies/, or .github/workflows/ in this plan."
todos:
  - id: todo-01-baseline-preflight
    content: "PE W0: lock immutable baseline (full SHA of origin/main) + capability probes (python>=3.12, uv, ANTHROPIC_API_KEY); Program Lock bind; stop_and_replan on drift"
    status: completed
  - id: todo-02-architect-select
    content: "Run l9-global-architect: confirm adapter placement mirrors environment/agents/adapters/claude-code/; record ADR"
    status: pending
  - id: todo-03-dependency
    content: "Bind claude-agent-sdk as locked optional extra agent-sdk in pyproject.toml + uv.lock; verify bundled CLI resolves"
    status: completed
  - id: todo-04-harness
    content: "Create environment/agents/adapters/claude-agent-sdk/l9_agent.py (ClaudeSDKClient, setting_sources=[project], json_schema output, budget, turns, checkpointing, MCP status); no allowed/disallowed tools, hooks, subagents or appended system prompt"
    status: completed
  - id: todo-05-config-ssot
    content: "Adapter config.yaml — removed in PR #689 remediation: its tool/deny/protected-file policy duplicated project settings; remaining runtime defaults live in l9_agent.py"
    status: cancelled
  - id: todo-06-validators
    content: "Add validate_agent_sdk_env.py (setting_sources includes project; no shadow policy keys; governance inputs present; report path gitignored; SDK pinned in lock; SDK import UNKNOWN when unsynced)"
    status: completed
  - id: todo-07-tests
    content: "tests/test_l9_agent.py: runtime-only option surface, removed-machinery guard, budget/turn bounds, report + MCP summary, validator fail cases, real-SDK seam; no network"
    status: completed
  - id: todo-08-make-targets
    content: "Makefile: agent-sdk, agent-sdk-plan, agent-sdk-validate (stacked follow-up)"
    status: pending
  - id: todo-09-docs
    content: "Adapter README.md (done); AGENTS.md/CLAUDE.md surface rows + llm.txt via l9-update-agent-docs (follow-up)"
    status: in_progress
  - id: todo-10-verify
    content: "CI: ruff + pytest adapter tests + validate_agent_sdk_env.py; --mcp-status proves project MCP servers; plan-mode task run produces report (needs ANTHROPIC_API_KEY)"
    status: in_progress
  - id: todo-11-pr
    content: "Stacked PR feat/claude-agent-sdk-adapter -> main; CODEOWNERS review; section receipt generated + validated"
    status: in_progress
isProject: false
kind: simple
execute_via: cursor-build
status: partially-built
---

# Claude Agent SDK adapter for Cursor-Governance

## Mission

Run the existing Claude Code actor through the Claude Agent SDK as a thin Cursor-Governance adapter that consumes the same committed project governance Claude Code loads, with zero new SSOT. Not a new L9 ProductKind or SurfaceIdentity.

## Baseline (PE W0)

| Field | Value |
|-------|-------|
| repo | Quantum-L9/Cursor-Governance |
| branch | feat/claude-agent-sdk-adapter |
| baseline_sha | 8d5cf5f6d14d3ce6d14fce2424bc32d84f449744 |
| capability_probes | python>=3.12, uv, ANTHROPIC_API_KEY |
| drift_policy | stop_and_replan |

## Scope

In scope: environment/agents/adapters/claude-agent-sdk/**, docs/plans/partially-built/claude-agent-sdk-adapter.plan.md, pyproject.toml/uv.lock (agent-sdk extra). Follow-up (stacked): Makefile targets, AGENTS.md/CLAUDE.md rows, llm.txt, ADR.

Out of scope (protected): CANONICAL_LAW.md, INVARIANTS.md, ORG_INVARIANTS.yaml, CODEOWNERS, .github/workflows/, rulesets/, policies/, security/, .claude/settings.json and l9_hook_exec.sh semantics.

## Architecture impact

- New adapter directory beside environment/agents/adapters/claude-code/; it does not call into that adapter's hooks or launcher.
- setting_sources=["project"] makes CLAUDE.md, .claude/settings.json (permissions + hooks) and .mcp.json authoritative for the SDK exactly as for Claude Code. The adapter passes no tool, hook, subagent, MCP or system-prompt policy.
- The adapter owns only runtime mechanics: cwd, permission mode, max_turns, max_budget_usd, JSON-schema report (reports/agent_sdk/, gitignored), file checkpointing, MCP status introspection.

### Adapter routing

| Task class | Route |
|-----------|-------|
| planning | permission_mode plan, no mutations |
| edits | permission_mode acceptEdits, budget-capped; tool permissions from .claude/settings.json |

## Verification

- pytest -q environment/agents/adapters/claude-agent-sdk/tests
- python environment/agents/adapters/claude-agent-sdk/validate_agent_sdk_env.py
- uv run --extra agent-sdk python environment/agents/adapters/claude-agent-sdk/l9_agent.py --mcp-status
- uv run --extra agent-sdk python environment/agents/adapters/claude-agent-sdk/l9_agent.py "<task>" --mode plan && test -s reports/agent_sdk/latest.json

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Untrusted workspace: CLI ignores .claude/settings.json permissions.allow | Fails closed (tools denied); trust the workspace on the host, never add an adapter allowlist |
| SDK drops CLAUDE.md if setting_sources omitted | SETTING_SOURCES validator + unit test |
| Shadow policy reintroduced in the adapter | SHADOW_POLICY validator + runtime-only option surface test |
| Runaway spend | max_budget_usd + max_turns |

## Rollback

- git revert <merge-sha>; remove the agent-sdk extra; uv lock
- Delete environment/agents/adapters/claude-agent-sdk/
- command / proof that rollback restored invariants: `make lint && pytest -q && git diff --stat origin/main -- CANONICAL_LAW.md INVARIANTS.md ORG_INVARIANTS.yaml` returns empty

## Section receipt

| Field | Value |
|-------|-------|
| receipt_path | <generated by skills/l9-plan-simple/scripts/generate_plan_section_receipt.py> |
| categories | `keep` (all existing adapters) \| `replace` (none) \| `delete` (none) \| `skip` (protected SSOT) |
| execute_via | cursor-build |
