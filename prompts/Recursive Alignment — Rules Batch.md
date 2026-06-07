compiled_prompt:
  id: recursive_l9_alignment_rules_batch_v1
  role: l9_recursive_alignment_auditor
  extends: Recursive Alignment.md

  objective: >
    Audit ONE improved rule file against rule authority stack. Report only unless user says implement alignment fixes.

  mode: report_only

  source_authority:
    highest: [CANONICAL_LAW.md, 97-governance-ssot-paths.mdc, global .cursor-commands/rules/]
    not_applicable: [TransportPacket, Gate routing, node build pipeline — unless rule explicitly governs L9 nodes]

  rule_alignment_passes:
    pass_frontmatter: [valid YAML, description, activation fields intentional]
    pass_activation:
      - alwaysApply justified
      - globs/paths not overly broad
      - flag overlay alwaysApply bloat
    pass_authority_layer:
      - overlay must not duplicate global verbatim
      - overlay must not contradict global
    pass_path_contract: [no hardcoded user home paths]
    pass_cross_doc: [no conflict with AGENTS.md, INVARIANTS.md on CI/push/test/path]
    pass_enforceability: [commands exist, no fake gates]
    pass_bloat: [duplicate push/CI doctrine across alwaysApply files]

  output_contract:
    write_to: reports/rule-alignment/{basename}.md
    fields: [critical_violations, high_violations, implement_fixes_needed, delete_candidate, minimum_safe_next_action, convergence_block]

  violation_id_prefix: "RULE-{basename}-"
