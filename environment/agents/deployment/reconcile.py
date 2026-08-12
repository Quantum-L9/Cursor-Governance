# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/deployment/reconcile.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Reconcile governed Cursor subagent roles into ~/.cursor/agents.

Desired-state materializer only. Does not schedule, accept results, or mutate
Program Execution state. Authoritative readiness is proven via validate + receipt.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent.parent.parent) not in sys.path:
    # repo root on path so `environment.agents.deployment.*` imports work when
    # invoked as `python3 environment/agents/deployment/reconcile.py`.
    sys.path.insert(0, str(_HERE.parent.parent.parent))

from environment.agents.deployment import receipts as receipt_lib  # noqa: E402
from environment.agents.deployment import validate as validate_lib  # noqa: E402
from environment.agents.deployment.renderers import cursor as cursor_renderer  # noqa: E402

CONTRACT_PATH = _HERE / "DEPLOYMENT_CONTRACT.yaml"
SUPPORTED_SURFACES = frozenset({"cursor"})


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML must be a mapping: {path}")
    return data


def _repo_root_from_here() -> Path:
    return _HERE.parent.parent.parent


def _governance_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _expand_agents_dir(raw: str, *, home: Path | None = None) -> Path:
    text = str(raw)
    if text.startswith("~/"):
        base = home if home is not None else Path.home()
        return (base / text[2:]).expanduser().resolve()
    return Path(text).expanduser().resolve()


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return _load_yaml(path)


def build_expected(
    *,
    repo_root: Path,
    surface_cfg: dict[str, Any],
) -> tuple[dict[str, str], str, str]:
    manifest_rel = str(surface_cfg["roles_manifest"])
    manifest_path = repo_root / manifest_rel
    if not manifest_path.is_file():
        raise FileNotFoundError(f"roles manifest missing: {manifest_path}")
    source_bytes = manifest_path.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    manifest = yaml.safe_load(source_bytes.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("roles manifest must be a mapping")
    roles = manifest.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("roles manifest missing roles mapping")
    role_schema = str(surface_cfg.get("role_schema") or manifest.get("schema") or "")
    renderer_version = str(surface_cfg.get("renderer_version") or cursor_renderer.RENDERER_VERSION)
    expected = cursor_renderer.expected_definitions(
        roles,
        source_rel=manifest_rel,
        role_schema=role_schema,
        source_digest=source_digest,
        renderer_version=renderer_version,
    )
    return expected, source_digest, renderer_version


def reconcile_cursor(
    *,
    repo_root: Path,
    workspace: Path,
    surface_cfg: dict[str, Any],
    agents_dir: Path | None = None,
    home: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Materialize managed Cursor agents and emit a deployment receipt."""
    global_dir = agents_dir or _expand_agents_dir(
        str(surface_cfg["global_agents_dir"]),
        home=home,
    )
    project_rel = str(surface_cfg.get("project_agents_rel") or ".cursor/agents")
    project_dir = (workspace / project_rel).resolve()

    expected, source_digest, renderer_version = build_expected(
        repo_root=repo_root,
        surface_cfg=surface_cfg,
    )
    expected_filenames = set(expected)

    actions: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    rendered_digests = {
        name: cursor_renderer.content_digest(text) for name, text in expected.items()
    }

    if not dry_run:
        global_dir.mkdir(parents=True, exist_ok=True)

    # Create / replace managed; never overwrite unmanaged collisions.
    for filename, text in sorted(expected.items()):
        path = global_dir / filename
        if path.is_file():
            current = path.read_text(encoding="utf-8")
            if cursor_renderer.is_managed(current):
                if current != text:
                    actions.append({"op": "replace_stale_managed", "path": str(path)})
                    if not dry_run:
                        path.write_text(text, encoding="utf-8")
                else:
                    actions.append({"op": "unchanged_managed", "path": str(path)})
            else:
                collisions.append(
                    {
                        "filename": filename,
                        "reason": "unmanaged_name_collision",
                        "path": str(path),
                        "action": "preserved_not_overwritten",
                    }
                )
                actions.append({"op": "skip_unmanaged_collision", "path": str(path)})
        else:
            actions.append({"op": "create_managed", "path": str(path)})
            if not dry_run:
                path.write_text(text, encoding="utf-8")

    # Remove obsolete L9-managed files only.
    if global_dir.is_dir():
        for path in sorted(global_dir.glob("*.md")):
            if path.name in expected_filenames:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if cursor_renderer.is_managed(text):
                actions.append({"op": "remove_obsolete_managed", "path": str(path)})
                if not dry_run:
                    path.unlink()
            else:
                actions.append({"op": "preserve_unmanaged", "path": str(path)})

    validation = validate_lib.validate_deployment(
        expected=expected,
        global_dir=global_dir,
        project_dir=project_dir if project_dir.is_dir() or project_dir.exists() else project_dir,
        collisions=collisions,
    )

    workspace_id = receipt_lib.workspace_id_for(workspace)
    observed_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    receipt_body: dict[str, Any] = {
        "schema": receipt_lib.RECEIPT_SCHEMA,
        "surface": "cursor",
        "workspace": {
            "id": workspace_id,
            "path": str(workspace.resolve()),
        },
        "governance_sha": _governance_sha(repo_root),
        "source_manifest": str(surface_cfg["roles_manifest"]),
        "source_manifest_digest": source_digest,
        "renderer_version": renderer_version,
        "expected_managed_roles": [
            cursor_renderer.ROLE_AGENT_NAMES[k] for k in sorted(cursor_renderer.ROLE_FILENAMES)
        ],
        "rendered_digests": rendered_digests,
        "effective_definition_checks": validation["effective_definition_checks"],
        "shadow_checks": validation["shadow_checks"],
        "collisions": collisions,
        "actions": actions,
        "observed_at": observed_at,
        "status": validation["status"],
    }

    receipt_path: Path | None = None
    if not dry_run:
        receipt_path = receipt_lib.write_deployment_receipt(
            receipt_body,
            surface="cursor",
            workspace_id=workspace_id,
        )

    return {
        "surface": "cursor",
        "status": validation["status"],
        "global_agents_dir": str(global_dir),
        "project_agents_dir": str(project_dir),
        "workspace_id": workspace_id,
        "actions": actions,
        "collisions": collisions,
        "validation": validation,
        "receipt_path": str(receipt_path) if receipt_path else None,
        "receipt": receipt_lib.with_receipt_digest(receipt_body),
        "rendered_digests": rendered_digests,
        "source_manifest_digest": source_digest,
        "renderer_version": renderer_version,
    }


def reconcile(
    *,
    surface: str,
    repo_root: Path,
    workspace: Path,
    agents_dir: Path | None = None,
    home: Path | None = None,
    dry_run: bool = False,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if surface not in SUPPORTED_SURFACES:
        raise ValueError(
            f"unsupported surface {surface!r}; Patch B implements cursor only "
            f"(supported={sorted(SUPPORTED_SURFACES)})"
        )
    contract = contract or load_contract()
    surfaces = contract.get("surfaces") or {}
    surface_cfg = surfaces.get(surface)
    if not isinstance(surface_cfg, dict):
        raise KeyError(f"DEPLOYMENT_CONTRACT missing surface: {surface}")
    return reconcile_cursor(
        repo_root=repo_root,
        workspace=workspace,
        surface_cfg=surface_cfg,
        agents_dir=agents_dir,
        home=home,
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", required=True, choices=sorted(SUPPORTED_SURFACES))
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--agents-dir",
        type=Path,
        default=None,
        help="Override global agents dir (tests / dry fixtures)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    args = parser.parse_args(argv)

    repo_root = (args.repo_root or _repo_root_from_here()).resolve()
    workspace = (args.workspace or Path.cwd()).resolve()

    try:
        result = reconcile(
            surface=args.surface,
            repo_root=repo_root,
            workspace=workspace,
            agents_dir=args.agents_dir.resolve() if args.agents_dir else None,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"ERROR: cursor subagent reconcile failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"cursor subagent reconcile: {result['status']} (workspace_id={result['workspace_id']})"
        )
        if result.get("receipt_path"):
            print(f"receipt: {result['receipt_path']}")
        for action in result.get("actions") or []:
            print(f"  {action['op']}: {action['path']}")
        for blocked in (result.get("validation") or {}).get("blocked") or []:
            label = blocked.get("filename") or blocked.get("path")
            print(f"  BLOCKED: {label}: {blocked.get('reason')}")

    return 0 if result["status"] == validate_lib.STATUS_READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
