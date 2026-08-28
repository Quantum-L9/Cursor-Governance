<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: recursive-improvement-kernel
version: 2.0.0
status: active
-->

# Recursive Improvement Kernel

Use only when an existing pack is supplied and the user requests hardening, convergence, or improvement.

## Passes

1. Inventory and baseline every file.
2. Tighten activation, authority, contracts, and failure rules.
3. Remove duplicates, dead files, orphans, and stale platform assumptions.
4. Harden scripts, schemas, examples, and adapters to production depth.
5. Run full validation and compare against the baseline.

Stop when another pass would add documentation volume without changing behavior or validation. Required release evidence is README, MANIFEST, CHANGELOG or change summary, VALIDATION, and the regression result. Additional reports are created only when they change a decision or satisfy the user request.
