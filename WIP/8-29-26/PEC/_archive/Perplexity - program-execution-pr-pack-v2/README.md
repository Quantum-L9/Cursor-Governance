# Program Execution PR Pack (v2 — gap-closure pass)

Target: `Quantum-L9/Cursor-Governance` (base branch `main`)

This is a revised pack addressing four gaps identified in a prior gap
analysis of the original pack:

- **Gap 1 (external configuration / token scope)** — `RUNBOOK.md` now
  includes a full token/permission matrix so an automation agent knows
  exactly what scope each step needs, and which two steps (GitHub ruleset
  apply, merge-queue toggle) require human-approved `administration:write`.
- **Gap 2 (deferred integration edits)** — `RUNBOOK.md` now gives literal
  append/modify snippets for every existing repo file that needs wiring
  (`ORG_INVARIANTS.yaml`, `COMMANDS_MANIFEST.yaml`, `CODEOWNERS`,
  `Makefile`, `.pre-commit-config.yaml`, `l9-lint-test.yml`,
  `TRUST_MODEL.md`) rather than just naming them as future work.
- **Gap 3 (missing wiring inside the pack)** — closed with new files this
  turn: `ops/lib/telemetry.py` (tested in-process emitter),
  `wiring/ob-010-instrumentation-diffs.md` (exact call-site diffs),
  7 real `semantic_contracts/*.yaml` files, a real
  `test_impact_map.v1.yaml`, and `deploy-with-provenance-gate.yml` (wires
  `verify_provenance.py` into an actual deploy gate).
- **Gap 4 (conceptual-only items)** — deferred to next turn per request.

## What's new vs. the previous pack

| New file | Closes |
|---|---|
| `ops/lib/telemetry.py` + `tests/tools/test_telemetry.py` | OB-010 had no in-process emitter; script-only version required a subprocess per event |
| `wiring/ob-010-instrumentation-diffs.md` | No tool file actually called the emitter |
| `reports/latest/semantic_contracts/*.yaml` (7 files) | `semantic_merge_probe.py` had no real contracts to consume |
| `reports/latest/test_impact_map.v1.yaml` | `select_impacted_tests.py` always fell back to full suite |
| `.github/workflows/deploy-with-provenance-gate.yml` | `verify_provenance.py` was never called from anywhere |

## How to use this pack

1. Read `RUNBOOK.md` — it now embeds the token matrix (Gap 1) directly
   above the numbered steps, and each step that touches an existing file
   gives the literal snippet to append (Gap 2).
2. Unzip into a fresh branch off `main`, add the files for the node you're
   activating, commit, open a PR.
3. Apply `wiring/ob-010-instrumentation-diffs.md` when you reach step 7 —
   it's a set of 4 small, additive diffs against files this pack already
   shipped, not new files.
4. `MANIFEST.json` lists all 68 files with per-file checksums and the
   validation performed before packaging.

## Validation before packaging

- All Python files compile clean; all YAML/JSON parse clean (one real
  bug — a malformed inline mapping in `artifact-provenance.yml` — was
  found and fixed during this pass).
- 10 pytest tests pass, including a new telemetry test suite that caught
  and fixed a real schema bug (`agent_id` incorrectly required as
  non-null string).
- The policy-generator round-trips with zero drift; the merge-queue
  checker correctly fails/passes based on batch dependency completeness.

See `MANIFEST.json` for the full file list and `RUNBOOK.md` for the
token matrix and wiring instructions.
