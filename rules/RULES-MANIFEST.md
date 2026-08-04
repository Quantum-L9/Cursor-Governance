# Cursor governance rules manifest

Generated: `2026-08-04T03:37:31Z`. Source: `rules/*.mdc`.

## Counts

| Bucket | Count |
|---|---:|
| Total MDC files | **60** |
| `alwaysApply: true` | **39** |
| `alwaysApply: false` | **21** |
| No boolean `alwaysApply` | **0** |
| Explicit stable IDs | **8** |
| Derived compatibility IDs | **52** |
| Deprecated rules | **1** |

## Rule index

| File | ID | Scope | Domain | Activation | Lines | Digest |
|---|---|---|---|---|---:|---|
| `00-global.mdc` | `l9.rule.00.global` | global | security | always | 279 | `617dac45e91d` |
| `01-git-push-prohibition.mdc` | `l9.rule.01.git.push.prohibition` | global | git | always | 73 | `634b7fa04d1a` |
| `01-vps-rules.mdc` | `l9.rule.01.vps.rules` | global | git | always | 185 | `b746e103e439` |
| `02-slash-commands.mdc` | `l9.rule.02.slash.commands` | global | governance | always | 153 | `a976f968cd15` |
| `03-graphiti-memory.mdc` | `l9.rule.03.graphiti.memory` | global | memory | always | 44 | `f05a463d9f4d` |
| `03-mcp-memory.mdc` | `l9.rule.03.mcp.memory` | global | deployment | auto_attached | 419 | `aa99208c2fcb` |
| `04-cursor-redis-session.mdc` | `l9.rule.04.cursor.redis.session` | global | memory | always | 64 | `204ee35409fc` |
| `05-ask-mode.mdc` | `l9.rule.05.ask.mode` | global | governance | always | 60 | `02606be85a98` |
| `05-recursive-execution-kernel.mdc` | `l9.rule.recursive-execution-kernel` | global | execution | agent_requested | 38 | `7c60143d21bf` |
| `10-lang-typescript.mdc` | `l9.rule.10.lang.typescript` | global | typescript | auto_attached | 181 | `bd8fad3dd090` |
| `20-lang-python.mdc` | `l9.rule.20.lang.python` | global | python | auto_attached | 186 | `8f9921b041c0` |
| `22-context7-auto-invoke.mdc` | `l9.rule.22.context7.auto.invoke` | global | git | always | 51 | `0d3ad3e7d982` |
| `25-python-dora-header.mdc` | `l9.rule.25.python.dora.header` | global | python | always | 168 | `e27ac2cc723b` |
| `30-framework-react.mdc` | `l9.rule.30.framework.react` | global | typescript | auto_attached | 143 | `38c1291f4681` |
| `40-domain-autonomy.mdc` | `l9.rule.40.domain.autonomy` | global | security | auto_attached | 180 | `2af64ed1e71a` |
| `43-lang-postgresql.mdc` | `l9.rule.43.lang.postgresql` | global | security | auto_attached | 54 | `376750159196` |
| `45-pre-action-verification.mdc` | `l9.rule.45.pre.action.verification` | global | general | always | 81 | `bd895d6eef3f` |
| `50-qa-testing.mdc` | `l9.rule.50.qa.testing` | global | testing | always | 206 | `fba2fc9b34d3` |
| `51-qa-playwright.mdc` | `l9.rule.51.qa.playwright` | global | testing | auto_attached | 34 | `351a1f35357a` |
| `52-qa-jest.mdc` | `l9.rule.52.qa.jest` | global | testing | auto_attached | 38 | `493fb58ae77a` |
| `60-anti-patterns.mdc` | `l9.rule.60.anti.patterns` | global | testing | always | 351 | `5bb1cfc03b24` |
| `61-secrets-and-dependencies.mdc` | `l9.rule.61.secrets.and.dependencies` | global | security | auto_attached | 51 | `bcf0390b7f24` |
| `65-observability-performance.mdc` | `l9.rule.65.observability.performance` | global | memory | auto_attached | 41 | `e935f52d5df6` |
| `70-tool-efficiency.mdc` | `l9.rule.70.tool.efficiency` | global | governance | always | 184 | `4ff48f649686` |
| `71-ci-cd-pipeline.mdc` | `l9.rule.71.ci.cd.pipeline` | global | ci | auto_attached | 38 | `394c3835f9e7` |
| `72-review-ergonomics.mdc` | `l9.rule.72.review.ergonomics` | global | output | auto_attached | 166 | `70e8536a09e5` |
| `73-prompts-and-evals.mdc` | `l9.rule.73.prompts.and.evals` | global | general | auto_attached | 36 | `d4ebf11f79db` |
| `74-ai-safety-policy.mdc` | `l9.rule.74.ai.safety.policy` | global | security | auto_attached | 42 | `ea84fcc11477` |
| `80-gmp-execution.mdc` | `l9.rule.80.gmp.execution` | global | ci | always | 65 | `3c14113e0d09` |
| `81-gmp-audit.mdc` | `l9.rule.81.gmp.audit` | global | governance | always | 90 | `a7998c5521fd` |
| `82-deployment-manifest.mdc` | `l9.rule.82.deployment.manifest` | global | deployment | auto_attached | 71 | `cf96edc3a20d` |
| `83-gmp-contracts.mdc` | `l9.rule.83.gmp.contracts` | global | governance | always | 129 | `c2b50866ca55` |
| `84-cursor-governance-wiring.mdc` | `l9.rule.cursor-governance-wiring` | global | governance | always | 71 | `ebf45d7841f3` |
| `85-workflow-state-bridge.mdc` | `l9.rule.85.workflow.state.bridge` | global | ci | always | 123 | `7225ed66e89f` |
| `86-module-tier-mapping.mdc` | `l9.rule.86.module.tier.mapping` | global | governance | always | 52 | `f3dd67b5e508` |
| `87-cursor-memory-kernel.mdc` | `l9.rule.87.cursor.memory.kernel` | global | memory | always | 154 | `e6cc99f83500` |
| `87-cursor-subagent-orchestration.mdc` | `l9.rule.87.cursor.subagent.orchestration` | global | governance | always | 18 | `80f019c1481c` |
| `87-wire-workflow-guard.mdc` | `l9.rule.87.wire.workflow.guard` | global | ci | auto_attached | 52 | `57cc1b6ac317` |
| `88-bounded-session-autonomy.mdc` | `l9.rule.88.bounded.session.autonomy` | global | general | agent_requested | 18 | `d6d9f3ceb747` |
| `88-perplexity-run-harness.mdc` | `l9.rule.88.perplexity.run.harness` | global | governance | always | 51 | `e599b2b56828` |
| `89-constellation-gate-workspace-session.mdc` | `l9.rule.89.constellation.gate.workspace.session` | global | governance | always | 35 | `b6b565182a82` |
| `90-protected-core.mdc` | `l9.rule.90.protected.core` | global | governance | always | 110 | `3d0a8c303d9d` |
| `91-existing-code-source-of-truth.mdc` | `l9.rule.91.existing.code.source.of.truth` | global | general | always | 64 | `b15272f75d3d` |
| `92-learned-lessons.mdc` | `l9.rule.92.learned.lessons` | global | general | always | 778 | `7a7ff8fa50b4` |
| `93-c1-server-protection.mdc` | `l9.rule.93.c1.server.protection` | global | git | always | 82 | `e0d5aa093de5` |
| `94-deployment-prohibition.mdc` | `l9.rule.94.deployment.prohibition` | global | deployment | always | 19 | `3f41555552fd` |
| `95-agent-pattern-activation.mdc` | `l9.rule.95.agent.pattern.activation` | global | memory | always | 109 | `1faa1aae1604` |
| `95-test-fix-policy.mdc` | `l9.rule.testing.integrity` | global | testing | always | 57 | `06536d954dd0` |
| `96-env-no-hardcode.mdc` | `l9.rule.configuration.no-hardcode` | global | security | auto_attached | 47 | `11a14cef03f9` |
| `96-git-push-approval.mdc` | `l9.rule.96.git.push.approval` | global | git | always | 90 | `d83de4c11329` |
| `96-output-discipline.mdc` | `l9.rule.output-discipline` | global | output | agent_requested | 25 | `503f33079bd9` |
| `97-governance-ssot-paths.mdc` | `l9.rule.governance-ssot-paths` | global | governance | always | 55 | `85fc156798a1` |
| `97-graph-engine-architecture.mdc` | `l9.rule.97.graph.engine.architecture` | global | security | always | 98 | `c7210c913c17` |
| `97-graph-layer-boundary.mdc` | `l9.rule.graph-layer-boundary` | global | memory | always | 29 | `127f9ae133ff` |
| `97-ide-profile-exceptions.mdc` | `l9.rule.ide-profile-exceptions` | global | governance | agent_requested | 48 | `6d019ab496ca` |
| `98-graphiti-memory-gate.mdc` | `l9.rule.98.graphiti.memory.gate` | global | memory | always | 34 | `eb667b616bfa` |
| `99-execute-as-instructed.mdc` | `l9.rule.99.execute.as.instructed` | global | general | always | 41 | `8a91df91897f` |
| `99-graphiti-temporal.mdc` | `l9.rule.99.graphiti.temporal` | global | memory | always | 24 | `7689319b2562` |
| `99-incident-report.mdc` | `l9.rule.99.incident.report` | global | deployment | always | 463 | `9674bb08f2bf` |
| `99-no-auto-commit.mdc` | `l9.rule.99.no.auto.commit` | global | git | always | 35 | `d097a5c3d6fb` |

## Notes

- IDs marked as derived are compatibility identities. Add explicit immutable `id` metadata when a rule is materially edited.
- The JSON and YAML files are generated from the same in-memory model as this document.
- Never edit manifest counters by hand.
