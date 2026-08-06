# L9 Cognitive Runtime MCP PR Contracts

One Markdown file per PR contract. Required sequence is PR-001 through PR-014. PR-015 and PR-016 are optional.

| PR | Contract | Optional | Depends on | Title |
|---|---|:---:|---|---|
| PR-001 | `L9CR-MCP-001` | No | None | Establish installable Python package and build baseline |
| PR-002 | `L9CR-MCP-002` | No | L9CR-MCP-001 | Add canonical typed models for cognitive runtime artifacts |
| PR-003 | `L9CR-MCP-003` | No | L9CR-MCP-002 | Introduce an in-memory CognitiveRuntimeService facade |
| PR-004 | `L9CR-MCP-004` | No | L9CR-MCP-003 | Add immutable runtime pack loading, manifest verification, and provenance |
| PR-005 | `L9CR-MCP-005` | No | L9CR-MCP-004 | Harden compiler parsing and remove silent fallback behavior |
| PR-006 | `L9CR-MCP-006` | No | L9CR-MCP-005 | Derive execution graphs from execution contracts |
| PR-007 | `L9CR-MCP-007` | No | L9CR-MCP-006 | Add runtime golden, determinism, concurrency, and security test suites |
| PR-008 | `L9CR-MCP-008` | No | L9CR-MCP-007 | Expose the cognitive runtime as a read-only MCP server over stdio |
| PR-009 | `L9CR-MCP-009` | No | L9CR-MCP-008 | Add isolated MCP run resources and bounded result storage |
| PR-010 | `L9CR-MCP-010` | No | L9CR-MCP-009 | Add hosted MCP Streamable HTTP transport |
| PR-011 | `L9CR-MCP-011` | No | L9CR-MCP-010 | Add OAuth authentication, scoped authorization, and audit middleware |
| PR-012 | `L9CR-MCP-012` | No | L9CR-MCP-011 | Add containerization and production deployment baseline |
| PR-013 | `L9CR-MCP-013` | No | L9CR-MCP-012 | Add reviewable Claude Code and Cursor MCP project configurations |
| PR-014 | `L9CR-MCP-014` | No | L9CR-MCP-013 | Add cross-client MCP conformance tests and production release gates |
| PR-015 | `L9CR-MCP-015` | Yes | L9CR-MCP-014 | Add GitHub organization and team-derived trust mapping |
| PR-016 | `L9CR-MCP-016` | Yes | L9CR-MCP-014 | Add validated agent adapter rendering |
