#!/usr/bin/env python3
"""Regression tests for the Foundry -> repository-factory qualification seam."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import self_test as core

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(*args: str, cwd: Path | None = None, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [*args],
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != expect:
        raise AssertionError(
            f"command exit {proc.returncode}, expected {expect}: {' '.join(args)}\n{proc.stdout}"
        )
    return proc


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_factory_fixture(root: Path) -> None:
    write(
        root / ".l9/architecture.yaml",
        """schema: l9.architecture-spec/v1
metadata:
  repository: Quantum-L9/l9-repo-template
  status: authoritative
  role: non-constellation-python-template
sibling_templates:
  nodes: Quantum-L9/L9-Node-Template
  constellation_deps: Quantum-L9/Constellation.PackageTemplate
""",
    )
    ownership = {
        "schema": "l9.birth-payload-ownership/v1",
        "repository_shape": [
            "pyproject.toml",
            ".l9/architecture.yaml",
            "src",
            "tests",
            "scripts/inventory_check.py",
        ],
        "product": ["src/**", "tests/**"],
        "chassis": [".l9/**", "pyproject.toml", "scripts/**"],
    }
    write(
        root / "scripts/birth-runner/payload-ownership.yaml",
        json.dumps(ownership, indent=2) + "\n",
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/birth-payload.schema.json",
        "title": "l9.birth-payload/v1",
        "type": "object",
        "additionalProperties": False,
    }
    write(
        root / "scripts/birth-runner/schemas/birth-payload.schema.json",
        json.dumps(schema, indent=2) + "\n",
    )
    compiler = r'''#!/usr/bin/env python3
import argparse, hashlib, json, subprocess
from pathlib import Path

def git(root,*args):
    p=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True,check=True)
    return p.stdout.strip()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--source-repository")
    ap.add_argument("--require-mode")
    a=ap.parse_args()
    src=a.source.resolve()
    tracked=git(src,"ls-files").splitlines()
    files=[]
    lines=[]
    for rel in sorted(tracked):
        body=(src/rel).read_bytes()
        h=hashlib.sha256(body).hexdigest()
        files.append({"path":rel,"sha256":h})
        lines.append(f"{h}  {rel}")
    shape=["pyproject.toml",".l9/architecture.yaml","src","tests","scripts/inventory_check.py"]
    matched=[]
    for item in shape:
        if (src/item).exists(): matched.append(item)
    mode="authoritative" if set(matched)==set(shape) else "additive"
    if a.require_mode and mode!=a.require_mode:
        raise SystemExit(3)
    doc={
      "schema":"l9.birth-payload/v1",
      "source":{"repository":a.source_repository or "Quantum-L9/fixture","revision":git(src,"rev-parse","HEAD"),"tree_sha":git(src,"rev-parse","HEAD^{tree}")},
      "mode":mode,
      "repository_shape":{"matched":matched},
      "packages":{"python":["foundry_fixture"]},
      "files":files,
      "manifest_sha256":hashlib.sha256(("\n".join(lines)+"\n").encode()).hexdigest(),
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
'''
    write(root / "scripts/birth-runner/compile_birth_payload.py", compiler)
    write(root / "scripts/birth-runner/new_repo.py", "print('fixture; not executed')\n")
    write(root / "docs/ops/REPO_BIRTH.md", "# Fixture birth contract\n")
    write(root / "scripts/birth-runner/README.md", "# Fixture birth runner\n")
    run("git", "init", cwd=root)
    run("git", "config", "user.email", "factory@example.invalid", cwd=root)
    run("git", "config", "user.name", "Factory Fixture", cwd=root)
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "factory fixture", cwd=root)


def build_frozen_foundry(root: Path, base: Path) -> Path:
    inventory_digest, plan_digest = core.build_fixture(root)
    core.emit_index(root, inventory_digest, plan_digest)
    run("git", "init", cwd=root)
    run("git", "config", "user.email", "foundry@example.invalid", cwd=root)
    run("git", "config", "user.name", "Foundry Fixture", cwd=root)
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "foundry fixture", cwd=root)
    freeze = base / "foundry-freeze.json"
    run(
        PYTHON,
        str(SCRIPT_DIR / "emit_freeze_receipt.py"),
        str(root),
        "--inventory-digest",
        inventory_digest,
        "--plan-ref",
        "docs/idea-origin/IMPLEMENTATION.plan.json",
        "--plan-digest",
        plan_digest,
        "--out",
        str(freeze),
    )
    return freeze


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="foundry-factory-test-") as td:
        base = Path(td)
        source = base / "source"
        source.mkdir()
        freeze = build_frozen_foundry(source, base)
        factory = base / "factory"
        factory.mkdir()
        build_factory_fixture(factory)
        out = base / "qualification"

        run(
            PYTHON,
            str(SCRIPT_DIR / "qualify_birth_handoff.py"),
            str(source),
            "--freeze-receipt",
            str(freeze),
            "--repo-template-root",
            str(factory),
            "--source-repository",
            "Quantum-L9/foundry-fixture",
            "--out-dir",
            str(out),
        )
        receipt = out / "birth-qualification-receipt.json"
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        if doc["status"] != "FACTORY_COMPILE_PASS":
            raise AssertionError("factory qualification did not reach FACTORY_COMPILE_PASS")
        if doc["compiled_birth_payload"]["mode"] != "authoritative":
            raise AssertionError("factory compiler did not prove authoritative mode")
        run(PYTHON, str(SCRIPT_DIR / "validate_birth_qualification.py"), str(receipt))

        # Qualification outputs must never be inside the source they describe.
        run(
            PYTHON,
            str(SCRIPT_DIR / "qualify_birth_handoff.py"),
            str(source),
            "--freeze-receipt",
            str(freeze),
            "--repo-template-root",
            str(factory),
            "--source-repository",
            "Quantum-L9/foundry-fixture",
            "--out-dir",
            str(source / "bad-output"),
            expect=1,
        )

        # Factory drift invalidates an earlier qualification receipt.
        ownership = factory / "scripts/birth-runner/payload-ownership.yaml"
        ownership.write_text(ownership.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        run(PYTHON, str(SCRIPT_DIR / "validate_birth_qualification.py"), str(receipt), expect=1)

    print("FOUNDRY_FACTORY_QUALIFICATION_TEST: PASS")
    print("- factory_probe=PASS")
    print("- factory_owned_compile=PASS")
    print("- authoritative_mode=PASS")
    print("- external_contract_location=PASS")
    print("- qualification_revalidation=PASS")
    print("- factory_drift_invalidation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
