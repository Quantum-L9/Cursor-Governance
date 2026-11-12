# Host bindings — what every session is bound to at startup

Each file here is one host's **default projection binding**: the projections every
session of that host is bound to automatically, at SessionStart, with no skill, command
or opt-in. The binding changes what a session reads, never what it may do.

| File | Host | Binds by default |
|---|---|---|
| `cursor.yaml` | Cursor | the operating plane, plus the canonical Cursor domain set (`l9.domain-consumer-binding/cursor@1`) |
| `claude-code.yaml` | Claude Code (CLI, desktop, IDE, web, mobile) | the operating plane alone |

The operating plane is `l9.projection/cursor-governance-operating-plane@2`. Everything
else is bound only by hand, per session: `/coding-agent`, `/lcto`, `/architect`.

## How it works

- `governance/host-bindings/<host>.yaml` holds the binding: the required base (the
  operating plane, with its binding and consumer adapter) and, for Cursor, the domain
  projections with their activation (`always`, `hosted_skill_requirement`,
  `explicit_task_requirement`).
- `ops/autonomy/host_binding.py` checks it with the verifiers that already exist; it adds
  no checking of its own.
  - The base is checked by its own consumer adapter,
    `ops/scripts/operating_plane_v2_projection.py`, in admitted mode.
  - Each domain is checked by the verifier its binding names
    (`skills/l9-global-architect/scripts/verify_architecture_intelligence.py`, over the
    shared `skills/l9-coding-agent/scripts/verify_canonical_binding.py`).
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
    hook's own time budget. It took about 6 s in testing.

### What the status means

Each status is reported only with the proof named:

| Status | When | What is bound |
|---|---|---|
| `BOUND` | the base is `CURRENT` and every activated domain is `ADMITTED_AND_CURRENT` | everything listed |
| `DEGRADED` | the base is `CURRENT`, at least one activated domain is not | the base and the domains that verified; each failed one is marked `NOT BOUND` with its reason |
| `NOT_BOUND` | the base is not `CURRENT`, or its adapter could not be run | nothing; admitted domains are not bound without the base |
| `REJECTED` | the contract or an activation is malformed | nothing |

When the base is bound, the session is told its eight source classes and the exact
command that releases one (`operating_plane_v2_projection.py --mode admitted
--source-class <class>`, pinned to the authority checkout it was verified against). The
adapter re-verifies before it releases anything; projection content is never pasted
into context up front. A bound domain is listed with its composed view to read.

### Fail-open and honest

- A binding that failed, degraded, timed out or was deferred never stops the session.
- It is reported as exactly that: `NOT BOUND — ... (fail-open: the session continues;
  cite no operating-plane semantics)`. Nothing that did not verify is ever shown as
  `BOUND`.
- The markdown and line renderings exit 0 even if `host_binding.py` itself raises
  (`HOST_BINDING_ERROR`). The hooks print the same `NOT BOUND` line when the module is
  missing, the interpreter is unresolved, it times out, or it prints nothing.
- The separate `coding projection:` line at startup is verification only. It says so:
  `not bound in this session — /coding-agent binds it`.

### Authority checkout

Admission is resolved against a `Quantum-L9/.github` checkout: `--authority-root`, then
`L9_AUTHORITY_ROOT`, then `.github` inside or beside the workspace. The domain verifiers
need that checkout's `HEAD` to be its `main`; a checkout left on another branch makes the
domains `STALE` (`AUTHORITY_REVISION_MISMATCH`) and the Cursor binding `DEGRADED`, while
the operating plane still binds.

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
