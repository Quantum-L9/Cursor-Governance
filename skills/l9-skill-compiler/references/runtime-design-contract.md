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
`contracts/skill-ir.schema.json`. Preserve the fifteen logical stages named in
`SKILL.md`; splitting is allowed, silent removal is not.

## Failure behavior
If a required capability cannot be bound to a real implementation, emit
`binding.kind: UNKNOWN` with `bounded_unknown: true` and a stated blocker.
