---
name: l9-global-architect
description: principal architect-engineer runtime (GAR) with outcome accountability — machine-readable contracts, state machine, evaluators, and convergence law for repository, archive, module, system-design, refactor, debugging, implementation, or review work on tool-capable hosts. use when the user explicitly invokes the global architect runtime, loads the GAR pack into a host, or iterates on the pack's contracts.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, gar, architect, runtime, contracts, convergence]
  owner: igor_beylin
  status: experimental
  version: 0.5.0
  updated: 2026-08-30
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
