id: "next_deliverable_pack_incorporation_3h8q"
date: "2026-06-20"
artifact_type: "execution_prompt"
name: "incorporate_max_leverage_principles_into_next_deliverable_pack"

prompt:
  role: "elite_deliverable_pack_architect"
  objective: "Incorporate maximum leverage, maximum reusability, domain-agnostic design, determinism, traceability, validation, efficiency, and single-ingress evaluation into the next deliverable pack."

  instruction_scope:
    apply_to: "next_deliverable_pack"
    not_runtime_directives_for_agent_behavior: true
    rule: "These principles must be embedded into the design, files, contracts, validation gates, docs, and architecture of the next deliverable pack, not treated as conversational behavior rules."

  incorporation_targets:
    max_leverage:
      pack_must_include:
        - "reusable contracts"
        - "compounding abstractions"
        - "future-action acceleration"
        - "clear leverage scoring or rationale"
        - "elimination of repeated manual work where feasible"

    max_reusable:
      pack_must_include:
        - "portable schemas"
        - "generic interfaces"
        - "adapter-ready boundaries"
        - "minimal domain coupling"
        - "clear extension points"

    domain_agnostic:
      pack_must_include:
        - "domain-neutral core"
        - "optional domain adapters only when explicitly needed"
        - "no hardcoded project, repo, client, vendor, or environment assumptions"
        - "Unknown labels instead of invented domain facts"

    max_determinism:
      pack_must_include:
        - "fixed execution order"
        - "explicit priority rules"
        - "pass/fail validation gates"
        - "clear stop conditions"
        - "deterministic outputs where feasible"

    max_traceability:
      pack_must_include:
        - "decision log"
        - "source reference map"
        - "assumption map"
        - "unknowns register"
        - "artifact manifest"
        - "validation log"

    max_validation:
      pack_must_include:
        - "input validation"
        - "output validation"
        - "contract validation"
        - "dependency validation"
        - "scope validation"
        - "honest pass/fail/skipped/Unknown reporting"

    max_efficiency:
      pack_must_include:
        - "minimal repeated context"
        - "bounded outputs"
        - "deduplicated docs"
        - "concise contracts"
        - "no decorative files"
        - "no redundant explanations"

  single_ingress:
    incorporate_if_applicable: true
    pack_design_requirement: >
      If the next deliverable pack contains multiple tools, modules, workflows,
      agents, consumers, routes, or execution paths, incorporate a single ingress
      concept into the pack architecture.
    ingress_contract:
      name: "single_ingress_packet"
      purpose: "Normalize, validate, trace, authorize, and route all external requests through one canonical entry contract."
      required_fields:
        - "request_id"
        - "objective"
        - "mode"
        - "inputs"
        - "constraints"
        - "context_refs"
        - "authority_rules"
        - "trace_id"
        - "validation_profile"
        - "output_contract"
      required_rules:
        - "Normalize input once."
        - "Validate input once."
        - "Assign trace_id once."
        - "Route only after validation passes."
        - "Reject unsupported routes fail-closed."
        - "Prevent direct module bypass unless explicitly authorized."

  pack_output_requirements:
    required_sections_or_files:
      - "ARCHITECTURE.md or equivalent architecture section"
      - "CONTRACTS.md or schema directory"
      - "VALIDATION.md"
      - "MANIFEST.md"
      - "DECISION_LOG.md"
      - "UNKNOWN_REGISTER.md"
      - "TRACEABILITY_MAP.yaml"
      - "ASSUMPTION_MAP.yaml"
      - "ARTIFACT_MANIFEST.yaml"
      - "CHANGE_SUMMARY.md"
    required_quality:
      - "complete"
      - "source-aligned"
      - "domain-agnostic where possible"
      - "reusable"
      - "deterministic"
      - "traceable"
      - "validated"
      - "efficient"
      - "ready to commit"

  hard_constraints:
    - "MUST incorporate these principles into the next deliverable pack itself."
    - "MUST NOT treat these principles as direct conversation output style rules."
    - "MUST NOT add unrelated scope."
    - "MUST NOT hardcode domain assumptions unless explicitly provided."
    - "MUST NOT create stubs, placeholders, decorative files, or fake validation."
    - "MUST preserve the actual objective of the next deliverable pack."
    - "MUST keep core abstractions domain-agnostic unless domain-specific behavior is required."
    - "MUST label missing information as Unknown."
    - "MUST include traceability and validation artifacts."

  validation_gates:
    - "next_deliverable_objective_preserved"
    - "principles_embedded_in_pack_files"
    - "not_used_as_conversation_style_directives"
    - "domain_agnostic_core_present"
    - "reuse_contracts_present"
    - "single_ingress_evaluated"
    - "deterministic_execution_defined"
    - "traceability_artifacts_present"
    - "validation_artifacts_present"
    - "efficiency_review_completed"
    - "unknowns_labeled"
    - "no_stubs"
    - "no_placeholders"
    - "no_fake_validation"
    - "no_scope_drift"

  stop_conditions:
    - "HALT if the next deliverable objective is unknown."
    - "HALT if incorporation would change the deliverable’s actual purpose."
    - "HALT if single ingress does not apply and would create unnecessary architecture."
    - "HALT if traceability or validation would be fake."
    - "HALT if domain-specific assumptions would contaminate a reusable core."