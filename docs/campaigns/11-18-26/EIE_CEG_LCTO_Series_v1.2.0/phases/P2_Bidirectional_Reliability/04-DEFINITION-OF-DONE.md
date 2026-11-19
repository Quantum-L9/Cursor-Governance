# Evidence-based definition of done

| Gate | Owner | Dependency | Claim | Required proof | Status | Receipt |
|---|---|---|---|---|---|---|
| G0 | BASE | none | P1 stacked PR heads are published and green, with typed CRM-to-graph contracts ready; no Docker or prior phase merge is required. | Check P1 code-ready receipts, PR parent chain, and current DB model/migration source surface. | NOT_RUN | NOT_RUN |
| G_SCHEMA | OUT | G0 | EIE outbound and inbound writers agree on the existing Postgres model/table interfaces before separate code changes require shared persistence. | One exact DB model/migration/interface shape owned solely by OUT, testable fake store API and source-bound handoff to IN; do not run Docker. | NOT_RUN | NOT_RUN |
| G_OUT | OUT | G_SCHEMA | EIE outbound graph sync uses a durable pending record and replayable idempotent acknowledgement state, demonstrated in focused tests. | Bounded DB-model/store contract plus injected-store persisted/restart simulation, duplicate and missing ACK negative; full Postgres crash window only P4 Docker rail. | NOT_RUN | NOT_RUN |
| G_IN | IN | G_SCHEMA | CEG feedback can be durably queued and consumed exactly for the tenant/entity under the approved OUT-owned storage interface. | Queue-full/restart/duplicate/request-selection negative unit cases against injected durable store, no direct schema write by IN. | NOT_RUN | NOT_RUN |
| G_FEED | FEED | G0 | CEG feedback sender honors authorized domain inference rules and precise statuses with default-off safety, checked without Docker. | Focused CEG sender/handler and Gate contract tests with fake signed response and above/below floor cases. | NOT_RUN | NOT_RUN |
| G_SEAM | SEAM | G0 | Unsupported score-invalidate route is removed or corrected at the actual owner, without adding an unapproved Gate action. | Current owner/caller inspection plus focused EIE negative test and any needed OUT-owned packet_router change; static Gate action listing. | NOT_RUN | NOT_RUN |
| G_DONE | BASE | G_OUT, G_IN, G_FEED, G_SEAM | P2 bidirectional durability implementation is fully published and green at the exact PR stack heads; actual two-process crash/replay is reserved for final P4 Docker. | P2 green PR/base/head records, DB model ownership closure, durable queue/outbox/inference and auth unit tests; real crash/DB acknowledgement acceptance only P4. | NOT_RUN | NOT_RUN |

## Negative controls

- **G0**: Do not claim actual Postgres crash safety from P1 static work.
- **G_SCHEMA**: IN must not independently edit pg_models.py or migrations; unresolved interface means IN waits while FEED continues.
- **G_OUT**: Process-local dedup alone is insufficient; no claim of tested real database restart.
- **G_IN**: Accepted must not mean in-memory-only or loss when queue full.
- **G_FEED**: Cannot imply live signed EIE consumption or production activation.
- **G_SEAM**: Do not silently treat fire-and-forget refusal as successful cache refresh.
- **G_DONE**: No false green from process-local fake restart.

No gate passes from a job's green banner when mandatory steps were skipped. A source file, PR, release artifact, deployed image and real runtime are distinct evidence stages. A PASS is eligible only when the actual required proof executed and the final exact head/result is bound. A BLOCKED gate needs one actual wake condition, not a fabricated retry. NOT_APPLICABLE requires the rationale recorded in CAMPAIGN.json.

All in-scope findings must be FIXED, ALREADY_SATISFIED, INVALID, or explicitly BLOCKED with owner and wake action. An unresolved BLOCKED cannot be called DONE.
