---
name: l9-skill-compiler
description: compile, rebuild, evolve, or validate reusable L9 Skills by deciding topology ownership before creation, classifying one primary family plus orthogonal traits, normalizing canonical Skill IR, rendering target profiles, and enforcing Capability Closure. use when creating or materially changing a reusable skill where topology, runtime design, capability binding, rendering, or activation/behavior evals must be decided.
metadata:
  version: "2.0.0"
  updated: "2026-08-26"
  role: skill_compiler_runtime
  tags: [l9, compiler, skill, ir, capability-closure, dag]
  owner: igor_beylin
---

# l9-skill-compiler v2.0.0

**Thin bootloader. No generic doctrine is duplicated here.**

**DAG-ENFORCED.** Execute the `skill-compiler-v2` DAG. Do not run this Skill as a prose sequence.

## Activate when

Creating, compiling, materially rebuilding, evolving, or validating a reusable Skill where
topology ownership, runtime design, capability bindings, target profile rendering, or
activation/behavior evaluation must be decided.

**First decide whether to extend, compose, replace, reject, or create.** Creation is not the
default outcome. Most-specific existing owner wins.

## Do not activate

- Merely wiring an existing pack into a repo -> `l9-wire-skill-into-repo`
- Authoring a generic L9 DAG -> `l9-dag-authoring`
- Generic reasoning methodology -> `l9-structured-reasoning`
- Next-prompt behavior -> `l9-ynp`
- A domain task already owned by a more specific Skill -> that Skill

## Runtime

- Canonical typed graph: `workflows/dags/skill_compiler_dag.py`
- Registry id: `skill-compiler-v2`, bound through the repo's existing `SessionDAG` registry and `workflows/dags/__init__.py` auto-discovery surface
- DAG authoring mechanics and registration conventions are owned by `l9-dag-authoring`. This Skill consumes them and does not invent a parallel registry.

Logical stages: COMPILE_REQUEST, BIND_INPUTS, SCAN_SKILL_TOPOLOGY, CLASSIFY_SKILL_PROFILE,
EXTRACT_SOURCE_INTELLIGENCE, NORMALIZE_SKILL_IR, DESIGN_RUNTIME, RENDER_TARGET_PROFILE,
STATIC_VALIDATE, CAPABILITY_CLOSURE, ACTIVATION_EVAL, BEHAVIOR_EVAL, PACKAGE,
HANDOFF_TO_WIRING, PASS_BLOCKED_FAIL.

## Machine contracts

`contracts/compile-request.schema.json`, `contracts/skill-profile.schema.json`,
`contracts/skill-ir.schema.json`, `contracts/capability-closure.schema.json`,
`contracts/build-receipt.schema.json`

Policies: `policies/skill-families.yaml`, `policies/runtime-routing.yaml`,
`policies/capability-closure.yaml`, `policies/target-profiles.yaml`,
`policies/behavior-evals.yaml`

Bounded LLM contracts: `references/source-intelligence-contract.md`,
`references/runtime-design-contract.md`, `references/evaluation-contract.md`

## Invariants

- Source material compiles into Skill IR first. Files render only from validated IR.
- Deterministic work is executable code. LLM nodes are explicit, bounded, schema-constrained.
- One primary family plus orthogonal traits determines runtime, validation, and required evals.
- A platform convention belongs to a target profile, never to universal Skill semantics.
- Every required capability is closed, or explicitly runtime-bound with probe and failure behavior.
- Fail closed on material UNKNOWN. Never downgrade a blocking failure to success.

## Handoff

Discovery, registry updates, autonomy manifest tier, adapter symlinks, and deprecation are
owned by `l9-wire-skill-into-repo`. This Skill emits a typed handoff and invokes the owner.
