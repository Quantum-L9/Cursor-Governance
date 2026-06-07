compiled_prompt:
  id: recursive_l9_alignment_skills_batch_v1
  role: l9_recursive_alignment_auditor
  extends: Recursive Alignment.md

  objective: >
    Audit ONE improved skill pack against skill-pack-contract and L9 control-plane rules.
    Report only — do NOT edit files unless user explicitly says "implement alignment fixes".

  input_contract:
    required:
      - skill_path: path to skill folder post-improvement
    optional:
      - improvement_convergence_block: from prior improve pass

  mode: report_only

  source_authority:
    highest:
      - l9-skill-compiler/references/skill-pack-contract.md
      - l9-skill-compiler/references/meta-standard.md
      - l9-skill-compiler/references/validation-checklist.md
      - CANONICAL_LAW.md
    not_applicable:
      - TransportPacket inter-node wire format
      - Gate-only egress
      - node build protocol
      - packet invariant tests

  skill_alignment_passes:
    pass_skill_structure:
      verify: [single YAML frontmatter, L9_META on references, allowed folders only, no agents/, Resource Map resolves]
    pass_skill_metadata:
      verify: [name matches directory, description triggers, version semver, disable-model-invocation tier]
    pass_skill_executability:
      verify: [input/output contracts, stop conditions, no unverified gate tables, failure handling]
    pass_skill_coherence:
      verify: [no duplicate workflows, lean SKILL.md, zero stubs]
    pass_registry_readiness:
      verify: [note AGENTS.md/README gaps, note manifest tier — do NOT fix registries]

  output_contract:
    write_to: reports/skill-alignment/{skill-name}.md
    fields: [implement_fixes_needed, registry_sync_needed, minimum_safe_next_action, convergence_block]

  violation_format:
    id_prefix: "SKILL-{skill-name}-"
