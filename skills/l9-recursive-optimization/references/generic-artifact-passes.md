<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: generic_passes
tags: [recursive, coverage, provenance, compression, domain-agnostic]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-07
/L9_META -->

# Generic Artifact Passes

## Purpose

Domain-agnostic alignment passes for artifact groups that are not L9 node/service packs (skill packs, prompts, plans, PlasticOS modules, docs). Run after context lock, before or alongside L9-specific passes when applicable.

## Passes

| # | Pass | Verify |
|---|------|--------|
| G1 | Coverage | All requested files, sections, and outputs exist |
| G2 | Contract | User intent, scope, interfaces, paths, and constraints preserved |
| G3 | Contradiction | Conflicts resolved by authority order or labeled `Unknown` |
| G4 | No-stub | No placeholders, TODO-as-deliverable, empty shells, fake validation |
| G5 | Provenance | Every output maps to source or user instruction |
| G6 | Validation | Files exist, non-empty, match manifest/filetree when pack-based |
| G7 | Compression | Repeated instructions eliminated unless needed for enforcement |
| G8 | Usability | Result installable or usable without reinterpretation |

## Skill Pack Overlay

When artifact type is a skill pack, also verify against `l9-skill-compiler` skill-pack-contract:

- `SKILL.md` frontmatter complete; `name` matches directory
- Every reference linked from `SKILL.md`
- No `agents/openai.yaml`
- No raw source dumps in control plane
- Repo wiring present when project-scoped

## When to Skip

L9 transport/Gate passes (alignment-protocol passes 2–4) remain N/A. Generic passes G1–G8 always apply.
