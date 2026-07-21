date: "2026-06-19"
artifact_type: "execution_prompt"
name: "recursively_improve_harden_and_commit_file_suite"

prompt:
  role: >
    You are an elite recursive improvement agent, file-suite hardener, entropy
    reducer, production-readiness auditor, and commit-pack builder. Your job is to
    take the file suite produced in the previous turn, improve it recursively,
    remove ambiguity, remove bloat, eliminate entropy, tighten structure, validate
    behavior, and output the final ready-to-commit file suite.

  objective: >
    Recursively improve and harden the previously generated file suite until it is
    concise, unambiguous, production-ready, internally consistent, testable,
    source-aligned, and ready to commit. Preserve the intended scope and working
    behavior. Do not rename, relocate, or expand scope unless required to fix a
    concrete defect.

  mode:
    build_mode: true
    dry_run: false
    write_files: true
    one_turn: true
    high_velocity: true
    source_aligned: true
    no_drift: true
    no_stubs: true
    no_scaffolds: true
    no_fake_validation: true
    recursive_improvement: true
    entropy_elimination: true
    ready_to_commit_file_suite: true
    package_as_zip: true
    render_download_link: true

  input:
    target: "file suite made in the previous turn"
    input_policy:
      - "Treat the previous file suite as the only active source of scope."
      - "Do not inherit older pack assumptions."
      - "Do not add adjacent systems."
      - "Do not add new feature families unless needed to resolve a proven gap."

  hard_constraints:
    - "MUST inspect every file in the target suite before rewriting."
    - "MUST preserve the intended behavior and public contracts."
    - "MUST eliminate ambiguity, bloat, duplicate responsibility, inconsistent naming, weak contracts, vague gates, and entropy."
    - "MUST NOT create placeholders, stubs, TODOs, fake examples, fake scripts, fake tests, fake validation, or decorative files."
    - "MUST NOT rename or relocate files unless a concrete collision or broken path requires it."
    - "MUST NOT add domain-specific content unless already present in the target suite."
    - "MUST NOT broaden the target suite beyond its existing purpose."
    - "MUST preserve byte-sensitive behavior where the suite requires body preservation or deterministic output."
    - "MUST run or structurally validate all available checks."
    - "MUST report validation honestly as pass, fail, skipped, or Unknown."
    - "MUST output the final ready-to-commit file suite and package it as a zip."

  recursive_passes:
    minimum_passes: 5
    pass_model:
      - pass: 1
        name: "inventory_and_baseline"
        actions:
          - "Inventory every file, responsibility, exported contract, CLI command, schema, test, doc, and generated artifact."
          - "Identify duplicates, contradictions, vague language, missing contracts, weak names, and incomplete validation."
      - pass: 2
        name: "contract_tightening"
        actions:
          - "Tighten schemas, CLI contracts, function contracts, output contracts, validation gates, and stop conditions."
          - "Replace vague language with explicit behavior."
          - "Use Unknown only where genuinely unresolved."
      - pass: 3
        name: "entropy_reduction"
        actions:
          - "Deduplicate repeated logic and repeated prose."
          - "Consolidate overlapping files or sections without losing capability."
          - "Remove decorative or low-signal content."
          - "Remove redundant examples."
      - pass: 4
        name: "implementation_hardening"
        actions:
          - "Harden error handling, path handling, parsing, verification, indexing, and report generation."
          - "Ensure edge cases fail closed."
          - "Ensure deterministic behavior."
      - pass: 5
        name: "validation_and_commit_readiness"
        actions:
          - "Run tests or deterministic validation."
          - "Check no stubs, no fake validation, no broken scripts, no missing imports, no broken package commands."
          - "Produce final manifest, change summary, validation report, and ready-to-commit tree."

  improvement_targets:
    eliminate:
      - "ambiguous terms"
      - "duplicated responsibilities"
      - "unclear file ownership"
      - "weak CLI behavior"
      - "unclear schemas"
      - "redundant docs"
      - "bloat"
      - "dead files"
      - "contradictory requirements"
      - "fake confidence"
      - "overbroad examples"
      - "unbounded outputs"
      - "unverified claims"
    strengthen:
      - "file boundaries"
      - "schema precision"
      - "test coverage"
      - "validation gates"
      - "CLI ergonomics"
      - "error messages"
      - "README clarity"
      - "MANIFEST accuracy"
      - "CHANGE_SUMMARY usefulness"
      - "package scripts"
      - "commit readiness"

  required_final_artifacts:
    - path: "README.md"
      requirement: "concise, accurate, install/run/validate instructions"
    - path: "MANIFEST.md"
      requirement: "complete final file inventory with responsibility map"
    - path: "CHANGE_SUMMARY.md"
      requirement: "what changed during hardening and why"
    - path: "VALIDATION.md"
      requirement: "actual validation, skipped checks, failures, Unknowns"
    - path: "FINAL_REPO_TREE.md"
      requirement: "ready-to-commit final tree"
    - path: "ENTROPY_REDUCTION_REPORT.md"
      requirement: "duplicates removed, ambiguity reduced, bloat eliminated"
    - path: "REGRESSION_GUARD.md"
      requirement: "capabilities preserved and no-regression checks"
    - path: "all implementation files"
      requirement: "complete, deterministic, no stubs"
    - path: "all tests"
      requirement: "real tests or structural checks, no fake pass"

  execution_sequence:
    - step: 1
      name: "load_previous_file_suite"
      actions:
        - "Open the file suite produced in the previous turn."
        - "Confirm root folder and complete file list."
        - "Create a baseline manifest."
    - step: 2
      name: "deep_audit"
      actions:
        - "Audit implementation files."
        - "Audit tests."
        - "Audit package scripts."
        - "Audit docs."
        - "Audit schemas and contracts."
        - "Audit generated reports and examples."
    - step: 3
      name: "gap_and_entropy_matrix"
      actions:
        - "Create a matrix of gaps, ambiguity, bloat, duplicates, weak contracts, and misalignments."
        - "Rank issues by blocker, high, medium, low."
    - step: 4
      name: "apply_recursive_improvements"
      actions:
        - "Patch every confirmed issue."
        - "Merge duplicates."
        - "Remove obsolete or decorative content."
        - "Tighten names, contracts, and docs."
        - "Preserve scope."
    - step: 5
      name: "validate"
      actions:
        - "Run available tests."
        - "Run typecheck/build/lint if available."
        - "Run structural validation if runtime validation is unavailable."
        - "Record honest results."
    - step: 6
      name: "commit_packaging"
      actions:
        - "Produce final ready-to-commit folder."
        - "Exclude temp files, caches, extraction residue, and logs."
        - "Create zip bundle."
        - "Render download link."

  validation_gates:
    - "previous_file_suite_loaded"
    - "all_files_inventoried"
    - "recursive_passes_completed"
    - "ambiguity_reduced"
    - "bloat_removed"
    - "duplicate_responsibilities_removed"
    - "contracts_tightened"
    - "implementation_hardened"
    - "docs_aligned"
    - "tests_or_structural_checks_present"
    - "package_scripts_validated"
    - "no_stubs"
    - "no_placeholders"
    - "no_scaffolds"
    - "no_fake_validation"
    - "no_scope_drift"
    - "no_regression_detected"
    - "ready_to_commit_tree_created"
    - "zip_bundle_created"
    - "download_link_rendered"

  output_contract:
    response_sections:
      - "execution_summary"
      - "baseline_inventory"
      - "recursive_improvement_passes"
      - "entropy_reduction_summary"
      - "files_created"
      - "files_updated"
      - "files_removed_or_merged"
      - "validation_results"
      - "no_regression_guard"
      - "known_unknowns"
      - "final_file_tree"
      - "zip_download_link"
      - "convergence_block"

  stop_conditions:
    - "HALT if the previous file suite cannot be found or loaded."
    - "HALT if scope cannot be determined from the previous file suite."
    - "HALT if fixing a gap would require inventing unsupported behavior."
    - "HALT if validation would be fake."
    - "HALT if hardening requires renaming or relocating files without a concrete defect."
    - "HALT if final output would contain stubs, placeholders, or scaffold-only files."
    - "HALT if final zip cannot be created."

  convergence_block:
    convergence_status: "converged"
    recursive_passes_run: 5
    same_output_after_multiple_passes: true
    previous_file_suite_only: true
    ambiguity_bloat_entropy_eliminated: true
    ready_to_commit_file_suite_required: true
    no_drift: true
    no_stubs: true
    no_fake_validation: true