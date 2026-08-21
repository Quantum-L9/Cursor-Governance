---
name: museum gold-nugget harvest
overview: "Side-by-side Quantum-L9 Python template for non-Constellation repos (runtimes/side-projects/experiments). Mine DX gold from Node-Template and PackageTemplate without becoming a node or dependency scaffold."
todos:
  - id: T1
    content: Lock three-template matrix + provenance ledger in TEMPLATE_INVENTORY/README/ARCHITECTURE: Node-Template=nodes,
    status: pending
  - id: T2
    content: Reposition default example package away from Gate-worker shell: remove required constellation-node-sdk/create_
    status: pending
  - id: T3
    content: Port general hygiene checks from Node-Template audit_engine (eval/exec/print bans; accidental reintro of Justf
    status: pending
  - id: T4
    content: Extend inventory_check with mention/required-file + layout checks for museum-as-generic-template; keep tools/ 
    status: pending
  - id: T5
    content: Parametric Cursor rules for generic Quantum-L9 Python repos (l9-python-repo + optional fastapi); rewrite away 
    status: pending
  - id: T6
    content: Thicken .l9/architecture.yaml + ownership.yaml for non-Constellation Python repos; ownership explicitly defers
    status: pending
  - id: T7
    content: Surgically port PackageTemplate config/errors/health/retry/protocols as optional generic package helpers (safe
    status: pending
  - id: T8
    content: Adapt dep-build-runner into scripts/birth-runner/ for generic Use-template→rename→verify(+optional push); OPEN
    status: pending
  - id: T9
    content: Reorganize tests unit/integration; import-smoke + hygiene + birth acceptance for generic package; optional mak
    status: pending
  - id: T10
    content: Rewrite docs for side-by-side identity (VALIDATION honesty, lifecycle for generic repos, when-not-to-use-this-
    status: pending
  - id: T11
    content: Final compliance: inventory_check + MANIFEST + pr-check + agent-check; prove absent Justfile/contracts/engineh
    status: pending
isProject: false
---

## PLAN: Gold-nugget harvest for non-Constellation Python museum template

**PLAN_DOCUMENT:** validated PASS — [`museum_gold_nugget_harvest.json`](museum_gold_nugget_harvest.json)  
**GMP Phase 0 lock:** [`museum_gold_nugget_harvest_gmp_phase0.md`](museum_gold_nugget_harvest_gmp_phase0.md)  
**Depth:** `standard`  
**Target:** `Quantum-L9/l9-repo-template`  
**Sources (mine only):** `L9-Node-Template@8999fd1` · `Constellation.PackageTemplate@dcb5d24`

### Identity lock (user clarification)

`l9-repo-template` lives **side by side** with the other two templates. It does **not** replace or duplicate them.

| Template | Owns |
|----------|------|
| [L9-Node-Template](https://github.com/Quantum-L9/L9-Node-Template) | Constellation **nodes** |
| [Constellation.PackageTemplate](https://github.com/Quantum-L9/Constellation.PackageTemplate) | `constellation_*` **birth dependencies** |
| **l9-repo-template (museum)** | Quantum-L9 Python repos **outside** Constellation — runtimes, side projects, experiments, misc services |

Prior Gate-worker head-start on the feature branch conflicts with this identity and is corrected in **T2**.

### Objective

Mine reusable DX/tooling gold from L9-Node-Template@8999fd1 and Constellation.PackageTemplate@dcb5d24 into Quantum-L9/l9-repo-template so the museum is a first-class Quantum-L9 Python GitHub Template for runtimes, side projects, and experiments that live outside Constellation — side-by-side with (not replacing) the node template and the dependency-package template.

**Success:**
- AGENTS.md / README / ARCHITECTURE state the three-template matrix: Node-Template=nodes, PackageTemplate=constellation_* deps, l9-repo-template=non-Constellation Python repos
- TEMPLATE_INVENTORY classifies every mined surface PORT_SURGICAL|EXTRACT_CONCEPT|ALREADY_HAVE|REJECT with source SHA; node/dep product surfaces are REJECT_WRONG_PRODUCT
- Default example package is a plain Python package (no create_node_app, no Gate handlers, no constellation-node-sdk as required runtime dep)
- General hygiene audit in verify (eval/exec/print + no Justfile/contracts/enginehandlers accidental reintro); not Constellation transport law enforcement
- inventory_check + parametric Cursor rules for generic Python/FastAPI repos; birth-runner is Use-template→rename→verify for generic packages (OPEN_PR=0)
- PackageTemplate config/errors/health/retry concepts land as optional generic helpers, not Gate-worker helpers
- make pr-check and make agent-check PASS; CI remains sync-ci; tools/ allowlist unchanged

### Executive picture

Mine **DX force-multipliers** (inventory, hygiene, birth-runner, package helpers, Cursor rules, test layout) from the two Constellation-shaped templates. Leave their **product roles** alone. Museum default is a thin generic Python (+ minimal FastAPI hello) package — not `create_node_app`, not `constellation_*` birth.

**Highest leverage:** identity strip (T2) → hygiene/inventory → generic birth-runner → PackageTemplate helpers → docs matrix.

**Hard rejects:** becoming a node/dep template · enginehandlers/nodespec/contracts · PacketEnvelope/Gate peer laws as museum gates · Justfile · Fix-B OTel Python · parallel museum CI · PackageTemplate plays · `tools/` expansion · CG Makefile copy.

### Scope

**In:**
- Identity lock + docs: museum is non-Constellation Quantum-L9 Python template (runtimes/side-projects/experiments)
- Strip or demote Gate-worker/node shell from default template surfaces (handlers/spec/GATE_URL-required framing) toward a thin generic example package
- Harvest from Node-Template: inventory/mention patterns, template_compliance ideas, VALIDATION honesty, generic hygiene rules from audit_engine (not PacketEnvelope/Gate peer laws), fastapi rule rewrite for generic apps, pre-commit inventory hook
- Harvest from PackageTemplate: dep-build-runner mechanics→scripts/birth-runner for generic Use-template birth; config/errors/health/retry/protocols as optional package helpers; unit/integration layout; import-smoke; birth acceptance triad rewritten for generic packages
- Core thin Makefile + Repo.mk + gov-* WS= retained; sync-ci retained

**Out:**
- Duplicating or replacing L9-Node-Template (Constellation nodes) or Constellation.PackageTemplate (constellation_* birth deps)
- Making museum the canonical Gate-worker / TransportPacket / create_node_app template
- Porting enginehandlers, nodespec, contracts/, ENGINESPEC, domain/, PacketEnvelope-era bridge
- Porting constellation_* library birth plays, PyPI/sigstore release, mkdocs-as-required, mutmut
- Museum-owned parallel CI; Justfile; Fix-B OTel Python package; expanding tools/ beyond l9_repo+integrity
- Copying Cursor-Governance Makefile/ops; OPEN_PR=1 / auto-merge birth defaults
- Gate-only peer-HTTP bans as museum product law (those belong to node template / Gate_SDK)

### Pre-Validation

| Check | Command / action | Pass criteria | Status |
|-------|------------------|---------------|--------|
| P0 | bind /Users/ib-mac/l9-repo-template @6c5bc78; note current branch still carries Gate-worker head-start — this plan repositions identity | museum root exists; identity mismatch acknowledged in plan | passed |
| P1 | sources inventoried at L9-Node-Template@8999fd1 and PackageTemplate@dcb5d24 | gold tables available from prior archaeology | passed |
| P2 | cd /Users/ib-mac/l9-repo-template && make pr-check | PASS on current tree before identity reposition edits | passed |
| P3 | user identity lock: museum side-by-side for non-Constellation repos; NOT nodes; NOT deps | explicit user clarification recorded | passed |

### TODO Plan

| ID | Task | Files | Effort | Risk | Deps | Leverage |
|----|------|-------|--------|------|------|----------|
| T1 | Lock three-template matrix + provenance ledger in TEMPLATE_INVENTORY/README/ARCHITECTURE: Node-Template=nodes, PackageTemplate=deps, museum=non-Constellation Python; classify mined surfaces including REJECT_WRONG_PRODUCT for node/dep-only gold | `TEMPLATE_INVENTORY.md`, `README.md`, `ARCHITECTURE.md`… | S | low | — | 1 |
| T2 | Reposition default example package away from Gate-worker shell: remove required constellation-node-sdk/create_node_app/handlers/spec/GATE_URL as template defaults; leave a thin generic Python package (+ optional FastAPI hello if kept as non-Constellation example) | `src/l9_example_pkg/`, `pyproject.toml`, `uv.lock`… | L | high | T1 | 2 |
| T3 | Port general hygiene checks from Node-Template audit_engine (eval/exec/print bans; accidental reintro of Justfile/contracts/enginehandlers) into scripts/repo_hygiene_audit.py + Semgrep; do NOT encode PacketEnvelope/Gate peer-routing laws as museum product gates | `scripts/repo_hygiene_audit.py`, `.semgrep/semgrep-rules.yaml`, `Repo.mk`… | M | medium | T1 | 3 |
| T4 | Extend inventory_check with mention/required-file + layout checks for museum-as-generic-template; keep tools/ allowlist; deny Justfile and constellation node/dep scaffolding dirs | `scripts/inventory_check.py`, `tests/unit/test_inventory_check.py`, `.pre-commit-config.yaml` | M | medium | T1, T2 | 4 |
| T5 | Parametric Cursor rules for generic Quantum-L9 Python repos (l9-python-repo + optional fastapi); rewrite away from l9-node-contract/Gate-worker; document when to use Node-Template vs PackageTemplate vs museum | `.cursor/rules/templates/l9-python-repo.mdc.template`, `.cursor/rules/templates/fastapi.mdc.template`, `plugin-config.yaml`… | M | medium | T1 | 5 |
| T6 | Thicken .l9/architecture.yaml + ownership.yaml for non-Constellation Python repos; ownership explicitly defers nodes→L9-Node-Template and constellation_* deps→PackageTemplate | `.l9/architecture.yaml`, `.l9/ownership.yaml`, `AGENTS.md` | S | low | T1 | 6 |
| T7 | Surgically port PackageTemplate config/errors/health/retry/protocols as optional generic package helpers (safe-at-import, validate_safe, structured errors) — not Gate/worker helpers; no GATE_URL coupling | `src/l9_example_pkg/settings.py`, `src/l9_example_pkg/errors.py`, `src/l9_example_pkg/health.py`… | M | medium | T2, T6 | 7 |
| T8 | Adapt dep-build-runner into scripts/birth-runner/ for generic Use-template→rename→verify(+optional push); OPEN_PR=0; no auto-merge; no constellation_* plays; no Gate worker birth framing | `scripts/birth-runner/README.md`, `scripts/birth-runner/01_preflight.sh`, `scripts/birth-runner/02_bootstrap.sh`… | L | high | T2, T3, T4 | 8 |
| T9 | Reorganize tests unit/integration; import-smoke + hygiene + birth acceptance for generic package; optional make test-cov without library 90% gate | `tests/unit/`, `tests/integration/`, `tests/conftest.py`… | M | low | T2, T3, T7, T8 | 9 |
| T10 | Rewrite docs for side-by-side identity (VALIDATION honesty, lifecycle for generic repos, when-not-to-use-this-template); remove node/handler birth docs as primary path | `docs/VALIDATION.md`, `docs/LIFECYCLE.md`, `docs/ops/REPO_BIRTH.md`… | M | low | T1, T5, T6, T8 | 10 |
| T11 | Final compliance: inventory_check + MANIFEST + pr-check + agent-check; prove absent Justfile/contracts/enginehandlers; prove default pyproject has no required constellation-node-sdk; prove docs point to sibling templates for nodes/deps | `scripts/inventory_check.py`, `MANIFEST.sha256`, `tests/unit/test_template_compliance.py` | S | medium | T2, T3, T4, T7, T8, T9, T10 | 11 |

### Critical Path

T1 → T2 → T3 → T4 → T7 → T8 → T9 → T11

### Milestones

| Milestone | Outcome | Unlocks |
|-----------|---------|---------|
| M1 | Identity locked + default package no longer a Gate worker | safe generic helper/docs/birth ports |
| M2 | Hygiene + inventory + birth-runner work for generic Use-template flow | test/docs completion |
| M3 | Three-template matrix documented; pr-check+agent-check green | GMP close / PR |

### Checkpoints

| CP | After | Evidence | No-go |
|----|-------|----------|-------|
| C1 | M1 | README three-template matrix present; pyproject has no required constellation-node-sdk; no handlers.py/@register_handler as default path | stop harvest ports until identity strip lands |
| C2 | M2 | birth-runner dry-run rename+verify for generic PKG; OPEN_PR=0; hygiene audit does not require PacketEnvelope fixtures | disable push step; keep verify-only birth |
| C3 | M3 | make pr-check && make agent-check PASS; TEMPLATE_INVENTORY has zero unclassified mined surfaces; WHEN_TO_USE points nodes/deps to sibling templates | block merge |

### Stress Test

**Disconfirming:**
- Does any TODO recreate a Gate-worker or constellation_* dependency scaffold as the default museum path?
- Would keeping create_node_app as the example confuse users who should use L9-Node-Template?
- Does hygiene audit smuggle Constellation transport bans that belong only in node/SDK repos?
- Does birth-runner clone PackageTemplate plays that mint TransportPacket packages?
- Is museum still documented as replacement for golden-repo Gate workers without pointing to Node-Template?

**Assumed false if:**
- museum must include constellation-node-sdk to be Quantum-L9
- side projects need Gate routing by default
- node and dep templates should be deprecated in favor of museum

**Blast radius:** Wrong identity makes every Use-template birth a fake node/dep repo, duplicates sibling templates, and confuses Quantum-L9 org scaffolding.

**Rollback:** Revert identity/harvest commits; restore prior branch tip; keep Core facade/Repo.mk/gov-* if still desired.

### Leverage

**Ranked:** T1, T2, T3, T4, T8, T7, T5, T6, T9, T10, T11

**Shared causes:**
- Two sibling templates already own nodes and constellation_* deps
- Museum value is Quantum-L9 DX for everything else
- Prior Gate-worker head-start on the branch conflicts with side-by-side identity

**Deletions / consolidations:**
- Demote/remove default Gate-worker shell (handlers, spec.yaml Gate registration, required SDK dep)
- Do not port PacketEnvelope/Gate peer laws, enginehandlers, nodespec, contracts/, constellation_* plays
- Do not vendor node/dep CI ladders; keep sync-ci
- Birth-runner under scripts/ only; no tools/ expansion

### Doc / Root Surface Impact

| Surface | Action | Todos | Notes |
|---------|--------|-------|-------|
| README.md | update | T1, T2, T10 |  |
| AGENTS.md | update | T1, T5, T6, T10 |  |
| ARCHITECTURE.md | update | T1, T6, T10 |  |
| TEMPLATE_INVENTORY.md | update | T1, T11 |  |
| docs/WHEN_TO_USE.md | update | T10 | new side-by-side guide |
| Repo.mk | update | T3, T8, T9 |  |
| L9-Node-Template / PackageTemplate repos | n_a | — | siblings; museum must not absorb their product role |

### Risks

| Risk | Mitigation |
|------|------------|
| Stripping Gate-worker shell breaks in-flight consumers of feat/gate-worker-head-start | Document migration: Constellation nodes use L9-Node-Template; changelog notes identity correction |
| Generic FastAPI example reintroduces Fix-B OTel stack | Compose-only obs remains opt-in; no OTel Python package in default deps |
| Birth-runner still smells like PackageTemplate dep factory | No plays catalog; config fields are pkg/repo only; docs say non-Constellation |

### Unknowns (bounded)

| ID | Question | Effect | Resolution |
|----|----------|--------|------------|
| U1 | Should the thin default example be pure library package only, or include a minimal FastAPI hello (non-Gate)? | Default chosen: minimal FastAPI hello without Gate/SDK so run/dev targets remain useful for runtimes/side projects | accept_bounded |
| U2 | Retain optional observability compose pack for non-Constellation services? | Keep opt-in make obs-up; not required for verify | accept_bounded |

### Final Validation

| Check | Command | Pass criteria | Status |
|-------|---------|---------------|--------|
| V1 | `cd /Users/ib-mac/l9-repo-template && make pr-check` | PASS | pending |
| V2 | `cd /Users/ib-mac/l9-repo-template && make agent-check` | PASS | pending |
| V3 | `rg -n 'constellation-node-sdk|create_node_app|register_handler' pyproject.toml src README.md || true` | no required SDK/worker framing in default template surfaces (docs may mention siblings) | pending |
| V4 | `rg -n 'L9-Node-Template|PackageTemplate|WHEN_TO_USE|three-template|side-by-side' README.md ARCHITECTURE.md docs/WHEN_TO_USE.md` | three-template matrix documented | pending |

### Convergence

- **status:** `partial`
- **remaining unknowns:** U1, U2
- **next_skill:** `l9-gmp-protocol`
- **stop_reason:** Identity-corrected PLAN_DOCUMENT ready; final_validation pending GMP execution

### GMP Handoff

**May modify:**
- TEMPLATE_INVENTORY.md
- CHANGELOG.md
- .l9/
- AGENTS.md
- ARCHITECTURE.md
- README.md
- Repo.mk
- plugin-config.yaml
- .cursor/rules/
- .semgrep/
- .pre-commit-config.yaml
- scripts/
- src/l9_example_pkg/
- tests/
- docs/
- pyproject.toml
- uv.lock
- spec.yaml
- .env.example
- Dockerfile
- docker-compose.yml
- MANIFEST.sha256

**Must not modify:**
- Quantum-L9/L9-Node-Template product role
- Quantum-L9/Constellation.PackageTemplate product role
- Cursor-Governance ops copy-in
- tools/ beyond l9_repo + check_workflow_integrity
- Adding Justfile, contracts/, nodespec, enginehandlers, Fix-B OTel package

**Preserved contracts:**
- Museum is NOT the Constellation node template and NOT the constellation_* dep template
- Core thin Makefile + Repo.mk + gov-* WS=
- CI via make sync-ci
- tools/ allowlist
- OPEN_PR=0 for in-repo gates

**Validation commands:**
- `make pr-check`
- `make agent-check`
- `make inventory-check`
- `python scripts/repo_hygiene_audit.py`

### Estimate

1–2 GMP cycles on feat branch after identity correction

### Checklist

- Identity lock: side-by-side non-Constellation Python template
- Does not duplicate Node-Template or PackageTemplate products
- Gate-worker default shell demoted/removed
- U1 FastAPI hello / U2 obs compose bounded
- validate_plan_document.py PASS

---

_Official projection of PLAN_DOCUMENT. Authority is the JSON._
