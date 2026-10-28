# Skill Manifest

## Control plane

- `SKILL.md`: identity, activation, authority, adaptive routing, evidence ledger, adapters, readiness, and failure law.
- `expertise_model.yaml`: compressed domain expertise.
- `skill_intelligence_report.yaml`: exemplary intelligence evidence.

## Adaptive reasoning

- `references/adaptive-optimize-router.yaml`
- `references/evidence-decision-ledger-contract.yaml`
- `references/adaptive-convergence.md`
- `scripts/route_optimize.py`
- `scripts/validate_decision_ledger.py`
- `scripts/validate_adaptive_reasoning.py`
- `assets/adaptive-route-cases.json`

## Domain contracts

- `references/optimize-cli-product-contract.md`
- `references/latent-capability-activation.md`
- `references/docs-code-capability-divergence.md`
- `references/revision-synthesis-leverage-adapter.md`
- `references/source-domain-agnostic-leverage.yaml`
- `references/ecosystem-adapters.md`
- `references/context-first-reuse.yaml`

## Delivery contracts

- `references/pr-commit-pack-contract.md`
- `references/deploy-playbook-contract.md`
- `references/agent-handoff-contract.md`
- `references/convergence-and-failure.md`

## Schemas and fixtures

- `schemas/pack-spec.schema.json`
- `schemas/pack-manifest.schema.json`
- `assets/pack-spec.example.json`
- `assets/activation-cases.json`

## Full-throttle activation mode

- `references/full-throttle-activation.md`: mode sub-contract (danger classifier, empirical back-out, pack shape, invariants).
- `assets/full-throttle.example.json`: example apply-mode report consumed by the pack builder.
- `scripts/flag_inventory.py`: off-by-default flag inventory + polarity-aware danger classifier + consumer-reachability signal (`consumer_evidence`/`needs_wiring`) + non-runtime/infra `scope` holds + flip transform.
- `scripts/full_throttle.py`: worktree-isolated flip → test → empirical back-out harness; multi-repo driver.
- `scripts/build_flag_activation_pack.py`: standalone review-required flag-activation pack builder.

## Execution and validation

- `scripts/build_commit_pack.py`
- `scripts/validate_commit_pack.py`
- `scripts/validate_identity_lock.py`
- `scripts/validate_activation_model.py`
- `scripts/validate_latent_capability_integration.py`
- `scripts/validate_revision_synthesis.py`
- `scripts/scan_capabilities.py`
- `scripts/measure.py`
- `scripts/validate_exemplary_skill.py`
- `scripts/self_test.py`
- `requirements.txt`: Python runtime dependencies (jsonschema, PyYAML).
- `references/source-dead-wiring-latent-capability-audit.md`: dead-wiring / latent-capability audit source contract.
