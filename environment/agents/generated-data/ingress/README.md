# Ingress

**Path:** `environment/agents/generated-data/ingress` | **Kind:** subsystem

## Modules

### `__init__.py`

Secure generated-data ingress front door.

### `ingest.py`

- `def ingest_packet() -> dict[str, Any]` — Durably capture and process a canonical generated-data packet.
- `def ingest_accepted_result() -> dict[str, Any]`
- `def ingest()`

### `receipts.py`

- `def packet_evidence_path(packet_digest) -> Path`
- `def write_packet_evidence(packet, packet_digest) -> Path`
- `def write_ingress(body) -> dict[str, Any]`
- `def load_ingress(acceptance_digest) -> dict[str, Any] | None`
- `def quarantine_meta(meta) -> Path`

### `security_gate.py`

- `def preflight(packet) -> dict[str, Any]` — Run BEFORE durable ordinary persistence. Never echo secrets.

## Dependencies

**Internal:** `environment`, `security_gate`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
