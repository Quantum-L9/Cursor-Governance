<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: operator
role: overview
version: 3.7.0
status: active
-->

# L9 Skill Compiler v3.7.0

A converged compiler for turning prompts, SOPs, workflows, kernels, and older skills into standalone exemplary skill packs.

## What changed

v3.7 keeps the v3.6 intelligence and validation model but corrects runtime packaging based on observed cross-agent behavior: `SKILL.md` is now placed at ZIP root, the archive is named exactly `skill.zip`, and development-only tests or unreferenced validators stay in the source tree instead of leaking into the runtime distribution.

## Install

Install the `l9-skill-compiler/` directory in the skill location configured by the target agent. Use `adapters/claude-code.md`, `adapters/manus.md`, or `adapters/cursor.md` for platform-specific routing. Do not invent a path when the target environment does not expose one.

## Validate

```bash
python scripts/validate_skill_pack.py .
python scripts/validate_exemplary_skill.py .
python -m unittest tests/test_validators.py  # source checkout only
```

## Package

```bash
python scripts/package_skill.py . /path/to/output
```

The distributable archive is always `skill.zip`. Its first member is root-level `SKILL.md`; there is no `l9-skill-compiler/` wrapper inside the ZIP. Source regression tests are excluded by default.
