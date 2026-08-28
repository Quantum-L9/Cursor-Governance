<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: metadata-contract
version: 3.7.0
status: active
-->

# Metadata Standard

## SKILL.md frontmatter

Use one YAML frontmatter block. Portable top-level keys are:

```yaml
---
name: skill-name
description: what the skill does and explicit use-when triggers
license: Proprietary
metadata:
  version: "1.0.0"
  owner: owner-name
  status: active
  tier: strong
---
```

Rules:
- `name` is lowercase hyphen-case and at most 64 characters. Do not fail solely because a temporary source/extraction directory has a different local name.
- `description` states capability, trigger conditions, and user vocabulary; keep it below 1024 characters.
- Put audit, ownership, version, layer, role, tags, and target-platform fields under `metadata`.
- Add `allowed-tools` only when the target platform explicitly supports and needs it.
- Do not add platform-specific top-level fields to the canonical core.
- Do not duplicate metadata in a second block.

## Other files

Markdown references and adapters use a compact `L9_META` HTML comment. Scripts use module docstrings or language-native comments. Schemas use YAML comments. Assets require a sidecar only when provenance or licensing is material.

## Validation

Fail metadata validation for unsupported top-level keys, invalid YAML, missing purpose, secrets, or claims that cannot be traced to evidence. Enforce a name-directory match only when the active target platform explicitly requires one.
