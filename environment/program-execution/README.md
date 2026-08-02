# Program Execution (`environment/program-execution/`)

Subsystem ownership boundary for the multi-repository **Program Execution
System** inside Cursor-Governance. This tree is the active home for the sealed
core pack and for the replaceable peripherals that will bind it to host
runtimes.

## Layout

```text
environment/program-execution/
├── README.md                         # this file — subsystem ownership boundary
├── core/                             # sealed Program Execution System (v2)
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── COMPATIBILITY.yaml
│   ├── CANONICAL_VOCABULARY.yaml
│   ├── MANIFEST.yaml
│   ├── shared/
│   ├── scripts/
│   ├── tests/
│   ├── validation/
│   ├── program-execution-blueprint-template/
│   └── program-execution-controller-template/
├── adapters/                         # future replaceable peripherals
├── conformance/                      # shared adapter conformance suite
├── registry/                         # adapter discovery and routing
├── integrations/                     # wrappers over existing runtimes
└── fixtures/                         # cross-adapter contract fixtures
```

## What lives where

| Path | Role |
|---|---|
| `core/` | Sealed Program Execution System pack. Blueprint + Controller templates, shared contracts, validators. Relocatable as a whole; **do not rename** internal siblings without a deliberate contract migration. |
| `adapters/` | Replaceable host/runtime peripherals (empty until first adapter lands). |
| `conformance/` | Shared adapter conformance suite against `core/` contracts. |
| `registry/` | Adapter discovery and routing. |
| `integrations/` | Thin wrappers over existing runtimes (e.g. Claude Code autonomy) — subordinate, not overwritten. |
| `fixtures/` | Cross-adapter contract fixtures. |

## Installation invariant

The pack unpacks **into** `core/`, not under a packaging wrapper:

- Correct: `environment/program-execution/core/README.md`
- Wrong: `environment/program-execution/core/program-execution-system-v2.0.0/`

Preserve these internal directory names on first install (validators and relative
references expect them as siblings):

- `program-execution-blueprint-template/`
- `program-execution-controller-template/`

## Why this location

**Not repository root.** Putting the pack at the Cursor-Governance root would
flood the governance namespace and blur Cursor-Governance itself, the Program
Execution System, and deployed Execution Programs.

**Not `execution-governance/`.** That tree is supporting / in-progress material,
not the primary source-of-truth boundary. `environment/` is the active home for
runtime environments and target-specific adapters.

**Not `environment/claude-code/autonomy/`.** That runtime owns bounded,
host-specific Claude Code campaigns (dependency readiness, locks, leases,
worktrees, durable state, fan-in assurance, exact-SHA merge eligibility). It
becomes a **subordinate adapter target** under `integrations/` / `adapters/`,
not something the Program Execution Controller overwrites.

## Start here

1. Read [`core/README.md`](core/README.md) and [`core/ARCHITECTURE.md`](core/ARCHITECTURE.md).
2. Shared laws: `core/shared/` (especially `INTERFACE_CONTRACT.md`).
3. Validate the sealed pack:

```bash
python environment/program-execution/core/scripts/validate_pair.py \
  environment/program-execution/core --mode template
```
