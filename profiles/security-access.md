# Security & Access — Least Privilege, Secrets, and Auth Correctness

## Principles
- **Least Privilege:** Request the smallest scope necessary.
- **No Secrets in Output:** Never echo API keys/tokens. Redact with `****…****` policy.
- **Single Source of Truth:** `environment/n8n-env-variable-audit.csv` defines expected keys.

---

## Credentials & Env
- Keys must live in `.env` (or the platform’s secret store), not in workflow JSON.
- If a required key is missing, trigger env sync (Option C) and proceed.
- Map environment profiles (dev/staging/prod) explicitly; prevent mixing.

---

## Authentication Patterns
- Follow the **correct method** for providers documented in workspace guides (e.g., Supabase: service role vs anon keys, JWT handling).
- Validate that nodes use the correct credential type and scope.

---

## Secret Scanning & Redaction
- Scan generated code/docs for patterns resembling secrets; redact automatically.
- If scanning finds a hard-coded secret, replace with env reference and log remediation.

---

## Approvals
- Only **security‑labeled** steps (e.g., permission escalations, production key rotation) may require human approval.
- Everything else proceeds automatically once fixed/redacted.
