# Governance friction brief: Odoo campaign, 2026-11-13 to 2026-11-16

Each entry records what happened, the evidence observed, the cost, and the fix this
brief proposes. "Observed" means a tool output or a log line seen in this session;
"inferred" is labelled as such. Entries are ordered by cost to the operator.

## F1. GitHub Actions could not check out the repository for about 8 hours

- **Observed.** From 2026-11-16 03:40 to 11:32 UTC, every CI job on #513 and #514
  failed in `actions/checkout` with `remote: Repository not found` (exit 128). The
  job's own `GITHUB_TOKEN Permissions` block listed `Contents: read`. The L9
  Analysis runs sat `queued` and never started. One re-run failed identically.
  GitHub's status page reported "All Systems Operational". Runs at 11:32 checked
  out normally, after the PR was closed and reopened.
- **Root cause: Unknown.** The session could not read
  `repos/{o}/{r}/actions/permissions*`: the session proxy answered "Access to this
  GitHub Actions path is not permitted through this proxy". Billing, Actions
  settings and an account-side event are all candidates; none was confirmed.
- **Cost.** The two fix PRs were blocked for 8 hours; the operator was told three
  times; three scheduled check-ins found no change.
- **Proposed fix.**
  1. Add a degraded-mode row to `docs/DEGRADED_MODE_CONTRACT.md`: when checkout
     fails with "Repository not found" while the token shows `Contents: read`, the
     cause is outside the repository. The agent says so once on the PR and asks the
     operator for exactly three checks (Actions settings, Actions billing, account
     email). This session improvised that path.
  2. Ask whether the session gateway can expose `GET actions/permissions` and
     `GET actions/permissions/workflow` read-only. Both are diagnostics, not
     mutations.

## F2. Odoo.sh cannot hold a build-persistent process environment

- **Observed (Cursor over SSH, both Odoo.sh hosts).** The Odoo workers run in a
  namespace the SSH shell cannot see. The shell environment carries only
  `ODOO_STAGE` and `ODOO_VERSION`. `~/.config/odoo/odoo.conf` holds a single option
  (`dbfilter`). Neither project Settings nor branch Settings has an
  environment-variable field. The Odoo.sh FAQ documents only those two variables.
  Verdict: **M3**, no persistent mechanism.
- **Cost.** Odoo cannot load `GATE_URL` or `L9_SIGNING_*`, so the Odoo↔Gate
  integration cannot be switched on, however much code is ready.
- **Proposed fix.** An ADR in the Odoo repository on where Odoo's Gate settings
  live (see `SESSION_BRIEF.md` §3), plus a dated row in `DEGRADED_MODE_CONTRACT.md`
  recording that Odoo.sh has no persistent process environment. The fact belongs
  in governance because every L9 consumer hosted on Odoo.sh will hit it.

## F3. The `Production` ruleset rejects Odoo.sh's "Merge" button

- **Observed.** The ruleset "Protect Staging & Production" requires a pull request,
  forbids non-fast-forward pushes, and requires `Ruff Lint & Format`,
  `Static Analysis`, `Pure Python Tests` and `CI Gate Result`. Odoo.sh "Merge"
  pushes a merge commit directly, so GitHub answers "Repository rule violations
  found — Changes must be made through a pull request". Odoo.sh "Rebase and Merge"
  works because it opens a PR (#516), but it rebases about 300 commits. Odoo.sh
  acts under the operator's GitHub identity and is not listed under ruleset
  "Apps", so no narrow bypass exists.
- **Decision (operator, 2026-11-16).** Accepted. For each promotion the operator
  disables the ruleset, merges, and re-enables it.
- **Proposed fix (optional, removes the toggle).** Promote with a pull request
  `Staging → Production` merged with "Create a merge commit". This gives the same
  result as the Odoo.sh button, with the required checks run. Make it a CTO
  procedure: open the PR, wait about 5 minutes for checks, merge with
  `merge_method=merge`. Never add a bypass for the operator's own identity:
  agents act as that identity too (F7).

## F4. Copilot reviews only the first push of a PR

- **Observed.** On #517, Copilot reviewed commit `db2f8f5` and raised a finding
  that was correct. The fix and the Bales work (`bb467cd` through `19b9588`) were
  not re-reviewed. `POST pulls/517/requested_reviewers` with
  `copilot-pull-request-reviewer[bot]` or `Copilot` returned `requested_reviewers: []`.
- **Cost.** The PR merged without a bot review of its largest commit. The operator
  had to relay a Copilot comment by screenshot because the CTO only subscribed to
  PR activity late.
- **Proposed fix.**
  1. The CTO subscribes to every lane PR the moment it is published
     (`subscribe_pr_activity`); bot findings then reach the CTO before the operator.
  2. Find out how to trigger a Copilot re-review from the API, or record that it
     cannot be triggered so nobody retries.
  3. When the final head has no bot review, the merge report says so explicitly.
     This session did.

## F5. Review bots on free tiers produce no review

- **Observed.** Codex replied "You have reached your Codex usage limits for code
  reviews". CodeRabbit replied "Review limit reached… costs up to $8.00" and
  "Your organization has reached its limit of developer seats".
- **Proposed fix.** Decide which bot is the reviewer of record for this repository
  and fund it, or drop the others so their placeholder comments stop waking the
  CTO.

## F6. `requirements-dev.txt` drifted from `ci.yml`

- **Observed.** `make venv` installs only `requirements-dev.txt`. `ci.yml` also
  installs `pyyaml==6.0.3` and `pre-commit==4.7.0` (pure-python-tests) and
  `lxml==6.0.2` (static-checks). A swarm agent could not run the suite. Fixed in
  #513.
- **Proposed fix.** Add a CI test asserting that every `pip install` pin in
  `ci.yml` appears with the same version in `requirements-dev.txt`. Without it the
  drift returns with the next CI edit.

## F7. Agents act under the operator's GitHub identity

- **Observed.** The CTO's PR replies, merges and pushes appear as `cryptoxdog`. A
  GitHub notification for the CTO's own reply woke the CTO as if it were a
  reviewer comment.
- **Consequence.** No ruleset bypass can separate the operator from the agents
  (F3). Self-authored comments re-enter the event stream.
- **Proposed fix.** Keep agents on the operator's identity for now, since it is
  sanctioned by `62-github-openclaw-authority`, but tag every agent-authored body
  with the existing Claude Code footer. Teach the PR-activity handler to drop
  events whose body carries the footer.

## F8. Ownership of Gate deploy and policy was routed through three CTOs

- **Observed.** CTO EIE first named CTO State Node as Gate deploy owner; CTO State
  Node then redirected to CTO CEG, citing an operator ruling. Two messages from
  this session reached the wrong owner before the third reached CEG.
- **Proposed fix.** One owner table for Constellation services (code, deploy,
  caller policy, secrets), kept in governance and read before any cross-CTO
  request. Today the routing lives only in messages.

## F9. Directive delivery raced the agent's publish

- **Observed.** Two scope corrections were sent at 12:07–12:08 UTC with default
  priority. The agent published at about 12:21 without having read them, then
  correctly refused to widen scope after publishing (`CTO-BLOCKER`). The CTO had
  to re-open the lane.
- **Proposed fix.** Covered in `CTO_SWARM_OPERATIONS_BRIEF.md` (A4 and A5): send
  scope corrections with `priority: now`, and give the pool contract an explicit
  re-assign verb.

## F10. Odoo.sh build behaviour that cost turns

- **Observed.** A Staging "Rebuild" replaces the Staging database with a fresh copy
  of Production. That made the rebuild the most faithful rehearsal of a promotion,
  but it erased hand-set ICPs. A build pushed while another operation was running
  was **dropped** ("Operation ignored. Another operation is in progress"), so #512
  never built until a manual Rebuild.
- **Proposed fix.** Put both facts in the `plasticos-odoo-sh-deploy` skill. After
  every Staging merge, check that the card's commit equals the branch head before
  treating it as tested.

## F11. Worker restarts dropped pending approvals

- **Observed.** Several `archive_session`, `send_message` and `delete_trigger`
  calls came back "did not run" after a worker restart, and one `archive_session`
  was interrupted mid-approval.
- **Proposed fix.** None at repository level. Calls must be idempotent and
  re-issued after a restart, which this session did. Recorded so the next CTO
  expects it.

## F12. Odoo runtime tests never ran

- **Observed.** The operator's constraint ("no Enterprise tests") held for the
  whole campaign. Cloud `make pr` also skips install-smoke by default. Migrations,
  write guards and the Bales merge therefore had their first real run on the
  Staging rebuild, and will again on Production.
- **Proposed fix.** One scheduled Enterprise runtime window per campaign, set when
  the campaign launches, so the gap is closed on a timetable rather than carried as
  risk.
