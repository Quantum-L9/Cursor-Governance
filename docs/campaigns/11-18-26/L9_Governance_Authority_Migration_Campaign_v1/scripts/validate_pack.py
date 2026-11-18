#!/usr/bin/env python3
"""Offline structural and integrity checks of this execution handoff.

This script verifies pack content only. It does not validate repo state, grant
admission, execute CI, authorize publication, or prove live enforcement.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required for pack structural validation") from exc

ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED = {
    "https://github.com/Quantum-L9/.github",
    "https://github.com/Quantum-L9/Cursor-Governance",
    "https://github.com/Quantum-L9/l9-ci-core",
    "https://github.com/Quantum-L9/L9-Ops-MCP",
    "https://github.com/Quantum-L9/l9-ci-sdk",
    "https://github.com/Quantum-L9/l9-repo-template",
}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_path(relative: str) -> Path:
    path = Path(relative)
    require(
        not path.is_absolute() and relative == path.as_posix(), f"unsafe manifest path: {relative}"
    )
    require(".." not in path.parts, f"traversal: {relative}")
    actual = ROOT / path
    require(actual.is_file() and not actual.is_symlink(), f"missing or nonregular file: {relative}")
    return actual


def header(file: Path) -> dict:
    text = file.read_text(encoding="utf-8")
    require(
        text.startswith("```yaml\nrepository_access:\n"),
        f"delegation header not first: {file.name}",
    )
    pieces = text.split("```", 2)
    require(len(pieces) >= 3, f"no closing delegation header: {file.name}")
    parsed = yaml.safe_load(pieces[1][len("yaml\n") :])
    require(
        isinstance(parsed, dict) and isinstance(parsed.get("repository_access"), dict),
        f"invalid access: {file.name}",
    )
    a = parsed["repository_access"]
    require(
        set(a) == {"writable", "read_only", "unlisted_repositories"},
        f"access keys drift: {file.name}",
    )
    require(a["unlisted_repositories"] == "no_access", f"unlisted access not denied: {file.name}")
    writable, readable = a["writable"], a["read_only"]
    require(
        isinstance(writable, list) and isinstance(readable, list),
        f"access lists invalid: {file.name}",
    )
    require(
        len(writable) == len(set(writable)) and len(readable) == len(set(readable)),
        f"access duplicates: {file.name}",
    )
    require(not (set(writable) & set(readable)), f"read-write collision: {file.name}")
    require(set(writable) | set(readable) <= ALLOWED, f"unlisted repo in header: {file.name}")
    return a


def reachable(a: str, b: str, by_id: dict[str, dict]) -> bool:
    """True if a depends (transitively) on b."""
    stack = list(by_id[a].get("depends_on", []))
    seen = set()
    while stack:
        node = stack.pop()
        if node == b:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(by_id[node].get("depends_on", []))
    return False


def validate() -> None:
    require((ROOT / "MANIFEST.json").is_file(), "missing MANIFEST.json")
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    require(
        manifest.get("schema") == "l9.campaign-pack-manifest/local-v1", "manifest schema invalid"
    )
    expected = manifest["files"]
    require(isinstance(expected, dict) and expected, "manifest empty")
    observed = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json" and not p.is_symlink()
    }
    require(
        observed == set(expected),
        "manifest census mismatch: "
        f"extra={sorted(observed - set(expected))}, "
        f"missing={sorted(set(expected) - observed)}",
    )
    for path, desc in expected.items():
        p = safe_path(path)
        raw = p.read_bytes()
        require(digest(raw) == desc["sha256"], f"digest mismatch: {path}")
        require(len(raw) == desc["bytes"], f"length mismatch: {path}")

    doc = yaml.safe_load((ROOT / "CAMPAIGN.yaml").read_text(encoding="utf-8"))
    require(doc["schema"] == "l9.campaign-handoff/local-v1", "campaign schema invalid")
    require(doc["status"] == "execution_handoff_not_run", "false execution claim")
    require(doc["architecture_frozen"] is True, "architecture not frozen")
    require(doc["publication"]["single_ceremony"] == "make pr", "publish ceremony drift")
    require(doc["publication"]["prohibit_gate_only_smoke_rehearsal"], "smoke gate allowed")
    require(
        doc["allowed_repositories"]["unlisted_repositories"] == "no_access", "repo scope not closed"
    )
    require(len(doc["observed_start_revisions"]) == 4, "incomplete baseline")
    for repo, sha in doc["observed_start_revisions"].items():
        require(bool(HEX40.fullmatch(sha)), f"bad repo SHA for {repo}")
    require(
        doc["concurrency"]["max_mutating_agents_per_worktree"] == 1, "multiwriter collision risk"
    )

    full_w = set(doc["allowed_repositories"]["writable"])
    full_r = set(doc["allowed_repositories"]["read_only"])
    require(
        full_w | full_r == ALLOWED and not full_w & full_r, "declared authorization universe drift"
    )
    launch = header(ROOT / "00_LAUNCH_IN_CTO_MODE.md")
    require(
        set(launch["writable"]) == full_w and set(launch["read_only"]) == full_r,
        "launch access differs from campaign",
    )

    lanes = doc["lanes"]
    by_id = {lane["id"]: lane for lane in lanes}
    require(len(lanes) == len(by_id) == 7, "lane inventory wrong")
    require(set(by_id) == {"S", "A", "B", "C", "M", "E", "F"}, "lane graph changed")
    for lane in lanes:
        lane_id = lane["id"]
        path = safe_path(lane["file"])
        a = header(path)
        expected_write = {f"https://github.com/{r}" for r in lane["writable"]}
        require(set(a["writable"]) == expected_write, f"lane {lane_id} write header mismatch")
        require(
            set(a["writable"]) <= full_w and set(a["read_only"]) <= (full_r | full_w),
            f"lane {lane_id} access mismatch",
        )
        require(len(lane["writable"]) <= 1, f"lane {lane_id} has multi-repo writes")
        for dep in lane.get("depends_on", []) + lane.get("activation_requires", []):
            require(dep in by_id and dep != lane_id, f"unknown or self-dependency {lane_id}->{dep}")
    for lane in lanes:
        require(not reachable(lane["id"], lane["id"], by_id), f"cycle: {lane['id']}")

    for a in lanes:
        for b in lanes:
            if a["id"] >= b["id"]:
                continue
            same_w = set(a["writable"]) & set(b["writable"])
            if same_w:
                require(
                    reachable(a["id"], b["id"], by_id) or reachable(b["id"], a["id"], by_id),
                    f"parallel conflicting repo writers: {a['id']} and {b['id']}",
                )
    require(
        "B" in by_id["E"]["activation_requires"], "Core activation not gated on authentic release"
    )
    require(
        set(by_id["F"]["depends_on"]) >= {"B", "C", "M", "E"},
        "rollout closure bypasses consumers/Core",
    )

    acceptance = doc["mandatory_acceptance_ids"]
    require(
        acceptance == [f"D{i:02d}" for i in range(1, 17)], "mandatory acceptance inventory mismatch"
    )
    coverage = (ROOT / "06_ACCEPTANCE_AND_PROOF.md").read_text()
    for item in acceptance:
        require(
            re.search(rf"^\| {item} \|", coverage, flags=re.MULTILINE) is not None,
            f"missing DoD: {item}",
        )
    invariant_doc = (ROOT / "07_INVARIANT_CONTROL_MATRIX.md").read_text()
    for i in range(1, 14):
        require(f"L9-ORG-{i:03d}" in invariant_doc, f"missing invariant handoff: {i}")
    for i in range(1, 9):
        require(f"L9-CTRL-{i:03d}" in invariant_doc, f"missing control handoff: {i}")
    print(
        f"PACK_STRUCTURAL_PASS {doc['campaign_id']}: "
        f"{len(expected)} SHA256 files, {len(lanes)} lanes, {len(acceptance)} DoD gates"
    )
    print(
        "NOTE: offline pack validation ONLY; "
        "no source PR, signed release or live platform tests were executed"
    )


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"PACK_STRUCTURAL_FAIL {exc}", file=sys.stderr)
        sys.exit(1)
