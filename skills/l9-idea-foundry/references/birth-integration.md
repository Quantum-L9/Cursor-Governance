# l9-repo-template birth integration

Load this reference at template-fit, factory qualification, local birth, remote birth, or when factory drift is suspected. Also load [birth-factory-contract.md](birth-factory-contract.md).

## Owner boundary

`Quantum-L9/l9-repo-template` is the sole non-Constellation Python birth owner. Foundry realizes and freezes the product staging repository. The factory owns:

- payload ownership semantics;
- `l9.birth-payload/v1` compilation and validation;
- birth orchestration;
- identity stamping and lock finalization;
- organization profile materialization;
- birth provenance;
- canonical CI enrollment/attestation;
- remote repository creation.

Foundry must not vendor or reinterpret those mechanisms.

## Current handoff sequence

```text
CODE_REALIZED
  -> FOUNDRY_INDEX
  -> PAYLOAD_FREEZE
  -> FACTORY_CONTRACT_PROBE
  -> FACTORY_COMPILE_PASS
  -> BIRTH_READY
  -> LOCAL_BIRTH_PASS
  -> optional REMOTE_BIRTH
  -> STOP BEFORE DEPLOYMENT
```

### 1. Exact Foundry state

```bash
python3 scripts/validate_foundry_payload.py <staging>
python3 scripts/emit_foundry_index.py <staging> --inventory-digest ... --plan-ref ... --plan-digest ...
# commit exact tree
python3 scripts/emit_freeze_receipt.py <staging> --inventory-digest ... --plan-ref ... --plan-digest ... --out /tmp/freeze.json
python3 scripts/validate_foundry_payload.py <staging> --birth-ready --freeze-receipt /tmp/freeze.json
```

### 2. Probe the current factory

```bash
python3 scripts/probe_birth_factory.py /path/to/l9-repo-template --out /tmp/factory-probe.json
```

Require the checkout to be clean. Bind its HEAD/tree and the digests of architecture, ownership, schema, compiler, engine, and birth docs.

### 3. Factory-owned payload compilation

```bash
python3 scripts/qualify_birth_handoff.py <staging> \
  --freeze-receipt /tmp/freeze.json \
  --repo-template-root /path/to/l9-repo-template \
  --source-repository Quantum-L9/<source-identity> \
  --out-dir /tmp/qualification
```

The qualifier invokes the factory's own `compile_birth_payload.py`. It never constructs the manifest itself. The output directory must be outside staging because the compiled contract describes the staging bytes and cannot include itself.

`BIRTH_READY` means both Foundry exact-state validation and factory compilation passed for the same source HEAD/tree.

### 4. Local birth

Before any remote creation, run the real factory's no-remote path. When prerequisites exist, the qualifier can invoke it with `--run-local-birth`; otherwise invoke the current factory command directly. Preserve actual output and receipt.

`LOCAL_BIRTH_PASS` requires observed factory success. A fake/stub runner is not evidence.

### 5. Remote birth

Remote birth is optional and separately authorized. Re-read the current factory syntax immediately before running it. Preserve actual factory state:

- `LOCAL`: local assembly/validation only;
- `PROVISIONAL`: published and enrolled, first PR still must prove canonical CI;
- `QUARANTINED`: published but required remote evidence failed/missing;
- `BORN`: later canonical-CI success on a real PR, not repository existence.

A remote repository is never production deployment.

## Template fit

Use `l9-repo-template` only when current architecture says the product fits its non-Constellation Python responsibility. Read sibling factory declarations from the live `.l9/architecture.yaml`; do not hardcode routing forever.

Never create a meaningless Python package merely to satisfy repository shape. Stop `TEMPLATE_MISMATCH` or route to the canonical sibling factory.

## Invalidation

| Changed evidence | Earliest invalid layer |
|---|---|
| idea authority / compiled intent | authority or blueprint |
| plan baseline / plan digest | planning |
| tracked staging bytes | freeze |
| factory revision/schema/ownership/compiler | factory qualification |
| organization birth profile | local birth |
| remote rules/attestation state | remote birth observation |

## Absolute prohibitions

- no Foundry-authored `l9.birth-payload/v1`;
- no birth contract inside source tree;
- no copied birth engine or payload ownership law;
- no copied org profile/CI enforcement;
- no remote birth before local birth pass;
- no `BORN` claim from repository creation;
- no deployment in Foundry.
