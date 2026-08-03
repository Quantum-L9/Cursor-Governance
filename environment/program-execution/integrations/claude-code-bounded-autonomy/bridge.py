from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.common.subprocess_runner import run_argv


class ClaudeBoundedAutonomyBridge:
    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()
        self.cli = self.root / "environment/claude-code/autonomy/cli.py"
        self.validator = self.root / "environment/claude-code/autonomy/validate_autonomy.py"

    def probe(self) -> dict[str, Any]:
        missing = [str(path) for path in (self.cli, self.validator) if not path.is_file()]
        return {"status": "PASS" if not missing else "BLOCKED", "missing": missing}

    def initialize(
        self,
        campaign_path: Path,
        state_root: Path,
    ) -> dict[str, Any]:
        result = run_argv(
            [
                "python3",
                str(self.cli),
                "init",
                str(campaign_path),
                "--state-root",
                str(state_root),
            ],
            cwd=self.root,
            timeout_seconds=60,
            environment={"L9_AUTONOMY_STATE_DIR": str(state_root)},
        )
        if result.exit_code != 0:
            raise RuntimeError(result.stderr or "bounded-autonomy init failed")
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("bounded-autonomy init output must be an object")
        return value
