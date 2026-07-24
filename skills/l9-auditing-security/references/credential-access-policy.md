<!-- L9_META
l9_schema: 1
parent: l9-auditing-security
origin: migrated-from profiles/security-access.md
sources: [profiles/security-access.md]
tags: [security, credentials, least-privilege, redaction]
status: active
/L9_META -->

# Credential and Access Policy

Least-privilege, credential rotation, and redaction rules for governance and agent operations.

## Authoritative documents

| Concern | Document |
|---|---|
| Credential handling policy | [learning/credentials-policy.md](../../../learning/credentials-policy.md) |
| API key verification procedure | [security/api-key-verification.md](../../../security/api-key-verification.md) |
| Audit log of security findings | [security/security-audit.md](../../../security/security-audit.md) |

The policy document is the source of truth. This reference exists to state the operating rules an
agent must follow without reading all three.

## Rules

- **Least privilege by default.** Request the narrowest scope that completes the task. An admin-scoped
  key used for a read is a finding, not a convenience.
- **Credentials come from the environment.** Read from `.env` or the secret store at the moment of
  use. Never reuse a value pasted earlier in a conversation, never hardcode, never commit.
- **Never echo a secret.** Do not print, log, or quote a key value — not even truncated. Confirm
  *which variable* was used, not what it contains.
- **Verify scope before blaming the service.** A key of the wrong class (for example an admin key
  where an inference key is required) produces authentication errors that look like outages.
- **Rotate on exposure.** Any credential that appears in a transcript, log, or diff is compromised and
  must be rotated — regardless of whether it was used.

## Verification before an API call

Confirm the variable is set and non-empty, confirm its scope matches the endpoint, then call. If
authentication fails, check key class before retrying — repeated calls with a wrong-class key produce
identical failures.

## Not implemented

The original profile claimed automatic redaction, automatic token refresh, and continuous audit
logging. None of that is wired. Redaction and rotation are **manual disciplines**, and
`security-audit.md` is written by hand.
