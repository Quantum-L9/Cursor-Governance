# L9 Coding Agent Manifest

**Release:** 1.3.0  
**Runtime identity:** `l9-coding-agent`  
**Distribution shape:** root `SKILL.md`, no wrapper directory

## Composition law

`SKILL.md` routes to `runtime/BOOTSTRAP.yaml`. The bootstrap loads only the current execution concern. `runtime/MANIFEST.yaml` owns machine-readable composition and semantic-owner mapping. Root operator and exemplary-intelligence artifacts are package-only unless the skill is being maintained, validated, promoted, or packaged.

## File inventory

- `CHANGELOG.md`
- `MANIFEST.md`
- `README.md`
- `RUNBOOK.md`
- `SKILL.md`
- `VALIDATION.md`
- `agents/openai.yaml`
- `catalogs/KILL_PATTERNS.yaml`
- `catalogs/REASON_CODES.yaml`
- `contracts/AUTHORITY_AND_BOUNDARIES.yaml`
- `contracts/CONVERGENCE.yaml`
- `contracts/EXECUTION_CONTRACT.yaml`
- `contracts/IMPLEMENTATION_INTEGRITY.yaml`
- `contracts/VALIDATION_AND_EVIDENCE.yaml`
- `evals/BEHAVIOR_CONFORMANCE.yaml`
- `expertise_model.yaml`
- `integrations/GAR_HANDOFF.yaml`
- `integrations/L9_RUNTIME_BINDING.yaml`
- `kernels/CODING_KERNEL.yaml`
- `references/smart_exemplary_spec.yaml`
- `runtime/BOOTSTRAP.yaml`
- `runtime/MANIFEST.yaml`
- `runtime/RUN_STATE.yaml`
- `runtime/STATE_MACHINE.yaml`
- `schemas/execution-contract.schema.json`
- `schemas/execution-receipt.schema.json`
- `scripts/validate_execution_contract.py`
- `scripts/validate_lazy_bootstrap.py`
- `scripts/validate_runtime_alignment.py`
- `skill_intelligence_report.yaml`

## Ownership notes

- Runtime semantics live under `runtime/`, `contracts/`, `kernels/`, `catalogs/`, and `integrations/`.
- Schemas and their runtime validators load only when structured contract/receipt validation is material.
- `expertise_model.yaml`, `skill_intelligence_report.yaml`, `references/smart_exemplary_spec.yaml`, evals, and operator docs do not govern ordinary coding execution.
- `agents/openai.yaml` is retained intentionally because this release targets ChatGPT as one supported installation surface.
