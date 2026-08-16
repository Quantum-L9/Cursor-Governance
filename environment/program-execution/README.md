# Program Execution

Program Execution is the serial authority plane for executable programs. Peer
and model providers connect through one shared Peer Execution Core.

- `core/`: Program truth, Program Locks, readiness, leases, task state,
  verification, canonical receipts, and convergence.
- `peer_execution/`: canonical provider request/result contracts, context,
  profiles, permissions, lifecycle, shared transports, telemetry evidence, and
  terminal receipt normalization.
- `adapters/`: thin provider or external-system translation only.
- `integrations/`: bridges to existing runtimes without copying authority.
- `registry/`: provider registry, execution profiles, routing, concurrency,
  health, and failover.
- `conformance/`: fail-closed architecture and behavioral checks.
- `campaigns/`: immutable campaign seeds plus landing policy
  (`CAMPAIGN_EXECUTION_POLICY.yaml` — one integration branch per campaign;
  `PR_REMEDIATE=0 make pr`; no remediate; no merge; no PRs against `main`).

Canonical peer topology lives only in
`environment/agents/PEER_RUNTIME_BINDINGS.yaml`:

```text
agent_ref + surface -> provider_ref + execution_profile_ref
```

A provider descriptor is identity-neutral. It MUST NOT carry `agent_ref`, own
Program state, author policy defaults, construct canonical receipts, or copy
scheduler/autonomy/memory behavior.

The binding law is registered at
`environment/contracts/execution/PEER_EXECUTION_THIN_ADAPTER_LAW.yaml`.

Mutable runtime belongs under `$HOME/.l9/`, never this source tree.

## Campaign front door

The only live campaign path is:

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` compiles allowlisted seeds, admits the Blueprint, boots
pec without a draft flag, executes every task, stacks PRs, and closes into
`campaigns/COMPLETED/<id>/`. Do not call `compile_campaign_source.py`,
`pec bootstrap`, or `program-execution intent` as a substitute.
`--admission-draft` is not a live path (`L9_ALLOW_ADMISSION_DRAFT=1` is
controller unit tests only). Host-only merge is not program close.

`git` and `git_repo_adapter` are campaign target tokens only. pec
reconcile binds `repository_id` to a local path. They are not worker
adapters and must not be added to `EXECUTION_ADAPTER_REGISTRY.yaml`.

Cursor and ChatGPT file-drop / handoff results never become PASS unless
the host payload carries `status: PASS`. Cursor file-drop probes stay
BLOCKED. Claude probes stay BLOCKED when the `claude` executable is
absent. DeepSeek is not a Program Execution provider.

Claude `backend_mode` and `model_hint` are probe evidence only.
