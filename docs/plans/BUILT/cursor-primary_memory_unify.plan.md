---
name: Legacy memory doctrine and side-door removal
status: built
built: true
overview: Reconcile Cursor-Governance with ADR-0006 by removing active Dropbox fallback doctrine and all live L9_MEMORY_HTTP_* / retired shared-memory side-door teaching from executable adapters, skills, commands, validators, and generated agent rules, while preserving historical evidence. Do not create a new memory subsystem, do not change Graphiti transport topology, and do not modify the accepted SessionStart/write-gate behavioral contracts.
todos:
  - id: built-marker
    content: Marked built after execution; session-start audit should skip
    status: completed
isProject: false
---
Strengthen rules identity registry and reference control plane
