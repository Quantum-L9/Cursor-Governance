from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from adapters.common.imports import load_module


class OutcomePublisher:
    def __init__(self, repository_root: str | Path, database_path: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.database = Path(database_path).resolve()

    def publish(
        self,
        receipt: dict[str, Any],
        *,
        repository: str,
        base_sha: str,
        agent_id: str,
    ) -> dict[str, Any]:
        orchestration = self.root / "subagent-generated-data/orchestration"
        if not orchestration.is_dir():
            raise FileNotFoundError(orchestration)
        projection = load_module(
            Path(__file__).with_name("receipt_projection.py"),
            "pes_generated_data_projection",
        )
        sys.path.insert(0, str(orchestration))
        try:
            from processor import GeneratedDataProcessor, ProcessingConfiguration

            packet = projection.generated_data_packet(
                receipt,
                repository=repository,
                base_sha=base_sha,
                agent_id=agent_id,
            )
            processor = GeneratedDataProcessor(
                ProcessingConfiguration(
                    repository_root=str(self.root),
                    database_path=str(self.database),
                )
            )
            result = processor.process_packet(
                packet,
                actor=agent_id,
                independent_validation_present=True,
                designated_authority_approval=True,
                recurrence_counts={},
            )
            if hasattr(result, "to_dict"):
                return result.to_dict()
            return {"result": str(result)}
        finally:
            sys.path.remove(str(orchestration))
