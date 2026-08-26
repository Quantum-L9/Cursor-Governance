# LLM-Router Reasoning Capability Microscope

This is an architecture microscope of `Quantum-L9/LLM-Router` as it stands today,
and the design it has to converge on. It is written the way these documents are
always written: dense prose, tables, current-state observations, a migration
order, explicit deferrals, and the tests that decide whether any of it worked.
Nothing here is a numbered task list, and it deliberately never becomes one.

## Current state

The router today resolves search capability through `requiresSearchProvider` in
`src/matrices/search-policy.ts` and dispatches through `resolveRoute` in
`src/index.ts`. Reasoning is not a first-class capability at all: a task that
needs reasoning gets whichever provider the general matrix in
`src/matrices/general-matrix.ts` happens to rank first, and nothing checks that
the chosen provider can actually reason.

Perplexity is wired as a general-purpose provider in
`src/matrices/perplexity-matrix.ts`. That is the root of the defect this
document exists to correct: the matrix advertises Perplexity models the
transport in `src/providers/perplexity.ts` cannot reach for reasoning work.

Budget downgrade in `src/budget/index.ts` currently walks the general matrix by
price alone. Under pressure it will happily downgrade a reasoning task onto a
provider with no reasoning capability, and the routing decision will still claim
the task was routed for reasoning.

## Provider authority

DeepSeek MUST be the primary governed reasoning provider. Every task whose
resolved capabilities include reasoning MUST dispatch to DeepSeek unless an
explicit, recorded policy override selects another reasoning-capable provider.

Perplexity is research only. Perplexity MUST NOT serve reasoning traffic under
any policy, any budget pressure, or any fallback path.

Perplexity reasoning models are unreachable through the current transport. The
matrix MUST NOT advertise a Perplexity model as reasoning-capable while
`src/providers/perplexity.ts` has no path to invoke it, because an advertised
capability that cannot be dispatched is a lie the budget planner will act on.

## Capability resolution

`requiresReasoning` becomes the canonical capability authority for reasoning.
The resolver in `src/matrices/capabilities.ts` MUST derive `reasoningRequired`
from `requiresReasoning` when it is an explicit boolean, and from the task type
otherwise, exactly the way `requiresSearchProvider` already derives search.

| Field | Source of truth | Consumer |
|---|---|---|
| `requiresSearch` | explicit boolean, else task default | search dispatch |
| `requiresReasoning` | explicit boolean, else task type | reasoning dispatch |
| `reasoningPolicySource` | `EXPLICIT` or `TASK_DEFAULT` | routing audit |

There MUST be exactly one resolver. A second place that decides whether a task
needs reasoning is the defect, not the feature.

## Budget behavior

Budget downgrade MUST remain within the capability family. A reasoning task that
is downgraded for cost MUST land on another reasoning-capable provider or fail
closed; it MUST NEVER be silently downgraded onto a provider that cannot reason.

The existing circuit-breaker, budget-reservation, and audit invariants in
`src/circuit-breaker.ts` and `src/budget/index.ts` MUST remain intact. This
change adds a capability dimension; it does not renegotiate the budget contract.

## Composite capabilities

Search combined with reasoning MUST fail closed in this release. There is no
provider in the matrix that can be proven to serve both, and guessing one is
how the Perplexity defect happened in the first place.

Vision combined with reasoning MUST fail closed in this release for the same
reason. `src/vision/index.ts` resolves vision independently and no reasoning
provider in the matrix declares vision support.

A composite research-then-reasoning execution — Perplexity researches, DeepSeek
reasons over the result — is explicitly DEFERRED to a later program. It is OUT
OF SCOPE here. Do not build a staged composite executor as part of this work.

## Dispatch integrity

The route decision MUST equal the actual provider dispatch. Today
`resolveRoute` can return a decision naming one provider while the execution
path in `src/index.ts` selects another after a budget or circuit-breaker
adjustment, and `getCallLog` records the decision rather than the dispatch.
Whatever the audit log records MUST be what actually ran.

`reasoning_content` MUST NEVER be persisted or exposed. DeepSeek returns
reasoning traces on the response envelope; they MUST be dropped at the transport
boundary in `src/providers/openai-transport.ts` and MUST NOT reach `getCallLog`,
`src/memory.ts`, or any returned payload. This is an invariant, not a preference.

## Control plane vocabulary

The control plane already carries a DeepSeek provider vocabulary and a
reasoning-depth field in `src/control-plane/contracts.ts`. This work MUST reuse
that existing vocabulary. Introducing a parallel naming scheme for the same
concept is prohibited.

We need to determine whether `src/control-plane/contracts.ts` already exposes a
reasoning-depth enum wide enough for the three depths the policy engine expects,
or whether it has to be widened. That question is answerable by reading the
file, and the answer decides how the policy-engine change is written.

We also need to verify whether the existing schema in `src/schemas.ts` accepts an
additive `requiresReasoning` field without a breaking change to consumers.

## Acceptance

ACCEPTANCE: a reasoning task with no explicit override dispatches to DeepSeek,
and the recorded call log names DeepSeek as the dispatched provider.

ACCEPTANCE: a reasoning task under budget pressure either downgrades to another
reasoning-capable provider or fails closed, and never lands on Perplexity.

ACCEPTANCE: no `reasoning_content` value appears in `getCallLog` output, in
memory, or in any returned payload, under any provider.

## Validation

The repository's own gate decides this, not a new one:

```bash
npm run verify:types
npm test
npm run lint
```

TEST: `tests/routing-matrix.test.ts` MUST cover reasoning resolution for both
the explicit-boolean and task-default paths.

TEST: `tests/capability-integrity.test.ts` MUST fail if the matrix advertises a
reasoning capability the transport cannot dispatch.

## Risk

RISK: widening the capability resolver touches the same code path as search
policy, and a regression there is silent — the router keeps returning routes,
they are just wrong. Existing search-policy tests MUST stay green unchanged.

RISK: dropping `reasoning_content` at the transport boundary could also drop
content consumers rely on if the field name collides with a legitimate payload
key. The drop MUST be keyed on the exact provider envelope field.
