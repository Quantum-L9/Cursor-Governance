# Rules stabilization validation

**Scope:** Cursor rule topology, rule ownership, generated manifests, selective delivery tooling, and startup fingerprinting.

| Gate | Result | Evidence |
|---|---|---|
| Overlay regression suite | PASS | `RESULT: PASS (8 cases)` |
| UV fingerprint suite | PASS | `RESULT: PASS (fingerprint cache, input change, invalid venv)` |
| Selective rule delivery suite | PASS | `RESULT: PASS (individual links, idempotence, collision fail-closed)` |
| Python syntax compilation | PASS | `` |
| Manifest generation | PASS | `GENERATED: 59 rules; always=38` |
| Manifest validation | PASS | `RESULT: PASS - manifests match filesystem and rule contracts` |
| Corpus audit generation | PASS | `WROTE: reports/rules-corpus-audit.md` |
| Scoped ruff | PASS | `All checks passed!` |
| Full repository ruff | DEFERRED | `Use --full; known unrelated debt may remain` |
| Full repository pytest | DEFERRED | `Use --full; known unrelated collection debt may remain` |

## Manual gate

Cursor UI discovery and all four activation modes require an installed Cursor session. They are tracked in the consumer repository's `reports/cursor-rules-activation-baseline.md` and are not represented as automated success.
