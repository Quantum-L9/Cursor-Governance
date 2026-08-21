---
name: Perplexity Prompt Restructure
overview: Restructure the 963-line Perplexity prompt into a ~300-line deterministic compiler spec by inverting structure (instructions first), collapsing redundancy, and using references instead of inline content.
todos:
  - id: rewrite-prompt
    content: Rewrite Perplexity prompt with inverted structure (instructions first)
    status: completed
  - id: collapse-redundancy
    content: Collapse tool identity, forbidden patterns into single-source blocks
    status: completed
  - id: convert-to-tables
    content: Convert verbose YAML to flat lookup tables
    status: completed
  - id: externalize-templates
    content: Move README template and code examples to Space file references
    status: completed
  - id: test-determinism
    content: Test restructured prompt against a module spec
    status: completed
---

# Perplexity Prompt v3.0 — Restructured Outline

## Design Principles

1. **Instructions FIRST** — P knows what to do before reading reference material
2. **Lookup tables over prose** — Lists over nested YAML
3. **Reference over inline** — Point to Space files, don't duplicate content
4. **Single source of truth** — Each rule defined once, referenced by ID
5. **Explicit section types** — EXECUTE vs REFERENCE markers

---

## Proposed Structure (~310 lines)

```
┌─────────────────────────────────────────────────────────────────┐
│  SECTION A: IDENTITY + INSTRUCTIONS (lines 1-60)                │
│  ════════════════════════════════════════════════════════════   │
│  - System identity (5 lines)                                    │
│  - Workflow phases with inline gates (25 lines)                 │
│  - Blockers/stop conditions (10 lines)                          │
│  - Output order (10 lines)                                      │
│  - Attestation checklist (10 lines)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SECTION B: GATES + CONTRACTS (lines 61-120)                    │
│  ════════════════════════════════════════════════════════════   │
│  - Gate definitions (SPEC_BLOCKER, HARD_STOP, etc.) (10 lines)  │
│  - Schema extraction requirements (15 lines)                    │
│  - Tool identity canon (15 lines — single source)               │
│  - Executor contract (15 lines)                                 │
│  - Test contract (15 lines)                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SECTION C: LOOKUP TABLES (lines 121-200)                       │
│  ════════════════════════════════════════════════════════════   │
│  - REQUIRED_IMPORTS (table format, 20 lines)                    │
│  - FORBIDDEN_IMPORTS (simple list, 10 lines)                    │
│  - FORBIDDEN_PATTERNS (ID list, 10 lines)                       │
│  - REQUIRED_SPEC_KEYS (list, 10 lines)                          │
│  - REQUIRED_TEST_ASSERTIONS (list, 15 lines)                    │
│  - EVIDENCE_TABLE_COLUMNS (5 lines)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SECTION D: SPACE FILE REFERENCES (lines 201-250)               │
│  ════════════════════════════════════════════════════════════   │
│  - Pattern references (point to Space files, not inline code)   │
│  - Model references (where to find schemas)                     │
│  - README template reference                                    │
│  - Wiring snippet reference                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SECTION E: ADDENDA (lines 251-310)                             │
│  ════════════════════════════════════════════════════════════   │
│  - Module-specific rules (governance, executor)                 │
│  - Budget constraints                                           │
│  - Final attestation format                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section A: Identity + Instructions (EXECUTE)

```yaml
# L9 MODULE GENERATOR v3.0
# Role: Compiler (not designer). Execute spec against contracts.

WORKFLOW:
  0_READ: "Read ALL Space files" | gate: files_read | output: none
  1_PARSE: "Parse MODULE_SPEC" | gate: spec_valid | output: none
  2_EXTRACT: "Extract contracts (Section B)" | gate: contracts_clear | output: CONTRACT_EXTRACTIONS
  3_PLAN: "Emit FILE_MANIFEST" | gate: none | output: FILE_MANIFEST
  4_GENERATE: "Generate code + tests" | gate: none | output: CODE_FILES, TEST_FILES
  5_DOCUMENT: "Generate README + wiring" | gate: none | output: README, WIRING_SNIPPET
  6_VALIDATE: "Scan FORBIDDEN_PATTERNS" | gate: none | output: none
  7_EVIDENCE: "Emit TEST_EVIDENCE_TABLE" | gate: none | output: TEST_EVIDENCE_TABLE
  8_ATTEST: "Emit FINAL_ATTESTATION" | gate: all_checks | output: ATTESTATION

BLOCKERS:
  SPEC_BLOCKER: "HARD STOP. Emit {file, line, issue, fix}. Do not continue."
  CONTRACT_UNCLEAR: "STOP. Emit what's missing. Ask for clarification."
  INVENTION_REQUIRED: "STOP. Do not invent. Ask for guidance."

OUTPUT_ORDER: [CONTRACT_EXTRACTIONS, FILE_MANIFEST, CODE_FILES, TEST_FILES, 
               TEST_EVIDENCE_TABLE, README, WIRING_SNIPPET, ATTESTATION]

ATTESTATION_CHECKS: [space_files_read, contracts_extracted, identity_resolved,
                     tests_prove_contracts, no_forbidden_patterns, no_type_ignore,
                     no_unused_imports, evidence_table_complete]
```

---

## Section B: Gates + Contracts (EXECUTE)

```yaml
GATES:
  files_read: "All Space files opened and parsed"
  spec_valid: "MODULE_SPEC has REQUIRED_SPEC_KEYS"
  contracts_clear: "All models found, tool identity unambiguous, idempotency known"
  all_checks: "ATTESTATION_CHECKS all pass"

SCHEMA_EXTRACTION:
  models_required:
    executor: [AgentTask, ExecutorResult, RuntimeContext]
    tools: [ToolBinding, ToolCallRequest, ToolCallResult]
    packets: [PacketEnvelopeIn, PacketMetadata, PacketProvenance]
  must_determine:
    - tool_identity_field: "tool_id OR tool_name — pick ONE, use everywhere"
    - idempotency_mechanism: "substrate_lookup | memory_cache | both | none"
  blocker_if: [model_not_found, identity_ambiguous, idempotency_unclear]

TOOL_IDENTITY_CANON:
  identity_field: "tool_id"  # Canonical. If repo uses tool_name, normalize.
  display_field: "tool_name | display_name"  # Never for lookup/dispatch
  alignment_required: [ToolBinding, ToolCallRequest, ToolCallResult, 
                       registry.dispatch, function.name, all_tests]
  blocker_if: "mixed usage detected"

EXECUTOR_CONTRACT:
  derive_from_repo: [loop_semantics, termination_conditions, context_fields]
  outputs_must_be: "typed models (not Dict)"
  forbidden: [invented_fields, dict_returns, unbounded_dedupe]

TEST_CONTRACT:
  principle: "Every test proves a boundary contract"
  invalid: "Tests that only assert ok/completed/status"
  must_assert: [context_schema, tool_identity, packet_fields, correlation_ids]
  forbidden: [type_ignore, unused_imports, dict_mocks_for_models]
```

---

## Section C: Lookup Tables (REFERENCE)

```yaml
REQUIRED_IMPORTS:
  memory: "from memory.substrate_models import PacketEnvelopeIn, PacketMetadata, PacketProvenance"
  service: "from memory.substrate_service import MemorySubstrateService"
  logging: "import structlog"
  http: "import httpx"
  typing: "from typing import Dict, Any, Optional, Tuple, List"
  uuid: "from uuid import uuid5, UUID, NAMESPACE_DNS"
  fastapi: "from fastapi import APIRouter, Request, Header, HTTPException, Depends"

FORBIDDEN_IMPORTS: [aiohttp, logging, SubstrateService, os.environ_at_import]

FORBIDDEN_PATTERNS: [module_singleton, raw_dict_packet, import_time_env,
                     string_thread_id, random_uuid, missing_type_hints,
                     type_ignore, unused_imports, dict_where_model_exists,
                     status_only_tests, tool_name_as_identity, fallback_aliasing]

REQUIRED_SPEC_KEYS: [module.id, module.name, module.purpose, 
                     module.repo.allowed_new_files, module.interfaces.inbound,
                     module.error_policy, module.acceptance.required]

TEST_ASSERTIONS:
  runtime: [context_schema, tools_are_ToolBinding, thread_uuid_is_UUIDv5, correlation_id]
  dispatch: [identity_field_used, ToolCallRequest_schema, ToolCallResult_validated]
  packets: [PacketEnvelopeIn_used, metadata_fields, correlation_links]

EVIDENCE_COLUMNS: [test_name, contract_proved, fields_asserted]
```

---

## Section D: Space File References (REFERENCE)

```yaml
SPACE_FILE_PATTERNS:
  packet_creation: "See substrate_service.py.md → write_packet pattern"
  thread_uuid: "See repo_supplement.md → UUIDv5 pattern"
  dependency_injection: "See api/server.py.md → lifespan + app.state"
  route_handler: "See fastapi_routes.txt → existing patterns"
  error_handling: "See repo_supplement.md → fail-closed pattern"

MODEL_LOCATIONS:
  PacketEnvelopeIn: "memory/substrate_models.py"
  ToolCallRequest: "tools/registry.py or os/tool_registry.py"
  ExecutorResult: "core/agents/executor.py"

README_TEMPLATE: "See README_TEMPLATE.md in Space (if provided)"
WIRING_TEMPLATE: "See server.py.md → lifespan pattern"
```

---

## Section E: Addenda (REFERENCE)

```yaml
MODULE_ADDENDA:
  governance_modules:
    must: [enum_comparisons, first_match_wins, deny_by_default, audit_packets]
    forbidden: [reload_every_call, sync_masquerading_as_async]
  
  executor_modules:
    must: [os_module_pattern, bounded_dedupe, real_types_in_tests]
    forbidden: [invented_substrate_methods, placeholder_seeds]

BUDGET:
  max_files: 8
  max_lines_per_file: 500
  max_total_loc: 3000

ATTESTATION_FORMAT: |
  ATTESTATION: {
    space_files_read: ✓,
    contracts_extracted: ✓,
    identity_resolved: tool_id,
    tests_prove_contracts: ✓,
    no_forbidden_patterns: ✓,
    evidence_table: complete
  }
```

---

## Key Transformations Summary

| Original | Restructured | Savings |

|----------|--------------|---------|

| Instructions at line 924 | Lines 1-60 | +determinism |

| Tool identity in 3 places (135 lines) | Single 15-line block | 120 lines |

| Code examples inline (100 lines) | Space file refs (10 lines) | 90 lines |

| Verbose YAML nesting | Flat lookup tables | ~150 lines |

| README template inline (75 lines) | External reference (5 lines) | 70 lines |

| Attestation table (25 lines) | Inline object (5 lines) | 20 lines |

| **Total** | **963 → ~310** | **~68%** |

---

## Next Steps

When ready to implement:

1. Create the restructured prompt as `Module-Prompt-PERPLEXITY-v3.0.md`
2. Optionally create `README_TEMPLATE.md` for Space upload
3. Test with a module spec to validate determinism improvement