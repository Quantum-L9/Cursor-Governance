# Decision and expansion contract

## Expansion classes

Each material growth item must be classified as exactly one of:

- `REQUIRED_BY_INTENT`
- `REQUIRED_DEPENDENCY`
- `REASONABLE_HARDENING`
- `TEST_OR_VALIDATION_ONLY`
- `UNJUSTIFIED_EXPANSION`
- `SPECULATIVE_GENERALIZATION`
- `DUPLICATE_CAPABILITY`
- `UNKNOWN`

Size is evidence, never a verdict. The decisive test is whether the added surface can be removed while the requested behavior remains correct, complete, and maintainable through existing canonical owners.

## Decision precedence

1. Proven deterministic CI/execution failure cannot be overridden by judgement.
2. Proven duplicate authority, shadow path, required-boundary bypass, misplaced domain logic, or conflicting contract authority yields `ARCHITECTURE_REPAIR_BEFORE_REMEDIATION`.
3. Confirmed unjustified expansion, speculative generalization, unrelated change, unnecessary dependency/configuration, or unsupported compatibility/fallback surface yields `NARROW_BEFORE_REMEDIATION`.
4. Missing original intent plus material semantic scope questions yields `INTENT_UNKNOWN_REVIEW_REQUIRED`.
5. `READY_FOR_REMEDIATION` requires exact revisions, acceptable current-stage CI evidence, no blocking architecture finding, no material unjustified expansion, and a bounded remediation packet.

## Agent expansion patterns

Treat Fable, Claude, Cursor, Codex, and future coding agents identically. Look for task reinterpretation, broad nearby refactors, speculative frameworks, duplicated helpers, compatibility layers without consumers, unrelated provider/config support, policy changes unrelated to the task, and fixes to unrelated nearby issues.
