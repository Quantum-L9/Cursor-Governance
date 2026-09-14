# PR: Refactor peer execution behind one thin-provider substrate

## Summary

This change fixes the execution-adapter ownership inversion in
`Cursor-Governance`. Reusable execution behavior no longer lives in Claude or
peer-specific worker adapters. It is owned once by `Peer Execution Core`, below
Program Controller admission and above provider invocation.

## Architecture

```text
Program Controller
  -> Peer Runtime Binding
  -> Execution Profile
  -> Peer Execution Core
  -> Shared Transport
  -> Thin Provider
  -> Provider / Host
```

The Program Controller remains the only Program-state authority. Peer Execution
Core manages provider-neutral admitted execution mechanics only. Root
`autonomy/` remains the authorization/control plane.

## Main changes

1. Promote the existing shared adapter lifecycle from `adapters/common/` into
   `peer_execution/`; keep import-compatible shims at the legacy path.
2. Add canonical request/result/context schemas and reusable execution profiles.
3. Change peer topology from `adapter_id` coupling to
   `provider_ref + execution_profile_ref`; provider descriptors no longer own
   `agent_ref`.
4. Make Claude Code a thin provider. Peer Execution Core supplies the validated
   context, resolved permission ceiling, timeout budget, telemetry context, and
   canonical receipt boundary before provider translation.
5. Retire `claude-code-bounded-autonomy` as a provider. Move its bounded runtime
   into shared `peer_execution/autonomy/` infrastructure.
6. Add `run_peer_task_pipeline.py` as an operator facade with provider host
   preflight before Controller admission, then exact contract-bound probing and
   canonical Controller claim/prepare/render/start/record/verify/complete calls.
   It is not a scheduler.
7. Enforce thin-driver AST/schema gates across every routable execution kind;
   worker, verifier, remote-action, and deployment drivers own provider-specific
   translation/invocation only.
8. Update CANONICAL_LAW, active execution contracts, autonomy registry, peer
   contract, planning template, and accepted ADRs.

## Authority corrections

- `local_write` no longer implies `git add` or `git commit` in Claude tool
  permissions.
- dormant providers remain `BLOCKED` until an actual invocation transport is
  implemented, even if their CLI executable happens to exist.
- retry counts above one fail closed until canonical retry receipts are
  implemented in Peer Execution Core.
- provider/model observations remain telemetry, not Program semantics.
- canonical rendered-contract v2 no longer false-fails for omitting a duplicate
  authorization ceiling; the Controller remains the ceiling authority.
- permission profiles are enforced in shared Peer Execution Core before any provider
  is dispatched.
- persisted execution requests are rebound to contract/profile/context/budget state
  before poll or cancel, and dispatch intent is durable before provider invocation.
- empty verification gate sets cannot produce `PASSED_LOCAL`.
- runtime identifiers fail closed instead of being sanitized into colliding paths.
- worker execution profiles deny every remote, release, deployment, destructive,
  and external-message action class even when a future provider advertises one.
- context manifests reject symlinked runtime directories, use atomic durable writes,
  and refuse execution-ID reuse against a different contract.
- thin-provider instantiation executes each provider module once per load path.
- Controller `abort-execution` owns failure recovery, lease release, dirty-worktree
  preservation, and unrecorded Attempt Receipt quarantine for safe retry.
- Attempt Receipt persistence is atomic and confined to the active Controller
  workspace before any successful collect lifecycle receipt is emitted.
- pack application stages the complete change in an isolated detached worktree and
  applies one verified binary patch to the real target, rolling back on failure.

## DeepSeek

Deferred by design. Claude records whether it is running through the default or
custom Anthropic-compatible backend without persisting endpoint secrets. A
future DeepSeek configuration therefore does not require Program Controller or
canonical receipt changes.

## Validation

Run:

```bash
python3 <pack>/scripts/validate_applied_repo.py .
```

The validator covers thin-provider conformance, Program Execution adapter
validation, Program Execution conformance, peer-binding validation, autonomy
contracts, shared bounded-runtime validation, manifest integrity, pipeline CLI
loadability, and `git diff --check`.

Live provider probes remain environment-dependent and are intentionally reported
separately from structural conformance. Missing Ruff is reported as SKIPPED; when
the pinned Ruff 0.16.0 executable exists, lint/format failures remain blocking.

## Remote behavior

None. This pack does not create a branch, commit, push, PR, merge, release, or
deployment.
