# l9-strategic-plan

**Proposed repository source of truth:** `Quantum-L9/Cursor-Governance/skills/l9-strategic-plan/`.
This package is a successor of the installed ChatGPT `strategic-planner` baseline. It is **not** a successor to Cursor's `l9-plan` or `l9-plan-simple`, which own execution planning.

## Scope

Preserves the baseline's strategic reasoning, graph continuity and bounded plan revisions; all original validation scripts and tests remain included. Adds owner-and-host separation, canonical domain-binding handoff, and governed `l9-graphiti-memory` integration guidance. The skill owner is Cursor-Governance; global L9 semantics live in `.github`, and Plan Keeper strategy admission stays external.

## Owner handoff

1. Register and commit this directory to `Cursor-Governance/skills/l9-strategic-plan/`, with the exact source and skill digest. That action is **for the operator**, not performed by this ZIP.
2. Read `references/l9-consumer-binding.md` and propose an admitted canonical binding successor to blocked `l9.domain-consumer-binding/strategic-planner@1`. The old version is immutable. Resolve 14 predecessor selector dispositions, preserve the six mandatory and two task-conditional domains.
3. Execute the actual L9 Semantic Compiler projection/composition, verification and consumer replay against the admitted `.github` revision. No generated projection or PASS receipt is inside this ZIP.
4. Attach the resulting real bundle, manifests and receipts to the source skill, bind the installed host to the exact source revision, and **then** upload the skill with its projection as a new ChatGPT distribution. Until then this ZIP is source-ready and **not consumer bound**.
5. For memory, use `references/l9-memory.md`. Reuse Memory's existing ingestion and topology publication interfaces; never use Supabase or direct graph writes.

## Existing tests (local, structural only)

Run from the `scripts/` directory: `python -m unittest discover -s . -p 'test_*.py'`. For a working-plan ZIP with a predecessor, invoke `validate_working_plan.py` with real predecessor and caller-authored policy. For applicable quantified Strategic Value work only, `verify_sv_binding.py` demands the actual compatible compiler and admitted historical projection artifacts; its lock is not proof of active consumer binding.

## Distribution status

- Source skill packaged: candidate
- Cursor-Governance committed/registered: **NOT_RUN**
- Canonical binding successor admitted: **NOT_RUN**
- Domain projection and consumer replay: **NOT_RUN**
- Graphiti Memory session round-trip: **NOT_RUN**
- Fresh-session behavioral evaluation: **NOT_RUN**
