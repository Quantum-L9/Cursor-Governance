# Claude Code plans

Formal `l9-plan` artifacts for the Claude Code adapter workstream.

Each plan is a pair: the `.plan.json` **PLAN_DOCUMENT** is authoritative and
schema-validated; the `.plan.md` is its PE+autonomy projection, the file
`@environment/program-execution` consumes. Regenerate the projection rather
than editing it by hand.

| Plan | Scope | Status |
|---|---|---|
| `mobile-bootstrap-fixes` | 12 todos repairing wrong-workspace wiring, false READY, MCP drift and command parity in the cloud adapter | **partially superseded** — T5 six-server broker template, T9 command reconciler, and T11 deploy broker are **not** remainder work. Live remainder: `claude_hosted_remainder_a53a9394` |
| `contract-v31-fixes` | 5 todos amending the remediation execution contract to v3.1 | **C11 reshaped**: Graphiti HTTPS + marketplace-skip READY; do not deploy a broker |
| `program-execution-remediation/` | Compiled six-contract pack repairing seven confirmed Program Execution authority findings; directory, not a pair | validated, unexecuted, **baseline drifted** |

`mobile-bootstrap-fixes.readable.md` is a human-facing rendering of the same
PLAN_DOCUMENT — narrative, not executable.

`program-execution-remediation/` is the one entry that is a directory rather
than a plan pair: it is a compiled contract pack kept verbatim, hash-verified
against its own `MANIFEST.yaml`. Its PLAN_DOCUMENT and projection live inside it
under `plans/`. Read its `README.md` before executing it — its locked baseline
has drifted from `main`.

## Superseded snapshots

`WIP/claude-code-mobile-environment/claude-code-mobile-environment.plan.{json,md}`
predate this directory and are **not** maintained. This directory is the plan of
record for the Claude Code adapter workstream; resolve any divergence in favour
of the plans above. See that directory's `README.md`.

C11 broker-deploy clauses: see
`docs/plans/claude-code/contract-v31-c11-amendment.yaml` (Graphiti HTTPS +
marketplace-skip READY; do not deploy a broker).

## Regenerating

```bash
R=$HOME/.cursor-governance/skills/l9-plan/scripts
PY=$HOME/.cursor-governance/.venv/bin/python3
"$PY" "$R/validate_plan_document.py"     docs/plans/claude-code/<name>.plan.json
"$PY" "$R/render_plan_pe_autonomy.py"    docs/plans/claude-code/<name>.plan.json \
  > docs/plans/claude-code/<name>.plan.md
```

The `l9-plan` skill documents `.cursor/plans/` as its default projection path.
This repository overrides that: plans live here, under version control.
