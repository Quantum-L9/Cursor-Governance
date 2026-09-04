# Root Autonomy Control Plane Bridge

This bridge maps one Program task into one root-autonomy campaign and action.
Program leases remain authoritative; the root-autonomy lease is subordinate and
must not outlive the Program lease.

## One live authority flow

`make campaign` execute binds through `grant.py` before any worker write:

1. Probe `autonomy/` (fail closed if the control plane is missing).
2. Resolve the full canonical `PeerBinding`
   (`agent_ref` / `surface` / `provider_ref` / `execution_profile_ref` /
   `autonomy_provider_ref`) — never a surface-only identity.
3. Read the **live Program parent** read-only through `program_authority.py`
   and refuse to issue anything beneath a parent that is terminal, released,
   expired, or bound to a different lease, base, or contract digest.
4. Map the rendered Program contract to a schema-valid campaign packet.
5. Compile and bootstrap the graph in the PEC workspace SQLite store.
6. Complete synthesis (the already-rendered contract) so the executor is READY.
7. Register a conformant `AdapterOrchestrator` session from that binding plus
   the current `autonomy/policies/adapter-requirements.json` policy.
8. Issue the executor lease with the adapter session and the Program parent
   bound into its metadata, with a TTL **capped to the parent's expiry**, and
   acknowledge exactly `_executor_authority(contract)` — the action-specific
   intersection of `requested_actions`, never the executor role's full set.
9. Authorize `repository.write_scoped` (+ `git.commit_local` only when the task
   requested `commit`) through `AdapterOrchestrator.authorize_tool`.
10. Write task/attempt-scoped receipts under `runtime/autonomy-grants/`
    (`<task>.attempt-<n>.grant.json` + `<task>.attempt-<n>.packet.json`).
    Workspace-global `autonomy-grant.json`/`autonomy-packet.json` are retired:
    concurrent tasks must never overwrite each other's authority evidence.

`AdapterOrchestrator.request_agent()` is deliberately **not** on this path. It
derives its acknowledgment set from the role policy and `acknowledge_agent()`
demands that exact set, which would hand a `local_write`-only task
`git.commit_local`. That is the invariant below, and it is not negotiable.

## The `autonomy_authority` sidecar

The grant returns a task-scoped `autonomy_authority` envelope
(`l9.program-execution.autonomy-authority.v1`). It travels **beside** the
rendered contract — through `CanonicalExecutionRequest`, the
`PeerExecutionAdapter` dispatch record, and into the provider — and never
inside it. `rendered_contract` and `rendered_contract_digest` stay defined
solely by what the Controller rendered, so carrying root authority can never
change Program contract identity. A sidecar naming another task is refused.

## Read-only `ProgramAuthorityVerifier`

`program_authority.py` is the only reader of canonical Program state on this
path, and it only ever reads:

- the connection is opened read-only, so a defect here cannot write Program
  truth;
- every call re-reads, so nothing acts on a parent that was revoked a moment
  ago;
- no Program transition is performed, requested, or implied.

A workspace with no canonical PEC state is reported `bound: false` rather than
treated as live — the authority evidence says what was actually read.

## Per-effect authorization and decision coverage

`ProgramBoundEffectAuthorizer` is the single PE-to-root authorizer for one
worker effect, composed into the live Claude `PreToolUse` wrapper
(`environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py`)
ahead of the existing `ops/autonomy/local_execution_gate.py`, which remains the
downstream owner of publish-path, L4, and worktree-isolation policy and
receives byte-identical hook stdin. For each effect, in order:

1. re-read the live Program parent and refuse any drift from the sidecar;
2. resolve the capability — a shell tool reaches `test.run` only through the
   canonical `peer_execution.validation_command` grammar;
3. normalize the resource inside the bound worktree, refusing absolute escapes,
   traversal, and symlinked parents or targets;
4. heartbeat the subordinate lease against the worktree's **actual** HEAD, so a
   drifted base revokes the lease instead of being authorized over;
5. ask the root gateway through the live orchestrator.

Missing authority, an unavailable authorizer, or a missing downstream gate
inside a worker window is a denial, not a pass.

Before the Controller records anything, `run_campaign` requires that every path
the worktree actually shows as changed by the provider window carries an
allowed `repository.write_scoped` decision under the same subordinate lease.
An unmediated write never becomes a recorded Program attempt.

## Grant generations

Root grants are generations, not Controller attempts. `grant_task_mutation`
with no explicit `attempt_number` first looks for the receipt PE already
recorded for the task (`latest_grant_receipt`): a lease that is still ACTIVE
beneath the same Program parent and peer binding is **resumed** (a lost window
keeps the authority it ran under); a terminal lease is succeeded by the next
generation, which mints a new root campaign id. Parent or binding drift refuses
the resume (`GRANT_PARENT_DRIFT`, `GRANT_BINDING_DRIFT`), and an explicit
request for a terminal generation is refused (`GRANT_GENERATION_TERMINAL`)
rather than re-minted under the same identity. A mutation grant is never
issued beneath an unbound parent (`PROGRAM_PARENT_UNBOUND`): with no canonical
Program state, expiry, revocation and drift are unobservable.

The worker environment the provider exports is a **lookup key** for that
receipt, never authority itself: the PreToolUse wrapper resolves
`L9_PROGRAM_ATTEMPT_NUMBER` and `L9_AUTONOMY_AUTHORITY_DIGEST` to the persisted
grant receipt, verifies the sidecar digest and every bound field, and runs the
authorizer on the receipt's sidecar. A forged digest, a missing receipt, or an
edited receipt denies every effect.

## Terminal subordinate lifecycle

- **Success:** a typed `ExecutionResult` is submitted under the subordinate
  lease, which completes the executor action and releases the lease and its
  resource claims. Finished work leaves no live mutation authority.
- **Controller rejection:** the root supporting artifact is invalidated.
  Root autonomy withdraws its own evidence; it never decides the verdict.
- **Failure or parent invalidation:** `revoke_task_grant()` revokes the lease
  and releases its claims, so a failed child retains nothing.

PEC remains the sole authority on Program state and completion. `run_campaign`
asks the Controller to verify independently *after* the root lifecycle closes,
and `owns_program_state` stays `false` everywhere in this bridge.

## Worker effect capabilities

The capability of an effect is derived from the tool's identity alone. A
worker's tool input is untrusted: a `capability` claim inside it is stripped
before inference, an unmapped tool name is refused (`TOOL_UNMAPPED`) rather
than defaulted to a read, and only `repository.read`, `repository.search`,
`repository.write_scoped`, `git.diff` and validated `test.run` may be exercised
as effects (`CAPABILITY_NOT_EFFECT_AUTHORIZABLE` otherwise), even when the
subordinate lease holds more. The terminal result must name the rendered
contract digest the lease was issued for.

## Invariants

- `requested_actions` is the ceiling: `local_write` never implies `commit`,
  Program Execution retains `commit`, and the provider receives only delegated
  actions.
- Push, pull request, and merge stay forbidden on this autonomous path.
- Program Execution remains local-commit-only.
