<!--
--- SKILL_META ---
skill_schema: 1
origin: structured-reasoning
layer: reference
role: reasoning_kernel
tags: [reasoning, metrics, acceptance, validation]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
sources:
  - harvested: core-thinking-mode Block 11 (Suite-5 legacy, stripped n8n/monitoring fiction)
--- /SKILL_META ---

Purpose:
Measurable acceptance criteria for high-stakes or moderate+ deliverables.
-->

# Success Metrics Template

Define 3–5 **specific, measurable** criteria before marking work complete.

```yaml
Success Metrics:
  Functional:
    - "[Outcome 1 — verifiable with tool or test]"
    - "[Outcome 2 — threshold or count]"
    - "[Outcome 3 — verification method named]"

  Performance:  # omit if not in scope
    - "[Metric] < [threshold]"

  Quality:
    - "Linter / static gates: PASS"
    - "Required tests: PASS"
    - "No new HIGH audit findings"

  Business:  # omit if not applicable
    - "[User-facing or KPI outcome]"
```

## Rules

- Vague metrics (`everything works`, `looks good`) are invalid — rewrite or drop.
- Each metric MUST name how it will be verified (command, test file, manual step).
- On moderate+ complexity, include at least one quality gate tied to repo CI where applicable.
