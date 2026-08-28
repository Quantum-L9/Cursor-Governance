<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: metadata-contract
version: 3.8.0
status: active
-->

# Metadata Standard

## SKILL.md frontmatter

Use one YAML frontmatter block. **Exactly five top-level keys are permitted**,
in this order:

```yaml
---
name: l9-skill-name
description: what the skill does. use when <trigger>, <trigger>, or <trigger>. do not use when <near miss>.
paths: "src/**"                 # optional
disable-model-invocation: true  # optional; required for explicit-only and archived packs
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, example]
  owner: owner-name
  status: active
  version: "1.0.0"
  updated: "2026-08-28"
  license: Proprietary
---
```

Anything else — `license`, `allowed-tools`, `skill_schema`, `layer`, `role`,
`tags`, `owner`, `status`, `version`, `updated`, `tier`, `targets` — is **nested
under `metadata:`**, never top level. This is not a style preference: a governed
repository's install gate rejects a non-native top-level key outright, so a pack
that ships one is not merely untidy, it is uninstallable until a human repairs it
by hand.

Rules:
- `name` is lowercase hyphen-case, at most 64 characters, and **must equal the
  pack directory name**. The folder is the identity on every discovery surface;
  a mismatch makes the pack undiscoverable. Judge the final destination folder,
  not a temporary extraction directory.
- `description` states capability, trigger conditions, and user vocabulary in
  **150-500 characters**, and must contain a `use when` or `use for` clause.
  Under the floor the triggers are missing; over the ceiling the body is leaking
  into what is the entire routing signal.
- `paths`, when present, must be non-empty. An empty glob hides the skill; omit
  the key instead.
- An archived or deprecated pack sets `disable-model-invocation: true`. A
  description saying "do not activate" is not a mechanism.
- Do not duplicate metadata in a second block. An `L9_META` HTML comment in
  `SKILL.md` restating the frontmatter is drift with two sources of truth — fold
  it into `metadata:` and delete it.

Publishing outside a governed repository (Anthropic Agent Skills accepts
top-level `license` and `allowed-tools`) is an explicit opt-in:
`validate_skill_pack.py --frontmatter-profile agent-skills`. It is never the
default, so portability cannot silently emit a pack the L9 gate rejects.

## Other files

Markdown references and adapters use a compact `L9_META` HTML comment. Scripts use module docstrings or language-native comments. Schemas use YAML comments. Assets require a sidecar only when provenance or licensing is material.

## Validation

Fail metadata validation for unsupported top-level keys, a name that does not
match the pack directory, a description outside 150-500 characters or without a
trigger clause, an empty `paths`, an archived pack that is not
`disable-model-invocation: true`, invalid YAML, missing purpose, secrets, or
claims that cannot be traced to evidence.

`scripts/validate_skill_pack.py` is the executable form of this section and is a
required gate before packaging. Do not restate this key set anywhere else in the
pack: one contract, one enforcement point.
