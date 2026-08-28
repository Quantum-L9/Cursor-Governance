<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: execution-cost-kernel
version: 2.0.0
status: active
-->

# Execution Cost Kernel

Bound expensive or high-risk generation.

- Gate C declares `files_in_scope` for every multi-file build.
- Coding and schema skills declare allowed and forbidden output types.
- Generated modules receive import, compile, or smoke-test postconditions.
- Research-backed skills state a source cap or a stopping rule.
- Halt on unresolved dependencies instead of silently retrying.
- Scope prior-session context explicitly; do not inherit unrelated output.
- User updates may announce the execution path, but approval is required only when a real decision is missing or the user asked for gated confirmation.
