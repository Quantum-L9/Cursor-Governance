"""Shared admission helpers for PE blueprint tooling (compile / accept / evidence).

Owned by ``environment/program-execution/scripts/``. Every mutation helper here
leaves MANIFEST.yaml digest-coherent (callers run :func:`write_manifest` after
changing tree content), and the placeholder scan reuses the canonical
validator's own ``PLACEHOLDERS`` patterns — this module never invents its own
admission semantics.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import yaml

PE_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (
    PE_ROOT / "core" / "program-execution-blueprint-template" / "scripts" / "validate_blueprint.py"
)
_VALIDATOR_MODULE_NAME = "pec_validate_blueprint"
_SCAN_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py"}


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, data: Any) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, width=110, allow_unicode=True),
        encoding="utf-8",
    )


def load_validator() -> Any:
    """Load the canonical Blueprint validator module (cached by module name)."""
    spec = importlib.util.spec_from_file_location(_VALIDATOR_MODULE_NAME, VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validate_blueprint.py: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_blueprint(root: Path, mode: str) -> list[str]:
    """Run the canonical Blueprint validator; returns [] on PASS."""
    return list(load_validator().validate(Path(root), mode))


def scan_placeholders(root: Path) -> list[str]:
    """Mirror the validator's placeholder scan (same patterns, same file classes)."""
    patterns = list(load_validator().PLACEHOLDERS)
    found: list[str] = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SCAN_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                found.append(f"{path.relative_to(root)}: unresolved placeholder {match.group(0)}")
                break
    return found


def write_manifest(root: Path, compiled_from: str) -> None:
    """Canonical Blueprint MANIFEST.yaml generator (digest of every tree file)."""
    files = []
    for path in sorted(Path(root).rglob("*")):
        if (
            path.is_file()
            and path.name != "MANIFEST.yaml"
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ):
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    dump_yaml(
        Path(root) / "MANIFEST.yaml",
        {
            "schema": "program-execution-blueprint.manifest.v2",
            "schema_version": "2.0.0",
            "template": "program-execution-blueprint",
            "compiled_from": compiled_from,
            "files": files,
            "integrity": {"algorithm": "sha256", "self_excluded": True},
        },
    )


def patch_phase0_operator_name(root: Path, owner: str) -> bool:
    """Fill PHASE0_USER_CONFIG.operator_ack.name when it is the template placeholder."""
    path = Path(root) / "PHASE0_USER_CONFIG.yaml"
    if not path.is_file():
        return False
    data = load_yaml(path)
    ack = dict(data.get("operator_ack") or {})
    name = str(ack.get("name") or "")
    if name and not name.startswith("REPLACE_WITH_"):
        return False
    ack["name"] = str(owner)
    data["operator_ack"] = ack
    dump_yaml(path, data)
    return True


def lock_exists_for_blueprint(root: Path) -> bool:
    """True when an existing program-lock binds this blueprint root.

    Post-bootstrap guard for pre-admission tools: once a Controller workspace
    is bootstrapped from a blueprint, its lock digests freeze the blueprint's
    source files — editing them afterwards poisons every verification with
    STALE, so admission tools must refuse.
    """
    target = str(Path(root).resolve())
    base = Path.home() / ".l9" / "programs"
    if not base.is_dir():
        return False
    for lock_path in base.glob("*/runtime/program-lock.json"):
        try:
            data = load_json(lock_path)
        except (OSError, json.JSONDecodeError):
            continue
        try:
            if str(Path(data.get("blueprint_root") or "").resolve()) == target:
                return True
        except OSError:
            continue
    return False
