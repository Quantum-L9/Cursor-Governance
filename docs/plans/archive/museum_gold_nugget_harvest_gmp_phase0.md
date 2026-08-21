# GMP Phase 0 lock (identity-corrected PLAN_DOCUMENT)

```
# GMP Phase 0 — TODO PLAN LOCK (from l9-plan)

[TODO T1]
Phase: 2
File: TEMPLATE_INVENTORY.md
Operation: Replace
Anchor: TEMPLATE_INVENTORY.md + README identity section
Description: Lock three-template matrix + provenance ledger in TEMPLATE_INVENTORY/README/ARCHITECTURE: Node-Template=nodes, PackageTemplate=deps, museum=non-Constellation Python; classify mined surfaces including REJECT_WRONG_PRODUCT for node/dep-only gold
Dependencies: none

[TODO T2]
Phase: 2
File: src/l9_example_pkg/
Operation: Replace
Anchor: src/l9_example_pkg and pyproject dependencies
Description: Reposition default example package away from Gate-worker shell: remove required constellation-node-sdk/create_node_app/handlers/spec/GATE_URL as template defaults; leave a thin generic Python package (+ optional FastAPI hello if kept as non-Constellation example)
Dependencies: T1

[TODO T3]
Phase: 2
File: scripts/repo_hygiene_audit.py
Operation: Create
Anchor: verify target in Repo.mk
Description: Port general hygiene checks from Node-Template audit_engine (eval/exec/print bans; accidental reintro of Justfile/contracts/enginehandlers) into scripts/repo_hygiene_audit.py + Semgrep; do NOT encode PacketEnvelope/Gate peer-routing laws as museum product gates
Dependencies: T1

[TODO T4]
Phase: 2
File: scripts/inventory_check.py
Operation: Wrap
Anchor: scripts/inventory_check.py REQUIRED/DENY
Description: Extend inventory_check with mention/required-file + layout checks for museum-as-generic-template; keep tools/ allowlist; deny Justfile and constellation node/dep scaffolding dirs
Dependencies: T1, T2

[TODO T5]
Phase: 2
File: .cursor/rules/templates/l9-python-repo.mdc.template
Operation: Create
Anchor: plugin-config.yaml rule list
Description: Parametric Cursor rules for generic Quantum-L9 Python repos (l9-python-repo + optional fastapi); rewrite away from l9-node-contract/Gate-worker; document when to use Node-Template vs PackageTemplate vs museum
Dependencies: T1

[TODO T6]
Phase: 2
File: .l9/architecture.yaml
Operation: Replace
Anchor: .l9/architecture.yaml identity/boundaries
Description: Thicken .l9/architecture.yaml + ownership.yaml for non-Constellation Python repos; ownership explicitly defers nodes→L9-Node-Template and constellation_* deps→PackageTemplate
Dependencies: T1

[TODO T7]
Phase: 2
File: src/l9_example_pkg/settings.py
Operation: Create
Anchor: src/l9_example_pkg helpers
Description: Surgically port PackageTemplate config/errors/health/retry/protocols as optional generic package helpers (safe-at-import, validate_safe, structured errors) — not Gate/worker helpers; no GATE_URL coupling
Dependencies: T2, T6

[TODO T8]
Phase: 2
File: scripts/birth-runner/README.md
Operation: Create
Anchor: scripts/birth-runner/ (NOT tools/)
Description: Adapt dep-build-runner into scripts/birth-runner/ for generic Use-template→rename→verify(+optional push); OPEN_PR=0; no auto-merge; no constellation_* plays; no Gate worker birth framing
Dependencies: T2, T3, T4

[TODO T9]
Phase: 2
File: tests/unit/
Operation: Replace
Anchor: tests/ layout
Description: Reorganize tests unit/integration; import-smoke + hygiene + birth acceptance for generic package; optional make test-cov without library 90% gate
Dependencies: T2, T3, T7, T8

[TODO T10]
Phase: 2
File: docs/VALIDATION.md
Operation: Create
Anchor: docs/ WHEN_TO_USE + identity
Description: Rewrite docs for side-by-side identity (VALIDATION honesty, lifecycle for generic repos, when-not-to-use-this-template); remove node/handler birth docs as primary path
Dependencies: T1, T5, T6, T8

[TODO T11]
Phase: 2
File: scripts/inventory_check.py
Operation: Wrap
Anchor: make pr-check / make agent-check
Description: Final compliance: inventory_check + MANIFEST + pr-check + agent-check; prove absent Justfile/contracts/enginehandlers; prove default pyproject has no required constellation-node-sdk; prove docs point to sibling templates for nodes/deps
Dependencies: T2, T3, T4, T7, T8, T9, T10

MODIFICATION LOCK
may-modify: TEMPLATE_INVENTORY.md, CHANGELOG.md, .l9/, AGENTS.md, ARCHITECTURE.md, README.md, Repo.mk, plugin-config.yaml, .cursor/rules/, .semgrep/, .pre-commit-config.yaml, scripts/, src/l9_example_pkg/, tests/, docs/, pyproject.toml, uv.lock, spec.yaml, .env.example, Dockerfile, docker-compose.yml, MANIFEST.sha256
must-not-modify: Quantum-L9/L9-Node-Template product role, Quantum-L9/Constellation.PackageTemplate product role, Cursor-Governance ops copy-in, tools/ beyond l9_repo + check_workflow_integrity, Adding Justfile, contracts/, nodespec, enginehandlers, Fix-B OTel package
preserved_contracts: Museum is NOT the Constellation node template and NOT the constellation_* dep template, Core thin Makefile + Repo.mk + gov-* WS=, CI via make sync-ci, tools/ allowlist, OPEN_PR=0 for in-repo gates
validation_commands: make pr-check, make agent-check, make inventory-check, python scripts/repo_hygiene_audit.py

Phase 0 complete. TODO PLAN locked from PLAN_DOCUMENT.

```
