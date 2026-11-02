<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: operator
role: overview
version: 3.9.0
status: active
-->

# L9 Skill Compiler v3.9.0

A compiler for turning prompts, SOPs, workflows, kernels, and older skills into standalone skill packs, classified honestly as `exemplary`, `strong`, `developing`, `failed`, or `mine_for_components_only`.

## What changed

v3.9 removes the v2 runtime references that 3.8 left behind (five deleted policy files and the Skill IR, family and capability-closure rules), wires the topology scan into the workflow, makes the pack validator fail on a `SKILL.md` that lists a file the pack does not ship, and rebuilds the release documents from real runs. See `CHANGELOG.md`.

## Install

Install the `l9-skill-compiler/` directory in the skill location configured by the target agent. Use `adapters/claude-code.md`, `adapters/manus.md`, or `adapters/cursor.md` for platform-specific routing. Do not invent a path when the target environment does not expose one.

## Validate

From the pack root:

```bash
python scripts/validate_skill_pack.py .
python scripts/validate_exemplary_skill.py .
python scripts/validate_smart_exemplary_spec.py references/canonical-smart-exemplary-spec.yaml
python -m pytest tests -q   # source checkout only; tests are not in the runtime ZIP
```

## Package

```bash
python scripts/package_skill.py . <output_directory>
```

Writes `<output_directory>/skill.zip` with `SKILL.md` as the first root entry and source tests excluded.
