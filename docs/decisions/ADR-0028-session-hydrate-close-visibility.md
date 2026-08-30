# ADR-0028: Session hydrate/close visibility and write-primary repair

## Status

Accepted

## Date

2026-08-30

## Context

SessionEnd (`graphiti-session-end.sh` → `close_session.py`) is fail-open. A
skipped close, `write_count: 0`, or a Cursor hook that never fires leaves no
signal that SessionStart can use. Close receipts under
`.l9/memory/closes/{session_id}.json` are an idempotency latch only;
`compile_session_packet` does not read them. Hydrate can therefore print a
generic PICKUP while the last session never landed in Graphiti.

`/end-session` documented `hydration.cli close --reason force_retry` as the
preferred repair. That replays the same heuristic closer as the hook and hides
the gap. ADR-0005 still requires one episodic store; ADR-0006 still requires
one Graphiti front door; ADR-0003 still keeps hook vs interactive **roles**.
This ADR answers a different question: how a missed close becomes **loud**, and
how repair is **written**.

Constraints: SessionStart must exit 0 (Cursor swallows hook rc). Do not restore
`memory-bank/`. Do not ingest `reports/repo-index` bodies. Do not treat local
receipts as resume SSOT.

## Options Considered

### Option A: Loud hydrate + write-primary repair (chosen)

Hook stays `close_session.py`. Skip/fail always writes a local receipt. One
Graphiti `write` fallback if `write_count=0`. SessionStart prints hard
`DEGRADED` + `REPAIR: /end-session`. `/end-session` primary is
`graphiti_memory_client.py write`. SessionStart exit 0.

- Pros: uses the existing store; repair is an explicit episode; hydrate can
  see a missing or empty receipt; Cursor-compatible
- Cons: a dead hook still only shows up at the *next* SessionStart

### Option B: Non-zero hook exit

SessionStart / sessionEnd exit non-zero on close-gap.

- Pros: looks fail-closed in a TTY
- Cons: Cursor swallows hook rc; agents still miss it

### Option C: `/end-session` prefers `hydration.cli close`

Replay Phase A/B as the repair.

- Pros: one closer
- Cons: second heuristic PICKUP; hides that the hook failed

### Option D: Restore `memory-bank/` as automatic fallback

- Pros: local bytes when Graphiti is down
- Cons: retired second SSOT; contradicts ADR-0005 / MEMORY_BANK_POLICY

### Option E: Ingest `reports/repo-index` bodies into Graphiti

- Pros: denser search
- Cons: structural dump; stale; T3-adjacent; wrong layer (code-graph / disk)

### Option F: Treat `.l9/memory/closes` as resume SSOT

- Pros: no Graphiti round-trip
- Cons: receipts are not episodes; drift from C1 Neo4j

## Decision

This ADR does not supersede ADR-0005 or ADR-0006.

We choose **Option A**. Invariants:

1. **Two writers, one store.** The hook owns `close_session.py`. `/end-session`
   owns `graphiti_memory_client.py write --kind pickup_context|lesson|error`.
   Do not prefer `hydration.cli close` as repair. After a successful repair
   write, stamp a close receipt so the next hydrate can clear DEGRADED.
2. **Automatic fallback is Graphiti write.** If `close_session.py` skips,
   raises, or finishes with `write_count=0`, the hook retries once via a Python
   helper. If that fails: fail receipt + ERROR on stderr. No `memory-bank/`.
   `/end-session` is the only human/agent repair.
3. **Receipts are latches, not SSOT.** Statuses: `closed`,
   `closed_enqueue_failed`, `close_failed`, `skipped_no_project`,
   `skipped_disabled`, `skipped_cli_missing`. Always write a receipt when the
   project dir is known. `write_count: 0` is a fail. Missing receipt for a
   prior opened session is a fail.
4. **Success vs S3-loud.** `closed_enqueue_failed` with `phase_a=true` and
   `write_count>0` is not a close-gap.
5. **One session id.** `resolve_session_id()`: explicit →
   `CURSOR_CONVERSATION_ID` → `CURSOR_SESSION_ID` → `default`.
6. **Opened latch.** SessionStart writes `.l9/memory/opens/<id>.json` and
   rotates `previous_opened.json` / `last_opened.json`. First session (no
   previous open) is not receipt-degraded.
7. **Background sessions** write their own open/close and must not overwrite
   parent `last_opened.json`.
8. **Recent PICKUP.** Search for `session=<prior_id>`. Close-gap when a prior
   open exists and the receipt is missing/fail/`write_count=0` **or** no fact
   contains that session id. Empty search + prior open is enough. No wall-clock
   TTL.
9. **Hard DEGRADED.** `format_additional_context` leads with `DEGRADED` and
   `REPAIR: /end-session` on close-gap. `next_action` is `/end-session`.
   SessionStart exits 0. Hook stderr uses ERROR on skip/fail. Enqueue stays
   exit 2. No v1 kill switch.
10. **Repair idempotency.** Skip a duplicate PICKUP when the receipt is already
    `closed` and `write_count>0`, unless superseding with a richer `next=`.
11. **Bootstrap stays RepoManifest-only.** Pointer path `reports/repo-index/`
    may appear in manifest `sources`; never ingest catalog bodies.
12. **T2 writes during work** remain agent/CLI (`lesson` / `insight` /
    structured PICKUP). Generic hydrate prose is a quality WARN, not a
    close-gap by itself.

## Consequences

- SessionStart banners can demand `/end-session` when the last session did not
  land. Agents cannot treat a missing receipt as invisible.
- `/end-session` writes Graphiti episodes instead of replaying the closer.
- Local `.l9/memory/` files stay gitignored latches.
- Repo identity in Graphiti remains the idempotent `bootstrap` RepoManifest
  (ADR-0006 front door). Structural indexes stay on disk / code-graph.
- A force-quit that skips `sessionEnd` is detected only at the next
  SessionStart (open latch with no close).

## Related

- ADR-0002 — memory enforcement contract
- ADR-0003 — two entry points, one contract (hook vs interactive roles)
- ADR-0004 — hook memory client contract pin
- ADR-0005 — one agent episodic memory; domain graphs out of band
- ADR-0006 — single memory front door (Graphiti)
- ADR-0007 — cloud Graphiti HTTPS reachability
- `docs/MEMORY_PIPELINE_MAP.md`
- `skills/l9-graphiti-memory/SKILL.md`
- `skills/l9-end-session/SKILL.md`
