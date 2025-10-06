# Workflow Governance — n8n Validation, Diff, Deploy, Migrate, Test

## Objective
Ensure every n8n workflow is production-ready: validated, connected, reproducible, and monitored.

---

## Validation
- **Schema & UUID:** Workflows must include UUID and consistent naming.
- **Nodes:** Verify node versions; update if deprecated or insecure.
- **Connections:** Detect and repair broken links (use connection repair utilities if available).
- **Environment:** Confirm required env vars exist; if not, trigger env sync (Option C) and continue.
- **Emoji/Encoding Hygiene:** Normalize or remove problematic characters to avoid parse errors.

### Required Checks (minimum)
1. Workflow integrity (no missing nodes/links)
2. Required credentials present (no plaintext secrets)
3. Required env keys present and mapped
4. Input/Output contracts documented
5. Dry-run simulation passes (if API keys available)

---

## Diff
- Compare current vs previous exported version.
- Summarize: nodes added/removed/changed; credentials touched; env keys added/removed.
- Record in Delivery Log.

---

## Deploy
- Preflight health check must be green.
- If risk score > threshold (from Security/Operational), block deploy and auto-suggest fixes.
- On success, emit a Deployment Summary (version, timestamp, env profile).

---

## Migrate
- When moving between environments (dev → staging → prod), remap credentials and env profiles safely.
- Re-run validation; stop only for **security-authorized** blocks (no general pauses).

---

## Test
- Run unit-like node tests if defined; otherwise run a smoke path.
- Capture error traces with redaction; do not print secrets.

---

## Outputs
- Validation Report
- Diff Summary
- Deployment Summary
- Delivery Log entries
