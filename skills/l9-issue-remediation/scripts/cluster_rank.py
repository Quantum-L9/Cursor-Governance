#!/usr/bin/env python3
"""Rank issue clusters by leverage (shared cause first).

Reads issue_ingest JSON. Emits a queue of all automatable clusters.
Does not pick a single sticky cluster.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
AUTOMATABLE = frozenset({"CODEBASE", "CROSS_REPO", "FALSE_POSITIVE"})


def _validated_output(value: str) -> Path:
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def _parent(ids: dict[str, str], key: str) -> str:
    while ids[key] != key:
        ids[key] = ids[ids[key]]
        key = ids[key]
    return key


def _union(ids: dict[str, str], a: str, b: str) -> None:
    pa, pb = _parent(ids, a), _parent(ids, b)
    if pa != pb:
        ids[pb] = pa


def cluster_issues(issues: list[dict]) -> list[dict]:
    """Group by explicit links; rank shared-cause / cross-repo / severity / oldest."""
    by_id: dict[str, dict] = {}
    for row in issues:
        issue_id = str(row.get("id") or "")
        if not issue_id:
            continue
        by_id[issue_id] = row

    ids = {key: key for key in by_id}
    for issue_id, row in by_id.items():
        for linked in row.get("linked_issues") or []:
            other = str(linked)
            if other in ids:
                _union(ids, issue_id, other)

    groups: dict[str, list[dict]] = {}
    for issue_id, row in by_id.items():
        groups.setdefault(_parent(ids, issue_id), []).append(row)

    clusters: list[dict] = []
    for index, members in enumerate(groups.values(), start=1):
        repos = {str(m.get("repo") or "") for m in members if m.get("repo")}
        sevs = [SEV_RANK.get(str(m.get("severity") or "low"), 9) for m in members]
        updated = [str(m.get("updated_at") or "") for m in members]
        ownerships = {str(m.get("ownership") or "CODEBASE").upper() for m in members}
        if ownerships & {"CROSS_REPO"} or len(repos) > 1:
            ownership = "CROSS_REPO"
        elif ownerships <= {"HUMAN"}:
            ownership = "HUMAN"
        elif ownerships <= {"EXTERNAL"}:
            ownership = "EXTERNAL"
        elif ownerships <= {"HUMAN", "EXTERNAL"}:
            ownership = "HUMAN"
        elif "FALSE_POSITIVE" in ownerships and not (ownerships & {"CODEBASE", "CROSS_REPO"}):
            ownership = "FALSE_POSITIVE"
        else:
            ownership = "CODEBASE"
        issue_ids = [str(m["id"]) for m in members]
        clusters.append(
            {
                "id": f"cluster-{index}",
                "ownership": ownership,
                "severity": next(
                    (k for k, v in SEV_RANK.items() if v == min(sevs)),
                    "low",
                ),
                "root_cause": "shared-link" if len(members) > 1 else "single",
                "owner_repo": sorted(repos)[0] if repos else "",
                "issues": issue_ids,
                "issue_count": len(members),
                "repo_count": len(repos),
                "oldest_updated": min(updated) if updated else "",
                "automatable": ownership in AUTOMATABLE,
            }
        )

    clusters.sort(
        key=lambda c: (
            0 if c["automatable"] else 1,
            -int(c["issue_count"]),
            -int(c["repo_count"]),
            SEV_RANK.get(str(c["severity"]), 9),
            str(c["oldest_updated"]),
        )
    )
    for rank, cluster in enumerate(clusters, start=1):
        cluster["leverage_rank"] = rank
    return clusters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issues", required=True, help="issues.json from issue_ingest.py")
    parser.add_argument("--output", default="clusters.json")
    parser.add_argument(
        "--automatable-only",
        action="store_true",
        help="omit HUMAN/EXTERNAL-only clusters from the mutate queue",
    )
    args = parser.parse_args()
    path = Path(args.issues)
    if not path.is_file():
        raise SystemExit(f"BLOCKED: issues file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = payload.get("issues") if isinstance(payload, dict) else payload
    if not isinstance(issues, list):
        raise SystemExit("BLOCKED: issues payload must be a list or {issues: [...]}")
    clusters = cluster_issues(issues)
    if args.automatable_only:
        clusters = [c for c in clusters if c.get("automatable")]
        for rank, cluster in enumerate(clusters, start=1):
            cluster["leverage_rank"] = rank
    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cluster_count": len(clusters),
        "open_issues": len(issues),
        "clusters": clusters,
    }
    dest = _validated_output(args.output)
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "cluster_count": len(clusters), "open_issues": len(issues)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
