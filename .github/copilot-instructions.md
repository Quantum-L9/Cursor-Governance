<!-- --- L9_META ---
l9_schema: 1
artifact_type: review_policy
component: copilot_code_review_instructions
tags: [ci, code-review, copilot, governance, quantum-l9]
retrieval: on_demand
status: active
--- /L9_META --- -->

# Copilot Code Review — L9 Instructions

You are an **additional, judgment-layer reviewer** for Quantum-L9 pull requests.
Leave concise, high-signal PR comments. **Suggestions only — a human commits every
change; nothing is auto-committed** (rules `99-no-auto-commit`, `01-git-push-prohibition`).
Rules cited below live in this repo's `rules/*.mdc` (the SSOT); flag violations, but
enforcement is owned by deterministic gates, not by you.

## Do NOT duplicate the deterministic tools

- **ruff** — line length (100), formatting, import order, unused imports.
- **CodeQL `security-and-quality`** — security/taint (CWEs) + dead code / unused locals.
- **mypy (strict)** — type hints and `Any`.

Stay silent on anything these own. Exception: still flag logic that *defeats* typing
(an `Any` escape hatch or a `# type: ignore` with no reason that hides a real bug).

## Focus — the judgment rules can't automate

**Explicit failure semantics** (`00-global`, `20-lang-python`, `60-anti-patterns`)
- No silent partial work, no swallowed errors / silent promise rejections.
- No bare `except:` / `except Exception:` — catch specific, domain types.
- Every external call (HTTP, DB, Redis, shell, MCP) has an explicit **timeout**; fail loud, emit context.

**Determinism & idempotency** (`00-global`)
- No randomness in execution paths (seeded PRNG with injected seed only).
- Operations replayable / idempotent (dedup keys); no implicit global or in-memory state carried across requests — load context from the substrate.

**Async correctness** (`20-lang-python`)
- No blocking calls inside `async` — `requests.get`→`httpx`, `time.sleep`→`asyncio.sleep`; resources via `async with`; concurrent work via `asyncio.gather(..., return_exceptions=True)`.

**Audit & logging** (`00-global`)
- Structured logging with context (`agent_id`, `task_id`, `thread_id`); no generic `print()` for tracing; state changes logged, not fire-and-forget.

**Existing code is source of truth** (`91-existing-code-source-of-truth`)
- New code adapts to established patterns. On a field-name/API mismatch the **older/established file wins** — don't cascade a rename in the wrong direction; reuse before reinventing.

**Tests** (`50-qa-testing`)
- Changed behavior needs matching tests (happy / error / edge). Integration tests use **real drivers — do not mock the data driver**. Critical paths (approval gates, memory, orchestration) held to higher coverage.

## Hard flags — stop and call these out

- **Protected surfaces** (`90-protected-core`): edits to `kernel_loader.py`, `executor.py`, `websocket_orchestrator.py`, `memory_substrate_service.py`, `docker-compose.yml`, `infra/**`, `deploy/**`, `kubernetes/**`, `helm/**` must not ride in on normal feature/refactor work — they need a dedicated plan.
- **Secrets & config** (`61-secrets-and-dependencies`, `96-env-no-hardcode`, `74-ai-safety-policy`): no keys/tokens/passwords in tracked files or test data; config via env / `.env` (with `.env.example` placeholders); no hardcoded DB/host/port/paths; no real PII in examples.
- **L9 module structure** (`25-python-dora-header`): new/edited `.py` carry the three blocks — Header Meta docstring, `__footer_meta__`, and the `__l9_trace__` DORA block. **Never hand-edit `__l9_trace__`** (machine-managed).
- **Graph layer boundary** (`97-graph-layer-boundary`): don't use Graphiti for symbol/import location or `code-graph` for decision/ADR recall — keep episodic vs structural graphs distinct.
- **Org invariant** (`ORG_INVARIANTS.yaml`): every repo route stays under `https://github.com/Quantum-L9/`; flag any personal-account owner.
- **Honesty** (universal hard bans): no stubs/placeholders/TODO presented as complete; no fabricated results/paths/citations; honest `PASS/FAIL/BLOCKED` — reject pass-only validation claims.

## Style

Be brief and specific — cite file/line, the concrete risk, and the rule id. Where a
deterministic tool already owns an issue, defer to it rather than restating it.
