compiled_prompt:
  id: skill_hardening_batch_orchestrator_v1
  role: gmp_skill_batch_executor

  objective: >
    Execute GMP-SKILL-HARDEN-001 per-skill loop: improvement then alignment.

  modification_lock:
    may_modify: [.cursor-commands/skills/l9-*/, .claude/skills/plasticos-*/, reports/skill-hardening-inventory.yaml, reports/skill-alignment/]
    must_not_modify: [AGENTS.md, .claude/README.md, AUTONOMY_MANIFEST.yaml, plasticos_*/, tests/, ci/]

  per_skill_sequence:
    1: "Recursive Improvement — Skills Batch.md → write skill pack"
    2: "Recursive Alignment — Skills Batch.md → reports/skill-alignment/{name}.md only"
    3: "If critical/high and implement_fixes_needed → apply to skill pack"
    4: "Update reports/skill-hardening-inventory.yaml"

  wave_skip_rule:
    applies_to: wave_2_only
    skip_when: [converged, zero critical/high, no file changes]

  batch_wire:
    deferred_until: all 43 skills complete
    skill: l9-wire-skill-into-repo
