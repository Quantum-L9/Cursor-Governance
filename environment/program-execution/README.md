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

For a long-form architecture document, the front door is:

```bash
make -C "$HOME/.cursor-governance" campaign-architecture \
  INTENT=<architecture.md> TARGET=<owner/repo>
```

`run_campaign.py` compiles seeds, admits the Blueprint, boots
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

## Campaign input routing (the front door)

`make campaign INTENT=<path>` classifies the input once, by content and schema
rather than by file extension, and then either routes it or refuses it. There is
no third outcome.

| Input | Route |
|---|---|
| `l9.program-execution.campaign-source.v2` | straight to `compile_campaign_source` → blueprint → PEC |
| `l9.program-execution.architecture-intent.v1` (declared, or `make campaign-architecture`) | architecture → campaign source → blueprint → PEC |
| activate seed (`campaign_id`, `title`, `objective`, `tasks`) | activate → campaign source → blueprint → PEC |
| brief memo (`.md`) | brief → activate → campaign source → blueprint → PEC |
| `program-execution.intent.v1` | **rejected** — design-time compiler input, no live adapter |
| anything else | **rejected** |

A supplied campaign source is written verbatim to the path the compiler reads.
It is never rebuilt through the activation compiler, because that regenerates it
from a weaker seed and drops task validations, dependencies, writable paths,
gates, evidence requirements, and authority data.

Classify without running anything:

```bash
make campaign-check-input INTENT=/path/to/CAMPAIGN_SOURCE.yaml
make campaign-check-input INTENT=/tmp/architecture.md ARCHITECTURE=1
```

### Long-form architecture intent

A dense operator document — an architecture design, a microscope audit, a
technical review, an implementation plan — compiles straight through:

```bash
make -C "$HOME/.cursor-governance" campaign-architecture \
  INTENT=/tmp/llm-router-microscope.md \
  TARGET=Quantum-L9/LLM-Router
```

No rewriting the architecture into releases, program ordering, numbered tasks,
an activate YAML, or a campaign source first. The document is segmented into
hashed source units, interpreted into a semantic IR whose every item must cite
and be grounded in the units it claims to read, audited for coverage, and
lowered into a full `campaign-source.v2` carrying `intent_provenance`. That
source then enters the same direct placement path an operator-supplied campaign
source uses — never brief → activate, which would rebuild it from a weaker
representation.

Two input modes: an unchanged assistant transcript passed to
`campaign-architecture` (the operator's choice of route is the signal), or a
document that declares `schema: l9.program-execution.architecture-intent.v1`
and `target:` in frontmatter and takes the ordinary `make campaign` route.
Unmarked Markdown handed to `make campaign` still goes to the brief compiler.

Every complete generated task is `definition_status: ready`; ordering is the
dependency graph, and a probeable open question becomes a ready read-only
evidence task with its dependents edged behind it (ADR-0023). Compilation fails
before any side effect when the source cannot be compiled at all — an
unreadable document, an unresolvable target, coverage that will not converge, a
contradiction of equal authority the source does not settle. It never mints a
Blueprint of BLOCKED tasks.

`compile_campaign_source.py` re-derives `intent_provenance` rather than trusting
it, so hand-deleting a mapped obligation from a generated campaign source fails
compilation instead of quietly shipping with a PASS coverage record attached.
Sources without `intent_provenance` are unaffected.

Details: `compiler/README.md`.

### Campaign ids are not preregistered

A campaign compiles because it is valid, not because its id appears in
`campaigns/COMPILE_ALLOWLIST.yaml`. That file is a historical ledger; nothing
admits against it, activation no longer patches it, and no campaign's compile
fingerprint depends on another campaign's registration. Id **collisions** are
still detected, from real state — existing campaign directories, the status
ledger, and the completed archive — which answers "does this id already exist",
never "is this id permitted to exist".

### When the front door rejects an input

Rejection happens before any worktree, blueprint, PEC state, or task exists, and
prints `PE_CAMPAIGN_INPUT_REJECTED` with the detected kind, the reason, the
supported kinds, `nothing_executed: true`, and the fix.

**That rejection is terminal for the invocation.** An agent that hits it must
stop and report `CAMPAIGN DID NOT START` with the failing command, the verbatim
error, the detected input type, why it is unsupported, the precise fix, and
confirmation that no private workaround was attempted.

Do not respond to a rejection by importing `run_campaign.py` and calling
`default_execute`, `default_arm`, `default_pec_bootstrap`, or any other
`default_*` stage function, and do not hand-reconstruct admission or execution.
Those are private helpers, not an API; composing them skips the routing the
front door exists to perform. Fix the input, or fix the router. Manual recovery
requires an explicit operator order.

## Fast path (execution productivity)

A campaign must start producing implementation work in minutes, not hours.
Preparation is bounded and, on a provisioned local repository, is expected to
reach the first executable task in well under 5 minutes.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md> CAMPAIGN_ARGS=--fast
# or, equivalently
L9_PE_MODE=fast make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md>
```

Fast mode relaxes **ceremony only**. Merge authority, publish authority,
writable-path restrictions, dependency correctness and controller verification
before completion are unchanged.

### Preparing an already-prepared campaign

Repeating `make campaign` for an id **resumes** it. The runtime is stepped aside
only when it did not come from the current inputs, so a repeat costs a fraction
of the first run and completed work survives:

- every preparation stage is fingerprint-keyed, and its reuse decision — or the
  reason it ran again — is recorded in `PREPARE_STATE.json` and printed next to
  the stage's duration
- arming renders contracts for the runnable frontier plus one wave of lookahead;
  the rest materialize on demand when a task is claimed
- editing a task's definition relocks that task (`pec relock`) instead of
  rebuilding the program. Changing the program body or the set of tasks is not
  absorbable and does rebuild
- in FAST mode a campaign that compiles and is launchable is accepted from local
  evidence, recorded in `LOCAL_ACCEPTANCE.json` as `authority: local_only`. That
  record is explicitly **not** sufficient for publish, merge or deploy, and no
  code path treats it as authority

Measured timings and the reasoning behind these choices are in
[`PREPARE_BASELINE.md`](PREPARE_BASELINE.md). Re-measure with:

```bash
.venv/bin/python environment/program-execution/scripts/tests/pe_prepare_bench.py --tasks 2 7 35
```

| Surface | What it does |
|---|---|
| `scripts/launchability.py` | Pre-bootstrap check that execution is possible at all; infers a validation command from repository convention when a task declares none |
| `scripts/pe_worker.py` | Worker handoff — renders the task brief and invokes `L9_PE_WORKER_CMD` so implementation tasks reach a worker before verification |
| `scripts/pe_timing.py` | Stage timings (`runtime/TIMINGS.json`), fingerprint-keyed reuse of preparation, and separated progress dimensions (`runtime/PROGRESS.json`) |
| `scripts/pe_prepare_state.py` | `PREPARE_STATE.json` — what preparation produced, from which inputs, and the recorded reason each stage was reused or ran again; also writes the FAST `LOCAL_ACCEPTANCE.json` provenance |
| `pec relock` | Adopts edited task definitions into a live runtime without discarding execution history |
| `pec/exec_env.py` | One resolved interpreter for worker-side and controller-side validation |
| `pec/workspace_reset.py` | `pec fresh-workspace` — idempotent recovery of task worktrees, registrations, branches and leases |

### Worker configuration

`L9_PE_WORKER_CMD` is a command template expanded with `{task_id}`,
`{worktree}` and `{brief}`; the same values also arrive as `L9_PE_TASK_ID`,
`L9_PE_WORKTREE`, `L9_PE_BRIEF` and `L9_PE_CONTRACT`. An implementation task
that reaches verification with an unmodified worktree fails as an
execution-path defect rather than verifying zero implementation. Tasks whose
`execution_kind` is an inspection kind (`analysis`, `inspection`, `decision`,
`program_control`, `review`) are exempt.

### Health check

```bash
make -C "$HOME/.cursor-governance" pe-smoke
```

The two-task smoke campaign runs a real worker end to end — compile →
launchability → admission → bootstrap → claim → worker handoff → modification
→ validation → verify → complete → dependency advance → TASK-002 — and then
again after a simulated interruption and reset. Run it first whenever a
campaign "prepares forever but never writes code".
