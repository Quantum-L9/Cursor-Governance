# Claude Code plans

Formal `l9-plan` artifacts for the Claude Code adapter workstream.

Each plan is a pair: the `.plan.json` **PLAN_DOCUMENT** is authoritative and
schema-validated; the `.plan.md` is its PE+autonomy projection, the file
`@environment/program-execution` consumes. Regenerate the projection rather
than editing it by hand.

| Plan | Scope | Status |
|---|---|---|
| `mobile-bootstrap-fixes` | 12 todos repairing wrong-workspace wiring, false READY, MCP drift and command parity in the cloud adapter | validated, unexecuted |
| `contract-v31-fixes` | 5 todos amending the remediation execution contract to v3.1 — partial-run safety, measured self-heal budget, and three C11 defects | validated, unexecuted |

`mobile-bootstrap-fixes.readable.md` is a human-facing rendering of the same
PLAN_DOCUMENT — narrative, not executable.

## Superseded snapshots

`WIP/claude-code-mobile-environment/claude-code-mobile-environment.plan.{json,md}`
predate this directory and are **not** maintained. This directory is the plan of
record for the Claude Code adapter workstream; resolve any divergence in favour
of the plans above. See that directory's `README.md`.

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
