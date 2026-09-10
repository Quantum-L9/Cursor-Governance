---
name: l9-update-agent-docs
description: compile repository changes into typed documentation and operational-contract obligations, assess Makefile/pyproject surfaces, and emit repo-docs receipts. use when refreshing repo or agent docs, checking docs or operational-contract impact after code/CI changes, generating module READMEs, or proving documentation freshness before merge.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, docs, obligations, agents, ci, maintenance]
  owner: igor_beylin
  status: active
  version: 3.1.0
  updated: 2026-09-08
  when_to_use: compile documentation obligations after repository changes, assess supported operational contract surfaces, refresh governed documentation through its canonical owner, or prove closure with a machine receipt
---

# Repository Documentation Obligation Compiler

## Purpose

Compile repository state plus a repository delta into first-class documentation obligations. Each material obligation names the exact target, source revision, canonical obligation owner, semantic owner, execution owner, mutation guard when applicable, required action, evidence, validation requirements, and lifecycle state. Surfaces are routing topology; `DocumentationObligation` remains the durable unit of work.

Repository documentation is not limited to Markdown. A repository surface may participate when it embeds a meaningful operator- or agent-facing contract that can be deterministically assessed against existing repository authority. `Makefile` and `pyproject.toml` are the first supported operational-contract surfaces. Their admission does not make Repo Docs the semantic authority for Make, Python packaging, dependency policy, CI, or root-file mutation policy.

The compiler is not a doctrine author, general docs writer, generic parser framework, ADR owner, API contract owner, CI platform, configuration framework, or replacement for specialist generators and domain authorities.

## Canonical contract

```text
repository state + repository delta
  -> documentation topology
  -> deterministic impact qualification
  -> target resolution
  -> DocumentationObligation[]
  -> selective semantic Harvest when required
  -> deterministic operational-surface assessment when configured
  -> owner-native action / handoff / preserve
  -> mutation-guard resolution
  -> validation
  -> repo-docs receipt
```

Machine authority:

- topology: `references/doc-surface-policy.yaml`
- obligation schema: `contracts/documentation-obligation.schema.json`
- receipt schema: `contracts/repo-docs-receipt.schema.json`
- machine compiler: `scripts/repo_docs.py`
- operational assessment registry: `scripts/doc_surface_analysis.py`
- compatibility CLI: `scripts/validate_pointer_headings.py`

`l9.repo-docs.receipt.v3` derives PASS/PARTIAL/BLOCKED from obligation terminality plus structural validation failures. Aggregate impact/capability/Harvest fields are diagnostics and provenance, not competing obligation truth.

## Ownership boundaries

- `l9-update-agent-docs` owns documentation topology, impact qualification, target resolution, obligation compilation, deterministic materiality assessment for explicitly registered operational surfaces, freshness semantics, admission of semantic evidence, optional `llms.txt`, and the repo-docs receipt.
- `DocumentationObligation` remains the only durable work unit. `assessment` is evidence attached to an obligation, never a second findings ledger or second obligation system.
- operational-surface ownership is split explicitly:
  - `obligation_owner` owns compilation and lifecycle accounting;
  - `semantic_owner` owns the meaning of the underlying operational contract;
  - `execution_owner` owns the bounded repair path;
  - `mutation_guard` owns mutation admissibility.
- `l9-update-agent-docs` must not absorb Make/Python semantic ownership merely because it detects a material defect.
- `ops/config/root-file-protection.json` remains the canonical mutation-protection contract. Repo Docs reads and resolves its rule at runtime; it must not copy `additive_only` or other guard semantics into a second authority.
- `l9-intelligence-harvest` owns semantic discovery and qualification. The compiler consumes canonical `harvest.json`; it never copies Harvest reasoning or mutates the donor through Harvest.
- `readme-pipeline-v1` and `scripts/generate_subsystem_readmes.py` own module README rendering and language extraction.
- `l9-architecture-decision-records` owns ADR authoring.
- repository/API owners own API reference generation.
- organization/community-health owners remain external.
- `CANONICAL_LAW.md` remains external authority.
- `AGENTS.md` remains the operating-instruction SSOT.
- `l9-wire-into-repo` owns wiring, rewiring, registration, and reachability.

Invariant: **Harvest discovers and qualifies semantic truth. Repo Docs compiles obligations and deterministic materiality evidence. Domain owners retain semantics. Mutation guards retain mutation authority. Specialist owners render their surfaces. Receipts prove closure.**

## Operational-surface architecture

Operational surfaces are opt-in and closed-world. A surface is assessable only when `references/doc-surface-policy.yaml` declares an analyzer ID that exists in the static registry in `scripts/doc_surface_analysis.py`.

Current registry:

- `makefile-contract-v1` -> `scripts/surface_analyzers/makefile.py`
- `python-project-contract-v1` -> `scripts/surface_analyzers/pyproject.py`

Unknown analyzer IDs fail closed. Do not add dynamic imports, entry-point discovery, repository scanning for plugins, or a generic parser framework.

An analyzer may produce deterministic findings only. Each finding identifies the violated property, observed state, expected state, evidence, severity, and remediation class. The analyzer does not author architecture, waive a guard, or declare its own mutation successful.

Assessment dispositions:

- `IMPROVE`: confirmed material defect remains; bounded action is required.
- `PRESERVE`: deterministic assessment found no material improvement; no mutation is justified.
- `HANDOFF`: the defect is real but execution belongs to another authority.
- `UNKNOWN`: assessment cannot safely resolve the condition.
- `NOT_APPLICABLE`: no applicable target exists.

A touched operational file is never proof of improvement by itself. A material finding keeps `material_improvement` validation non-terminal until a rerun observes that the finding is gone.

## Makefile contract

`makefile_contract` is a repository operator command contract. Its analyzer is intentionally narrow and deterministic. It currently checks:

- direct `python`/`python3` recipe invocation when the Makefile declares a locked `PYTHON` runner;
- literal `python` / `python3` / `$(PYTHON)` recipe script arguments that no longer resolve.

The surface may be expanded only with evidence-backed deterministic checks whose semantic authority already exists in the repository. Do not use it to invent targets, redesign operator workflows, or turn Makefile style preferences into material findings.

## Python project contract

`python_project_contract` is the Python environment and tooling contract. Its analyzer currently checks:

- `project.requires-python` alignment with Ruff, mypy, and Pyright interpreter settings when those settings are present;
- `uv.lock` presence when `[tool.uv]` declares the uv project environment contract;
- skill `scripts/self_test.py` registration against `ops/config/python-contract.json`;
- root pytest collection protection for those self-test scripts through pyproject addopts or root `conftest.py`.

Dependency and tool-policy truth remains in the repository's existing Python authorities. Do not add packages from aspiration, infer version policy from preference, or duplicate `ops/config/python-contract.json` inside this skill.

## Evidence and authority order

1. `CANONICAL_LAW.md`
2. `ops/autonomy/surface_profile.yaml`
3. `AGENTS.md`
4. owner-native mutation/security contracts such as `ops/config/root-file-protection.json`
5. `references/doc-surface-policy.yaml` for this skill's topology and analyzer routing
6. owner-native source/configuration named by the topology
7. admitted `harvest.json` for semantic qualification only
8. Unknown

Donor material is evidence, never beneficiary authority. Stronger beneficiary semantics win.

## Execution protocol

### 1. Bind repository and change scope

Run the machine compiler before editing:

```bash
python skills/l9-update-agent-docs/scripts/repo_docs.py --root <repo> --changed-since <base> --receipt .artifacts/repo-docs-receipt.json --json
```

For GitHub PR execution, pass the source PR head and the tested checkout revision separately when available:

```bash
--source-head-sha <pr-head-sha> --tested-revision-sha <tested-merge-or-checkout-sha>
```

Never collapse source head and tested revision into one ambiguous SHA.

### 2. Read obligations, not only surfaces

For every non-terminal obligation inspect:

- `target.path`
- legacy `owner` routing fields where present
- `ownership.obligation_owner`
- `ownership.semantic_owner`
- `ownership.execution_owner`
- `ownership.mutation_guard`
- `trigger.source_changes`
- `revision`
- `qualification`
- `assessment`
- `required_action`
- `evidence`
- `lifecycle`
- `validation.required`

Do not invent a target to make the receipt green. `c-bind-before-write` remains the bind-before-write rule.

### 3. Qualify semantic obligations upstream

If an obligation is `AWAITING_QUALIFICATION`, run `l9-intelligence-harvest` against the bounded request emitted under `semantic_harvest.request`. Supply its canonical `harvest.json` on rerun:

```bash
python skills/l9-update-agent-docs/scripts/repo_docs.py ... --harvest <path/to/harvest.json>
```

A changed `harvest.json` or `*.harvest.json` may be auto-discovered only when its `source_identity.repo_docs` binding matches the repository, required surfaces, and semantic-source digest. Stale or ambiguous Harvest evidence does not close an obligation.

Only qualified nuggets with resolvable `CONFIRMED` evidence may satisfy semantic qualification. Accepted dispositions come from the topology. `MERGE_WITH_EXISTING` with stronger beneficiary semantics produces `PRESERVE`, not overwrite.

### 4. Assess supported operational surfaces

Operational assessment runs after obligation compilation and semantic qualification, before closure validation.

For each configured operational surface:

1. resolve the exact target;
2. resolve the declared analyzer from the closed registry;
3. resolve the mutation guard from its canonical owner;
4. run deterministic assessment;
5. attach normalized findings and evidence to the existing obligation;
6. produce `IMPROVE`, `PRESERVE`, `HANDOFF`, `UNKNOWN`, or `NOT_APPLICABLE`;
7. never mutate solely because the target was touched.

If the analyzer cannot be resolved, the obligation is `BLOCKED`. Do not guess a fallback. A repository that does not declare `ops/config/root-file-protection.json` does not block assessment. If that guard is declared but cannot be resolved, block only when a mutation would otherwise be proposed.

### 5. Execute through the named owner

| Obligation owner/mode | Allowed action |
|---|---|
| `l9-update-agent-docs` / owner-native root index | Surgical pointer/index refresh permitted by topology. |
| operational contract / `repository-native` execution owner | Apply only the bounded repair justified by assessment, subject to the resolved mutation guard and repository-native validation. |
| `readme-pipeline-v1` / generator | Run `scripts/generate_subsystem_readmes.py` for the resolved subsystem. Do not hand-write a generated module README. |
| specialist/external owner | Handoff or use that owner's canonical capability. Do not absorb its implementation here. |
| `llms.txt` projection | Generate only when enabled and a canonical base URL exists. It is projection, never authority. |

Module README config SSOT: `config/subsystems/readme_config.yaml`. Sequencer: `workflows/dags/readme_pipeline_dag.py` (`readme-pipeline-v1`). Polyglot parsing remains at the generator owner.

For `Makefile` and `pyproject.toml`, always resolve `ops/config/root-file-protection.json` before treating a proposed mutation as admissible. A guard justification mechanism authorizes the guard only; it does not transfer semantic ownership to Repo Docs.

### 6. Root-document write rules

- `CLAUDE.md`: load pointer only. Create only when topology permits `create_if_absent`. No doctrine, CI table, or registry dump.
- `AGENTS.md`: surgical additive operating-instruction update only. Never fold to a pointer.
- root `README.md`: pointer/index correction only. Never generate from the module README generator.
- `ARCHITECTURE.md`: surgical architecture-index refresh only when present; never create when topology says `never`.
- `INVARIANTS.md`: invariant/enforcement index. Create only when topology permits. Point to enforcing sources; do not copy organization-law bodies.
- `CANONICAL_LAW.md`: never mutate through this skill.

Required pointer headings remain governed by `references/pointer-heading-map.yaml` and `c-required-section-validation`.

If ownership or source-of-truth is in doubt, read `kernels/Recursive Alignment.md`. If a confirmed defect needs repair, read `kernels/Validate & Repair.md`. Cite those kernels by path; do not wrap or compress them into this skill.

### 7. Validate owner action and close obligations

Rerun the compiler against the same change base. A touched file alone is not terminal proof.

Lifecycle:

```text
DETECTED -> AWAITING_QUALIFICATION -> OPEN -> SATISFIED -> VALIDATED -> CLOSED
```

Side states: `HANDOFF_REQUIRED`, `PRESERVED`, `BLOCKED`, `NOT_APPLICABLE`.

Terminal states are `CLOSED`, `PRESERVED`, and `NOT_APPLICABLE`. `SATISFIED` is not terminal until required validation passes.

For operational surfaces, `PRESERVED` means assessment ran and found no material improvement. If an assessment reports findings, the target must be reassessed after repair; target freshness alone cannot close `material_improvement`.

Final receipt semantics:

- `PASS`: every applicable obligation is terminal and no structural failure exists.
- `PARTIAL`: one or more applicable obligations remain non-terminal.
- `BLOCKED`: an obligation or structural prerequisite cannot be proven/executed safely.
- `FAIL`: contract, schema, managed-region, or other structural correctness validation failed.

## Honest validation vocabulary

Record only checks that actually ran: **Passed**, **Failed**, **Skipped**, **Unknown**, or **NotApplicable**. Local execution is not remote CI. A workflow conclusion does not replace the uploaded receipt.

Do not claim PASS from a touched file, a grep, an accepted submission, a stale Harvest artifact, or an analyzer's own assertion that its mutation succeeded.

## Extension rule

A future operational surface should normally require only:

1. one topology declaration;
2. one analyzer implementation;
3. one static registry entry;
4. focused regression tests.

If adding a new surface requires rewriting `repo_docs.py`, the obligation lifecycle, Harvest architecture, or receipt semantics, stop and reassess the seam before expanding it.

Do not introduce a generic plugin system merely to avoid adding a static registry line.

## Forbidden

- A second documentation SSOT outside `references/doc-surface-policy.yaml`
- A second durable obligation type beside `DocumentationObligation`
- A second findings ledger for operational assessments
- Copying the Harvest brain into this skill
- Copying `root-file-protection.json` rules into Repo Docs policy as independent truth
- Making Repo Docs the semantic owner of Make, Python packaging, CI, dependency policy, or root-file protection
- Dynamic analyzer/plugin discovery
- Authoring ADRs or API contracts here
- Adding general language parsers here
- Hand-editing generated module README content instead of using its owner
- Treating `llms.txt` as doctrine
- Creating root files not permitted by topology
- Changing generated formatter ownership blocks by hand
- Inventing a new CI workflow for this capability when an existing CI owner can consume the receipt

## Stop condition

Stop only when the evaluated receipt is PASS, or when the remaining non-terminal obligation is explicitly BLOCKED with evidence and the correct owner/handoff named. The compiler must be able to explain exactly what remains, why it exists, who owns its semantics, who may execute the repair, which mutation guard applies, and what evidence closes it.
