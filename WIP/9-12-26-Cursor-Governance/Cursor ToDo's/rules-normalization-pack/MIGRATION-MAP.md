# MIGRATION-MAP - per-rule disposition

Generated from measured file sizes and confirmed frontmatter. Covers the 44
`alwaysApply: true` rules plus the one dead `.md` file. The 21 already-scoped
rules are correct as-is and are not listed.

Tiers: **A** keep always | **G** glob-scoped | **D** agent-selected via description | **X** merge or move out | **!** broken

| rule | bytes | tier | action |
|---|---:|:--:|---|
| `92-learned-lessons.mdc` | 29,357 | X | Move to l9-graphiti-memory retrieval. 29 KB of accumulated lessons is recall material, not policy. |
| `99-incident-report.mdc` | 14,595 | X | Move to commands/incident-report.md. A 14.6 KB template is not a rule. |
| `00-global.mdc` | 13,676 | A | Keep always, but split. Target under 4 KB. Push language/QA/tooling sections into the globbed rules that already exist. |
| `02-slash-commands.mdc` | 7,649 | D | Agent-selected. Command docs belong in commands/ and get pulled on demand. |
| `60-anti-patterns.mdc` | 7,358 | D | Agent-selected via description. Anti-patterns are situational, not per-turn. |
| `93-perplexity-research-protocol.md` | 6,528 | ! | DEAD FILE. A .md file in the rules directory is ignored by Cursor's rules system. 6.5 KB doing nothing. Rename to .mdc. |
| `87-cursor-memory-kernel.mdc` | 6,402 | X | Merge into 30-memory.mdc. |
| `25-python-dora-header.mdc` | 6,264 | G | globs: **/*.py |
| `84-cursor-governance-wiring.mdc` | 5,517 | D | Agent-selected. Only relevant during wiring work. |
| `01-vps-rules.mdc` | 5,423 | G | globs: infra/**, deploy/**, ops/**, **/*.tf, **/docker-compose*.yml |
| `50-qa-testing.mdc` | 5,280 | G | globs: tests/**, **/*_test.py, **/*.test.ts, **/*.spec.ts |
| `97-graph-engine-architecture.mdc` | 4,965 | G | globs scoped to graph engine paths. |
| `23-l9-skill-routing.mdc` | 4,647 | A | Keep always. Routing must be present to route. Trim to essentials. |
| `90-protected-core.mdc` | 4,148 | A | Keep always. Protection rules must not be skippable. |
| `81-gmp-audit.mdc` | 3,539 | D | Agent-selected during audit flows. |
| `70-tool-efficiency.mdc` | 3,389 | A | Keep always. Directly reduces token spend. Small. |
| `04-cursor-redis-session.mdc` | 3,232 | X | Merge into 30-memory.mdc. |
| `03-graphiti-memory.mdc` | 3,207 | X | Merge into 30-memory.mdc. |
| `85-workflow-state-bridge.mdc` | 3,118 | D | Agent-selected. |
| `80-gmp-execution.mdc` | 2,978 | D | Agent-selected during GMP execution. |
| `95-agent-pattern-activation.mdc` | 2,962 | D | Agent-selected. |
| `45-pre-action-verification.mdc` | 2,863 | A | Keep always. Worthless if conditionally loaded. |
| `93-c1-server-protection.mdc` | 2,823 | G | globs on C1 server paths; keep always only if the risk is genuinely destructive. |
| `96-git-push-approval.mdc` | 2,793 | X | Merge into 10-write-authority.mdc. |
| `83-gmp-contracts.mdc` | 2,616 | D | Agent-selected. |
| `22-context7-auto-invoke.mdc` | 2,483 | A | Keep always. Small, and it gates a tool the agent must know exists. |
| `01-git-push-prohibition.mdc` | 2,323 | X | Merge into 10-write-authority.mdc. |
| `95-test-fix-policy.mdc` | 2,218 | G | globs: tests/**, **/*_test.py, **/*.test.ts |
| `91-existing-code-source-of-truth.mdc` | 2,164 | A | Keep always. Anti-hallucination guard. Small. |
| `89-constellation-gate-workspace-session.mdc` | 2,105 | D | Agent-selected. |
| `87-l4-local-autonomy.mdc` | 2,061 | X | Merge into 10-write-authority.mdc. |
| `86-module-tier-mapping.mdc` | 1,987 | D | Agent-selected. |
| `88-shared-worktree-isolation.mdc` | 1,983 | D | Agent-selected. |
| `97-governance-ssot-paths.mdc` | 1,938 | A | Keep always. Path contract prevents drift. Small. |
| `05-ask-mode.mdc` | 1,822 | A | Keep always. Drop globs: [] - dead metadata. |
| `97-graph-layer-boundary.mdc` | 1,768 | G | globs on graph paths. Drop globs:['**/*'] - ignored while alwaysApply is true. |
| `99-execute-as-instructed.mdc` | 1,710 | A | Keep always. Small. |
| `88-perplexity-run-harness.mdc` | 1,614 | D | Agent-selected. |
| `99-no-auto-commit.mdc` | 1,513 | X | Merge into 10-write-authority.mdc. |
| `98-graphiti-memory-gate.mdc` | 1,297 | X | Merge into 30-memory.mdc. Drop globs:['**/*'] - ignored under alwaysApply: true. |
| `98-make-pr-remediation.mdc` | 1,225 | D | Agent-selected. Fires only after `make pr`. |
| `94-deployment-prohibition.mdc` | 973 | X | Merge into 10-write-authority.mdc. |
| `62-github-openclaw-authority.mdc` | 944 | D | Agent-selected. |
| `87-cursor-subagent-orchestration.mdc` | 836 | X | Convert to real agent files under agents/. |
| `99-graphiti-temporal.mdc` | 662 | X | Merge into 30-memory.mdc. Drop globs:['**/*'] - ignored under alwaysApply: true. |

## Tier totals

| tier | meaning | count |
|:--:|---|---:|
| A | Always | 10 |
| G | Glob-scoped | 7 |
| D | Agent-selected | 14 |
| X | Merge / move out | 13 |
| ! | BROKEN | 1 |

## Budget effect

- always-apply now: **182,427 bytes** (~45,606 tokens every turn)
- after retiering, before trimming: **38,840 bytes** (~9,710 tokens)
- after trimming `00-global` to 4 KB and `23-l9-skill-routing` to 3 KB: **27,613 bytes** (~6,903 tokens)
- reduction: **85%**

Nothing is deleted. Every byte stays reachable - it just stops riding along on
turns that do not need it.
