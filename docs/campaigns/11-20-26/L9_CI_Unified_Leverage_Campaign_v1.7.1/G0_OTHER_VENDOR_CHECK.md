# G0 extension: minimal account verification for other tools

**Read-only, one screen at a time, only when source/logs cannot answer.** This extends `OPERATOR_VERIFY_FIRST.md` without adding a mandatory tour of every dashboard. CTO first compiles source + run evidence and asks for one highest-impact missing vendor fact at a time; focus on Codecov and GitGuardian because of proven false-green CEG runs. CodeQL/Sonar's pre-existing three-screen workflow retains precedence. If account lacks scope, write `UNKNOWN` and continue on independent engineering.

1. **GitGuardian**: authenticated dashboard for organization membership, connected GitHub repositories (CEG and EIE), paid plan/scan quota, secret scanning integration status, incident count, and whether native PR protection is enabled. Operator must not share API keys. If no connected project, note that ggshield CLI scan execution is independent of dashboard incident persistence unless configured with native features.
2. **Codecov**: authenticated app for `Quantum-L9/Cognitive.Engine.Graphs` project; determine activation, required upload token/OIDC support, last *accepted* upload and quality/patch coverage status. Existing hosted CEG #508 Codecov upload was rejected. Do not request or show token value; request only presence/entitlement and whether upload authentication can be made available to GitHub.
3. **Gitleaks**: only if relevant to unresolved EIE license restriction. Verify app license/subscription account and whether Dependabot events have an authorized secret strategy. Do not presume every Dependabot PR is safe to skip.
4. **Dependabot/GitHub security**: use GitHub UI only if connector cannot read alerts/permissions. Confirm dependency graph, Dependabot alerts, code scanning and secret scanning enabled for named repositories; distinguish repo from org admin. Use one account screen for the most important unknown rather than six separate UI tours.
5. **Codecov/CodeRabbit/Perplexity/Sonar overlap**: only ask about paid spend/seat once if important; determine whether Codecov/LLM review is separately billed, actual projects/seats/limits, and avoid purchases. `UNKNOWN` is a legitimate endpoint.

This is a follow-up to the single startup sequence in `OPERATOR_VERIFY_FIRST.md`,
not a second opening script. After the original three screens and actual source/run
inspection, summarize only work performed and ask for the most consequential
remaining account fact. If only this pack was read, say the pack records historical
false-green observations; do not claim current hosted runs were personally checked.
The extension performs no tests/scans or mutations. Independent authorized
engineering remains governed by the scoped G0 boundary in the parent document.

One user response per screen. After each: one-sentence observed state, next needed screen, or mark Unknown. Never ask for credentials, card numbers, invoices, or full screenshots containing secrets. No UI click that changes a setting until distinct approval. At G0 close produce short table: observed tool access, configured scope, actual executed scan, native accepted output, entitlement, cost, unresolved blockers and owner. G0 verification does not itself authorize vendor mutations.
