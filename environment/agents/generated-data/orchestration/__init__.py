"""L9 Subagent-Generated Data — Instantiation Wave 1 (durable orchestration).

Provides the durable pipeline engine the activation layer builds on:
- module_loader: load prior-wave runtime/adapter modules by their real path
- state_store: SQLite-backed job state machine, snapshots, attempts, receipts,
  reuse events, context selections, invalidation events, and dead letters
- receipts: hash-chained processing receipts with chain verification
- retry_policy: deterministic retry classification and backoff decisions
- processor: wires the Wave 1-3 runtime into a persisted processing job

This layer owns orchestration and dispatch only. Canonical memory admission,
storage, reuse persistence, and source invalidation remain owned by
l9-graphiti-memory.
"""

__version__ = "1.0.0"
