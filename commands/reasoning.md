---
name: reasoning
version: "6.1.0"
description: "Structured reasoning — evidence, risk, action; auto-chains to /ynp"
auto_chain: ynp
---

# /reasoning — Structured reasoning

Delegates to skill **`l9-structured-reasoning`**.

Do not emit an uncalibrated confidence percent. Stance is `evidence_quality` × `decision_risk` → `action`.

## Usage

```text
/reasoning
/reasoning <decision or diagnosis>
```

## Execution

1. Read `skills/l9-structured-reasoning/SKILL.md` and `references/confidence-policy.yaml`.
2. Classify `task_kind` and `epistemic_methods` (abductive, deductive, inductive, comparative).
3. Emit the stance block. `calibration_status` defaults to `none`. `stated_probability` stays null unless a calibrated window, n, and ece are present.
4. Auto-chain to `/ynp`. YNP recommends only; it does not auto-execute.

## Output

Show the decision, decisive evidence, material Unknowns, trade-offs, and the next action or stop condition. No ceremonial Confidence heading.

```yaml
evidence_quality: high | medium | low | unknown
decision_risk: reversible | guarded | irreversible
action: proceed | proceed_with_validation | bounded_probe | block
calibration_status: none
stated_probability: null
```
