---
name: l9-idea-foundry
description: compile an implementation-ready idea pack into tested code and a birth-ready quantum-l9 repository. use when a mature idea should leave specification and become a real repo via l9-repo-template. do not use for websites, existing-repo changes, or production deployment.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, foundry, idea-pack, repo-birth, plan-simple, harvest]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-09-02
---

# L9 Idea Foundry

Transform implementation-ready idea authority into tested source code, preserve why the code exists, and hand the exact validated product state to the canonical repository factory.

Optimize for **compounding reuse**, not artifact count: reuse upstream owners, compile intent once, automate deterministic seams, and leave the newborn easier to evolve than the pack was to interpret.

## Core Contract

| Input | Output | Scope |
|-------|--------|-------|
| Implementation-ready idea pack or specification archive | Tested payload + Foundry index + freeze receipt + local birth | Compose L9 owners; never own Website-Bot, PE, or production deploy |

Load [references/contracts.md](references/contracts.md) and [references/composition.md](references/composition.md).

## Authority Order

1. Explicit user outcome and named constraints.
2. Idea pack authority map (canonical / locked / accepted outrank proposed / unknown).
3. Live upstream owners (`l9-intelligence-harvest`, GAR when active, `l9-plan-simple`, `l9-repo-template`).
4. This skill's blueprint, traceability, and birth-integration references.
5. `Unknown` — stop with an explicit disposition; do not invent a local brain.

## Activation / Reject

**Activate** when a mature idea pack must become tested code and a birth-ready Quantum-L9 repository.

**Reject** website-only work (Website-Bot), bounded existing-repo changes (`l9-plan-simple` / `l9-idea-execute`), and any request that includes production deployment.

Cursor and Claude load this pack only on explicit invoke or a hint-allowed Read/attach. `disable-model-invocation: true` is the mechanism; a ChatGPT implicit-invocation policy is not.

## Ownership and composition

Preserve these owners:

- The idea pack owns product intent, source authority, locked scope, acceptance conditions, anti-goals, evidence, hypotheses, and explicit unknowns.
- `l9-intelligence-harvest` owns donor-to-beneficiary semantic mining when that transfer problem exists. Its output is evidence, never product authority.
- An explicitly active `l9-global-architect` owns architecture judgment. Do not copy GAR law into Foundry.
- `l9-plan-simple` owns implementation-plan structure, decomposition, stress testing, implementation-level leverage analysis, `PLAN_DOCUMENT`, and plan validation.
- This skill owns idea authority normalization, beneficiary framing, cross-repository leverage/reuse selection, composition, code realization from the accepted plan, durable product traceability, and the authoritative product payload.
- `Quantum-L9/l9-repo-template` owns repository birth, chassis, payload ownership, provenance, org-profile application, publication, and remote attestation.
- `Quantum-L9/.github` and current L9 CI owners retain organization governance and CI authority.
- This skill never owns production deployment.

Read [references/composition.md](references/composition.md) before invoking sibling capabilities. Never copy their schemas, validators, state machines, or policy into this pack.

## Terminal target

Default path:

`IDEA_PACK -> AUTHORITY_MAP -> BENEFICIARY_REUSE -> OPTIONAL_HARVEST -> ARCHITECTURE -> COMPILED_INTENT -> VALIDATED_PLAN -> CODE_REALIZED -> FOUNDRY_INDEX -> BIRTH_READY -> LOCAL_BIRTH_PASS -> OPTIONAL_PROVISIONAL_REPOSITORY`

A remote repository is optional. Production deployment is never part of this path.

## Leverage law

1. **Upstream before local.** Search verified L9 owners before creating a new shared owner.
2. **Compile once.** After `IMPLEMENTATION_BLUEPRINT.yaml` is accepted, downstream stages consume it instead of independently reinterpreting the entire raw pack.
3. **Reuse proven work.** When a prior Foundry index exists, reuse validated intermediate results only while their governing inputs and external evidence remain unchanged.
4. **Automate deterministic seams.** Hashing, indexing, exact-state binding, and contract validation belong in scripts, not repeated model judgment.
5. **Earn abstractions.** Add a shared abstraction only for multiple verified consumers, a demonstrated recurring operation, or one verified shared failure mode.
6. **Make provenance operational.** Traceability must let a future agent move from requirement -> architecture -> plan -> code -> test without archaeology.
7. **Delete duplicate responsibility.** A new local brain is a defect when an upstream owner already exists.
8. **Validate the exact handoff state.** Birth consumes what was actually frozen, not what the agent remembers validating.

## Workflow

### 1. Bind and inventory the idea source

Accept ZIP/TAR archives, directories, loose specification files, or an idea-stage repository.

When bytes are locally available, run:

```bash
python3 scripts/inventory_idea_pack.py <source> --out <inventory.json>
```

Recursively inspect relevant nested archives. Preserve unreadable/unsafe archive observations as explicit inventory issues instead of silently omitting them.

Identify:

- canonical / locked / accepted requirements,
- proposed decisions and hypotheses,
- unknowns and disputes,
- rejected / deferred / superseded material,
- acceptance demos and success criteria,
- anti-goals and forbidden behavior,
- existing code, reusable components, named L9 dependencies, and external authorities.

Read [references/contracts.md](references/contracts.md).

### 2. Build the authority map

Create `docs/idea-origin/AUTHORITY_MAP.yaml`.

Every material claim must resolve to exactly one state:

`CANONICAL | LOCKED | ACCEPTED | PROPOSED | HYPOTHESIS | UNKNOWN | REJECTED | DEFERRED | SUPERSEDED`

Do not silently promote proposed or unknown material. Resolve contradictions using explicit current user instruction, then explicit pack supersession law, then source authority. File age alone cannot overrule canonical material.

A material unknown blocks only the behavior whose correctness depends on it.

### 3. Build the beneficiary, reuse, and constellation-leverage map

Before designing local architecture, define:

- repository/product identity,
- required product capabilities,
- selected `l9-repo-template` class or explicit alternative,
- current verified L9 owners relevant to the idea,
- reuse disposition for every shared responsibility in the selected slice,
- missing responsibilities that genuinely belong in the newborn,
- the highest-leverage cross-repository move,
- duplicate owners deliberately avoided,
- future actions made cheaper/safer by the chosen contracts,
- tempting speculative abstractions deliberately rejected.

Record these in `IMPLEMENTATION_BLUEPRINT.yaml` under `beneficiary`, `reuse_map`, and `constellation_leverage`.

Allowed reuse dispositions are defined in [references/contracts.md](references/contracts.md). `OWN_LOCALLY` requires evidence that upstream reuse is not the correct owner.

Do not duplicate Plan Simple's todo-level leverage ranking. Foundry leverage is about upstream ownership, reusable boundaries, and future-action acceleration.

### 4. Run Intelligence Harvest only when it is actually a transfer problem

Invoke `l9-intelligence-harvest` when the idea pack or named donor contains reusable semantic intelligence whose fit against the beneficiary can change architecture, reuse, acceptance tests, or implementation scope.

Typical triggers:

- prior systems, kernels, workflows, architecture packs, or reusable implementation patterns,
- another repo/pack named as a donor,
- multiple candidate mechanisms whose portable semantics matter,
- a likely L9 capability reuse whose exact beneficiary fit is unresolved.

Skip Harvest when the pack is already a direct, self-contained implementation specification and donor-to-beneficiary transfer adds no discriminating evidence.

Preserve `harvest.json` and `harvest-receipt.json` as planning evidence. Do not execute donor code by default and do not let Harvest override canonical pack requirements.

### 5. Compile architecture and the pre-code ingress

Create `docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml` with at least:

- product objective and first executable outcome,
- `compilation` contract binding source inventory and authority map,
- beneficiary, reuse map, and constellation leverage,
- invariants and anti-goals,
- selected stack and justification,
- canonical owners for state, mutation, lifecycle, and policy,
- trust and public/private boundaries,
- modules and dependency direction,
- persisted schemas and typed contracts,
- deterministic vs model-mediated logic,
- material failure/idempotency/retry/recovery semantics,
- selected vertical-slice acceptance path,
- deferred surfaces and contained unknowns,
- required validation,
- accepted Harvest evidence refs when applicable,
- architecture-direction, L9-alignment, and first-order answers.

Set:

```yaml
compilation:
  ingress_role: PRE_CODE_SSOT
  source_inventory_digest: sha256:...
  authority_map_ref: docs/idea-origin/AUTHORITY_MAP.yaml
  raw_source_after_acceptance: EVIDENCE_ONLY
  change_policy: EARLIEST_INVALID_LAYER
```

After acceptance, Plan Simple and code realization consume this compiled intent. They may follow cited evidence refs but must not create a second interpretation of the whole raw pack.

Prefer a modular monolith unless evidence forces distribution. Conceptual services are responsibilities first, processes second.

When GAR is active, use GAR for architecture judgment and bind its decision evidence. Do not claim GAR conformance when GAR was not actually used.

### 6. Delegate implementation planning to `l9-plan-simple`

For nontrivial code realization, invoke `l9-plan-simple` after architecture is accepted and before material code mutation.

Foundry consumes the validated `PLAN_DOCUMENT` as the implementation plan SSOT. Require:

- objective and first executable outcome represented,
- in/out scope explicit,
- todos bound to concrete files or explicit blockers,
- dependency order coherent,
- stress-test and first-order leverage completed,
- acceptance and validation obligations represented,
- plan validator PASS observed.

Do not fork or restate the `l9-plan` schema, renderer, planning doctrine, stress test, leverage rules, or validator.

**Negotiate the handoff mode from current evidence:**

- Prefer `plan_handoff: EMBEDDED` when the live Plan Simple contract proves first-class embedded planning exists. Record the evidence ref and `compatibility_fallback: false`.
- Otherwise use `plan_handoff: EMBEDDED_PRE_BIRTH`, set `compatibility_fallback: true`, record the reason, and consume only the validated planning surface.
- Never infer embedded mode merely because execution/publish capability is absent.
- If no authorized Plan Simple mode can produce a validated plan, stop with `PLANNING_CAPABILITY_BLOCKED`.

### 7. Select and realize the code slice

Use the pack's explicit first build mission or acceptance demo when present. Otherwise choose the smallest end-to-end slice that proves the product primitive.

A valid slice crosses real boundaries and produces observable behavior. Reject:

- directories plus TODOs,
- interfaces without a concrete path,
- mock-only happy paths,
- generated schemas with no consumer,
- wrappers without product behavior,
- tests that only assert mocked calls,
- local copies of an existing upstream L9 owner.

At least one acceptance path must run on local/synthetic data without production dependencies.

Implement in validated-plan order. Every nontrivial changed surface must map to a requirement, accepted architecture decision, Harvest disposition, or explicit reversible implementation decision.

### 8. Build durable traceability

Create `docs/idea-origin/TRACEABILITY.yaml`.

For every selected-slice capability map:

`requirement refs -> architecture/Harvest refs -> Plan Simple todo refs -> implementation paths -> executable evidence refs -> remaining unknown IDs`

Do not duplicate provenance into another traceability document. `IMPLEMENTED` requires real implementation paths and real discriminating evidence.

### 9. Prove template fit

Before materializing the authoritative payload, inspect the live `l9-repo-template` architecture and birth contract.

Use the non-Constellation Python template only when a real Python-owned responsibility exists. Do not invent a meaningless Python package to satisfy birth shape.

Route Constellation nodes/dependencies to the sibling factory declared by the live template. For genuinely incompatible products, stop with `TEMPLATE_MISMATCH` rather than forcing the wrong chassis.

Read [references/birth-integration.md](references/birth-integration.md).

### 10. Validate code realization and emit the downstream ingress

The authoritative payload must include real code, tests, architecture metadata, idea-origin contracts, and template-required repository shape.

Run project-native validation first. Then run the Foundry gate:

```bash
python3 scripts/validate_foundry_payload.py <payload>
```

Generate the deterministic resume/index surface:

```bash
python3 scripts/emit_foundry_index.py <payload> \
  --inventory-digest sha256:<64hex> \
  --plan-ref <validated-plan-ref> \
  --plan-digest sha256:<64hex>

python3 scripts/validate_foundry_payload.py <payload>
```

`FOUNDRY_INDEX.json` is generated output. Do not hand-edit it. Its job is to let future agents hydrate current origin context and detect changed semantic inputs without rereading the entire idea pack.

### 11. Freeze the exact payload and delegate birth

Initialize/retain the staging payload as a git repository, commit the exact validated tree including `FOUNDRY_INDEX.json`, and require a clean worktree.

Emit the external freeze receipt:

```bash
python3 scripts/emit_freeze_receipt.py <payload> \
  --inventory-digest sha256:<64hex> \
  --plan-ref <validated-plan-ref> \
  --plan-digest sha256:<64hex> \
  --out <external-freeze.json>
```

Then require:

```bash
python3 scripts/validate_foundry_payload.py <payload> \
  --birth-ready \
  --freeze-receipt <external-freeze.json>
```

The freeze receipt must bind HEAD, tracked-tree digest, source inventory digest, plan digest, and the committed Foundry index digest. After this point the staging repository is immutable evidence; record birth observations externally unless you deliberately revalidate, recommit, and re-freeze.

Use the current `l9-repo-template` birth compiler and birth engine. Run local/no-remote birth first. Only after local birth passes may remote creation occur when explicitly requested and authorized.

Do not recreate `new_repo.py`, birth-runner stages, org seeding, or CI distribution.

### 12. Resume/recompile without repeating unchanged work

If the staging product already contains `docs/idea-origin/FOUNDRY_INDEX.json`, read [references/recompile.md](references/recompile.md).

Reuse intermediate results only when their governing digests, current operator intent, external owner evidence, and component-specific preconditions remain valid. Invalidate from the earliest changed layer.

Never reuse a freeze receipt after any tracked payload change. Never reuse a Plan Simple plan solely because its file hash matches if its baseline/preconditions no longer hold.

### 13. Stop before deployment

After remote birth, report the actual template-observed birth state. Do not execute production deployment, production data migration, DNS cutover, secret rotation, paid-service activation, app-store release, or production traffic changes.

Deployment configuration may exist as inert repository content when the accepted implementation plan requires it.

After remote birth, Foundry origin artifacts become provenance and context acceleration. Current repository ground truth and repo-local law own subsequent implementation.

## Unknown dispositions

Use only:

- `VERIFY_NOW`
- `BOUND_WITH_INTERFACE`
- `DEFER_OUTSIDE_SLICE`
- `BLOCK_SURFACE`

Do not let one unresolved regulated or external fact freeze unrelated code. Do not let repository birth erase it either.

## Completion gate

Do not claim completion until every applicable item is evidenced:

- source inventory completed or bounded with explicit issues,
- authority map exists and conflicts are resolved/bounded,
- beneficiary/reuse/constellation-leverage map exists,
- required Harvest completed or explicitly not applicable,
- architecture accepted with required questions answered,
- blueprint is accepted as the pre-code single ingress,
- validated `l9-plan-simple` plan exists for nontrivial implementation,
- plan handoff mode is evidence-bound,
- selected slice contains real working behavior,
- acceptance path passes on local/synthetic inputs,
- material unknowns have explicit dispositions,
- traceability maps implemented capabilities through plan/code/evidence,
- deterministic `FOUNDRY_INDEX.json` matches current origin artifacts,
- authoritative payload validates,
- exact payload state is frozen at a clean commit and bound by an external freeze receipt,
- template birth payload contract is compiled from that exact state,
- local/no-remote birth passes,
- remote attestation is reported only when remote birth was requested and observed,
- production deployment did not occur.

Read [references/workflow.md](references/workflow.md) for recovery routing.

## Validation

- Inventory, payload, index, and freeze scripts MUST be the deterministic gates named below.
- `FOUNDRY_INDEX.json` is generated; do not hand-edit it.
- Do not claim completion unless every applicable completion-gate item is evidenced.
- `python3 scripts/self_test.py` MUST PASS after script or contract changes.

## Skill self-validation

Before packaging or after changing Foundry scripts/contracts, run:

```bash
python3 scripts/self_test.py
```

Do not claim deterministic Foundry gates are healthy when this self-test fails or cannot run.

## Final response

Return a compact operator receipt with:

- repository/package identity,
- first executable outcome,
- Harvest: `USED | NOT_APPLICABLE | BLOCKED`, with refs when used,
- architecture decision ref,
- constellation leverage move and major upstream reuse,
- `l9-plan-simple` plan ref, handoff mode, and validation status,
- implemented surfaces,
- validation actually performed and observed result,
- remaining deferred/blocked surfaces,
- idea inventory digest/source revision,
- Foundry index ref/digest,
- staging payload revision and freeze-receipt ref,
- birth payload contract ref,
- observed birth state: `LOCAL | PROVISIONAL | QUARANTINED | BORN` only when actually observed,
- repository URL only if created,
- `DEPLOYMENT: NOT PERFORMED`.

Never claim production readiness merely because repository birth passed.
