# Source Acquisition Contract

Use this contract only for `PROBE_CAPABILITIES`, `LOCK_SOURCE_IDENTITY`, and `INVENTORY_DONOR`.

## Ownership

Harvest owns **admission, immutable source identity, and deterministic inventory**. It does not own provider authentication, network session management, or connector implementation.

Remote transport is supplied by the active runtime through an existing repository client, HTTPS client, or connector. Normalize that evidence through `contracts/source-acquisition.schema.json` and `scripts/inventory_source.py --acquisition <receipt>` before inventory or semantic reconstruction.

Do not add GitHub-, Cursor-, Claude-, ChatGPT-, or provider-specific authentication logic to the harvest skill.

## Source classes

- `local_path`: local file or directory; hash bytes directly.
- `repository_checkout`: local repository checkout; pin the observed revision outside semantic interpretation, then hash tracked evidence used by the harvest.
- `remote_repository`: repository observed through a connector or repository client. Require an immutable revision and hashed inventory before PASS.
- `url`: remote document/resource. Require response identity (`ETag` or `Last-Modified`) or a content SHA-256.
- `document_or_pack`: supplied artifact or archive; inventory contained evidence without executing donor content.

## Transport order

Use the strongest available existing path:

1. Existing local checkout at an immutable revision.
2. Existing runtime repository connector/client pinned to an immutable revision.
3. Existing HTTPS client with response identity/content digest.
4. Otherwise return `BLOCKED`.

Do not silently convert a remote repository into an anonymous local evidence folder. If a connector materializes content, preserve the remote repository identity and transport in the acquisition receipt.

## Verification levels

- `CONTENT_REHASHED`: the deterministic script re-read materialized bytes and matched the receipt inventory.
- `CONTENT_HASH_DECLARED`: the runtime supplied per-artifact SHA-256 values but bytes were not locally re-read by the script.
- `IDENTITY_ONLY`: source identity is known but content inventory is not closed. This is insufficient for exhaustive remote-repository harvest completion.

A lower verification level must never be described as a higher one.

## Failure behavior

Fail closed when an immutable remote repository revision is absent, a materialized root is inaccessible, declared hashes do not match materialized bytes, or a URL lacks response identity/content digest. Preserve the limitation in the receipt and do not fabricate local checkout proof.
