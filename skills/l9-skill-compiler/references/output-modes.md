<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: output-mode-contract
version: 3.8.0
status: active
-->

# Output Modes

- `discuss`: decision options, trade-offs, and recommended path; no files unless requested.
- `analyze`: evidence-backed strengths, defects, divergence, tier, and prioritized corrections.
- `design`: exact file tree, resource routing, adapter map, validation plan, and unknowns.
- `build`: complete new pack plus validation evidence and archive when requested.
- `rebuild`: preserve intent, remove debt, replace the complete pack, and record functional changes.
- `exemplary`: build plus expertise model, intelligence report, measured activation, authority, heuristics, failure controls, and exemplary validation.
- `hardened-rebuild`: inspect every file, tighten contracts, remove entropy, harden implementation, and regression-test against the prior baseline.
- `package`: stage the runtime file set, validate it, create root-flat `skill.zip`, inspect it, and return it.

Never return only a plan when the user requested a build or package.
