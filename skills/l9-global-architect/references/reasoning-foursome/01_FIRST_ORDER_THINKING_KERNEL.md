# L9 First-Order Thinking Kernel

**Status:** Converged baseline  
**Version:** 1.0.0  
**Semantic owner:** governing cause and intervention selection

## 1. Cardinal Question

> **What is the one thing that, if changed correctly, makes the greatest amount of other work unnecessary?**

This is the governing First-Order question in L9.

First-Order Thinking is not task prioritization, symptom repair, or generic root-cause analysis. It is causal compression: identify the governing cause and the smallest authoritative intervention that eliminates the maximum amount of derivative work.

## 2. Purpose

First-Order Thinking exists to prevent L9 from spending effort on work that should disappear after the correct intervention.

It converts:

```text
symptom A -> fix A
symptom B -> fix B
symptom C -> fix C
symptom D -> fix D
```

into:

```text
governing cause
  -> one authoritative change
  -> A, B, C, and D no longer require independent repair
```

The desired output is not "the most important task." It is the highest-causal-compression intervention supported by evidence.

## 3. First-Order Invariants

### FO-01: Seek the one governing intervention
Every material reasoning pass MUST first seek a single governing intervention capable of making the maximum amount of downstream work unnecessary.

Do not assume multiple interventions are necessary merely because multiple symptoms exist.

### FO-02: One-change compression MUST be attempted before multi-change planning
A plan containing many repairs MUST be challenged with:

> What single upstream or authoritative change would eliminate the need for the greatest number of these repairs?

If evidence proves no single intervention can satisfy the objective, select the smallest independent intervention set and record why further compression is not valid.

### FO-03: Eliminate work, do not merely perform it efficiently
An intervention that makes ten tasks unnecessary is generally superior, all else equal, to an intervention that makes those ten tasks faster.

First-Order value is strongly evidenced by **work eliminated**, not activity completed.

### FO-04: Fix governing causes before derivative symptoms
Repeated local failures, duplicate implementations, policy drift, inconsistent adapters, and repeated repairs are evidence to search for a shared governing cause.

A local symptom MAY be fixed directly only when:

- no higher valid common cause exists;
- the higher cause is outside authorized scope and cannot be safely deferred;
- containment is required before the governing repair; or
- evidence shows the symptom is genuinely independent.

### FO-05: Intervene at the authoritative ownership boundary
The chosen intervention MUST target the semantic owner or highest valid ownership boundary capable of resolving the governing cause without invalid fan-out.

Filesystem height, organizational seniority, or broad blast radius are not evidence of authority.

### FO-06: Prefer the smallest decisive change
First-Order reasoning MUST minimize the intervention surface after locating the governing cause.

The target is:

> smallest change at the correct owner that causes the largest valid reduction in necessary work.

Large rewrites are not First-Order merely because they are upstream.

### FO-07: Preserve the locked objective
Causal compression MUST serve the actual objective.

A change that elegantly eliminates work by changing the goal, weakening requirements, deleting required behavior, or redefining success is invalid.

### FO-08: Causal claims MUST be evidence-bound
The kernel MUST distinguish:

- verified governing cause;
- inferred governing cause;
- competing cause;
- unknown cause.

Unknown MUST remain Unknown when evidence is insufficient.

### FO-09: Disconfirm the attractive root cause
Before locking an intervention, actively seek evidence that the proposed governing cause is merely another symptom or that the intervention would leave substantial supposedly eliminated work still necessary.

### FO-10: Define the work expected to disappear
Every First-Order decision MUST explicitly state what work, duplication, repair, uncertainty, or future effort should become unnecessary if the intervention is correct.

This creates a falsifiable post-execution test.

### FO-11: Residual work MUST be distinguished from eliminated work
After selecting the intervention, classify downstream work as:

- expected to become unnecessary;
- still necessary;
- uncertain pending execution;
- newly created prerequisite.

Do not claim total causal compression when material independent work remains.

### FO-12: First-Order Thinking MUST hand off consequences rather than absorb them
Once the governing intervention is selected, broad modeling of what else changes belongs to the Second-Order Consequence Lens.

First-Order does not own the consequence graph.

## 4. First-Order Decision Contract

A converged First-Order decision SHOULD expose:

```yaml
first_order_decision:
  objective: ""
  governing_cause:
    statement: ""
    status: verified|inferred|unknown
    evidence_refs: []
  authoritative_owner: ""
  decisive_intervention: ""
  why_this_one_change: ""
  work_expected_to_become_unnecessary: []
  residual_work_still_required: []
  disconfirming_evidence_checked: []
  assumptions: []
  unknowns: []
  confidence: high|medium|low|unknown
  second_order_handoff_required: true
```

## 5. First-Order Gate

Do not proceed to broad implementation planning until these questions are answered:

1. What is the governing cause?
2. Who owns it?
3. What is the smallest decisive intervention?
4. What other work becomes unnecessary if it succeeds?
5. What evidence could prove this is not the governing intervention?
6. What material work remains independent?

## 6. Failure Modes

### FO-F01: Symptom ladder
Fixing symptoms in sequence while never challenging the shared cause.

### FO-F02: Task-list worship
Treating an existing backlog as proof that every task remains necessary.

### FO-F03: Upstream theater
Choosing a broad upstream change without evidence that it is the governing owner.

### FO-F04: Rewrite bias
Mistaking maximum scope for maximum leverage.

### FO-F05: Goal substitution
Making work unnecessary by weakening or changing the objective.

### FO-F06: Forced singularity
Pretending one cause exists when evidence proves multiple independent governing causes.

### FO-F07: Premature consequence ownership
Expanding First-Order into a full simulation of future effects instead of handing off to Second-Order.

## 7. Relationship to the Other Components

First-Order answers:

> **What one change should we make so the greatest amount of other work becomes unnecessary?**

It does NOT answer:

- What else will change if we do it? -> Second-Order
- What else changed because we did it? -> Second-Order
- How much systemic leverage will that create? -> Leverage
- How should realized learning propagate through the mesh? -> Signal Leverage

First-Order supplies the intervention. It does not own the future consequence surface or leverage valuation.
