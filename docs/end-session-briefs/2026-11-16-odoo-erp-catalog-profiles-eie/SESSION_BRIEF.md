# Session brief: Odoo campaign "ERP Catalog → Profiles → EIE"

| Field                    | Value                                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Repository               | `cryptoxdog/IB-Odoo_19` (branches `Staging`, `Production`)                                                    |
| CTO session              | `session_017xwbxuHzgYyNp8PADvkSnt` (Claude Code cloud, `/lcto` CTO mode)                                      |
| Period                   | 2026-11-13 to 2026-11-16 (UTC)                                                                                |
| Swarm                    | 11 coding agents (Opus 5.5, medium effort), all archived                                                      |
| Staging head at close    | `42db406` (#517)                                                                                              |
| Production head at close | `93c34c6`, "Merge Staging into Production"; contains `42db406` (verified with `git merge-base --is-ancestor`) |
| Hand-off                 | to L CTO; this campaign has converged                                                                         |

## 1. Outcome

The campaign's code is merged and promoted. On 2026-11-16 Production went from
`cfbe504` (2026-11-10) to `93c34c6`: about 300 commits, 25+ module version bumps
and more than 26 migrations. The merge used a merge commit, not a rebase.

| Area                             | Delivered                                                                                                                                                                                                                                                                                                  | PRs                               |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| ERP catalog → material profiles  | Loader puts ERP material profiles on the exact ERP site partner; production refusal and single-run lock                                                                                                                                                                                                    | #502                              |
| Matching hygiene                 | Match and offers are refused until the intake or lot has polymer and form. The refusal also covers manual drafts and send.                                                                                                                                                                                 | #504, #509                        |
| Escalation                       | Unresolved exceptions route to an Operations Manager, never the salesperson                                                                                                                                                                                                                                | #505                              |
| Gate converge v2 (EIE)           | v2 codec (request builder, response parser, mapping table); typed, reviewed profile writeback against cartridge `plasticos` 0.6.0                                                                                                                                                                          | #506, #507; EIE cartridge PR #348 |
| Enrichment sweep                 | Odoo side of the scheduled EIE buyer sweep. It follows the contract at `EIE@a606791:docs/contracts/enrichment-sweep.md` and ships **off** (ICP `plasticos.gate.sweep_enabled=0`, both crons inactive).                                                                                                     | #512                              |
| Export module                    | Surgical fixes (stale booking confirmation, counts, holds, commit replay)                                                                                                                                                                                                                                  | #503                              |
| Staging upgradability            | Strip the stale inherited-view xpath that broke the upgrade; repair a broken crm_bridge anchor                                                                                                                                                                                                             | #510                              |
| Clean build log                  | `res.partner.user_id` declared `recursive=True`; duplicate field labels removed                                                                                                                                                                                                                            | #511                              |
| Clean build log                  | Base modules stop declaring `partner_id` NOT NULL. The owner rule moves to an extensible constraint (partner, or a CRM-lead owner from crm_bridge). New CI test against relaxing a required field from a downstream module.                                                                                | #514                              |
| Dev environment                  | `requirements-dev.txt` now pins the packages `ci.yml` installs (pyyaml, pre-commit, lxml), so `make venv` runs the CI suite                                                                                                                                                                                | #513                              |
| Bales is packaging, never a form | Operator ruling 2026-11-16. Bales is retired as a form in profiles, the mapping sheet and its builder, `form_codes`, both form masters and the Gate payload. Colliding profiles are merged onto the form-less survivor; pairs it cannot merge are logged; the upgrade never aborts. Recurrence test added. | #517                              |
| Closed-offer integrity           | `transaction_id` on a closed offer accepts only the first link of an accepted offer, including during state changes. A raw write can no longer cancel, reject or expire an accepted offer.                                                                                                                 | #517                              |

Every PR merged with CI Gate Result green. Every Copilot review thread on #516 and
#517 was answered with the fixing commit and resolved.

## 2. Live state at close

| Item                                  | State                                                                                                                                                           | Evidence                                         |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Production code                       | `93c34c6`, containing Staging `42db406`                                                                                                                         | git ancestry, read 2026-11-16                    |
| Production Odoo.sh build of `93c34c6` | **Not observed by this session.** The operator owns this check.                                                                                                 | —                                                |
| Bales retirement on real data         | **Not observed.** Pure tests only; its first real runs are the Staging and Production upgrades. The update log carries the moved, merged and unresolved counts. | `plasticos_material_profile/bales_retirement.py` |
| `plasticos_export`                    | Uninstalled, by operator decision 2026-11-15. Still uninstalled when last checked (Staging rebuild of 2026-11-16).                                              | operator decision                                |
| Gate (Constellation.Gate)             | Not deployed. The operator **deferred** the deploy until testing is done and GitHub settings, keys and key ids are confirmed.                                   | CTO CEG message, 2026-11-16                      |
| Odoo → Gate wiring                    | Blocked: Odoo.sh has no build-persistent process environment (Cursor probe P0 verdict **M3** on both hosts)                                                     | `GATE-WIRING-RESULT`, 2026-11-16                 |
| Converge contract on Production       | v1 (seed default). The v2 ICP keys were never written to a surviving database (Staging's database was replaced by the 2026-11-16 rebuild).                      | —                                                |
| Enrichment sweep                      | Off everywhere                                                                                                                                                  | #512 defaults                                    |

## 3. Gate wiring: decisions recorded, work remaining

Operator decisions, 2026-11-15/16:

- **Tenant** `plasticos` on every Odoo database. This is not a choice: EIE
  (EIE-IDENT-02) and CEG (HEALTH-05) both bind tenant = domain spec id = Neo4j
  database. `scrapmanagement` is withdrawn, and `docs/GATE_ODOO_WIRING.md` in the
  Odoo repository still names it and needs correcting.
- **Topology, option A.** One Gate, the production Gate on C1, proposed URL
  `https://gate.quantumaipartners.com`. Only **Production** Odoo is wired.
  Staging Odoo gets no key and no Gate environment until a separate staging Gate,
  with staging EIE and CEG, exists.
- **Key id** `odoo-plasticos-v1` (ed25519). The public key was handed to CTO CEG,
  which recorded it with the caller policy
  `{node: odoo, kind: consumer, tenants: [plasticos], actions: [match, converge, enrichment-sweep, enrichment-sweep-results]}`.
  The private key exists only on the operator's workstation (`~/.l9/gate-keys/`,
  mode 600) and was never printed or committed.

Remaining, in order:

1. **ADR, Odoo side.** `gate_config.py` reads `GATE_URL` and `L9_*` only from the
   process environment, and Odoo.sh cannot persist one (M3). The decision is where
   Odoo's Gate settings live. The private key must not go into the database: Staging
   is rebuilt from Production copies, so the key would leak there. Candidate
   carriers are an Odoo.sh-persistent file outside the build tree, if one exists,
   or `odoo.conf` options read through `odoo.tools.config`. The first needs Odoo.sh
   support to confirm it; the second is a second config source, which
   `gate_config.py` deliberately forbids today. Odoo.sh support has not been
   asked yet.
2. **Gate deploy** on C1 by CTO CEG, after the operator lifts the deferral. CEG
   then supplies `GATE_URL`, Gate's key id and Gate's public key.
3. **Cursor runbook P2 to P5, Production only.** P0 and P1 are done. The runbook,
   with SSH hostnames removed, is [`GATE_WIRING_RUNBOOK.md`](GATE_WIRING_RUNBOOK.md)
   in this folder. P2 must use the carrier the ADR picks.
4. **First Match and first Enrich on Production**, on an explicit operator "go".
   `auto_writeback` stays 0, so results land in review.

## 4. Operator decisions owed

| #   | Decision                                                      | Context                                                                                                                                                                                   |
| --- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | #502: ERP product ids vs names in the loader input            | raised during #502; unresolved                                                                                                                                                            |
| D2  | 17 rejected ERP rows (OPAQUE, TRANSLUCENT, RESIN values)      | the loader rejects them by design; mapping or exclusion is the operator's call                                                                                                            |
| D3  | Running the ERP material-profile loader on Production         | the loader refuses production databases on purpose; a run needs an explicit permit and a code path                                                                                        |
| D4  | Odoo Enterprise runtime tests                                 | Operator constraint in force all campaign: none run. TransactionCase tests that exist but have **never run**: offer link freeze, raw-close transitions, Bales runtime, #507 lane B, #505. |
| D5  | Gate settings carrier (§3 step 1)                             | ADR needed before any Odoo↔Gate traffic                                                                                                                                                   |
| D6  | Gate deploy go-ahead (C1)                                     | deferred by the operator                                                                                                                                                                  |
| D7  | Orphan material/facility profiles with no partner and no lead | #514's upgrade report logs any it finds; the operator decides what to do with them                                                                                                        |

## 5. Risks carried into Production

- **Untested at runtime:** the Bales merge (reference repointing and duplicate
  deletion), and the offer write guards. Both are covered only by pure tests and
  static review. Mitigation: read the Production update log for the Bales counts,
  and spot-check one accepted offer and one material profile.
- **Copilot reviewed only #517's first commit.** GitHub ignored a re-request
  through the API for the final head `19b9588`. The final head was reviewed by the
  CTO only.
- **The Production ruleset was toggled off** for the promotion merge, then back on
  (operator, 2026-11-16). Confirm it is active.

## 6. Hand-off to L CTO

The campaign swarm is fully archived and no campaign PR is open. Two sessions were
launched at close, at the operator's request. The operator drives each one
directly, and this CTO does not track them:

| Session                             | Id                                 | Mode                    | Owns                                                                                                                                                      |
| ----------------------------------- | ---------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PlasticOS Odoo UI polish            | `session_017xwbxyk6BYspwHQPVKAFxs` | coding                  | Production layout and aesthetic fixes, one item at a time, views and assets only, PRs to `Staging`. First item: the contact form's half-width Sites list. |
| PlasticOS Odoo architect (advisory) | `session_017xwbxuGBnqXGLob4ewjdtZ` | `/architect`, no coding | Advice and ADRs on request: the Gate settings carrier (D5), data decisions D1–D3 and D7, the untested runtime risks, UI consistency                       |

Both run Opus 5.5 at medium effort on `cryptoxdog/IB-Odoo_19` `Staging`, under
this campaign's standing constraints. Next work, in priority order:

1. Confirm the Production build and the Bales log counts (operator, about 5 minutes).
2. D5 ADR, then Gate wiring §3.
3. D4: decide a window for Enterprise runtime tests, or keep accepting the risk.
4. D1 to D3 and D7: data decisions for the ERP import track.

The protocol changes that would let this hand-off run without operator approvals
are in `CTO_SWARM_OPERATIONS_BRIEF.md` in this folder.
