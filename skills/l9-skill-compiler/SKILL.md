---
name: l9-skill-compiler
description: compile, rebuild, validate, and package prompts, SOPs, workflows, kernels, and existing agent skills into standalone exemplary skill packs. use when the user asks to create or improve a reusable skill, make a skill portable across Claude Code, Manus, Cursor, or other agents, sharpen activation and reject signals, extract expert heuristics, enforce authority and evidence rules, eliminate drift or stubs, or produce a validated ZIP.
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, compiler, skill, exemplary, portability, packaging]
  owner: igor_beylin
  status: active
  version: "3.8.0"
  updated: "2026-08-28"
  license: Proprietary
  supersedes: l9-skill-compiler v2.0.0 (skill-compiler-v2 DAG runtime)
  targets: [claude-code, manus, cursor, agent-skills]
---

# L9 Skill Compiler

## Purpose

Turn source material or an existing skill into the smallest standalone pack that reliably changes future agent behavior. Exemplary means compressed judgment backed by evidence, not a thicker folder.

## Activation Boundary

Use this skill for creation, conversion, audit, rebuild, hardening, validation, portability, or packaging of reusable agent skills. Do not use it for one-off prompts that the user does not want packaged, ordinary document editing, or installing a multi-skill archive without first splitting it into one skill per pack.

## Authority Order

1. Latest explicit user instruction and supplied source artifacts.
2. `references/skill-pack-contract.md`.
3. `references/meta-standard.md` and `references/platform-portability.md`.
4. Activated runtime directives and specialized contracts.
5. Verified implementation and validation evidence.
6. `Unknown`; inference never outranks evidence.

## Modes

| Mode | Result | Primary references |
|---|---|---|
| discuss | choices and trade-offs | `references/output-modes.md` |
| analyze | evidence-backed gap and divergence report | `references/skill-pack-contract.md` |
| design | bounded file tree and resource map | `references/file-contract.md` |
| build / rebuild | complete skill pack | `references/build_execution_contract.md` |
| exemplary | complete pack plus intelligence evidence | `references/smart-exemplary-skill-contract.md` |
| hardened-rebuild | converged multi-pass replacement | `references/kernel-recursive-improvement.md` |
| package | validated runtime `skill.zip` with root `SKILL.md` | `scripts/package_skill.py` |

## Mandatory Workflow

1. Load `references/binding-runtime-directives.md` and record activated directives.
2. Parse the source and produce Gate A using `schemas/gate-a-source-parse.schema.yaml`.
3. For exemplary work, extract and compress expertise before designing files. Produce `expertise_model.yaml` and Gate B.
4. Select the minimum high-leverage structure. Produce Gate C and lock files in scope.
5. Build complete files only. Produce Gate D with zero stubs, TODOs, placeholders, or unverified pass claims. Write `SKILL.md` frontmatter to the five permitted top-level keys in `references/meta-standard.md` — `name`, `description`, `paths`, `disable-model-invocation`, `metadata` — with everything else nested under `metadata:`. A pack that emits `license` or `allowed-tools` at top level is rejected by the install gate of every governed repository and has to be repaired by hand before it can be wired.
6. Validate structural, contract, execution, evidence, operator, and regression classes. Produce Gate E. `scripts/validate_skill_pack.py <pack>` is a required gate here, not an optional check: it is the executable form of the frontmatter contract and fails the build on a non-native top-level key, a name that does not match the pack directory, a description outside 150-500 characters or with no trigger clause, an empty `paths`, or an archived pack that is not `disable-model-invocation: true`.
7. Create platform adapters only when they change installation, tool binding, activation, or output routing. Produce Gate F when wiring is in scope.
8. Package only after validation passes. Produce Gate G and the actual archive.

```text
parse_source
-> extract_expertise
-> compress_expertise
-> design_skill
-> build_complete_files
-> validate_with_evidence
-> adapt_platforms
-> package
```

## Exemplary Gate

A generated skill may be classified `exemplary` only when all of the following are present and validated:

- strong activation signals and explicit reject signals
- ranked source authority and conflict rules
- conditional expert heuristics in condition -> judgment -> action form
- adapters that change real decision rules, not vocabulary
- named failure modes with prevention controls
- scored leverage points
- an after-use correction hook based only on observed failures
- deterministic validation evidence

Run:

```bash
python scripts/validate_skill_pack.py <skill-folder>
python scripts/validate_exemplary_skill.py <skill-folder>
```

If any required gate is missing, failed, blocked, or `Unknown`, downgrade honestly to `strong`, `developing`, `failed`, or `mine_for_components_only`.

## Packaging Contract

- Produce one runtime archive named exactly `skill.zip`.
- Put `SKILL.md` at the ZIP root; do not wrap the skill contents in a top-level skill directory.
- Treat `SKILL.md` frontmatter `name` as canonical. The source/extraction directory may have any local name; flatten only the distributable archive.
- Exclude source regression tests, cache/junk files, and unreferenced `scripts/validate_*.py` development validators by default.
- Keep a validator in the runtime ZIP only when `SKILL.md`, `references/`, or `adapters/` explicitly names it as a runtime dependency.
- Use `--include-tests` or `--include-unreferenced-validators` only for diagnostic/source archives, not normal runtime delivery.
- Do not claim a ZIP exists until it has been created and inspected.
- Do not include `agents/openai.yaml` unless ChatGPT packaging is explicitly requested.

## Resource Map

### Release and operator evidence
- `README.md`
- `RUNBOOK.md`
- `MANIFEST.md`
- `CHANGELOG.md`
- `VALIDATION.md`

### Core contracts
- `references/skill-pack-contract.md`
- `references/meta-standard.md`
- `references/platform-portability.md`
- `references/file-contract.md`
- `references/output-modes.md`
- `references/build_execution_contract.md`
- `references/enforcement-gates.md`

### Exemplary intelligence
- `expertise_model.yaml`
- `skill_intelligence_report.yaml`
- `references/expertise_extraction_framework.md`
- `references/smart-exemplary-skill-contract.md`
- `references/canonical-smart-exemplary-spec.yaml`

### Runtime directives and kernels
- `references/binding-runtime-directives.md`
- `references/kernel-agent-state.md`
- `references/kernel-first-order-thinking.md`
- `references/kernel-build-quality.md`
- `references/kernel-skill-doctrine.md`
- `references/kernel-compounding-leverage.md`
- `references/kernel-anti-drift.md`
- `references/kernel-execution-cost.md`
- `references/kernel-validation-evidence.md`
- `references/kernel-recursive-improvement.md`
- `references/kernel-convergence-architect.md`
- `references/kernel-reasoning-think-strategy.md`
- `references/kernel-zero-stub-build.md`

### Platform adapters
- `adapters/claude-code.md`
- `adapters/manus.md`
- `adapters/cursor.md`
- `adapters/l9-platform.md`

### Gate schemas
- `schemas/gate-a-source-parse.schema.yaml`
- `schemas/gate-b-expertise-model.schema.yaml`
- `schemas/gate-c-file-tree.schema.yaml`
- `schemas/gate-d-build-manifest.schema.yaml`
- `schemas/gate-e-validation-report.schema.yaml`
- `schemas/gate-f-wiring-report.schema.yaml`
- `schemas/gate-g-package-record.schema.yaml`

### Deterministic tools
- `scripts/validate_skill_pack.py`
- `scripts/validate_exemplary_skill.py`
- `scripts/validate_smart_exemplary_spec.py`
- `scripts/package_skill.py`

## Failure Handling

State the exact blocker, preserve useful components, label unverifiable claims `Unknown`, and provide the smallest safe correction. Never fabricate missing resources, tool support, validation results, or installation paths.
