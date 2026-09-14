# Reconciled Environment Experience Architecture

## Purpose

This pack models the execution environment as an observed control system rather than one monolithic "ready/not-ready" flag. The nine unique source packs cover different sessions and repositories, so a canonical state must preserve both recurring cross-session defects and context-specific exceptions.

## Canonical boundaries

1. **Repository ownership boundary** — consumer-tracked paths are authoritative for repository content. Bootstrap may project only into non-owned/session-owned surfaces.
2. **Environment authority plane** — interpreter, PATH/PYTHONPATH, account variables, settings, and breakglass authority require explicit source provenance and precedence.
3. **Bootstrap lifecycle plane** — settings, skills, rules, memory, MCP, plugins, and capabilities carry per-component status, reason, freshness, and remediation evidence.
4. **Capability plane** — GitHub REST, GitHub GraphQL, credential validity, broker reachability, MCP parse/approval, and memory transports are separate capabilities.
5. **Governance execution plane** — rules/skills may require a mechanism only if the surface and consumer repository implement it, or the contract declares a supported fallback.
6. **Safety plane** — destructive/staging guardrails remain fail-closed under unresolved scope while exposing actionable, stage-specific diagnostics and reachable authorized exceptions.
7. **Continuity plane** — writeback, hydration, receipts, queued notifications, and release state carry task-bearing and freshness information.
8. **Validation plane** — local CI parity, generated-artifact membership, toolchain readiness, and service dependencies are checked before remote publication.

## Dependency direction

Repository ownership and authority provenance are upstream of bootstrap projection. Bootstrap freshness and capability probing are upstream of rule activation and memory hydration. Project toolchain resolution is upstream of local validation. Governance publish contracts and release receipts are upstream of publication. Safety gates wrap mutations but must not become an alternate owner of repository state.

## Current architecture gaps

The highest-leverage gaps are CI-002 (ownership-safe projection), CI-004 (fresh bootstrap receipts), CI-006 (authority drift), CI-009 (toolchain authority), and CI-001 (GitHub transport truth). Open policy choices are isolated in `OPEN_DECISIONS.yaml` rather than being silently resolved here.
