compiled_prompt:
  id: rules_hardening_batch_orchestrator_v1
  role: gmp_rules_batch_executor

  per_batch_sequence:
    1: kernels/Recursive Improvement (L9).md
    2: kernels/Recursive Alignment.md
    3: fix critical/high if implement_fixes_needed
    4: update rules_inventory.yaml + rules_hardening_log.md

  commit_discipline:
    after_global_batch: make governance-backup
    after_overlay_batch: stop — PlasticOS commit is separate user action unless user says commit

  stop_conditions:
    - modification lock violation
    - global delete requested without approval
    - phase 5 doc edit needed → STOP and ask
