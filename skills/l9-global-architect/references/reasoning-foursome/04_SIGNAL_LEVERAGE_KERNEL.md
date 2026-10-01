# L9 Signal Leverage Kernel

**Status:** First-class constitutional primitive  
**Version:** 1.0.0  
**Semantic owner:** evidence-bearing signal propagation, topology, meaning preservation, eligibility, reconvergence, evidence-bound write-back, and bounded signal loops  
**Normative source:** `references/L9_LEVERAGE_LAW_AND_RANKING_INVARIANTS_v1.0.md`

## 1. Cardinal Question

> **How should useful evidence and validated learning move through the L9 constellation so that meaning is preserved, eligible participants become stronger, authority remains intact, and feedback loops converge rather than amplify noise?**

Signal Leverage is a first-class L9 primitive.

It is separate from compounding leverage:

- **Leverage** decides whether a gain creates systemic value and what should become reusable.
- **Signal Leverage** governs how evidence-bearing signals carrying that gain move through the system safely and usefully.

Signal Leverage does NOT decide the intervention, invent consequences, or assign systemic value.

## 2. Constitutional Signal Law

> **Useful learning that cannot move safely is trapped leverage. Signal movement that carries no useful learning is noise.**

A valid signal path MUST preserve sufficient meaning for the downstream concern, respect semantic authority, reach only eligible consumers, and remain governable as it branches, reconverges, and feeds back.

## 3. Signal Envelope

A material signal SHOULD preserve the minimum semantic envelope required by its consumers:

```yaml
signal_envelope:
  signal_id: ""
  producer_ref: ""
  produced_at: ""
  concern: ""
  payload_ref: ""
  evidence_refs: []
  provenance_refs: []
  context_refs: []
  authority_ref: ""
  confidence: high|medium|low|unknown
  eligibility:
    consumer_classes: []
    exclusions: []
  propagation:
    generation: 0
    parent_signal_refs: []
    route_refs: []
  novelty_ref: ""
  convergence_ref: ""
```

Not every implementation must serialize this exact shape. The semantics must be preservable.

## 4. Canonical Signal Topologies

### SL-T1: One-way propagation

```text
A → B
```

A producer emits useful evidence to one eligible consumer.

Use when return flow adds no material value.

### SL-T2: Bidirectional leverage

```text
A ↔ B
```

A strengthens B and B returns non-redundant evidence, validation, context, or learning that strengthens A.

Bidirectional traffic is leverage only when the return path changes reachable behavior or reduces future decision cost. Echoes and acknowledgements alone do not qualify.

### SL-T3: Closed-loop / circular leverage

```text
A → B → C → A'
```

A signal traverses multiple participants and returns as changed state, evidence, constraint, or learning that improves a future traversal.

A valid closed loop requires:

- a distinguishable new state `A'`;
- evidence that the returned signal changed future behavior, capability, validation, knowledge, or cost;
- loop convergence controls; and
- no semantic authority theft.

Circularity without changed future behavior is not compounding leverage.

### SL-T4: Multi-directional spiderweb / mesh leverage

```text
                    ┌→ Ba ──────────┐
                    │                ↓
A → B ──────────────┼→ Bb → C → D → X
│                   │       ↘       ↑
│                   └→ Bc ───→ Z ───┘
│                              │
└──────────── learning ←───────┘
```

The mesh has no required global lap.

Signals MAY:

- branch;
- fan out;
- bypass intermediate participants;
- move laterally;
- move upstream or downstream;
- cross domains;
- diverge and reconverge;
- spawn productive subloops;
- return through feedback paths;
- create new eligible routes; and
- reshape future propagation topology.

Linear and circular flows are special cases of the mesh.

## 5. Signal Leverage Invariants

### SL-01: Signals MUST preserve useful meaning
A signal that loses required evidence, provenance, context, semantics, authority, or uncertainty destroys leverage.

### SL-02: Signal routing MUST follow usefulness and eligibility, not adjacency
The nearest participant is not automatically the right consumer. Signals may bypass or move laterally when that reduces loss, coupling, latency, duplicated ownership, or unnecessary hops.

### SL-03: Independent paths MAY multiply evidence, not copies
Multiple paths are justified only when they add non-redundant evidence, validation, context, interpretation, resilience, or consumer-specific transformation.

Duplicate transmission alone is not leverage.

### SL-04: Branches MUST earn their fan-out
Every branch MUST preserve, add, or transport useful meaning that would otherwise be unavailable. Irrelevant broadcast is negative leverage.

### SL-05: Reconvergence MUST synthesize
Reconverging paths SHOULD produce stronger state, decision support, constraint, evidence, or capability. Merely concatenating duplicate signals is not useful reconvergence.

### SL-06: Consequential write-back MUST be evidence-bound
A weak or isolated signal MUST NOT rewrite architectural authority, policy, or durable learning merely because it exists.

Promotion strength MUST be proportional to consequence, confidence, evidence quality, and authority level.

### SL-07: Write-back MUST preserve semantic ownership
Signals MAY challenge an owner's conclusion. They MUST NOT silently become the owner of the concern they update.

### SL-08: Write-back MUST change future reachable behavior to count as leverage
A returned signal becomes leverage when an eligible future action can consume it and behave differently through changed capability, constraints, validation, knowledge, routing, or decision cost.

Storage without consumption is not learning.

### SL-09: Closed loops MUST demonstrate state change
A loop that circulates unchanged information is not a leverage loop.

The return path MUST produce meaningful delta, such as corrected belief, improved model, stronger validation, promoted capability, reduced work, or safer constraint.

### SL-10: Signal loops MUST be bounded
Every local propagation loop MUST have one or more domain-appropriate controls such as:

- convergence criteria;
- idempotency;
- novelty detection;
- generation limits;
- thresholds;
- cooling periods;
- deduplication;
- quorum;
- supersession; or
- explicit terminal receipts.

The leverage system is persistent. Individual signal episodes are governable.

### SL-11: No global lap is required
Independent propagation paths and subloops MAY operate asynchronously. One productive loop need not wait for unrelated parts of the constellation to converge.

### SL-12: Validated shared gains SHOULD reach every eligible consumer
When Leverage identifies a shared gain and eligible beneficiary class, Signal Leverage SHOULD provide the lowest-drag governed dissemination path or record why propagation is unavailable.

Eligibility does not mean universal broadcast.

### SL-13: Topology escalation MUST be earned
One-way → bidirectional → closed-loop → mesh escalation is justified only when the additional topology creates useful evidence, learning, reuse, resilience, or reduced future work.

Connectivity theater is forbidden.

### SL-14: Signal drag MUST be visible
Latency, noise, duplicate routing, transformation loss, coupling, fan-out cost, stale context, and maintenance burden are material signal costs and MUST be exposed to Leverage evaluation.

### SL-15: Hard law outranks signal optimization
Signal reach never overrides correctness, safety, privacy, scope, ownership, security, or higher-authority architectural constraints.

## 6. Signal Propagation Contract

```yaml
signal_propagation_decision:
  source_signal_ref: ""
  concern: ""
  required_meaning:
    evidence: true
    provenance: true
    context: true
    authority: true
    uncertainty: true
  topology: one_way|bidirectional|closed_loop|mesh
  eligible_consumers: []
  excluded_consumers: []
  routes:
    - route_id: ""
      consumers: []
      adds_nonredundant_value: ""
      transformation_refs: []
  reconvergence:
    required: false
    synthesis_owner: ""
    expected_delta: ""
  loop_controls:
    novelty: ""
    idempotency: ""
    generation_limit: ""
    convergence: ""
  expected_signal_drag: []
  evidence_refs: []
```

## 7. Signal Propagation Receipt

```yaml
signal_propagation_receipt:
  signal_ref: ""
  topology_observed: one_way|bidirectional|closed_loop|mesh
  consumers_reached: []
  consumers_skipped: []
  meaning_preservation:
    evidence_preserved: true|false|unknown
    provenance_preserved: true|false|unknown
    context_preserved: true|false|unknown
    authority_preserved: true|false|unknown
    uncertainty_preserved: true|false|unknown
  nonredundant_value_added: []
  reconvergence_results: []
  write_back_results: []
  future_behavior_changed: []
  signal_drag_observed: []
  convergence:
    status: converged|partial|blocked|unknown
    control_refs: []
  leverage_evidence_refs: []
```

## 8. Write-Back Protocol

Signal Leverage MUST distinguish:

1. **observation** - evidence exists;
2. **challenge** - evidence may falsify a current conclusion;
3. **recommendation** - evidence supports a possible change;
4. **promotion candidate** - evidence supports durable reusable learning;
5. **promoted write-back** - the authoritative owner accepted a durable change.

Signal movement alone MUST NOT collapse these states.

## 9. Relationship to the Other Components

### First-Order → Signal Leverage
First-Order may emit intervention decisions, assumptions, and falsification criteria that need to reach downstream evaluators or future passes.

Signal Leverage MUST preserve the decision's ownership and MUST NOT select a replacement intervention.

### Second-Order → Signal Leverage
Second-Order emits predicted and observed consequence evidence, causal attribution, and forecast error.

Signal Leverage owns transporting that evidence to Leverage and later reasoning consumers without changing the consequence model.

### Leverage → Signal Leverage
Leverage identifies validated shared gains, eligible beneficiary classes, leverage-learning outputs, and mesh-value changes.

Signal Leverage owns governed dissemination and write-back.

### Signal Leverage → Leverage
Signal Leverage returns topology evidence, propagation receipts, fan-out, reconvergence, loop behavior, meaning preservation, and signal drag.

Leverage decides the systemic value of that observed topology.

## 10. Failure Modes

### SL-F01: Signal flattening
Evidence is reduced to an uncited summary that downstream consumers cannot verify.

### SL-F02: Broadcast theater
Signals are sent widely without eligibility or downstream value.

### SL-F03: Echo-loop theater
A circular path exists but no future behavior changes.

### SL-F04: Connectivity inflation
More edges are treated as higher leverage without evidence.

### SL-F05: Authority laundering
A signal is promoted into policy or truth without the semantic owner accepting it.

### SL-F06: Duplicate-knowledge multiplication
The same intelligence is copied into many places, creating drift rather than leverage.

### SL-F07: Runaway recursion
Loops trigger themselves without novelty, threshold, idempotency, cooling, or convergence controls.

### SL-F08: Reconvergence without synthesis
Branches return and are merely concatenated instead of producing stronger state.

### SL-F09: Signal loss
Evidence, provenance, uncertainty, context, or authority is stripped in transit.

### SL-F10: Trapped leverage
A validated shared gain exists but no governed route reaches eligible consumers.

## 11. Architecture Test

A proposed signal edge, callback, event, bus, write-back, or feedback loop MUST answer:

1. What useful meaning moves?
2. Which eligible consumer becomes more capable?
3. What non-redundant value does this path add?
4. Why is this topology better than a simpler path?
5. What evidence and provenance remain attached?
6. Who owns any consequential state change?
7. How does the loop converge?
8. What future behavior changes if propagation succeeds?
9. What signal drag does the path create?

If these cannot be answered, the signal path has not earned admission.
