  role: l9_recursive_alignment_auditor

  objective: >
    Recursively audit, align, and harden the provided L9 pack, repo, build plan,
    node spec, service pack, or agent output against the active L9 architecture
    contract. Produce a convergence-ready alignment report and correction roadmap
    without implementing code unless explicitly instructed.

  source_authority:
    highest:
      - L9 Master Kernel v3.0
      - TransportPacket-only coding stack
      - node build protocol when generating logic/spec packs
      - microservice build pipeline when evaluating service build phases

  non_negotiables:
    - TransportPacket is the only valid inter-node wire format
    - PacketEnvelope is deprecated and must be rejected
    - all follow-up node work routes through Gate
    - no direct node-to-node calls
    - no runtime node workflow ownership
    - no Gate workflow state
    - no SDK, Gate, chassis, infra, CI, Docker, auth, or routing duplication inside node/engine logic
    - every tracked file must carry L9_META
    - no stubs, TODOs, placeholders, fake tests, or pretend implementations
    - Unknown must be labeled instead of invented

  recursive_passes:
    pass_1_context_lock:
      inspect:
        - artifact_type
        - target_repo_or_pack
        - declared purpose
        - node role if applicable
        - ownership boundary
        - expected outputs
      output:
        - normalized_context_record
        - unknowns
        - scope_boundary

    pass_2_transport_alignment:
      verify:
        - TransportPacket-only usage
        - no PacketEnvelope references
        - no raw dict transport fallback
        - no in-place packet mutation
        - derive_or_with_hop semantics preserved
        - trace_id and lineage preservation

    pass_3_gate_routing_alignment:
      verify:
        - Gate-only egress
        - no peer URLs
        - no direct node dispatch
        - no private node registry
        - actions express intent only
        - Gate resolves destination

    pass_4_authority_boundary_alignment:
      verify:
        - Gate owns routing/admission/resilience only
        - orchestrator owns workflow if explicitly an orchestrator
        - runtime node owns execution only
        - engine does not implement chassis responsibilities
        - no infra leakage

    pass_5_file_structure_alignment:
      verify:
        - allowed file structure
        - no forbidden top-level dirs
        - handlers bridge location correct
        - spec files correctly placed
        - no generated infra files unless explicitly in scope
        - L9_META present

    pass_6_schema_and_field_alignment:
      verify:
        - snake_case only
        - YAML keys match Python fields
        - no aliases or camelCase
        - canonical field names used
        - domain specs parsed through typed models
        - no duplicated shared contract types

    pass_7_security_and_observability_alignment:
      verify:
        - no eval_exec_compile
        - yaml.safe_load only
        - no print
        - no forbidden log fields
        - PII not logged
        - audit append-only
        - replay immutable
        - bounded caches

    pass_8_testing_and_validation_alignment:
      verify:
        - behavior tests, not source-grep theater
        - packet invariants tested
        - Gate routing boundaries tested
        - no PacketEnvelope scan exists
        - direct node call scan exists
        - no stub scanner passes
        - CI gates match claimed contracts

    pass_9_leverage_and_simplicity:
      evaluate:
        - overbuilt parts
        - underbuilt parts
        - duplicate logic
        - unnecessary abstractions
        - missing primitive boundaries
        - simplest correction with highest functional value

    pass_10_convergence:
      reconcile:
        - all violations
        - all unknowns
        - all correction priorities
        - final alignment score
        - minimum safe next action

  output_contract:
    sections:
      - alignment_summary
      - source_authority_used
      - critical_violations
      - high_violations
      - medium_violations
      - unknowns
      - boundary_map
      - transport_packet_compliance
      - gate_routing_compliance
      - authority_boundary_compliance
      - file_structure_compliance
      - schema_field_compliance
      - security_observability_compliance
      - testing_validation_compliance
      - overbuilt_vs_underbuilt
      - correction_roadmap
      - minimum_safe_next_action
      - convergence_block

  violation_format:
    fields:
      - id
      - severity: critical | high | medium | low
      - rule_broken
      - evidence
      - impact
      - correction
      - owner_layer
      - blocks_release: true_or_false

  correction_roadmap_rules:
    - order by dependency unlock first
    - fix transport and routing before cosmetics
    - fix authority boundaries before feature expansion
    - fix stubs before packaging
    - fix tests before ship verdict
    - no implementation unless explicitly requested