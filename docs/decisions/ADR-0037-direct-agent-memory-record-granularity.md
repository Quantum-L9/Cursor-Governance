# ADR-0037: Direct agent memory records represent independently governable knowledge

## Status

Accepted

## Date

2026-09-24

## Supersedes

Nothing. Clarifies ADR-0031 / ADR-0033. It changes no runtime behaviour, adds no
hook, receipt, memory class, lifecycle state, permission class, write API or
persistence mechanism.

## Context

The direct agent-write contract (`memory.write_agent`, `rules/87-cursor-memory-kernel.mdc`,
`skills/l9-graphiti-memory/SKILL.md`) asks for "one atomic fact" / "one fact per
write". The phrase states the intended granularity but never defines it, and it
is easy to over-read as one grammatical sentence, one subject–predicate–object
triple, or a property a runtime classifier should decide.

The property that matters is whether a piece of knowledge can be retrieved and
superseded on its own. An agent often learns several unrelated durable things in
one task; bundling them into one record couples them, so superseding one would
rewrite the others. Conversely, two concepts whose *relationship* is the durable
knowledge lose meaning if they are split.

Three mechanisms are already distinct in the tree and are sometimes conflated in
prose:

| Mechanism | Where | What it is |
|---|---|---|
| SessionStart hydration / prefetch | `hooks/memory_prefetch.py`, `preconditions.session_prefetch` in `memory-enforcement.contract.json` | the only memory precondition on repository mutation |
| Direct agent write | `memory.write_agent` → `MemoryService.write` | ordinary durable knowledge the agent chose to keep |
| Governed write | `memory.phase_lock` → `memory.write_governed` → `MemoryService.write_governed` | conflict-sensitive write bound to a namespace snapshot |

## Options Considered

1. **Leave "one atomic fact" undefined.** Zero cost, but the phrase keeps being
   read as one sentence or one triple, and nothing states that independent
   memories are separate writes or that `memory.phase_lock` is not prefetch.
   Rejected: the ambiguity is the defect.
2. **Enforce atomicity at runtime** (proposition counting, an NLP splitter, or
   an LLM validator in front of `memory.write_agent`). Mechanically checkable
   in principle, but it adds a new authority surface on the agent lane that
   ADR-0033 / CANONICAL_LAW §8.6 forbid interposing, and semantic splitting is
   unreliable. Rejected.
3. **Define granularity by independent retrievability and supersession; keep
   runtime enforcement structural.** No new mechanism; the agent decomposes;
   existing schema, grant and admission controls stay the enforcement boundary.
   **Chosen.**
4. **Add a batch write that carries several facts in one call.** Would
   formalise "remember several things" as one request, but couples unrelated
   records in one admission and adds a new write API. Rejected: several
   `memory.write_agent` calls already express it.

## Decision

**A direct agent memory record represents one independently retrievable
assertion, or one closely coupled relationship, that can be superseded without
changing unrelated knowledge. Independent assertions are written as separate
records.**

Semantic decomposition is the agent's responsibility. Runtime validation
enforces the record contract — payload shape, allowed memory classes, content
bounds, namespace grant, identity, tags, idempotency key, `MemoryService`
admission — and does not attempt to decide proposition-level atomicity.

### Examples

One record — the relationship is the knowledge:

> Repository and governance handoffs use separate namespaces to prevent cross-plane contamination.

Three records — the ideas are independent:

> Repository handoffs use the in-scope repository namespace.
> Degraded hydration remains usable for session closure.
> Direct agent-authored durable memory uses the agent memory write lane.

The agent makes three `memory.write_agent` calls. No batch mechanism exists or
is needed.

### Lane table

| Write lane | Purpose | `memory.phase_lock` | SessionStart prefetch per write |
|---|---|---|---|
| `memory.write_agent` | ordinary agent-selected durable knowledge | **No** | no prerequisite |
| `memory.write_governed` | conflict-sensitive write under the governed task path | **Required** (existing) | existing execution contract only |

`memory.phase_lock` governs the governed-write lane. It is not the SessionStart
memory-prefetch receipt, is not proof that hydration occurred, and MUST NOT
become a prerequisite for ordinary `memory.write_agent`.

## Invariants

| ID | Invariant |
|---|---|
| INV-AMW-01 | A `memory.write_agent` record is one independently retrievable assertion or one closely coupled relationship; independent assertions are separate writes. |
| INV-AMW-02 | No runtime NLP, proposition counting, semantic splitter or classifier decides "atomicity". Structural validation is the enforcement boundary. |
| INV-AMW-03 | Several independent memories are several `memory.write_agent` calls; no batch or session-summary record is required. |
| INV-AMW-04 | `memory.write_agent` does not require `memory.phase_lock`; its authority is identity, namespace grant, payload contract and `MemoryService` admission. |
| INV-AMW-05 | `memory.write_governed` keeps its existing `memory.phase_lock` requirement. |
| INV-AMW-06 | `memory.phase_lock` is not the SessionStart hydration receipt, not the prefetch gate, and not a prerequisite for `memory.write_agent`. |
| INV-AMW-07 | SessionStart prefetch, canonical hydration, `fresh_receipt` / `usable_receipt`, mutation-gate semantics, receipt identity and namespace hydration are unchanged. |
| INV-AMW-08 | No new hook, receipt, memory class, lifecycle state, permission class, write API or persistence mechanism. |

Regression suite: `tests/ops/memory/test_agent_write_semantics.py` (real
`MemoryService` over a temporary sqlite store — A: no lock on the direct lane;
B: governed write refuses without a held lock; C: sequential independent
writes; D: existing structural rejections; plus the contract-level separation
of `phase_lock` from `session_prefetch`).

## Consequences

Positive:

- direct memory stays small and independently reusable;
- unrelated knowledge is not coupled into session-summary blobs;
- supersession can target one idea without invalidating unrelated facts;
- no semantic parser or atomicity classifier is introduced.

Negative:

- decomposition remains a model judgment, so a record may occasionally be too
  broad or too narrow. That trade-off is accepted.
