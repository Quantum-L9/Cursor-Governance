---
name: Dual-mode Google auth playbook
overview: Rewrite the Google OAuth playbook doc to document the domain-wide-delegation setup (the model actively being wired in your other session) as the primary path, with the original per-identity OAuth-consent model preserved as an explicit fallback/revert path — documentation only, no code or secrets touched.
todos:
  - id: rewrite-playbook
    content: Rewrite workspace/contracts/06-google-oauth-dual-identity-setup.md with primary (domain-wide delegation) + fallback (OAuth consent) sections, status snapshot, and the scope-boundary nuance for ib@/nc@
    status: pending
  - id: reword-tasks-md
    content: Optionally reword the memory-bank/tasks.md deferred-nc@ entry for consistency with the new primary model (confirm with user first)
    status: pending
isProject: false
---

## Why the existing playbook needs rewriting

I already wrote [workspace/contracts/06-google-oauth-dual-identity-setup.md](workspace/contracts/06-google-oauth-dual-identity-setup.md) in a prior turn, but it only documents the OAuth-consent model (per-identity `client_secret.json` + refresh token). Since then, your other session has made real, uncommitted changes across this repo switching the target architecture to **Google Workspace domain-wide delegation**:

- [workspace/skills/google_cal_skill/gcal.py](workspace/skills/google_cal_skill/gcal.py) — rewritten: OAuth refresh-token flow removed entirely (`generate_auth_url`, `exchange_code_for_token` deleted), replaced with `service_account.Credentials.from_service_account_info(..., subject=GOOGLE_DELEGATED_USER)`
- [workspace/skills/google_workspace/scripts/gmail_inbox.py](workspace/skills/google_workspace/scripts/gmail_inbox.py) — same pattern
- [workspace/skills/google_cal_skill/SKILL.md](workspace/skills/google_cal_skill/SKILL.md) and [workspace/skills/google_workspace/SKILL.md](workspace/skills/google_workspace/SKILL.md) — env vars changed from `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` to `GOOGLE_SERVICE_ACCOUNT_JSON` + `GOOGLE_DELEGATED_USER`
- [bin/secure-env.sh](bin/secure-env.sh) line 170 — commented-out fetch for `openclaw-igorbot/google-service-account` -> `GOOGLE_SERVICE_ACCOUNT_JSON`
- [credentials/aws-secrets-setup.sh](credentials/aws-secrets-setup.sh) line 80 — creates the `openclaw-igorbot/google-service-account` secret placeholder (`[NOT YET PROVISIONED]`)

You confirmed: `scrapmanagement.com` is Google Workspace Business+ and you have super-admin access, and you want a documented way to revert to the old per-identity OAuth model if domain-wide delegation doesn't pan out (it's being configured live in another session right now).

## What the rewritten playbook will contain

Single file, rewritten in place: [workspace/contracts/06-google-oauth-dual-identity-setup.md](workspace/contracts/06-google-oauth-dual-identity-setup.md)

1. **Status snapshot** — current uncommitted state (the 5 files above), so the playbook accurately reflects "where things stand," not stale assumptions.

2. **Primary path: domain-wide delegation** (matches your other session's direction)
   - Remaining steps to finish wiring `ib@scrapmanagement.com` read-only only (nc@ stays deferred, per your answer): create/confirm service account + JSON key in Google Cloud Console, authorize its Client ID in `admin.google.com` -> Security -> API Controls -> Domain-wide Delegation with **read-only scopes only** (`gmail.readonly`, optionally `drive.readonly`/`calendar.readonly`), store the JSON key as `openclaw-igorbot/google-service-account`, uncomment the `bin/secure-env.sh` line, set `GOOGLE_DELEGATED_USER=ib@scrapmanagement.com`, restart gateway, verify.
   - **Important nuance to call out explicitly**: domain-wide delegation scopes are authorized once per service account, not per impersonated mailbox — Google's admin console has no way to say "read-only for ib@, full access for nc@" on the same service account. So "read-only for ib@" will be enforced by *application-level discipline* (the skill only ever calling read endpoints for that identity), not a hard Google-side permission boundary. This becomes a real decision point when `nc@` is picked back up later: either (a) widen this same service account's authorized scopes to include send/modify (which would then also make ib@ technically capable of those calls at the Google layer), or (b) create a second, separately-scoped service account for nc@'s full access and keep this one permanently read-only-scoped. Flagged for later, not decided now.

3. **Fallback / revert path: per-identity OAuth consent** (the original plan, preserved)
   - If domain-wide delegation is abandoned: revert `gcal.py` and `gmail_inbox.py` to their pre-service-account versions (via `git checkout` once the current changes are committed, or by hand using the diff as reference), reinstate `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REFRESH_TOKEN` env vars, and use the two client-secret files you already have saved outside the repo (`google_oauth_igor 2.json` for `ib@`, project `l-cto-481000`; `google_oauth_IgorBot.json` for `nc@`, project `clear-router-481000-j6`) to run the interactive consent flow as previously outlined (build consent URL, you log in and approve, exchange code for refresh token, store in AWS).
   - Note: this path does not depend on Workspace admin access at all, so it also works if `scrapmanagement.com` ever moves off Workspace Business+.

4. **Deferred identity note carried forward**: `nc@scrapmanagement.com` / IgorBot's own inbox stays out of scope for both paths until `ib@` read-only is proven working, matching the existing [memory-bank/tasks.md](memory-bank/tasks.md) entry (light reword only, to say "domain-wide delegation" instead of "OAuth client" if it reads oddly next to the new primary path — no substantive change).

5. Explicit banner at the top: **documentation only — no code, secrets, or cloud-console changes are made by writing this file.**

## Scope boundary

- Only [workspace/contracts/06-google-oauth-dual-identity-setup.md](workspace/contracts/06-google-oauth-dual-identity-setup.md) gets rewritten.
- No touching `gcal.py`, `gmail_inbox.py`, `secure-env.sh`, `aws-secrets-setup.sh`, or any SKILL.md — those are your other session's in-progress work and are left exactly as-is.
- No AWS calls, no browser OAuth flow, no git commits/pushes.
- [memory-bank/tasks.md](memory-bank/tasks.md) gets at most a one-line reword for consistency — optional, will confirm before touching.