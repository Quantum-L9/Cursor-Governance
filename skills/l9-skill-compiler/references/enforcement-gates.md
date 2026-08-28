<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: enforcement-gates
version: 3.7.0
status: active
-->

# Enforcement Gates

- Gate A, Source Parse: objective, scope, inputs, outputs, triggers, reject signals, constraints, resources, risks, unknowns, directive activation, and source dependency status.
- Gate B, Expertise Model: required only for exemplary mode; experts, doctrine, invariants, authority, signals, heuristics, adapters, failure controls, and leverage.
- Gate C, File Tree: exact allowlist, purpose, dependency map, output contract, adapter activation, and convergence decision.
- Gate D, Build Manifest: files written, completeness, zero unfinished markers, script compile status, and checks actually run.
- Gate E, Validation Report: six validation classes, evidence matrix, tier decision, failures, and correction order.
- Gate F, Wiring Report: required only when installation or repository wiring is requested; verified target, changes, and rollback.
- Gate G, Package Record: actual ZIP path, manifest, size, root shape, validation status, and checksum.

The compiler may keep gate artifacts in the build workspace rather than shipping them, except `expertise_model.yaml` and `skill_intelligence_report.yaml` for an exemplary skill. Skipping an applicable gate is a protocol violation.
