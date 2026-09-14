#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY = Path(os.environ["L9_REPO_TEMPLATE"]) if os.environ.get("L9_REPO_TEMPLATE") else Path()
sys.path.insert(0, str(ROOT / "scripts"))
from package_birth_handoff import HandoffError, package, sha256  # noqa: E402


def run(*args: str, cwd: Path) -> None:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr or proc.stdout)


def write_lineage(source: Path) -> dict[str, str]:
    evidence_dir = source / "lineage"
    evidence_dir.mkdir()
    paths = {
        "idea_execute_receipt": evidence_dir / "idea-execute-receipt.json",
        "gar_decision": evidence_dir / "gar-decision.json",
        "plan": evidence_dir / "plan.json",
        "campaign_source": evidence_dir / "campaign-source.yaml",
        "pe_receipt": evidence_dir / "pe-receipt.json",
    }
    paths["idea_execute_receipt"].write_text(
        '{"schema":"l9.idea-execute-receipt/v1"}\n', encoding="utf-8"
    )
    paths["gar_decision"].write_text(
        '{"schema":"l9.gar.product-architecture-decision/v1"}\n', encoding="utf-8"
    )
    paths["plan"].write_text('{"schema":"l9.plan-document/v1"}\n', encoding="utf-8")
    paths["campaign_source"].write_text("schema: l9.campaign-source/v2\n", encoding="utf-8")
    paths["pe_receipt"].write_text(
        '{"schema":"l9.program-execution-receipt/v1"}\n', encoding="utf-8"
    )
    (source / "receipts").mkdir()
    (source / "receipts" / "pec.json").write_text(
        '{"schema":"l9.pec-receipt/v1"}\n', encoding="utf-8"
    )
    out = {}
    for key, path in paths.items():
        out[key] = sha256(path)
        out[f"{key}_path"] = str(path.relative_to(source))
    return out


def main() -> int:
    if not FACTORY.is_dir():
        print("SKIP: l9-repo-template checkout unavailable; set L9_REPO_TEMPLATE")
        return 0
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        source = Path(tmp) / "source"
        source.mkdir()
        run("git", "init", "-b", "main", cwd=source)
        (source / "README.md").write_text("# Fixture\n", encoding="utf-8")
        lineage = write_lineage(source)
        run("git", "add", "README.md", "lineage", "receipts", cwd=source)
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
            "acceptance_evidence_refs": ["receipts/pec.json"],
            **lineage,
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
        fake = dict(evidence)
        fake["idea_execute_receipt"] = "sha256:" + "b" * 64
        fake_path = Path(tmp) / "fake.json"
        fake_path.write_text(json.dumps(fake), encoding="utf-8")
        (source / "dirty.txt").unlink()
        try:
            package(
                source=source,
                evidence_path=fake_path,
                factory=FACTORY,
                out_dir=Path(tmp) / "fake",
                operation="local_validation",
            )
        except HandoffError as exc:
            assert "does not match hashed" in str(exc)
        else:
            raise AssertionError("unhashed lineage digest was accepted")
    print("PASS: l9-repo-birth self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
