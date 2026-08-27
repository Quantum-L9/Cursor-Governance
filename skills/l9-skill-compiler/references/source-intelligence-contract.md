# Bounded LLM contract: EXTRACT_SOURCE_INTELLIGENCE

## Scope
Extract reusable semantics from source material into IR-shaped fields. Nothing else.

## Permitted
- Identify objective, invariants, risks, inputs, outputs implied by source material.
- Identify candidate activation and non-activation phrasings.
- Mark anything unsupported by source as an explicit UNKNOWN entry.

## Forbidden
- File existence checks, YAML/JSON parsing, reference resolution, cycle detection.
- Package enumeration or registry mutation.
- Asserting that any command or test ran.
- Inventing confidence percentages.

## Output contract
Return a JSON object with keys `extracted`, `evidence`, `unknowns`.
Every element of `extracted` must cite a `source_ref` present in the CompileRequest.
Any claim without a `source_ref` must move to `unknowns`.

## Failure behavior
If source material does not support a required IR field, emit the field in
`unknowns` with `bounded_unknown: true`. Do not guess. Downstream Capability
Closure will return BLOCKED, which is the correct outcome.
