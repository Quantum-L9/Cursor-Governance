# ADR-0053: Infisical is the secret store; AWS Secrets Manager is the Cursor login seed only

## Status

Accepted

## Date

2026-11-02

## Context

Secrets moved from AWS Secrets Manager (`openclaw-igorbot/*`) to Infisical
project `cursor-governance` in stages. Code followed: Claude surfaces bind
every key from Infisical with no AWS on the path (`capability_bind.py`,
SessionStart, the vault MCP bridge), and the operator adds new secrets
(Context7, SonarCloud, Semgrep, …) to Infisical. The migration was recorded
only as an append-only `AGENTS.md` amendment (INFISICAL_MACHINE_IDENTITY_V1,
2026-09-24), so the higher authorities kept the old model:

- `CANONICAL_LAW.md` §14 required "the registered AWS secret ref" and named
  AWS SM the secrets SSOT; §12 sent secret resolution to AWS.
- Rule 62 and `AGENTS.md` §8 restated it; the secrets README told operators to
  add secrets in AWS first, then sync.
- The skill was named `l9-aws-secrets`, and its router route fired on the bare
  word "infisical", so agents were steered to an "AWS" skill whenever secrets
  came up.
- A legacy ref resolved only through the AWS resolver; the ref → Infisical
  name map lived inside the one-way port script.

## Decision

1. Infisical project `cursor-governance` is the single store for agent secrets
   on every surface (`CANONICAL_LAW.md` §14.1, `AGENTS.md`
   SECRETS_INFISICAL_STORE_V1). New secrets go there and into `root_env_keys`.
2. AWS Secrets Manager stays only as the Cursor / operator login seed for the
   Infisical machine identity. No secret is added to AWS; no object is deleted.
3. The skill is renamed `l9-secrets`, with an action-scoped description and
   route.
4. `ops/secrets/legacy_refs.py` owns the legacy ref → Infisical name map;
   `capability_bind.py --check` accepts a legacy ref; `make secrets-check`
   checks Infisical, and the AWS tools move to `secrets-aws-*` targets.

## Consequences

- Agents following a ref or the law land on Infisical, not AWS.
- Cursor SessionStart still needs AWS for its login seed until a Cursor-native
  Infisical login replaces it (out of scope; operator decision 2026-11-02).
- `CANONICAL_LAW.md` §12/§14 and `AGENTS.md` §8 remain as history; §14.1 and
  SECRETS_INFISICAL_STORE_V1 supersede them.
