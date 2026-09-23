---
name: l9-update-agent-docs
description: compile repository changes into typed documentation and operational-contract obligations, assess Makefile, Python, workflow, and OpenAPI surfaces, and emit repo-docs receipts. use when refreshing repo or agent docs, checking docs or operational-contract impact after code/CI changes, generating evidence-backed module READMEs, or proving documentation freshness before merge.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, docs, obligations, agents, ci, maintenance]
  owner: igor_beylin
  status: active
  version: 3.8.0
  updated: 2026-09-21
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
  -> filetree.md inventory (required, first)
  -> missing module/submodule README diagnosis from that inventory
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
- filetree generator: `scripts/doc_filetree.py`
- module README generator: `scripts/generate_module_readmes.py`
- operational assessment registry: `scripts/doc_surface_analysis.py`
- compatibility CLI: `scripts/validate_pointer_headings.py`

`l9.repo-docs.receipt.v3` derives PASS/PARTIAL/BLOCKED from obligation terminality plus structural validation failures. Aggregate impact/capability/Harvest fields are diagnostics and provenance, not competing obligation truth.

## Ownership boundaries

- `l9-update-agent-docs` owns documentation topology, impact qualification, target resolution, obligation compilation, deterministic materiality assessment for explicitly registered operational surfaces, freshness semantics, admission of semantic evidence, required `filetree.md`, default-enabled `llm.txt`, and the repo-docs receipt.
- `DocumentationObligation` remains the only durable work unit. `assessment` is evidence attached to an obligation, never a second findings ledger or second obligation system.
- operational-surface ownership is split explicitly:
  - `obligation_owner` owns compilation and lifecycle accounting;
  - `semantic_owner` owns the meaning of the underlying operational contract;
  - `execution_owner` owns the bounded repair path;
  - `mutation_guard` owns mutation admissibility.
- `l9-update-agent-docs` must not absorb Make/Python semantic ownership merely because it detects a material defect.
- `ops/config/root-file-protection.json` remains the canonical mutation-protection contract. Repo Docs reads and resolves its rule at runtime; it must not copy `additive_only` or other guard semantics into a second authority.
- `l9-intelligence-harvest` owns semantic discovery and qualification. The compiler consumes canonical `harvest.json`; it never copies Harvest reasoning or mutates the donor through Harvest.
- `l9-update-agent-docs` owns the root `filetree.md` inventory (`scripts/doc_filetree.py`) and README compilation (`scripts/generate_module_readmes.py` over `readme_model.py`, `source_facts.py`, `readme_evidence.py`, `readme_renderers.py`, `readme_quality.py`). `filetree.md` is generated or refreshed first and is the sole automatic README membership authority. It does not call an LLM, execute source, or import the donor repo. `readme-pipeline-v1` remains an optional sequencer that calls the repo re-export.
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
- `workflow-contract-v1` -> `scripts/surface_analyzers/workflow.py`
- `openapi-contract-v1` -> `scripts/surface_analyzers/openapi.py`

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

## Workflow and OpenAPI contracts

`workflow_contract` validates only workflow-internal `needs` references and local `uses: ./…` paths. `openapi_contract` validates OpenAPI 3.x structure, slash-prefixed path keys, and responses for declared operations. Both analyzers emit `HANDOFF` findings: workflow and API owners retain semantic and repair authority. They never write a workflow or an API contract, and no mutation guard is resolved because this skill is assessment-only on those surfaces.

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

### 2. Generate or refresh `filetree.md` first, then compile READMEs

`filetree.md` is a required root output of this skill. The compiler writes or updates it from the live tree in code before it diagnoses missing files. Do not walk the tree as a second source of truth after `filetree.md` has been written.

README generation is deterministic repository-documentation **compilation**, not AST-to-Markdown projection. Five stages, in order:

1. **QUALIFY.** `filetree.md` is the sole automatic membership authority. Configuration may suppress a target (`skip: true`) and decorate the rest; it can never invent one. A configured path the inventory does not authorize is reported as stale, not honoured. Exclusion is decided on whole path segments before any classification, and covers the whole subtree.
2. **MODEL.** Compile deterministic repository evidence into a typed README model. `source_evidence` in `references/doc-surface-policy.yaml` is the single registry for admitted source files, static extractors, inventory classification, and implementation-change impact. The closed extractors cover Python, shell, JavaScript/TypeScript, Terraform, XML, and Dockerfiles; they never execute source. Parse failures stay as named evidence and produce a `partial` coverage status. Purpose precedence is: configured purpose, the target's own authoritative contract (`SKILL.md` frontmatter `description`, then its `## Purpose`), package `__init__.py` docstring, target-local manifest description, then — only for a genuine single-module target — that module's docstring. A directory holding several modules never borrows one child's docstring. Where no source supports a statement, the statement is absent.
3. **RENDER.** Select a closed-world renderer from the target kind: `skill`, `module`, `subsystem`, `corpus`, `index`. Render only sections with positive content. Standard-library imports are not rendered. Module identity is preserved; relationships are typed and source-backed. Short summaries link to a complete interface or file index rather than silently dropping the tail. Source coverage reports extracted versus eligible files, symbols, relationships, and any extraction issue.
4. **VALIDATE.** Check target authority, path identity, ownership marker, evidence provenance, duplicate heading anchors, root-escaping references, local file links, local anchors, and semantic quality. An ERROR is a compiler defect and fails the run.
5. **RECONCILE.** Compare the authorized desired corpus with the generator-owned corpus on disk. Create, refresh, leave unchanged, preserve, retire or report a conflict. Only generator-owned artifacts are created, refreshed or retired.

When uncertain whether a directory deserves generated documentation, do not generate it. An empty directory earns no README.

A generated README is a projection. It never outranks `SKILL.md`, repository-native configuration, or any other canonical owner.

### 3. Read obligations, not only surfaces

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

### 4. Qualify semantic obligations upstream

If an obligation is `AWAITING_QUALIFICATION`, run `l9-intelligence-harvest` against the bounded request emitted under `semantic_harvest.request`. Supply its canonical `harvest.json` on rerun:

```bash
python skills/l9-update-agent-docs/scripts/repo_docs.py ... --harvest <path/to/harvest.json>
```

A changed `harvest.json` or `*.harvest.json` may be auto-discovered only when its `source_identity.repo_docs` binding matches the repository, required surfaces, and semantic-source digest. Stale or ambiguous Harvest evidence does not close an obligation.

Only qualified nuggets with resolvable `CONFIRMED` evidence may satisfy semantic qualification. Accepted dispositions come from the topology. `MERGE_WITH_EXISTING` with stronger beneficiary semantics produces `PRESERVE`, not overwrite.

### 5. Assess supported operational surfaces

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

### 6. Execute through the named owner

| Obligation owner/mode | Allowed action |
|---|---|
| `l9-update-agent-docs` / owner-native root index | Surgical pointer/index refresh permitted by topology. |
| operational contract / `repository-native` execution owner | Apply only the bounded repair justified by assessment, subject to the resolved mutation guard and repository-native validation. |
| `l9-update-agent-docs` / `filetree.md` | Required. Create if absent. Refresh only when the live file already carries `<!-- l9-filetree: generated-from-tree -->`. An unowned `filetree.md` is preserved; diagnosis still walks the live tree. |
| `l9-update-agent-docs` / module READMEs | After `filetree.md`, reconcile the whole authorized corpus via `scripts/generate_module_readmes.py` (qualify → model → render → validate → reconcile). Kinds are renderer identities: a directory with its own `SKILL.md` is `skill`; one with two or more direct source files is `subsystem`; one with fewer is `module`; a document/config folder with files is `corpus`; a parent of two or more qualifying children is `index`. Index qualification runs deepest-first so nested parents reach the fixed point. Recognition is structural and repo-agnostic; never add a path allowlist. Excluded at any depth, whole subtree: `fixtures` / `generated` / `handoff` / `deliverables` / `receipts` / `drafts` / `assets` / `tests` / `_archived`, plus skill-pack sidecars (`SKILL.md` ancestor except `scripts/`) and the skip prefixes. Matching is on whole path segments — `generated-data` is a real directory. Empty directories earn nothing. Do not limit the reconciliation to the current change set; the optional `changed=` filter is manual CLI scope only and suppresses retirement, because a partial view cannot judge staleness. Ownership marker: `<!-- l9-readme: generated-by=l9-update-agent-docs version=3 kind=… -->`, with older markers still recognized so an older corpus migrates. A generator-owned README at a no-longer-authorized target is retired. `auto_generated: false` front matter outranks any marker; that and any unmarked shape is handwritten and is never overwritten without `--force`. A marker recording a format version this compiler does not understand is a conflict, never a rewrite. The receipt carries the evidence-coverage profile for every reconciled README. Optional sequencer: `readme-pipeline-v1`. |
| specialist/external owner | Handoff or use that owner's canonical capability. Do not absorb its implementation here. |
| `llm.txt` projection | Default enabled. Create if absent. Refresh only when the live file already carries `<!-- l9-llm-txt: generated-projection -->`. If `llm.txt` is missing and `llms.txt` exists, rename (preserve bytes). If both exist, delete leftover `llms.txt`. Never overwrite an unowned `llm.txt`. `--write-llm` does not authorize that overwrite. Projection, never authority. |

`filetree.md` is required and skill-owned, and is the sole automatic README membership authority. README compilation reads that inventory and is executable without a consumer-root generator, YAML map, or donor repo. Optional overlay: `config/subsystems/readme_config.yaml` — it may supply `title`, `tier`, `description`, `purpose` and `skip` for a target the inventory already authorizes, and cannot create one. Optional sequencer: `workflows/dags/readme_pipeline_dag.py` (`readme-pipeline-v1`). A source parse failure stays `partial` with a named extraction issue; do not hide it or replace it with invented prose.

For `Makefile` and `pyproject.toml`, always resolve `ops/config/root-file-protection.json` before treating a proposed mutation as admissible. A guard justification mechanism authorizes the guard only; it does not transfer semantic ownership to Repo Docs.

### 7. Root-document write rules

- `CLAUDE.md`: load pointer only. Create only when topology permits `create_if_absent`. No doctrine, CI table, or registry dump.
- `AGENTS.md`: surgical additive operating-instruction update only. Never fold to a pointer.
- root `README.md`: pointer/index correction only. Never generate from the module README generator.
- Root Python fences: syntax-check only `python` fences in files named by `references/pointer-heading-map.yaml`, using `scripts/doc_policy.py::python_fence_validate_root`. Parse without executing snippets; do not scan arbitrary Markdown or duplicate the repository security scanner.
- `ARCHITECTURE.md`: surgical architecture-index refresh only when present; never create when topology says `never`.
- `INVARIANTS.md`: invariant/enforcement index. Create only when topology permits. Point to enforcing sources; do not copy organization-law bodies.
- `filetree.md`: required inventory. Create if absent; refresh only a marker-owned generated file. Projection, never authority.
- `llm.txt`: default-enabled LLM discovery index. Create if absent; refresh only a marker-owned generated file. Retire leftover `llms.txt` once `llm.txt` exists (rename first when the canonical name is still missing). Do not treat as doctrine.
- Owned-write rule for every skill-handled file: missing → create when policy allows; generator marker present and stale → refresh; any other existing file → preserve. Do not infer overwrite from staleness, validation noise, or `--write-llm`.
- Each admission is receipt evidence, not silence: `create` / `refresh` satisfy the obligation through the run mutation; `unchanged` (render byte-identical to the target) closes it with `target_freshness: PASS`; `preserve` (unowned target left in place) is the terminal `PRESERVED` lifecycle with the admission recorded as evidence. A `skipped` admission (no-write mode, or a blocked write) keeps the obligation open. A filesystem error during retirement or an owned write is a `BLOCKED` receipt state and structural failure, never a crash.
- `CANONICAL_LAW.md`: never mutate through this skill.

Required pointer headings remain governed by `references/pointer-heading-map.yaml` and `c-required-section-validation`.

If ownership or source-of-truth is in doubt, read `kernels/Recursive Alignment.md`. If a confirmed defect needs repair, read `kernels/Validate & Repair.md`. Cite those kernels by path; do not wrap or compress them into this skill.

### 8. Validate owner action and close obligations

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
- Executing code from fenced Markdown or expanding root Python-fence validation beyond the declared pointer-document topology
- Authoring ADRs or API contracts here
- Adding LLM-authored or donor-repo README generation
- Overwriting a handwritten module README, an unowned skill-handled file, or the repository-root README.md
- Leaving `llms.txt` in place after `llm.txt` exists
- Skipping source files because an ancestor directory is named `.l9` (skip only paths relative to the scanned module or repo root)
- Hand-editing generated module README content instead of using its owner. A wrong generated README is a compiler defect: repair the compiler or its evidence and regenerate.
- Treating `filetree.md` or `llm.txt` as doctrine
- Diagnosing missing module READMEs without a current `filetree.md` inventory
- Letting configuration, a renderer, an AST extractor or a CLI helper create a README target the inventory does not authorize
- Emitting a purpose, responsibility or boundary no deterministic repository evidence supports, or a section whose only content is that there is none
- Deriving a directory's purpose from one child module when several live there
- Retiring a README that carries no ownership marker, or rewriting one whose marker records a newer format version
- Creating root files not permitted by topology
- Changing generated formatter ownership blocks by hand
- Inventing a new CI workflow for this capability when an existing CI owner can consume the receipt

## Stop condition

Stop only when the evaluated receipt is PASS, or when the remaining non-terminal obligation is explicitly BLOCKED with evidence and the correct owner/handoff named. The compiler must be able to explain exactly what remains, why it exists, who owns its semantics, who may execute the repair, which mutation guard applies, and what evidence closes it.
