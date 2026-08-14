---
description: Non-negotiable anti-patterns agents must not introduce
---

# Anti-patterns (MUST NOT)

## MUST NOT

- Weaken tests, types, schemas, linters, or security checks to force a pass
- Add stubs, placeholders, fake implementations, or TODO-as-done
- Hardcode secrets, machine paths, or environment-specific hosts in shared rules/code
- Duplicate governance SSOT outside `~/.cursor-governance`
- Invent a second episodic memory SSOT beside Graphiti
- Force-push / hard-reset main without explicit authorization
- Suppress valid diagnostics without authoritative justification

## Corpus

Examples and extended catalog: `learning/patterns/anti-patterns.md`

<!-- generated-from: rules/60-anti-patterns.mdc; do-not-edit -->
