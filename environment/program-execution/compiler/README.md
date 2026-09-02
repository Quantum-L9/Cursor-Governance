# Program Execution compiler module

Logical name: `l9-devpack-compiler`.

This directory is the in-tree compiler boundary for Program Execution. It is a
**module of this repository**, not a separate git repository.

Authority: `environment/program-execution/campaigns/PE_COMPILER_MODULE_ALIGNMENT.yaml`
(AUTH-001, 2026-08-14). Build contract:
`campaigns/cc-pe-intent-compiler-v1/CONTRACT_SOURCE.md` (Quality Gates A–F).

## Two input contracts, deliberately not one

| Contract | Shape | Route |
| --- | --- | --- |
| `program-execution.intent.v1` | a **minimal** goal: one objective, optional targets and policy. Prescribing tasks, files, waves, or worker prompts is a schema violation. | design-time: Intent Resolver → Synthesizer |
| `l9.program-execution.architecture-intent.v1` | a **dense** operator document: architecture design, microscope audit, technical review, implementation plan. Prose, tables, code fences, deferrals, tests. | live: architecture → campaign-source.v2 → Blueprint → PEC |

They are opposite problems and share no schema. Widening the minimal intent to
accept task lists would destroy the property that makes it useful, and asking an
operator to boil a 2,000-line audit down to one sentence destroys everything the
audit said. So the architecture route is its own contract end to end.

## Pipeline

```
NL goal → program-execution.intent.v1 → Intent Resolver → INTENT_RESOLUTION.yaml
        → Program Synthesizer → Blueprint v2 → official validation → Program Lock → RUN_REQUEST / Controller
```

The compiler emits **design-time definitions only**. The existing Program
Execution Controller remains the exclusive runtime authority for mutable
execution state, task attempts, verification results, gate results, leases,
recovery state, and handoff receipts.

## Mission-bound pipeline

A Program Intent may be admitted under a Mission. When it is, the same pipeline
runs with one extra input and two extra outputs:

```
parsed Mission Revision  +  explicit Program Intent
        → Mission Admission                      mission_admission.py
        → Intent Resolver                        resolver.py
              effective[action] =
                  existing_ceiling[action] AND mission_ceiling[action]
        → INTENT_RESOLUTION.yaml + mission_context
        → Program Synthesizer                    synthesizer.py
              Blueprint artifacts
              MISSION_CONTEXT.yaml                ← before the manifest
              canonical MANIFEST.yaml finalized
        → official instantiated-Blueprint validation
        → blueprint_digest = SHA-256(exact MANIFEST.yaml bytes)
        → Mission Program Binding                 mission_binding.py
              written OUTSIDE the Blueprint root
        → prepared for lock
```

An **unbound** Program Intent takes the ordinary path above, unchanged: no
Mission context file, no Mission provenance, no behavioural difference.

### The four orderings that are not decorative

| Ordering | Why |
| --- | --- |
| Admission receives an *explicit* Program Intent | Nothing here decomposes a Mission into Programs, so nothing can invent one |
| `MISSION_CONTEXT.yaml` before `MANIFEST.yaml` | The manifest inventories every file but itself; a context written after it is uncovered, and the validator rejects that |
| Official validation before `blueprint_digest` | An invalid Blueprint has no admissible identity, so there is nothing for a binding to pin |
| Binding after the digest, and outside the Blueprint | The binding names `blueprint_digest`; storing it inside would make Blueprint identity depend on a document naming that identity (ADR-0026) |

### Mission narrows, never widens

The Mission ceiling is intersected with the ceiling the policy profile and the
Program Intent already produced. `AND` can only clear bits, so a Mission
declaring `push: true` cannot hand a Program push authority the profile
withheld — widening is structurally impossible rather than merely checked.

### What the Mission context is, and is not

`MISSION_CONTEXT.yaml` carries exactly `schema`, `mission_id`,
`mission_revision`, and `mission_digest`
(`schemas/mission-context.schema.json`, closed to additional properties). It is
provenance: it says *which exact Mission Revision admitted this Program* so a
reader can fetch the Mission itself. Mission objective, acceptance criteria,
authority ceiling, budgets, constraints, scope, lifecycle, and owner are
deliberately absent — a copy of Mission semantics inside a Blueprint is a second
source of Mission truth, and supersession cannot correct a copy.

Mission identity is read off the parsed `Mission` at every step, never off a
caller argument, so a Program cannot claim a Mission it was not admitted to.
Blueprint identity comes from the single shared implementation,
`../core/shared/blueprint_identity.py`.

### Still deferred, and said so rather than implied

Program Lock Mission binding import; Controller Mission projection and any
Controller lookup of live Mission state; `make campaign` and compiler front-door
(`cli.py`) wiring; autonomous Mission-to-Program decomposition; the aggregate
Mission budget ledger that `max_programs`, `max_parallel_programs`, cost,
tokens, gate calls, and duration would need; the semantic Mission scope-subset
engine, which has no machine selector grammar to check against; and every
Mission runtime construct — Controller, Scheduler, Lease, Work Item, Task State.

## Architecture route

```
architecture prose
    → normalize / hash / segment          architecture_intent.py
    → candidate semantic extraction        architecture_extractor.py
    → provenance + grounding admission     architecture_ir.py
    → coverage audit, critic, repair       architecture_coverage.py
    → campaign-source.v2 + provenance      architecture_to_campaign.py
    → Blueprint v2 → PEC → execute         scripts/compile_campaign_source.py
```

Operator entry:

```bash
make -C "$HOME/.cursor-governance" campaign-architecture \
  INTENT=/tmp/llm-router-microscope.md \
  TARGET=Quantum-L9/LLM-Router
```

The document needs no edits. A document that declares its own frontmatter
(`schema: l9.program-execution.architecture-intent.v1`, `target: owner/repo`)
takes the ordinary `make campaign` route instead. Unmarked Markdown handed to
`make campaign` still goes to the brief compiler — this route never steals
generic memo traffic.

### What is authority and what is not

| Layer | Owns | Never owns |
| --- | --- | --- |
| Source units | what the document says, addressably | interpretation |
| Extractor (LLM or lexical) | candidate interpretation | authority, coverage PASS, write access |
| Admission + grounding | which candidates the source vouches for | what the candidate means |
| Coverage audit | whether anything material fell out | repairing it |
| Lowering | campaign constructs and their ordering | inventing obligations |

An extracted item enters the campaign only if it cites source units that exist
*and* its statement is grounded in the text of those units. A fluent invention
that cites a real unit id shares the id but not the vocabulary, and dies at
admission. Confidence is reported and consulted nowhere.

### Forward progress

Every complete generated task is `definition_status: ready` (ADR-0023).
Ordering is `dependencies`, `dependency_edges`, `waves`, and gates. A probeable
open question ("we need to determine whether …") becomes a **ready** read-only
evidence task with the work that consumes it edged behind it — never a blocked
task, because a blocked task with no `blocked → ready` transition is
permanently unclaimable.

Compilation fails, before any side effect, only for conditions more rounds
cannot fix: an unreadable source, an unresolvable target, coverage that will not
converge, a contradiction between equal-authority obligations that the source
itself does not settle, a document that violates its own published schema
(`program-execution.intent.v1`, `program-execution.autonomy-policy.v1`,
`program-execution.intent-resolution.v1`), or a constraint that would widen
authority beyond the active policy profile. The alternative — minting a
Blueprint full of BLOCKED tasks — looks like a program and can never run.

### Extractors

`resolve_extractor()` picks by explicit selection, then a live Claude Code CLI,
then the deterministic lexical reader. `L9_ARCHITECTURE_EXTRACTOR=deterministic`
forces the lexical one; tests always do, so no unit test needs a live model.

The Claude Code adapter is thin by construction: argv only (never a shell
string), a timeout, an output-size bound, `--permission-mode plan`, and a
tool deny-list. Source text reaches it as data; it holds no write authority and
cannot widen its own.

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
| Mission context contract | `schemas/mission-context.schema.json` | ADR-0024, ADR-0026 |
| Mission Program admission | `mission_admission.py` | ADR-0024, ADR-0026 |
| Mission Program Binding production | `mission_binding.py` | ADR-0026, Gate D |
| Official validator adapter | `blueprint_validate.py` | §13, Gate D |
| Front door | `cli.py` | §15, Gate E |
| Test matrix (13 §18 scenarios) | `tests/` | §18, Gate F |
| Architecture Intent contract | `architecture_intent.py`, `schemas/architecture-intent.schema.json` | segmentation, hashing, normative signals |
| Architecture semantic IR | `architecture_ir.py` | provenance, grounding, dedupe, contradictions |
| Extractor boundary + adapters | `architecture_extractor.py`, `schemas/architecture-extractor-{request,response}.schema.json` | chunking, Claude Code adapter, lexical extractor |
| Coverage, critic, repair | `architecture_coverage.py`, `schemas/architecture-resolution.schema.json` | dispositions, PASS semantics, bounded repair |
| Campaign lowering + provenance | `architecture_to_campaign.py` | campaign-source.v2, `intent_provenance` |
| Architecture front door | `../scripts/compile_architecture_intent.py` | pre-side-effect compilation |

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
