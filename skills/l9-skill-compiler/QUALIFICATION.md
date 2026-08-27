# First qualification run — l9-intelligence-harvest

The first real compile attempted through the operator CLI, used to qualify the
compiler rather than to ship a Skill. The run is recorded here in full,
including the outcome the compiler actually returned.

## Invocation

```bash
python skills/l9-skill-compiler/scripts/compile_skill.py create \
  --name l9-intelligence-harvest \
  --source "kernels/Gold Nugget Extractor 🚀.md" \
  --objective "Given an uploaded pack, perform in one pass: full unpack, system reconstruction, blue-sky strategic analysis, gold-nugget extraction, and a buildable execution blueprint" \
  --profile portable --profile l9
```

## Observed result

| Field | Value |
|---|---|
| exit code | `3` |
| status | `BLOCKED` |
| error class | `COMPILATION_BLOCKED` |
| DAG terminal state | `BOUNDED_LLM_REQUIRED` |
| halted at | `TOPOLOGY_OWNERSHIP_JUDGMENT` |
| topology decision | `ESCALATE_TO_BOUNDED_LLM` |
| topology evidence | `live_skills_enumerated=54`, `multiple_partial_owners=l9-gap-analysis,l9-harvest-pipeline,l9-code-analysis` |
| artifacts written | none |
| build receipt | not claimed (`build_receipt_complete: false`) |

No Skill was created. The operator typed `create`; the compiler answered that
ownership is unresolved. That answer stands — the CLI verb does not override it.

## Defects found

Classified and repaired in the owning layer, or reported where repair was out
of this contract's scope.

### COMPILER_DEFECT — namespace prefix counted as ownership evidence (fixed)

`scan_skill_topology.candidates()` scored `tokens(role) | tokens(name)` against
the request's tokens. Every Skill in this repository is named `l9-*`, so `l9`
was a free capability point for every candidate. Effects:

- a proposed name with one incidental real token match reached the
  `capability_overlap >= 2` threshold and returned `EXTEND_EXISTING`
  deterministically, with no escalation;
- a proposed name with no real overlap at all still produced 54 candidates.

Reproduced before the fix: `l9-zzz-quantum-widget` with the objective
`xyzzy plugh` returned `ESCALATE_TO_BOUNDED_LLM`, while the identical request
named `zzz-quantum-widget` correctly returned `CREATE_NEW`. This run originally
returned `EXTEND_EXISTING` against `l9-harvest-pipeline` on the strength of
`l9` plus `harvest`.

Fixed by deriving the uninformative token set from the live corpus — tokens
every live Skill shares prove nothing about ownership — rather than hardcoding
a prefix. Regression tests: `tests/test_topology_decision.py`.

### COMPILER_DEFECT — DESIGN_RUNTIME demanded this compiler's own stages (fixed)

`references/runtime-design-contract.md` instructed every `DESIGN_RUNTIME`
execution to "preserve the fifteen logical stages named in `SKILL.md`". That
file is this compiler's own SKILL.md, so the contract required every compiled
Skill's runtime to reproduce the compiler's compiler-family graph. Corrected to
name the subject Skill's own profile as the source of its stages, with the
fifteen stages scoped to the case where the subject is this compiler.

### COMPILER_DEFECT — MODEL_INSTRUCTION bindings never resolved (fixed)

`check_capability_closure.py` verified target existence for `EXECUTABLE`,
`DAG_NODE`, and `DELEGATED_SKILL` bindings but not for `MODEL_INSTRUCTION`. A
required capability bound to a reference file that does not exist returned
`CLOSED`. This is material to exactly the Skill shape this source implies: an
advisory or diagnostic Skill binds most of its capabilities to instruction
documents. A `MODEL_INSTRUCTION` target that names a path must now resolve; a
bare string is still treated as inline instruction text.

## Source defects

The source is `kernels/Gold Nugget Extractor 🚀.md`. These are reported, not
worked around, and not resolved by inventing intent on the source's behalf.

1. **Pre-filled convergence block.** The required output ends with literal
   constants — `convergence_status: converged`, `recursive_passes_run: 8`,
   `drift_detected_after_final_pass: false`, `build_blueprint_ready: true` —
   asserted regardless of what the run observed. That is fabricated validation
   evidence, and it contradicts the same document's own "no fake precision"
   rule. A Skill compiled from it as written would ship a false-validation
   surface.
2. **No activation surface.** The source defines sixteen output sections but
   never states when the capability should fire, when it must not, or which
   sibling owns the adjacent case. The compiler requires `positive`,
   `negative`, and `sibling_collision` activation fixtures; none are supported
   by the source, so all three would have to be invented.
3. **No capability bindings.** There are no executables, schemas, or
   validators. Section 12, "Validation Model", enumerates structural, schema,
   import, unit, integration, and no-stub checks as *content the answer should
   describe*, not as checks the Skill runs. Capability Closure would return
   BLOCKED, which is the correct outcome.
4. **Ambiguous identity.** The document calls itself a "Compiler Prompt" and
   emits a "Contract Compiler Handoff" while forbidding implementation code. It
   behaves as a read-only diagnostic capability. Compiling it as-is would
   encode an arbitrary family choice.

Defects 2 and 4 are what the topology escalation is reporting: with no
activation surface and an ambiguous identity, no evidence separates this from
`l9-gap-analysis`, `l9-code-analysis`, or `l9-harvest-pipeline`. Resolving the
source defects is the prerequisite for an ownership judgment, and none of them
is repairable inside the compiler.

## What the run qualifies

The deterministic plane executed correctly: the request bound against the
canonical schema, topology enumerated 54 live Skills, guards fired from stage
output, and the run stopped at the first node with no deterministic substitute
rather than reporting a build. A separate run supplying an IR
(`--ir`) drives the tail — `NORMALIZE_SKILL_IR`, `RENDER_TARGET_PROFILE` across
both profiles, `STATIC_VALIDATE`, `CAPABILITY_CLOSURE`, `ACTIVATION_EVAL` — and
still blocks at `BEHAVIOR_EVAL`, which has no deterministic substitute either.
