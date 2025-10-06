# Operational Health — Preflight, Health Checks, Monitoring

## Aim
Never ship broken or unmonitored workflows. Enforce preflight gates, runtime checks, and post‑deploy monitoring.

---

## Preflight Checklist (run before diff/deploy)
- Environment synced and validated
- Credentials resolvable and scoped correctly
- Required services reachable (basic ping or mock)
- Workflow validation (see Workflow Governance profile)
- Version header present and current
- Risk score acceptable

---

## Health Checks
- Define smoke paths and expected results.
- Record health snapshots during deploy.
- If a check fails, auto‑remediate when safe (reconnect, retry with backoff, repair known node issues) and proceed; otherwise fail fast with a clear path to fix.

---

## Monitoring
- Capture success/failure counts, latency buckets, and error types (redacted).
- Emit a small **Operations Summary** on deploy completion.

---

## Rollback & Checkpoints
- Maintain a checkpoint before risky changes.
- On failure above threshold, rollback to last healthy workflow version.
- Log the rollback decision in the Delivery Log.
