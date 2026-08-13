# Cursor governance rules manifest

Generated: `2026-08-14T16:07:52Z`. Source: `rules/*.mdc`.

## Counts

| Bucket | Count |
|---|---:|
| Total MDC files | **68** |
| `alwaysApply: true` | **45** |
| `alwaysApply: false` | **23** |
| No boolean `alwaysApply` | **0** |
| Explicit stable IDs | **0** |
| Derived compatibility IDs | **68** |
| Deprecated rules | **1** |

## Rule index

| File | ID | Scope | Domain | Activation | Lines | Digest |
|---|---|---|---|---|---:|---|
| `00-global.mdc` | `l9.rule.00.global` | global | security | always | 279 | `a9a3c4f08ebd` |
| `01-git-push-prohibition.mdc` | `l9.rule.01.git.push.prohibition` | global | git | always | 73 | `6b927b2c58ab` |
| `01-vps-rules.mdc` | `l9.rule.01.vps.rules` | global | git | always | 185 | `5e450fe4b1a5` |
| `02-slash-commands.mdc` | `l9.rule.02.slash.commands` | global | governance | always | 152 | `74135d8079df` |
| `03-graphiti-memory.mdc` | `l9.rule.03.graphiti.memory` | global | memory | always | 61 | `ac7320148e83` |
| `03-mcp-memory.mdc` | `l9.rule.03.mcp.memory` | global | deployment | auto_attached | 419 | `9acc51f294a8` |
| `04-cursor-redis-session.mdc` | `l9.rule.04.cursor.redis.session` | global | memory | always | 64 | `20b6d6cc1849` |
| `05-ask-mode.mdc` | `l9.rule.05.ask.mode` | global | governance | always | 59 | `c61a1562d055` |
| `05-recursive-execution-kernel.mdc` | `l9.rule.05.recursive.execution.kernel` | global | execution | agent_requested | 32 | `e71d08c6085e` |
| `10-lang-typescript.mdc` | `l9.rule.10.lang.typescript` | global | typescript | auto_attached | 177 | `6f3f1cba9b95` |
| `15-work-tracking.mdc` | `l9.rule.15.work.tracking` | global | general | agent_requested | 11 | `35231a24d9bb` |
| `20-lang-python.mdc` | `l9.rule.20.lang.python` | global | python | auto_attached | 184 | `ff7d2c9337b7` |
| `22-context7-auto-invoke.mdc` | `l9.rule.22.context7.auto.invoke` | global | git | always | 51 | `0d3ad3e7d982` |
| `23-l9-skill-routing.mdc` | `l9.rule.23.l9.skill.routing` | global | governance | always | 89 | `a33ee9440db9` |
| `25-python-dora-header.mdc` | `l9.rule.25.python.dora.header` | global | python | always | 166 | `3d3c0adce1de` |
| `30-framework-react.mdc` | `l9.rule.30.framework.react` | global | typescript | auto_attached | 139 | `99c30e79186d` |
| `40-domain-autonomy.mdc` | `l9.rule.40.domain.autonomy` | global | security | auto_attached | 176 | `d9eea4c8153c` |
| `43-lang-postgresql.mdc` | `l9.rule.43.lang.postgresql` | global | security | auto_attached | 49 | `6ad1f03ec17c` |
| `45-pre-action-verification.mdc` | `l9.rule.45.pre.action.verification` | global | general | always | 85 | `997a5055773c` |
| `46-kernel-pack-new-branch.mdc` | `l9.rule.46.kernel.pack.new.branch` | global | general | always | 29 | `c279fab25184` |
| `50-qa-testing.mdc` | `l9.rule.50.qa.testing` | global | testing | always | 201 | `065dbc102466` |
| `51-qa-playwright.mdc` | `l9.rule.51.qa.playwright` | global | testing | auto_attached | 28 | `cde8669cf30e` |
| `52-qa-jest.mdc` | `l9.rule.52.qa.jest` | global | testing | auto_attached | 28 | `d962c29bcae4` |
| `60-anti-patterns.mdc` | `l9.rule.60.anti.patterns` | global | testing | always | 351 | `dd7c1435ca07` |
| `61-secrets-and-dependencies.mdc` | `l9.rule.61.secrets.and.dependencies` | global | security | auto_attached | 44 | `8cb3bf6fe692` |
| `62-github-openclaw-authority.mdc` | `l9.rule.62.github.openclaw.authority` | global | git | always | 17 | `8fa1679e0328` |
| `65-observability-performance.mdc` | `l9.rule.65.observability.performance` | global | memory | auto_attached | 37 | `ad2094596166` |
| `70-tool-efficiency.mdc` | `l9.rule.70.tool.efficiency` | global | governance | always | 184 | `993687901db8` |
| `71-ci-cd-pipeline.mdc` | `l9.rule.71.ci.cd.pipeline` | global | ci | auto_attached | 34 | `09190b8a2116` |
| `72-review-ergonomics.mdc` | `l9.rule.72.review.ergonomics` | global | output | auto_attached | 163 | `59ba4135d674` |
| `73-prompts-and-evals.mdc` | `l9.rule.73.prompts.and.evals` | global | general | auto_attached | 32 | `3c76fec810f9` |
| `74-ai-safety-policy.mdc` | `l9.rule.74.ai.safety.policy` | global | security | auto_attached | 39 | `541f5a39f891` |
| `80-gmp-execution.mdc` | `l9.rule.80.gmp.execution` | global | ci | always | 65 | `ed64dfe9390f` |
| `81-gmp-audit.mdc` | `l9.rule.81.gmp.audit` | global | governance | always | 90 | `ef4a222671dc` |
| `82-deployment-manifest.mdc` | `l9.rule.82.deployment.manifest` | global | deployment | auto_attached | 66 | `479c5a2ecc1b` |
| `83-gmp-contracts.mdc` | `l9.rule.83.gmp.contracts` | global | governance | always | 129 | `24c536dd8153` |
| `84-cursor-governance-wiring.mdc` | `l9.rule.84.cursor.governance.wiring` | global | governance | always | 67 | `4491ac1e7c19` |
| `85-workflow-state-bridge.mdc` | `l9.rule.85.workflow.state.bridge` | global | memory | always | 85 | `5053dea9a2be` |
| `86-module-tier-mapping.mdc` | `l9.rule.86.module.tier.mapping` | global | governance | always | 52 | `2e4024f8f8b7` |
| `87-cursor-memory-kernel.mdc` | `l9.rule.87.cursor.memory.kernel` | global | memory | always | 160 | `fdf0be39c33e` |
| `87-cursor-subagent-orchestration.mdc` | `l9.rule.87.cursor.subagent.orchestration` | global | governance | always | 18 | `33604398e139` |
| `87-l4-local-autonomy.mdc` | `l9.rule.87.l4.local.autonomy` | global | git | always | 49 | `7c709b33b6d7` |
| `87-wire-workflow-guard.mdc` | `l9.rule.87.wire.workflow.guard` | global | ci | auto_attached | 47 | `279122e9a3d0` |
| `88-bounded-session-autonomy.mdc` | `l9.rule.88.bounded.session.autonomy` | global | general | agent_requested | 18 | `a99f7b00c3b2` |
| `88-perplexity-run-harness.mdc` | `l9.rule.88.perplexity.run.harness` | global | governance | always | 51 | `12437e7f5e20` |
| `88-shared-worktree-isolation.mdc` | `l9.rule.88.shared.worktree.isolation` | global | git | always | 42 | `65e2a9c8fa6c` |
| `89-constellation-gate-workspace-session.mdc` | `l9.rule.89.constellation.gate.workspace.session` | global | governance | always | 34 | `da564ec0d699` |
| `90-protected-core.mdc` | `l9.rule.90.protected.core` | global | governance | always | 100 | `fcba3a0e98eb` |
| `91-existing-code-source-of-truth.mdc` | `l9.rule.91.existing.code.source.of.truth` | global | general | always | 64 | `4c00176a2371` |
| `92-learned-lessons.mdc` | `l9.rule.92.learned.lessons` | global | general | always | 806 | `29fa6efe0c8e` |
| `93-c1-server-protection.mdc` | `l9.rule.93.c1.server.protection` | global | git | always | 82 | `425be8bde08f` |
| `93-perplexity-research-protocol.mdc` | `l9.rule.93.perplexity.research.protocol` | global | general | agent_requested | 141 | `6ee421f2585c` |
| `94-deployment-prohibition.mdc` | `l9.rule.94.deployment.prohibition` | global | deployment | always | 18 | `7a94db235388` |
| `95-agent-pattern-activation.mdc` | `l9.rule.95.agent.pattern.activation` | global | memory | always | 109 | `0c077285f21f` |
| `95-test-fix-policy.mdc` | `l9.rule.95.test.fix.policy` | global | testing | always | 51 | `bdcb5376bdda` |
| `96-env-no-hardcode.mdc` | `l9.rule.96.env.no.hardcode` | global | general | auto_attached | 34 | `dfb9fe3954f4` |
| `96-git-push-approval.mdc` | `l9.rule.96.git.push.approval` | global | git | always | 97 | `6612401e27a5` |
| `96-output-discipline.mdc` | `l9.rule.96.output.discipline` | global | output | agent_requested | 19 | `3079c1d21f94` |
| `97-governance-ssot-paths.mdc` | `l9.rule.97.governance.ssot.paths` | global | git | always | 49 | `f472f499420b` |
| `97-graph-engine-architecture.mdc` | `l9.rule.97.graph.engine.architecture` | global | security | always | 97 | `8ba078e7917c` |
| `97-graph-layer-boundary.mdc` | `l9.rule.97.graph.layer.boundary` | global | memory | always | 31 | `cb4121c0d61d` |
| `97-ide-profile-exceptions.mdc` | `l9.rule.97.ide.profile.exceptions` | global | general | agent_requested | 42 | `32e96e77cfe3` |
| `98-graphiti-memory-gate.mdc` | `l9.rule.98.graphiti.memory.gate` | global | memory | always | 33 | `c9da41934e34` |
| `98-make-pr-remediation.mdc` | `l9.rule.98.make.pr.remediation` | global | general | always | 30 | `fec38412787b` |
| `99-execute-as-instructed.mdc` | `l9.rule.99.execute.as.instructed` | global | general | always | 41 | `ed81ca9d7f79` |
| `99-graphiti-temporal.mdc` | `l9.rule.99.graphiti.temporal` | global | memory | always | 23 | `a57d2288be29` |
| `99-incident-report.mdc` | `l9.rule.99.incident.report` | global | deployment | always | 463 | `7bf15c37f97f` |
| `99-no-auto-commit.mdc` | `l9.rule.99.no.auto.commit` | global | git | always | 48 | `6258c09dd6bc` |

## Notes

- IDs marked as derived are compatibility identities. Add explicit immutable `id` metadata when a rule is materially edited.
- The JSON and YAML files are generated from the same in-memory model as this document.
- Never edit manifest counters by hand.
