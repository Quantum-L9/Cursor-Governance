"""Durable lease management for long-running concurrent action lanes."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class ClaimLease:
    campaign_id: str
    action_id: str
    holder_agent_id: str
    acquired_at: str
    renewed_at: str
    expires_at: str
    status: str
    resume_cursor: str | None = None
    last_verified_commit: str | None = None

    def expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return datetime.fromisoformat(self.expires_at) <= current


class LeaseConflict(RuntimeError):
    pass


class LeaseStore:
    MAX_TTL = timedelta(hours=24)

    def __init__(self, root: Path | str) -> None:
        self.path = Path(root) / "leases.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, dict[str, object]]) -> None:
        tmp = self.path.with_suffix(f".json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def _key(self, campaign_id: str, action_id: str) -> str:
        return f"{campaign_id}:{action_id}"

    def _with_lock(self):
        lock_path = self.path.with_suffix(".lock")
        handle = lock_path.open("a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def acquire(
        self,
        *,
        campaign_id: str,
        action_id: str,
        holder_agent_id: str,
        ttl: timedelta = timedelta(hours=4),
        resume_cursor: str | None = None,
        last_verified_commit: str | None = None,
        now: datetime | None = None,
    ) -> ClaimLease:
        if ttl <= timedelta(0) or ttl > self.MAX_TTL:
            raise ValueError("lease ttl must be greater than zero and no more than 24 hours")
        current = now or datetime.now(UTC)
        key = self._key(campaign_id, action_id)
        handle = self._with_lock()
        try:
            payload = self._read()
            existing_raw = payload.get(key)
            if existing_raw:
                existing = ClaimLease(**existing_raw)  # type: ignore[arg-type]
                if not existing.expired(current) and existing.holder_agent_id != holder_agent_id:
                    raise LeaseConflict(
                        f"action {action_id!r} is leased by {existing.holder_agent_id!r}"
                    )
            acquired_at = (
                str(existing_raw.get("acquired_at"))
                if existing_raw and existing_raw.get("holder_agent_id") == holder_agent_id
                else current.isoformat()
            )
            lease = ClaimLease(
                campaign_id=campaign_id,
                action_id=action_id,
                holder_agent_id=holder_agent_id,
                acquired_at=acquired_at,
                renewed_at=current.isoformat(),
                expires_at=(current + ttl).isoformat(),
                status="running",
                resume_cursor=resume_cursor,
                last_verified_commit=last_verified_commit,
            )
            payload[key] = asdict(lease)
            self._write(payload)
            return lease
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def renew(
        self,
        *,
        campaign_id: str,
        action_id: str,
        holder_agent_id: str,
        ttl: timedelta = timedelta(hours=4),
        resume_cursor: str | None = None,
        last_verified_commit: str | None = None,
        now: datetime | None = None,
    ) -> ClaimLease:
        key = self._key(campaign_id, action_id)
        payload = self._read()
        raw = payload.get(key)
        if not raw:
            raise LeaseConflict(f"no active lease for action {action_id!r}")
        existing = ClaimLease(**raw)  # type: ignore[arg-type]
        if existing.holder_agent_id != holder_agent_id:
            raise LeaseConflict(
                f"lease holder mismatch: {existing.holder_agent_id!r} != {holder_agent_id!r}"
            )
        return self.acquire(
            campaign_id=campaign_id,
            action_id=action_id,
            holder_agent_id=holder_agent_id,
            ttl=ttl,
            resume_cursor=resume_cursor if resume_cursor is not None else existing.resume_cursor,
            last_verified_commit=(
                last_verified_commit
                if last_verified_commit is not None
                else existing.last_verified_commit
            ),
            now=now,
        )

    def release(self, *, campaign_id: str, action_id: str, holder_agent_id: str) -> None:
        key = self._key(campaign_id, action_id)
        handle = self._with_lock()
        try:
            payload = self._read()
            raw = payload.get(key)
            if not raw:
                return
            existing = ClaimLease(**raw)  # type: ignore[arg-type]
            if existing.holder_agent_id != holder_agent_id:
                raise LeaseConflict(
                    f"lease holder mismatch: {existing.holder_agent_id!r} != {holder_agent_id!r}"
                )
            del payload[key]
            self._write(payload)
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
