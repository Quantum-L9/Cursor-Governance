<!-- --- L9_META ---
l9_schema: 1
artifact_type: learning
component: credentials_policy_security_layer
tags: [learning, credentials, policy, security, governance]
retrieval: on_demand
status: active
--- /L9_META --- -->

# Credentials Policy — 10X Governance Security Layer

## Objective
Ensure that all credentials within the environment comply with least-privilege principles, correct scoping, and periodic rotation requirements.

## Governance Integration
- `.cursor/rules.json`: Enforces environment credential sync.
- `.env` and `environment/*.csv`: Primary verification source for key scope, status, and rotation dates.
- `.cursor/profiles/security-access.md`: Governs access and redaction.

## Rules
1. **Scope Control:** Each credential must specify `SCOPE=[service|internal|restricted]`.
2. **Rotation:** Keys must rotate every 90 days or sooner.
3. **Storage:** No plaintext credentials allowed in workflows or scripts.
4. **Redaction:** Any detected raw keys are replaced with token references automatically.

## Anomaly Detection
- Scans L9 VPS environment variables for anomalies using reasoning logic.
- Identifies mismatched, leaked, or invalid credentials.
- Performs autonomous remediation via `api-key-verification.md` and `env_validator.py`.

## Logging
Results stored in `/logs/security_credential_audit.log`.

## Behavior
- Non-blocking and continuous.
- Automatic redaction and credential correction.
- Updates results and recommendations without user interruption.
