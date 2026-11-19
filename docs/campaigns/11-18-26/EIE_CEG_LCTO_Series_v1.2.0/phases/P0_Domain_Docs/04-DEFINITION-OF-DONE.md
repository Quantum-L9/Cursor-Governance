# Evidence-based definition of done

| Gate | Owner | Dependency | Claim | Required proof | Status | Receipt |
|---|---|---|---|---|---|---|
| G0 | BASE | none | Pinned code/tenant test-pack source and deliberate single LCTO activation permit Phase P0 development; live deployment pack admission remains a separate P4 proof. | Check current immutable source heads, explicit operator-scope override, native authoritative test-pack/fixture origin, verified stack ledger and active LCTO; do not require running Docker. | NOT_RUN | NOT_RUN |
| G_DOC | DOC | none | EIE README/AGENTS/invariants/ADR index are current and compliant, with the campaign-only extra human-review waiver applied. | Concrete docs diffs, correct 8-gate Repo.mk references, nonduplicated local invariants with negative tests, ADR collision resolution, docs lint and current-head PR green. | NOT_RUN | NOT_RUN |
| G_SPEC | ESPEC | G0 | Current native tenant test-pack/typed row/edge contracts accept only compatible EIE and CEG meanings without runtime Docker. | EIE and CEG native spec-loader unit tests and typed compatibility/negative fixture receipts; bind specimen revision and admission uncertainty. | NOT_RUN | NOT_RUN |
| G_ROUTE | SEAM | G0 | Gate route ownership and caller authorization contract pass unit/contract negatives; live signing/traffic is deferred to P4. | Read current canonical actions and caller policy, run non-Docker route unit and negative authorization tests; identify missing scoped test signing key from Infisical for final P4. | NOT_RUN | NOT_RUN |
| G_DONE | BASE | G_DOC, G_SPEC, G_ROUTE | P0 documents/domain-compatibility work is published in correctly stacked green PRs and ready for P1; final live signed Graph proof waits until program P4. | All P0 writer PR URL/base/head ledger entries green (or evidence-backed already satisfied), docs negative tests, native dual-spec and Gate static unit receipts. | NOT_RUN | NOT_RUN |

## Negative controls

- **G0**: Unknown test-pack source blocks spec edits only, not independent docs/route assurance.
- **G_DOC**: No local AGENT review pause; README cannot claim an unrun five-service integration.
- **G_SPEC**: Historical CEG fixture cannot be promoted into deployed/active pack authority.
- **G_ROUTE**: A static positive assertion cannot claim a live signed round trip.
- **G_DONE**: Do not block P1 on Docker or merge or claim P0 proved live Neo4j.

No gate passes from a job's green banner when mandatory steps were skipped. A source file, PR, release artifact, deployed image and real runtime are distinct evidence stages. A PASS is eligible only when the actual required proof executed and the final exact head/result is bound. A BLOCKED gate needs one actual wake condition, not a fabricated retry. NOT_APPLICABLE requires the rationale recorded in CAMPAIGN.json.

All in-scope findings must be FIXED, ALREADY_SATISFIED, INVALID, or explicitly BLOCKED with owner and wake action. An unresolved BLOCKED cannot be called DONE.
