# MANIFEST.md

## Pack

Name: L9 Mobile Chat Session Hydration Strategy Pack  
Version: 1.1.3 polished deliverable  
Status: polished_ready_to_commit_canonical_draft  
Baseline: l9_recursive_design_refine_build_pack_v20_hygiene_aligned

## Responsibility

This pack enables ChatGPT mobile L9 sessions to hydrate by slice, resume from a compact packet, preserve architecture boundaries, and harvest end-session signals without carrying full transcripts or full kernel stacks.

## One-Command Validation

```bash
python run_all.py
```

## Scope Boundary

```yaml
owns:
  - mobile_chat_hydration
  - session_boot_prompt
  - hydration_playbook
  - context_slice_hydration_law
  - end_session_harvest_trigger
  - signal_propulsion_contract
  - artifact_registration_law

must_not_own:
  - universal_runtime
  - kernel_orchestration
  - repo_execution
  - assurance_verdicts
  - policy_decisions
  - graph_memory_runtime
```

## Inventory

Files inventoried: 66

See `FINAL_REPO_TREE.md` for the complete tree and `00_manifest/MANIFEST.yaml` for hash inventory.
