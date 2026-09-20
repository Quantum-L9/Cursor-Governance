# Filetree

**Repository:** `cursor-governance`

Projection only. Generated from the live tree. Not authority.

<!-- l9-filetree: generated-from-tree -->

## Root files

- `AGENTS.md`
- `ARCHITECTURE.md`
- `CANONICAL_LAW.md`
- `CHANGELOG.md`
- `CLAUDE.md`
- `CODEOWNERS`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `INVARIANTS.md`
- `LICENSE`
- `Makefile`
- `ORG_INVARIANTS.yaml`
- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `TODO.md`
- `activation-command.md`
- `biome.json`
- `conftest.py`
- `end-session.yaml`
- `filetree.md`
- `llm.txt`
- `pyproject.toml`
- `requirements.txt`
- `sonar-project.properties`
- `uv.lock`

## Modules

| Path | Kind | Sources | README |
| --- | --- | --- | --- |
| `autonomy` | module | 8 | present |
| `autonomy/adapters` | submodule | 8 | present |
| `autonomy/adapters/claude_code` | submodule | 2 | present |
| `autonomy/adapters/cursor` | submodule | 4 | present |
| `autonomy/compiler` | submodule | 2 | present |
| `autonomy/examples` | corpus | 3 | present |
| `autonomy/examples/adapters` | corpus | 2 | present |
| `autonomy/policies` | corpus | 5 | present |
| `autonomy/runtime` | submodule | 12 | present |
| `autonomy/schemas` | corpus | 8 | present |
| `autonomy/validation` | submodule | 5 | present |
| `commands` | corpus | 23 | present |
| `commands/dora-commands` | corpus | 7 | present |
| `config` | corpus | 0 | present |
| `contracts` | corpus | 0 | present |
| `contracts/schemas` | corpus | 11 | present |
| `environment` | index | 6 | present |
| `environment/agents` | submodule | 2 | present |
| `environment/agents/adapters` | index | 7 | present |
| `environment/agents/adapters/claude-code` | submodule | 6 | present |
| `environment/agents/adapters/claude-code/hooks` | submodule | 15 | present |
| `environment/agents/adapters/claude-code/memory` | submodule | 3 | present |
| `environment/agents/adapters/claude-code/web` | submodule | 2 | present |
| `environment/agents/adapters/claude-desktop` | submodule | 1 | present |
| `environment/agents/adapters/codex` | corpus | 3 | present |
| `environment/agents/adapters/cursor` | submodule | 2 | present |
| `environment/agents/adapters/cursor/skills/l9-skill-gateway` | submodule | 0 | present |
| `environment/agents/adapters/gemini` | corpus | 3 | present |
| `environment/agents/adapters/generic` | corpus | 2 | present |
| `environment/agents/adapters/manus` | corpus | 3 | present |
| `environment/agents/cursor-subagents` | submodule | 1 | present |
| `environment/agents/deployment` | submodule | 4 | present |
| `environment/agents/deployment/renderers` | submodule | 2 | present |
| `environment/agents/docs` | corpus | 5 | present |
| `environment/agents/generated-data` | index | 11 | present |
| `environment/agents/generated-data/adapters` | submodule | 5 | present |
| `environment/agents/generated-data/ingress` | submodule | 4 | present |
| `environment/agents/generated-data/integration` | submodule | 2 | present |
| `environment/agents/generated-data/invalidation` | submodule | 2 | present |
| `environment/agents/generated-data/operations` | submodule | 5 | present |
| `environment/agents/generated-data/orchestration` | submodule | 7 | present |
| `environment/agents/generated-data/retrieval` | submodule | 4 | present |
| `environment/agents/generated-data/roles` | corpus | 6 | present |
| `environment/agents/generated-data/routes` | corpus | 6 | present |
| `environment/agents/generated-data/runtime` | submodule | 7 | present |
| `environment/agents/generated-data/schemas` | corpus | 5 | present |
| `environment/agents/integration` | submodule | 1 | present |
| `environment/agents/lifecycle` | submodule | 5 | present |
| `environment/agents/readiness` | submodule | 3 | present |
| `environment/agents/results` | submodule | 3 | present |
| `environment/agents/results/adapters` | submodule | 2 | present |
| `environment/agents/tools` | submodule | 3 | present |
| `environment/contracts/autonomy/meta` | corpus | 5 | present |
| `environment/contracts/execution` | corpus | 2 | present |
| `environment/contracts/execution/adr` | corpus | 13 | present |
| `environment/contracts/execution/templates` | corpus | 2 | present |
| `environment/ide` | corpus | 8 | present |
| `environment/mcp` | corpus | 2 | present |
| `environment/plugins` | corpus | 4 | present |
| `environment/program-execution` | submodule | 1 | present |
| `environment/program-execution-campaigns/CG-PES-RUN2-HARDENING` | corpus | 3 | present |
| `environment/program-execution/adapters` | submodule | 1 | present |
| `environment/program-execution/adapters/chatgpt` | submodule | 3 | present |
| `environment/program-execution/adapters/ci` | index | 2 | present |
| `environment/program-execution/adapters/ci/generic-shell` | submodule | 2 | present |
| `environment/program-execution/adapters/ci/github-actions` | submodule | 4 | present |
| `environment/program-execution/adapters/claude-code` | submodule | 4 | present |
| `environment/program-execution/adapters/codex` | submodule | 1 | present |
| `environment/program-execution/adapters/common` | submodule | 14 | present |
| `environment/program-execution/adapters/cursor-background` | submodule | 1 | present |
| `environment/program-execution/adapters/cursor-foreground` | submodule | 1 | present |
| `environment/program-execution/adapters/deployment/target-specific` | submodule | 3 | present |
| `environment/program-execution/adapters/gemini` | submodule | 1 | present |
| `environment/program-execution/adapters/github` | submodule | 1 | present |
| `environment/program-execution/adapters/github/checks` | submodule | 3 | present |
| `environment/program-execution/adapters/github/common` | submodule | 5 | present |
| `environment/program-execution/adapters/github/deployments` | submodule | 3 | present |
| `environment/program-execution/adapters/github/remote-actions` | submodule | 4 | present |
| `environment/program-execution/adapters/manus` | submodule | 1 | present |
| `environment/program-execution/audits` | corpus | 2 | present |
| `environment/program-execution/campaigns` | corpus | 5 | present |
| `environment/program-execution/campaigns/bounded-replanning-v1` | corpus | 2 | present |
| `environment/program-execution/campaigns/cc-pe-intent-compiler-v1` | corpus | 4 | present |
| `environment/program-execution/campaigns/eie-inference-isolation-v1` | corpus | 2 | present |
| `environment/program-execution/campaigns/l9-devpack-program-execution-hardening` | corpus | 5 | present |
| `environment/program-execution/campaigns/l9-ecosystem-fix-plan` | corpus | 6 | present |
| `environment/program-execution/campaigns/l9-ecosystem-fix-plan/deliverables/ib-odoo_19/reference` | submodule | 2 | present |
| `environment/program-execution/campaigns/l9-ecosystem-fix-plan/history/v1.0.0` | corpus | 3 | present |
| `environment/program-execution/campaigns/level3-make-pr-single-path` | corpus | 4 | present |
| `environment/program-execution/campaigns/pe-router-capability-safety-v4` | corpus | 2 | present |
| `environment/program-execution/campaigns/pe-v3-hardening` | index | 2 | present |
| `environment/program-execution/campaigns/pe-v3-hardening/audits` | corpus | 2 | present |
| `environment/program-execution/campaigns/pe-v3-hardening/blueprint` | corpus | 33 | present |
| `environment/program-execution/campaigns/pe-v3-hardening/blueprint/schemas` | corpus | 23 | present |
| `environment/program-execution/campaigns/pe-v3-hardening/blueprint/scripts` | submodule | 2 | present |
| `environment/program-execution/campaigns/scripts` | submodule | 1 | present |
| `environment/program-execution/campaigns/session-runtime-hydration-convergence-v1` | corpus | 2 | present |
| `environment/program-execution/compiler` | submodule | 19 | present |
| `environment/program-execution/compiler/schemas` | corpus | 8 | present |
| `environment/program-execution/conformance` | submodule | 2 | present |
| `environment/program-execution/conformance/fixtures/hostile` | corpus | 8 | present |
| `environment/program-execution/conformance/fixtures/negative` | corpus | 6 | present |
| `environment/program-execution/conformance/fixtures/positive` | corpus | 5 | present |
| `environment/program-execution/conformance/schemas` | corpus | 11 | present |
| `environment/program-execution/core` | corpus | 11 | present |
| `environment/program-execution/core/program-execution-blueprint-template` | corpus | 33 | present |
| `environment/program-execution/core/program-execution-blueprint-template/schemas` | corpus | 23 | present |
| `environment/program-execution/core/program-execution-blueprint-template/scripts` | submodule | 2 | present |
| `environment/program-execution/core/program-execution-controller-template` | corpus | 10 | present |
| `environment/program-execution/core/program-execution-controller-template/policy` | corpus | 8 | present |
| `environment/program-execution/core/program-execution-controller-template/references` | corpus | 12 | present |
| `environment/program-execution/core/program-execution-controller-template/schemas` | corpus | 12 | present |
| `environment/program-execution/core/program-execution-controller-template/scripts` | submodule | 4 | present |
| `environment/program-execution/core/program-execution-controller-template/scripts/pec` | submodule | 18 | present |
| `environment/program-execution/core/scripts` | submodule | 5 | present |
| `environment/program-execution/core/shared` | submodule | 1 | present |
| `environment/program-execution/core/shared/schemas` | corpus | 6 | present |
| `environment/program-execution/core/validation` | corpus | 2 | present |
| `environment/program-execution/integrations` | submodule | 1 | present |
| `environment/program-execution/integrations/agent-identity` | submodule | 2 | present |
| `environment/program-execution/integrations/autonomy-control-plane` | submodule | 4 | present |
| `environment/program-execution/integrations/bootstrap` | submodule | 4 | present |
| `environment/program-execution/integrations/cursor-task-tools` | submodule | 3 | present |
| `environment/program-execution/integrations/graphiti` | submodule | 1 | present |
| `environment/program-execution/integrations/subagent-generated-data` | submodule | 4 | present |
| `environment/program-execution/mission` | submodule | 2 | present |
| `environment/program-execution/mission/schemas` | corpus | 2 | present |
| `environment/program-execution/peer_execution` | submodule | 27 | present |
| `environment/program-execution/peer_execution/autonomy` | submodule | 14 | present |
| `environment/program-execution/registry` | corpus | 8 | present |
| `environment/program-execution/scripts` | submodule | 35 | present |
| `environment/program-execution/validation` | corpus | 2 | present |
| `environment/program-execution/validation/history` | corpus | 4 | present |
| `environment/skill-adapters` | corpus | 2 | present |
| `governance` | corpus | 4 | present |
| `intelligence` | corpus | 4 | present |
| `intelligence/context-memory` | submodule | 1 | present |
| `intelligence/context-memory/sessions` | corpus | 11 | present |
| `intelligence/models` | corpus | 3 | present |
| `intelligence/reasoning` | submodule | 1 | present |
| `kernels` | corpus | 17 | present |
| `kernels/L9 Coding Control Plane` | corpus | 10 | present |
| `kernels/L9 Coding Control Plane/ai-control-plane` | corpus | 7 | present |
| `learning` | corpus | 1 | present |
| `learning/failures` | corpus | 8 | present |
| `learning/graphiti-episodes` | corpus | 6 | present |
| `learning/patterns` | corpus | 2 | present |
| `learning/solutions` | corpus | 2 | present |
| `ops` | module | 1 | present |
| `ops/autonomy` | submodule | 25 | present |
| `ops/config` | corpus | 15 | present |
| `ops/contracts` | submodule | 11 | present |
| `ops/contracts/adapters` | submodule | 1 | present |
| `ops/graphiti` | submodule | 3 | present |
| `ops/graphiti/distill_queue` | submodule | 4 | present |
| `ops/graphiti/docs` | corpus | 2 | present |
| `ops/graphiti/hydration` | submodule | 13 | present |
| `ops/graphiti/memory-bank-template` | corpus | 5 | present |
| `ops/hooks` | submodule | 30 | present |
| `ops/lib` | submodule | 1 | present |
| `ops/memory` | submodule | 16 | present |
| `ops/schemas` | corpus | 3 | present |
| `ops/scripts` | submodule | 117 | present |
| `ops/scripts/adapters` | submodule | 2 | present |
| `ops/scripts/lib` | submodule | 22 | present |
| `ops/secrets` | submodule | 20 | present |
| `ops/skill_routing` | submodule | 7 | present |
| `ops/ui-operator` | submodule | 2 | present |
| `ops/ui-operator/cartridges` | corpus | 2 | present |
| `ops/ui-operator/schemas` | corpus | 2 | present |
| `pipeline` | corpus | 3 | present |
| `profiles` | corpus | 12 | present |
| `prompts` | corpus | 0 | present |
| `protocols` | corpus | 5 | present |
| `releases` | corpus | 1 | present |
| `reports` | corpus | 1 | present |
| `rules` | corpus | 3 | present |
| `schemas` | corpus | 1 | present |
| `scripts` | module | 5 | present |
| `security` | corpus | 2 | present |
| `skills` | corpus | 1 | present |
| `skills/l9-api-smoke-testing` | submodule | 0 | present |
| `skills/l9-architecture-decision-records` | submodule | 0 | present |
| `skills/l9-audit-plans` | submodule | 0 | present |
| `skills/l9-audit-plans/scripts` | submodule | 4 | present |
| `skills/l9-auditing-performance` | submodule | 0 | present |
| `skills/l9-auditing-security` | submodule | 0 | present |
| `skills/l9-aws-secrets` | submodule | 0 | present |
| `skills/l9-bounded-autonomy` | submodule | 0 | present |
| `skills/l9-chat-extraction` | submodule | 0 | present |
| `skills/l9-ci-ops` | submodule | 0 | present |
| `skills/l9-claude-code-deepseek` | submodule | 0 | present |
| `skills/l9-claude-coding-contract-compiler` | submodule | 0 | present |
| `skills/l9-claude-coding-contract-compiler/scripts` | submodule | 6 | present |
| `skills/l9-cli-optimization` | submodule | 0 | present |
| `skills/l9-cli-optimization/scripts` | submodule | 16 | present |
| `skills/l9-code-analysis` | submodule | 0 | present |
| `skills/l9-code-graph-rag-mcp` | submodule | 0 | present |
| `skills/l9-code-graph-rag-mcp/scripts` | submodule | 5 | present |
| `skills/l9-code-maintenance` | submodule | 0 | present |
| `skills/l9-code-maintenance/scripts` | submodule | 3 | present |
| `skills/l9-component-verification` | submodule | 0 | present |
| `skills/l9-context7-docs` | submodule | 0 | present |
| `skills/l9-dag-authoring` | submodule | 0 | present |
| `skills/l9-dag-authoring/fixtures` | submodule | 3 | present |
| `skills/l9-dag-authoring/scripts` | submodule | 11 | present |
| `skills/l9-e2e-blocker-resolution` | submodule | 0 | present |
| `skills/l9-end-session` | submodule | 0 | present |
| `skills/l9-forge` | submodule | 0 | present |
| `skills/l9-gap-analysis` | submodule | 0 | present |
| `skills/l9-git-work-preserve` | submodule | 0 | present |
| `skills/l9-git-work-preserve/scripts` | submodule | 10 | present |
| `skills/l9-global-architect` | submodule | 0 | present |
| `skills/l9-gmp-protocol` | submodule | 0 | present |
| `skills/l9-governance-symlinks` | submodule | 0 | present |
| `skills/l9-graphiti-memory` | submodule | 0 | present |
| `skills/l9-idea-execute` | submodule | 0 | present |
| `skills/l9-idea-execute/scripts` | submodule | 9 | present |
| `skills/l9-idea-foundry` | submodule | 0 | present |
| `skills/l9-idea-foundry/scripts` | submodule | 10 | present |
| `skills/l9-incident-response` | submodule | 0 | present |
| `skills/l9-intelligence-harvest` | submodule | 0 | present |
| `skills/l9-intelligence-harvest/scripts` | submodule | 8 | present |
| `skills/l9-issue-remediation` | submodule | 0 | present |
| `skills/l9-issue-remediation/scripts` | submodule | 8 | present |
| `skills/l9-kubernetes-deploying` | submodule | 0 | present |
| `skills/l9-mac-storage-triage` | submodule | 0 | present |
| `skills/l9-mac-storage-triage/scripts` | submodule | 14 | present |
| `skills/l9-mac-storage-triage/scripts/actions` | submodule | 8 | present |
| `skills/l9-mac-storage-triage/scripts/lib` | submodule | 1 | present |
| `skills/l9-monitoring-terminal-errors` | submodule | 0 | present |
| `skills/l9-pe-campaign-activate` | submodule | 0 | present |
| `skills/l9-pe-campaign-activate/scripts` | submodule | 3 | present |
| `skills/l9-pe-nuggets` | submodule | 0 | present |
| `skills/l9-pe-nuggets/scripts` | submodule | 1 | present |
| `skills/l9-pipeline-audit` | submodule | 0 | present |
| `skills/l9-pipeline-audit/scripts` | submodule | 6 | present |
| `skills/l9-pipeline-orchestrator` | submodule | 5 | present |
| `skills/l9-plan` | submodule | 0 | present |
| `skills/l9-plan-simple` | submodule | 0 | present |
| `skills/l9-plan-simple/scripts` | submodule | 5 | present |
| `skills/l9-plan/scripts` | submodule | 11 | present |
| `skills/l9-pr-digest` | submodule | 0 | present |
| `skills/l9-pr-digest/scripts` | submodule | 6 | present |
| `skills/l9-pr-remediation` | submodule | 0 | present |
| `skills/l9-pr-remediation/scripts` | submodule | 11 | present |
| `skills/l9-prompt-engineering` | submodule | 0 | present |
| `skills/l9-python-tdd-with-uv` | submodule | 0 | present |
| `skills/l9-recursive-optimization` | submodule | 0 | present |
| `skills/l9-repo-index` | submodule | 0 | present |
| `skills/l9-repo-sync` | submodule | 0 | present |
| `skills/l9-repo-sync/scripts` | submodule | 4 | present |
| `skills/l9-repository-renovation` | submodule | 0 | present |
| `skills/l9-repository-renovation/scripts` | submodule | 11 | present |
| `skills/l9-setting-up-ci` | submodule | 0 | present |
| `skills/l9-setting-up-terraform` | submodule | 0 | present |
| `skills/l9-skill-compiler` | submodule | 0 | present |
| `skills/l9-skill-compiler/scripts` | submodule | 6 | present |
| `skills/l9-structured-reasoning` | submodule | 0 | present |
| `skills/l9-structured-reasoning/scripts` | submodule | 8 | present |
| `skills/l9-ui-operator` | submodule | 0 | present |
| `skills/l9-update-agent-docs` | submodule | 0 | present |
| `skills/l9-update-agent-docs/scripts` | submodule | 13 | present |
| `skills/l9-update-agent-docs/scripts/surface_analyzers` | submodule | 3 | present |
| `skills/l9-wire-into-repo` | submodule | 0 | present |
| `skills/l9-wire-into-repo/scripts` | submodule | 2 | present |
| `skills/l9-ynp` | submodule | 0 | present |
| `skills/l9-ynp/scripts` | submodule | 1 | present |
| `telemetry` | corpus | 0 | present |
| `tools` | module | 1 | present |
| `tools/l9_agent_ui_control` | submodule | 15 | present |
| `tools/l9_agent_ui_control/helpers` | submodule | 2 | present |
| `tools/l9_agent_ui_control/sql` | corpus | 6 | present |
| `workflows` | module | 11 | present |
| `workflows/Dags-Harvest` | corpus | 6 | present |
| `workflows/dags` | submodule | 13 | present |
| `workflows/dags/_runtime` | submodule | 2 | present |
| `workflows/dags/gmp` | submodule | 5 | present |
| `workflows/dags/gmp/nodes` | submodule | 2 | present |
| `workflows/dags/intelligence_harvest` | submodule | 6 | present |
| `workflows/defs` | corpus | 4 | present |
| `workflows/nodes` | submodule | 7 | present |
| `workflows/session` | submodule | 3 | present |

## Tree

```
.
generated/
  governance/
kernels/
  Build.md
  Diagnose First Kernel.md
  Flawless Victory.md
  GMP Rules Hardening — Execute.md
  Gold Nugget Extractor 🚀.md
  Improve.md
  Leverage.md
  Pre-flight.md
  Preflight 2.md
  Recursive Alignment.md
  Recursive Improvement (L9).md
  Recursive Leverage.md
  Rules Hardening Batch Orchestrator.md
  Skill Hardening Batch Orchestrator.md
  Validate & Eliminate Stubs.md
  Validate & Fill Gaps.md
  Validate & Repair.md
  L9 Coding Control Plane/
    AGENTS.md
    ARCHITECTURE.md
    CHANGELOG.md
    CONTRIBUTING.md
    MANIFEST.md
    ROADMAP.md
    SECURITY.md
    SPECIFICATION.md
    package.json
    pyproject.toml
    ai-control-plane/
      AUDIT.md
      BUILD.md
      CHANGE.md
      DEFINITION_OF_DONE.md
      PLAN.md
      RELEASE.md
      VALIDATION.md
    docs/
pipeline/
  pipeline_kickstart.md
  pipeline_midstream.md
  pipeline_precommit.md
releases/
  POLICY_RELEASE.schema.yaml
tools/
  README.md
  check_repo_hygiene.py
  l9_agent_ui_control/
    README.md
    __init__.py
    config.py
    decorators.py
    drive_ibpc_paste.py
    drive_ssms_extract.py
    executor.py
    install_local.sh
    install_remote_tunnel.sh
    integrity_check.py
    local_console.py
    phase_b_extract.sh
    reverse_tunnel.sh
    runner.py
    task_queue.py
    websocket_client.py
    helpers/
      README.md
      __init__.py
      logging.py
    sql/
      01_catalog_tables.sql
      02_catalog_columns.sql
      03_discover_payment_like_tables.sql
      04_list_p0_dump_targets.sql
      05_probe_payment_tops.sql
      07_p0_sample_tops.sql
intelligence/
  adaptive-reasoning.md
  intelligence-manifest.json
  pre-build-question-framework.md
  system-reflection.md
  context-memory/
    README.md
    show_context_graphiti.py
    sessions/
      2026-02-10-20.json
      2026-02-15-15.json
      2026-02-15-18.json
      2026-03-01-14.json
      2026-03-16-14.json
      2026-03-16-15.json
      2026-03-26-16.json
      2026-03-26-19.json
      2026-03-27-00.json
      2026-04-07-09.json
      index.json
  meta-learning/
  workspace/
  models/
    command_execution_risk.md
    escalation_need.md
    file_compliance_risk.md
  reasoning/
    README.md
    reasoning-snapshot-generator.py
  standards/
config/
  subsystems/
security/
  api-key-verification.md
  security-audit.md
learning/
  credentials-policy.md
  failures/
    check-must-not-recreate-archived.md
    formal_lessons_pending.json
    integrity-tool-must-not-heal.md
    learned-lessons-corpus.md
    precommit-hook-attribution.md
    reasoning_insights.md
    repeated-mistakes.md
    worktree-make-pr-wiring.md
    incidents/
  patterns/
    anti-patterns.md
    quick-fixes.md
  solutions/
    authentication-fixes.md
    json-issues.md
  graphiti-episodes/
    audit-log.episodes.json
    manifest.json
    quick-fixes.episodes.json
    repeated-mistakes.episodes.json
    solutions.episodes.json
    violations.episodes.json
contracts/
  schemas/
    canonical.schema.capability_contract.v1.yaml
    canonical.schema.contract_extraction_record.v1.yaml
    canonical.schema.contract_projection_binding.v1.yaml
    canonical.schema.contract_registry.v1.yaml
    canonical.schema.cursor_rules_manifest.v3.yaml
    canonical.schema.evidence_contract.v1.yaml
    canonical.schema.governance_contract.v1.yaml
    canonical.schema.invariant_contract.v1.yaml
    canonical.schema.policy_contract.v1.yaml
    canonical.schema.rule_activation_binding.v1.yaml
    canonical.schema.workflow_contract.v1.yaml
workflows/
  README.md
  __init__.py
  gmp_enforcer.py
  gmp_executor.py
  harvest_deploy.py
  harvest_executor.py
  lint_fix_executor.py
  migrate_executor.py
  runner.py
  state.py
  use_harvest_executor.py
  wire_executor.py
  dags/
    README.md
    __init__.py
    dag_authoring_dag.py
    gmp_execution_dag.py
    gmp_langgraph_executor.py
    harvest_deploy_dag.py
    inspect_dag.py
    intelligence_harvest_dag.py
    plan_simple_build_dag.py
    pr_train_dag.py
    readme_pipeline_dag.py
    refactoring_dag.py
    slash_command_update_dag.py
    wire_dag.py
    gmp/
      README.md
      __init__.py
      executor.py
      graph.py
      routing.py
      state.py
      nodes/
        README.md
        __init__.py
        core.py
    intelligence_harvest/
      README.md
      __init__.py
      executor.py
      graph.py
      nodes.py
      routing.py
      state.py
    _runtime/
      README.md
      __init__.py
      durable_checkpointer.py
  Dags-Harvest/
    DAG-Harvest-1.md
    DAG-Harvest-2.md
    DAG-Harvest-3.md
    DAG-Harvest-4.md
    DAG-Harvest-5.md
    DAG-Harvest-6-MAKE DAGS.md
  nodes/
    README.md
    __init__.py
    checkpoint.py
    deploy.py
    extract.py
    inject.py
    report.py
    validate.py
  defs/
    gmp-execution.yaml
    harvest-deploy.yaml
    readme-pipeline.yaml
    workflow-template.yaml
  session/
    README.md
    __init__.py
    interface.py
    registry.py
foundation/
  security/
schemas/
  org-invariants.schema.json
autonomy/
  README.md
  __init__.py
  cli.py
  errors.py
  io.py
  models.py
  policy_loader.py
  versioning.py
  wave3_cli.py
  runtime/
    README.md
    __init__.py
    artifacts.py
    capability_gateway.py
    claims.py
    cli.py
    engine.py
    leases.py
    receipts.py
    scheduler.py
    store.py
    timeutil.py
    types.py
  policies/
    adapter-requirements.json
    operation-aliases.json
    pipeline-invariants.json
    resource-classes.json
    role-capabilities.json
  schemas/
    adapter-config.schema.json
    agent-contract.schema.json
    agent-deployment.schema.json
    agent-lease.schema.json
    artifact-envelope.schema.json
    campaign-authorization.schema.json
    conformance-report.schema.json
    orchestration-receipt.schema.json
  adapters/
    README.md
    __init__.py
    bridge.py
    conformance.py
    contract_renderer.py
    heartbeat_hook.py
    orchestrator.py
    protocol.py
    tool_hook.py
    cursor/
      README.md
      __init__.py
      adapter.py
      host_bridge.py
      mint_admission.py
    claude_code/
      README.md
      __init__.py
      adapter.py
  examples/
    w7-actions.json
    w7-campaign.json
    w7-deployment.json
    adapters/
      claude-code.json
      cursor.json
  compiler/
    README.md
    __init__.py
    graph_compiler.py
  validation/
    README.md
    __init__.py
    doctor.py
    golden_trace.py
    graph_linter.py
    simulator.py
execution-governance/
scripts/
  README.md
  __init__.py
  claude-deepseek.sh
  generate_subsystem_readmes.py
  preflight.sh
  verify-routing.sh
governance/
  ASSERTION_TYPES.yaml
  CHANGE_PROCESS.md
  POLICY_MODEL.md
  TRUST_MODEL.md
rules/
  RULES-MANIFEST.json
  RULES-MANIFEST.md
  RULES-MANIFEST.yaml
prompts/
environment/
  ide/
    exceptions.yaml
    extensions.core.json
    extensions.eslint_owned.json
    policy.json
    render.cursor.json
    settings.base.json
    settings.node.json
    settings.python.json
  program-execution/
    README.md
    program_policy.py
    core/
      ALIGNMENT_REPORT.md
      ARCHITECTURE.md
      CANONICAL_VOCABULARY.yaml
      CHANGELOG.md
      COMPATIBILITY.yaml
      CONVERGENCE_REPORT.yaml
      DELTA_REPORT.md
      IMPROVEMENT_REPORT.md
      MANIFEST.yaml
      RELEASE_NOTES.md
      VALIDATION.md
      shared/
        README.md
        blueprint_identity.py
        schemas/
          action-authorization.schema.json
          campaign-source.schema.json
          evidence-reference.schema.json
          gate-evaluation.schema.json
          handoff-receipt.schema.json
          replan-revision.schema.json
      program-execution-controller-template/
        ARCHITECTURE.md
        CHANGELOG.md
        CONTROLLER.yaml
        DESIGN_RATIONALE.md
        INSTANTIATION_GUIDE.md
        MANIFEST.yaml
        RUNBOOK.md
        SECURITY.md
        TEMPLATE_VARIABLES.yaml
        VALIDATION.md
        receipts/
        references/
          APPROVALS_WAIVERS_AND_HANDOFF.md
          AUTHORITY_AND_RISK.md
          AUTONOMY_BRIDGE.md
          BLUEPRINT_MAPPING.md
          CONTRACTS_AND_SCOPE.md
          NEGATIVE_TEST_MATRIX.md
          RECOVERY.md
          REMOTE_ACTIONS.md
          SCHEDULER_AND_LEASES.md
          STATE_MACHINE.md
          VERIFICATION_AND_RECEIPTS.md
          WORKER_ADAPTER.md
        schemas/
          approval.schema.json
          attempt-receipt.schema.json
          controller.schema.json
          event.schema.json
          gate-evaluation.schema.json
          handoff-receipt.schema.json
          program-lock.schema.json
          repository-registration.schema.json
          source-contract.schema.json
          task-contract.schema.json
          verification-receipt.schema.json
          waiver.schema.json
        scripts/
          README.md
          instantiate.py
          pec.py
          run_negative_tests.py
          validate_controller.py
          pec/
            README.md
            __init__.py
            attempts.py
            blueprint.py
            cli.py
            common.py
            contracts.py
            controller.py
            dispatch.py
            exec_env.py
            gates.py
            ledger.py
            preflight.py
            reasons.py
            replan.py
            runtime.py
            signals.py
            state.py
            workspace_reset.py
        policy/
          authority.yaml
          autonomy.yaml
          evidence.yaml
          parallelism.yaml
          remote-actions.yaml
          risk-tiers.yaml
          stop-conditions.yaml
          waivers.yaml
      program-execution-blueprint-template/
        AGENT_EXECUTION_CONTRACT.md
        ARCHITECTURE.md
        AUTHORITY_REGISTRY.yaml
        CHANGELOG.md
        CONVERGENCE_GATES.yaml
        CURRENT_STATE_DELTA.yaml
        CUTOVER_AND_ROLLBACK.yaml
        DECISION_REGISTER.yaml
        DEFINITION_OF_DONE.md
        DEPENDENCY_GRAPH.yaml
        DESIGN_RATIONALE.md
        DO_NOT_BUILD.yaml
        EVIDENCE_CATALOG.yaml
        EXECUTION_INDEX.yaml
        EXECUTION_TARGETS.yaml
        EXECUTION_WAVES.yaml
        EXECUTIVE_DECISION.md
        HANDOFF.md
        INSTANTIATION_GUIDE.md
        MANIFEST.yaml
        OBSERVABILITY_PLAN.yaml
        OPERATING_MODEL.md
        PHASE0_USER_CONFIG.yaml
        PROGRAM.yaml
        RISK_REGISTER.yaml
        RUNBOOK.md
        SOURCE_TRACEABILITY.yaml
        TASK_CARDS.yaml
        TEMPLATE_VARIABLES.yaml
        UNKNOWN_REGISTER.yaml
        VALIDATION.md
        WAIVER_REGISTER.yaml
        WORKSTREAMS.yaml
        schemas/
          acceptance-receipt.schema.json
          authority-registry.schema.json
          convergence-gate.schema.json
          convergence-gates.schema.json
          current-state-delta.schema.json
          cutover-and-rollback.schema.json
          decision-register.schema.json
          dependency-graph.schema.json
          do-not-build.schema.json
          evidence-catalog.schema.json
          execution-index.schema.json
          execution-targets.schema.json
          execution-waves.schema.json
          observability-plan.schema.json
          phase0-user-config.schema.json
          program.schema.json
          risk-register.schema.json
          source-traceability.schema.json
          task-card.schema.json
          task-cards.schema.json
          unknown-register.schema.json
          waiver-register.schema.json
          workstreams.schema.json
        scripts/
          README.md
          instantiate.py
          validate_blueprint.py
      scripts/
        README.md
        generate_manifest.py
        instantiate_pair.py
        run_negative_tests.py
        validate_pair.py
        validate_replan.py
      validation/
        validation_report.yaml
        validation_summary.md
    audits/
      pec-remediation-workpack.v1.yaml
      pipeline-assembly-audit.v1.yaml
    mission/
      README.md
      binding.py
      mission.py
      schemas/
        mission-program-binding.schema.json
        mission.schema.json
    integrations/
      README.md
      __init__.py
      agent-identity/
        README.md
        identity_binding.py
        registry_reader.py
      bootstrap/
        README.md
        context_renderer.py
        peer_context.py
        peer_readiness.py
        status_probe.py
      cursor-task-tools/
        README.md
        background_transport.py
        foreground_transport.py
        task_mapper.py
      autonomy-control-plane/
        README.md
        bridge.py
        contract_mapper.py
        grant.py
        program_authority.py
      graphiti/
        README.md
        context_reader.py
      subagent-generated-data/
        README.md
        campaign_summary.py
        compile_units.py
        outcome_publisher.py
        receipt_projection.py
    adapters/
      README.md
      __init__.py
      claude-code/
        README.md
        excerpts.py
        permission_renderer.py
        provider.py
        stream_parser.py
      gemini/
        README.md
        provider.py
      ci/
        github-actions/
          README.md
          artifact_collector.py
          dispatcher.py
          monitor.py
          provider.py
        generic-shell/
          README.md
          evidence_collector.py
          provider.py
      codex/
        README.md
        provider.py
      common/
        README.md
        __init__.py
        approvals.py
        base.py
        contracts.py
        core_receipts.py
        digests.py
        errors.py
        imports.py
        models.py
        protocol.py
        receipts.py
        runtime_store.py
        schema_registry.py
        subprocess_runner.py
      github/
        README.md
        __init__.py
        remote-actions/
          README.md
          branch.py
          provider.py
          pull_request.py
          push.py
        checks/
          README.md
          check_publisher.py
          provider.py
          status_reader.py
        common/
          README.md
          __init__.py
          auth_probe.py
          gh_transport.py
          permission_probe.py
          response_normalizer.py
        deployments/
          README.md
          deployment_record.py
          environment_gate.py
          provider.py
      deployment/
        target-specific/
          README.md
          generate_target_adapter.py
          provider.py
          validate_target_adapter.py
      manus/
        README.md
        provider.py
      cursor-background/
        README.md
        provider.py
      chatgpt/
        README.md
        artifact_collector.py
        envelope_renderer.py
        provider.py
      cursor-foreground/
        README.md
        provider.py
    scripts/
      README.md
      __init__.py
      accept_blueprint.py
      adapter_cli.py
      apply_repository_alignment.py
      blueprint_ops.py
      campaign_exec.py
      campaign_input.py
      campaign_pr_copy.py
      collect_evidence.py
      compile_architecture_intent.py
      compile_campaign_source.py
      context7_stack_proof.py
      gate_s0_baseline.py
      generate_manifest.py
      launchability.py
      pe_prepare_state.py
      pe_timing.py
      pe_trace.py
      pe_worker.py
      peer_execution_cli.py
      probe_executable_peers.py
      probe_execution_adapters.py
      provider_loader.py
      render_adapter_matrix.py
      render_capability_index.py
      replay_campaign.py
      router.py
      run_campaign.py
      run_conformance.py
      run_parity_gate.py
      run_peer_task_pipeline.py
      validate_campaign_promotion.py
      validate_execution_adapters.py
      validate_manifest.py
      validate_thin_providers.py
    registry/
      EXECUTION_ADAPTER_HEALTH.yaml
      EXECUTION_ADAPTER_REGISTRY.yaml
      EXECUTION_CAPABILITY_INDEX.yaml
      EXECUTION_CONCURRENCY_POLICY.yaml
      EXECUTION_ERROR_MAPPING.yaml
      EXECUTION_FAILOVER_POLICY.yaml
      EXECUTION_PROFILE_REGISTRY.yaml
      EXECUTION_ROUTING_POLICY.yaml
    environment/
      program-execution/
        campaigns/
          pe-v3-hardening/
            integrity/
    campaigns/
      CAMPAIGN_EXECUTION_POLICY.yaml
      CAMPAIGN_STATUS.yaml
      COMPILE_ALLOWLIST.yaml
      ECOSYSTEM_ODOO_ALIGNMENT.yaml
      PE_COMPILER_MODULE_ALIGNMENT.yaml
      session-runtime-hydration-convergence-v1/
        CAMPAIGN_SOURCE.yaml
        source-integrity-receipt.json
      bounded-replanning-v1/
        CAMPAIGN_SOURCE.yaml
        source-integrity-receipt.json
        handoff/
      level3-make-pr-single-path/
        CAMPAIGN_SOURCE.yaml
        HOST_REGISTRATIONS.yaml
        INTENT.yaml
        source-integrity-receipt.json
        handoff/
      eie-inference-isolation-v1/
        CAMPAIGN_SOURCE.yaml
        source-integrity-receipt.json
      l9-ecosystem-fix-plan/
        AUTH-001-SUPERSESSION.yaml
        CAMPAIGN_EXECUTION_BINDING.yaml
        CAMPAIGN_SOURCE.yaml
        CURRENT_STATE.yaml
        EXECUTION_FROM_ODOO.md
        source-integrity-receipt.json
        handoff/
        deliverables/
          ib-odoo_19/
            reference/
              README.md
              plasticos_ceg_match_mapper.py
              plasticos_eie_converge_mapper.py
        history/
          v1.0.0/
            CAMPAIGN_SOURCE.yaml
            handoff.json
            source-integrity-receipt.json
      pe-router-capability-safety-v4/
        CAMPAIGN_SOURCE.yaml
        source-integrity-receipt.json
      adr-identity-integrity-v1/
      scripts/
        README.md
        close_campaign.py
      pe-v3-hardening/
        audits/
          recursive-alignment.md
          validate-repair.md
        baseline/
        blueprint/
          AGENT_EXECUTION_CONTRACT.md
          ARCHITECTURE.md
          AUTHORITY_REGISTRY.yaml
          CHANGELOG.md
          CONVERGENCE_GATES.yaml
          CURRENT_STATE_DELTA.yaml
          CUTOVER_AND_ROLLBACK.yaml
          DECISION_REGISTER.yaml
          DEFINITION_OF_DONE.md
          DEPENDENCY_GRAPH.yaml
          DESIGN_RATIONALE.md
          DO_NOT_BUILD.yaml
          EVIDENCE_CATALOG.yaml
          EXECUTION_INDEX.yaml
          EXECUTION_TARGETS.yaml
          EXECUTION_WAVES.yaml
          EXECUTIVE_DECISION.md
          HANDOFF.md
          INSTANTIATION_GUIDE.md
          MANIFEST.yaml
          OBSERVABILITY_PLAN.yaml
          OPERATING_MODEL.md
          PHASE0_USER_CONFIG.yaml
          PROGRAM.yaml
          RISK_REGISTER.yaml
          RUNBOOK.md
          SOURCE_TRACEABILITY.yaml
          TASK_CARDS.yaml
          TEMPLATE_VARIABLES.yaml
          UNKNOWN_REGISTER.yaml
          VALIDATION.md
          WAIVER_REGISTER.yaml
          WORKSTREAMS.yaml
          schemas/
            acceptance-receipt.schema.json
            authority-registry.schema.json
            convergence-gate.schema.json
            convergence-gates.schema.json
            current-state-delta.schema.json
            cutover-and-rollback.schema.json
            decision-register.schema.json
            dependency-graph.schema.json
            do-not-build.schema.json
            evidence-catalog.schema.json
            execution-index.schema.json
            execution-targets.schema.json
            execution-waves.schema.json
            observability-plan.schema.json
            phase0-user-config.schema.json
            program.schema.json
            risk-register.schema.json
            source-traceability.schema.json
            task-card.schema.json
            task-cards.schema.json
            unknown-register.schema.json
            waiver-register.schema.json
            workstreams.schema.json
          scripts/
            README.md
            instantiate.py
            validate_blueprint.py
      l9-devpack-program-execution-hardening/
        AUTH-001-SUPERSESSION.yaml
        CAMPAIGN_SOURCE.yaml
        PROGRAM_SOURCE.md
        VALIDATION_EVIDENCE.md
        source-integrity-receipt.json
        handoff/
        deliverables/
          l9-devpack-compiler/
      cc-pe-intent-compiler-v1/
        AUTH-001-SUPERSESSION.yaml
        CAMPAIGN_SOURCE.yaml
        CONTRACT_SOURCE.md
        source-integrity-receipt.json
        handoff/
        deliverables/
          l9-devpack-compiler/
    compiler/
      README.md
      __init__.py
      architecture_classification.py
      architecture_coverage.py
      architecture_extractor.py
      architecture_intent.py
      architecture_ir.py
      architecture_target.py
      architecture_to_campaign.py
      blueprint_validate.py
      cli.py
      intent.py
      mission_admission.py
      mission_binding.py
      policy.py
      program_action.py
      prohibition_kind.py
      repo_truth.py
      resolver.py
      synthesizer.py
      policies/
      schemas/
        architecture-extractor-request.schema.json
        architecture-extractor-response.schema.json
        architecture-intent.schema.json
        architecture-resolution.schema.json
        autonomy-policy.schema.json
        intent-resolution.schema.json
        intent.schema.json
        mission-context.schema.json
      fixtures/
    peer_execution/
      README.md
      __init__.py
      approvals.py
      base.py
      bindings.py
      context.py
      contracts.py
      core_receipts.py
      digests.py
      driver_execution.py
      errors.py
      execution.py
      front_door.py
      golden_vectors.py
      imports.py
      models.py
      permissions.py
      profiles.py
      protocol.py
      provider.py
      receipts.py
      replan_projection.py
      runner.py
      runtime_store.py
      schema_registry.py
      subprocess_runner.py
      terminal_receipts.py
      validation_command.py
      autonomy/
        README.md
        __init__.py
        bootstrap.py
        claim_lease.py
        cli.py
        join_controller.py
        merge_coordinator.py
        models.py
        readiness.py
        resource_locks.py
        scheduler.py
        state_dir.py
        state_store.py
        validate_autonomy.py
        worker_lane.py
        examples/
        profiles/
    validation/
      VALIDATION.md
      adapter_matrix.yaml
      history/
        VALIDATION.pre_peer_execution_core.md
        collision_report.pre_peer_execution_core.yaml
        source_reuse_report.pre_peer_execution_core.yaml
        validation_report.pre_peer_execution_core.yaml
    conformance/
      README.md
      __init__.py
      helpers.py
      counterexamples/
      schemas/
        canonical-execution-request.schema.json
        canonical-provider-result.schema.json
        capability-receipt.schema.json
        context-manifest.schema.json
        deployment-receipt.schema.json
        executable-peer-readiness.schema.json
        execution-adapter-spec.schema.json
        execution-profile.schema.json
        host-envelope.schema.json
        lifecycle-receipt.schema.json
        remote-action-receipt.schema.json
      fixtures/
        positive/
          claude-code-direct-write.yaml
          cursor-foreground-readonly.yaml
          generic-shell-verification.yaml
          github-pr-authorized.yaml
          valid-adapter.yaml
        negative/
          authority-widening.yaml
          authorization-inflation.yaml
          missing-identity-binding.yaml
          self-verification.yaml
          stale-program-lock.yaml
          unsupported-capability.yaml
        hostile/
          cancellation-without-evidence.yaml
          changed-files-mismatch.yaml
          copied-core-schema.yaml
          credential-leak-attempt.yaml
          deployment-target-omitted.yaml
          forged-receipt-digest.yaml
          github-merge-escalation.yaml
          hostile-cases.yaml
  plugins/
    exceptions.yaml
    policy.json
    render.claude.json
    render.cursor.json
  contracts/
    autonomy/
      meta/
        autonomy-surface-profile.meta.md
        context-sensitive-git-guardrails.meta.md
        l4-local-autonomy.meta.md
        peer-execution-bounded-autonomy-runtime.meta.md
        root-autonomy-control-plane.meta.md
    execution/
      MANIFEST.yaml
      PEER_EXECUTION_THIN_ADAPTER_LAW.yaml
      adr/
        ADR-0017-peer-execution-core-upstream-of-adapters.md
        ADR-0018-separate-peer-identity-profile-transport-provider.md
        ADR-0019-canonical-execution-request-result-and-shared-transports.md
        ADR-0020-provider-neutral-inference-routing-deepseek-deferred.md
        ADR-0021-decompose-claude-code-thick-adapter.md
        ADR-0022-thin-adapter-conformance-is-merge-blocking.md
        ADR-0023-task-readiness-ordering-and-blocking-semantics.md
        ADR-0024-mission-parent-intent-and-controller-boundary.md
        ADR-0025-mission-revision-immutability-and-lifecycle-separation.md
        ADR-0026-exact-mission-program-binding-and-non-circular-blueprint-identity.md
        ADR-0027-mission-acceptance-separate-from-program-acceptance.md
        ADR-0032-universal-campaign-ingress-and-architecture-admission.md
        ADR-0033-compiler-owned-structure-target-resolution-and-program-owner.md
      templates/
        canonical.template.executable_plan.v1.plan.md
        canonical.template.executable_plan.v1.plan.md.meta.md
  agents/
    README.md
    runtime_paths.py
    runtime_paths_test.py
    tools/
      README.md
      render_principals.py
      validate_agents.py
      validate_executable_peers.py
    integration/
      README.md
      __init__.py
    cursor-subagents/
      README.md
      result_bridge.py
      schemas/
    lifecycle/
      README.md
      __init__.py
      compose_start.py
      compose_stop.py
      receipts.py
      schemas.py
    docs/
      DEPLOY.md
      MEMORY_TOPOLOGY.md
      SONAR-FP-PATH-ESCAPE.md
      WORK_CLAIM_PROTOCOL.md
      network-allowlist.md
    generated-data/
      ingress/
        README.md
        __init__.py
        ingest.py
        receipts.py
        security_gate.py
      config/
      integration/
        README.md
        __init__.py
        end_to_end_golden.py
      law/
      runtime/
        README.md
        __init__.py
        classifier.py
        harvester.py
        learning_closure.py
        packet_validator.py
        promotion_gate.py
        routing_engine.py
      roles/
        executor.yaml
        poller.yaml
        recon.yaml
        reviewer.yaml
        synthesis.yaml
        verifier.yaml
      operations/
        README.md
        __init__.py
        dead_letter.py
        health.py
        replay.py
        status.py
      schemas/
        generated-data-unit.schema.json
        learning-closure.schema.json
        provenance.schema.json
        routing-decision.schema.json
        subagent-data-packet.schema.json
      adapters/
        README.md
        __init__.py
        graphiti_memory.py
        ingest_memory_candidate.py
        l9_python.py
        odoo.py
      retrieval/
        README.md
        __init__.py
        context_query.py
        context_selector.py
        reuse_recorder.py
      orchestration/
        README.md
        __init__.py
        delivery_worker.py
        module_loader.py
        processor.py
        receipts.py
        retry_policy.py
        state_store.py
      invalidation/
        README.md
        __init__.py
        repository_event_bridge.py
      routes/
        architecture.yaml
        contracts.yaml
        memory.yaml
        opportunities.yaml
        patterns.yaml
        validation.yaml
    schemas/
    adapters/
      claude-code/
        README.md
        install.sh
        overlay_hosted_settings_env.py
        validate_claude_env.py
        validate_memory_enforcement.py
        validate_skill_activation.py
        verify_account_env.py
        generated/
        memory/
          README.md
          errors.py
          memory_bridge.py
          memory_state.py
        bin/
        web/
          README.md
          setup.bootstrap.sh
          setup.sh
        baseline/
        adapters/
        hooks/
          README.md
          bootstrap_capability_preflight.sh
          context7_stack_pretool.py
          l9_hook_exec.sh
          local_execution_gate_wrap.py
          memory_gate.py
          memory_prefetch.py
          memory_writeback.py
          merge_gate_wrap.py
          pr_summary_posttool.py
          root_file_advisory_wrap.py
          session_debt_wrap.py
          session_deps_cloud.sh
          session_start_claude_governance.sh
          skill_usage_logger.py
          user_prompt_skill_router.py
      gemini/
        gemini-block.md
        settings.template.json
        setup.md
      cursor/
        README.md
        install.sh
        validate_skill_projection.py
        skills/
          l9-skill-gateway/
            README.md
            SKILL.md
      codex/
        agents-block.md
        mcp.template.json
        setup.md
      claude-desktop/
        README.md
        render_claude_desktop_config.py
      manus/
        mcp-connector.json
        session_bootstrap.md
        setup.md
      generic/
        bootstrap.template.md
        mcp.template.json
    results/
      README.md
      __init__.py
      gateway.py
      receipts.py
      schemas/
      adapters/
        README.md
        __init__.py
        cursor_subagent.py
    deployment/
      README.md
      __init__.py
      receipts.py
      reconcile.py
      validate.py
      renderers/
        README.md
        __init__.py
        cursor.py
    readiness/
      README.md
      __init__.py
      compose.py
      probe_runtime.py
  mcp/
    CHATGPT_GITMCP_DOGFOOD.md
    master.mcp.json
  skill-adapters/
    LLM_RULE_ADAPTER_ROOTS.yaml
    SKILL_ADAPTER_ROOTS.yaml
  program-execution-campaigns/
    CG-PES-RUN2-HARDENING/
      CAMPAIGN_AUTHORIZATION.yaml
      CAMPAIGN_CHARTER.yaml
      CAMPAIGN_EXECUTION.yaml
ops/
  README.md
  __init__.py
  memory/
    README.md
    __init__.py
    canonical_validation.py
    cli.py
    control_plane_client.py
    diagnostics.py
    hydration.py
    legacy_reconciliation.py
    mcp_instantiation.py
    namespace_context.py
    receipt_contract.py
    receipts.py
    runtime_binding.py
    search_identity.py
    session_contracts.py
    session_state.py
    store_compat.py
  skill_routing/
    README.md
    __init__.py
    materialize.py
    receipt.py
    registry.py
    resolve.py
    route_prompt.py
    session_locator.py
  config/
    commit-verification-contract.json
    doctrine-baseline.rules.yaml
    governance-runtime-contract.yaml
    llm_rules_projection.yaml
    memory-binding.json
    memory-canonical-epoch.json
    memory-egress-allowlist.json
    memory-receipt-contract.json
    precommit-hook-contract.json
    python-contract.json
    root-file-protection.json
    wip-corpus.yaml
    wip-inventory.schema.yaml
    wip-prune-receipt.schema.yaml
    workspace-clean-routing.yaml
  secrets/
    README.md
    authed_npm.sh
    aws_cli_preflight.py
    bootstrap_agent_env.sh
    broker_identity.py
    capability_bind.py
    capability_broker.py
    capability_client.py
    capability_registry.py
    gh_npm.sh
    hydrate_infisical.py
    infisical_cli_login.py
    login_registry.py
    port_aws_to_infisical.py
    probe_broker.py
    resolve_secret.py
    session_start_secrets.py
    surface_trust.py
    sync_secrets_registry.py
    validate_capability_contract.py
    validate_capability_hosts.py
  contracts/
    README.md
    build_doctrine_census.py
    build_rule_doctrine_census.py
    build_rules.py
    cluster_doctrine.py
    detect_hidden_doctrine.py
    extract_doctrine.py
    render_cursor_rule.py
    resolve_rule_contracts.py
    validate_doctrine_ratchet.py
    validate_rule_binding.py
    validate_rule_projections.py
    adapters/
      README.md
      cursor_rules.py
  graphiti/
    README.md
    __init__.py
    graphiti_gate_lib.py
    graphiti_memory_client.py
    hydration/
      README.md
      __init__.py
      archive_transcript.py
      cli.py
      close_session.py
      compile_session_packet.py
      identity.py
      openai_fixed_host.py
      openai_key.py
      pickup_write.py
      redaction.py
      resume_signal_scorer.py
      session_latches.py
      transcript.py
    distill_queue/
      README.md
      __init__.py
      __main__.py
      enqueue.py
      worker.py
    docs/
      CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md
      MACHINE-ENV-POLICY.md
    memory-bank-template/
      RETIRED.md
      activeContext.md
      progress.md
      tasks.md
      tech-debt.md
  schemas/
    rule-manifest.schema.json
    rule-metadata.schema.json
    rule-selection.schema.json
  ui-operator/
    README.md
    console.py
    jit_drafter.py
    receipts/
    cartridges/
      github-packages-actions-access.yaml
      vercel-project-settings-stub.yaml
    drafts/
    schemas/
      cartridge.schema.yaml
      receipt.schema.yaml
  autonomy/
    README.md
    __init__.py
    acceptance_dry_run.py
    authorize_merge.py
    breakglass_receipt.py
    command_parse.py
    execution_profile.py
    first_publication_gate.py
    git_execution_exemption.py
    git_guardrails.py
    kernel_gate.py
    kernel_predicates.py
    l4_local.py
    local_execution_gate.py
    merge_gate.py
    open_pr_probe.py
    pr_board.py
    pr_fleet.py
    profile_loader.py
    resolve_execution_gate.py
    root_file_advisory.py
    session_debt.py
    stack_safe_merge.py
    surface_detect.py
    verification_bypass_gate.py
    worktree_isolation_gate.py
  hooks/
    README.md
    before-shell-execution-gate.sh
    before_mcp_code_graph_gate.sh
    before_shell_execution_gate.py
    before_submit_skill_router.py
    ensure_graphiti_tunnel.sh
    graphiti-gate-edits.sh
    graphiti-gate-shell.sh
    graphiti-gate-subagent.sh
    graphiti-mark-ok.sh
    graphiti-prefetch.sh
    graphiti-reset-generation.sh
    graphiti-session-end.sh
    graphiti_common.sh
    graphiti_gate_runner.sh
    l4-local-execution-gate-shell.sh
    lifecycle-subagent-start.sh
    lifecycle-subagent-stop.sh
    plan-kernel-execute-gate.sh
    plan_kernel_gate.py
    plan_memory_prefetch.py
    pr_gate_failure_shell.sh
    pr_publish_memory_write.py
    pre-tool-use-code-graph-gate.sh
    pre_tool_use_code_graph_gate.sh
    session_end_governance_backup.sh
    session_end_repo_hygiene.sh
    session_start_bootstrap.sh
    session_start_code_graph_health.sh
    session_start_memory_orchestrator.sh
    workspace_open_plugin_loader.py
  scripts/
    README.md
    agent_worktree_start.sh
    attribute_tree_writers.sh
    audit_corpus_reachability.py
    audit_rule_references.py
    audit_rules_corpus.py
    backup_gate.sh
    backup_to_github.sh
    bootstrap_agent_environment.sh
    build_claude_skill_registry.py
    capture_rules_cleanup_preflight.py
    check_governance_wiring.sh
    check_rules_standard.py
    check_skills_standard.py
    classify_generated_dirtiness.sh
    classify_hydrate_state.py
    claude_bootstrap_receipt.py
    claude_projection.py
    claude_projection_snapshot.py
    clean_pyc.sh
    compose_pr_body.py
    emit_claude_readiness.py
    ensure_git_merge_drivers.sh
    ensure_gov_python.sh
    ensure_uv_environment.sh
    ensure_workspace_wired.sh
    export_chats.sh
    generate_commands_manifest.py
    generate_rules_manifest.py
    git_merge_driver_generated.sh
    governance_activate_fresh.sh
    governance_refresh_receipt.py
    governance_sync.sh
    install_commit_hook.sh
    install_cursor_hooks_bootstrap.sh
    install_export_job.sh
    install_ide_profile.sh
    install_l9_dispatcher.sh
    inventory_cursor_extensions.py
    inventory_mcp_servers.py
    main_bound_check.py
    migrate_claude_orphan_skills.py
    normalize_rules_frontmatter.py
    open_pr_after_gate.sh
    operational-oversight.py
    parse_chat_exports.py
    pr_gate_failure.py
    pr_overlap_check.py
    pr_preflight.sh
    probe_network_posture.py
    process_context.sh
    process_learnings.sh
    project_llm_rules.py
    reconcile_claude_commands.py
    reconcile_claude_l9_skills.py
    reconcile_claude_settings.py
    reconcile_llm_rule_adapters.py
    reconcile_llm_skill_adapters.py
    regenerate_autonomy_policy_loader.py
    render_bootstrap_context.py
    repo_hygiene.py
    resolve_changed_files.sh
    resolve_governance_paths.sh
    resolve_stack_tip.py
    run_distiller.sh
    run_ff_post_shelf.sh
    run_improve.sh
    run_pr_gate.sh
    run_pr_precommit.sh
    run_pr_security.sh
    run_pytest_suites.sh
    run_python_test_suites.py
    run_rules_stabilization_validation.sh
    run_skill_self_tests.py
    run_workspace_clean.sh
    scan_launchagents.py
    scratch_hold.py
    select_pr_pytest_paths.py
    session_end_dirt_close.py
    session_init.sh
    session_start_runtime_report.py
    setup_claude_code_plugins.sh
    setup_workspace_symlinks.sh
    show_context.sh
    stack_pr.py
    sync_generated_artifacts.py
    sync_selected_rules.py
    tenx_status.sh
    tool_pattern_extractor.py
    transform_learning_to_episodes.py
    validate_autonomy_contracts.py
    validate_commands_manifest.py
    validate_commit_verification_contract.py
    validate_generated_allowlist.py
    validate_gh_package_deps.py
    validate_git_denial_residue.py
    validate_governance_contract_surface.py
    validate_governance_no_hardcoded_paths.sh
    validate_governance_symlinks.sh
    validate_legacy_doctrine_residue.py
    validate_max_velocity.py
    validate_memory_egress_boundary.py
    validate_org_policy.py
    validate_precommit_hook_contract.py
    validate_python_contract.py
    validate_root_file_protection.py
    validate_rules_manifest.py
    validate_workflow_action_pins.py
    verify-setup-alignment.sh
    verify_docker.sh
    verify_worktree_clean.py
    wip_corpus.py
    wire_governance_workspace.sh
    workspace_clean.py
    workspace_wire.py
    worktree_add_wired.sh
    write_pr_summary.py
    write_runtime_readiness_receipt.py
    adapters/
      README.md
      agentdocs.sh
      cursor.sh
    lib/
      README.md
      __init__.py
      bind_memory_interpreter.sh
      cursor_plans_store.sh
      dirtiness.py
      fetch_receipt.sh
      gh_auth_probe.sh
      gh_graphql.sh
      gh_subscribe_pr.sh
      path_contracts.sh
      precommit_log.sh
      repo_write_lock.sh
      resolve_pr_stack.sh
      retire_leftover_launchagents.sh
      rule_frontmatter.py
      rules_overlay.sh
      run_with_timeout.sh
      session_git_excludes.sh
      ssot_machine_local_keep.sh
      surface_detect.sh
      wave_prefix.py
      workspace_kind.sh
      workspace_roots.py
  lib/
    README.md
    safe_https.py
commands/
  COMMANDS_MANIFEST.yaml
  _harvest-copy-REVIEW.md
  clean.md
  commands-index.md
  end-session.md
  ff.md
  gmp.md
  governance-backup.md
  harvest.md
  index.md
  inspect.md
  issues.md
  l9-plan-build.md
  lcto.md
  migrate.md
  plan-audit.md
  pr-train.md
  pr.md
  refactor-sweep.md
  refactor.md
  spec.md
  start-session.md
  use-harvest.md
  dora-commands/
    do-README.md
    do-deploy.md
    do-end.md
    do-init.md
    do-metrics.md
    do-next.md
    do-status.md
  emma-repo-commands/
skills/
  AUTONOMY_MANIFEST.yaml
  l9-architecture-decision-records/
    README.md
    SKILL.md
    references/
  l9-prompt-engineering/
    README.md
    SKILL.md
  l9-context7-docs/
    README.md
    SKILL.md
  l9-mac-storage-triage/
    README.md
    SKILL.md
    bin/
    config/
    references/
    agents/
    steps/
    scripts/
      00-diagnose.sh
      01-summarize.sh
      02-initialize-env.sh
      03-validate-env.sh
      04-plan.sh
      05-apply.sh
      06-verify.sh
      07-inventory-noise.sh
      08-focus-layout.sh
      09-emit-findings.sh
      README.md
      emit-findings.py
      inspect-sparse-file.sh
      mode-run.sh
      scan-ncdu.sh
      actions/
        README.md
        delete-verified-source.sh
        docker-prune-unused.sh
        empty-trash.sh
        mail-cache-remove.sh
        offload-rclone.sh
        purge-stale-caches.sh
        spotlight-exclusions.sh
        spotlight-reindex-prepare.sh
      lib/
        README.md
        common.sh
    handoffs/
      current/
      examples/
  l9-forge/
    README.md
    SKILL.md
    references/
  l9-idea-execute/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      _common.py
      check_adapter_capability.py
      preflight_execution_pack.py
      route_execution.py
      self_test.py
      validate_adapter_snapshot.py
      validate_envelope.py
      validate_graph.py
      validate_receipt.py
    assets/
  l9-auditing-security/
    README.md
    SKILL.md
    references/
  l9-code-graph-rag-mcp/
    README.md
    SKILL.md
    scripts/
      README.md
      code_graph_batch_index.sh
      code_graph_cli.py
      code_graph_gmp_baseline.sh
      code_graph_health.sh
      code_graph_plasticos_gate.py
    assets/
  l9-plan/
    README.md
    SKILL.md
    references/
    agents/
    schemas/
    scripts/
      README.md
      emit_gmp_phase0.py
      paths.py
      render_plan_markdown.py
      render_plan_pe_autonomy.py
      route_plan.py
      self_test.py
      sync_cursor_plan_template.py
      validate_exemplary_skill.py
      validate_pack_structure.py
      validate_plan_document.py
      validate_plan_kernel_receipt.py
    fixtures/
    assets/
  l9-chat-extraction/
    README.md
    SKILL.md
    references/
  l9-intelligence-harvest/
    README.md
    SKILL.md
    references/
    contracts/
    meta/
    agents/
    policies/
    scripts/
      README.md
      _common.py
      bind_request.py
      inventory_source.py
      qualify_nuggets.py
      rank_nuggets.py
      render_brief.py
      self_test.py
      validate_harvest.py
  l9-auditing-performance/
    README.md
    SKILL.md
    references/
  l9-plan-simple/
    README.md
    SKILL.md
    references/
    agents/
    schemas/
    scripts/
      README.md
      generate_plan_section_receipt.py
      paths.py
      plan_sections.py
      self_test.py
      validate_plan_section_receipt.py
  l9-pipeline-audit/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      audit_pipeline.py
      audit_plans.py
      audit_plans_self_test.py
      harvest_plan_invariants.py
      run_intelligence_harvest.py
      self_test.py
  l9-setting-up-ci/
    README.md
    SKILL.md
  l9-gap-analysis/
    README.md
    SKILL.md
    references/
  l9-pe-campaign-activate/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      authorize_campaign_merge.py
      compile_activation_files.py
      compile_brief.py
      fixtures/
  l9-aws-secrets/
    README.md
    SKILL.md
    references/
    agents/
  l9-recursive-optimization/
    README.md
    SKILL.md
    references/
  l9-gmp-protocol/
    README.md
    SKILL.md
    references/
  l9-pipeline-orchestrator/
    README.md
    SKILL.md
    advance.py
    apply_branch_protection.py
    automerge_gate.py
    make_state.py
    verify_branch_protection.py
  l9-incident-response/
    README.md
    SKILL.md
    references/
  l9-skill-compiler/
    README.md
    SKILL.md
    references/
    policies/
    schemas/
    adapters/
    scripts/
      README.md
      _common.py
      package_skill.py
      scan_skill_topology.py
      validate_exemplary_skill.py
      validate_skill_pack.py
      validate_smart_exemplary_spec.py
  l9-claude-code-deepseek/
    README.md
    SKILL.md
  l9-end-session/
    README.md
    SKILL.md
    references/
  l9-monitoring-terminal-errors/
    README.md
    SKILL.md
  l9-repo-index/
    README.md
    SKILL.md
    references/
  l9-structured-reasoning/
    README.md
    SKILL.md
    references/
    agents/
    schemas/
    scripts/
      README.md
      compare_runs.py
      evaluate_confidence_cases.py
      evaluate_fixtures.py
      route_reasoning.py
      self_test.py
      validate_exemplary_skill.py
      validate_ledger.py
      validate_skill.py
    fixtures/
  l9-global-architect/
    README.md
    SKILL.md
    kernels/
    evals/
    contracts/
    runtime/
    agents/
    decisions/
    integrations/
    catalogs/
    bindings/
  l9-ui-operator/
    README.md
    SKILL.md
    references/
    playbooks/
  l9-pr-remediation/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      codeql_fetch.py
      debt_audit.py
      gate_receipt.py
      ingest_signals.py
      issue_handoff.py
      protocol.py
      reply_threads.py
      self_test.py
      semgrep_fetch.py
      sonar_fetch.py
      validate_plan.py
  l9-wire-into-repo/
    README.md
    SKILL.md
    references/
    scripts/
      README.md
      self_test.py
      validate_wiring_fixture.py
    fixtures/
  l9-setting-up-terraform/
    README.md
    SKILL.md
  l9-dag-authoring/
    README.md
    SKILL.md
    references/
    contracts/
    agents/
    policies/
    scripts/
      README.md
      classify_conversion_disposition.py
      classify_graph_kind.py
      convert_session_to_langgraph.py
      inspect_repo_surfaces.py
      probe_registration.py
      render_receipt.py
      self_test.py
      validate_command_trigger.py
      validate_langgraph_source.py
      validate_request.py
      validate_session_dag_source.py
    fixtures/
      README.md
      convert_langgraph_source.py
      convert_ok_session.py
      convert_prose_action.py
  l9-e2e-blocker-resolution/
    README.md
    SKILL.md
    references/
  l9-audit-plans/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      refine_plans.py
      run_audit_plans.py
      self_test.py
      shelf_plans.py
  l9-claude-coding-contract-compiler/
    README.md
    SKILL.md
    references/
    agents/
    schemas/
    examples/
    scripts/
      README.md
      compile_contract.py
      generate_claude_settings.py
      generate_preflight.py
      plan_decomposition.py
      validate_chain.py
      validate_contract.py
  l9-code-maintenance/
    README.md
    SKILL.md
    references/
    scripts/
      README.md
      code_maintenance.py
      refactor_sweep.py
      self_test.py
  l9-code-analysis/
    README.md
    SKILL.md
    references/
  l9-kubernetes-deploying/
    README.md
    SKILL.md
    references/
  l9-python-tdd-with-uv/
    README.md
    SKILL.md
  l9-governance-symlinks/
    README.md
    SKILL.md
  l9-api-smoke-testing/
    README.md
    SKILL.md
  l9-ci-ops/
    README.md
    SKILL.md
    references/
  l9-bounded-autonomy/
    README.md
    SKILL.md
    references/
  l9-issue-remediation/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      close_resolved_issue.py
      cluster_rank.py
      fleet_discover.py
      issue_ingest.py
      open_issues_gate.py
      post_issue_comment.py
      pr_landing.py
      self_test.py
  l9-graphiti-memory/
    README.md
    SKILL.md
  l9-component-verification/
    README.md
    SKILL.md
    references/
  l9-ynp/
    README.md
    SKILL.md
    references/
    scripts/
      README.md
      self_test.py
  l9-repository-renovation/
    README.md
    SKILL.md
    references/
    schemas/
    scripts/
      README.md
      api_surface.py
      audit_repository.py
      common.py
      compare_audits.py
      compile_contract.py
      render_pr_body.py
      run_validation_matrix.py
      self_test.py
      validate_contract.py
      validate_exemplary_skill.py
      validate_pr_pack.py
    assets/
  l9-git-work-preserve/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      diagnose_ref_value.py
      extract_path_union.py
      git_fetch.py
      harvest_worktree_dirt.py
      inventory_git_work.py
      pack_self_test.py
      prune_execute.py
      prune_open_pr_copies.py
      triage_preserved_refs.py
      validate_pack_structure.py
  l9-idea-foundry/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      _common.py
      emit_foundry_index.py
      emit_freeze_receipt.py
      inventory_idea_pack.py
      probe_birth_factory.py
      qualify_birth_handoff.py
      self_test.py
      validate_birth_qualification.py
      validate_foundry_payload.py
      validate_skill_contract.py
    assets/
  l9-cli-optimization/
    README.md
    SKILL.md
    references/
    docs/
    schemas/
    scripts/
      README.md
      build_commit_pack.py
      build_flag_activation_pack.py
      flag_inventory.py
      full_throttle.py
      measure.py
      route_optimize.py
      scan_capabilities.py
      self_test.py
      validate_activation_model.py
      validate_adaptive_reasoning.py
      validate_commit_pack.py
      validate_decision_ledger.py
      validate_exemplary_skill.py
      validate_identity_lock.py
      validate_latent_capability_integration.py
      validate_revision_synthesis.py
    assets/
  l9-pe-nuggets/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      extract_nuggets.py
  l9-pr-digest/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      pr_digest.py
      pr_digest_core.py
      pr_digest_render.py
      pr_evidence.py
      require_digest.py
      self_test.py
  l9-repo-sync/
    README.md
    SKILL.md
    references/
    agents/
    scripts/
      README.md
      ff.sh
      ff_shelf.py
      self_test.py
      validate_pack_structure.py
  l9-update-agent-docs/
    README.md
    SKILL.md
    references/
    contracts/
    scripts/
      README.md
      compile_semantic_obligations.py
      doc_change.py
      doc_filetree.py
      doc_llm.py
      doc_llms.py
      doc_obligations.py
      doc_owned_write.py
      doc_policy.py
      doc_surface_analysis.py
      generate_module_readmes.py
      repo_docs.py
      self_test.py
      validate_pointer_headings.py
      surface_analyzers/
        README.md
        __init__.py
        makefile.py
        pyproject.py
telemetry/
profiles/
  advanced-features.md
  dev_mode.md
  operational-health.md
  orchestrator.md
  reasoning_docs.md
  reasoning_l9.md
  reasoning_technical_operations.md
  security-access.md
  session-startup-protocol.md
  versioning.md
  workflow-governance.md
  ynp_mode.md
protocols/
  GMP VARIABLE PROMPT.v1.1.md
  GMP VARIABLE SPEC.v1.1 .md
  GMP-Action-Prompt-Canonical-v1.0.md
  GMP-Audit-Prompt-Canonical-v1.0.md
  GMP-System-Prompt-v1.0.md
reports/
  rules-cleanup-rename-map.yaml
```
