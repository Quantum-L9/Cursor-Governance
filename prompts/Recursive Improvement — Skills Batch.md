compiled_prompt:
  id: recursive_l9_improvement_skills_batch_v1
  role: l9_recursive_improvement_agent
  extends: Recursive Improvement.md

  objective: >
    Recursively improve and harden ONE skill pack folder per invocation.
    Inherit all passes from recursive_l9_improvement_prompt_v3.
    Apply skill-pack-contract as the structural authority.

  input_contract:
    required:
      - skill_path: absolute or repo-relative path to ONE skill folder
    optional:
      - scope: global | project

  hard_rules_additions:
    - MUST NOT edit AGENTS.md, .claude/README.md, or AUTONOMY_MANIFEST.yaml
    - MUST NOT duplicate L9 packs into .claude/skills/
    - MUST NOT create agents/openai.yaml
    - MUST preserve disable-model-invocation if present in source SKILL.md
    - MUST label Unknown when repo-specific gate tables cannot be verified

  authority_order:
    1: provided skill pack
    2: l9-skill-compiler/references/skill-pack-contract.md
    3: l9-skill-compiler/references/meta-standard.md
    4: l9-skill-compiler/references/file-contract.md
    5: l9-skill-compiler/references/validation-checklist.md
    6: CANONICAL_LAW.md

  skill_pack_improvement_contract:
    SKILL_md:
      MUST_have_single_yaml_frontmatter: true
      MUST_have_fields: [name, description, skill_schema, layer, role, tags, owner, status, version, updated]
      MUST_have_sections: [Purpose, "Core Contract or compact workflow", "Authority Order", "Resource Map", "Validation", "Failure Handling"]
      MUST_NOT_have: [embedded slash-command frontmatter blocks, duplicate name blocks, SKILL_META HTML comment]
      router_rule: SKILL.md is control plane; workflows longer than 40 lines MUST move to references/
    references:
      MUST_have_L9_META: true
      MUST_be_linked_from_SKILL: true
    global_l9:
      prefix: l9-
      location: .cursor-commands/skills/
    project_plasticos:
      prefix: plasticos-
      location: .claude/skills/
      MUST_NOT: [AUTONOMY_MANIFEST entry]

  validation_gates_additions:
    - single_frontmatter_block_verified
    - all_references_have_metadata
    - resource_map_links_resolve
    - no_agents_openai_yaml
    - description_has_explicit_triggers

  output_requirements:
    must_return:
      - complete_revised_skill_pack_all_files
      - convergence_block
      - skill_inventory_row
      - per_file_summary
    must_not_edit: [AGENTS.md, .claude/README.md, AUTONOMY_MANIFEST.yaml]

  convergence_block:
    required: true
    inherit_fields_from: recursive_l9_improvement_prompt_v3
