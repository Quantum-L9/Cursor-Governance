# Program Execution authority remediation (compiled contract pack)

A compiled, validated, **unexecuted** remediation package for the seven
confirmed non-memory findings in `environment/program-execution/**`. It is
stored here as the plan of record; nothing in it has been run against the
repository.

The pack is kept **verbatim** as received. `MANIFEST.yaml` carries a SHA-256 for
every artifact and those hashes are checked against this tree, so do not
reformat, rename, or regenerate files inside it. Amendments belong in a new
compiled pack, not in edits here.

## What is in it

| Path | Role |
|---|---|
| `plans/program_execution_remediation_plan.json` | PLAN_DOCUMENT — authoritative, schema-validated |
| `plans/..._d681ee05.plan.md` | PE+autonomy projection of that PLAN_DOCUMENT |
| `claude-code-contracts/campaign-spec.yaml` | Canonical compiler input |
| `claude-code-contracts/emitted/PR-00{1..6}.contract.json` | The six compiled contract instances |
| `claude-code-contracts/artifacts/PR-00N/…` | Per-contract `preflight.sh`, `CLAUDE.md`, `.claude/settings.json` |
| `claude-code-contracts/compiler-runtime/` | `claude-coding-contract-compiler` v2.7.0, as loaded |
| `claude-code-contracts/validation/` | The packaging run's own validation output |
| `evidence/` | Finding ledger, root-cause matrix, current-state delta, kernel receipt |
| `validation-receipts/independent-revalidation.yaml` | This repository's independent re-run of every gate |
| `RUNBOOK.md` | Operator handoff. Not execution authority — the PLAN_DOCUMENT is. |

## Validation status

Every gate the pack declares was re-executed here rather than taken on trust,
and all of them reproduce: compiler regression suite 11/11, per-contract
validation 6/6, chain validation PASS at digest
`sha256:4d340ed5…41c2b3`, deterministic recompile byte-identical, and all 97
raw manifest hashes verified. The repository's own `l9-plan` 4.1.0 validators
also pass on the PLAN_DOCUMENT and the kernel receipt.

Full detail, including the interpreter used and three recorded findings, is in
`validation-receipts/independent-revalidation.yaml`.

## Before executing it — read this

**The pack is not executable as-is.** It pins baseline
`5eff2cdb27d709d37a9ee79fe8c2bc42515ff19d`, which `main` has since moved past.
Seven of the thirty-two paths named across the six contracts changed content
between that baseline and current `HEAD` — including
`scripts/run_campaign.py`, `pec/controller.py`, `scripts/run_peer_task_pipeline.py`,
and `pec/blueprint.py`, which PR-002 asserts is `behavior_unchanged` against a
version that is no longer HEAD.

The pack's own RUNBOOK requires stop/replan on material current-state drift, so
re-adjudicate the seven findings against current `main` and recompile before
running contract 1. That is finding `RV-001` in the receipt.

The compiler's execution model, once a recompiled pack is current: one branch,
one validated local commit per contract, `PR-001 → … → PR-006` in order, a fresh
`preflight.sh` run at the start of every contract, no publication between
contracts, and exactly one terminal `make pr` after PR-006's commit. Merge is
outside the chain.

## Excluded from the commit

`MANIFEST.yaml` declares 98 artifacts; 93 are committed. The five omitted are
`compiler-runtime/scripts/__pycache__/*.cpython-313.pyc` — packaging-machine
bytecode caught by this repository's `.gitignore`. Every one is compiled output
of a `.py` source that is committed, so no content is missing.
