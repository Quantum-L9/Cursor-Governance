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
| `autonomy/adapters` | submodule | 8 | missing |
| `autonomy/adapters/claude_code` | submodule | 2 | missing |
| `autonomy/adapters/cursor` | submodule | 4 | missing |
| `autonomy/compiler` | submodule | 2 | missing |
| `autonomy/runtime` | submodule | 12 | missing |
| `autonomy/validation` | submodule | 5 | missing |
| `environment/agents` | module | 2 | present |
| `environment/agents/adapters/claude-code` | submodule | 6 | present |
| `environment/agents/adapters/claude-code/hooks` | submodule | 15 | missing |
| `environment/agents/adapters/claude-code/memory` | submodule | 3 | missing |
| `environment/agents/adapters/claude-code/web` | submodule | 2 | present |
| `environment/agents/adapters/claude-desktop` | submodule | 1 | present |
| `environment/agents/adapters/cursor` | submodule | 2 | present |
| `environment/agents/adapters/cursor/skills/l9-skill-gateway` | submodule | 0 | missing |
| `environment/agents/adapters/manus` | submodule | 12 | present |
| `environment/agents/cursor-subagents` | submodule | 1 | present |
| `environment/agents/deployment` | submodule | 4 | missing |
| `environment/agents/deployment/renderers` | submodule | 2 | missing |
| `environment/agents/generated-data/adapters` | submodule | 5 | missing |
| `environment/agents/generated-data/ingress` | submodule | 4 | missing |
| `environment/agents/generated-data/integration` | submodule | 2 | missing |
| `environment/agents/generated-data/invalidation` | submodule | 2 | missing |
| `environment/agents/generated-data/operations` | submodule | 5 | missing |
| `environment/agents/generated-data/orchestration` | submodule | 7 | missing |
| `environment/agents/generated-data/retrieval` | submodule | 4 | missing |
| `environment/agents/generated-data/runtime` | submodule | 7 | missing |
| `environment/agents/integration` | submodule | 1 | missing |
| `environment/agents/lifecycle` | submodule | 5 | missing |
| `environment/agents/readiness` | submodule | 3 | missing |
| `environment/agents/results` | submodule | 3 | missing |
| `environment/agents/results/adapters` | submodule | 2 | missing |
| `environment/agents/tools` | submodule | 3 | missing |
| `environment/program-execution` | module | 1 | present |
| `environment/program-execution/adapters` | submodule | 1 | missing |
| `environment/program-execution/adapters/chatgpt` | submodule | 3 | present |
| `environment/program-execution/adapters/ci/generic-shell` | submodule | 2 | present |
| `environment/program-execution/adapters/ci/github-actions` | submodule | 4 | present |
| `environment/program-execution/adapters/claude-code` | submodule | 4 | present |
| `environment/program-execution/adapters/codex` | submodule | 1 | present |
| `environment/program-execution/adapters/common` | submodule | 14 | missing |
| `environment/program-execution/adapters/cursor-background` | submodule | 1 | present |
| `environment/program-execution/adapters/cursor-foreground` | submodule | 1 | present |
| `environment/program-execution/adapters/deployment/target-specific` | submodule | 3 | present |
| `environment/program-execution/adapters/gemini` | submodule | 1 | present |
| `environment/program-execution/adapters/github` | submodule | 1 | missing |
| `environment/program-execution/adapters/github/checks` | submodule | 3 | present |
| `environment/program-execution/adapters/github/common` | submodule | 5 | missing |
| `environment/program-execution/adapters/github/deployments` | submodule | 3 | present |
| `environment/program-execution/adapters/github/remote-actions` | submodule | 4 | present |
| `environment/program-execution/adapters/manus` | submodule | 1 | present |
| `environment/program-execution/campaigns/l9-ecosystem-fix-plan/deliverables/ib-odoo_19/reference` | submodule | 2 | missing |
| `environment/program-execution/campaigns/pe-v3-hardening/blueprint/scripts` | submodule | 2 | missing |
| `environment/program-execution/campaigns/scripts` | submodule | 1 | missing |
| `environment/program-execution/compiler` | submodule | 19 | present |
| `environment/program-execution/conformance` | submodule | 2 | present |
| `environment/program-execution/core/program-execution-blueprint-template/scripts` | submodule | 2 | missing |
| `environment/program-execution/core/program-execution-controller-template/scripts` | submodule | 4 | missing |
| `environment/program-execution/core/program-execution-controller-template/scripts/pec` | submodule | 18 | missing |
| `environment/program-execution/core/scripts` | submodule | 5 | missing |
| `environment/program-execution/core/shared` | submodule | 1 | missing |
| `environment/program-execution/integrations` | submodule | 1 | missing |
| `environment/program-execution/integrations/agent-identity` | submodule | 2 | present |
| `environment/program-execution/integrations/autonomy-control-plane` | submodule | 4 | present |
| `environment/program-execution/integrations/bootstrap` | submodule | 4 | present |
| `environment/program-execution/integrations/cursor-task-tools` | submodule | 3 | present |
| `environment/program-execution/integrations/graphiti` | submodule | 1 | present |
| `environment/program-execution/integrations/subagent-generated-data` | submodule | 4 | present |
| `environment/program-execution/mission` | submodule | 2 | present |
| `environment/program-execution/peer_execution` | submodule | 27 | present |
| `environment/program-execution/peer_execution/autonomy` | submodule | 14 | present |
| `environment/program-execution/scripts` | submodule | 35 | missing |
| `intelligence/context-memory` | module | 1 | present |
| `intelligence/reasoning` | module | 1 | missing |
| `ops` | module | 1 | present |
| `ops/autonomy` | submodule | 27 | present |
| `ops/contracts` | submodule | 11 | missing |
| `ops/contracts/adapters` | submodule | 1 | missing |
| `ops/graphiti` | submodule | 2 | missing |
| `ops/graphiti/hydration` | submodule | 10 | missing |
| `ops/hooks` | submodule | 32 | present |
| `ops/lib` | submodule | 1 | missing |
| `ops/memory` | submodule | 24 | present |
| `ops/scripts` | submodule | 119 | present |
| `ops/scripts/adapters` | submodule | 2 | missing |
| `ops/scripts/lib` | submodule | 25 | present |
| `ops/secrets` | submodule | 20 | present |
| `ops/skill_routing` | submodule | 7 | missing |
| `ops/ui-operator` | submodule | 2 | present |
| `scripts` | module | 5 | missing |
| `skills/l9-api-smoke-testing` | module | 0 | missing |
| `skills/l9-architecture-decision-records` | module | 0 | missing |
| `skills/l9-audit-plans` | module | 0 | missing |
| `skills/l9-audit-plans/scripts` | submodule | 4 | missing |
| `skills/l9-auditing-performance` | module | 0 | missing |
| `skills/l9-auditing-security` | module | 0 | missing |
| `skills/l9-aws-secrets` | module | 0 | missing |
| `skills/l9-bounded-autonomy` | module | 0 | missing |
| `skills/l9-chat-extraction` | module | 0 | missing |
| `skills/l9-ci-ops` | module | 0 | missing |
| `skills/l9-claude-code-deepseek` | module | 0 | missing |
| `skills/l9-claude-coding-contract-compiler` | module | 0 | present |
| `skills/l9-claude-coding-contract-compiler/scripts` | submodule | 6 | missing |
| `skills/l9-cli-optimization` | module | 0 | present |
| `skills/l9-cli-optimization/scripts` | submodule | 16 | missing |
| `skills/l9-code-analysis` | module | 0 | missing |
| `skills/l9-code-graph-rag-mcp` | module | 0 | missing |
| `skills/l9-code-graph-rag-mcp/scripts` | submodule | 5 | missing |
| `skills/l9-code-maintenance` | module | 0 | missing |
| `skills/l9-code-maintenance/scripts` | submodule | 3 | missing |
| `skills/l9-component-verification` | module | 0 | missing |
| `skills/l9-context7-docs` | module | 0 | missing |
| `skills/l9-dag-authoring` | module | 0 | missing |
| `skills/l9-dag-authoring/fixtures` | submodule | 3 | missing |
| `skills/l9-dag-authoring/scripts` | submodule | 11 | missing |
| `skills/l9-e2e-blocker-resolution` | module | 0 | missing |
| `skills/l9-end-session` | module | 0 | missing |
| `skills/l9-forge` | module | 0 | missing |
| `skills/l9-gap-analysis` | module | 0 | missing |
| `skills/l9-git-work-preserve` | module | 0 | missing |
| `skills/l9-git-work-preserve/scripts` | submodule | 10 | missing |
| `skills/l9-global-architect` | module | 0 | missing |
| `skills/l9-global-architect/scripts` | submodule | 1 | missing |
| `skills/l9-gmp-protocol` | module | 0 | missing |
| `skills/l9-governance-symlinks` | module | 0 | missing |
| `skills/l9-graphiti-memory` | module | 0 | missing |
| `skills/l9-idea-execute` | module | 0 | missing |
| `skills/l9-idea-execute/scripts` | submodule | 9 | missing |
| `skills/l9-incident-response` | module | 0 | missing |
| `skills/l9-intelligence-harvest` | module | 0 | missing |
| `skills/l9-intelligence-harvest/scripts` | submodule | 8 | missing |
| `skills/l9-issue-remediation` | module | 0 | missing |
| `skills/l9-issue-remediation/scripts` | submodule | 8 | missing |
| `skills/l9-kubernetes-deploying` | module | 0 | missing |
| `skills/l9-mac-storage-triage` | module | 0 | present |
| `skills/l9-mac-storage-triage/scripts` | submodule | 14 | missing |
| `skills/l9-mac-storage-triage/scripts/actions` | submodule | 8 | missing |
| `skills/l9-mac-storage-triage/scripts/lib` | submodule | 1 | missing |
| `skills/l9-monitoring-terminal-errors` | module | 0 | missing |
| `skills/l9-pe-campaign-activate` | module | 0 | missing |
| `skills/l9-pe-campaign-activate/scripts` | submodule | 3 | missing |
| `skills/l9-pe-nuggets` | module | 0 | missing |
| `skills/l9-pe-nuggets/scripts` | submodule | 1 | missing |
| `skills/l9-pipeline-audit` | module | 0 | missing |
| `skills/l9-pipeline-audit/scripts` | submodule | 6 | missing |
| `skills/l9-pipeline-orchestrator` | module | 5 | present |
| `skills/l9-plan` | module | 0 | missing |
| `skills/l9-plan-simple` | module | 0 | missing |
| `skills/l9-plan-simple/scripts` | submodule | 5 | missing |
| `skills/l9-plan/scripts` | submodule | 11 | missing |
| `skills/l9-pr-audit` | module | 0 | missing |
| `skills/l9-pr-audit/scripts` | submodule | 5 | missing |
| `skills/l9-pr-digest` | module | 0 | missing |
| `skills/l9-pr-digest/scripts` | submodule | 6 | missing |
| `skills/l9-pr-remediation` | module | 0 | present |
| `skills/l9-pr-remediation/scripts` | submodule | 12 | present |
| `skills/l9-prompt-engineering` | module | 0 | missing |
| `skills/l9-python-tdd-with-uv` | module | 0 | missing |
| `skills/l9-recursive-optimization` | module | 0 | missing |
| `skills/l9-repo-birth` | module | 0 | missing |
| `skills/l9-repo-birth/scripts` | submodule | 2 | missing |
| `skills/l9-repo-index` | module | 0 | missing |
| `skills/l9-repo-sync` | module | 0 | missing |
| `skills/l9-repo-sync/scripts` | submodule | 4 | missing |
| `skills/l9-repository-renovation` | module | 0 | present |
| `skills/l9-repository-renovation/scripts` | submodule | 11 | missing |
| `skills/l9-setting-up-ci` | module | 0 | missing |
| `skills/l9-setting-up-terraform` | module | 0 | missing |
| `skills/l9-skill-compiler` | module | 0 | present |
| `skills/l9-skill-compiler/scripts` | submodule | 6 | missing |
| `skills/l9-structured-reasoning` | module | 0 | present |
| `skills/l9-structured-reasoning/scripts` | submodule | 8 | missing |
| `skills/l9-ui-operator` | module | 0 | missing |
| `skills/l9-update-agent-docs` | module | 0 | missing |
| `skills/l9-update-agent-docs/scripts` | submodule | 12 | missing |
| `skills/l9-update-agent-docs/scripts/surface_analyzers` | submodule | 3 | missing |
| `skills/l9-wire-into-repo` | module | 0 | missing |
| `skills/l9-wire-into-repo/scripts` | submodule | 2 | missing |
| `skills/l9-ynp` | module | 0 | missing |
| `skills/l9-ynp/scripts` | submodule | 1 | missing |
| `tools` | module | 1 | missing |
| `tools/l9_agent_ui_control` | submodule | 15 | present |
| `tools/l9_agent_ui_control/helpers` | submodule | 2 | missing |
| `workflows` | module | 11 | present |
| `workflows/dags` | submodule | 13 | missing |
| `workflows/dags/_runtime` | submodule | 2 | missing |
| `workflows/dags/gmp` | submodule | 5 | missing |
| `workflows/dags/gmp/nodes` | submodule | 2 | missing |
| `workflows/dags/intelligence_harvest` | submodule | 6 | missing |
| `workflows/nodes` | submodule | 7 | missing |
| `workflows/session` | submodule | 3 | missing |

## Tree

```
.
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
  adapters/
    __init__.py
    bridge.py
    conformance.py
    contract_renderer.py
    heartbeat_hook.py
    orchestrator.py
    protocol.py
    tool_hook.py
    claude_code/
      __init__.py
      adapter.py
    cursor/
      __init__.py
      adapter.py
      host_bridge.py
      mint_admission.py
  compiler/
    __init__.py
    graph_compiler.py
  examples/
    adapters/
  policies/
  runtime/
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
  schemas/
  validation/
    __init__.py
    doctor.py
    golden_trace.py
    graph_linter.py
    simulator.py
commands/
  emma-repo-commands/
config/
  subsystems/
contracts/
  schemas/
environment/
  agents/
    README.md
    runtime_paths.py
    runtime_paths_test.py
    adapters/
      claude-code/
        README.md
        install.sh
        overlay_hosted_settings_env.py
        validate_claude_env.py
        validate_memory_enforcement.py
        validate_skill_activation.py
        verify_account_env.py
        adapters/
        baseline/
        bin/
        generated/
        hooks/
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
        memory/
          errors.py
          memory_bridge.py
          memory_state.py
        web/
          README.md
          setup.bootstrap.sh
          setup.sh
      claude-desktop/
        README.md
        render_claude_desktop_config.py
      codex/
      cursor/
        README.md
        install.sh
        validate_skill_projection.py
        skills/
          l9-skill-gateway/
            SKILL.md
      gemini/
      generic/
      manus/
        README.md
        infisical_mcp_server.py
        install.sh
        materialize_memory_authority.py
        mcp_server.py
        memory_lifecycle.py
        render_infisical_mcp_connector.py
        render_mcp_connector.py
        render_memory_mcp_connector.py
        serve_infisical_mcp.sh
        serve_mcp.sh
        serve_memory_mcp.sh
        validate_manus_adapter.py
    cursor-subagents/
      README.md
      result_bridge.py
      schemas/
    deployment/
      __init__.py
      receipts.py
      reconcile.py
      validate.py
      renderers/
        __init__.py
        cursor.py
    docs/
    generated-data/
      adapters/
        __init__.py
        graphiti_memory.py
        ingest_memory_candidate.py
        l9_python.py
        odoo.py
      config/
      ingress/
        __init__.py
        ingest.py
        receipts.py
        security_gate.py
      integration/
        __init__.py
        end_to_end_golden.py
      invalidation/
        __init__.py
        repository_event_bridge.py
      law/
      operations/
        __init__.py
        dead_letter.py
        health.py
        replay.py
        status.py
      orchestration/
        __init__.py
        delivery_worker.py
        module_loader.py
        processor.py
        receipts.py
        retry_policy.py
        state_store.py
      retrieval/
        __init__.py
        context_query.py
        context_selector.py
        reuse_recorder.py
      roles/
      routes/
      runtime/
        __init__.py
        classifier.py
        harvester.py
        learning_closure.py
        packet_validator.py
        promotion_gate.py
        routing_engine.py
      schemas/
    integration/
      __init__.py
    lifecycle/
      __init__.py
      compose_start.py
      compose_stop.py
      receipts.py
      schemas.py
    readiness/
      __init__.py
      compose.py
      probe_runtime.py
    results/
      __init__.py
      gateway.py
      receipts.py
      adapters/
        __init__.py
        cursor_subagent.py
      schemas/
    schemas/
    tools/
      render_principals.py
      validate_agents.py
      validate_executable_peers.py
  contracts/
    autonomy/
      meta/
    execution/
      adr/
      templates/
  ide/
  mcp/
  plugins/
  program-execution/
    README.md
    program_policy.py
    adapters/
      __init__.py
      chatgpt/
        README.md
        artifact_collector.py
        envelope_renderer.py
        provider.py
      ci/
        generic-shell/
          README.md
          evidence_collector.py
          provider.py
        github-actions/
          README.md
          artifact_collector.py
          dispatcher.py
          monitor.py
          provider.py
      claude-code/
        README.md
        excerpts.py
        permission_renderer.py
        provider.py
        stream_parser.py
      codex/
        README.md
        provider.py
      common/
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
      cursor-background/
        README.md
        provider.py
      cursor-foreground/
        README.md
        provider.py
      deployment/
        target-specific/
          README.md
          generate_target_adapter.py
          provider.py
          validate_target_adapter.py
      gemini/
        README.md
        provider.py
      github/
        __init__.py
        checks/
          README.md
          check_publisher.py
          provider.py
          status_reader.py
        common/
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
        remote-actions/
          README.md
          branch.py
          provider.py
          pull_request.py
          push.py
      manus/
        README.md
        provider.py
    archive/
      campaign-input-v1/
        CG-PES-RUN2-HARDENING/
        session-runtime-hydration-convergence-v1/
    audits/
    campaigns/
      COMPLETED/
        level3-make-pr-single-path/
          handoff/
      adr-identity-integrity-v1/
      bounded-replanning-v1/
        handoff/
      cc-pe-intent-compiler-v1/
        deliverables/
          l9-devpack-compiler/
        handoff/
      eie-inference-isolation-v1/
      l9-devpack-program-execution-hardening/
        deliverables/
          l9-devpack-compiler/
        handoff/
      l9-ecosystem-fix-plan/
        deliverables/
          ib-odoo_19/
            reference/
              plasticos_ceg_match_mapper.py
              plasticos_eie_converge_mapper.py
        handoff/
        history/
          v1.0.0/
      pe-router-capability-safety-v4/
      pe-v3-hardening/
        audits/
        baseline/
        blueprint/
          schemas/
          scripts/
            instantiate.py
            validate_blueprint.py
      scripts/
        close_campaign.py
      session-runtime-hydration-convergence-v2/
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
      fixtures/
      policies/
      schemas/
    conformance/
      README.md
      __init__.py
      helpers.py
      counterexamples/
      fixtures/
        hostile/
        negative/
        positive/
      schemas/
    core/
      program-execution-blueprint-template/
        schemas/
        scripts/
          instantiate.py
          validate_blueprint.py
      program-execution-controller-template/
        policy/
        receipts/
        references/
        schemas/
        scripts/
          instantiate.py
          pec.py
          run_negative_tests.py
          validate_controller.py
          pec/
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
      scripts/
        generate_manifest.py
        instantiate_pair.py
        run_negative_tests.py
        validate_pair.py
        validate_replan.py
      shared/
        blueprint_identity.py
        schemas/
      validation/
    environment/
      program-execution/
        campaigns/
          pe-v3-hardening/
            integrity/
    integrations/
      __init__.py
      agent-identity/
        README.md
        identity_binding.py
        registry_reader.py
      autonomy-control-plane/
        README.md
        bridge.py
        contract_mapper.py
        grant.py
        program_authority.py
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
      graphiti/
        README.md
        context_reader.py
      subagent-generated-data/
        README.md
        campaign_summary.py
        compile_units.py
        outcome_publisher.py
        receipt_projection.py
    mission/
      README.md
      binding.py
      mission.py
      schemas/
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
    registry/
    scripts/
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
    templates/
      campaign-source-v2/
    validation/
      history/
  skill-adapters/
execution-governance/
foundation/
  security/
generated/
  governance/
governance/
intelligence/
  context-memory/
    README.md
    show_context_graphiti.py
    sessions/
  meta-learning/
  models/
  reasoning/
    reasoning-snapshot-generator.py
  standards/
  workspace/
kernels/
  L9 Coding Control Plane/
    ai-control-plane/
    docs/
learning/
  failures/
    incidents/
  graphiti-episodes/
  patterns/
  solutions/
ops/
  README.md
  __init__.py
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
    memory_lane_exemption.py
    merge_gate.py
    open_pr_probe.py
    pr_board.py
    pr_fleet.py
    profile_loader.py
    receipt_binding.py
    resolve_execution_gate.py
    root_file_advisory.py
    session_debt.py
    stack_safe_merge.py
    surface_detect.py
    verification_bypass_gate.py
    worktree_isolation_gate.py
  config/
  contracts/
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
      cursor_rules.py
  graphiti/
    __init__.py
    graphiti_gate_lib.py
    docs/
    hydration/
      __init__.py
      archive_transcript.py
      cli.py
      close_session.py
      compile_session_packet.py
      identity.py
      pickup_write.py
      redaction.py
      session_latches.py
      transcript.py
    memory-bank-template/
  hooks/
    README.md
    before-shell-execution-gate.sh
    before_mcp_code_graph_gate.sh
    before_shell_execution_gate.py
    before_submit_skill_router.py
    child_conversation.py
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
    session_authored_paths.py
    session_end_governance_backup.sh
    session_end_repo_hygiene.sh
    session_start_bootstrap.sh
    session_start_code_graph_health.sh
    session_start_memory_orchestrator.sh
    workspace_open_plugin_loader.py
  lib/
    safe_https.py
  memory/
    README.md
    __init__.py
    agent_assertion.py
    agent_lane.py
    canonical_validation.py
    cli.py
    control_plane_client.py
    diagnostics.py
    environment_heal.py
    export_agent_assertion_env.sh
    hook_envelope.py
    hydration.py
    legacy_reconciliation.py
    mcp_instantiation.py
    namespace_context.py
    print_agent_assertion_env.py
    receipt_contract.py
    receipts.py
    run_memory_mcp.sh
    runtime_binding.py
    seal_artifact_provenance.py
    search_identity.py
    session_contracts.py
    session_state.py
    store_compat.py
  schemas/
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
    relocate_plugin_siblings.sh
    render_bootstrap_context.py
    repo_hygiene.py
    resolve_changed_files.sh
    resolve_governance_paths.sh
    resolve_stack_tip.py
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
    session_authored_ledger.py
    session_end_dirt_close.py
    session_end_preserve.py
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
      git_remote_head.sh
      path_contracts.sh
      plugin_siblings.sh
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
      workspace_link_health.sh
      workspace_roots.py
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
  skill_routing/
    __init__.py
    materialize.py
    receipt.py
    registry.py
    resolve.py
    route_prompt.py
    session_locator.py
  ui-operator/
    README.md
    console.py
    jit_drafter.py
    cartridges/
    drafts/
    receipts/
    schemas/
  vendor/
    wheels/
  make/
pipeline/
profiles/
prompts/
protocols/
releases/
reports/
rules/
schemas/
scripts/
  __init__.py
  claude-deepseek.sh
  generate_subsystem_readmes.py
  preflight.sh
  verify-routing.sh
security/
skills/
  l9-api-smoke-testing/
    SKILL.md
  l9-architecture-decision-records/
    SKILL.md
    references/
  l9-audit-plans/
    SKILL.md
    agents/
    references/
    scripts/
      refine_plans.py
      run_audit_plans.py
      self_test.py
      shelf_plans.py
  l9-auditing-performance/
    SKILL.md
    references/
  l9-auditing-security/
    SKILL.md
    references/
  l9-aws-secrets/
    SKILL.md
    agents/
    references/
  l9-bounded-autonomy/
    SKILL.md
    references/
  l9-chat-extraction/
    SKILL.md
    references/
  l9-ci-ops/
    SKILL.md
    references/
  l9-claude-code-deepseek/
    SKILL.md
  l9-claude-coding-contract-compiler/
    README.md
    SKILL.md
    agents/
    examples/
    references/
    schemas/
    scripts/
      compile_contract.py
      generate_claude_settings.py
      generate_preflight.py
      plan_decomposition.py
      validate_chain.py
      validate_contract.py
  l9-cli-optimization/
    README.md
    SKILL.md
    assets/
    docs/
    references/
    schemas/
    scripts/
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
  l9-code-analysis/
    SKILL.md
    references/
  l9-code-graph-rag-mcp/
    SKILL.md
    assets/
    scripts/
      code_graph_batch_index.sh
      code_graph_cli.py
      code_graph_gmp_baseline.sh
      code_graph_health.sh
      code_graph_plasticos_gate.py
  l9-code-maintenance/
    SKILL.md
    references/
    scripts/
      code_maintenance.py
      refactor_sweep.py
      self_test.py
  l9-component-verification/
    SKILL.md
    references/
  l9-context7-docs/
    SKILL.md
  l9-dag-authoring/
    SKILL.md
    agents/
    contracts/
    fixtures/
      convert_langgraph_source.py
      convert_ok_session.py
      convert_prose_action.py
    policies/
    references/
    scripts/
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
  l9-e2e-blocker-resolution/
    SKILL.md
    references/
  l9-end-session/
    SKILL.md
    references/
  l9-forge/
    SKILL.md
    references/
  l9-gap-analysis/
    SKILL.md
    references/
  l9-git-work-preserve/
    SKILL.md
    agents/
    references/
    scripts/
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
  l9-global-architect/
    SKILL.md
    agents/
    bindings/
    catalogs/
    contracts/
    decisions/
    evals/
    fixtures/
    integrations/
    kernels/
    runtime/
    schemas/
    scripts/
      validate_product_architecture_decision.py
  l9-gmp-protocol/
    SKILL.md
    references/
  l9-governance-symlinks/
    SKILL.md
  l9-graphiti-memory/
    SKILL.md
  l9-idea-execute/
    SKILL.md
    agents/
    assets/
    references/
    scripts/
      _common.py
      check_adapter_capability.py
      preflight_execution_pack.py
      route_execution.py
      self_test.py
      validate_adapter_snapshot.py
      validate_envelope.py
      validate_graph.py
      validate_receipt.py
  l9-incident-response/
    SKILL.md
    references/
  l9-intelligence-harvest/
    SKILL.md
    agents/
    contracts/
    meta/
    policies/
    references/
    scripts/
      _common.py
      bind_request.py
      inventory_source.py
      qualify_nuggets.py
      rank_nuggets.py
      render_brief.py
      self_test.py
      validate_harvest.py
  l9-issue-remediation/
    SKILL.md
    agents/
    references/
    scripts/
      close_resolved_issue.py
      cluster_rank.py
      fleet_discover.py
      issue_ingest.py
      open_issues_gate.py
      post_issue_comment.py
      pr_landing.py
      self_test.py
  l9-kubernetes-deploying/
    SKILL.md
    references/
  l9-mac-storage-triage/
    README.md
    SKILL.md
    agents/
    bin/
    config/
    handoffs/
      current/
      examples/
    references/
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
      emit-findings.py
      inspect-sparse-file.sh
      mode-run.sh
      scan-ncdu.sh
      actions/
        delete-verified-source.sh
        docker-prune-unused.sh
        empty-trash.sh
        mail-cache-remove.sh
        offload-rclone.sh
        purge-stale-caches.sh
        spotlight-exclusions.sh
        spotlight-reindex-prepare.sh
      lib/
        common.sh
    steps/
  l9-monitoring-terminal-errors/
    SKILL.md
  l9-pe-campaign-activate/
    SKILL.md
    agents/
    references/
    scripts/
      authorize_campaign_merge.py
      compile_activation_files.py
      compile_brief.py
      fixtures/
  l9-pe-nuggets/
    SKILL.md
    agents/
    references/
    scripts/
      extract_nuggets.py
  l9-pipeline-audit/
    SKILL.md
    agents/
    references/
    scripts/
      audit_pipeline.py
      audit_plans.py
      audit_plans_self_test.py
      harvest_plan_invariants.py
      run_intelligence_harvest.py
      self_test.py
  l9-pipeline-orchestrator/
    README.md
    SKILL.md
    advance.py
    apply_branch_protection.py
    automerge_gate.py
    make_state.py
    verify_branch_protection.py
  l9-plan-simple/
    SKILL.md
    agents/
    references/
    schemas/
    scripts/
      generate_plan_section_receipt.py
      paths.py
      plan_sections.py
      self_test.py
      validate_plan_section_receipt.py
    fixtures/
  l9-plan/
    SKILL.md
    agents/
    assets/
    fixtures/
    references/
    schemas/
    scripts/
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
  l9-pr-audit/
    SKILL.md
    adapters/
    agents/
    assets/
    references/
    schemas/
    scripts/
      build_audit_bundle.py
      build_change_ledger.py
      deterministic_closure.py
      execute_mutation_probe.py
      self_test.py
  l9-pr-digest/
    SKILL.md
    agents/
    references/
    scripts/
      pr_digest.py
      pr_digest_core.py
      pr_digest_render.py
      pr_evidence.py
      require_digest.py
      self_test.py
  l9-pr-remediation/
    README.md
    SKILL.md
    agents/
    references/
    scripts/
      README.md
      codeql_fetch.py
      debt_audit.py
      gate_receipt.py
      ingest_signals.py
      issue_handoff.py
      protocol.py
      reply_threads.py
      require_audit.py
      self_test.py
      semgrep_fetch.py
      sonar_fetch.py
      validate_plan.py
  l9-prompt-engineering/
    SKILL.md
  l9-python-tdd-with-uv/
    SKILL.md
  l9-recursive-optimization/
    SKILL.md
    references/
  l9-repo-birth/
    SKILL.md
    schemas/
    scripts/
      package_birth_handoff.py
      self_test.py
  l9-repo-index/
    SKILL.md
    references/
  l9-repo-sync/
    SKILL.md
    agents/
    references/
    scripts/
      ff.sh
      ff_shelf.py
      self_test.py
      validate_pack_structure.py
  l9-repository-renovation/
    README.md
    SKILL.md
    assets/
    references/
    schemas/
    scripts/
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
  l9-setting-up-ci/
    SKILL.md
  l9-setting-up-terraform/
    SKILL.md
  l9-skill-compiler/
    README.md
    SKILL.md
    adapters/
    policies/
    references/
    schemas/
    scripts/
      _common.py
      package_skill.py
      scan_skill_topology.py
      validate_exemplary_skill.py
      validate_skill_pack.py
      validate_smart_exemplary_spec.py
  l9-structured-reasoning/
    README.md
    SKILL.md
    agents/
    fixtures/
    references/
    schemas/
    scripts/
      compare_runs.py
      evaluate_confidence_cases.py
      evaluate_fixtures.py
      route_reasoning.py
      self_test.py
      validate_exemplary_skill.py
      validate_ledger.py
      validate_skill.py
  l9-ui-operator/
    SKILL.md
    playbooks/
    references/
  l9-update-agent-docs/
    SKILL.md
    contracts/
    references/
    scripts/
      compile_semantic_obligations.py
      doc_change.py
      doc_filetree.py
      doc_llm.py
      doc_obligations.py
      doc_owned_write.py
      doc_policy.py
      doc_surface_analysis.py
      generate_module_readmes.py
      repo_docs.py
      self_test.py
      validate_pointer_headings.py
      surface_analyzers/
        __init__.py
        makefile.py
        pyproject.py
  l9-wire-into-repo/
    SKILL.md
    fixtures/
    references/
    scripts/
      self_test.py
      validate_wiring_fixture.py
  l9-ynp/
    SKILL.md
    references/
    scripts/
      self_test.py
telemetry/
tools/
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
      __init__.py
      logging.py
    sql/
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
  Dags-Harvest/
  dags/
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
    _runtime/
      __init__.py
      durable_checkpointer.py
    gmp/
      __init__.py
      executor.py
      graph.py
      routing.py
      state.py
      nodes/
        __init__.py
        core.py
    intelligence_harvest/
      __init__.py
      executor.py
      graph.py
      nodes.py
      routing.py
      state.py
  defs/
  nodes/
    __init__.py
    checkpoint.py
    deploy.py
    extract.py
    inject.py
    report.py
    validate.py
  session/
    __init__.py
    interface.py
    registry.py
```
