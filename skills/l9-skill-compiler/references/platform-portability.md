<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: portability-contract
version: 1.0.0
status: active
-->

# Platform Portability Contract

## Core rule

Build one canonical skill core. Add thin adapters only for platform differences. Never fork the doctrine merely because tool names or install locations differ.

## Canonical core

- `SKILL.md` frontmatter `name` is canonical. A local source/extraction directory may differ; rename only when a target platform explicitly requires a named install directory.
- One `SKILL.md` using portable top-level keys from `meta-standard.md`.
- Relative links only.
- No assumed filesystem path, connector, shell, or tool unless supplied by the target environment.

## Claude Code and Manus

Use the canonical skill folder directly when the platform accepts Agent Skills-style packs. Add platform-specific tool restrictions only when explicitly requested and supported. Installation paths are environment facts; inspect or label `Unknown` rather than guessing.

## Cursor

Prefer the canonical skill folder when the environment supports it. Otherwise create a thin rule or `AGENTS.md` entry that:
- maps activation signals to the canonical `SKILL.md`
- binds available tools
- states output location
- does not duplicate contracts, heuristics, or validation law

## Other agents

An adapter must declare:

```yaml
adapter:
  platform: string
  load_when: []
  installation_target: verified_path_or_Unknown
  tool_bindings: []
  activation_mapping: []
  output_routing: []
  does_not_change:
    - authority_order
    - exemplary_gate
    - source_intent
```

Reject adapters that add only branding or vocabulary.
