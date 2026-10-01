# L9 Leverage Law and Ranking Invariants

**Status:** Converged architecture baseline  
**Version:** 1.0.0  
**Scope:** Entire L9 constellation  
**Applies to:** repositories, nodes, modules, agents, tools, dependencies, libraries, services, contracts, schemas, APIs, adapters, prompts, skills, models, memory, data, policies, validators, tests, CI, observability, infrastructure, workflows, fixes, improvements, learned heuristics, generated intelligence, and any future architectural participant or retained element.

---

## 1. North-Star Law

> **Everything L9 builds, adopts, learns, changes, or retains MUST increase the constellation's capacity to make its other parts and future parts more capable. Every useful gain MUST be reusable by every eligible participant, and every realized improvement MUST expand the leverage available for subsequent improvements.**

L9 does not measure architectural value only by what a component can do locally.

Its deeper value is determined by:

1. what it enables other participants to do;
2. what it allows them to stop rediscovering or rebuilding;
3. what new leverage paths it creates;
4. what learning it returns to the constellation; and
5. how much stronger the constellation becomes because the participant exists.

A component that performs useful local work but creates no sufficient reusable or systemic advantage is below the L9 leverage standard.

---

# 2. Universal Constellation Leverage Invariants

## UCL-01: Every participant MUST be a leverage multiplier

Every participant in the L9 constellation MUST increase useful leverage somewhere beyond its isolated local function.

A participant qualifies as a leverage multiplier when it materially contributes one or more of the following:

- reusable capability;
- reusable intelligence or knowledge;
- reduced uncertainty;
- reduced repeated work;
- stronger validation;
- improved reliability;
- better interoperability;
- increased automation;
- improved optionality;
- better reach or propagation;
- lower friction;
- lower risk;
- clearer ownership;
- stronger contracts or schemas;
- better defaults;
- better observability;
- stronger learning capacity;
- improved future decision quality;
- improved future participants.

A participant that adds maintenance, coupling, cognitive burden, failure surface, or ownership complexity without producing sufficient leverage in return is **negative leverage**.

Necessary plumbing is not exempt. It earns its place by enabling a higher-order leverage multiplier that cannot be achieved more simply.

## UCL-02: Shared gains MUST propagate

A validated improvement created anywhere in the constellation MUST become available to every eligible participant that can benefit from it without independent rediscovery.

**One learns. Eligible many become stronger.**

Eligibility may depend on compatibility, scope, authority, safety, version, domain, or capability requirements. Eligibility does not mean blind universal adoption.

The invariant is that validated shared value must not remain trapped inside one participant when the constellation can safely reuse it.

## UCL-03: Local optimization MUST NOT reduce systemic leverage

A change is not an L9 improvement merely because one component becomes locally better.

A local improvement fails the leverage standard when it materially reduces constellation-wide:

- interoperability;
- reusable capability;
- learning capacity;
- optionality;
- maintainability;
- future integration freedom;
- ownership clarity;
- propagation quality; or
- total useful leverage.

GAR and downstream architecture judgments must therefore evaluate important changes at the constellation boundary, not only at the local component boundary.

## UCL-04: Admission and retention are earned

Every addition to the constellation MUST justify its leverage contribution.

Every retained element MUST continue to justify its cost, coupling, maintenance burden, cognitive load, and failure surface relative to the leverage it creates or enables.

Valid leverage moves include:

- add;
- improve;
- share;
- consolidate;
- replace;
- simplify;
- delete.

Deletion can be highly leveraged when it removes duplicate responsibility, friction, drift, or unnecessary architecture.

## UCL-05: Leverage follows usefulness, not adjacency

A participant may strengthen another participant directly or indirectly.

The constellation MUST NOT require artificial direct connections merely to prove systemic value.

A shared primitive, policy, contract, tool, dependency, learned heuristic, or capability may strengthen distant consumers through existing propagation mechanisms.

The law is systemic benefit, not full graph connectivity.

---

# 3. Compounding Leverage Law

## CL-01: Leverage MUST accumulate across participants

Each participant in a valid leverage path MUST leave downstream eligible participants with a stronger operating position than they would otherwise have had.

A participant must not merely consume prior work. It must preserve and, where applicable, increase the leverage it received.

Conceptually:

```text
A
↓
creates leverage for B
↓
B consumes A's gain and adds its own
↓
C receives accumulated leverage from A + B
↓
C adds further leverage
↓
...
```

This is **cumulative capability transfer**.

## CL-02: Realized outcomes MUST be capable of becoming learning

An output is not the end of a leverage process.

Where measurable consequences exist, the system must be capable of observing:

- what worked;
- what failed;
- what changed;
- what created value;
- what created friction;
- which assumptions held;
- which predictions were wrong; and
- which reusable improvement should result.

Raw telemetry is not enough. Useful outcomes must be transformable into reusable learning.

## CL-03: Learning MUST alter a future baseline

Learning compounds only when future work can consume it.

```text
prior baseline
    ↓
execution
    ↓
realized outcome
    ↓
learning
    ↓
durable improvement
    ↓
stronger future baseline
```

A report, database record, metric, or observation that no future participant consumes does not by itself constitute compounding leverage.

## CL-04: Cycle convergence does not terminate the leverage system

A **cycle convergence event** occurs when a bounded propagation process stabilizes sufficiently for its result to become usable system state.

Convergence terminates an episode, not the leverage system.

The leverage system is intentionally persistent. Realized improvements remain available to generate new leverage paths, new signals, new subloops, and new propagation waves.

## CL-05: Compounded leverage creates new available leverage

L9 distinguishes four related concepts:

### Available leverage
An evidenced leverage opportunity reachable from the current system state.

### Predicted leverage
The improvement expected if that opportunity is exploited.

### Realized leverage
The improvement actually observed after execution.

### Compounded leverage
The additional future leverage made possible because realized leverage became part of the system.

Conceptually:

```text
available leverage
      ↓
predicted leverage
      ↓
intervention
      ↓
realized leverage
      ↓
learning + durable improvement
      ↓
expanded available leverage
      ↓
new interventions
```

Predicted and realized leverage MUST remain distinct. Forecast error is itself learning.

## CL-06: The system SHOULD seek an increasing leverage slope

The constellation should not merely accumulate more components.

It should seek increasing marginal systemic leverage as reusable capabilities, learned intelligence, propagation paths, and productive subloops accumulate.

Conceptually, if `L_n` represents constellation leverage after change `n`:

```text
L_(n+1) > L_n
```

The stronger L9 aspiration is:

```text
ΔL_(n+1) > ΔL_n
```

This is a directional architectural objective, not permission to fabricate numerical precision.

The goal is a continuously steepening leverage curve: each improvement makes future improvement easier, broader, safer, or more powerful.

---

# 4. Leverage Topologies

Leverage topology describes **how leverage propagates**, not merely whether a component is useful.

Higher leverage topologies create more opportunities for reuse, feedback, learning, fan-out, and compounding.

## Topology A: One-way leverage

```text
A → B
```

A improves B's operating position.

This is useful but structurally limited.

## Topology B: Bidirectional leverage

```text
A ↔ B
```

A strengthens B and B returns useful leverage that strengthens A.

Bidirectional participation has greater leverage potential than one-way participation because improvement can recursively affect both participants.

## Topology C: Circular or closed-loop leverage

```text
A → B → C → A'
```

A useful output traverses multiple participants and returns as new system state that improves a future traversal.

A closed loop is not a terminated loop. It is a connected feedback path through which leverage may continue to circulate and compound.

A cycle may converge locally while the loop remains available for future activity.

## Topology D: Multi-directional leverage mesh

```text
                    ┌→ Ba ──────────┐
                    │                ↓
A → B ──────────────┼→ Bb → C → D → X
│                   │       ↘       ↑
│                   └→ Bc ───→ Z ───┘
│                              │
└──────────── learning ←───────┘
```

The leverage mesh is not a racetrack and has no required global lap.

Leverage may:

- branch;
- fan out;
- bypass intermediate participants;
- propagate laterally;
- move upstream;
- move downstream;
- cross domains;
- reconverge;
- spawn subloops;
- return through feedback paths;
- create new participants or edges; and
- reshape the mesh itself.

The linear and circular models are special cases of the broader leverage mesh.

---

# 5. Multi-Directional Leverage Mesh Invariants

## MLM-01: Leverage MAY branch

Any participant may produce multiple leverage-bearing outputs when distinct eligible consumers or concerns benefit.

Architecture must not force all leverage through one artificial linear pipeline.

## MLM-02: Every meaningful branch MUST multiply leverage

A branch is justified only when it adds, preserves, or transports useful leverage that would otherwise be lost or unavailable.

Branches that create no meaningful leverage are unnecessary complexity.

## MLM-03: Branches MAY diverge and reconverge

Different branches may perform specialized transformations and later recombine.

Reconvergence SHOULD synthesize a stronger system state, decision, capability, or constraint rather than merely concatenate outputs.

## MLM-04: Leverage MAY bypass participants

Useful leverage may move directly to a distant eligible participant when forcing it through intermediate participants would add coupling, latency, loss, or unnecessary ownership.

## MLM-05: Leverage MAY propagate laterally

Sibling participants may strengthen each other even when neither is formally upstream or downstream of the other.

Upstream and downstream are useful local descriptions, not a complete model of constellation leverage.

## MLM-06: One validated gain SHOULD strengthen many eligible participants

When a validated improvement belongs to a shared capability, the correct shared owner MUST make the improvement available to every eligible consumer without independent rediscovery.

This is the constellation equivalent of a learned capability being promoted once and distributed across an eligible fleet.

## MLM-07: Productive subloops are leverage accelerators

The constellation SHOULD create and preserve local feedback subloops that can improve independently without waiting for a global cycle.

Example:

```text
Ba → E → evaluation → learning → Ba'
```

At the same time:

```text
Bb → F → X → shared capability → Bb'
```

Each subloop can increase leverage elsewhere in the mesh. Overlapping productive subloops therefore increase the rate at which leverage compounds system-wide.

## MLM-08: No global lap is required

The leverage mesh MUST NOT assume a single ordered global cycle.

Multiple propagation paths and subloops may operate asynchronously. A new leverage wave may begin before unrelated parts of the mesh have converged.

## MLM-09: The mesh itself MAY improve

Realized leverage can reveal:

- new reusable capabilities;
- new participants;
- better edges;
- unnecessary participants;
- new shared owners;
- new consumers;
- better propagation paths;
- better subloops.

Therefore leverage does not merely flow through the architecture. It can improve the architecture through which future leverage flows.

## MLM-10: The system SHOULD increase leverage density

Over time the constellation should trend toward:

- fewer dead-weight participants;
- fewer repeated discoveries;
- stronger shared capabilities;
- greater eligible reuse;
- better fan-out;
- higher-quality reconvergence;
- more productive subloops;
- stronger learning propagation;
- lower friction;
- fewer preventable failures; and
- more reusable advantage per unit of architectural complexity.

---

# 6. Signal Leverage Law

Signal leverage is a separate concern from compounding leverage.

Compounding leverage defines how capability accumulates.

Signal leverage defines how evidence-bearing observations move through the architecture so that useful learning can safely influence future behavior.

## SL-01: Signals MUST preserve useful meaning

A signal that loses the evidence, provenance, context, or semantics needed by downstream consumers destroys leverage.

## SL-02: Independent signal paths MAY increase leverage

Multiple non-redundant paths may add different evidence, validation, context, or interpretation before convergence.

Duplicate transmission alone is not multiplicative leverage.

## SL-03: Consequential write-back MUST be evidence-bound

A single weak signal must not rewrite architectural authority merely because it exists.

Consequential promotion should require sufficient evidence for the specific risk and authority involved.

## SL-04: Write-back MUST change future behavior to count as leverage

Signal return alone is not compounding.

A write-back becomes leverage when it changes future reachable behavior, capability, constraints, validation, knowledge, or decision cost.

## SL-05: Signal loops MUST avoid unbounded recursion

Local signal cycles must have convergence, idempotency, novelty, threshold, cooling, or equivalent controls appropriate to their domain.

The leverage system is persistent. Individual signal propagation episodes must still remain governable.

---

# 7. Leverage Rank: First-Class L9 Primitive

## 7.1 Purpose

Every significant L9 participant MUST expose a **Leverage Rank** as part of its architectural identity or fingerprint.

The rank represents the strongest evidenced leverage topology in which the participant materially participates.

Higher ranks represent structurally greater leverage potential because the participant contributes to broader feedback, reuse, propagation, and compounding surfaces.

A rank is not earned by documentation claims. It is earned by evidenced architecture and behavior.

## 7.2 Canonical Leverage Rank Ladder

### LR-0: Negative or dead-weight leverage

The participant creates more cost, coupling, maintenance, risk, or cognitive burden than useful leverage.

**Disposition:** remove, replace, consolidate, or redesign.

### LR-1: Local multiplier

The participant provides useful local leverage and improves at least one eligible downstream consumer or higher-order capability.

It is not yet meaningfully reciprocal or recursive.

### LR-2: Bidirectional multiplier

The participant participates in at least one evidenced bidirectional leverage relationship in which both sides become stronger through reciprocal useful output.

```text
A ↔ B
```

### LR-3: Closed-loop multiplier

The participant materially participates in an evidenced multi-step feedback loop where realized output returns as useful system state and improves future execution.

```text
A → B → C → A'
```

### LR-4: Multi-directional mesh multiplier

The participant materially participates in an evidenced leverage mesh involving multiple useful directions such as branching, fan-out, lateral propagation, bypass, reconvergence, or multiple simultaneous leverage paths.

```text
      → B1 → C1
A → B → B2 → C2 → X
      → B3 → Z
```

### LR-5: Constellation compounding multiplier

The participant materially contributes to a continuously learning leverage mesh where:

- multiple productive subloops exist;
- realized outcomes create durable learning;
- shared gains propagate to eligible consumers;
- new available leverage is created;
- future baselines improve;
- the participant helps other participants improve their own leverage rank or score; and
- the constellation's leverage capacity measurably or evidentially increases because of the participant.

LR-5 is the current highest leverage rank.

It represents a participant that does not merely operate inside the constellation. It helps the constellation become better at improving itself.

---

# 8. Rank Promotion Law

Every L9 participant MUST strive toward the highest leverage rank that is justified by its purpose, scope, safety, and architecture.

Promotion MUST NOT be achieved by adding meaningless edges or artificial feedback loops.

A leverage rank promotion requires evidence that the new topology creates additional useful leverage.

## Promotion principle

```text
more connections ≠ more leverage
more loops ≠ more leverage
more files ≠ more leverage
more complexity ≠ more leverage
```

Promotion requires **more useful systemic advantage**.

## Promotion examples

### LR-1 → LR-2
A previously one-way tool begins consuming validated downstream feedback that improves its own future output.

### LR-2 → LR-3
A reciprocal relationship becomes part of a multi-step closed loop whose returned learning changes future behavior.

### LR-3 → LR-4
The participant gains useful fan-out, lateral propagation, bypass, reconvergence, or multiple simultaneous leverage paths.

### LR-4 → LR-5
The participant becomes part of a learning constellation where local subloops compound, shared improvements propagate, future baselines rise, and the participant helps create new leverage elsewhere in the mesh.

## Demotion

Leverage rank MUST be demotable when evidence shows that the claimed topology is stale, broken, unused, non-beneficial, or no longer compounds useful leverage.

Rank is current architectural truth, not a permanent badge.

---

# 9. Leverage Score: First-Class L9 Primitive

## 9.1 Rank and score are different

**Leverage Rank** describes topology and structural leverage class.

**Leverage Score** measures how effectively the participant is realizing leverage within its current architecture.

A participant MUST NOT claim a high score merely because it has a high rank.

Likewise, excellent execution at LR-2 does not silently become LR-4. Topology promotion requires its own evidence.

## 9.2 Canonical score range

Leverage Score is an integer from **0 to 100**.

Scores MUST be evidence-backed and MUST NOT use fake decimal precision.

Recommended dimensions:

| Dimension | Weight | Core question |
|---|---:|---|
| Realized systemic improvement | 25 | What measurable or strongly evidenced improvement did this participant actually create? |
| Eligible consumer strengthening | 20 | How much did eligible participants become more capable because of it? |
| Reuse and propagation | 15 | How effectively do useful gains propagate without rediscovery? |
| Learning and feedback return | 15 | Does real-world or runtime evidence improve future behavior? |
| Leverage creation | 10 | Does this participant create new available leverage, new subloops, or new capabilities? |
| Friction and maintenance efficiency | 10 | How much leverage is retained after maintenance, complexity, latency, and cognitive costs? |
| Evidence quality and recency | 5 | How current, direct, and trustworthy is the supporting evidence? |
| **Total** | **100** | |

The score contract may evolve as empirical L9 measurement matures, but the separation of topology rank from realized leverage score is invariant.

## 9.3 Grade

A human-readable grade MAY be derived from the score:

- **A:** 90-100
- **B:** 80-89
- **C:** 70-79
- **D:** 60-69
- **F:** below 60

Grades are summaries, not substitutes for the underlying evidence.

---

# 10. Leverage Fingerprint

Every significant L9 participant MUST expose a current **Leverage Fingerprint** at an authoritative identity surface that agents can reliably discover.

For repositories, the fingerprint MUST be part of the repository's canonical identity surface.

For non-repository components, modules, tools, dependencies, and agents, the fingerprint MUST live in the authoritative metadata, manifest, README, registry, or equivalent surface actually used for discovery.

There MUST be one semantic owner for the fingerprint. Derived displays MAY project it but MUST NOT become competing authorities.

## Canonical semantic fields

```yaml
leverage_fingerprint:
  leverage_rank: LR-0|LR-1|LR-2|LR-3|LR-4|LR-5
  leverage_score: 0-100
  leverage_grade: A|B|C|D|F
  topology_class: local|bidirectional|closed_loop|multidirectional_mesh|constellation_compounding
  status: predicted|partially_realized|realized|degraded|unknown
  available_leverage: []
  predicted_leverage: []
  realized_leverage: []
  compounded_leverage: []
  strengths_provided: []
  eligible_consumers_strengthened: []
  productive_subloops: []
  learning_returns: []
  propagation_surfaces: []
  friction_or_drag: []
  evidence_refs: []
  measured_at: null
  next_rank_target: null
  promotion_requirements: []
  blockers_or_unknowns: []
```

The exact physical storage path is intentionally not fixed by this doctrine. Storage belongs to the relevant identity, repository, or constellation architecture owner.

The semantic primitive is fixed.

---

# 11. Leverage Evaluation Rules

## LE-01: Rank requires evidence

No participant may self-assign a rank based only on intended architecture.

Predicted future topology may be recorded, but current rank reflects current evidenced participation.

## LE-02: Score requires realized evidence

Predicted benefit MUST remain separate from realized benefit.

Unknown or inaccessible evidence MUST remain Unknown rather than being converted into an optimistic score.

## LE-03: High rank does not excuse low realized value

A participant may occupy LR-4 structurally and still have a weak leverage score.

This indicates under-realized mesh potential, not automatic excellence.

## LE-04: High score does not fabricate higher topology

A highly effective LR-2 participant remains LR-2 until evidence supports promotion.

## LE-05: Scores MUST account for drag

Maintenance burden, unnecessary complexity, duplicated ownership, latency, operational risk, and cognitive cost reduce realized leverage.

Gross capability is not net leverage.

## LE-06: Improvements SHOULD raise either rank, score, or both

Every significant architectural improvement should be evaluated for whether it:

- raises realized leverage score;
- enables a leverage rank promotion;
- strengthens another participant's score or promotion path; or
- removes negative leverage.

If none applies, the improvement's systemic value should be challenged.

---

# 12. Agents: Stronger Leverage Requirements

Agents are first-class leverage participants and MUST expose a Leverage Fingerprint.

Agents will eventually be evaluated, compared, ranked, scored, graded, improved, and potentially selected competitively.

Agent evaluation MUST prioritize realized systemic leverage over superficial activity metrics.

Useful agent leverage evidence includes:

- reduction in repeated human intervention;
- improved downstream agent success;
- improved quality of generated artifacts;
- reusable learning returned to the constellation;
- reduction in repeated failure classes;
- stronger contracts, plans, evidence, or decisions for downstream agents;
- productive participation in subloops;
- improved future execution from prior outcomes;
- propagation of validated improvements to eligible peers;
- reduced execution friction or uncertainty;
- creation of new available leverage.

Token count, task count, message count, raw activity, or apparent autonomy are NOT themselves leverage.

## Agent competition principle

Agents SHOULD compete on **realized net leverage**.

A stronger agent is not merely one that completes more tasks. It is one that leaves the surrounding system more capable after its work.

Agent comparison MUST preserve task and scope comparability and MUST resist metric gaming.

---

# 13. Anti-Gaming and Failure Invariants

## AG-01: Connectivity theater is forbidden

Adding edges, integrations, callbacks, events, or feedback paths solely to increase apparent leverage rank is negative leverage.

## AG-02: Circularity without learning is not compounding

A loop that repeatedly circulates unchanged information is not a leverage loop.

## AG-03: Broadcast without eligibility is not leverage

Propagation to irrelevant consumers creates noise, coupling, and risk.

## AG-04: Storage without consumption is not learning

Persisted information becomes leverage only when an eligible future action can consume it and behave differently.

## AG-05: Duplicate knowledge is not multiplication

Copying the same intelligence into many places without a canonical owner increases drift rather than leverage.

## AG-06: High fan-out can be negative leverage

Fan-out is beneficial only when intended consumers receive useful value with acceptable coupling and maintenance cost.

## AG-07: Scores MUST NOT become the objective

Leverage scores are measurements of systemic value, not targets to game.

When optimizing the metric harms the underlying constellation, the metric has failed and MUST be revised.

## AG-08: Hard architectural law outranks leverage optimization

Leverage never overrides correctness, security, safety, explicit scope, ownership, mandatory contracts, or higher-authority architectural invariants.

---

# 14. Leverage Mesh Doctrine

The L9 constellation should be understood as a living leverage mesh rather than a linear pipeline or single circular loop.

Life, code, learning, and leverage are not naturally linear.

Within the mesh:

- participants multiply leverage;
- useful gains propagate;
- branches specialize;
- subloops learn independently;
- branches reconverge;
- learning changes future baselines;
- improvements create new improvement opportunities;
- the mesh itself evolves;
- stronger participants help other participants become stronger;
- constellation-wide leverage compounds continuously.

The highest architectural value comes from participants that make other participants better at making still more participants better.

---

# 15. Canonical L9 Leverage Doctrine

> **Everything in L9 MUST be a leverage multiplier.**
>
> **Every validated shared gain MUST become available to every eligible participant without independent rediscovery.**
>
> **Every participant MUST strive toward the highest justified leverage rank.**
>
> **Bidirectional leverage is stronger than isolated one-way leverage. Closed-loop leverage is stronger than simple reciprocity when returned outcomes improve future behavior. Multi-directional mesh leverage is stronger still because leverage can branch, fan out, bypass, propagate laterally, reconverge, and participate in multiple productive subloops. Constellation-compounding leverage is the highest current rank because realized learning repeatedly strengthens the system that generates the next improvement.**
>
> **Individual cycles may converge. The leverage system does not terminate.**
>
> **The architectural objective is not merely more components or more connections. It is a continuously improving constellation in which each addition, improvement, dependency, tool, agent, artifact, and learned result increases the system's capacity to create still more leverage.**

---

# 16. Locked Concepts

The following concepts are considered converged by this document:

1. **Universal leverage scope:** the law applies to everything in the constellation, not only nodes or repositories.
2. **Mandatory multiplier:** every participant MUST create or enable sufficient leverage.
3. **Shared-gain propagation:** one validated improvement should strengthen every eligible consumer.
4. **Persistent compounding:** realized leverage creates new available leverage.
5. **Cycle convergence:** bounded episodes may converge without terminating the persistent leverage system.
6. **Linear leverage as a special case:** linear and simple circular loops are valid but lower-order topologies.
7. **Multi-directional leverage mesh:** leverage may branch, bypass, propagate laterally, reconverge, and reshape its own topology.
8. **Subloop acceleration:** creative productive subloops increase the rate of system-wide compounding.
9. **Leverage Rank:** topology participation is a first-class identity primitive.
10. **Leverage Score:** realized leverage is a first-class measurable primitive distinct from rank.
11. **Leverage Fingerprint:** every significant participant exposes its current rank, score, evidence, leverage surfaces, and promotion path.
12. **Promotion:** every participant strives toward the highest justified leverage rank without artificial complexity.
13. **Demotion:** stale or unrealized topology claims lose rank.
14. **Agent leverage:** agents are ranked and improved by realized systemic leverage, not activity theater.
15. **Increasing leverage slope:** L9 seeks increasing marginal systemic leverage as the constellation matures.

---

**End of canonical leverage invariants baseline.**
