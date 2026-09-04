# Emma V2.0 downstream birth workload

This folder is the handoff surface for the Emma V2.0 repository birth.

## Authority

The user explicitly authorizes the downstream Cursor agent to execute the canonical Quantum-L9 repository-birth path for `Quantum-L9/Emma` through:

`LOCAL -> PROVISIONAL -> first canonical CI validation PR -> BORN`

Production deployment is **not** authorized. Live OpenClaw activation, production secrets, DNS, production data migration, paid-service activation, and production traffic remain out of scope.

## Frozen Emma authority

- Emma frozen HEAD: `9612d73c5fc0778d9b6ba73f877bf88c1ca2262d`
- tracked-tree digest: `sha256:eade92f7a011936eeb32bce45f3ddb706dd03841f0fa99ff7a167dc3dd23bf6f`
- Foundry index digest: `sha256:bf7ca0be110e0142495158807b3bb6bd54d7785078ca9cf139e48c0822462ead`
- source inventory digest: `sha256:a90091dc6b8fcf855e57554c9c13faf58cafab68dabd3a8d70e7fa23ffa16eda`
- Plan Simple digest: `sha256:5df9e865858aa4152b0c9d4fbfa416673e2790f92586c2fcb74b2dfdd5d3b293`
- Foundry P8 gate: `BIRTH_READY: PASS`

## Canonical birth-owner evidence pins

- `Quantum-L9/l9-repo-template@13eb091cd842be545b3352ae608bc82f227db830`
- `Quantum-L9/.github@968398e59d647ba3e9f63dc9fbe23655ece54845`
- `Quantum-L9/Cursor-Governance@119d0df04347f1e45367cccfb68f494a753f4dca`

Before remote mutation, apply the moved-owner rule in `CURSOR_REPO_BIRTH_HANDOFF.md` and use the current canonical owner when relevant contracts have not invalidated the frozen payload.

## Payload

`payload/` contains a byte-preserving Base64 split of `emma-frozen-tree-for-cursor.tar.gz`.

Reconstruct with:

```bash
cd WIP/Emma-V2.0
cat payload/emma-frozen-tree-for-cursor.tar.gz.b64.part* | base64 -d > emma-frozen-tree-for-cursor.tar.gz
sha256sum -c payload/emma-frozen-tree-for-cursor.tar.gz.sha256
tar -xzf emma-frozen-tree-for-cursor.tar.gz
```

Expected archive SHA-256:

`84029aba7a26b6b39dd026552ae13e60b0cefdcae61500b604438a6c2a986cc8`

The reconstructed archive contains the 56-file frozen Emma working tree, P8 freeze evidence, P9 handoff/receipts, source authority, birth authority, and upstream pins.

The original larger conversation workload ZIP had SHA-256:

`816c53a5f3a0af8c3ed9cbeeeee191f58477938257decb8b1ab52bcf2e305ce1`

Historical nested phase ZIPs are not duplicated in this Git history. The birth-critical source, authority, evidence, and receipts are preserved in the reconstructed archive.

## Start here

1. Reconstruct and extract the payload above.
2. Read `05_BIRTH_HANDOFF/CURSOR_REPO_BIRTH_HANDOFF.md`.
3. Verify the frozen source and P8 freeze receipt.
4. Execute canonical LOCAL birth first.
5. Only after canonical `BIRTH: PASS / STATE: LOCAL`, execute remote birth through `l9-repo-template`.
6. Earn `BORN` only from current canonical CI evidence on the exact validation PR head.

Do not recreate or fork the repository birth engine and do not claim `BORN` from repository existence or root push alone.
