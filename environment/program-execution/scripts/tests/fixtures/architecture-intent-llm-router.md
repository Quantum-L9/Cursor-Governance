# LLM-Router Reasoning Provider Microscope

owner: Igor Beylin
target_repo: `Quantum-L9/LLM-Router`

This is a long-form architecture microscope of the LLM-Router reasoning plane.
It was produced as free prose by an architecture review session, not as a
numbered task list, and it is intentionally dense: current-state observations,
governing obligations, migration sequencing, explicit deferrals, and test
expectations all live in ordinary Markdown. The Program Execution architecture
compiler is expected to compile this document directly, without any manual
rewrite into Release blocks, numbered tasks, or activation YAML.

## Executive summary

The router currently treats every provider as interchangeable chat capacity.
That worked while all traffic was conversational. It stops working the moment
reasoning-class requests carry governance obligations: reasoning traffic has a
distinct cost envelope, a distinct privacy envelope, and a distinct provider
contract. The architecture decision is to make reasoning a first-class routed
capability with one governed primary provider and hard boundaries around every
other provider's role.

## Provider roles

| Provider | Role | Boundary |
| --- | --- | --- |
| DeepSeek | governed reasoning | DeepSeek MUST be the primary governed reasoning provider for all reasoning-class requests. |
| Perplexity | research retrieval | Perplexity is research-only and MUST NOT serve reasoning-class requests. |
| OpenRouter pool | conversational overflow | Overflow traffic keeps the existing conversational contract. |

The Perplexity boundary is absolute at this stage: Perplexity reasoning models
MUST NOT be reachable through any routing path, including fallback and retry
paths. A reasoning request that cannot be served by DeepSeek fails closed
rather than silently degrading to a research provider.

## Capability authority

The `requiresReasoning` request field becomes the canonical capability
authority for reasoning routing. Today three separate heuristics guess at
reasoning intent from prompt length, model-name hints, and caller metadata.
All three heuristics MUST be subordinated to `requiresReasoning`: the field
decides, and the heuristics survive only as telemetry annotations.

The control plane MUST reuse the existing DeepSeek and reasoning-depth
vocabulary already shipped in the router configuration schema. Do not mint a
parallel vocabulary for the same concepts.

### Current state observed

The current dispatch table lives in `src/router/dispatch.ts` and the
capability flags live in `src/router/capabilities.ts`. The dispatch decision
and the provider call are made in two different modules today, which is where
drift can hide. Nothing in this section is an instruction; it is the observed
baseline the obligations below are written against.

```ts
// Observed shape, current main. Illustrative only — inert source material.
const route = pickProvider(request);      // decision
const reply = providers[route].call(req); // dispatch
```

## Dispatch integrity

The route decision recorded in the audit log MUST equal the actual provider
dispatch for every request. Any divergence between the decision record and
the dispatched provider is a correctness defect, not an observability gap.

## Budget behavior

Budget pressure MUST downgrade a reasoning request only within its capability
family, using cache-hit token counts from the transport layer for budget
accounting. A reasoning request under budget pressure downgrades to a cheaper
reasoning configuration; it never crosses into the research family.

Determine whether the transport layer already exposes cache-hit token counts
for budget accounting. This is answerable by reading the transport response
handling in the repository; downstream budget work builds on that answer.

## Composite capabilities fail closed

Two composite requests are not yet governed and MUST fail closed initially:

- A request combining search and reasoning MUST fail closed at intake.
- A request combining vision and reasoning MUST fail closed at intake.

Failing closed here is deliberate scope control: each composite needs its own
governance review before it can be routed at all.

## Privacy invariant

The provider-side `reasoning_content` field is never persisted and never
exposed to callers. It MUST NOT appear in logs, audit records, cached
responses, or API replies. This invariant holds across every provider and
every storage layer the router touches.

## Existing invariants preserved

The existing circuit-breaker, budget-enforcement, and audit-trail invariants
MUST remain intact through this migration. The reasoning plane extends those
mechanisms; it does not fork them. Any change that weakens an existing
circuit, budget, or audit guarantee is out of bounds regardless of how much
it simplifies the reasoning path.

## Sequencing

The capability authority migration must precede the dispatch integrity work,
because the audit comparison is only meaningful once `requiresReasoning` is
the deciding field. Budget behavior work must precede the composite intake
gates, since the composite gates reuse the budget family classification.

## Deferred: research-to-reasoning composite

A research-then-reasoning composite pipeline (Perplexity retrieval feeding
DeepSeek reasoning) is explicitly staged for a later phase and is deferred
from this program. It stays visible as a deferral: nothing in this program
may quietly implement it, and nothing in this program may make it harder to
implement later.

## Risks

The main migration risk is silent behavior drift while the heuristics are
subordinated: a request routed differently by the field than by the old
heuristics changes cost attribution. Treat divergence telemetry as the
mitigation, not manual review of individual requests.

There is an assumption that the existing configuration schema can accept the
reasoning-depth field additively without a breaking version bump; validate
that assumption against the schema tests during implementation and roll back
the additive field if it is falsified.

## Validation expectations

Routing behavior is validated with the repository's own test suite; the
following commands are the acceptance floor for the routing work:

- npm test --silent -- test/routing.test.ts
- npm run lint --silent

Acceptance for the privacy invariant: a regression test proves
`reasoning_content` is absent from logs, audit records, cache entries, and
API replies for a reasoning-class request served end to end.
