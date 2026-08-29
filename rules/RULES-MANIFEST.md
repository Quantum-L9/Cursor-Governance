# Cursor governance rules manifest

Generated: `2026-08-29T00:29:49Z`. Source: `rules/*.mdc`.

## Counts

| Bucket | Count |
|---|---:|
| Total MDC files | **68** |
| `alwaysApply: true` | **32** |
| `alwaysApply: false` | **36** |
| No boolean `alwaysApply` | **0** |
| Explicit stable IDs | **68** |
| Derived compatibility IDs | **0** |
| Deprecated rules | **0** |

## Rule index

| File | ID | Scope | Domain | Activation | Lines | Digest |
|---|---|---|---|---|---:|---|
| `00-global.mdc` | `l9.rule.00.global` | global | governance | always | 36 | `ceaafbc51009` |
| `02-slash-commands.mdc` | `l9.rule.slash-commands` | global | governance | always | 161 | `9b2cf950134c` |
| `03-graphiti-memory.mdc` | `l9.rule.graphiti.memory` | global | memory | always | 68 | `d3fca17315f9` |
| `04-cursor-redis-session.mdc` | `l9.rule.04.cursor.redis.session` | global | memory | agent_requested | 70 | `64a0e957121b` |
| `05-ask-mode.mdc` | `l9.rule.05.ask.mode` | global | governance | always | 65 | `4b2f5f472100` |
| `06-governance-ssot-paths.mdc` | `l9.rule.governance-ssot-paths` | global | git | always | 56 | `a8c0978cff70` |
| `08-vps-ops.mdc` | `l9.rule.08.vps.ops` | global | git | agent_requested | 192 | `8ca195f6994d` |
| `09-execute-as-instructed.mdc` | `l9.rule.09.execute.as.instructed` | global | general | always | 48 | `13d3fb355837` |
| `10-lang-typescript.mdc` | `l9.rule.10.lang.typescript` | global | typescript | agent_requested | 182 | `bb98eadfc112` |
| `15-work-tracking.mdc` | `l9.rule.15.work.tracking` | global | general | agent_requested | 38 | `79c9306f7061` |
| `20-lang-python.mdc` | `l9.rule.20.lang.python` | global | python | agent_requested | 190 | `fa976f39b458` |
| `22-context7-auto-invoke.mdc` | `l9.rule.22.context7.auto.invoke` | global | git | always | 65 | `d683a886480c` |
| `23-l9-skill-routing.mdc` | `l9.rule.skill-routing` | global | governance | always | 100 | `9e2ab29ad5ce` |
| `25-python-dora-header.mdc` | `l9.rule.25.python.dora.header` | global | python | auto_attached | 173 | `49302e69c080` |
| `30-framework-react.mdc` | `l9.rule.30.framework.react` | global | typescript | agent_requested | 145 | `935829c0a8d1` |
| `40-domain-autonomy.mdc` | `l9.rule.40.domain.autonomy` | global | security | agent_requested | 182 | `fbbfa0dc8cc4` |
| `41-graph-engine-architecture.mdc` | `l9.rule.41.graph.engine.architecture` | global | security | agent_requested | 104 | `db87e22cdb8a` |
| `42-no-abandoned-work.mdc` | `l9.rule.42.no.abandoned.work` | global | git | always | 83 | `0faf271f6403` |
| `43-lang-postgresql.mdc` | `l9.rule.43.lang.postgresql` | global | security | agent_requested | 54 | `3a3ff21bfdec` |
| `44-recursive-execution-kernel.mdc` | `l9.rule.recursive-execution-kernel` | global | execution | agent_requested | 39 | `4c064ea19ce3` |
| `45-pre-action-verification.mdc` | `l9.rule.pre-action-verification` | global | general | always | 87 | `2d4e738329b0` |
| `46-kernel-pack-new-branch.mdc` | `l9.rule.46.kernel.pack.new.branch` | global | general | agent_requested | 36 | `76c8cba8c93a` |
| `47-agent-pattern-activation.mdc` | `l9.rule.47.agent.pattern.activation` | global | memory | agent_requested | 116 | `058301b4286b` |
| `48-make-pr-remediation.mdc` | `l9.rule.48.make.pr.remediation` | global | general | always | 125 | `72302848d33a` |
| `49-shared-worktree-isolation.mdc` | `l9.rule.49.shared.worktree.isolation` | global | git | always | 85 | `9f0288253b25` |
| `50-qa-testing.mdc` | `l9.rule.50.qa.testing` | global | testing | auto_attached | 207 | `4e739913c198` |
| `51-qa-playwright.mdc` | `l9.rule.51.qa.playwright` | global | testing | agent_requested | 34 | `ea8a218a6725` |
| `52-qa-jest.mdc` | `l9.rule.52.qa.jest` | global | testing | agent_requested | 35 | `38f6e2e26683` |
| `53-pr-overlap-guardrail.mdc` | `l9.rule.53.pr.overlap.guardrail` | global | git | always | 112 | `043137b8e8a5` |
| `54-context-sensitive-git-guardrails.mdc` | `l9.rule.54.git.guardrails` | global | git | always | 78 | `22327366534e` |
| `55-ff-only-ssot-sync.mdc` | `l9.rule.55.ff.only.ssot.sync` | global | git | always | 57 | `4ef14331a2f4` |
| `59-incident-lessons.mdc` | `l9.rule.incident.lessons` | global | deployment | agent_requested | 22 | `3fb8e334a6b1` |
| `60-anti-patterns.mdc` | `l9.rule.anti.patterns` | global | testing | always | 27 | `664ff6afbb7f` |
| `61-secrets-and-dependencies.mdc` | `l9.rule.61.secrets.and.dependencies` | global | security | agent_requested | 50 | `d90a13c2549a` |
| `62-github-openclaw-authority.mdc` | `l9.rule.62.github.openclaw.authority` | global | git | always | 23 | `9b4abefa8ef4` |
| `63-env-no-hardcode.mdc` | `l9.rule.configuration.no-hardcode` | global | general | auto_attached | 42 | `369e0ab6d90f` |
| `65-observability-performance.mdc` | `l9.rule.65.observability.performance` | global | memory | agent_requested | 43 | `888c5c4b9057` |
| `69-ide-profile-exceptions.mdc` | `l9.rule.ide-profile-exceptions` | global | general | agent_requested | 49 | `2bc076e7c46c` |
| `70-tool-efficiency.mdc` | `l9.rule.70.tool.efficiency` | global | governance | agent_requested | 190 | `80a4344c4649` |
| `71-ci-cd-pipeline.mdc` | `l9.rule.71.ci.cd.pipeline` | global | ci | agent_requested | 39 | `760adb0709d8` |
| `72-review-ergonomics.mdc` | `l9.rule.72.review.ergonomics` | global | output | agent_requested | 168 | `64a18349f4bf` |
| `73-prompts-and-evals.mdc` | `l9.rule.73.prompts.and.evals` | global | general | agent_requested | 37 | `e9cb31a41b5a` |
| `74-ai-safety-policy.mdc` | `l9.rule.74.ai.safety.policy` | global | security | agent_requested | 44 | `30dafdd1c06c` |
| `75-bounded-session-autonomy.mdc` | `l9.rule.75.bounded.session.autonomy` | global | execution | agent_requested | 25 | `0127f988d59b` |
| `76-wire-workflow-guard.mdc` | `l9.rule.76.wire.workflow.guard` | global | governance | auto_attached | 55 | `f94087db811a` |
| `77-cursor-subagent-orchestration.mdc` | `l9.rule.77.cursor.subagent.orchestration` | global | governance | agent_requested | 24 | `67cc9f7af1be` |
| `78-perplexity-run-harness.mdc` | `l9.rule.78.perplexity.run.harness` | global | general | agent_requested | 62 | `ff0c6fe1e02f` |
| `79-output-discipline.mdc` | `l9.rule.output-discipline` | global | output | agent_requested | 26 | `ea8f58ae1f55` |
| `80-gmp-execution.mdc` | `l9.rule.80.gmp.execution` | global | ci | always | 71 | `14a64f58c0e8` |
| `81-gmp-audit.mdc` | `l9.rule.81.gmp.audit` | global | governance | agent_requested | 96 | `0a3985c2fdc4` |
| `82-deployment-manifest.mdc` | `l9.rule.82.deployment.manifest` | global | deployment | agent_requested | 72 | `b57f632b093e` |
| `83-gmp-contracts.mdc` | `l9.rule.83.gmp.contracts` | global | governance | always | 135 | `f9c358d00e0e` |
| `84-cursor-governance-wiring.mdc` | `l9.rule.cursor-governance-wiring` | global | governance | always | 73 | `7121eb2a6c46` |
| `85-workflow-state-bridge.mdc` | `l9.rule.85.workflow.state.bridge` | global | memory | agent_requested | 91 | `3e623c8e396d` |
| `86-module-tier-mapping.mdc` | `l9.rule.86.module.tier.mapping` | global | governance | agent_requested | 58 | `7a05740e99d2` |
| `87-cursor-memory-kernel.mdc` | `l9.rule.cursor.memory.kernel` | global | memory | always | 166 | `a27cb6825319` |
| `88-l4-local-autonomy.mdc` | `l9.rule.l4.local-autonomy` | global | git | always | 69 | `88a6bc6c681c` |
| `89-constellation-gate-workspace-session.mdc` | `l9.rule.89.constellation.gate.workspace.session` | global | governance | agent_requested | 40 | `3b1b5e0cfd03` |
| `90-protected-core.mdc` | `l9.rule.90.protected.core` | global | governance | always | 106 | `0e67f1cc2c17` |
| `91-existing-code-source-of-truth.mdc` | `l9.rule.91.existing.code.source.of.truth` | global | general | always | 70 | `5043e3374dca` |
| `92-learned-lessons.mdc` | `l9.rule.learned.lessons` | global | general | always | 30 | `a90cefaa4b6d` |
| `93-c1-server-protection.mdc` | `l9.rule.93.c1.server.protection` | global | git | always | 88 | `a89e589b42cb` |
| `94-deployment-prohibition.mdc` | `l9.rule.94.deployment.prohibition` | global | deployment | always | 23 | `95043be2ba11` |
| `95-test-fix-policy.mdc` | `l9.rule.testing.integrity` | global | testing | always | 57 | `cbf9a0e89a3d` |
| `96-multi-agent-main-bound-execution.mdc` | `l9.rule.96.multi.agent.main.bound.execution` | global | git | always | 129 | `4c3da47effd7` |
| `97-graph-layer-boundary.mdc` | `l9.rule.graph-layer-boundary` | global | memory | always | 37 | `381364ee74a4` |
| `98-graphiti-memory-gate.mdc` | `l9.rule.graphiti.memory.gate` | global | memory | always | 48 | `557a495cb0ca` |
| `99-no-auto-commit.mdc` | `l9.rule.git.mutation-gate` | global | git | always | 62 | `f40fb8497a18` |

## Notes

- IDs marked as derived are compatibility identities. Add explicit immutable `id` metadata when a rule is materially edited.
- The JSON and YAML files are generated from the same in-memory model as this document.
- Never edit manifest counters by hand.
