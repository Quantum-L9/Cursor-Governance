# Program Execution compiler module

Logical name: `l9-devpack-compiler`.

This directory is the in-tree compiler boundary for Program Execution. It is a
**module of this repository**, not a separate git repository.

Authority: `environment/program-execution/campaigns/PE_COMPILER_MODULE_ALIGNMENT.yaml`
(AUTH-001, 2026-08-14). Build contract:
`campaigns/cc-pe-intent-compiler-v1/CONTRACT_SOURCE.md` (Quality Gates A–F).

## Pipeline

```
NL goal → program-execution.intent.v1 → Intent Resolver → INTENT_RESOLUTION.yaml
        → Program Synthesizer → Blueprint v2 → official validation → Program Lock → RUN_REQUEST / Controller
```

The compiler emits **design-time definitions only**. The existing Program
Execution Controller remains the exclusive runtime authority for mutable
execution state, task attempts, verification results, gate results, leases,
recovery state, and handoff receipts.

## Components

| Component | File(s) | Contract |
| --- | --- | --- |
| Intent contract | `schemas/intent.schema.json` | §4, Gate A |
| Intent resolution IR | `schemas/intent-resolution.schema.json` | §5-§6, Gate B |
| Autonomy policy schema + profile | `schemas/autonomy-policy.schema.json`, `policies/quantum-l9.safe-autonomy.v1.yaml` | §7 |
| Intent parser | `intent.py` | §4 |
| Repository truth discovery (DPK-aware) | `repo_truth.py` | §8 |
| Policy loader + ceiling narrowing | `policy.py` | §7 |
| Intent Resolver | `resolver.py` | §5-§6 |
| Program action (create/extend/supersede) | `program_action.py` | §14 |
| Program Synthesizer | `synthesizer.py` | §9-§12, Gate C |
| Official validator adapter | `blueprint_validate.py` | §13, Gate D |
| Front door | `cli.py` | §15, Gate E |
| Test matrix (13 §18 scenarios) | `tests/` | §18, Gate F |

## Front door

```bash
PYTHONPATH=environment/program-execution python3 -m compiler.cli intent \
  "Evolve l9-devpack-compiler so I can give it a simple goal and it handles the full execution pipeline autonomously" \
  [--target <owner/repo>] [--repo-root <dir>] [--output <dir>]
```

Synthesized Blueprints default to `$HOME/.l9/blueprints/<program-id>` and are
validated with the official Blueprint v2 validator
(`core/program-execution-blueprint-template/scripts/validate_blueprint.py`)
in `--mode instantiated` before the "prepared for lock" verdict.

## Must not own

- Mutable Program runtime, leases, attempts, gate results, or handoff receipts
- A second Controller or scheduler
- Peer-local policy or adapter-owned semantics

## Campaigns

| Campaign | Role |
| --- | --- |
| `cc-pe-intent-compiler-v1` | Build this module from `CONTRACT_SOURCE.md` |
| `l9-devpack-program-execution-hardening` | Harden this same module (provenance, proof semantics, PE v2 projection) |
