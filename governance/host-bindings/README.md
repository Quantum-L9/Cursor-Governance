# Host bindings — what every session is bound to at startup

Each file here is one host's **default projection binding**: the projections every
session of that host is bound to automatically, at SessionStart, with no skill, command
or opt-in. The binding changes what a session reads, never what it may do.

| File | Host | Binds by default |
|---|---|---|
| `cursor.yaml` | Cursor | the operating plane, plus the canonical Cursor domain set (`l9.domain-consumer-binding/cursor@1`) |
| `claude-code.yaml` | Claude Code (both surfaces: CLI and web) | the operating plane, plus the coding-agent execution projection (`l9.projection/coding-agent-execution@1`) |

The operating plane is `l9.projection/cursor-governance-operating-plane@2`. Everything
else is bound only by hand, per session: `/coding-agent`, `/lcto`, `/architect`,
`/planner` (each contract's `session_start.manual_bindings`).

Claude Code binds the coding-agent execution projection by default by operator decision
(2026-11-20). That is a host binding, not a default-on mode: modes stay opt-in
(`ops/autonomy/projection_mode.py` `MODE_MUST_BE_OPT_IN`), and a registered `/lcto` swarm
child still turns coding-agent mode ACTIVE itself — the host default never satisfies
`ops/autonomy/coding_agent_binding_gate.py`. If the projection is not
`ADMITTED_AND_CURRENT`, the session is `DEGRADED` to the operating plane alone with one
`WARN:` line, and never blocked.

## How it works

- `governance/host-bindings/<host>.yaml` holds the binding: the required base (the
  operating plane, with its binding and consumer adapter) and the domain projections with
  their activation (`always`, `hosted_skill_requirement`,
  `explicit_task_requirement`).
- `ops/autonomy/host_binding.py` checks it with the verifiers that already exist; it adds
  no checking of its own.
  - The base is checked by its own consumer adapter,
    `ops/scripts/operating_plane_v2_projection.py`, in admitted mode.
  - Each domain is checked by the verifier its binding names, read by the same
    `projection_mode` helpers the manual modes use: a domain binding through
    `skills/l9-global-architect/scripts/verify_architecture_intelligence.py` (over the
    shared `skills/l9-coding-agent/scripts/verify_canonical_binding.py`), the coding-agent
    execution binding through its status reader `ops/scripts/coding_projection_status.py`.
  - A conditional projection is loaded only when its condition is named with
    `--activate`; otherwise it is not even checked.
- Every contract must declare `session_start.autobind: true` and
  `depends_on_skill: false`, or it is rejected. A skill can never gate the default
  binding.
- Both hosts' SessionStart hooks call it directly:
  - Cursor (`ops/hooks/session_start_bootstrap.sh`): `--host cursor --format markdown`,
    as the `### default projection binding (cursor)` block. It replaced the old
    report-only operating-plane block, so the adapter runs once. 30 s limit inside the
    60 s hook; it took about 9 s against an authority checkout at `main` in testing.
  - Claude Code
    (`environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`,
    mirrored to `.claude/hooks/`): `--host claude-code --format line`, inside the
    hook's own time budget. With the coding projection it took about 6 s in testing; the
    separate `coding projection:` line no longer runs the classifier a second time.

### What the status means

Each status is reported only with the proof named:

| Status | When | What is bound |
|---|---|---|
| `BOUND` | the base is `CURRENT` and every activated domain is `ADMITTED_AND_CURRENT` | everything listed |
| `DEGRADED` | the base is `CURRENT`, at least one activated domain is not | the base and the domains that verified; each failed one gets one `WARN: … NOT BOUND` line with its reason |
| `NOT_BOUND` | the base is not `CURRENT`, or its adapter could not be run | nothing; admitted domains are not bound without the base |
| `REJECTED` | the contract or an activation is malformed | nothing |

When the base is bound, the session is told its eight source classes and the exact
command that releases one (`operating_plane_v2_projection.py --mode admitted
--source-class <class>`, pinned to the authority checkout it was verified against). The
adapter re-verifies before it releases anything; projection content is never pasted
into context up front. A bound domain is listed with the view(s) to read: a domain
binding's composed view, or the coding projection's three source-class views.

### Fail-open and honest

- A binding that failed, degraded, timed out or was deferred never stops the session.
- It is reported as exactly that: `NOT BOUND — ... (fail-open: the session continues;
  cite no operating-plane semantics)`. Nothing that did not verify is ever shown as
  `BOUND`.
- The markdown and line renderings exit 0 even if `host_binding.py` itself raises
  (`HOST_BINDING_ERROR`). The hooks print the same `NOT BOUND` line when the module is
  missing, the interpreter is unresolved, it times out, or it prints nothing.
- The separate `coding projection:` line differs per host. Cursor's is verification only
  and says so: `not bound in this session — /coding-agent binds it`. Claude Code's points
  at the default binding, which verifies and binds it (`bound by default for Claude Code`).

### Authority checkout

Admission is resolved against a `Quantum-L9/.github` checkout: `--authority-root`, then
`L9_AUTHORITY_ROOT`, then the governance-managed checkout `~/.l9/authority/.github`
(relocate with `L9_AUTHORITY_MANAGED_ROOT`), then `.github` inside or beside the workspace.
Both SessionStart hooks provision the managed checkout before binding
(`ops/scripts/ensure_authority_checkout.sh`: full clone, fetched at most every 900 s,
fast-forward only on a clean `main`, never reset or deleted), so the binding resolves the
same authority in every repository instead of only where a `.github` clone happens to sit
beside the workspace. Domain verifiers read `origin/main` from a detached snapshot of
that checkout (`pinned_checkout`, the same snapshot the operating plane uses). The
clone's branch and dirty tree stay untouched, so a checkout that is not on `main` does
not make the domains `STALE`.

## Run it by hand

```bash
"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/host_binding.py" \
  --host cursor --workspace "$PWD" --format json        # exit 0 BOUND, 3 DEGRADED/NOT_BOUND, 1 REJECTED
"$HOME/.cursor-governance/.venv/bin/python" "$HOME/.cursor-governance/ops/autonomy/host_binding.py" \
  --host cursor --activate hosted_skill_requirement --format markdown
```

## Changing a binding

Edit the host's YAML. Every projection it names must already have a binding under
`governance/projection-bindings/` (or `governance/authority-bindings/`) and a committed,
verified bundle under `generated/governance/`. Tests: `tests/ops/autonomy/test_host_binding.py`.
