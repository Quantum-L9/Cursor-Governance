# Program Execution Architecture

The Program Controller remains the sole Program-state authority. Provider
integration is subordinate to Controller admission and is split into explicit
layers so a new model or host never becomes a new execution system.

```text
Program Controller
  -> Peer Runtime Binding
  -> Execution Profile
  -> Peer Execution Core
  -> Shared Transport
  -> Thin Provider
  -> Provider / Host
```

## Ownership

- `core/` owns Program truth, Program Locks, readiness, task state, canonical
  receipts, independent verification, and convergence.
- `peer_execution/` owns provider-neutral lifecycle, context manifests,
  permissions, budgets, shared process mechanics, provider result normalization,
  and Program-facing receipt construction.
- `environment/program-execution/peer_execution/autonomy/` owns shared admitted-dispatch bounded
  concurrency mechanics. It is subordinate to Program Controller readiness and
  root `autonomy/` authorization.
- `adapters/<provider>/` contains only provider-specific capability probing,
  request translation/invocation, response translation, and provider-specific
  helpers.
- `environment/agents/PEER_RUNTIME_BINDINGS.yaml` owns peer identity -> surface ->
  provider -> execution-profile topology.

Provider descriptors never own `agent_ref`. A provider may disappear or be
substituted without changing peer identity or Program state.

## Failure law

Provider absence, transport absence, and unsupported capabilities return
`BLOCKED` or `CAPABILITY_UNSUPPORTED`. They never create false completion,
provider-local Program state, or a second scheduler.

## Dual plane

The Program Controller is the sole Program-state authority. The autonomy
runtime at `peer_execution/autonomy/` is a subordinate dispatch plane.
`pec status` reports a read-only `autonomy_plane` object. Autonomy
`compile_context()` reports a read-only `program_plane` object. Neither
plane writes the other's packets. pec does not auto-init
`.l9/autonomy/campaigns`.

## Admission

Compile campaign source → validate Blueprint → `pec bootstrap`. Default
bootstrap calls instantiated `validate_blueprint` on a complete pair and
refuses `definition_status=draft`. `--admission-draft` is inspect-only.
