# DAG Lifecycle Contract

## Classification

Choose exactly one primary operation: CREATE, UPDATE, VALIDATE, REGISTER, COMMAND_BIND, or CONVERT.

CREATE and UPDATE may change DAG source. REGISTER may change only canonical registration/discovery surfaces. COMMAND_BIND may change only the requested command trigger. VALIDATE is read-only.

CONVERT classifies a `SESSION_GUIDANCE` graph against `policies/session-deprecation.yaml` and applies one disposition. It may emit a new `StateGraph` only for `CONVERT_TO_LANGGRAPH`. Twin and absorb dispositions write a receipt and do not emit. CONVERT never deletes the source SessionDAG in the same step. `allow_session_retire` stays false.

## Ownership

Resolve the domain owner before authoring semantics. This Skill translates or reconciles already-authorized workflow semantics into the canonical DAG representation. If semantic ownership is ambiguous, return BLOCKED rather than designing a new domain process here.

## Update law

An UPDATE preserves DAG identity and callers unless the request explicitly authorizes a migration. Never create a second DAG merely because the current graph needs repair.

## Completion

PASS requires all mandatory structural checks and all runtime probes available for the requested operation. PARTIAL is allowed only when a valid artifact exists but a non-local runtime probe cannot execute. BLOCKED means a material authority or dependency is unresolved, including an unknown CONVERT catalog id, a non-session source, or a missing `proof_path` on a twin or absorb row. FAIL means a deterministic contract was violated.
