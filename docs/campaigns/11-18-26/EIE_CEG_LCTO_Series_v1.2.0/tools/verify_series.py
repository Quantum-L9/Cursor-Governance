#!/usr/bin/env python3
"""Artifact integrity, ownership, and gate DAG checks. No runtime/authority attestation.

This checker is intentionally independent of GitHub and Docker. It verifies the
CAMPAIGN.json source declarations, their companion files, and real negative
controls; never imply its success proves deployed product behavior.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPOS = {
    "https://github.com/Quantum-L9/Enrichment.Inference.Engine",
    "https://github.com/Quantum-L9/Cognitive.Engine.Graphs",
    "https://github.com/Quantum-L9/Constellation.Gate",
}
FORBIDDEN = ("Makefile", "Repo.mk")


def insist(cond: bool, why: str) -> None:
    if not cond:
        raise ValueError(why)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_inventory(root: Path, manifest_name: str = "MANIFEST.json") -> None:
    manifest = json.loads((root / manifest_name).read_text())
    expected = manifest["files"]
    actual = {}
    for p in root.rglob("*"):
        if not p.is_file() or p == root / manifest_name:
            continue
        rel = p.relative_to(root)
        if "__pycache__" in rel.parts or p.name.endswith(".pyc"):
            continue
        actual[rel.as_posix()] = digest(p)
    insist(actual == expected, f"file census/hash mismatch in {root.name}")


def valid_relative_path(s: str) -> bool:
    return (
        bool(s)
        and not s.startswith("/")
        and "\\" not in s
        and all(z not in ("", ".", "..") for z in s.split("/"))
    )


def matching_paths(a: str, b: str) -> bool:
    """Conservative test for overlapping owner paths, including wildcards and directories."""
    if a == b:
        return True
    if fnmatch.fnmatchcase(a, b) or fnmatch.fnmatchcase(b, a):
        return True
    a_glob = any(c in a for c in "*?[")
    b_glob = any(c in b for c in "*?[")
    aprefix = a.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0].rstrip("/")
    bprefix = b.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0].rstrip("/")
    if a.endswith("/") or b.endswith("/"):
        return a.startswith(b) or b.startswith(a)
    if a_glob and b_glob:
        return aprefix.startswith(bprefix) or bprefix.startswith(aprefix)
    if a_glob:
        return b.startswith(aprefix) and (aprefix.endswith("/") or "/" in b[len(aprefix) :])
    if b_glob:
        return a.startswith(bprefix) and (bprefix.endswith("/") or "/" in a[len(bprefix) :])
    return False


def validate_writer_ownership(spec: dict[str, Any]) -> None:
    """Raise on same-phase write collisions, undeclared destinations, or
    forbidden Makefile edits."""
    seen: dict[str, list[tuple[str, str]]] = {}
    ids: set[str] = set()
    for lane in spec["lanes"]:
        lane_id = lane["id"]
        insist(lane_id not in ids, f"duplicate lane {lane_id}")
        ids.add(lane_id)
        insist(lane["kind"] in ("writer", "assurance"), f"unsupported lane kind {lane_id}")
        writers = lane.get("writable_repositories", [])
        readers = lane.get("read_only_repositories", [])
        scoped = lane.get("write_paths", {})
        insist(set(writers).issubset(REPOS), f"out-of-scope writable repository in {lane_id}")
        insist(
            not set(writers) & set(readers), f"repository both read-only and writable in {lane_id}"
        )
        insist(
            set(scoped) == set(writers), f"write_paths mismatch writable repositories for {lane_id}"
        )
        if lane["kind"] == "assurance":
            insist(not writers and not scoped, f"assurance writer {lane_id}")
            continue
        insist(writers and any(scoped.values()), f"writer has no authorized paths: {lane_id}")
        for repo, paths in scoped.items():
            insist(repo in REPOS, f"undeclared repo {repo}")
            for path in paths:
                insist(valid_relative_path(path), f"invalid relative write path {repo}:{path}")
                for forbidden in FORBIDDEN:
                    insist(
                        not matching_paths(path, forbidden),
                        f"forbidden {forbidden} write path {repo}:{path}",
                    )
                for other_lane, other_path in seen.get(repo, []):
                    insist(
                        not matching_paths(path, other_path),
                        (
                            f"write-scope collision in {repo}: {lane_id}:{path} "
                            f"overlaps {other_lane}:{other_path}"
                        ),
                    )
                seen.setdefault(repo, []).append((lane_id, path))


def validate_gate_graph(spec: dict[str, Any], phase_index: int) -> None:
    ids = {g["id"] for g in spec["gates"]}
    insist(len(ids) == len(spec["gates"]), "duplicate gate ID")
    writers = {lane["id"] for lane in spec["lanes"]}
    lookup = {g["id"]: g for g in spec["gates"]}
    for g in spec["gates"]:
        insist(g["status"] == "NOT_RUN", f"untruthful gate state {g['id']}")
        insist(g.get("owner_lane") in writers, f"missing gate owner {g['id']}")
        insist(bool(g.get("required_proof")), f"missing required proof {g['id']}")
        deps = g.get("depends_on") or []
        insist(not (set(deps) - ids), f"unknown gate predecessor {g['id']}")
        insist(g["id"] not in deps, f"self dependent gate {g['id']}")
    for lane in spec["lanes"]:
        insist(
            not (set(lane.get("wait_for_gates", [])) - ids), f"unknown lane wait gate {lane['id']}"
        )
    visiting, done = set(), set()

    def visit(gid: str) -> None:
        insist(gid not in visiting, f"gate cycle at {gid}")
        if gid in done:
            return
        visiting.add(gid)
        for dep in lookup[gid]["depends_on"]:
            visit(dep)
        visiting.remove(gid)
        done.add(gid)

    for gid in ids:
        visit(gid)
    if phase_index < 4:
        insist(
            "G_RAIL" not in ids and "G_PUBLISH" not in ids, f"early Docker gate in P{phase_index}"
        )
        insist(
            "Docker" in spec["campaign"]["observable_done"]
            and "deferred" in spec["campaign"]["observable_done"].lower(),
            f"premature runtime claim P{phase_index}",
        )
    else:
        must = {
            "G0",
            "G_SWEEP",
            "G_SCORE",
            "G_E2E_CODE",
            "G_DOC_PREP",
            "G_PUBLISH",
            "G_RAIL",
            "G_DOC",
            "G_DONE",
        }
        insist(must.issubset(ids), "missing terminal prepublication or runtime gate")
        insist(
            set(lookup["G_PUBLISH"]["depends_on"])
            == {"G_SWEEP", "G_SCORE", "G_E2E_CODE", "G_DOC_PREP"},
            "G_PUBLISH missing prepublication predecessors",
        )
        insist(
            lookup["G_RAIL"]["depends_on"] == ["G_PUBLISH"],
            "Docker rail must depend on publication",
        )
        insist("G_RAIL" in lookup["G_DOC"]["depends_on"], "post-rail docs gate detached")
        insist(lookup["G_E2E_CODE"]["owner_lane"] == "E2E", "E2E proof wrong owner")
        insist(lookup["G_DOC_PREP"]["owner_lane"] == "DOC", "DOC PR proof wrong owner")
        insist(
            not any(
                "G_RAIL" in lane.get("wait_for_gates", [])
                for lane in spec["lanes"]
                if lane["id"] in ("E2E", "DOC")
            ),
            "E2E or DOC publication would wait for Docker, creating a deadlock",
        )


def validate_phase_launch(text: str, continuation: str) -> None:
    # The exact upstream template always renders a generic HOLD. Do not patch a generated file.
    insist(
        "HOLD until explicit operator activation" in text,
        "unexpected native-template launch change",
    )
    insist("Single activation, not five" in continuation, "phase incorrectly reactivates CTO")
    insist(
        "does not require a second operator activation" in continuation,
        "missing single-CTO precedence clarification",
    )
    insist(
        "P4.G_PUBLISH" in continuation and "No `Makefile` or `Repo.mk` changes" in continuation,
        "phase continuation missing Docker/write boundary",
    )


def validate_root(root: Path = ROOT) -> None:
    file_inventory(root)
    series = json.loads((root / "SERIES.json").read_text())
    insist(
        series["single_cto_required"] and series["fixed_pool_max"] <= 5,
        "one CTO/pool limit violated",
    )
    insist(
        series["publication_ssot"] == "current_governed_make_pr_with_verified_explicit_PR_BASE",
        "make pr authority changed",
    )
    insist(series["manual_docker_gate"] == "P4.G_PUBLISH_then_P4.G_RAIL", "Docker gate changed")
    insist(len(series["phases"]) == 5, "phase count changed")
    insist(
        (root / "reference/Recursive Alignment(20261119-032949).md").is_file(),
        "exact kernel missing",
    )
    insist(
        digest(root / "reference/Recursive Alignment(20261119-032949).md")
        == series["alignment_kernel_sha256"],
        "kernel digest mismatch",
    )
    for i, ent in enumerate(series["phases"]):
        insist(ent["phase"] == i, "phase order changed")
        p = root / "phases" / ent["name"]
        insist(p.is_dir(), f"missing phase {p}")
        file_inventory(p)
        spec = json.loads((p / "CAMPAIGN.json").read_text())
        insist(
            spec["campaign"]["status"] == "DRAFT_NOT_ACTIVATED", f"unjustified activation at P{i}"
        )
        insist(spec["campaign"]["version"] == series["version"], f"phase version drift P{i}")
        insist(
            len(spec["lanes"]) == ent["lanes"] and len(spec["gates"]) == ent["gates"],
            f"phase counts wrong P{i}",
        )
        insist(ent["findings"] == len(spec["findings"]), f"finding count drift P{i}")
        insist(digest(p / "MANIFEST.json") == ent["manifest_sha256"], f"phase manifest drift P{i}")
        canonical = (json.dumps(spec, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        insist(
            hashlib.sha256(canonical).hexdigest() == ent["compiled_source_sha256"],
            f"phase source integrity P{i}",
        )
        validate_writer_ownership(spec)
        validate_gate_graph(spec, i)
        validate_phase_launch(
            (p / "00-LCTO-LAUNCH.md").read_text(), (p / "09-SINGLE-CTO-CONTINUATION.md").read_text()
        )
        for lane in spec["lanes"]:
            text = (p / "lanes" / (lane["id"] + ".md")).read_text()
            insist(
                text.startswith("```yaml\nrepository_access:\n"),
                f"lane access header not first {lane['id']}",
            )
            insist(
                "  unlisted_repositories: no_access" in text.split("```", 3)[1],
                f"lane open repository access {lane['id']}",
            )
            if lane["kind"] == "writer":
                insist(
                    any("make pr" in a for a in lane.get("acceptance", [])),
                    "writer bypasses publisher",
                )
        insist(
            any("Makefile and Repo.mk" in x for x in spec["scope"]["exclude"]),
            f"Makefile boundary missing P{i}",
        )
        if i == 1:
            insist(
                "Actual CEG Neo4j node/edge persistence and readback"
                in spec["campaign"]["observable_done"],
                "P1 live graph proof mislabeled",
            )
        if i == 2:
            insist(
                "actual process-kill windows" in spec["campaign"]["observable_done"],
                "P2 live crash proof mislabeled",
            )
        if i == 3:
            insist(
                "actual persistence is verified in P4" in spec["campaign"]["observable_done"],
                "P3 graph-only evidence overclaim",
            )
        if i == 4:
            insist(
                "without executing Docker until G_PUBLISH" in spec["campaign"]["priority_zero"],
                "P4 premature Docker gate",
            )
    print(
        "PASS: five phase source/byte manifests, actual exclusive write paths, "
        "Makefile exclusions, single-CTO launch, DAG acyclicity and Docker barrier"
    )
    print(
        "NOT RUN: host/projection activation, current PR/CI, signed Gate, real Neo4j or production"
    )


if __name__ == "__main__":
    try:
        validate_root()
    except (ValueError, AssertionError, KeyError, TypeError) as err:
        print("FAIL: " + str(err), file=sys.stderr)
        raise SystemExit(1)
