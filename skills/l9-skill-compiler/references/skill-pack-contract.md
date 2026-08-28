<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: pack-contract
version: 3.7.0
status: active
-->

# Skill Pack Contract

## Purpose

Authoritative standalone protocol for creating, analyzing, rebuilding, validating, adapting, and packaging one reusable skill.

## Required shape

```text
skill-name/
  SKILL.md
  references/   optional, for progressive disclosure
  scripts/      optional, for deterministic repeatable work
  schemas/      optional, for machine-checkable contracts
  adapters/     optional, for platform or domain differences
  assets/       optional, for output materials only
  tests/        optional source-only regression tests; excluded from runtime ZIP by default
```

Do not create a folder because it looks complete. Every file must change activation, decision quality, execution reliability, validation, portability, or reuse.

## Source intake

Inspect all supplied material before design. Extract objective, inputs, outputs, triggers, reject signals, workflow, authority, constraints, resources, risks, and unknowns. When an uploaded archive contains multiple skills, split the work into one skill per output archive instead of blending unrelated entrypoints.

## Exemplary pipeline

```text
parse_source
-> extract_expertise
-> compress_expertise
-> design_skill
-> build_complete_files
-> validate_with_evidence
-> package
```

Exemplary work requires `expertise_model.yaml` and `skill_intelligence_report.yaml`. A summary is not an expertise model.

## Design rules

- Keep `SKILL.md` below 500 lines when practical.
- Put large or conditional doctrine one link away in `references/`.
- Use scripts only when deterministic execution improves correctness or repeatability.
- Use adapters only when the target context changes tools, authority, gates, output shape, or installation.
- Preserve source intent while deleting duplicate prose and stale assumptions.
- Lock the file tree before building multi-file packs.

## Build rules

- Create complete files, not patches, when a full pack is requested.
- Zero stubs, TODOs, fake examples, invented connectors, or untested pass claims.
- Never let an adapter become the authority for the core doctrine.
- Do not make repo wiring mandatory unless a repository is actually in scope.
- Do not include `agents/openai.yaml` unless ChatGPT packaging is explicitly requested.

## Validation rules

Run the six classes in `kernel-validation-evidence.md`: structural, contract, execution, evidence, operator, and regression. Missing or blocked checks remain visible. An emitted report is not proof that a check passed.

## Packaging rules

- Produce one runtime ZIP named exactly `skill.zip`.
- `SKILL.md` MUST be at archive root and MUST be the only `SKILL.md` entrypoint in the ZIP.
- Do not wrap the runtime contents in the source skill directory.
- Exclude `tests/`, cache/junk files, and unreferenced `scripts/validate_*.py` development validators by default.
- Preserve validators that the runtime control plane explicitly references.
- Validate the staged runtime file set, not development-only source files that will not ship.
- Inspect the archive manifest after creation and fail if a wrapper directory or test leakage is detected.
- Keep below the target platform's upload limit when one is known; otherwise report size without inventing a limit.

## Tier decisions

- `exemplary`: every required intelligence and validation gate passes.
- `strong`: complete and useful, but one or more exemplary gates are unmeasured or absent.
- `developing`: material gaps remain but the pack is usable for iteration.
- `failed`: the pack cannot safely perform its job.
- `mine_for_components_only`: valuable pieces exist inside a release-blocked pack.
