# L9 Reasoning Foursome Architecture

**Status:** Converged four-kernel baseline  
**Version:** 1.0.0  
**Scope:** L9 reasoning architecture  
**Components:** First-Order Thinking Kernel, Second-Order Consequence Lens, Leverage Kernel, Signal Leverage Kernel

## 1. Constitutional Rule

Every reasoning component in this pack MUST comply with the L9 Leverage Law and MUST preserve exactly one semantic owner per concern.

The four components are complementary and non-competing:

1. **First-Order Thinking Kernel** owns governing cause and intervention selection through causal compression and work elimination.
2. **Second-Order Consequence Lens** owns predicted and observed consequence surfaces plus prediction-versus-observation learning.
3. **Leverage Kernel** owns systemic value evaluation, predicted/realized/compounded leverage, rank, score, fingerprint, and mesh-value improvement.
4. **Signal Leverage Kernel** owns evidence-bearing propagation: meaning-preserving signal movement, topology, branching, reconvergence, eligibility, safe write-back, and bounded signal loops.

Signal Leverage is a first-class primitive. It is not a subsection of Leverage and not a transport implementation detail.

## 2. Why Signal Leverage Is Separate

Compounding leverage answers:

> **What systemic value exists, was realized, and should strengthen the constellation?**

Signal leverage answers:

> **How does the evidence-bearing signal carrying that value move through the constellation without losing meaning, stealing authority, creating noise, or recursing without bound?**

A system can identify valuable learning and still lose it through bad propagation. Conversely, a system can move many signals while creating no leverage. The concerns therefore require separate semantic owners.

## 3. Canonical Architecture

```text
                         L9 LEVERAGE LAW
                                │
                                ▼
                      FIRST-ORDER THINKING
                  governing cause + intervention
                                │
                                ▼
                   SECOND-ORDER CONSEQUENCE LENS
                 predict → execute → observe → compare
                                │
                     evidence-bearing outputs
                                ▼
                    SIGNAL LEVERAGE KERNEL
           preserve → route → branch → reconverge → bound
                     │                       │
                     │                       └───────────────┐
                     ▼                                       │
                      LEVERAGE KERNEL                        │
       value → rank → score → compounding → mesh improvement│
                     │                                       │
                     └──── eligible validated learning ──────┘
                                      │
                                      ▼
                         SIGNAL LEVERAGE WRITE-BACK
                 targeted propagation to eligible consumers
                                      │
                                      ▼
                         stronger future reasoning baseline
```

Signal Leverage is not merely a serial stage. It is the governed propagation plane through which evidence and validated learning move among the other three components and the wider L9 constellation.

## 4. Canonical Flow

```text
objective
  -> First-Order selects the governing intervention
  -> Second-Order BEFORE predicts material consequences
  -> Signal Leverage preserves and routes the prediction evidence
  -> Leverage evaluates predicted systemic value and drag
  -> execution occurs outside the reasoning foursome
  -> Second-Order AFTER observes consequences and forecast error
  -> Signal Leverage preserves and routes observed evidence
  -> Leverage evaluates realized and compounded leverage
  -> Leverage identifies eligible shared gains and future baseline changes
  -> Signal Leverage performs evidence-bound, eligibility-bound write-back
  -> future First-Order, Second-Order, Leverage, and eligible L9 participants consume stronger state
```

## 5. Signal Topology Model

Signal Leverage recognizes four canonical propagation topologies.

### One-way

```text
A → B
```

Useful signal moves from producer to consumer.

### Bidirectional

```text
A ↔ B
```

Each side returns non-redundant evidence or learning that can improve the other.

### Closed-loop / circular

```text
A → B → C → A'
```

A signal traverses multiple participants and returns as changed state, evidence, or constraint that improves a future traversal.

Circularity without changed future behavior is not leverage.

### Multi-directional mesh

```text
                    ┌→ Ba ──────────┐
                    │                ↓
A → B ──────────────┼→ Bb → C → D → X
│                   │       ↘       ↑
│                   └→ Bc ───→ Z ───┘
│                              │
└──────────── learning ←───────┘
```

Signals may branch, fan out, bypass, move laterally, reconverge, spawn productive subloops, and reshape future propagation paths. No global lap is required.

## 6. Non-Collision Ownership Table

| Concern | Semantic owner | Other components may |
|---|---|---|
| Locked objective | First-Order | consume; flag contradiction |
| Governing cause | First-Order | falsify with evidence |
| Intervention selection | First-Order | challenge, never replace silently |
| Predicted consequence surface | Second-Order | consume |
| Observed consequence surface | Second-Order | consume |
| Prediction/observation comparison | Second-Order | consume forecast error |
| Predicted systemic leverage | Leverage | provide evidence only |
| Realized systemic leverage | Leverage | provide evidence only |
| Compounded leverage | Leverage | consume resulting learning |
| Leverage Rank / Score / Fingerprint | Leverage | expose topology/evidence only |
| Signal envelope and meaning preservation | Signal Leverage | supply payload |
| Signal path and topology semantics | Signal Leverage | value the path, not route it |
| Branch / fan-out / bypass / reconvergence | Signal Leverage | request or consume paths |
| Eligibility-bound propagation | Signal Leverage | Leverage identifies gain/eligible value class |
| Evidence-bound write-back | Signal Leverage | semantic owners accept/reject returned evidence |
| Signal-loop convergence and recursion control | Signal Leverage | expose domain convergence criteria |
| Future intervention judgment | First-Order on next pass | consumes returned learning |

## 7. Hard Separation Rules

### FOUR-01: Exactly one semantic owner per concern
No component may silently absorb another component's concern.

### FOUR-02: First-Order selects interventions
Second-Order, Leverage, and Signal Leverage may challenge with evidence but MUST return intervention selection to First-Order.

### FOUR-03: Second-Order owns consequences
Leverage and Signal Leverage MUST NOT invent predicted or observed consequence paths.

### FOUR-04: Leverage owns systemic value
Second-Order and Signal Leverage MUST NOT assign Leverage Rank, Score, or net systemic value.

### FOUR-05: Signal Leverage owns propagation semantics
Leverage MAY identify a valuable gain and eligible consumers, but Signal Leverage owns how the signal is preserved, routed, branched, reconverged, bounded, and written back.

### FOUR-06: Propagation is not value
A heavily connected signal path does not prove leverage. Duplicate transmission, irrelevant fan-out, and circularity without learning are negative leverage candidates.

### FOUR-07: Value is not propagation
A validated gain that cannot reach an eligible future consumer is unrealized compounding potential. Leverage identifies the value; Signal Leverage must provide a governed path or record the propagation gap.

### FOUR-08: Re-evaluation is a handoff
Falsifying evidence returns to the semantic owner. No component resolves conflict by stealing ownership.

### FOUR-09: Every bounded signal episode MUST converge
The leverage system is persistent, but each propagation episode must have domain-appropriate idempotency, novelty, threshold, cooling, generation, or equivalent convergence control.

### FOUR-10: New reasoning primitives require non-overlapping semantic value
No fifth reasoning component may be added without proving a distinct concern, clear owner, eliminated work, reusable output, and net leverage.

## 8. Convergence Semantics

- **First-Order convergence:** a governing intervention is sufficiently justified.
- **Second-Order pre-execution convergence:** material predicted consequences are sufficiently mapped.
- **Second-Order post-execution convergence:** material observed consequences are sufficiently captured and compared.
- **Leverage convergence:** predicted or realized systemic value is sufficiently supported for the current decision.
- **Signal Leverage convergence:** the current propagation episode has preserved required meaning, reached or deliberately excluded eligible consumers, completed required write-back, and satisfied recursion/novelty controls.

Convergence of any bounded episode does not terminate the persistent leverage system.
