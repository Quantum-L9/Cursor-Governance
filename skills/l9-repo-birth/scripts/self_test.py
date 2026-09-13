#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY = Path("/home/ubuntu/workspace/l9-repo-template")
sys.path.insert(0, str(ROOT / "scripts"))
from package_birth_handoff import HandoffError, package  # noqa: E402

DIGEST = "sha256:" + "a" * 64


def run(*args: str, cwd: Path) -> None:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr or proc.stdout)


def main() -> int:
    if not FACTORY.is_dir():
        print("SKIP: l9-repo-template checkout unavailable")
        return 0
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        source = Path(tmp) / "source"
        source.mkdir()
        run("git", "init", "-b", "main", cwd=source)
        (source / "README.md").write_text("# Fixture\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=source)
        run(
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "fixture",
            cwd=source,
        )
        revision = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
        tree = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
        ).strip()
        evidence = {
            "schema": "l9.repo-birth-evidence/v1",
            "source_repository": "Quantum-L9/fixture",
            "source_revision": revision,
            "source_tree_sha": tree,
            "idea_execute_receipt": DIGEST,
            "gar_decision": DIGEST,
            "plan": DIGEST,
            "campaign_source": DIGEST,
            "pe_receipt": DIGEST,
            "acceptance_evidence_refs": ["receipts/pec.json"],
        }
        evidence_path = Path(tmp) / "evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        result = package(
            source=source,
            evidence_path=evidence_path,
            factory=FACTORY,
            out_dir=Path(tmp) / "out",
            operation="local_validation",
        )
        contract = json.loads(Path(result["contract"]).read_text(encoding="utf-8"))
        assert contract["source"]["revision"] == revision
        assert contract["payload"]["schema"] == "l9.birth-payload/v1"
        (source / "dirty.txt").write_text("drift\n", encoding="utf-8")
        try:
            package(
                source=source,
                evidence_path=evidence_path,
                factory=FACTORY,
                out_dir=Path(tmp) / "dirty",
                operation="local_validation",
            )
        except HandoffError as exc:
            assert "dirty" in str(exc)
        else:
            raise AssertionError("dirty source was accepted")
    print("PASS: l9-repo-birth self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
