---
name: l9-update-agent-docs
description: compile repository changes into typed, target-resolved documentation obligations, selectively qualify semantic obligations with l9-intelligence-harvest, route owner-native actions, and emit evidence-backed repo-docs receipts. use when refreshing repo or agent docs, checking documentation impact after code/CI/governance changes, generating module READMEs, or proving documentation freshness before PR/merge.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, docs, obligations, agents, ci, maintenance]
  owner: igor_beylin
  status: active
  version: 3.0.0
  updated: 2026-09-03
  when_to_use: compile documentation obligations after repository changes, refresh governed documentation through its canonical owner, or prove documentation closure with a machine receipt
---

# Repository Documentation Obligation Compiler

## Purpose

Compile repository state plus a repository delta into first-class documentation obligations. Each material obligation names the exact target, source revision, canonical owner, owner-native action, evidence, validation requirements, and lifecycle state. Surfaces are routing topology; `DocumentationObligation` is the durable unit of work.

The compiler is not a doctrine author, general docs writer, parser framework, ADR owner, API contract owner, CI platform, or replacement for specialist documentation generators.

## Canonical contract

```text
repository state + repository delta
  -> documentation topology
  -> deterministic impact qualification
  -> target resolution
  -> DocumentationObligation[]
  -> selective semantic Harvest when required
  -> owner-native action / handoff
  -> validation
  -> repo-docs receipt
```

Machine authority:

- topology: `references/doc-surface-policy.yaml`
- obligation schema: `contracts/documentation-obligation.schema.json`
- receipt schema: `contracts/repo-docs-receipt.schema.json`
- machine compiler: `scripts/repo_docs.py`
- compatibility CLI: `scripts/validate_pointer_headings.py`

`l9.repo-docs.receipt.v3` derives PASS/PARTIAL/BLOCKED from obligation terminality plus structural validation failures. Aggregate impact/capability/Harvest fields are diagnostics and provenance, not competing obligation truth.

## Ownership boundaries

- `l9-update-agent-docs` owns documentation topology, impact qualification, target resolution, obligation compilation, freshness semantics, admission of semantic evidence, optional `llms.txt`, and the repo-docs receipt.
- `l9-intelligence-harvest` owns semantic discovery and qualification. The compiler consumes canonical `harvest.json`; it never copies Harvest reasoning or mutates the donor through Harvest.
- `readme-pipeline-v1` and `scripts/generate_subsystem_readmes.py` own module README rendering and language extraction.
- `l9-architecture-decision-records` owns ADR authoring.
- repository/API owners own API reference generation.
- organization/community-health owners remain external.
- `CANONICAL_LAW.md` remains external authority.
- `AGENTS.md` remains the operating-instruction SSOT.
- `l9-wire-into-repo` owns wiring, rewiring, registration, and reachability.

Invariant: **Harvest discovers and qualifies semantic truth. Repo Docs compiles documentation obligations. Specialist owners render their surfaces. Receipts prove closure.**

## Evidence and authority order

1. `CANONICAL_LAW.md`
2. `ops/autonomy/surface_profile.yaml`
3. `AGENTS.md`
4. `references/doc-surface-policy.yaml` for this skill's documentation topology
5. owner-native source/configuration named by the topology
6. admitted `harvest.json` for semantic qualification only
7. Unknown

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
- `owner.id` and `owner.execution_mode`
- `trigger.source_changes`
- `revision`
- `qualification`
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

### 4. Execute through the named owner

| Obligation owner/mode | Allowed action |
|---|---|
| `l9-update-agent-docs` / owner-native root index | Surgical pointer/index refresh permitted by topology. |
| `readme-pipeline-v1` / generator | Run `scripts/generate_subsystem_readmes.py` for the resolved subsystem. Do not hand-write a generated module README. |
| specialist/external owner | Handoff or use that owner's canonical capability. Do not absorb its implementation here. |
| `llms.txt` projection | Generate only when enabled and a canonical base URL exists. It is projection, never authority. |

Module README config SSOT: `config/subsystems/readme_config.yaml`. Sequencer: `workflows/dags/readme_pipeline_dag.py` (`readme-pipeline-v1`). Polyglot parsing remains at the generator owner.

### 5. Root-document write rules

- `CLAUDE.md`: load pointer only. Create only when topology permits `create_if_absent`. No doctrine, CI table, or registry dump.
- `AGENTS.md`: surgical additive operating-instruction update only. Never fold to a pointer.
- root `README.md`: pointer/index correction only. Never generate from the module README generator.
- `ARCHITECTURE.md`: surgical architecture-index refresh only when present; never create when topology says `never`.
- `INVARIANTS.md`: invariant/enforcement index. Create only when topology permits. Point to enforcing sources; do not copy organization-law bodies.
- `CANONICAL_LAW.md`: never mutate through this skill.

Required pointer headings remain governed by `references/pointer-heading-map.yaml` and `c-required-section-validation`.

If ownership or source-of-truth is in doubt, read `kernels/Recursive Alignment.md`. If a confirmed defect needs repair, read `kernels/Validate & Repair.md`. Cite those kernels by path; do not wrap or compress them into this skill.

### 6. Validate owner action and close obligations

Rerun the compiler against the same change base. A touched file alone is not terminal proof.

Lifecycle:

```text
DETECTED -> AWAITING_QUALIFICATION -> OPEN -> SATISFIED -> VALIDATED -> CLOSED
```

Side states: `HANDOFF_REQUIRED`, `PRESERVED`, `BLOCKED`, `NOT_APPLICABLE`.

Terminal states are `CLOSED`, `PRESERVED`, and `NOT_APPLICABLE`. `SATISFIED` is not terminal until required validation passes.

Final receipt semantics:

- `PASS`: every applicable obligation is terminal and no structural failure exists.
- `PARTIAL`: one or more applicable obligations remain non-terminal.
- `BLOCKED`: an obligation or structural prerequisite cannot be proven/executed safely.
- `FAIL`: contract, schema, managed-region, or other structural correctness validation failed.

## Honest validation vocabulary

Record only checks that actually ran: **Passed**, **Failed**, **Skipped**, **Unknown**, or **NotApplicable**. Local execution is not remote CI. A workflow conclusion does not replace the uploaded receipt.

Do not claim PASS from a touched file, a grep, an accepted submission, or a stale Harvest artifact.

## Forbidden

- A second documentation SSOT outside `references/doc-surface-policy.yaml`
- A second durable obligation type beside `DocumentationObligation`
- Copying the Harvest brain into this skill
- Authoring ADRs or API contracts here
- Adding language parsers here
- Hand-editing generated module README content instead of using its owner
- Treating `llms.txt` as doctrine
- Creating root files not permitted by topology
- Changing generated formatter ownership blocks by hand
- Inventing a new CI workflow for this capability when an existing CI owner can consume the receipt

## Stop condition

Stop only when the evaluated receipt is PASS, or when the remaining non-terminal obligation is explicitly BLOCKED with evidence and the correct owner/handoff named. The compiler must be able to explain exactly what remains, why it exists, who owns it, and what evidence closes it.
