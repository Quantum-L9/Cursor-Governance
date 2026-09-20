# Ingress

**Path:** `environment/agents/generated-data/ingress` | **Tier:** discovered

## Purpose

Secure generated-data ingress front door.



## Components

_No public classes in this path._

## Functions

- `def ingest_packet() -> dict[str, Any]` — Durably capture and process a canonical generated-data packet.
- `def ingest_accepted_result() -> dict[str, Any]`
- `def ingest()`
- `def packet_evidence_path(packet_digest) -> Path`
- `def write_packet_evidence(packet, packet_digest) -> Path`
- `def write_ingress(body) -> dict[str, Any]`
- `def load_ingress(acceptance_digest) -> dict[str, Any] | None`
- `def quarantine_meta(meta) -> Path`
- `def preflight(packet) -> dict[str, Any]` — Run BEFORE durable ordinary persistence. Never echo secrets.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `collections.abc`, `datetime`, `environment.agents.runtime_paths`, `hashlib`, `importlib.util`, `json`, `os`, `pathlib`, `re`, `security_gate`, `shlex`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
