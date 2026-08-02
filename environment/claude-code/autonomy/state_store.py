"""Atomic, digest-verified durable campaign state."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .models import CampaignState

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]


def canonical_digest(state: CampaignState) -> str:
    payload = json.dumps(
        state.to_dict(include_digest=False),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StateStore:
    """File-backed campaign state with atomic writes and integrity checks."""

    def __init__(self, root: Path | str) -> None:
        # No directory is created here: construction must be side-effect-free so
        # the SessionStart bootstrap can probe for campaigns read-only without
        # dirtying a consumer workspace. Write paths (`save`/`checkpoint`) create
        # the tree lazily via `_lock`'s parent mkdir.
        self.root = Path(root)
        self.campaign_dir = self.root / "campaigns"

    def path_for(self, campaign_id: str) -> Path:
        safe = campaign_id.replace("/", "_").replace("..", "_")
        if not safe or safe.startswith("."):
            raise ValueError("invalid campaign_id")
        return self.campaign_dir / f"{safe}.json"

    @contextmanager
    def _lock(self, path: Path) -> Iterator[None]:
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def save(self, state: CampaignState) -> Path:
        path = self.path_for(state.campaign_id)
        with self._lock(path):
            state.state_digest = canonical_digest(state)
            encoded = json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n"
            tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
            tmp.write_text(encoded, encoding="utf-8")
            os.replace(tmp, path)
        return path

    def load(self, campaign_id: str) -> CampaignState:
        path = self.path_for(campaign_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        state = CampaignState.from_dict(raw)
        expected = state.state_digest
        actual = canonical_digest(state)
        if expected and expected != actual:
            raise ValueError(
                f"state digest mismatch for {campaign_id!r}: expected {expected}, got {actual}"
            )
        state.state_digest = actual
        return state

    def list_campaigns(self) -> tuple[str, ...]:
        return tuple(path.stem for path in sorted(self.campaign_dir.glob("*.json")))

    def checkpoint(
        self,
        state: CampaignState,
        *,
        action_id: str,
        evidence: dict[str, object],
        next_action_set: list[str],
    ) -> Path:
        state.checkpoints.append(
            {
                "sequence": len(state.checkpoints) + 1,
                "created_at": datetime.now(UTC).isoformat(),
                "action_id": action_id,
                "evidence": evidence,
                "next_action_set": next_action_set,
            }
        )
        return self.save(state)
