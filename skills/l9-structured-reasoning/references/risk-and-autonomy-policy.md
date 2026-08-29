# Risk and Autonomy Policy

Use evidence quality and reversibility to choose the action. Do not invent numeric confidence.
Canonical allow-set: `confidence-policy.yaml`.

| Evidence | Reversible | Guarded | Irreversible |
|---|---|---|---|
| high | proceed | proceed with validation | proceed only with explicit authorization and rollback or containment |
| medium | proceed with validation | bounded probe | block or obtain direct evidence |
| low | bounded probe | bounded probe | block |
| unknown | bounded probe if safe | block | block |

## Authorization boundary

- Read and analyze when access exists.
- Mutate only with explicit authority.
- Never infer destructive or external write authority from a reasoning request.
- When authority is missing, produce an exact plan, patch proposal, or handoff.

## Probe rule

Choose the probe with the highest expected decision value per unit of cost. Stop after the first probe that resolves the material uncertainty.

## Reconsideration

Every guarded or irreversible decision should name the evidence or condition that would trigger reconsideration.
