# Program Execution authority remediation (compiled contract pack)

A compiled, validated, **unexecuted** remediation package for the seven
confirmed non-memory findings in `environment/program-execution/**`. It is
stored here as the plan of record; nothing in it has been run against the
repository.

The pack is kept **verbatim** as received, with one deliberate removal (see
*Excluded from the commit*). `MANIFEST.yaml` carries a SHA-256 for every
artifact and those hashes are checked against this tree, so do not reformat,
rename, or regenerate files inside it. Amendments belong in a new compiled pack,
not in edits here.

## What is in it

| Path | Role |
|---|---|
| `plans/program_execution_remediation_plan.json` | PLAN_DOCUMENT — authoritative, schema-validated |
| `plans/..._d681ee05.plan.md` | PE+autonomy projection of that PLAN_DOCUMENT |
| `claude-code-contracts/campaign-spec.yaml` | Canonical compiler input |
| `claude-code-contracts/emitted/PR-00{1..6}.contract.json` | The six compiled contract instances |
| `claude-code-contracts/artifacts/PR-00N/…` | Per-contract `preflight.sh`, `CLAUDE.md`, `.claude/settings.json` |
| `claude-code-contracts/validation/` | The packaging run's own validation output |
| `evidence/` | Finding ledger, root-cause matrix, current-state delta, kernel receipt |
| `validation-receipts/independent-revalidation.yaml` | This repository's independent re-run of every gate |
| `RUNBOOK.md` | Operator handoff. Not execution authority — the PLAN_DOCUMENT is. |

The compiler is **not** in here. `skills/l9-claude-coding-contract-compiler`
(v2.7.0) is the compiler of record for this pack — see below.

## Validation status

Every gate the pack declares was re-executed here rather than taken on trust,
and all of them reproduce: compiler regression suite 11/11, per-contract
validation 6/6, chain validation PASS at digest
`sha256:4d340ed5…41c2b3`, deterministic recompile byte-identical, and all 97
raw manifest hashes verified against the pack as received. The repository's own
`l9-plan` 4.1.0 validators also pass on the PLAN_DOCUMENT and the kernel receipt.

Each of those gates was then run a **second** time using
`skills/l9-claude-coding-contract-compiler` instead of the compiler the pack
shipped. Both agree on everything that matters: same 11/11, same 6/6, same chain
digest, and all six contract JSONs byte-identical. The only difference anywhere
is one provenance comment line per generated `CLAUDE.md` and `preflight.sh`
naming the emitting pack. That equivalence is what makes the repo skill a sound
substitute, and it is why the pack's bundled copy is not committed.

To revalidate or recompile:

```bash
PY=$HOME/.cursor-governance/.venv/bin/python
C=$HOME/.cursor-governance/skills/l9-claude-coding-contract-compiler/scripts
cd docs/plans/claude-code/program-execution-remediation/claude-code-contracts
$PY "$C/validate_chain.py" emitted/PR-00{1,2,3,4,5,6}.contract.json
```

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

`MANIFEST.yaml` declares 98 artifacts; 44 are committed. All 54 omissions are
under `claude-code-contracts/compiler-runtime/`, and nothing outside that
directory is missing:

- **49 compiler files.** The pack bundled a complete
  `claude-coding-contract-compiler` v2.7.0 — its own `SKILL.md`, `agents/`,
  `references/`, `schemas/` and `scripts/`. This repository already owns that
  compiler at the same version as `skills/l9-claude-coding-contract-compiler`,
  and the repository's copy is the hardened one: ruff-clean imports plus a
  `_sibling()` importer fixing a real `sys.modules` basename collision between
  skill packs. Committing the pack's copy would have put a second `SKILL.md` and
  a second authority corpus for one tool under `docs/`. It was removed after the
  equivalence above was proven, not before.
- **5 `.pyc` files** — `compiler-runtime/scripts/__pycache__/*.cpython-313.pyc`,
  packaging-machine bytecode caught by this repository's `.gitignore`.

So manifest verification against this tree reports 43 hashes verified, 0
mismatched, 54 absent, and `MANIFEST.yaml` itself self-skipped — 43 + 54 + 1 =
98. Verify the compiler against the skill instead.
