---
name: tier2-schema-proposer-tests
overview: Add Tier-2 behavioral tests for `schema_proposer` and a kernel-aligned field-name invariant guard so the only engine path that introduces field names from runtime data fails closed against L9 Master Kernel §3.1, §5.1, §5.2.
todos:
  - id: switch_to_agent
    content: Switch from Plan mode to Agent mode (user approval gate)
    status: completed
  - id: edit_proposer_constants
    content: Add `import re`, `BANNED_FIELD_NAMES_L9_KERNEL` frozenset, `_SNAKE_CASE_RE` pattern, and `_is_canonical_field_name()` helper to `app/engines/convergence/schema_proposer.py`
    status: completed
  - id: edit_proposer_propose_guard
    content: Add the canonical-name guard with structlog.warning to `_build_field_proposals()` after the existing threshold check
    status: completed
  - id: edit_proposer_apply_guards
    content: Add defense-in-depth canonical-name guards with structlog.warning to `_apply_node_properties()`, `_apply_gate_proposals()`, and `_apply_scoring_proposals()`
    status: completed
  - id: create_tier2_test_file
    content: Create `tests/contracts/tier2/test_schema_proposer_behavioral.py` with L9 metadata header and three test classes (TestProposeSchemaForKnownDomain, TestProposeSchemaRespectsCurrentYamlScope, TestProposeSchemaEnforcesKernelFieldNameInvariants), using flat confidence-fixture shape
    status: completed
  - id: run_make_agent_check
    content: Run `make agent-check` and confirm all 7 gates pass; iterate on any violations
    status: completed
  - id: verify_existing_tests_green
    content: Confirm `pytest tests/test_schema_proposer.py` and the rest of `tests/contracts/tier2/` remain green
    status: completed
  - id: open_pr
    content: Open PR `feat/tier2-schema-proposer-behavioral-tests` with kernel-anchored body, non-goals, and follow-up notes (ApprovalDecision duplication, fixture-shape reconciliation, potential INV-SEC PR)
    status: in_progress
isProject: false
---

# Tier-2 Behavioral Tests + Kernel Name-Invariant Guard for `schema_proposer`

## Context

`tests/contracts/tier2/` has 16 behavioral contract tests covering enforcement, packet runtime, provenance, and attestation. `app/engines/convergence/schema_proposer.py` is the only convergence-engine module with no Tier-2 behavioral coverage, and it is the unique engine path where field names enter the system as **runtime data** (LLM-derived) rather than committed source — so static lint/audit cannot catch canonical-name violations there. This plan closes both gaps in one PR, scoped to two files.

Branch: `feat/tier2-schema-proposer-behavioral-tests`
Tier per [AGENTS.md](AGENTS.md): **T2** (tests) + **T3** (engine logic). PR + review required.

## Authority anchors

All decisions cite the L9 Master Kernel ([_L9 Master Kernel.md](_L9%20Master%20Kernel.md)) directly; none of `INV-ARCH-06`, `section_5_2_banned`, or PII-keyword filtering are kernel-sanctioned and they are explicitly out of scope.

- **§1 authority order** — schemas/contracts > agent-invented rules; "stricter rule wins"
- **§2.3 INV-OBS-05** — `print()` banned; structured logging required for any drop event
- **§3.1** — all Python and YAML fields MUST be `snake_case`; no aliases or camelCase
- **§5.1** — TransportPacket-related canonical-name drift list (`packetid`, `packetID`, `traceId`, `threadId`, `parentIds`, `sourceNode`, `onBehalfOf`, `orgId`, …)
- **§5.2** — spec.yaml canonical-name drift list (`matchentities`, `nodelabels`, `matchdirections`, `candidateprop`, `null_semantics`, `computation_type`, `targetnode`, `idproperty`)
- **§7** — generated code requires L9 metadata headers and zero CRITICAL/HIGH scanner violations

[AGENTS.md](AGENTS.md) contracts touched: **C-04** (structlog only), **C-05** (modern type syntax), **C-17** (snake_case).

## Files touched (locked scope — exactly two)

1. [app/engines/convergence/schema_proposer.py](app/engines/convergence/schema_proposer.py) — T3 — add kernel-derived constant + two `if` guards + structlog warning
2. `tests/contracts/tier2/test_schema_proposer_behavioral.py` — T2 — new file, three test classes

Out of scope (not modified, called out in PR body for follow-up):
- `tests/test_schema_proposer.py` — fixture-shape inconsistency (flat vs nested confidences). New file uses the **flat** shape to align with the existing test file; reconciliation is a follow-up.
- Duplicate `ApprovalDecision` (defined both at [app/engines/convergence/schema_proposer.py](app/engines/convergence/schema_proposer.py) line 61 and `app/models/loop_schemas.py`) — flagged in PR body.
- PII / security keyword filtering — **deferred** until a separate governance PR adds an `INV-SEC-*` contract to the kernel.

## Baseline (already verified against live source)

- `MIN_FILL_RATE = 0.60`, `MIN_AVG_CONFIDENCE = 0.70` — [schema_proposer.py:18–19](app/engines/convergence/schema_proposer.py)
- `_build_field_proposals()` threshold guard but no name guard — [schema_proposer.py:179–205](app/engines/convergence/schema_proposer.py)
- `_apply_node_properties()` writes proposed fields blindly — [schema_proposer.py:208–221](app/engines/convergence/schema_proposer.py)
- `_extract_existing_fields()` reads `yaml_spec["ontology"]["nodes"]` with `entities` fallback — [schema_proposer.py:259–267](app/engines/convergence/schema_proposer.py)
- `_bump_version()` returns `x.{y+1}.0-discovered` — [schema_proposer.py:359–366](app/engines/convergence/schema_proposer.py)
- `_build_confidence_map()` accepts both flat `{f: 0.9}` and nested `{"entries": {f: {"confidence": ..., "source": ...}}}` shapes — [schema_proposer.py:136–149](app/engines/convergence/schema_proposer.py)
- Existing tests use the **flat** confidence shape — [tests/test_schema_proposer.py:38–42](tests/test_schema_proposer.py)

No new dependencies. `pyproject.toml` is untouched. `pytest.ini_options.asyncio_mode = "auto"` already set.

## Phase 2 — Implementation deltas

### Delta 1 — `schema_proposer.py` (one constant, two guards, one structlog call)

**A. Insert after the existing module constants (after line 20):**

```python
# L9 Master Kernel §3.1 + §5.1 + §5.2 — banned non-canonical field name forms.
# This list is the single source of truth derived from the kernel and changes only
# when the kernel changes. It is NOT a per-domain or per-tenant override.
BANNED_FIELD_NAMES_L9_KERNEL: frozenset[str] = frozenset(
    {
        # §5.1 — TransportPacket / shared contract drift forms
        "packetid",
        "packetID",
        "packettype",
        "packetType",
        "contentHash",
        "content_hash_sha256",
        "threadId",
        "threadID",
        "traceId",
        "traceID",
        "parentIds",
        "sourceNode",
        "onBehalfOf",
        "orgId",
        "orgID",
        # §5.2 — spec.yaml drift forms (incl. valid-snake_case-but-wrong synonyms)
        "matchentities",
        "nodelabels",
        "matchdirections",
        "candidateprop",
        "null_semantics",
        "computation_type",
        "targetnode",
        "idproperty",
    }
)

# L9 Master Kernel §3.1 — canonical snake_case form for any proposed field name.
_SNAKE_CASE_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")
```

Add `import re` to the module imports (currently absent).

**B. Replace the threshold-only guard at [schema_proposer.py:188–189](app/engines/convergence/schema_proposer.py):**

```python
        if fill_rate < MIN_FILL_RATE or avg_conf < MIN_AVG_CONFIDENCE:
            continue
        if not _is_canonical_field_name(field_name):
            logger.warning(
                "schema_proposer.kernel_name_invariant_violation",
                field_name=field_name,
                entity_count=acc.non_null,
                stage="propose",
                kernel_section="L9 §3.1/§5.1/§5.2",
            )
            continue
```

**C. Insert a defense-in-depth mirror in `_apply_node_properties` at [schema_proposer.py:219–221](app/engines/convergence/schema_proposer.py):**

```python
            for fp in proposed_fields:
                if fp.field_name in approved_fields:
                    if not _is_canonical_field_name(fp.field_name):
                        logger.warning(
                            "schema_proposer.kernel_name_invariant_violation",
                            field_name=fp.field_name,
                            stage="apply",
                            kernel_section="L9 §3.1/§5.1/§5.2",
                        )
                        continue
                    props[fp.field_name] = {"type": fp.field_type, "source": fp.source}
```

The same guard pattern is added to `_apply_gate_proposals` (line 224) and `_apply_scoring_proposals` (line 235), checking `gp.field_name` / `sp.field_name`.

**D. Add helper near the other private helpers (after `_build_confidence_map`):**

```python
def _is_canonical_field_name(name: str) -> bool:
    """Per L9 Master Kernel §3.1 + §5.1 + §5.2: snake_case form, not in drift list."""
    if name in BANNED_FIELD_NAMES_L9_KERNEL:
        return False
    return bool(_SNAKE_CASE_RE.fullmatch(name))
```

Net: one new constant, one regex constant, one helper, four call sites (one in propose path + three in apply path), one new stdlib import.

### Delta 2 — `tests/contracts/tier2/test_schema_proposer_behavioral.py` (new file)

L9 metadata header (per §7), then three test classes. Uses the **flat** confidence shape to align with [tests/test_schema_proposer.py](tests/test_schema_proposer.py).

```python
"""Tier-2 behavioral contract tests for app.engines.convergence.schema_proposer.

L9 Master Kernel anchors: §3.1 (snake_case), §5.1 (TransportPacket name drift),
§5.2 (spec.yaml name drift), §2.3 INV-OBS-05 (structured logging on drop).

L9_META:
  tier: 2
  domain: convergence
  authority: L9 Master Kernel v3.0
  pr_class: app_code + tier2_test
"""
```

#### `TestProposeSchemaForKnownDomain`

Uses flat `{"final_field_confidences": {"industry_vertical": 0.90}}` shape, all-filled batches of size 10. Verifies:

- `propose()` returns a `SchemaProposalSet` with `domain` set
- `proposed_fields` is non-empty when batch confidence > `MIN_AVG_CONFIDENCE` and fill_rate > `MIN_FILL_RATE`
- `yaml_diff` is non-empty
- `version_bump` matches `r"^\d+\.\d+\.\d+-discovered$"`
- `entities_analysed` equals batch size
- Empty batch → empty `SchemaProposalSet`
- `confidence=0.50` (below threshold) → field excluded
- `fill_rate=0.50` (5/10 non-null) → field excluded

The malformed assertion from the GMP (`assert 0.50 < MIN_FILL_RATE is False or ...`) is corrected to `assert 0.50 < MIN_FILL_RATE`.

#### `TestProposeSchemaRespectsCurrentYamlScope`

Renamed from the GMP's "TenantIsolation" — the real invariant is "the proposer respects the `current_yaml` it was given," not `INV-ARCH-06` (which governs Neo4j queries). Verifies:

- A field already in `current_yaml.ontology.nodes.<Node>.properties` is excluded from `proposed_fields`
- Two distinct YAMLs A and B with overlapping existing field names suppress the same name independently for each call (no global hidden state)
- A novel field not in any provided YAML is proposed

#### `TestProposeSchemaEnforcesKernelFieldNameInvariants`

Parametrized over `BANNED_FIELD_NAMES_L9_KERNEL` (frozenset import from the module). Verifies:

- Each banned name (e.g. `packetid`, `traceId`, `matchentities`, `null_semantics`) is **never** present in `result.proposed_fields` even when batch fill_rate=1.0 and confidence=0.95
- Names violating snake_case (`camelCase`, `PascalCase`, `dotted.path`, leading underscore, leading digit) are excluded
- A safe field (`industry_vertical`) is proposed alongside a banned field (`traceId`) in the same batch — proves the guard is per-field, not per-batch
- `BANNED_FIELD_NAMES_L9_KERNEL` is a `frozenset` and contains all §5.1 + §5.2 entries listed in the kernel
- `apply()` defense-in-depth: a hand-built `SchemaProposalSet` containing a banned name is **not** written to the returned YAML

## Phase 3 — Validation

| Aspect | Check |
|---|---|
| Public API of `propose()` / `apply()` | Unchanged — same signatures, same return types |
| Behavior on canonical inputs | Identical — guard only acts on non-canonical names |
| L9 §3.1 / §5.1 / §5.2 | Enforced at proposal AND apply |
| L9 §2.3 INV-OBS-05 | Every drop emits `logger.warning` with `kernel_section` field |
| AGENTS.md C-04 (structlog) | Compliant |
| AGENTS.md C-05 (`list[T]`, `T \| None`) | Compliant — `frozenset[str]`, `re.Pattern[str]` |
| AGENTS.md C-13 (transport lockstep) | Untouched — no transport bundle file modified |
| AGENTS.md C-21 (SDK ingress) | Untouched |
| `make agent-check` 7 gates | Must pass before commit |
| `tests/test_schema_proposer.py` | Must remain green (existing flat-shape fixtures still work) |
| Other Tier-2 tests | Untouched |

## Phase 4 — PR + finalization

PR title: `feat(convergence): tier-2 behavioral tests + kernel name-invariant guard for schema_proposer`

PR body must include:

- Authority block citing L9 §3.1, §5.1, §5.2, §2.3 INV-OBS-05
- Tier classification: T3 engine + T2 tests
- Explicit non-goals: no PII filtering, no per-domain override, no `ApprovalDecision` deduplication, no transport changes
- Follow-up notes: (a) `ApprovalDecision` duplication, (b) `tests/test_schema_proposer.py` fixture shape reconciliation, (c) potential future `INV-SEC-*` governance PR for PII

Definition of done:

- Two files modified, no others
- All four write-paths in `schema_proposer.py` are guarded (`_build_field_proposals` + the three `_apply_*` helpers)
- All three test classes green; parametrized banned-name test covers every entry in `BANNED_FIELD_NAMES_L9_KERNEL`
- `make agent-check` clean (lint, format, mypy, unit, ci, audit, contracts)
- No new CRITICAL/HIGH scanner violations
- No new dependencies

## Risk and reversibility

Two-file PR. Single revert restores prior behavior. Zero impact on T4/T5 (transport, schema, kb). Worst case (constant typo or regex bug) drops legitimate fields with a logged warning — visible immediately in observability, no silent data loss because YAML diffs are reviewed before apply.