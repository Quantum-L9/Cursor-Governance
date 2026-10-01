# L9 Second-Order Consequence Lens

**Status:** Converged baseline  
**Version:** 1.0.0  
**Semantic owner:** consequence propagation before and after an intervention

## 1. Cardinal Questions

Second-Order Reasoning has two inseparable questions:

> **BEFORE: What changes IF we change it?**

> **AFTER: What changed BECAUSE we changed it?**

The lens exists to model system response to a First-Order intervention, first predictively and then observationally.

It does not choose the intervention and it does not score leverage.

## 2. Purpose

First-Order identifies the governing intervention.

Second-Order expands the causal horizon beyond the direct result:

```text
intervention
  -> direct result
  -> affected participants
  -> changed behaviors
  -> downstream consequences
  -> feedback
  -> delayed consequences
  -> altered system state
```

After execution, the same lens observes the real consequence surface and compares it with what was predicted.

## 3. The Second-Order Mini-Loop

```text
candidate intervention
      |
      v
PREDICT
what changes IF we do it?
      |
      v
execution
      |
      v
OBSERVE
direct result
      |
      v
observed downstream effects
      |
      v
COMPARE
predicted vs observed
      |
      v
forecast error + causal learning
      |
      +----> Leverage Kernel
      +----> future First-Order evidence
```

This mini-loop lives inside a First-Order intervention pass and inside the broader persistent leverage loop.

## 4. Second-Order Invariants

### SO-01: Every material intervention MUST receive a consequence lens proportional to its stakes
The deeper the irreversibility, coupling, blast radius, uncertainty, or systemic reach, the deeper the consequence analysis SHOULD be.

Trivial and easily reversible changes do not require ceremonial modeling.

### SO-02: Predict before execution
Before a material intervention, the lens MUST ask what else is expected to change if the intervention occurs.

Prediction is required so later learning is not rewritten by hindsight.

### SO-03: Observe after execution
After execution, the lens MUST inspect what actually changed beyond the direct result when such evidence is available and material.

### SO-04: Compare prediction with observation
Predicted and observed consequence surfaces MUST remain distinct and MUST be compared.

The delta is a first-class learning signal.

### SO-05: Consequences include beneficial and harmful effects
The lens MUST NOT equate "second-order" with "unintended harm."

It MUST permit consequences that are:

- beneficial or harmful;
- intended or unintended;
- direct or indirect;
- immediate or delayed;
- reinforcing or balancing;
- local or systemic;
- certain, uncertain, or unknown.

### SO-06: Model state change, not just event chains
The lens SHOULD describe how the relevant system state differs after the intervention, not merely enumerate chronological events.

A useful question is:

> What becomes newly true, false, possible, impossible, easier, harder, coupled, decoupled, required, or unnecessary?

### SO-07: Follow material consequence paths until they converge, dissipate, or become immaterial
Second-Order reasoning MUST NOT recurse forever.

A path may stop when:

- it reaches a stable state relevant to the decision;
- further effects are immaterial to the objective;
- evidence becomes too weak to support useful claims;
- a separate semantic owner must evaluate the result; or
- the path becomes a new independent reasoning problem.

### SO-08: Branching consequence paths are expected
One intervention may create many consequence paths.

```text
change
  +-> path A
  +-> path B
  +-> path C
```

The lens MUST NOT force consequences into a single linear chain.

### SO-09: Feedback effects MUST be represented when they change later behavior
If a consequence returns to influence an earlier participant or future execution, record the feedback relationship.

Second-Order describes the feedback. Leverage determines whether and how that feedback compounds systemic value.

### SO-10: Causal attribution after execution MUST be disciplined
Observed change is not automatically caused by the intervention.

Post-execution reasoning MUST distinguish:

- strongly attributed consequence;
- plausible consequence;
- correlated observation;
- competing cause;
- unknown attribution.

### SO-11: Counterfactual comparison SHOULD be used when material
Where feasible, ask:

> What would likely have happened if we had not made the intervention?

This prevents ordinary background change from being credited to the intervention.

### SO-12: Irreversibility and path dependence are consequence properties
The lens SHOULD identify when an intervention changes future option space, creates lock-in, shifts ownership, introduces new dependencies, or makes reversal materially harder.

It reports these effects. It does not own leverage valuation of them.

### SO-13: Second-Order MUST NOT choose the intervention
If predicted consequences invalidate the candidate, the lens returns that evidence to First-Order for re-selection.

It does not silently choose a replacement.

### SO-14: Second-Order MUST NOT score leverage
The lens may describe that capability, cost, risk, reach, optionality, or learning changed.

It MUST NOT decide the participant's Leverage Rank, Leverage Score, or net systemic leverage. Those belong to the Leverage Kernel.

## 5. Pre-Execution Consequence Contract

```yaml
second_order_prediction:
  intervention_ref: ""
  direct_expected_result: ""
  consequence_paths:
    - path_id: ""
      affected_participants: []
      predicted_changes: []
      timing: immediate|near_term|delayed|unknown
      direction: beneficial|harmful|mixed|neutral|unknown
      reversibility: easy|bounded|difficult|irreversible|unknown
      causal_confidence: high|medium|low|unknown
      evidence_refs: []
  system_state_expected_to_change: []
  assumptions: []
  unknowns: []
```

`direction` is descriptive relative to the locked objective and known constraints. It is not a Leverage Score.

## 6. Post-Execution Consequence Contract

```yaml
second_order_observation:
  intervention_ref: ""
  direct_observed_result: ""
  observed_consequence_paths:
    - path_id: ""
      affected_participants: []
      observed_changes: []
      attribution: strong|plausible|correlated|competing_cause|unknown
      evidence_refs: []
  prediction_comparison:
    confirmed: []
    overpredicted: []
    underpredicted: []
    unpredicted: []
    contradicted: []
  forecast_error_learning: []
  first_order_reconsideration_required: false
  leverage_handoff_required: true
```

## 7. Failure Modes

### SO-F01: Unintended-consequence reductionism
Treating Second-Order as a hunt for bad surprises only.

### SO-F02: Hindsight rewriting
Changing the original prediction after observing the outcome.

### SO-F03: Infinite consequence recursion
Following increasingly speculative chains with no materiality boundary.

### SO-F04: Correlation capture
Crediting every later observation to the intervention.

### SO-F05: Leverage theft
Scoring or ranking systemic value instead of returning consequence evidence to Leverage.

### SO-F06: Intervention theft
Selecting a replacement intervention instead of returning falsifying evidence to First-Order.

### SO-F07: Linearization
Ignoring branching, reconvergence, delayed effects, or feedback because they do not fit a simple chain.

## 8. Relationship to the Other Components

Second-Order answers:

> **What changes IF we make the First-Order intervention?**

and later:

> **What changed BECAUSE we made it?**

It does NOT answer:

- What one thing should we change? -> First-Order
- Which consequences create the most systemic leverage? -> Leverage
- What Leverage Rank or Score results? -> Leverage

Its output is the consequence surface that makes predicted and realized leverage evidence-based rather than speculative.
