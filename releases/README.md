# Organization Policy Releases

This directory defines the release-record contract for
`ORG_INVARIANTS.yaml`.

It does not contain fabricated release receipts.

## Release identity

A release record binds:

- policy ID;
- semantic policy version;
- immutable Git commit;
- policy digest;
- policy-schema digest;
- assertion-registry digest;
- approval reference;
- compatibility statement.

## Immutability

Blocking consumers must not treat a mutable branch such as `main` as an
immutable release.

The canonical commit must be a full 40-character Git commit identifier.

## Digests

A SHA-256 digest proves that the bytes or canonical payload used to calculate
the digest match.

It does not prove:

- who approved the content;
- who published it;
- whether the signer was authorized;
- whether the release process was followed.

## Signatures and attestations

A signature or attestation adds identity and provenance evidence.

This repository must not claim signing or attestation is operational until the
corresponding infrastructure and verified evidence exist.

## Release production

A release record should be produced only after:

1. policy and schema validation passes;
2. assertion references resolve;
3. repository tests pass;
4. independent approval is recorded;
5. the immutable commit is known;
6. digests are calculated from committed files;
7. compatibility impact is documented.

## Versioning

Use semantic versioning:

- patch for non-semantic corrections;
- minor for backward-compatible additions;
- major for incompatible changes.

A version number must not be reused for different content.

## Downstream consumption

Platform-binding, assurance, CI, and consumer repositories may consume an
approved release record.

They must not reinterpret it as authority to redefine the policy.
