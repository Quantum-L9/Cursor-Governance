#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_birth_handoff import HandoffError, package, sha256  # noqa: E402

FIXTURE_COMPILER = r"""#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--template-src", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--source-repository", required=True)
args = parser.parse_args()
source = Path(args.source)
revision = subprocess.check_output(
    ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
).strip()
tree = subprocess.check_output(
    ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
).strip()
Path(args.out).write_text(
    json.dumps(
        {
            "schema": "l9.birth-payload/v1",
            "source": {
                "revision": revision,
                "tree_sha": tree,
                "repository": args.source_repository,
            },
        }
    )
    + "\n",
    encoding="utf-8",
)
"""


def run(*args: str, cwd: Path) -> None:
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr or proc.stdout)


def git_init(path: Path) -> None:
    run("git", "init", "-b", "main", cwd=path)
    run(
        "git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "add", ".", cwd=path
    )
    run(
        "git",
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "fixture",
        cwd=path,
    )


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


def make_source(tmp: Path) -> tuple[Path, dict[str, str], str, str]:
    source = tmp / "source"
    source.mkdir()
    (source / "README.md").write_text("# Fixture\n", encoding="utf-8")
    lineage = write_lineage(source)
    git_init(source)
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    return source, lineage, revision, tree


def make_factory(tmp: Path) -> Path:
    factory = tmp / "factory"
    runner = factory / "scripts" / "birth-runner"
    runner.mkdir(parents=True)
    (runner / "compile_birth_payload.py").write_text(FIXTURE_COMPILER, encoding="utf-8")
    (runner / "new_repo.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    git_init(factory)
    return factory


def evidence_for(lineage: dict[str, str], revision: str, tree: str) -> dict[str, object]:
    return {
        "schema": "l9.repo-birth-evidence/v1",
        "source_repository": "Quantum-L9/fixture",
        "source_revision": revision,
        "source_tree_sha": tree,
        "acceptance_evidence_refs": ["receipts/pec.json"],
        **lineage,
    }


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_raw:
        tmp = Path(tmp_raw)
        source, lineage, revision, tree = make_source(tmp)
        factory = make_factory(tmp)
        evidence = evidence_for(lineage, revision, tree)
        evidence_path = tmp / "evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        missing = tmp / "missing-factory"
        missing.mkdir()
        try:
            package(
                source=source,
                evidence_path=evidence_path,
                factory=missing,
                out_dir=tmp / "missing",
                operation="local_validation",
            )
        except HandoffError as exc:
            if "FACTORY_BIRTH_INTERFACE_UNAVAILABLE" not in str(exc):
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("missing factory interface was accepted")

        result = package(
            source=source,
            evidence_path=evidence_path,
            factory=factory,
            out_dir=tmp / "out",
            operation="local_validation",
        )
        contract = json.loads(Path(result["contract"]).read_text(encoding="utf-8"))
        if contract["source"]["revision"] != revision:
            raise AssertionError("contract revision mismatch")
        if contract["payload"]["schema"] != "l9.birth-payload/v1":
            raise AssertionError("payload schema mismatch")

        (source / "dirty.txt").write_text("drift\n", encoding="utf-8")
        try:
            package(
                source=source,
                evidence_path=evidence_path,
                factory=factory,
                out_dir=tmp / "dirty",
                operation="local_validation",
            )
        except HandoffError as exc:
            if "dirty" not in str(exc):
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("dirty source was accepted")

        fake = dict(evidence)
        fake["idea_execute_receipt"] = "sha256:" + "b" * 64
        fake_path = tmp / "fake.json"
        fake_path.write_text(json.dumps(fake), encoding="utf-8")
        (source / "dirty.txt").unlink()
        try:
            package(
                source=source,
                evidence_path=fake_path,
                factory=factory,
                out_dir=tmp / "fake",
                operation="local_validation",
            )
        except HandoffError as exc:
            if "does not match hashed" not in str(exc):
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("unhashed lineage digest was accepted")
    print("PASS: l9-repo-birth self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
