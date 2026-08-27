# Bounded LLM contract: DESIGN_RUNTIME

## Scope
Given a validated SkillProfile and partial IR, propose the workflow graph and
capability bindings. Structure only, never execution.

## Permitted
- Propose nodes, ordering, guards, terminal states, and failure paths.
- Assign each node `kind: deterministic` or `kind: bounded_llm`.
- Propose binding kinds from the closed enum in `policies/capability-closure.yaml`.
- Split a logical stage into multiple physical nodes when branching or fallback
  semantics would otherwise be hidden in prose.

## Forbidden
- Assigning any item from `runtime_routing.deterministic_code` to a bounded_llm node.
- Emitting a binding without `success_condition` and `failure_behavior`.
- Creating a parallel DAG framework or duplicating `l9-dag-authoring` mechanics.
- Emitting wiring, discovery, or registry instructions owned by `l9-wire-skill-into-repo`.

## Output contract
Return `{workflow: {entrypoint, nodes[]}, capabilities: []}` conforming to
`contracts/skill-ir.schema.json`. Preserve every logical stage the subject Skill's own profile and source
require; splitting a stage is allowed, silent removal is not. Those stages come
from the subject, never from this compiler: the fifteen stages named in
`SKILL.md` are this compiler's own graph and apply only when the subject is
this compiler.

## Failure behavior
If a required capability cannot be bound to a real implementation, emit
`binding.kind: UNKNOWN` with `bounded_unknown: true` and a stated blocker.
