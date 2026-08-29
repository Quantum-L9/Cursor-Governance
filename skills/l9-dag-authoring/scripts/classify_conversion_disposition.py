#!/usr/bin/env python3
"""Classify a SessionDAG CONVERT request against session-deprecation.yaml."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from classify_graph_kind import classify

DISPOSITIONS = {"DELETE_TWIN", "ABSORB_INTO_SKILL", "CONVERT_TO_LANGGRAPH"}
PACK = Path(__file__).resolve().parents[1]
CATALOG_PATH = PACK / "policies" / "session-deprecation.yaml"


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("catalog"), list):
        raise ValueError("session-deprecation.yaml must have a catalog list")
    return data


def _row_by_id(catalog: list, dag_id: str) -> dict | None:
    for row in catalog:
        if isinstance(row, dict) and row.get("dag_id") == dag_id:
            return row
    return None


def _exists(repo: Path, rel: str | None) -> bool:
    if not rel:
        return False
    return (repo / rel).is_file()


def _twin_stategraph_exists(repo: Path, row: dict) -> bool:
    emit_dir = row.get("emit_dir")
    if emit_dir:
        graph_py = repo / emit_dir / "graph.py"
        if graph_py.is_file():
            kind = classify(graph_py)
            return kind.get("graph_kind") == "LANGGRAPH_RUNTIME"
    return False


def classify_row(repo: Path, row: dict | None, dag_id: str | None) -> dict:
    if row is None:
        return {
            "status": "BLOCKED",
            "dag_id": dag_id,
            "disposition": None,
            "reason": "unknown_catalog_id",
        }

    dag_id = str(row.get("dag_id") or dag_id or "")
    source = row.get("source_path")
    disposition = row.get("disposition")
    proof = row.get("proof_path")
    owner = row.get("domain_owner")

    if source:
        kind = classify(repo / source)
        if kind.get("graph_kind") != "SESSION_GUIDANCE":
            return {
                "status": "BLOCKED",
                "dag_id": dag_id,
                "disposition": None,
                "graph_kind": kind.get("graph_kind"),
                "reason": "source_must_be_SESSION_GUIDANCE",
            }

    if disposition not in DISPOSITIONS:
        return {
            "status": "BLOCKED",
            "dag_id": dag_id,
            "disposition": None,
            "reason": "unknown_disposition",
        }

    if disposition in {"DELETE_TWIN", "ABSORB_INTO_SKILL"} and not _exists(repo, proof):
        return {
            "status": "BLOCKED",
            "dag_id": dag_id,
            "disposition": disposition,
            "reason": "missing_proof_path",
            "proof_path": proof,
        }

    if disposition == "CONVERT_TO_LANGGRAPH":
        if not owner:
            return {
                "status": "BLOCKED",
                "dag_id": dag_id,
                "disposition": disposition,
                "reason": "missing_domain_owner",
            }
        if _twin_stategraph_exists(repo, row):
            return {
                "status": "BLOCKED",
                "dag_id": dag_id,
                "disposition": disposition,
                "reason": "twin_StateGraph_already_exists",
            }

    return {
        "status": "PASS",
        "dag_id": dag_id,
        "disposition": disposition,
        "domain_owner": owner,
        "source_path": source,
        "proof_path": proof,
        "emit_dir": row.get("emit_dir"),
    }


def classify_request(repo: Path, dag_id: str, catalog_path: Path = CATALOG_PATH) -> dict:
    data = load_catalog(catalog_path)
    return classify_row(repo, _row_by_id(data["catalog"], dag_id), dag_id)


def classify_all(repo: Path, catalog_path: Path = CATALOG_PATH) -> dict:
    data = load_catalog(catalog_path)
    results = [classify_row(repo, row, row.get("dag_id")) for row in data["catalog"]]
    convert = [r for r in results if r.get("disposition") == "CONVERT_TO_LANGGRAPH"]
    return {
        "status": "PASS" if all(r["status"] == "PASS" for r in results) else "BLOCKED",
        "count": len(results),
        "convert_to_langgraph_count": len(convert),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--dag-id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--catalog", default=str(CATALOG_PATH))
    ns = ap.parse_args(argv)
    repo = Path(ns.repo_root)
    catalog = Path(ns.catalog)
    if ns.all:
        payload = classify_all(repo, catalog)
    elif ns.dag_id:
        payload = classify_request(repo, ns.dag_id, catalog)
    else:
        print(json.dumps({"status": "FAIL", "error": "need --dag-id or --all"}, indent=2))
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload.get("status") == "PASS":
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
