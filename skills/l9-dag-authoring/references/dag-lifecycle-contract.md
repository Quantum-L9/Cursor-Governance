# DAG Lifecycle Contract

## Classification

Choose exactly one primary operation: CREATE, UPDATE, VALIDATE, REGISTER, or COMMAND_BIND.

CREATE and UPDATE may change DAG source. REGISTER may change only canonical registration/discovery surfaces. COMMAND_BIND may change only the requested command trigger. VALIDATE is read-only.

## Ownership

Resolve the domain owner before authoring semantics. This Skill translates or reconciles already-authorized workflow semantics into the canonical DAG representation. If semantic ownership is ambiguous, return BLOCKED rather than designing a new domain process here.

## Update law

An UPDATE preserves DAG identity and callers unless the request explicitly authorizes a migration. Never create a second DAG merely because the current graph needs repair.

## Completion

PASS requires all mandatory structural checks and all runtime probes available for the requested operation. PARTIAL is allowed only when a valid artifact exists but a non-local runtime probe cannot execute. BLOCKED means a material authority or dependency is unresolved. FAIL means a deterministic contract was violated.
