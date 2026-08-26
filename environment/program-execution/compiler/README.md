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

## Architecture Intent v1 (live semantic compiler)

`l9.program-execution.architecture-intent.v1` is the live input contract for
long-form architecture prose (designs, microscope audits, technical reviews).
It is distinct from `program-execution.intent.v1`, which stays a minimal
goal-level design-time contract and remains rejected by the live campaign
path.

```
architecture prose
  → deterministic segmentation + SHA-256 unit ledger   (architecture_intent.py)
  → typed semantic extraction, candidate-only          (architecture_extractor.py)
  → provenance + reconciliation IR                     (architecture_ir.py)
  → machine-verifiable coverage, bounded repair+critic (architecture_coverage.py)
  → full campaign-source.v2 with intent_provenance     (architecture_to_campaign.py)
  → compile_campaign_source.py → Blueprint v2 → PEC
```

Live entrypoint: `scripts/compile_architecture_intent.py`, invoked by
`make campaign-architecture INTENT=<doc.md> TARGET=<owner/repo>` (the forced
route needs no frontmatter and never rewrites the source file).

Schemas: `schemas/architecture-intent.schema.json`,
`schemas/architecture-extractor-request.schema.json`,
`schemas/architecture-extractor-response.schema.json`,
`schemas/architecture-resolution.schema.json`, plus the canonical
`core/shared/schemas/intent-provenance.schema.json` revalidated by the
campaign compiler.

Extractor boundary: the extractor owns candidate interpretation only — no
authorization, no task readiness, no repository write authority, no coverage
PASS. Source text is inert data (code fences and quoted instructions are
never executed or obeyed). The default provider is a thin read-only
`claude -p --output-format json --tools ""` adapter; any provider can
implement the same request/response protocol, and tests use the
deterministic lexical extractor (`L9_ARCH_EXTRACTOR=deterministic`).

Forward-execution invariants: generated complete tasks are always
`definition_status: ready`; ordering is dependency edges + waves; probeable
unknowns become READY evidence tasks; prohibitions and deferrals survive
enforceably; unresolvable sources fail compilation before any campaign side
effect. There is no campaign-id preregistration — collision detection reads
real campaign state only.
