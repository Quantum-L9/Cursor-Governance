import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from inventory_source import inventory_acquisition  # noqa: E402


def _receipt(root=None, *, sha="a" * 40):
    return {
        "schema_version": "1.0",
        "adapter": "remote_repository",
        "locator": "https://github.com/Quantum-L9/example",
        "transport": "connector",
        "source_identity": {
            "kind": "repository",
            "provider": "github",
            "repository": "Quantum-L9/example",
            "immutable_ref": sha,
        },
        "materialized_root": str(root) if root else None,
        "inventory": [],
        "verification": "CONTENT_HASH_DECLARED",
        "limitations": ["transport evidence supplied by runtime connector"],
        "status": "PASS",
    }


def test_legacy_local_path_contract_is_preserved(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "inventory_source.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["status"] == "PASS"
    assert payload["source_identity"]["kind"] == "directory"
    assert payload["inventory"][0]["path"] == "a.txt"


def test_remote_github_is_explicitly_blocked_until_runtime_supplies_receipt() -> None:
    done = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "inventory_source.py"),
            "https://github.com/Quantum-L9/example",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 3
    payload = json.loads(done.stdout)
    assert payload["reason"] == "remote_transport_required"
    assert payload["adapter"] == "remote_repository"
    assert "do not fabricate local checkout proof" in payload["next"]


def test_connector_remote_repository_admits_hashed_virtual_inventory(tmp_path: Path) -> None:
    manifest = _receipt()
    manifest["inventory"] = [
        {
            "path": "README.md",
            "bytes": 5,
            "sha256": hashlib.sha256(b"hello").hexdigest(),
            "classification": "candidate",
        }
    ]
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    identity, rows, verification, error, errors = inventory_acquisition(str(path))
    assert error is None
    assert errors == []
    assert identity["immutable_ref"] == "a" * 40
    assert identity["transport"] == "connector"
    assert rows == manifest["inventory"]
    assert verification == "CONTENT_HASH_DECLARED"


def test_remote_repository_without_immutable_ref_fails_closed(tmp_path: Path) -> None:
    manifest = _receipt()
    manifest["source_identity"].pop("immutable_ref")
    manifest["inventory"] = [
        {
            "path": "README.md",
            "bytes": 5,
            "sha256": hashlib.sha256(b"hello").hexdigest(),
            "classification": "candidate",
        }
    ]
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    _, _, _, error, errors = inventory_acquisition(str(path))
    assert error == "invalid_acquisition_receipt"
    assert "remote_repository requires repository identity with immutable_ref" in errors


def test_materialized_connector_receipt_rehashes_and_detects_tamper(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    source = root / "README.md"
    source.write_text("hello", encoding="utf-8")
    raw = source.read_bytes()
    manifest = _receipt(root, sha="b" * 40)
    manifest["inventory"] = [
        {
            "path": "README.md",
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "classification": "candidate",
        }
    ]
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    identity, rows, verification, error, errors = inventory_acquisition(str(path))
    assert error is None
    assert errors == []
    assert identity["immutable_ref"] == "b" * 40
    assert rows == manifest["inventory"]
    assert verification == "CONTENT_REHASHED"
    source.write_text("tampered", encoding="utf-8")
    _, _, _, error, _ = inventory_acquisition(str(path))
    assert error == "acquisition_inventory_mismatch"


def test_inventory_cli_accepts_acquisition_receipt(tmp_path: Path) -> None:
    manifest = _receipt(sha="c" * 40)
    manifest["inventory"] = [
        {
            "path": "a.py",
            "bytes": 1,
            "sha256": hashlib.sha256(b"x").hexdigest(),
            "classification": "candidate",
        }
    ]
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "inventory_source.py"), "--acquisition", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["status"] == "PASS"
    assert payload["source_identity"]["immutable_ref"] == "c" * 40
    assert payload["verification"] == "CONTENT_HASH_DECLARED"
