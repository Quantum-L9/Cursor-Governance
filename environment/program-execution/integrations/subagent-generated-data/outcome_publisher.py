from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from adapters.common.imports import load_module


class OutcomePublisher:
    """Publish PE outcomes through the one canonical generated-data ingress."""

    def __init__(self, repository_root: str | Path, database_path: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.database = Path(database_path).resolve()

    def _load_ingress(self):
        path = self.root / "environment/agents/generated-data/ingress/ingest.py"
        ingress_dir = path.parent
        if str(ingress_dir) not in sys.path:
            sys.path.insert(0, str(ingress_dir))
        spec = importlib.util.spec_from_file_location("pe_generated_data_ingest", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["pe_generated_data_ingest"] = module
        spec.loader.exec_module(module)
        return module

    def publish(
        self,
        receipt: dict[str, Any],
        *,
        repository: str,
        base_sha: str,
        agent_id: str,
        campaign_id: str | None = None,
        graph_id: str | None = None,
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_counts: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        """Project and ingest one PE terminal outcome.

        Validation and authority flags are evidence-derived and fail closed.
        Publication errors are returned to the caller through a durable ingress
        receipt; enqueueing is never reported as downstream acceptance.
        """

        if not isinstance(independent_validation_present, bool):
            raise TypeError("independent_validation_present must be a bool")
        if not isinstance(designated_authority_approval, bool):
            raise TypeError("designated_authority_approval must be a bool")
        projection = load_module(
            Path(__file__).with_name("receipt_projection.py"),
            "pes_generated_data_projection",
        )
        packet = projection.generated_data_packet(
            receipt,
            repository=repository,
            base_sha=base_sha,
            agent_id=agent_id,
            campaign_id=campaign_id,
            graph_id=graph_id,
        )
        source_digest = hashlib.sha256(
            json.dumps(receipt, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        ingress = self._load_ingress()
        result = ingress.ingest_packet(
            generated_data_packet=packet,
            source_receipt_digest=source_digest,
            source_kind="program_execution_outcome",
            actor=agent_id,
            repository_root=self.root,
            database_path=self.database,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_counts=dict(recurrence_counts or {}),
            deliver_when_configured=True,
        )
        return {
            "packet_id": packet["packet_id"],
            "source_receipt_digest": source_digest,
            "ingress_receipt": result,
        }
