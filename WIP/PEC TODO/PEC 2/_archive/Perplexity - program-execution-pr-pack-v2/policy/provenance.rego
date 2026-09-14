package provenance
deny[msg] { not input.attestation; msg := "artifact has no attestation; deployment must be blocked" }
deny[msg] { input.attestation; required := {"source_sha", "workflow_ref", "node_id", "contract_digest"}; provided := {k | some k; input.attestation.predicate[k]}; missing := required - provided; count(missing) > 0; msg := sprintf("attestation missing required predicate fields: %v", [missing]) }
