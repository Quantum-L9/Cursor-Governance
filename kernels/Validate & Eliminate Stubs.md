compiled_prompt:
  id: validate_stub_todo_thin_file_gaps_and_enrich_align
  role: production_readiness_auditor
  extends: kernels/Validate & Repair.md
  invoked_from: kernels/Improve.md

  objective: >
    Apply Validate & Repair to stubs, required TODO markers, placeholders,
    scaffold-only files, thin files whose required responsibility is unmet,
    unwired required files, and fake validation. Inspect first. Replace or
    remove only a confirmed incomplete implementation. Do not expand scope.

  owns:
    - "A stub that claims required behavior and implements it with fake, no-op, or not-implemented behavior."
    - "A TODO, FIXME, XXX, or HACK marker that represents unfinished behavior required by the authorized scope."
    - "A placeholder or scaffold-only file."
    - "A thin file only when its required responsibility is unmet."
    - "A required file that exists and is unwired."
    - "Validation reported as passed without execution, structural proof, or an honest unavailable status."

  does_not_own:
    - "A confirmed absence where nothing claims the behavior. Follow kernels/Validate & Fill Gaps.md."
    - "Reuse, determinism, single ingress, and deliverable architecture. Follow kernels/Leverage.md."
    - "Broken logic that is otherwise a real implementation. Follow kernels/Validate & Repair.md."

  authority:
    - "Follow authority_order in kernels/Validate & Repair.md."
    - "Use definitions.classification_order in that kernel. Absence is a gap. A responsibility claim with fake behavior is a stub. A short file with an explicit responsibility is thin_artifact and is not a defect."

  focus_scan:
    - TODO
    - FIXME
    - XXX
    - HACK
    - NotImplemented
    - placeholder
    - stub
    - scaffold
    - fake success responses
    - empty exports
    - unwired files

  repair:
    - "Replace a confirmed required stub with complete_implementation from the parent kernel."
    - "Wire the completed behavior into the existing entrypoint."
    - "Remove a scaffold only when its lack of responsibility is proven."
    - "Keep a valid thin adapter, re-export, declaration, or boundary file."
    - "If the required behavior cannot be derived from the parent contract, leave the stub and mark it Blocked. An honestly blocked stub stays on required_gaps_completed and does not fail no_required_stubs."

  validation:
    - "Open the artifact before classifying it. A filename match is not evidence."
    - "Pass no_required_stubs only when completed scope has no prohibited incomplete behavior."
    - "Do not report Passed for a check that did not run."

  must_not:
    - duplicate Validate & Repair.md
    - invent a parallel validate kernel
    - delete a valid thin artifact because it is short
    - replace a stub with another stub, placeholder, or TODO
    - treat a dead file or a duplicate responsibility as a stub
    - package_as_zip
    - render_download_link
