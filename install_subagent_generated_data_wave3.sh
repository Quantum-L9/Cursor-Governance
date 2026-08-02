#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
BASE="$ROOT/subagent-generated-data"
ADAPTERS="$BASE/adapters"
TESTS="$BASE/tests"
FIXTURES="$TESTS/fixtures"
for required in \
  "$BASE/law/SUBAGENT_GENERATED_DATA_LAW.md" \
  "$BASE/runtime/packet_validator.py" \
  "$BASE/runtime/harvester.py" \
  "$BASE/runtime/classifier.py" \
  "$BASE/runtime/routing_engine.py" \
  "$BASE/runtime/promotion_gate.py" \
  "$BASE/runtime/learning_closure.py" \
  "$BASE/routes/memory.yaml" \
  "$BASE/routes/contracts.yaml" \
  "$BASE/routes/validation.yaml" \
  "$BASE/routes/patterns.yaml" \
  "$BASE/routes/architecture.yaml" \
  "$BASE/routes/opportunities.yaml"
do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: Required Wave 1 or Wave 2 file is missing: $required" >&2
    exit 1
  fi
done
mkdir -p \
  "$ADAPTERS" \
  "$TESTS/conformance" \
  "$TESTS/routing" \
  "$TESTS/negative" \
  "$TESTS/golden" \
  "$FIXTURES" \
  "$BASE/.runtime/memory-outbox" \
  "$BASE/.runtime/contracts-outbox" \
  "$BASE/.runtime/validation-outbox" \
  "$BASE/.runtime/patterns-outbox" \
  "$BASE/.runtime/architecture-outbox" \
  "$BASE/.runtime/opportunities-outbox"
cat > "$ADAPTERS/__init__.py" <<'PY'
"""
Destination and repository-class adapters for L9 subagent-generated data.
Adapters do not decide whether a unit is eligible for promotion. They receive
already evaluated promotion results and translate approved units into
destination-specific envelopes.
Authority remains with:
- the routing engine;
- the promotion gate;
- the destination system;
- and designated human or canonical authorities where required.
"""
__version__ = "1.0.0"
PY
cat > "$ADAPTERS/graphiti_memory.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
class GraphitiAdapterError(RuntimeError):
    """Raised when governed memory delivery cannot be completed safely."""
@dataclass(frozen=True)
class MemoryCandidate:
    schema_version: str
    kind: str
    candidate_id: str
    source: Mapping[str, Any]
    knowledge: Mapping[str, Any]
    governance: Mapping[str, Any]
    provenance: Mapping[str, Any]
    generated_at: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "candidate_id": self.candidate_id,
            "source": dict(self.source),
            "knowledge": dict(self.knowledge),
            "governance": dict(self.governance),
            "provenance": dict(self.provenance),
            "generated_at": self.generated_at,
        }
@dataclass(frozen=True)
class MemoryDeliveryResult:
    candidate_id: str
    status: str
    transport: str
    destination_reference: str
    receipt_hash: str
    response: Mapping[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status,
            "transport": self.transport,
            "destination_reference": self.destination_reference,
            "receipt_hash": self.receipt_hash,
            "response": dict(self.response),
        }
class MemoryTransport(Protocol):
    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Deliver one governed memory candidate."""
class FileOutboxTransport:
    """Durably enqueue candidates for later Graphiti ingestion."""
    def __init__(self, outbox_dir: str | Path) -> None:
        self.outbox_dir = Path(outbox_dir)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        candidate_id = str(candidate["candidate_id"])
        target = self.outbox_dir / f"{candidate_id}.json"
        payload = canonical_json(candidate)
        payload_hash = hashlib.sha256(payload).hexdigest()
        if target.exists():
            existing = target.read_bytes()
            existing_hash = hashlib.sha256(existing).hexdigest()
            if existing_hash != payload_hash:
                raise GraphitiAdapterError(
                    f"Candidate ID collision with different payload: "
                    f"{candidate_id}"
                )
            return {
                "status": "already_enqueued",
                "path": str(target),
                "payload_hash": payload_hash,
            }
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=self.outbox_dir,
            prefix=f".{candidate_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(target)
        return {
            "status": "enqueued",
            "path": str(target),
            "payload_hash": payload_hash,
        }
class HttpJsonTransport:
    """Submit governed candidates to an HTTP JSON endpoint."""
    def __init__(
        self,
        endpoint: str,
        *,
        bearer_token: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError(
                "Graphiti HTTP endpoint must use http:// or https://"
            )
        self.endpoint = endpoint
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "l9-subagent-generated-data/1.0",
        }
        if self.bearer_token:
            headers["Authorization"] = (
                f"Bearer {self.bearer_token}"
            )
        request = Request(
            self.endpoint,
            data=canonical_json(candidate),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read()
                status_code = response.status
        except HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise GraphitiAdapterError(
                f"Graphiti endpoint rejected candidate: "
                f"HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise GraphitiAdapterError(
                f"Graphiti endpoint unavailable: {exc}"
            ) from exc
        if not 200 <= status_code < 300:
            raise GraphitiAdapterError(
                f"Unexpected Graphiti status: {status_code}"
            )
        if not body:
            return {
                "status": "accepted",
                "http_status": status_code,
            }
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {
                "raw_response": body.decode(
                    "utf-8",
                    errors="replace",
                )
            }
        if not isinstance(parsed, Mapping):
            parsed = {"response": parsed}
        return {
            "status": "accepted",
            "http_status": status_code,
            **dict(parsed),
        }
class CommandTransport:
    """Invoke an explicit Graphiti ingestion command with JSON on stdin."""
    def __init__(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 30,
    ) -> None:
        if not command:
            raise ValueError(
                "Graphiti command transport requires a command"
            )
        self.command = command
        self.timeout_seconds = timeout_seconds
    def deliver(
        self,
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        completed = subprocess.run(
            self.command,
            input=canonical_json(candidate),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout.decode(
            "utf-8",
            errors="replace",
        )
        stderr = completed.stderr.decode(
            "utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise GraphitiAdapterError(
                "Graphiti command rejected candidate: "
                f"exit={completed.returncode}; stderr={stderr}"
            )
        if not stdout.strip():
            response: Mapping[str, Any] = {
                "status": "accepted"
            }
        else:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                parsed = {
                    "status": "accepted",
                    "stdout": stdout,
                }
            if not isinstance(parsed, Mapping):
                response = {
                    "status": "accepted",
                    "response": parsed,
                }
            else:
                response = parsed
        return {
            **dict(response),
            "stderr": stderr,
            "exit_code": completed.returncode,
        }
class GraphitiMemoryAdapter:
    """Compile approved memory-route units into governed candidates."""
    def __init__(self, transport: MemoryTransport) -> None:
        self.transport = transport
    def compile_candidate(
        self,
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        promotion_result: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> MemoryCandidate:
        self._require_memory_promotion(
            harvested_unit=harvested_unit,
            routing_decision=routing_decision,
            promotion_result=promotion_result,
        )
        original = harvested_unit["original_unit"]
        identity = packet["identity"]
        provenance = packet["provenance"]
        unit_id = str(harvested_unit["unit_id"])
        route_decision_id = str(
            routing_decision["decision_id"]
        )
        candidate_seed = {
            "unit_id": unit_id,
            "packet_id": packet["packet_id"],
            "route_decision_id": route_decision_id,
            "promotion_id": promotion_result[
                "promotion_id"
            ],
            "statement_hash": harvested_unit[
                "statement_hash"
            ],
        }
        candidate_hash = hashlib.sha256(
            canonical_json(candidate_seed)
        ).hexdigest()
        generated_at = datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z")
        return MemoryCandidate(
            schema_version="1.0.0",
            kind="MemoryCandidate",
            candidate_id=f"memcand-{candidate_hash[:24]}",
            source={
                "campaign_id": identity["campaign_id"],
                "graph_id": identity["graph_id"],
                "action_id": identity["action_id"],
                "agent_id": identity["agent_id"],
                "role": identity["role"],
                "lease_id": identity["lease_id"],
                "repository": identity["repository"],
                "repository_class": identity[
                    "repository_class"
                ],
                "base_sha": identity["base_sha"],
                "packet_id": packet["packet_id"],
                "primary_artifact_id": packet[
                    "primary_result"
                ]["artifact_id"],
            },
            knowledge={
                "unit_id": unit_id,
                "statement": original["statement"],
                "primary_class": original[
                    "primary_class"
                ],
                "epistemic_status": original[
                    "epistemic_status"
                ],
                "scope": original["scope"],
                "confidence": original["confidence"],
                "freshness": original["freshness"],
                "expected_reuse": original[
                    "expected_reuse"
                ],
                "invalidation_conditions": original[
                    "invalidation_conditions"
                ],
            },
            governance={
                "authority_class": "advisory",
                "route": "memory",
                "routing_decision_id": route_decision_id,
                "promotion_id": promotion_result[
                    "promotion_id"
                ],
                "promotion_decision": promotion_result[
                    "decision"
                ],
                "risk_class": promotion_result[
                    "risk_class"
                ],
                "visibility": original.get(
                    "visibility",
                    "repository_local",
                ),
                "may_override_repository_state": False,
                "may_override_canonical_authority": False,
            },
            provenance={
                **dict(provenance),
                "source_evidence": original[
                    "source_evidence"
                ],
                "statement_hash": harvested_unit[
                    "statement_hash"
                ],
                "packet_hash": packet.get(
                    "packet_hash"
                ),
            },
            generated_at=generated_at,
        )
    def deliver(
        self,
        candidate: MemoryCandidate,
    ) -> MemoryDeliveryResult:
        payload = candidate.to_dict()
        response = self.transport.deliver(payload)
        response_status = str(
            response.get("status", "unknown")
        )
        accepted_statuses = {
            "accepted",
            "enqueued",
            "already_enqueued",
            "merged",
            "contested",
            "quarantined",
        }
        if response_status not in accepted_statuses:
            raise GraphitiAdapterError(
                "Graphiti transport returned unsupported status: "
                f"{response_status!r}"
            )
        destination_reference = str(
            response.get(
                "memory_id",
                response.get(
                    "path",
                    response.get(
                        "candidate_id",
                        candidate.candidate_id,
                    ),
                ),
            )
        )
        receipt_payload = {
            "candidate_id": candidate.candidate_id,
            "status": response_status,
            "destination_reference": destination_reference,
            "response": dict(response),
        }
        receipt_hash = hashlib.sha256(
            canonical_json(receipt_payload)
        ).hexdigest()
        return MemoryDeliveryResult(
            candidate_id=candidate.candidate_id,
            status=response_status,
            transport=type(self.transport).__name__,
            destination_reference=destination_reference,
            receipt_hash=receipt_hash,
            response=dict(response),
        )
    @staticmethod
    def _require_memory_promotion(
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        promotion_result: Mapping[str, Any],
    ) -> None:
        unit_id = str(harvested_unit.get("unit_id"))
        if routing_decision.get("unit_id") != unit_id:
            raise GraphitiAdapterError(
                "Routing decision unit does not match harvested unit"
            )
        if promotion_result.get("unit_id") != unit_id:
            raise GraphitiAdapterError(
                "Promotion result unit does not match harvested unit"
            )
        if routing_decision.get("route") != "memory":
            raise GraphitiAdapterError(
                "Graphiti adapter only accepts memory route decisions"
            )
        if routing_decision.get("status") != "eligible":
            raise GraphitiAdapterError(
                "Graphiti adapter requires an eligible route decision"
            )
        if promotion_result.get("decision") != "promote":
            raise GraphitiAdapterError(
                "Graphiti adapter requires a promote decision"
            )
def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def select_transport(args: argparse.Namespace) -> MemoryTransport:
    if args.endpoint:
        return HttpJsonTransport(
            args.endpoint,
            bearer_token=(
                args.token
                or os.environ.get(
                    "L9_GRAPHITI_MEMORY_TOKEN"
                )
            ),
            timeout_seconds=args.timeout,
        )
    if args.command:
        return CommandTransport(
            args.command,
            timeout_seconds=args.timeout,
        )
    return FileOutboxTransport(args.outbox)
def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and deliver one approved generated-data "
            "memory candidate."
        )
    )
    parser.add_argument("--packet", required=True)
    parser.add_argument("--harvested-unit", required=True)
    parser.add_argument("--routing-decision", required=True)
    parser.add_argument("--promotion-result", required=True)
    parser.add_argument(
        "--outbox",
        default=(
            "subagent-generated-data/"
            ".runtime/memory-outbox"
        ),
    )
    parser.add_argument("--endpoint")
    parser.add_argument("--token")
    parser.add_argument(
        "--command",
        nargs="+",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
    )
    args = parser.parse_args()
    adapter = GraphitiMemoryAdapter(
        select_transport(args)
    )
    candidate = adapter.compile_candidate(
        harvested_unit=load_json(
            args.harvested_unit
        ),
        routing_decision=load_json(
            args.routing_decision
        ),
        promotion_result=load_json(
            args.promotion_result
        ),
        packet=load_json(args.packet),
    )
    if args.compile_only:
        print(
            json.dumps(
                candidate.to_dict(),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = adapter.deliver(candidate)
    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$ADAPTERS/l9_python.py" <<'PY'
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
class L9PythonAdapterError(ValueError):
    """Raised when an L9 Python repository cannot be adapted safely."""
@dataclass(frozen=True)
class RepositoryContext:
    repository_class: str
    root: str
    authoritative_files: tuple[str, ...]
    validation_commands: tuple[str, ...]
    architecture_surfaces: tuple[str, ...]
    protected_paths: tuple[str, ...]
    metadata: Mapping[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_class": self.repository_class,
            "root": self.root,
            "authoritative_files": list(
                self.authoritative_files
            ),
            "validation_commands": list(
                self.validation_commands
            ),
            "architecture_surfaces": list(
                self.architecture_surfaces
            ),
            "protected_paths": list(
                self.protected_paths
            ),
            "metadata": dict(self.metadata),
        }
class L9PythonRepositoryAdapter:
    """Interpret generated data for strict L9 Python repositories."""
    REQUIRED_FILES = (
        "pyproject.toml",
        "uv.lock",
        "AGENTS.md",
    )
    AUTHORITATIVE_FILES = (
        "AGENTS.md",
        "ARCHITECTURE.md",
        "DEVELOPMENT.md",
        "TESTING.md",
        "OPERATIONS.md",
        "RUNBOOK.md",
        "SECURITY.md",
        "pyproject.toml",
        "uv.lock",
    )
    VALIDATION_COMMANDS = (
        "uv sync --locked",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run pyright",
        "uv run pytest --tb=short -q",
    )
    PROTECTED_PATHS = (
        ".env",
        "**/*.pem",
        "**/*.key",
        "**/secrets/**",
        ".github/workflows/**",
        "AGENTS.md",
        "SECURITY.md",
    )
    def inspect(
        self,
        repository_root: str | Path,
    ) -> RepositoryContext:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise L9PythonAdapterError(
                f"Repository root does not exist: {root}"
            )
        missing_required = [
            filename
            for filename in self.REQUIRED_FILES
            if not (root / filename).is_file()
        ]
        architecture_surfaces = self._discover_surfaces(
            root
        )
        return RepositoryContext(
            repository_class="l9_python",
            root=str(root),
            authoritative_files=tuple(
                filename
                for filename in self.AUTHORITATIVE_FILES
                if (root / filename).exists()
            ),
            validation_commands=self.VALIDATION_COMMANDS,
            architecture_surfaces=tuple(
                architecture_surfaces
            ),
            protected_paths=self.PROTECTED_PATHS,
            metadata={
                "strict_typing_expected": True,
                "uv_lock_required": True,
                "py_typed_expected": True,
                "ci_required": True,
                "missing_required_files": missing_required,
                "conformant": not missing_required,
            },
        )
    def enrich_unit(
        self,
        unit: Mapping[str, Any],
        context: RepositoryContext,
    ) -> dict[str, Any]:
        enriched = dict(unit)
        metadata = dict(enriched.get("adapter_metadata", {}))
        metadata.update(
            {
                "repository_class": "l9_python",
                "validation_authority": {
                    "format_and_lint": "ruff",
                    "type_analysis": "pyright_strict",
                    "behavior_validation": "pytest",
                    "dependency_environment": "uv",
                },
                "canonical_validation_commands": list(
                    context.validation_commands
                ),
                "authoritative_files": list(
                    context.authoritative_files
                ),
                "architecture_surfaces": list(
                    context.architecture_surfaces
                ),
                "protected_paths": list(
                    context.protected_paths
                ),
            }
        )
        primary_class = str(
            unit.get("primary_class", "")
        )
        if primary_class in {
            "validation_procedure",
            "regression_candidate",
            "invariant_candidate",
        }:
            metadata["required_validation_ladder"] = [
                "format",
                "lint",
                "type",
                "test",
                "ci",
            ]
        if primary_class in {
            "architecture_boundary",
            "ownership_finding",
            "dependency_finding",
        }:
            metadata[
                "architecture_authority_required"
            ] = True
        enriched["adapter_metadata"] = metadata
        return enriched
    @staticmethod
    def _discover_surfaces(
        root: Path,
    ) -> list[str]:
        candidates = (
            "src",
            "tests",
            "evals",
            "prompts",
            "typings",
            ".github/workflows",
            "docs",
        )
        return [
            candidate
            for candidate in candidates
            if (root / candidate).exists()
        ]
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or enrich data for an L9 Python repo."
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--unit")
    args = parser.parse_args()
    adapter = L9PythonRepositoryAdapter()
    context = adapter.inspect(args.repository)
    result: Mapping[str, Any]
    if args.unit:
        unit = load_json(args.unit)
        if not isinstance(unit, Mapping):
            raise SystemExit("Unit root must be an object")
        result = adapter.enrich_unit(unit, context)
    else:
        result = context.to_dict()
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if context.metadata["conformant"]
        else 1
    )
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$ADAPTERS/odoo.py" <<'PY'
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
class OdooAdapterError(ValueError):
    """Raised when an Odoo repository cannot be adapted safely."""
@dataclass(frozen=True)
class OdooRepositoryContext:
    repository_class: str
    root: str
    addon_roots: tuple[str, ...]
    modules: tuple[str, ...]
    validation_authority: Mapping[str, str]
    protected_paths: tuple[str, ...]
    metadata: Mapping[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_class": self.repository_class,
            "root": self.root,
            "addon_roots": list(self.addon_roots),
            "modules": list(self.modules),
            "validation_authority": dict(
                self.validation_authority
            ),
            "protected_paths": list(
                self.protected_paths
            ),
            "metadata": dict(self.metadata),
        }
class OdooRepositoryAdapter:
    """Interpret generated data for pragmatic local-first Odoo repos."""
    PROTECTED_PATHS = (
        ".env",
        "**/*.pem",
        "**/*.key",
        "**/secrets/**",
        "odoo.conf",
        "filestore/**",
        "data/postgres/**",
    )
    VALIDATION_AUTHORITY = {
        "business_correctness": "odoo_runtime_tests",
        "style_and_lint": "ruff",
        "typing": "pyright_basic_editor_guardrail",
        "integration": "live_odoo_runtime",
    }
    def inspect(
        self,
        repository_root: str | Path,
    ) -> OdooRepositoryContext:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise OdooAdapterError(
                f"Repository root does not exist: {root}"
            )
        addon_roots = self._discover_addon_roots(root)
        modules = self._discover_modules(
            root,
            addon_roots,
        )
        return OdooRepositoryContext(
            repository_class="odoo",
            root=str(root),
            addon_roots=tuple(addon_roots),
            modules=tuple(modules),
            validation_authority=self.VALIDATION_AUTHORITY,
            protected_paths=self.PROTECTED_PATHS,
            metadata={
                "local_first": True,
                "strict_typing_expected": False,
                "pyright_mode": "basic",
                "runtime_tests_are_authority": True,
                "docker_required": False,
                "module_count": len(modules),
                "conformant": bool(addon_roots),
            },
        )
    def enrich_unit(
        self,
        unit: Mapping[str, Any],
        context: OdooRepositoryContext,
    ) -> dict[str, Any]:
        enriched = dict(unit)
        metadata = dict(enriched.get("adapter_metadata", {}))
        metadata.update(
            {
                "repository_class": "odoo",
                "validation_authority": dict(
                    context.validation_authority
                ),
                "addon_roots": list(context.addon_roots),
                "known_modules": list(context.modules),
                "protected_paths": list(
                    context.protected_paths
                ),
                "typing_policy": {
                    "mode": "basic",
                    "unknown_member_noise_is_not_primary_signal": True,
                    "runtime_correctness_over_type_purity": True,
                },
            }
        )
        primary_class = str(
            unit.get("primary_class", "")
        )
        if primary_class in {
            "validation_procedure",
            "regression_candidate",
            "invariant_candidate",
        }:
            metadata["required_validation"] = [
                "ruff",
                "module_install_or_upgrade",
                "odoo_runtime_tests",
                "relevant_live_integration",
            ]
        if primary_class in {
            "architecture_boundary",
            "ownership_finding",
        }:
            metadata["inspect_first"] = [
                "__manifest__.py",
                "models/__init__.py",
                "models/*.py",
                "views/*.xml",
                "security/ir.model.access.csv",
            ]
        enriched["adapter_metadata"] = metadata
        return enriched
    @staticmethod
    def _discover_addon_roots(
        root: Path,
    ) -> list[str]:
        candidates: list[Path] = []
        common = (
            root / "addons",
            root / "custom_addons",
            root / "odoo" / "addons",
        )
        for path in common:
            if path.is_dir():
                candidates.append(path)
        for manifest in root.rglob("__manifest__.py"):
            parent = manifest.parent.parent
            if parent.is_dir():
                candidates.append(parent)
        unique = sorted(
            {
                str(path.relative_to(root))
                for path in candidates
                if path != root
            }
        )
        return unique
    @staticmethod
    def _discover_modules(
        root: Path,
        addon_roots: list[str],
    ) -> list[str]:
        modules: set[str] = set()
        for relative_root in addon_roots:
            addon_root = root / relative_root
            if not addon_root.is_dir():
                continue
            for child in addon_root.iterdir():
                if (
                    child.is_dir()
                    and (child / "__manifest__.py").is_file()
                ):
                    modules.add(
                        str(child.relative_to(root))
                    )
        return sorted(modules)
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or enrich data for an Odoo repo."
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--unit")
    args = parser.parse_args()
    adapter = OdooRepositoryAdapter()
    context = adapter.inspect(args.repository)
    result: Mapping[str, Any]
    if args.unit:
        unit = load_json(args.unit)
        if not isinstance(unit, Mapping):
            raise SystemExit("Unit root must be an object")
        result = adapter.enrich_unit(unit, context)
    else:
        result = context.to_dict()
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if context.metadata["conformant"]
        else 1
    )
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$FIXTURES/valid-recon-packet.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "packet_id": "packet-campaign-001-recon-001",
  "identity": {
    "campaign_id": "campaign-001",
    "graph_id": "graph-001",
    "repository": "Quantum-L9/example",
    "repository_class": "l9_python",
    "base_sha": "abc1234",
    "action_id": "recon-001",
    "agent_id": "agent-recon-001",
    "role": "recon",
    "lease_id": "lease-recon-001"
  },
  "primary_result": {
    "artifact_id": "artifact-recon-001",
    "artifact_kind": "ReconReport",
    "completion_status": "completed"
  },
  "generated_data_units": [
    {
      "unit_id": "unit-repo-fact-001",
      "primary_class": "repository_fact",
      "epistemic_status": "observed",
      "statement": "The repository uses uv.lock as the dependency resolution contract.",
      "source_evidence": [
        {
          "source_id": "source-uv-lock",
          "source_type": "repository_path",
          "repository": "Quantum-L9/example",
          "path": "uv.lock",
          "base_sha": "abc1234",
          "locator": "file"
        }
      ],
      "scope": {
        "repositories": [
          "Quantum-L9/example"
        ],
        "repository_classes": [
          "l9_python"
        ],
        "paths": [
          "uv.lock"
        ],
        "task_types": [
          "dependency_setup"
        ],
        "roles": [
          "executor",
          "verifier"
        ]
      },
      "confidence": 0.98,
      "freshness": {
        "observed_at": "2026-08-02T15:00:00Z",
        "base_sha": "abc1234",
        "expires_at": null
      },
      "proposed_routes": [
        "memory"
      ],
      "expected_reuse": {
        "task_local": true,
        "cross_task": true,
        "cross_campaign": true,
        "cross_repository": false,
        "description": "Future setup and verification agents should use locked uv commands."
      },
      "invalidation_conditions": [
        {
          "condition_type": "relevant_path_changed",
          "selector": "uv.lock"
        },
        {
          "condition_type": "policy_version_changed",
          "selector": "dependency_strategy"
        }
      ],
      "visibility": "repository_local"
    },
    {
      "unit_id": "unit-contract-gap-001",
      "primary_class": "task_contract_gap",
      "epistemic_status": "derived",
      "statement": "Dependency setup tasks should explicitly require uv sync --locked.",
      "source_evidence": [
        {
          "source_id": "source-pyproject",
          "source_type": "repository_path",
          "repository": "Quantum-L9/example",
          "path": "pyproject.toml",
          "base_sha": "abc1234",
          "locator": "project"
        },
        {
          "source_id": "source-uv-lock",
          "source_type": "repository_path",
          "repository": "Quantum-L9/example",
          "path": "uv.lock",
          "base_sha": "abc1234",
          "locator": "file"
        }
      ],
      "scope": {
        "repositories": [
          "Quantum-L9/example"
        ],
        "repository_classes": [
          "l9_python"
        ],
        "paths": [
          "pyproject.toml",
          "uv.lock"
        ],
        "task_types": [
          "dependency_setup"
        ],
        "roles": [
          "executor"
        ]
      },
      "confidence": 0.92,
      "freshness": {
        "observed_at": "2026-08-02T15:00:00Z",
        "base_sha": "abc1234",
        "expires_at": null
      },
      "proposed_routes": [
        "contracts"
      ],
      "expected_reuse": {
        "task_local": false,
        "cross_task": true,
        "cross_campaign": true,
        "cross_repository": true,
        "description": "The requirement applies to L9 Python dependency setup tasks."
      },
      "invalidation_conditions": [
        {
          "condition_type": "policy_version_changed",
          "selector": "dependency_strategy"
        }
      ],
      "visibility": "constellation_internal"
    }
  ],
  "unresolved_unknowns": [
    {
      "unknown_id": "unknown-ci-001",
      "description": "It is not yet verified whether CI uses uv sync --locked.",
      "class": "validation",
      "blocking_status": "non_blocking",
      "owner": "verification-agent",
      "next_action": "Inspect CI workflow dependency setup.",
      "evidence_needed": "Current workflow file and successful CI receipt.",
      "source_action": "recon-001"
    }
  ],
  "provenance": {
    "repository": "Quantum-L9/example",
    "repository_class": "l9_python",
    "base_sha": "abc1234",
    "input_artifacts": [],
    "evidence_artifacts": [
      "artifact-recon-001"
    ],
    "inspected_paths": [
      "pyproject.toml",
      "uv.lock"
    ],
    "executed_commands": [
      "git rev-parse HEAD"
    ],
    "generated_at": "2026-08-02T15:00:00Z"
  },
  "reuse_assessment": {
    "reusable_data_found": true,
    "task_local_value": 4,
    "cross_task_value": 5,
    "cross_repository_value": 3,
    "confidence": 0.95,
    "reason": "The packet contains durable dependency and task-contract knowledge."
  },
  "generated_at": "2026-08-02T15:00:00Z"
}
JSON
cat > "$FIXTURES/invalid-missing-evidence-packet.json" <<'JSON'
{
  "schema_version": "1.0.0",
  "packet_id": "packet-invalid-001",
  "identity": {
    "campaign_id": "campaign-001",
    "graph_id": "graph-001",
    "repository": "Quantum-L9/example",
    "repository_class": "l9_python",
    "base_sha": "abc1234",
    "action_id": "recon-invalid",
    "agent_id": "agent-recon-invalid",
    "role": "recon",
    "lease_id": "lease-recon-invalid"
  },
  "primary_result": {
    "artifact_id": "artifact-invalid",
    "artifact_kind": "ReconReport",
    "completion_status": "completed"
  },
  "generated_data_units": [
    {
      "unit_id": "unit-invalid-observed",
      "primary_class": "repository_fact",
      "epistemic_status": "observed",
      "statement": "This observed statement has no evidence.",
      "source_evidence": [],
      "scope": {
        "repositories": [
          "Quantum-L9/example"
        ],
        "repository_classes": [
          "l9_python"
        ],
        "paths": [],
        "task_types": [],
        "roles": []
      },
      "confidence": 0.9,
      "freshness": {
        "observed_at": "2026-08-02T15:00:00Z",
        "base_sha": "abc1234",
        "expires_at": null
      },
      "proposed_routes": [
        "memory"
      ],
      "expected_reuse": {
        "task_local": false,
        "cross_task": true,
        "cross_campaign": false,
        "cross_repository": false,
        "description": "Should fail because no evidence is present."
      },
      "invalidation_conditions": [
        {
          "condition_type": "relevant_path_changed",
          "selector": "**"
        }
      ],
      "visibility": "repository_local"
    }
  ],
  "unresolved_unknowns": [],
  "provenance": {
    "repository": "Quantum-L9/example",
    "repository_class": "l9_python",
    "base_sha": "abc1234",
    "input_artifacts": [],
    "evidence_artifacts": [],
    "inspected_paths": [],
    "executed_commands": [],
    "generated_at": "2026-08-02T15:00:00Z"
  },
  "reuse_assessment": {
    "reusable_data_found": true,
    "task_local_value": 1,
    "cross_task_value": 2,
    "cross_repository_value": 1,
    "confidence": 0.2,
    "reason": "Negative fixture."
  },
  "generated_at": "2026-08-02T15:00:00Z"
}
JSON
cat > "$TESTS/conformance/test_wave3_conformance.py" <<'PY'
from __future__ import annotations
import ast
import importlib.util
import json
import sys
import unittest
from pathlib import Path
import yaml
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
ADAPTERS = BASE / "adapters"
ROUTES = BASE / "routes"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ADAPTERS))
from packet_validator import PacketValidator
from routing_engine import RoutingEngine
from graphiti_memory import FileOutboxTransport
from l9_python import L9PythonRepositoryAdapter
from odoo import OdooRepositoryAdapter
class Wave3ConformanceTests(unittest.TestCase):
    def test_all_python_files_parse(self) -> None:
        for directory in (RUNTIME, ADAPTERS):
            for path in sorted(directory.glob("*.py")):
                with self.subTest(path=path):
                    ast.parse(
                        path.read_text(
                            encoding="utf-8"
                        )
                    )
    def test_all_routes_are_valid_yaml(self) -> None:
        for path in sorted(ROUTES.glob("*.yaml")):
            with self.subTest(path=path):
                payload = yaml.safe_load(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
                self.assertIsInstance(payload, dict)
                self.assertEqual(
                    payload["route_id"],
                    path.stem,
                )
    def test_route_engine_conformance(self) -> None:
        errors = RoutingEngine().validate_routes()
        self.assertEqual(errors, [])
    def test_valid_fixture_passes_packet_validation(
        self,
    ) -> None:
        report = PacketValidator().validate_file(
            FIXTURES / "valid-recon-packet.json"
        )
        self.assertTrue(
            report.valid,
            report.to_dict(),
        )
    def test_invalid_fixture_fails_packet_validation(
        self,
    ) -> None:
        report = PacketValidator().validate_file(
            FIXTURES
            / "invalid-missing-evidence-packet.json"
        )
        self.assertFalse(report.valid)
        codes = {
            finding.code
            for finding in report.findings
        }
        self.assertIn(
            "SGD-EVIDENCE-REQUIRED",
            codes,
        )
    def test_file_outbox_is_idempotent(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            transport = FileOutboxTransport(temp)
            payload = {
                "candidate_id": "memcand-idempotent",
                "value": 1,
            }
            first = transport.deliver(payload)
            second = transport.deliver(payload)
            self.assertEqual(
                first["status"],
                "enqueued",
            )
            self.assertEqual(
                second["status"],
                "already_enqueued",
            )
    def test_repository_adapters_have_distinct_policy(
        self,
    ) -> None:
        self.assertTrue(
            L9PythonRepositoryAdapter()
            .VALIDATION_COMMANDS
        )
        self.assertEqual(
            OdooRepositoryAdapter()
            .VALIDATION_AUTHORITY["typing"],
            "pyright_basic_editor_guardrail",
        )
if __name__ == "__main__":
    unittest.main()
PY
cat > "$TESTS/routing/test_end_to_end_routing.py" <<'PY'
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
ADAPTERS = BASE / "adapters"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ADAPTERS))
from harvester import SubagentDataHarvester
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine
from graphiti_memory import (
    FileOutboxTransport,
    GraphitiMemoryAdapter,
)
class EndToEndRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(
            (
                FIXTURES
                / "valid-recon-packet.json"
            ).read_text(encoding="utf-8")
        )
    def test_packet_harvests_two_units(self) -> None:
        result = SubagentDataHarvester().harvest(
            self.packet
        )
        self.assertEqual(
            len(result.harvested_units),
            2,
        )
        self.assertEqual(
            result.duplicate_unit_ids,
            (),
        )
    def test_repository_fact_routes_to_memory(self) -> None:
        harvest = SubagentDataHarvester().harvest(
            self.packet
        )
        memory_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit[
                "primary_class"
            ] == "repository_fact"
        )
        decisions = RoutingEngine().route(
            memory_unit.to_dict()
        )
        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            decisions[0].route,
            "memory",
        )
        self.assertEqual(
            decisions[0].status,
            "eligible",
        )
    def test_contract_gap_requires_medium_risk_control(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(
            self.packet
        )
        contract_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit[
                "primary_class"
            ] == "task_contract_gap"
        )
        route = RoutingEngine().route(
            contract_unit.to_dict()
        )[0]
        result = PromotionGate().evaluate(
            harvested_unit=contract_unit.to_dict(),
            routing_decision=route.to_dict(),
            independent_validation_present=False,
            recurrence_count=1,
        )
        self.assertEqual(
            result.decision,
            "defer",
        )
        self.assertIn(
            "medium_risk_requires_validation_or_recurrence",
            result.reasons,
        )
    def test_memory_candidate_delivery_to_outbox(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(
            self.packet
        )
        memory_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit[
                "primary_class"
            ] == "repository_fact"
        )
        route = RoutingEngine().route(
            memory_unit.to_dict()
        )[0]
        promotion = PromotionGate().evaluate(
            harvested_unit=memory_unit.to_dict(),
            routing_decision=route.to_dict(),
            independent_validation_present=True,
            recurrence_count=2,
        )
        self.assertEqual(
            promotion.decision,
            "promote",
        )
        with tempfile.TemporaryDirectory() as temp:
            adapter = GraphitiMemoryAdapter(
                FileOutboxTransport(temp)
            )
            candidate = adapter.compile_candidate(
                harvested_unit=memory_unit.to_dict(),
                routing_decision=route.to_dict(),
                promotion_result=promotion.to_dict(),
                packet=self.packet,
            )
            delivery = adapter.deliver(candidate)
            self.assertEqual(
                delivery.status,
                "enqueued",
            )
            target = Path(
                delivery.destination_reference
            )
            self.assertTrue(target.is_file())
            stored = json.loads(
                target.read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                stored["kind"],
                "MemoryCandidate",
            )
            self.assertEqual(
                stored["governance"][
                    "authority_class"
                ],
                "advisory",
            )
            self.assertFalse(
                stored["governance"][
                    "may_override_repository_state"
                ]
            )
if __name__ == "__main__":
    unittest.main()
PY
cat > "$TESTS/negative/test_fail_closed.py" <<'PY'
from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
ADAPTERS = BASE / "adapters"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ADAPTERS))
from harvester import SubagentDataHarvester
from packet_validator import (
    PacketValidationFailure,
)
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine
from graphiti_memory import (
    FileOutboxTransport,
    GraphitiAdapterError,
    GraphitiMemoryAdapter,
)
class FailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_packet = json.loads(
            (
                FIXTURES
                / "valid-recon-packet.json"
            ).read_text(encoding="utf-8")
        )
    def test_harvester_rejects_invalid_packet(self) -> None:
        invalid = json.loads(
            (
                FIXTURES
                / "invalid-missing-evidence-packet.json"
            ).read_text(encoding="utf-8")
        )
        with self.assertRaises(
            PacketValidationFailure
        ):
            SubagentDataHarvester().harvest(
                invalid
            )
    def test_graphiti_rejects_non_memory_route(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(
            self.valid_packet
        )
        unit = harvest.harvested_units[0].to_dict()
        bad_route = {
            "decision_id": "route-bad",
            "unit_id": unit["unit_id"],
            "route": "contracts",
            "destination": "task-contracts",
            "status": "eligible",
            "reason_codes": [],
            "required_authority": "runtime",
            "requires_independent_validation": False,
            "decision_hash": "bad",
        }
        promotion = {
            "promotion_id": "promotion-bad",
            "unit_id": unit["unit_id"],
            "route": "contracts",
            "decision": "promote",
            "risk_class": "low",
            "authority_required": "runtime",
            "reasons": [],
            "conditions": [],
            "promotion_hash": "bad",
        }
        with tempfile.TemporaryDirectory() as temp:
            adapter = GraphitiMemoryAdapter(
                FileOutboxTransport(temp)
            )
            with self.assertRaises(
                GraphitiAdapterError
            ):
                adapter.compile_candidate(
                    harvested_unit=unit,
                    routing_decision=bad_route,
                    promotion_result=promotion,
                    packet=self.valid_packet,
                )
    def test_graphiti_rejects_deferred_promotion(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(
            self.valid_packet
        )
        unit = harvest.harvested_units[0].to_dict()
        route = RoutingEngine().route(unit)[0]
        promotion = PromotionGate().evaluate(
            harvested_unit=unit,
            routing_decision=route.to_dict(),
            independent_validation_present=False,
            recurrence_count=1,
        )
        self.assertNotEqual(
            promotion.decision,
            "promote",
        )
        with tempfile.TemporaryDirectory() as temp:
            adapter = GraphitiMemoryAdapter(
                FileOutboxTransport(temp)
            )
            with self.assertRaises(
                GraphitiAdapterError
            ):
                adapter.compile_candidate(
                    harvested_unit=unit,
                    routing_decision=route.to_dict(),
                    promotion_result=promotion.to_dict(),
                    packet=self.valid_packet,
                )
    def test_outbox_rejects_candidate_id_collision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            transport = FileOutboxTransport(temp)
            transport.deliver(
                {
                    "candidate_id": "memcand-collision",
                    "value": 1,
                }
            )
            with self.assertRaises(
                GraphitiAdapterError
            ):
                transport.deliver(
                    {
                        "candidate_id": "memcand-collision",
                        "value": 2,
                    }
                )
    def test_contested_memory_is_not_eligible(
        self,
    ) -> None:
        packet = copy.deepcopy(
            self.valid_packet
        )
        packet["generated_data_units"][0][
            "epistemic_status"
        ] = "contested"
        harvest = SubagentDataHarvester().harvest(
            packet
        )
        unit = harvest.harvested_units[0].to_dict()
        decision = RoutingEngine().route(unit)[0]
        self.assertEqual(
            decision.status,
            "deferred",
        )
if __name__ == "__main__":
    unittest.main()
PY
cat > "$TESTS/golden/test_golden_pipeline.py" <<'PY'
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
from harvester import SubagentDataHarvester
from learning_closure import (
    LearningClosureEvaluator,
)
from packet_validator import PacketValidator
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine
class GoldenPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads(
            (
                FIXTURES
                / "valid-recon-packet.json"
            ).read_text(encoding="utf-8")
        )
    def test_golden_packet_is_deterministic(self) -> None:
        harvester = SubagentDataHarvester()
        first = harvester.harvest(
            self.packet
        ).to_dict()
        second = harvester.harvest(
            self.packet
        ).to_dict()
        self.assertEqual(first, second)
    def test_complete_learning_closure(self) -> None:
        validation = PacketValidator().validate(
            self.packet
        ).to_dict()
        harvest = SubagentDataHarvester().harvest(
            self.packet
        ).to_dict()
        routing_engine = RoutingEngine()
        routes = routing_engine.route_many(
            harvest["harvested_units"]
        )
        promotion_gate = PromotionGate()
        promotions = promotion_gate.evaluate_many(
            harvested_units=harvest[
                "harvested_units"
            ],
            routing_decisions=[
                route.to_dict()
                for route in routes
            ],
            independent_validation_present=True,
            designated_authority_approval=True,
            recurrence_counts={
                unit["unit_id"]: 2
                for unit in harvest[
                    "harvested_units"
                ]
            },
        )
        closure = LearningClosureEvaluator().evaluate(
            campaign_id="campaign-001",
            expected_action_ids=["recon-001"],
            packets=[self.packet],
            validation_reports=[validation],
            harvest_results=[harvest],
            routing_decisions=[
                route.to_dict()
                for route in routes
            ],
            promotion_results=[
                promotion.to_dict()
                for promotion in promotions
            ],
            evidence_archive_complete=True,
        )
        self.assertEqual(
            closure.status,
            "closed",
            closure.to_dict(),
        )
    def test_learning_closure_blocks_missing_packet(
        self,
    ) -> None:
        closure = LearningClosureEvaluator().evaluate(
            campaign_id="campaign-001",
            expected_action_ids=[
                "recon-001",
                "verifier-001",
            ],
            packets=[self.packet],
            validation_reports=[
                PacketValidator().validate(
                    self.packet
                ).to_dict()
            ],
            harvest_results=[],
            routing_decisions=[],
            promotion_results=[],
            evidence_archive_complete=True,
        )
        self.assertEqual(
            closure.status,
            "blocked",
        )
        failed_checks = {
            check.check_id
            for check in closure.checks
            if not check.passed
        }
        self.assertIn(
            "SGD-CLOSE-001",
            failed_checks,
        )
if __name__ == "__main__":
    unittest.main()
PY
cat > "$TESTS/run_wave3_tests.py" <<'PY'
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[1]
def run_suite(
    directory: Path,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(directory),
        "-p",
        "test_*.py",
        "-v",
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return {
        "directory": str(directory),
        "command": command,
        "exit_code": completed.returncode,
        "output": completed.stdout,
        "passed": completed.returncode == 0,
    }
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run all Wave 3 test suites."
    )
    parser.add_argument(
        "--json",
        action="store_true",
    )
    args = parser.parse_args()
    suites = [
        BASE / "tests" / "conformance",
        BASE / "tests" / "routing",
        BASE / "tests" / "negative",
        BASE / "tests" / "golden",
    ]
    results = [
        run_suite(directory)
        for directory in suites
    ]
    if args.json:
        print(
            json.dumps(
                {
                    "passed": all(
                        result["passed"]
                        for result in results
                    ),
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            print(
                f"\n=== {result['directory']} ==="
            )
            print(result["output"])
    return (
        0
        if all(result["passed"] for result in results)
        else 1
    )
if __name__ == "__main__":
    raise SystemExit(main())
PY
python - <<'PY'
from __future__ import annotations
import ast
import hashlib
import json
import sys
from pathlib import Path
try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "ERROR: PyYAML is required for Wave 3 validation"
    ) from exc
try:
    import jsonschema
except ImportError as exc:
    raise SystemExit(
        "ERROR: jsonschema is required for Wave 3 validation"
    ) from exc
base = Path("subagent-generated-data")
adapters = base / "adapters"
tests = base / "tests"
python_files = sorted(
    list(adapters.glob("*.py"))
    + list(tests.rglob("*.py"))
)
json_files = sorted(
    tests.rglob("*.json")
)
yaml_files = sorted(
    (base / "routes").glob("*.yaml")
)
errors: list[str] = []
for path in python_files:
    try:
        ast.parse(
            path.read_text(encoding="utf-8")
        )
    except SyntaxError as exc:
        errors.append(
            f"{path}: Python syntax error: {exc}"
        )
for path in json_files:
    try:
        json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        errors.append(
            f"{path}: JSON error: {exc}"
        )
for path in yaml_files:
    try:
        payload = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        errors.append(
            f"{path}: YAML error: {exc}"
        )
        continue
    if not isinstance(payload, dict):
        errors.append(
            f"{path}: YAML root must be an object"
        )
if errors:
    print("WAVE 3 STATIC VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("WAVE 3 STATIC VALIDATION PASSED")
PY
python "$TESTS/run_wave3_tests.py"
python - <<'PY'
from __future__ import annotations
import hashlib
from pathlib import Path
base = Path("subagent-generated-data")
wave3_files = sorted(
    [
        *list((base / "adapters").glob("*.py")),
        *list((base / "tests").rglob("*.py")),
        *list((base / "tests").rglob("*.json")),
    ]
)
print()
print("FINAL WAVE 3 TREE")
for path in wave3_files:
    print(path)
print()
print("WAVE 3 SHA-256")
for path in wave3_files:
    digest = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    print(f"{digest}  {path}")
PY
echo
echo "Wave 3 installation complete."
echo
echo "Created adapters:"
echo "  $ADAPTERS/graphiti_memory.py"
echo "  $ADAPTERS/l9_python.py"
echo "  $ADAPTERS/odoo.py"
echo
echo "Created test suites:"
echo "  $TESTS/conformance/"
echo "  $TESTS/routing/"
echo "  $TESTS/negative/"
echo "  $TESTS/golden/"
echo
echo "Created fixtures:"
echo "  $FIXTURES/valid-recon-packet.json"
echo "  $FIXTURES/invalid-missing-evidence-packet.json"
