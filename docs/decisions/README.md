# Architecture Decision Records

This directory is the repository's record of durable architecture decisions. Each ADR is self-contained: its filename, status, context, options, decision, and consequences are the authoritative record. Historical files retain their existing numbers and filenames; this index does not renumber, supersede, or rewrite them.

## Current cross-repository decision records

| Record | Status | Scope |
|---|---|---|
| [ADR-0036: Core Owns the Makefile Compiler Runtime](ADR-0036-core-owns-makefile-compiler-runtime.md) | Accepted | Compiler V2 renderer ownership: `Quantum-L9/l9-ci-core` owns generated `Repo.mk`; Cursor-Governance retains dispatcher and publication authority. |
| [ADR-0037: Direct Agent Memory Records Represent Independently Governable Knowledge](ADR-0037-direct-agent-memory-record-granularity.md) | Accepted | Defines one `memory.write_agent` record (independently retrievable/supersedable); independent memories are separate writes; `memory.phase_lock` belongs to the governed lane only and is not SessionStart prefetch. |

New durable architecture decisions are added as ADRs in this directory. Superseding a decision requires a later ADR that links to the record it replaces; prior records are never deleted merely because a newer choice exists.
