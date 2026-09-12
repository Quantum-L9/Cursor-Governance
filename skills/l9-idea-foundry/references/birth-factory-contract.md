# Repository factory handoff contract

Load this reference when Foundry reaches template-fit, exact-state freeze, birth-payload compilation, local birth, or remote birth.

## Authority boundary

`Quantum-L9/l9-repo-template` owns the non-Constellation Python birth contract. Foundry owns the product staging repository and its idea-origin evidence. **Foundry never authors `l9.birth-payload/v1`.** The factory compiler emits that evidence from the clean committed source snapshot.

At every real handoff, inspect the current factory checkout instead of treating this reference as eternal syntax. The observed 2026-09-11 contract had:

- factory role: `non-constellation-python-template`;
- sibling node factory: `Quantum-L9/L9-Node-Template`;
- sibling Constellation dependency factory: `Quantum-L9/Constellation.PackageTemplate`;
- authoritative `repository_shape`: `pyproject.toml`, `.l9/architecture.yaml`, `src`, `tests`, `scripts/inventory_check.py`;
- compiled contract schema: `l9.birth-payload/v1`;
- birth states: `LOCAL | PROVISIONAL | BORN | QUARANTINED`;
- birth command ends at `PROVISIONAL` when remote succeeds; `BORN` requires later canonical CI on a real pull request.

## Required live probe

Before calling a Foundry payload `BIRTH_READY`, bind the current factory checkout and inspect:

1. `.l9/architecture.yaml`;
2. `scripts/birth-runner/payload-ownership.yaml`;
3. `scripts/birth-runner/schemas/birth-payload.schema.json`;
4. `scripts/birth-runner/compile_birth_payload.py`;
5. `scripts/birth-runner/new_repo.py`;
6. `docs/ops/REPO_BIRTH.md` and the birth-runner README for operator syntax.

Use `scripts/probe_birth_factory.py` to record the machine-relevant facts. A factory probe is evidence, not copied factory policy.

## Birth-payload law

The birth payload contract answers only: **which bytes, from which immutable source snapshot, did the product contribute?**

It must not contain Foundry product intent, desired CI, repo class, target repository identity, template version, organization policy, birth timestamp, absence declarations, or birth provenance. Those belong to other authorities.

The compiled contract must live outside the source tree it describes. Putting it inside the source makes the manifest circular.

Qualification command shape:

```bash
python3 scripts/qualify_birth_handoff.py /path/to/staging \
  --freeze-receipt /tmp/product.foundry-freeze.json \
  --repo-template-root /path/to/l9-repo-template \
  --source-repository Quantum-L9/<staging-source-identity> \
  --out-dir /tmp/foundry-birth-qualification
```

The qualifier first reruns Foundry birth-ready validation, probes the live factory, invokes the factory's own compiler with `--require-mode authoritative`, and checks that the factory manifest names the same source revision/tree and exact repository-shape classification.
It then reprobes the factory and requires the same revision, tree, and bound contract-file digests, closing the probe-to-compile drift window.

## Local birth law

Factory compilation proves source admissibility. It does **not** prove a newborn passes the chassis, org profile, lock, lint, type, tests, provenance, and inventory gates.

Before any remote creation, run the factory's own no-remote birth path. `scripts/qualify_birth_handoff.py --run-local-birth` may do this only when the real template checkout and required organization-profile source are available. Preserve the factory's actual result.

Foundry states:

- `BIRTH_READY`: Foundry exact-state validation + live factory compiler qualification PASS.
- `LOCAL_BIRTH_PASS`: actual factory local/no-remote birth PASS.
- `PROVISIONAL_REPOSITORY`: remote factory birth observed as PROVISIONAL.
- `QUARANTINED`: remote factory birth observed as QUARANTINED.
- `BORN`: **not produced by repository birth**; requires the later canonical-CI event defined by the factory.

## Drift and invalidation

- Staging source changed after freeze → invalidate freeze, factory compile, and local birth evidence.
- Factory compiler/schema/ownership contract changed → keep product authority, but invalidate factory qualification and rerun it.
- Organization profile changed → rerun local birth before remote birth.
- Template fit changed → route to the current sibling factory or stop `TEMPLATE_MISMATCH`.

## Forbidden moves

- hand-writing or patching `l9.birth-payload/v1`;
- copying `new_repo.py`, payload ownership, org materialization, CI distribution, or provenance logic into Foundry;
- inventing a Python package to coerce an incompatible product into the template;
- putting the compiled birth contract inside the source repository;
- claiming `BORN` because a repository exists;
- retrying remote publication to hide a `QUARANTINED` result.
