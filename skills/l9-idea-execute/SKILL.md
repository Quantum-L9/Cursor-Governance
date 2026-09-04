---
name: l9-idea-execute
description: route a validated ideaos decision into the shortest governed execution owner. use when idea-to-execution work needs a new product repo, website-bot build, bounded existing-repo change, or program-execution campaign. do not use for raw idea refinement or when ideaos has not decided outcomes.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, ideaos, execution, routing, foundry, website-bot, program-execution]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-09-02
---

# L9 Idea Execute

## Purpose

Turn validated IdeaOS intent into governed downstream execution without becoming another planner, factory, coding runtime, or Program Execution engine.

Preserve this authority chain:

```text
IdeaOS -> l9-idea-execute -> authoritative downstream owner -> owner-native receipt
```

IdeaOS decides **what outcomes are required**. This skill decides **which existing owner can satisfy each outcome and how to hand it off correctly**. The downstream owner decides **how to perform its work**.

## Core Contract

| Input | Output | Scope |
|-------|--------|-------|
| Validated IdeaOS decision or execution-ready pack | Envelope + Execution Graph + thin Receipt | Route and hand off only — never become IdeaOS, Foundry, Website-Bot, or PE |

Load [references/contracts.md](references/contracts.md) and [references/architecture.md](references/architecture.md).

## Authority Order

1. Explicit user outcome and named constraints.
2. Validated IdeaOS decision / pack (source authority + supersession).
3. Live downstream owner contracts (Website-Bot, Foundry, PE, `l9-plan-simple`).
4. This skill's envelope, graph, and adapter references.
5. `Unknown` — stop with an explicit failure state; do not guess an owner.

## Activation / Reject

**Activate** when a validated IdeaOS decision must become governed execution across a new product repo, Website-Bot, bounded existing-repo change, or PE-shaped campaign.

**Reject** a raw idea that still needs IdeaOS. Reject generic coding, ceremonial re-planning of a valid execution-ready pack, and any request that treats publication or merge as implied by execution.

Cursor and Claude load this pack only on explicit invoke or a hint-allowed Read/attach. `disable-model-invocation: true` is the mechanism; a ChatGPT implicit-invocation policy is not.

## Non-goals

Never:

- redo IdeaOS semantic refinement, product judgment, or go/no-go reasoning;
- create a new repository when a specialized factory already owns the artifact;
- send raw IdeaOS packs directly to Website-Bot;
- compile or mutate PE internals such as Blueprint, Program Lock, PEC task state, or LAUNCH.json;
- split one atomic cross-repository campaign into independent campaigns merely to bypass an executor limitation;
- regenerate a valid higher-authority execution plan or contract chain ceremonially;
- become a generic code mutation authority;
- treat publication or merge authority as implied by execution authority;
- guess an owner for an unbound capability.

## Core artifacts

Use three layers only:

1. **Idea Execution Envelope**: normalized execution requirements derived from validated IdeaOS output.
2. **Execution Graph**: atomic execution units, owner adapters, dependencies, and blockers.
3. **Idea Execution Receipt**: references and digests to authoritative downstream receipts/states.

Do not create a second implementation plan between these layers.

Read [references/contracts.md](references/contracts.md) when creating or validating these artifacts.

## Workflow

### 1. Establish IdeaOS authority

Require a validated IdeaOS decision, IdeaOS pack, or equivalent source that clearly establishes the required outcomes, constraints, unresolved unknowns, and affected surfaces.

If only a raw idea is present and semantic development is still required, stop with `IDEAOS_DECISION_REQUIRED`. Do not silently become IdeaOS.

Preserve source authority and supersession rules. Do not reinterpret stale or explicitly superseded material as current intent.

### 2. Compile the Idea Execution Envelope

Normalize the accepted IdeaOS decision into `l9.idea-execution-envelope/v1`.

Express requirements as capabilities and outcomes, not executor names. For example:

```yaml
requirements:
  - id: ER-001
    capability: product_repository
    target_state: new
    required: true
  - id: ER-002
    capability: website
    target_state: new
    required: true
```

IdeaOS-facing requirements must not say `use_foundry`, `use_website_bot`, `use_pe`, or choose a provider/model.

Run:

```bash
python3 scripts/validate_envelope.py IDEA_EXECUTION_ENVELOPE.yaml
```

Stop on validation failure.

### 3. Preserve the highest-authority existing execution artifact

Before planning anything, inspect the source for valid current execution artifacts such as:

- dependency-ordered implementation contracts;
- machine-validated plans;
- acceptance matrices;
- rollback and replay contracts;
- explicit Program Execution handoffs;
- target filetrees or scoped modification plans.

If an artifact is current, compatible with repository state, and sufficient for the selected executor, reuse it.

Apply the rule:

> Never downgrade an execution-ready pack back into an unplanned idea.

Planning is conditional, not ceremonial.

### 4. Classify execution topology

Use the deterministic routing rules in [references/architecture.md](references/architecture.md) and the bundled capability registry.

Run:

```bash
python3 scripts/route_execution.py IDEA_EXECUTION_ENVELOPE.yaml > EXECUTION_GRAPH.yaml
python3 scripts/validate_graph.py EXECUTION_GRAPH.yaml
```

Initial topologies:

- `NEW_PRODUCT_REPOSITORY`
- `SPECIALIZED_FACTORY`
- `EXISTING_REPO_CHANGE`
- `EXISTING_SYSTEM_CAMPAIGN`

If multiple independent units exist, keep them separate and preserve explicit dependency edges. Dependencies determine ordering; category does not.

### 5. Resolve owners before executors

Resolve runtime/artifact ownership first, then execution adapter.

Examples:

- website artifact -> `Quantum-L9/Website-Bot`;
- generic unowned new product/system repository -> `l9-idea-foundry`;
- bounded existing-repository change -> current `l9-plan-simple` path when planning/execution is required;
- campaign-shaped coordinated existing-system change -> Program Execution adapter.

A coding executor does not become the runtime owner of the repositories it modifies.

Unknown ownership -> `CAPABILITY_OWNER_UNKNOWN` and stop.

### 6. Probe the adapter's current public contract

Treat downstream adapters as version-sensitive boundaries.

Before invoking any mutable downstream system:

1. Inspect its current public intake/front-door documentation.
2. Determine supported topology and authority.
3. Verify the requested execution unit is faithfully representable.
4. Compile only the owner-native input it currently accepts.
5. Validate using owner-native validation where available.
6. Invoke only the canonical public front door.

If the executor is conceptually correct but cannot represent the topology, stop with `EXECUTOR_CAPABILITY_GAP`. Never degrade the idea to fit the tool.

Read [references/adapters.md](references/adapters.md) for all adapter contracts.

### 7. Invoke only with bounded authority

Execution authority is unit-local. Publication, remote repository creation, deployment, and merge remain separate unless explicitly authorized by the downstream owner's current contract and the user.

Do not widen authority because another unit in the graph has stronger permission.

### 8. Observe authoritative terminal state

After downstream work, capture references to the owner's canonical receipt/state. Verify that it binds to the expected input or source revision when the owner provides such evidence.

Do not recreate or summarize downstream evidence as a substitute for its receipt.

### 9. Join into the Idea Execution Receipt

Produce a thin `l9.idea-execution-receipt/v1` that records:

- source IdeaOS decision/envelope digest;
- graph digest;
- per-unit owner, adapter, requested terminal state, resulting state;
- authoritative receipt/state references and digests when available;
- unresolved blockers;
- next legal transition.

### 10. Resume from the earliest invalid unit

On a rerun:

- reuse completed units whose source inputs, dependency outputs, owner contract, and receipt bindings remain valid;
- invalidate a unit when its governing input or adapter contract changed materially;
- invalidate downstream dependent units, not unrelated siblings;
- never reuse a publication/deployment authorization merely because local execution evidence is reusable.

## Topology rules

### Specialized factory outranks generic repository birth

If a specialized factory owns creation of the required artifact, route directly to it even if that factory internally provisions a repository.

Therefore:

```text
website -> Website-Bot
```

not:

```text
website -> Foundry -> Website-Bot
```

Use Foundry only when a new **product/system repository** is required and no specialized downstream factory already owns that artifact.

### Existing system campaign

Classify coordinated work as `EXISTING_SYSTEM_CAMPAIGN` when multiple existing repositories/owners participate in one causal program or when cross-repository dependencies, joins, shared rollback, or terminal convergence make the work atomic.

Do not decompose one atomic campaign solely because the current executor has an admission limitation.

### Bounded existing-repository change

Use `EXISTING_REPO_CHANGE` when one existing repository can satisfy the outcome without cross-repository convergence.

Use existing valid plans first. Invoke current planning only if the work is not already sufficiently planned for its executor.

## Adapter invariants

### Foundry

Use `l9-idea-foundry` only for an unowned new product/system repository. Let Foundry own its blueprint, code realization, traceability, freeze, and `l9-repo-template` seam.

If Foundry is unavailable, stop. Do not recreate it inside this skill.

### Website-Bot

Compile a rich `domain_spec.source.yaml` projection from IdeaOS truth. Never hand-maintain Website-Bot's generated flat DomainSpec.

Let Website-Bot own normalization, pipeline planning, build stages, provisioning, publication, deployment, and its downstream SEO handoff.

### Program Execution

Program Execution is an **evolving adapter**. Always inspect its live current contract before use.

Current baseline as of 2026-09-02: the sole live front door is `make campaign INTENT=<brief.md|activate.yaml>` and the structured activation compiler is single-target. Multi-repository campaigns must therefore fail `EXECUTOR_CAPABILITY_GAP` on that baseline rather than being forced through one target.

Read [references/program-execution-adapter.md](references/program-execution-adapter.md) before every PE-shaped handoff. Treat that file as a baseline/discovery guide, not permanent PE law.

### Plan Simple

Treat `l9-plan-simple` as conditional for bounded existing-repository work. Reuse an existing valid plan when present. Verify the live skill contract before invocation because planning/execution handoff modes may evolve.

## Determinism and evidence

- Normalize the IdeaOS decision once.
- Route from the normalized envelope, not repeatedly from raw pack prose.
- Keep stable requirement IDs and execution-unit IDs.
- Use explicit dependencies and stop states.
- Cite exact source artifacts for non-obvious routing facts.
- Prefer digests for machine artifacts when available.
- Keep adapter discovery evidence with the run when a moving executor contract affects the route.

## Failure states

Use explicit states rather than improvisation:

- `IDEAOS_DECISION_REQUIRED`
- `ENVELOPE_INVALID`
- `CAPABILITY_OWNER_UNKNOWN`
- `EXECUTION_TOPOLOGY_UNSUPPORTED`
- `ADAPTER_CONTRACT_UNAVAILABLE`
- `EXECUTOR_CAPABILITY_GAP`
- `OWNER_NATIVE_INPUT_INVALID`
- `DOWNSTREAM_EXECUTION_FAILED`
- `DOWNSTREAM_RECEIPT_INVALID`
- `PROTECTED_ACTION_REQUIRES_AUTHORITY`

A blocked route is a valid result when the idea is sound but the current executor substrate is incomplete.

## Battle-test examples

Read [references/examples.md](references/examples.md) when validating routing behavior. The canonical regression cases are:

- SplitWisely -> Foundry, not Website-Bot;
- a website-only requirement -> Website-Bot, not Foundry;
- one bounded existing repo -> existing-repo route;
- PR Cognitive Convergence -> PE-shaped multi-repo campaign, but blocked on the 2026-09-02 single-target PE baseline;
- mixed new product + website -> two units, concurrent unless an explicit dependency requires product identity first.

## Validation

- Envelope, graph, and adapter scripts MUST be the deterministic gates named below.
- A blocked route with an explicit failure state is a valid result.
- Do not claim a downstream owner ran unless its canonical receipt/state is referenced.

## Scripts

- `scripts/validate_envelope.py`: validate the normalized Idea Execution Envelope.
- `scripts/route_execution.py`: deterministically compile the initial Execution Graph from validated requirements and the capability registry.
- `scripts/validate_graph.py`: validate graph shape, dependencies, cycles, topology/adapter invariants, and blocker consistency.
- `scripts/check_adapter_capability.py`: test an execution unit against a discovered adapter capability snapshot.
- `scripts/self_test.py`: run deterministic positive and negative regression fixtures.

These scripts validate and route declared execution semantics. They do not replace model judgment for ambiguous IdeaOS meaning or downstream owner-specific compilation.

## Reference map

- [references/architecture.md](references/architecture.md): authority, topology, decomposition, concurrency, and reuse rules.
- [references/contracts.md](references/contracts.md): Envelope, Graph, adapter capability snapshot, and Receipt contracts.
- [references/adapters.md](references/adapters.md): Foundry, Website-Bot, Plan Simple, and Program Execution adapter behavior.
- [references/program-execution-adapter.md](references/program-execution-adapter.md): moving PE discovery seam and current baseline.
- [references/examples.md](references/examples.md): regression examples and expected routing outcomes.
- [references/capability-registry.yaml](references/capability-registry.yaml): minimal demonstrated-owner registry; expand only for real consumers.
