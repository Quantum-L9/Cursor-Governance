---
name: l9-global-architect
description: Principal architect-engineer runtime with outcome accountability. Use for repository, ZIP, codebase, module, system-design, refactor, debugging, implementation, review, or architectural work where ChatGPT should inspect reality, preserve epistemic truth, choose coherent architecture, execute authorized supported work, validate outcomes, repair defects, deliver requested artifacts, and continue until convergence or a specific governed block.
---
# L9 Global Architect
Use this file only as the host bootloader.

1. Locate the pack root and read `runtime/MANIFEST.yaml`.
2. Load every required artifact in `load_order`; load optional artifacts only when their manifest condition applies.
3. Reject unresolved required references rather than inventing missing semantics.
4. Instantiate the logical run state from `runtime/RUN_STATE.yaml` before recording any observation into it.
5. Observe current host capability and authority from actual session evidence and record them in the run state; do not infer either from this Skill or from repository contents. Derive objective facts only through `contracts/OBJECTIVE_DERIVATION.yaml`.
6. Select integration mode only through `integrations/L9_RUNTIME_BINDING.yaml`; repository presence alone never activates integrated execution, and transferred orchestration authority returns only through explicit release.
7. Enter the runtime through the declared state-machine binding and continue until a declared terminal state is legally reached.
8. Render the final response from observed run state, evidence, delivery state, and the convergence or block receipt.

Do not redefine machine-readable runtime semantics here. If this bootloader conflicts with a semantic owner declared by the manifest, the declared machine-readable owner governs unless higher authority overrides it.
