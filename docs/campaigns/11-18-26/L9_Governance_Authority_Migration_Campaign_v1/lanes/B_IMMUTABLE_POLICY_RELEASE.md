```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/.github
  read_only:
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-core
  unlisted_repositories: no_access
```

# B: issue and verify authentic immutable policy release

**Executor:** the activating CTO session, same single `.github` writer slot as A, after A is merged. A pool agent must not clone, branch, or push this repository. **No simultaneous A/F modification of the same paths.** Source must be read back from the merged `.github` SHA, never from a pending worktree or the mutable `main` alias. If the signer or attestor is absent, stop at `BLOCKED`. Do not publish an unsigned blocking release. See `09_EXECUTION_BINDING.md`.

## Work contract

- Inspect `.github` release/ADR and actual signing/in-toto mechanisms; identify source-of-signature authority. Discover any existing compatible signed policy release infrastructure; reuse instead of introducing a second issuer or vault.
- Produce actual release metadata at current owner: canonical repository/path/immutable source SHA, policy ID/version, exact canonicalized payload digest, policy schema digest, assertion registry digest, compatibility, referenced owner approval, release identity/time and predecessor. Never make a release record point to the future SHA of the commit which contains itself; follow an observed two-step/attestation process where necessary.
- Verify trust: correct accepted signer/identity and signature/attestation integrity, binding to exact policy source and release metadata. A hash comparison is required but not sufficient. Use the selected owner's actual commands/tools only after inspecting the current source; no unverified generated command or claimed signing key.
- Release must be retrievable and re-verifiable by a read-only consumer at an immutable coordinate. Re-check policy's integrity contract and in-toto requirement. Derive consumer-input acceptance fixtures for valid, tampered and changed-issuer cases without turning the verifier into global authority.
- Open reviewable release PR through verified `make pr` and obtain exact permitted owner merge when required; capture final merged release SHA and signed artifact identity. A failure to obtain signer/attestor/owner authority stays `BLOCKED`; never downgrade release policy to unblock rollout.

## Done

A separately verified, actually signed/attested release is present with exact SHA/path/digests/authorization and a consumer-readable, immutable reference. Only this proof unlocks C/M consumer activation and E live policy enforcement. A successful A PR alone does not unlock them.
