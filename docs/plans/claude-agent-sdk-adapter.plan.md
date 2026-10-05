---
name: Claude Agent SDK adapter for Cursor-Governance
overview: "Add a governed Claude Agent SDK harness under environment/agents/adapters/claude-agent-sdk/ that loads committed project governance (CLAUDE.md, .claude/settings.json, .mcp.json), routes hooks through l9_hook_exec.sh, hard-denies SSOT mutations, and emits a schema-validated report. Do NOT touch CANONICAL_LAW.md, INVARIANTS.md, ORG_INVARIANTS.yaml, rulesets/, policies/, or .github/workflows/ in this plan."
handoff_mode: cursor-build
todos:
  - id: todo-01-baseline-preflight
    content: "PE W0: lock immutable baseline (full SHA of origin/main) + capability probes (python>=3.10, uv, ANTHROPIC_API_KEY, ~/.cursor-governance launcher path); Program Lock bind; stop_and_replan on drift"
    status: completed
  - id: todo-02-architect-select
    content: "Run l9-global-architect: confirm adapter placement mirrors environment/agents/adapters/claude-code/; record ADR"
    status: pending
  - id: todo-03-dependency
    content: "uv add claude-agent-sdk; pin in pyproject.toml + uv.lock; verify bundled CLI resolves"
    status: pending
  - id: todo-04-harness
    content: "Create environment/agents/adapters/claude-agent-sdk/l9_agent.py (ClaudeSDKClient, setting_sources=[project], permission rules, invariant_guard, l9_dispatch, audit_logger, subagents, json_schema output, budget, checkpointing)"
    status: completed
  - id: todo-05-config-ssot
    content: "Add adapter config.yaml (protected files/prefixes, allowed/disallowed rules with invariant refs, budget, turns) - read-only consumer of ORG_INVARIANTS.yaml"
    status: completed
  - id: todo-06-validators
    content: "Add validate_agent_sdk_env.py (setting_sources includes project; every deny maps to an invariant; launcher path relative)"
    status: completed
  - id: todo-07-tests
    content: "tests/test_l9_agent.py: invariant_guard deny paths, launcher exit-code mapping, audit log shape, validator gates; no network"
    status: completed
  - id: todo-08-make-targets
    content: "Makefile: agent-sdk, agent-sdk-plan, agent-sdk-validate (stacked follow-up)"
    status: pending
  - id: todo-09-docs
    content: "Adapter README.md (done); AGENTS.md/CLAUDE.md surface rows + llm.txt via l9-update-agent-docs (follow-up)"
    status: in_progress
  - id: todo-10-verify
    content: "CI: make lint && pytest -q adapter tests && validate_agent_sdk_env.py; dry run in plan mode produces report + telemetry"
    status: pending
  - id: todo-11-pr
    content: "Stacked PR feat/claude-agent-sdk-adapter -> main; CODEOWNERS review; section receipt generated + validated"
    status: in_progress
---

# Claude Agent SDK adapter for Cursor-Governance

## Mission

Introduce the Claude Agent SDK as a third governed surface (after Cursor and Claude Code CLI/Web) that consumes the same committed governance artifacts and the same hook launcher, with zero new SSOT.

## Baseline (PE W0)

| Field | Value |
|-------|-------|
| repo | Quantum-L9/Cursor-Governance |
| branch | feat/claude-agent-sdk-adapter |
| baseline_sha | 8d5cf5f6d14d3ce6d14fce2424bc32d84f449744 |
| capability_probes | python>=3.10, uv, ANTHROPIC_API_KEY, ~/.cursor-governance/environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh |
| drift_policy | stop_and_replan |

## Scope

In scope: environment/agents/adapters/claude-agent-sdk/**, docs/plans/claude-agent-sdk-adapter.plan.md. Follow-up (stacked): Makefile targets, pyproject.toml/uv.lock, AGENTS.md/CLAUDE.md rows, llm.txt, ADR.

Out of scope (protected): CANONICAL_LAW.md, INVARIANTS.md, ORG_INVARIANTS.yaml, CODEOWNERS, .github/workflows/, rulesets/, policies/, security/, .claude/settings.json and l9_hook_exec.sh semantics.

## Architecture impact

- New adapter directory mirrors environment/agents/adapters/claude-code/ layout; no shared code forked.
- Governance flow: SDK hook event -> l9_dispatch -> l9_hook_exec.sh --class {governor|observer} -> existing L9 hook scripts. Governor veto exit code (config: governor_veto_exit_code) => PreToolUse deny.
- In-process invariant_guard adds a launcher-independent deny for SSOT paths.
- setting_sources=["project"] makes CLAUDE.md, .claude/settings.json, .mcp.json authoritative for the SDK exactly as for Claude Code.

### Adapter routing (from `registry/EXECUTION_ROUTING_POLICY.yaml`)

| Task class | Route |
|-----------|-------|
| audit / gap-analysis | l9-auditor subagent (Read, Grep, Glob only) |
| remediation | l9-remediator subagent, permission_mode acceptEdits, budget-capped |
| planning | permission_mode plan, no mutations |

## Verification

- pytest -q environment/agents/adapters/claude-agent-sdk/tests
- python environment/agents/adapters/claude-agent-sdk/validate_agent_sdk_env.py
- uv run environment/agents/adapters/claude-agent-sdk/l9_agent.py --mode plan
- test -s reports/agent_sdk/latest.json && test -s telemetry/agent_sdk_audit.jsonl

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Governor veto exit code differs from l9_hook_exec.sh | governor_veto_exit_code in config.yaml; confirm before merge |
| SDK drops CLAUDE.md if setting_sources omitted | G_SETTING_SOURCES validator + unit test |
| Runaway spend | max_budget_usd + max_turns; plan mode default in CI |
| Hook ordering non-deterministic | invariant_guard and l9_dispatch independent; deny wins |

## Rollback

- git revert <merge-sha>; uv remove claude-agent-sdk; uv lock
- Delete environment/agents/adapters/claude-agent-sdk/
- command / proof that rollback restored invariants: `make lint && pytest -q && git diff --stat origin/main -- CANONICAL_LAW.md INVARIANTS.md ORG_INVARIANTS.yaml` returns empty

## Section receipt

| Field | Value |
|-------|-------|
| receipt_path | <generated by skills/l9-plan-simple/scripts/generate_plan_section_receipt.py> |
| categories | `keep` (all existing adapters) \| `replace` (none) \| `delete` (none) \| `skip` (protected SSOT) |
| handoff_mode | cursor-build |
