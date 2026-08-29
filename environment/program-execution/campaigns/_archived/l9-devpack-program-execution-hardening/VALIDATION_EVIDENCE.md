# Validation Evidence — l9-devpack-program-execution-hardening

Independent, reproducible receipts that the program's native Blueprint v2 +
Controller pair materializes and validates **green** at definition time. These
were produced against this repo's frozen core distribution at
`environment/program-execution/core`.

> Runtime state is **not** committed to the SSOT (see `README.md`). The pair
> below is materialized under the external program root and is reproducible from
> `PROGRAM_SOURCE.md` at any time by re-running the sequence.

## Source binding

| Field | Value |
|---|---|
| Immutable source | `PROGRAM_SOURCE.md` |
| Digest algorithm | sha256 |
| Digest | `aa1bc91c4c784aacd7be79e77149f776f95ef218439ec3f5e54dcab25314f78d` |
| Bytes | `86909` |

## Reproduction sequence

```bash
CORE=environment/program-execution/core

# 1. Instantiate the aligned Blueprint + Controller pair
python3 "$CORE/scripts/instantiate_pair.py" \
  --program-name "L9 Devpack Compiler Program Execution v2 Hardening" \
  --program-id l9-devpack-program-execution-hardening \
  --program-version 1.0.0 \
  --program-owner igor_beylin \
  --controller-name "L9 Devpack Hardening Controller" \
  --controller-id l9-devpack-hardening-controller \
  --controller-owner igor_beylin \
  --date 2026-08-10 \
  --target "$PROGRAM_ROOT"

# 2. Overlay the compiled Blueprint source set from PROGRAM_SOURCE.md
#    (the 19 `# FILE:` YAML/index sections + the EXECUTIVE_DECISION.md and
#     HANDOFF.md narrative patches), then regenerate the manifest:
python3 -c "import sys; sys.path.insert(0,'$BP/scripts'); \
  from instantiate import write_manifest; from pathlib import Path; \
  write_manifest(Path('$BP').resolve())"

# 3. Validate both sides in instantiated mode
python3 "$BP/scripts/validate_blueprint.py" "$BP" --mode instantiated
python3 "$CT/scripts/validate_controller.py" "$CT" --mode instantiated
```

## Results

```
# Blueprint (instantiated)
PASS
mode=instantiated

# Controller (instantiated)
PASS
mode=instantiated
```

The blueprint validator enforces (all satisfied): presence of all 33 required
sources; JSON-Schema conformance of the 18 registry files; exact
`EXECUTION_INDEX.required_sources` set; canonical v2 contract identifiers;
cross-file ID resolution (authorities, decisions, unknowns, risks, waivers,
evidence, workstreams, tasks, gates, waves, sources); DAG acyclicity;
task↔wave exclusive membership; canonical ten-action authorization ceiling on
every task; `program.definition_status = accepted`; every task
`definition_status ∈ {ready, blocked, cancelled, superseded}`; **zero**
unresolved `{{…}}` / `REPLACE_WITH_…` placeholders; resolvable markdown links;
compilable Python; and a full per-file `MANIFEST.yaml` sha256 match.

## Interpretation

Green here means **structural / design-time compile-readiness of the program
definition** — consistent with the program's own DEC-004 (`validate_devpack`
reports structural compile-readiness, not executed runtime proof). It does **not**
assert that the `l9-devpack-compiler` target repository was modified: that work
is gated behind `UNK-001` and delivered under `deliverables/l9-devpack-compiler/`.
