---
description: Prompt, kernel, and eval discipline for L9.
paths:
- config/kernels/**/*
- config/prompts/**/*
- evals/**/*
- scripts/eval_*.py
---

# Prompts and evals (L9)

## Versioning and ownership

- Kernel and prompt configurations must be versioned with clear owners.
- Changes to prompts or kernels should be traceable via commit messages and PR descriptions.

---

## Eval requirements

- When changing core prompts, kernels, or agent configurations:
  - Define which eval suites should run (scenarios, workloads, or regression sets).
  - Run the relevant evals and capture results before merging.
- For regressions or riskier changes, add or extend eval cases to cover the new behavior.

---

## Eval harness patterns

- Eval scripts (`evals/**/*`, `scripts/eval_*.py`) should:
  - Be deterministic and reproducible.
  - Clearly document inputs, expected behavior, and pass/fail criteria.
- Treat eval results as **first-class evidence** alongside tests when assessing changes.

---

<!-- generated-from: rules/73-prompts-and-evals.mdc; do-not-edit -->
