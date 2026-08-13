<!-- L9_META
l9_schema: 1
parent: l9-code-maintenance
layer: reference
role: sweep_protocol
tags: [refactor-sweep, governance, dry-run]
owner: igor_beylin
status: active
version: 3.1.0
updated: 2026-08-13
/L9_META -->

# Refactor Sweep Protocol

## Purpose

Deterministic read-only impact analysis. Prevents sloppy refactors.

## Chain

intent → DISCOVERY → CLASSIFICATION → IMPACT → GOVERNANCE DECISION → REPORT → STOP

## Phases

1. **Discovery** — locate instances via `rg` over intent-derived tokens and known path markers. Also `rg` `$HOME/.cursor-governance/learning/failures/repeated-mistakes.md` and `$HOME/.cursor-governance/learning/patterns/quick-fixes.md` for constraint tokens (known-bad patterns the sweep must not reintroduce; known-good templates to prefer). There is no `lessons.learned.md` — those two files are the corpus.
2. **Classification** — assign layer/domain; flag bootstrap, lifecycle, protected paths.
3. **Impact** — mechanical? logic change? import graph? public contract?
4. **Governance** — one of: Eligible for harvest-use | GMP REQUIRED | FORBIDDEN.
5. **Report** — stdout only; never write code.

## Rules

- If ANY instance is NOT mechanical → entire sweep NON-MECHANICAL.
- If ANY protected file involved → GMP REQUIRED.
- Path moves, schema `$id` renames, law-file edits → GMP REQUIRED.
- Intent that keeps root `autonomy/` callable while adding a campaign bridge → note do-not-move for root `autonomy/`.

## Outcomes

| Outcome | Action |
|---------|--------|
| All mechanical, no protected | Eligible for /harvest-use |
| Mixed mechanical + semantic | GMP REQUIRED |
| Lifecycle / bootstrap / law | GMP REQUIRED |
| Cross-layer violation | FORBIDDEN |

No gray areas. No partial approvals. After REPORT: STOP.
