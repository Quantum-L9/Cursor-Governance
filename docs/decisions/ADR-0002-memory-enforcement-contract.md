# ADR-0002: Memory is an enforced contract, not advisory context

## Status

Accepted

## Date

2026-08-02

## Context

The Claude Code surface had the `l9-shared-memory` server wired and healthy, and
the SessionStart hook *mentioned* it (`shared memory: L9_MEMORY_HTTP_URL set`).
But nothing required an agent to prefetch memory, conflict-check, or write back.
Memory usage was **discretionary**, and discretionary controls lose to momentum:
a full multi-PR governance session ran without a single memory read or write.

This is the same defect this repo already identified for autonomous merge in
ADR-0001 — *"the gate is advisory, not enforced at the permission boundary"* —
reproduced for memory. An instruction the model can skip is a suggestion, not a
control. The `GATES-002` fail-closed primitive existed but defaulted off and was
Cursor-only; it was never ported to Claude Code.

## Decision

Make memory a **machine-readable, hook-enforced, CI-validated contract** for the
Claude Code surface. The agent no longer has the choice; the harness does.

- **Contract**: `environment/claude-code/memory/memory-enforcement.contract.json`
  with a JSON Schema (`memory-enforcement.schema.json`). It declares the governed
  writes, required preconditions, fail modes, and hook wiring.
- **Enforcement point — PreToolUse gate** (`hooks/memory_gate.py`): classifies
  each tool call against the contract and emits a `deny` permission decision when
  a governed write's preconditions are unmet. It only ever ADDS denials.
  - `session_prefetch` — a SessionStart receipt must exist (fresh, this session).
  - `phase_lock` — for authority-file edits, `git commit/push/merge`, and PR
    create/merge: a conflict-checked lock **re-verified against the memory
    server** (`memory.verify_phase_lock`). A forged local lock file without a real
    server claim does not pass.
- **SessionStart prefetch** (`hooks/memory_prefetch.py`): hydrates the namespace
  and writes the receipt. Fail-open (never blocks startup) — but no receipt means
  the gate stays fail-closed for governed writes. Net effect: fail-closed at the
  write boundary without ever bricking session start.
- **Stop write-back** (`hooks/memory_writeback.py`): deterministically ingests a
  session episode (branch, HEAD, commits) so provenance lands regardless of agent
  choice.
- **Validation** (`validate_memory_enforcement.py`, run by `validate_claude_env.py`
  in CI): checks the contract against its schema AND **wiring parity** — every
  hook the contract declares must be registered in `settings.template.json` with
  the matching event. Enforcement-by-documentation fails CI.

## Options considered

1. **Keep memory advisory** (status quo). Rejected: demonstrably skipped.
2. **Stronger prose / a routing rule.** Rejected: still discretionary — a rule the
   model may ignore is not a control.
3. **A fail-closed PreToolUse gate driven by a validated contract** (this ADR).
   Chosen: removes the agent's choice at the tool boundary and is CI-checkable.

## Consequences

- Governed writes on the Claude Code surface are impossible without a memory
  prefetch, and authority edits / pushes / merges are impossible without a
  server-verified phase-lock. The agent cannot opt out.
- **Operator retains override** (the human, not the agent):
  `L9_MEMORY_ENFORCEMENT=off` disables enforcement on surfaces without a memory
  endpoint; `L9_MEMORY_ENFORCEMENT_BREAKGLASS=<reason>` allows a specific call and
  records the override. Neither is settable by the agent for its own hook
  subprocesses.
- **Availability coupling (accepted):** when memory is unreachable, lock-gated
  writes fail closed. That is the intent; the break-glass and disable envs are the
  recovery path.
- **Trust boundary (documented):** the prefetch *receipt* is trust-on-write (low
  stakes — worst case a session skips reading memory). The *phase-lock* is
  server-authoritative, so it resists local forgery. Enforcement ultimately rests
  on the Claude Code harness executing PreToolUse hooks and honoring `deny` — the
  same trust the `rm -rf` deny relies on.
- The gate adds one `verify_phase_lock` round-trip to lock-gated writes only
  (authority edits, pushes, merges), not to every tool call.

## Follow-ups

- Port the same contract to other surfaces (Cursor already has `GATES-002`;
  reconcile the two so there is one memory-enforcement authority).
- Consider server-issued signed lock tokens to remove the receipt trust-on-write
  gap entirely.
