# Program Execution authority remediation (compiled contract pack)

A compiled, validated, **unexecuted** remediation package for the seven
confirmed non-memory findings in `environment/program-execution/**`. It is
stored here as the plan of record; nothing in it has been run against the
repository.

The pack is kept **verbatim** as received apart from two recorded changes — a
removed duplicate compiler and a regenerated `.plan.md` kernel receipt, both
under *Excluded from the commit*. `MANIFEST.yaml` carries a SHA-256 for every
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

## Baseline

Rebound to `d6b30cdc0dd87213e972d61dd383b91a1b63d180` on 2026-08-29. The pack
originally pinned `5eff2cdb`, `main` moved past it, and 7 of the 32 paths the six
contracts name had changed content — including `pec/blueprint.py`, which PR-002
guarantees `behavior_unchanged` against, asserted over a version that was no
longer HEAD.

All seven findings were re-adjudicated by reading current source rather than
re-reading the prior ledger: **7/7 still CONFIRMED**, with current-source
locations per finding in `evidence/readjudication_d6b30cdc.yaml`. The chain was
recompiled against the new baseline — the `cold_resume` ancestry assertion is the
only remediation-content change, and no root cause, item, scope path, success
property or exclusion moved. Recompiled chain: 6/6 per-contract, chain PASS at
the same digest, regression 11/11.

**Still re-measure at execution start.** The recorded drift table is a snapshot
and `main` keeps moving; `todo-00-execution-preflight` and
`on_drift: stop_and_replan` exist for exactly that.

The compiler's execution model: one branch off `d6b30cdc…`, one validated local
commit per contract, `PR-001 → … → PR-006` in order, a fresh `preflight.sh` at
the start of every contract, no publication between contracts, and exactly one
terminal `make pr` after PR-006's commit. Merge is outside the chain.

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

The 19 files touched by the 2026-08-29 baseline rebind — `campaign-spec.yaml`,
the six contracts, and the six generated `CLAUDE.md` / `preflight.sh` pairs — no
longer match their `MANIFEST.yaml` entries either. `MANIFEST.yaml` is a record of
the original packaging run and is deliberately not rewritten: this repository has
no generator for its `canonical_self_zeroed` scheme, so hand-editing its hashes
would fabricate provenance. Verify those files against
`evidence/readjudication_d6b30cdc.yaml` and git history instead.

One further file is deliberately not byte-exact: the `.plan.md` projection. Its
packaged `kernel_pass` block recorded the packaging agent's own kernel runs,
hashed over that machine's exact bytes, and this repository's gate checks that
hash on every changed `*.plan.md` — so the file could not be both hygienic and
self-consistent while carrying a foreign receipt. The plan kernels were re-applied
here and a fresh `kernel_pass` written, which also folded the measured baseline
drift below into the plan's own *Immutable baseline* section. No root cause, todo,
DAG edge, success property or exclusion changed. See `RV-005`.

So manifest verification against this tree reports 42 hashes verified, 1
mismatched, 54 absent, and `MANIFEST.yaml` itself self-skipped — 42 + 1 + 54 + 1
= 98. Verify the compiler against the skill instead.
