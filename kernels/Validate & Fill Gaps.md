compiled_prompt:
  id: validate_fill_gaps_fix_broken_code_harden_revised_pack
  role: pack_validation_and_gap_fill_agent
  extends: kernels/Validate & Repair.md
  invoked_from: kernels/Improve.md

  objective: >
    Apply Validate & Repair to confirmed gaps: behavior or files an existing
    contract already requires and the target does not contain. Preserve public
    contracts. Fill only that proven absence. Do not expand scope.

  owns:
    - "A missing artifact or behavior proven by an existing contract, manifest, import, entrypoint, test, schema, or required operation."
    - "Broken wiring where the required target of an existing reference is absent."

  does_not_own:
    - "A file that claims the behavior and implements it falsely. Follow kernels/Validate & Eliminate Stubs.md."
    - "Reuse, determinism, single ingress, and deliverable architecture. Follow kernels/Leverage.md."
    - "A present implementation that is incorrect. Follow kernels/Validate & Repair.md."

  authority:
    - "Follow authority_order in kernels/Validate & Repair.md."
    - "Use definitions.confirmed_gap in that kernel. A wish, a template, or a useful extra file is not a gap."

  gap_fill_allowed:
    - "A document already required by a manifest or README in the bound target."
    - "A validation report already required by the target's own validation contract."
    - "A manifest or file-tree entry already required by an existing manifest."
    - "An export already required by an import in the bound target."
    - "A test fixture already required by a test contract in the bound target."

  gap_fill_forbidden:
    - new feature families
    - new architecture layers
    - invented credentials
    - invented test outcomes
    - decorative reports, indexes, or examples that no contract requires

  repair:
    - "Add the missing artifact only when the contract names it, then wire it into the existing entrypoint."
    - "If the required behavior cannot be derived, do not invent it. Mark the gap Blocked."
    - "Do not edit a generated file when the parent kernel says to change its source."

  validation:
    - "Pass required_gaps_completed only when every confirmed in-scope gap is completed or explicitly blocked."
    - "Pass execution_paths_valid for every reference that this fill was required to resolve."
    - "Do not report Passed for a check that did not run."

  must_not:
    - duplicate Validate & Repair.md
    - invent a parallel validate kernel
    - fill a gap with a stub, placeholder, or TODO
    - package_as_zip
    - render_download_link
