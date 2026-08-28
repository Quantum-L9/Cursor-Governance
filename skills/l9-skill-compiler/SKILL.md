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
- Programmatic invocation: `workflows/dags/skill_compiler_runner.py`. It derives execution order, each stage's argv, guard entry, and terminal state from the graph itself, so it carries no stage list of its own.
- DAG authoring mechanics and registration conventions are owned by `l9-dag-authoring`. This Skill consumes them and does not invent a parallel registry.

Logical stages: COMPILE_REQUEST, BIND_INPUTS, SCAN_SKILL_TOPOLOGY, CLASSIFY_SKILL_PROFILE,
EXTRACT_SOURCE_INTELLIGENCE, NORMALIZE_SKILL_IR, DESIGN_RUNTIME, RENDER_TARGET_PROFILE,
STATIC_VALIDATE, CAPABILITY_CLOSURE, ACTIVATION_EVAL, BEHAVIOR_EVAL, PACKAGE,
HANDOFF_TO_WIRING, PASS_BLOCKED_FAIL.

## Operator entrypoint

`scripts/compile_skill.py` is a thin facade over the same DAG. It normalizes operator
input into a canonical CompileRequest and invokes `skill-compiler-v2`; it owns no
compilation semantics and never sequences stages itself.

```bash
python skills/l9-skill-compiler/scripts/compile_skill.py optimize l9-existing-skill
python skills/l9-skill-compiler/scripts/compile_skill.py rebuild skills/l9-existing-skill
python skills/l9-skill-compiler/scripts/compile_skill.py compile request.yaml
python skills/l9-skill-compiler/scripts/compile_skill.py create \
  --name l9-new-skill --source ./source.md --profile portable --profile l9
```

| Mode | Canonical intent | Subject |
|---|---|---|
| `optimize <skill>` | `evolve` | resolved live Skill, its pack as source material |
| `rebuild <skill>` | `rebuild` | resolved live Skill, identity preserved |
| `compile <file>` | intent from the request | JSON or YAML request file |
| `create --name --source` | `create` | proposed name plus source material |

YAML is an input adapter only: it normalizes into the same object as the equivalent
JSON and is validated by the one `contracts/compile-request.schema.json`. There is no
second schema, and a key the canonical schema does not allow fails closed.

Flags: `--dry-run`, `--output-json`, `--request-id`, `--profile`, `--objective`,
`--receipt-path`, `--output-dir`, `--no-package`, `--ir`, `--skills-root`.

`--dry-run` parses, resolves the Skill or source, scans topology, classifies the
profile, and prints the normalized request and planned node order. It writes no pack,
performs no wiring or registration, and never reports a build.

The convenience verb never decides ownership. `create` still passes through the
topology stage, so `EXTEND_EXISTING`, `COMPOSE_EXISTING`, `REPLACE_EXISTING`, and
`REJECT_NEW_SKILL` remain possible answers and are surfaced as given.

Bounded-LLM nodes have no deterministic substitute. A terminal-only run stops at the
first such node and reports `BOUNDED_LLM_REQUIRED` with the node and its contract; the
agent executes that node under the contract and re-invokes with `--ir` to drive the
deterministic tail. A blocked run is never reported as a build.

Exit codes: `0` PASS, `2` invalid operator input, `3` BLOCKED, `4` compilation or
runtime FAIL, `5` validation FAIL, `10` unclassified. Failures are typed
(`REQUEST_SCHEMA_INVALID`, `SKILL_NOT_FOUND`, `TOPOLOGY_BLOCKED`, `DAG_NOT_AVAILABLE`,
`COMPILATION_BLOCKED`, `VALIDATION_FAILED`, …) and `--output-json` emits the
request, topology decision, skill profile, DAG terminal state, stage records,
artifacts, unknowns, and errors. The executable and the contracts remain
authoritative over this section.

## Machine contracts

`contracts/compile-request.schema.json`, `contracts/skill-profile.schema.json`,
`contracts/skill-ir.schema.json`, `contracts/capability-closure.schema.json`,
`contracts/build-receipt.schema.json`

Policies: `policies/skill-families.yaml`, `policies/runtime-routing.yaml`,
`policies/capability-closure.yaml`, `policies/target-profiles.yaml`,
`policies/behavior-evals.yaml`, `policies/topology-ownership.yaml`

First qualification run and defect classification: `QUALIFICATION.md`

Bounded LLM contracts: `references/source-intelligence-contract.md`,
`references/runtime-design-contract.md`, `references/evaluation-contract.md`

## Invariants

- Source material compiles into Skill IR first. Files render only from validated IR.
- Deterministic work is executable code. LLM nodes are explicit, bounded, schema-constrained.
- One primary family plus orthogonal traits determines runtime, validation, and required evals.
- A platform convention belongs to a target profile, never to universal Skill semantics.
- Every required capability is closed, or explicitly runtime-bound with probe and failure behavior.
- **The existence of a DAG does not justify a Skill.** Skills represent capabilities;
  DAGs represent execution graphs. Create or retain a DAG-named Skill only when the
  capability itself is DAG authoring, validation, registration, or lifecycle
  management. Otherwise the DAG is a runtime artifact of the owning capability, the
  owning Skill references it, and no sibling DAG-specific Skill is created.
  Enforced deterministically at `SCAN_SKILL_TOPOLOGY` by
  `policies/topology-ownership.yaml`.
- Fail closed on material UNKNOWN. Never downgrade a blocking failure to success.

## Handoff

Discovery, registry updates, autonomy manifest tier, adapter symlinks, and deprecation are
owned by `l9-wire-skill-into-repo`. This Skill emits a typed handoff and invokes the owner.
