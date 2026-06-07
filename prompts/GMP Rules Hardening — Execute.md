compiled_prompt:
  id: gmp_rules_hardening_execute_v1
  role: gmp_rules_batch_executor
  run_id: GMP-RULES-HARDEN-001

  objective: >
    Execute a GMP-locked rules-only hardening run: optimize batch Improvement/Alignment
    prompts for .mdc/.md rule artifacts, inventory all rule files, improve → align → fix
    global rules (SSOT), dedupe PlasticOS overlay, thin Claude path refs, validate,
    produce evidence report. RULES ONLY — no skills, no skill wiring, no AUTONOMY_MANIFEST.

  agent_kickoff: >
    Execute GMP-RULES-HARDEN-001. Phase 0 approved. Load l9-gmp-protocol.
    Follow this prompt through Phase 7. Do not edit the plan file if attached.
    Stop after Wave 1 overlay checkpoint unless user says continue.

  protocol: l9-gmp-protocol phases 0–7

  artifact_trees:
    global_cursor_rules:
      path: .cursor-commands/rules/*.mdc
      count_approx: 57
      ssot: GlobalCommands
      commit_target: Cursor-Governance via make governance-backup
      frontmatter: [description, alwaysApply, globs]
    repo_cursor_overlay:
      path: .cursor/rules/*.mdc
      count_approx: 24
      ssot: IB-Odoo_19 repo (PlasticOS overlay)
      commit_target: PlasticOS make commit — NOT Cursor-Governance
      frontmatter: [description, alwaysApply, globs]
    claude_path_refs:
      path: .claude/rules/*.md
      count_approx: 9
      role: path-scoped summaries — NOT a competing lawbook
      frontmatter: [paths]
      commit_target: PlasticOS repo
      must_not: duplicate full INVARIANTS.md / global rule doctrine verbatim

  hard_rules:
    - RULES_ONLY
    - optimize_batch_prompts_first — do NOT overwrite Recursive Improvement.md or Recursive Alignment.md
    - use_gmp_protocol_with_modification_lock
    - do_not_touch_skills_or_skill_packs
    - do_not_wire_skills_or_edit_AUTONOMY_MANIFEST
    - do_not_edit_AGENTS_md_or_INVARIANTS_md_unless_user_explicitly_approves_phase_5_doc_fixes
    - preserve_mdc_frontmatter_unless_audit_proves_wrong
    - preserve_alwaysApply_and_globs_unless_audit_proves_wrong
    - global_rule_deletion_report_only — never delete global .mdc without explicit human approval
    - overlay_may_delete_only_if_fully_duplicated_by_global_with_evidence
    - claude_rules_may_thin_to_pointer_not_delete_doctrine
    - mark_TransportPacket_Gate_node_passes_N/A_unless_rule_governs_L9_nodes
    - no_implementation_code_no_fake_validation
    - label_Unknown_not_invent

  modification_lock:
    may_modify:
      - .cursor-commands/prompts/Recursive Improvement — Rules Batch.md
      - .cursor-commands/prompts/Recursive Alignment — Rules Batch.md
      - .cursor-commands/prompts/Rules Hardening Batch Orchestrator.md
      - .cursor-commands/rules/*.mdc
      - .cursor/rules/*.mdc
      - .claude/rules/*.md
      - reports/rules_inventory.yaml
      - reports/rules_hardening_log.md
      - reports/rule-alignment/*.md
      - reports/rule_conflict_matrix.csv
      - reports/rule_dedup_decisions.md
      - reports/rules_final_validation.md
      - reports/GMP-Report-018-rules-hardening-batch.md
    must_not_modify:
      - .cursor-commands/prompts/Recursive Improvement.md
      - .cursor-commands/prompts/Recursive Alignment.md
      - .cursor-commands/skills/**
      - .claude/skills/**
      - plasticos_/**
      - tests/**
      - ci/**
      - .github/workflows/**
      - pipeline_v2.py
      - AGENTS.md
      - INVARIANTS.md
      - ARCHITECTURE.md
      - AUTONOMY_MANIFEST.yaml

  authority_order:
    1: CANONICAL_LAW.md (.cursor/governance/CANONICAL_LAW.md)
    2: .cursor-commands/rules/97-governance-ssot-paths.mdc
    3: other global .cursor-commands/rules/*.mdc
    4: repo .cursor/rules/*.mdc (overlay — narrower, non-conflicting only)
    5: AGENTS.md / INVARIANTS.md (executable ground truth for PlasticOS commands)
    6: .claude/rules/*.md (pointers/summaries only)

  conflict_resolution:
    - global_wins_over_overlay on same topic
    - overlay_may_add_repo_specific_constraints — never weaken global
    - executable_ground_truth_wins_over_stale_prose — verify Makefile, ci.yml, AGENTS.md
    - unresolved → label Unknown + minimum_safe_next_action

  gmp_phases:
    phase_0:
      name: Plan lock + batch prompts + inventory
      todos:
        - T-001: Create Recursive Improvement — Rules Batch.md (Appendix A1)
        - T-002: Create Recursive Alignment — Rules Batch.md (Appendix A2)
        - T-003: Create Rules Hardening Batch Orchestrator.md (Appendix A3)
        - T-004: Create reports/rules_inventory.yaml (all .mdc + .claude/rules/*.md)
      exit: Phase 0 complete. Inventory locked. Batch prompts written.

    phase_1:
      name: Baseline confirmation
      checks:
        - every inventoried path exists
        - frontmatter parses
        - no protected path in TODO list
      exit: OVERALL STATUS READY

    phase_2:
      name: Implementation — improve align fix by wave
      exit: all waves complete or checkpoint stop

    phase_3:
      name: Enforcement
      checks:
        - no accidental scope creep into skills/addons
        - deletion candidates documented in rule_dedup_decisions.md

    phase_4:
      name: Validation
      commands:
        - bash .cursor-commands/ops/scripts/validate_governance_symlinks.sh
        - bash .cursor-commands/ops/scripts/validate_governance_no_hardcoded_paths.sh
      mechanical:
        - no /Users/ or /home/ hardcoded paths in changed rules
        - frontmatter valid on all changed .mdc
        - overlay alwaysApply count reported before/after

    phase_5:
      name: Recursive verify
      checks: diff vs locked TODOs only

    phase_6:
      name: SSOT backup (global changes only)
      command: make governance-backup
      when: after global rule batches committed locally in GlobalCommands git root

    phase_7:
      name: Finalize
      output: reports/GMP-Report-018-rules-hardening-batch.md

  per_rule_micro_loop:
    1_improve: Load Recursive Improvement — Rules Batch.md → write complete revised file(s)
    2_align: Load Recursive Alignment — Rules Batch.md → reports/rule-alignment/{basename}.md only (report mode)
    3_fix: Apply correction_roadmap critical/high only
    4_tracker: Update reports/rules_inventory.yaml row + append reports/rules_hardening_log.md

  batch_strategy:
    global_preferred_batch_size: 5_to_8
    group_global_by_prefix:
      - "97-governance-ssot-paths first"
      - "00-09 global / git / slash"
      - "80-89 gmp"
      - "90-99 protection"
      - "10-29 language"
      - "remaining global"
    overlay_waves:
      wave_1_high_drift:
        - 00-plasticos-master-context.mdc
        - 70-github-api-commit.mdc
        - 81-ci-manifest-contract.mdc
        - 82-ci-module-wiring.mdc
        - 83-ci-phantom-enum.mdc
        - 84-ci-odoo19-patterns.mdc
        - 85-ci-naming-ruff.mdc
        - 86-ci-github-actions.mdc
      wave_2_overlay_remainder:
        - all other .cursor/rules/*.mdc not in wave_1
      wave_3_claude_path_refs:
        - .claude/rules/architecture.md
        - .claude/rules/invariants.md
        - .claude/rules/learnings.md
        - .claude/rules/neo4j.md
        - .claude/rules/security.md
        - .claude/rules/system-state.md
        - .claude/rules/testing.md
        - .claude/rules/xml-views.md

  phase_5_cross_artifact:
    mode: read_only_first
    output:
      - reports/rule_conflict_matrix.csv
      - reports/rule_dedup_decisions.md
    implement_in_rules_only: true
    AGENTS_INVARIANTS_fixes: deferred unless user explicitly approves

  checkpoint:
    after: overlay wave_1
    deliver: rules_inventory.yaml + reports/rule-alignment/70-github-api-commit.md + alwaysApply count summary
    wait: user says continue for wave 2+

  acceptance_criteria:
    - batch_prompts_created_originals_preserved
    - all_rule_files_inventoried
    - global_rules_improved_and_aligned
    - overlay_deduped_against_global
    - claude_rules_thinned_not_competing
    - validation_scripts_run_or_failures_reported
    - conflict_matrix_and_dedup_decisions_exist
    - GMP-Report-018_signed

  convergence_block:
    required: true
    fields:
      - convergence_status
      - rules_only_scope_preserved
      - prompts_optimized_first
      - global_rules_status
      - overlay_status
      - claude_refs_status
      - validation_status
      - remaining_unknowns

---

# GMP-RULES-HARDEN-001 — Executable Rules Hardening Prompt

Paste this entire file (or say: **Execute `@.cursor-commands/prompts/GMP Rules Hardening — Execute.md`**).

Load **l9-gmp-protocol**. Do **not** edit attached plan files.

---

## Appendix A1 — Create `Recursive Improvement — Rules Batch.md`

```yaml
compiled_prompt:
  id: recursive_l9_improvement_rules_batch_v1
  role: l9_recursive_improvement_agent
  extends: Recursive Improvement.md

  objective: >
    Recursively improve ONE rule file or thematic batch of rule files (.mdc or .claude/rules/*.md).
    Inherit recursive passes from recursive_l9_improvement_prompt_v3.

  input_contract:
    required:
      - rule_path: path to ONE .mdc or .claude/rules/*.md OR thematic group list
      - tree: global_cursor | repo_overlay | claude_path_ref

  hard_rules_additions:
    - MUST preserve YAML frontmatter: description, alwaysApply, globs (.mdc) OR paths (.claude/rules/*.md)
    - MUST NOT edit skills, AGENTS.md, INVARIANTS.md, AUTONOMY_MANIFEST
    - MUST NOT weaken global authority when editing overlay
    - MUST use $HOME/Dropbox/... paths — never /Users/<user>/ or /home/<user>/
    - MUST strengthen MUST / MUST NOT / STOP / fail-closed where rule should be enforceable
    - MUST deduplicate against global rule on same topic before expanding overlay prose
    - global .mdc deletion: NEVER — report delete_candidate only

  rule_improvement_contract:
    body:
      - operational precision over philosophy
      - real commands only (make pr-check, make push, bash .cursor-commands/ops/scripts/...)
      - remove stale CI gates that contradict AGENTS.md / ci.yml
      - keep numbered-prefix meaning (81-ci-* = manifest contract, etc.)
    claude_path_refs:
      - may compress to pointer: "Authority: INVARIANTS.md §X / global rule Y"
      - must not become full duplicate of INVARIANTS.md

  output_requirements:
    must_return:
      - complete_revised_rule_file(s)
      - convergence_block
      - inventory_row: {path, tree, files_changed, execution_readiness}
      - per_file_summary: max one line per file
    must_not_return: [commentary_only, partial_patch_for_single_file_rules]
```

---

## Appendix A2 — Create `Recursive Alignment — Rules Batch.md`

```yaml
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
```

---

## Appendix A3 — Create `Rules Hardening Batch Orchestrator.md`

```yaml
compiled_prompt:
  id: rules_hardening_batch_orchestrator_v1
  role: gmp_rules_batch_executor

  per_batch_sequence:
    1: Recursive Improvement — Rules Batch.md
    2: Recursive Alignment — Rules Batch.md
    3: fix critical/high if implement_fixes_needed
    4: update rules_inventory.yaml + rules_hardening_log.md

  commit_discipline:
    after_global_batch: make governance-backup
    after_overlay_batch: stop — PlasticOS commit is separate user action unless user says commit

  stop_conditions:
    - modification lock violation
    - global delete requested without approval
    - phase 5 doc edit needed → STOP and ask
```

---

## Appendix A4 — `reports/rules_inventory.yaml` schema

```yaml
run_id: GMP-RULES-HARDEN-001
updated: null
rules:
  - path: .cursor-commands/rules/97-governance-ssot-paths.mdc
    tree: global_cursor
    basename: 97-governance-ssot-paths
    alwaysApply: true
    globs: null
    topic: governance_paths
    wave: global_0
    improve_status: pending
    align_status: pending
    dedup_action: keep  # keep | thin | delete_candidate
    execution_readiness: null
```

Pre-populate every `.cursor-commands/rules/*.mdc`, `.cursor/rules/*.mdc`, and `.claude/rules/*.md`.

---

## Execution order (Phase 2)

1. **Global Wave 0:** `97-governance-ssot-paths.mdc` alone first.
2. **Global batches:** 5–8 files by prefix (see `batch_strategy.group_global_by_prefix`).
3. **Overlay Wave 1:** 8 high-drift PlasticOS rules (see `overlay_waves.wave_1`).
4. **CHECKPOINT** — show inventory + sample alignment + alwaysApply before/after counts.
5. **Overlay Wave 2:** remaining `.cursor/rules/*.mdc`.
6. **Claude Wave 3:** `.claude/rules/*.md` — thin to pointers where duplicated.
7. **Phase 5 read-only:** conflict matrix + dedup decisions (no AGENTS.md edits unless approved).
8. **Phase 4–7:** validation scripts, governance-backup, GMP-Report-018.

---

## Inventory row commands (Phase 0 helper)

```bash
# Global
ls -1 .cursor-commands/rules/*.mdc

# Overlay
ls -1 .cursor/rules/*.mdc

# Claude path refs
ls -1 .claude/rules/*.md

# alwaysApply audit
grep -l "alwaysApply: true" .cursor/rules/*.mdc | wc -l
```

---

## Final declaration template (Phase 7)

```
GMP-RULES-HARDEN-001 COMPLETE.
Global rules: {n_changed}/{n_total}. Overlay: {n_changed}/{n_total}. Claude refs: {n_changed}/{n_total}.
Validation: {PASS|FAIL}. Governance backup: {done|skipped|FAIL}.
Evidence: reports/GMP-Report-018-rules-hardening-batch.md
```
