# GlobalCommands rules manifest

Generated: `2026-04-11T18:47:40Z` (UTC). Folder: `/Users/ib-mac/Dropbox/Cursor Governance/GlobalCommands/rules`.

## Counts

| Bucket | Count |
|--------|------:|
| `alwaysApply: true` | **37** |
| `alwaysApply: false` | **11** |
| No boolean `alwaysApply` | **0** |

## File index

- `00-global.mdc` — alwaysApply **true** — Primary global rules for the L9 Secure AI OS monorepo: architecture invariants, safety, and universal coding standards.
- `01-git-push-prohibition.mdc` — alwaysApply **true** — NEVER push to git without explicit user request. This is the #1 rule for this project.
- `01-vps-rules.mdc` — alwaysApply **true** — L9 production VPS reference: SSH, paths, Docker stack, Caddy routes, and local edit → push → pull workflow.
- `02-slash-commands.mdc` — alwaysApply **true** — Slash command recognition and execution - repo-agnostic governance protocols
- `03-mcp-memory.mdc` — alwaysApply **true** — L9 Memory Stack - C1 PRIMARY server, PostgreSQL, Neo4j, Redis, pgvector
- `04-cursor-redis-session.mdc` — alwaysApply **true** — Redis session context via MCP (cache_get_session_context / cache_set_session_context) to resume work and avoid cross-session amnesia.
- `05-ask-mode.mdc` — alwaysApply **true** — Behavioral rules for Ask Mode in Cursor - no code generation, plain English explanations only.
- `10-lang-typescript.mdc` — alwaysApply **false** — TypeScript + TSX language rules for AI OS UI and agent-facing frontends.
- `20-lang-python.mdc` — alwaysApply **true** — Python rules for AI OS runtime, agents, orchestration, and backend services.
- `25-python-dora-header.mdc` — alwaysApply **true** — L9 Python module structure: header meta, footer meta, and DORA __l9_trace__ block per codegen contract.
- `30-framework-react.mdc` — alwaysApply **false** — React UI rules for AI OS control panels, consoles, and visualization surfaces.
- `30-odoo-native.mdc` — alwaysApply **true** — Odoo-native code patterns for PlastOS modules: ORM, recordsets, domains, actions
- `40-domain-autonomy.mdc` — alwaysApply **false** — Autonomous agents and AI OS autonomy domain rules: safety envelopes, escalation, and irreversible action constraints.
- `50-qa-testing.mdc` — alwaysApply **true** — Testing and QA rules for AI OS agents, runtimes, and integrations.
- `60-anti-patterns.mdc` — alwaysApply **true** — Common anti-patterns and mistakes across TypeScript, Python, React, FastAPI, security, and testing, with side-by-side corrections.
- `61-secrets-and-dependencies.mdc` — alwaysApply **false** — Secrets handling and dependency/supply-chain rules for L9.
- `65-observability-performance.mdc` — alwaysApply **false** — Observability and performance rules for L9 runtime, agents, memory, and orchestration.
- `70-tool-efficiency.mdc` — alwaysApply **true** — Developer tooling efficiency: terminal usage, command batching, context budgeting, and Cursor tool ergonomics.
- `71-ci-cd-pipeline.mdc` — alwaysApply **false** — CI/CD pipeline and policy enforcement rules for L9.
- `72-review-ergonomics.mdc` — alwaysApply **false** — Review ergonomics, PR size guidance, and checklists for L9.
- `73-prompts-and-evals.mdc` — alwaysApply **false** — Prompt, kernel, and eval discipline for L9.
- `74-ai-safety-policy.mdc` — alwaysApply **false** — AI content safety and policy rules for prompts and kernels in L9.
- `80-gmp-execution.mdc` — alwaysApply **true** — GMP v1.7 action workflow: enforce Phases 0–6, quick actions, and corrective runs for L9 repo changes.
- `81-gmp-audit.mdc` — alwaysApply **true** — GMP audit and verification rules: canonical and guide prompts mapped to L9 PRs and workspaces.
- `82-deployment-manifest.mdc` — alwaysApply **false** — Deployment manifest and orchestrator wiring rules derived from DEPLOYMENT_MANIFEST_v1.7 and GMP orchestrator prompts.
- `83-gmp-contracts.mdc` — alwaysApply **true** — GMP contract enforcement: binding report paths, sequential GMP IDs, ISO dates, and post-write validation.
- `84-cursor-governance-wiring.mdc` — alwaysApply **true** — Where cursor memory and wiring live: .cursor-commands in every repo, executables in governance. Applies to all repos (global).
- `85-workflow-state-bridge.mdc` — alwaysApply **true** — Bridge Cursor runs to workflow_state.md: enforce state sync, phases, and next-step alignment for the L9 repo.
- `86-module-tier-mapping.mdc` — alwaysApply **true** — Map files to L9 tiers (kernel, runtime, infra, UX) and inject the right GMP module prompts per tier.
- `87-cursor-memory-kernel.mdc` — alwaysApply **true** — Cursor Memory Kernel enforcement — authoritative source for memory operations, scopes, and session lifecycle
- `87-wire-workflow-guard.mdc` — alwaysApply **false** — Guardrails for wiring changes between kernels, executors, orchestrators, and infra in the L9 OS.
- `88-perplexity-run-harness.mdc` — alwaysApply **true** — L9-specific Perplexity/Cursor harness: enforce surgical edits, no manual fallbacks, and batch spec generation.
- `89-constellation-gate-workspace-session.mdc` — alwaysApply **true** — Constellation.Gate (2026-04-11): Suite 6 workspace setup, git layout, and why Cursor symlinks stay out of git.
- `90-protected-core.mdc` — alwaysApply **true** — Protected L9 core and infra files: require separate Phase 0 plan and dedicated GMP runs before any edit.
- `91-existing-code-source-of-truth.mdc` — alwaysApply **true** — Existing code is source of truth — new code adapts to established patterns
- `92-learned-lessons.mdc` — alwaysApply **true** — Critical lessons learned from repeated mistakes. These rules prevent known failure patterns.
- `93-c1-server-protection.mdc` — alwaysApply **true** — C1 server protection: no Docker, deploy, or .env changes and no remote git operations without explicit user approval.
- `94-deployment-prohibition.mdc` — alwaysApply **true** — Prohibits AI agents from using the 10X deployment script.
- `95-agent-pattern-activation.mdc` — alwaysApply **true** — Agent pattern auto-activation: detect subsystem (auth, tools, memory, code) and required approval before mutations.
- `95-plasticos-equipment-policy.mdc` — alwaysApply **true** — Equipment type wiring policy for PlasticOS facility profiles
- `95-test-fix-policy.mdc` — alwaysApply **true** — Never skip tests to avoid failures — fix the underlying issue
- `96-env-no-hardcode.mdc` — alwaysApply **true** — Use .env for configuration — never hardcode database, hosts, ports
- `96-git-push-approval.mdc` — alwaysApply **true** — Git push requires explicit user approval — never auto-push
- `97-graph-engine-architecture.mdc` — alwaysApply **true** — Graph Engine architecture: chassis contract, gates, Cypher security, action handlers
- `98-odoo-sh-staging.mdc` — alwaysApply **true** — Odoo.sh staging reference: instance URL, build ID, SSH access, and shell commands for Odoo 19.
- `99-execute-as-instructed.mdc` — alwaysApply **true** — Execute exactly as instructed — no autonomous reasoning or skipping steps
- `99-incident-report.mdc` — alwaysApply **true** — Governance incident reports: unauthorized deletion, VPS overstepping, corrective actions, and permanent enforcement lessons.
- `99-no-auto-commit.mdc` — alwaysApply **true** — Never auto-commit or auto-push without explicit user approval
