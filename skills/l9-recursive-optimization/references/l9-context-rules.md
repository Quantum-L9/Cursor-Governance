<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: l9_context
tags: [l9, transportpacket, gate, boundaries, meta]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
/L9_META -->

# L9 Context Rules

## Purpose

Shared non-negotiables applied during alignment and improvement when the artifact group touches L9 nodes, Gate, transport, or service packs.

## Apply When Relevant

Skip entire section when artifact is non-L9 (e.g. PlasticOS Odoo-only module with no Gate integration).

## Non-Negotiables

| Rule | Enforcement |
|------|-------------|
| TransportPacket-only wire format | PacketEnvelope MUST be rejected |
| Gate-only egress | No direct node-to-node calls |
| No runtime node workflow ownership | Orchestrator owns workflow only when declared |
| No Gate workflow state | Gate owns routing/admission/resilience only |
| No chassis/SDK/infra duplication in node logic | No CI, Docker, auth, routing duplication inside engine |
| L9_META on tracked files | Every tracked file carries metadata |
| Zero stub | No TODOs, placeholders, fake tests, pretend implementations |
| Unknown labeled | Never invent missing contract facts |

## PlasticOS Overlay

When optimizing PlasticOS artifacts, also verify against workspace rules:

- `AGENTS.md` CI compliance and module wiring
- `INVARIANTS.md` enforced invariants
- Odoo 19 patterns (no `_sql_constraints`, `<list>` not `<tree>`, etc.)
- `pipeline_v2.py` must remain inactive
- Repo governance paths use `$HOME/Dropbox/...` not machine-specific absolute paths in committed rules

Authority: workspace rules win for Odoo-specific patterns; L9 transport/Gate rules win for node/service artifacts.

## Conflict Resolution

1. Explicit user instruction
2. Higher-layer architecture contract (L9 kernel vs workspace overlay by artifact type)
3. Strongest enforceable formulation that preserves intent
4. `Unknown` if irreconcilable without user input
