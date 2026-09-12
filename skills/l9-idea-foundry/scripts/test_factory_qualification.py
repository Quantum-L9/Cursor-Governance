#!/usr/bin/env python3
"""Regression tests for the Foundry -> repository-factory qualification seam."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

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
    compiler = r"""#!/usr/bin/env python3
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
    source={
      "repository":a.source_repository or "Quantum-L9/fixture",
      "revision":git(src,"rev-parse","HEAD"),
      "tree_sha":git(src,"rev-parse","HEAD^{tree}"),
    }
    doc={
      "schema":"l9.birth-payload/v1",
      "source":source,
      "mode":mode,
      "repository_shape":{"matched":matched},
      "packages":{"python":["foundry_fixture"]},
      "files":files,
      "manifest_sha256":hashlib.sha256(("\n".join(lines)+"\n").encode()).hexdigest(),
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
if __name__=="__main__": main()
"""
    write(root / "scripts/birth-runner/compile_birth_payload.py", compiler)
    # Interface fixture for the factory's no-remote birth engine: it accepts the
    # real argument shape and reports the factory's own PASS token. It never
    # creates a repository; the seam under test is Foundry's evidence binding.
    write(
        root / "scripts/birth-runner/new_repo.py",
        (
            "import sys\n"
            "args = sys.argv[1:]\n"
            "assert '--no-remote' in args, args\n"
            "assert '--org-profile-src' in args, args\n"
            "print('fixture birth engine (no repository created)')\n"
            "print('BIRTH: PASS')\n"
        ),
    )
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


def build_org_profile(root: Path) -> None:
    write(root / "profile/CODEOWNERS", "* @quantum-l9/owners\n")
    write(root / "profile/policy.yaml", "schema: fixture-org-profile/v1\nbranch_protection: true\n")
    run("git", "init", cwd=root)
    run("git", "config", "user.email", "org@example.invalid", cwd=root)
    run("git", "config", "user.name", "Org Profile Fixture", cwd=root)
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", "org profile fixture", cwd=root)


def qualify(
    source: Path, freeze: Path, factory: Path, out: Path, *extra: str, expect: int = 0
) -> subprocess.CompletedProcess[str]:
    return run(
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
        *extra,
        expect=expect,
    )


def revalidate(receipt: Path, *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    return run(
        PYTHON, str(SCRIPT_DIR / "validate_birth_qualification.py"), str(receipt), expect=expect
    )


def expect_reason(proc: subprocess.CompletedProcess[str], needle: str, label: str) -> None:
    if needle not in proc.stdout:
        raise AssertionError(f"{label}: expected {needle!r} in:\n{proc.stdout}")


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

        # F3: pre-qualification exact-state validation cannot emit BIRTH_READY.
        pre = run(
            PYTHON,
            str(SCRIPT_DIR / "validate_foundry_payload.py"),
            str(source),
            "--freeze-validated",
            "--freeze-receipt",
            str(freeze),
        )
        if "BIRTH_READY" in pre.stdout or "phase: FREEZE_VALIDATED" not in pre.stdout:
            raise AssertionError(f"pre-factory validation claimed readiness:\n{pre.stdout}")

        # F3: successful FACTORY_COMPILE_PASS is the only source of BIRTH_READY.
        proc = qualify(source, freeze, factory, out)
        expect_reason(proc, "foundry_state=BIRTH_READY", "qualification stdout")
        receipt = out / "birth-qualification-receipt.json"
        doc = json.loads(receipt.read_text(encoding="utf-8"))
        if doc["status"] != "FACTORY_COMPILE_PASS":
            raise AssertionError("factory qualification did not reach FACTORY_COMPILE_PASS")
        if doc["foundry_state"] != "BIRTH_READY":
            raise AssertionError("FACTORY_COMPILE_PASS did not record BIRTH_READY")
        if doc["compiled_birth_payload"]["mode"] != "authoritative":
            raise AssertionError("factory compiler did not prove authoritative mode")
        if not doc["source"]["tracked_tree_digest"].startswith("sha256:"):
            raise AssertionError("qualification did not bind source tracked bytes")
        revalidate(receipt)

        # A receipt cannot self-assert a state its status does not support.
        forged = out / "forged-receipt.json"
        forged_doc = dict(doc)
        forged_doc["foundry_state"] = "LOCAL_BIRTH_PASS"
        forged.write_text(json.dumps(forged_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        expect_reason(revalidate(forged, expect=1), "does not follow from", "forged state")

        # Qualification outputs must never be inside the source they describe.
        qualify(source, freeze, factory, source / "bad-output", expect=1)

        # F4: post-qualification dirty source bytes invalidate the receipt even
        # though HEAD and HEAD^{tree} are unchanged.
        core_py = source / "src/foundry_fixture/core.py"
        original = core_py.read_text(encoding="utf-8")
        core_py.write_text(original + "\n# uncommitted drift\n", encoding="utf-8")
        expect_reason(revalidate(receipt, expect=1), "source worktree is dirty", "dirty tracked")
        core_py.write_text(original, encoding="utf-8")
        revalidate(receipt)
        stray = source / "src/foundry_fixture/stray.py"
        stray.write_text("print('untracked')\n", encoding="utf-8")
        expect_reason(revalidate(receipt, expect=1), "source worktree is dirty", "untracked file")
        stray.unlink()
        revalidate(receipt)

        # F4: local birth binds the organization profile it consumed, and
        # profile drift invalidates LOCAL_BIRTH_PASS.
        org = base / "org-profile"
        org.mkdir()
        build_org_profile(org)
        local_out = base / "local-qualification"
        proc = qualify(
            source,
            freeze,
            factory,
            local_out,
            "--run-local-birth",
            "--repo",
            "foundry-fixture",
            "--pkg",
            "foundry_fixture",
            "--desc",
            "fixture product",
            "--org-profile-src",
            str(org),
        )
        expect_reason(proc, "status=LOCAL_BIRTH_PASS foundry_state=LOCAL_BIRTH_PASS", "local birth")
        local_receipt = local_out / "birth-qualification-receipt.json"
        local_doc = json.loads(local_receipt.read_text(encoding="utf-8"))
        bound = local_doc["local_birth"]["org_profile"]
        if bound["kind"] != "directory" or not bound["git_revision"] or not bound["git_clean"]:
            raise AssertionError(f"organization profile binding incomplete: {bound}")
        revalidate(local_receipt)

        policy = org / "profile/policy.yaml"
        policy_text = policy.read_text(encoding="utf-8")
        policy.write_text(policy_text + "require_signed_commits: true\n", encoding="utf-8")
        expect_reason(
            revalidate(local_receipt, expect=1), "organization profile content drift", "org drift"
        )
        run("git", "add", "profile/policy.yaml", cwd=org)
        run("git", "commit", "-m", "policy change", cwd=org)
        expect_reason(
            revalidate(local_receipt, expect=1), "organization profile content drift", "org commit"
        )
        # Reverting bytes without reverting the revision is still drift.
        policy.write_text(policy_text, encoding="utf-8")
        run("git", "add", "profile/policy.yaml", cwd=org)
        run("git", "commit", "-m", "revert policy change", cwd=org)
        expect_reason(
            revalidate(local_receipt, expect=1), "organization profile revision drift", "org rev"
        )

        # Factory drift invalidates an earlier qualification receipt.
        ownership = factory / "scripts/birth-runner/payload-ownership.yaml"
        ownership.write_text(ownership.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        revalidate(receipt, expect=1)

    print("FOUNDRY_FACTORY_QUALIFICATION_TEST: PASS")
    print("- factory_probe=PASS")
    print("- factory_owned_compile=PASS")
    print("- authoritative_mode=PASS")
    print("- birth_ready_state_ordering=PASS")
    print("- external_contract_location=PASS")
    print("- qualification_revalidation=PASS")
    print("- dirty_source_invalidation=PASS")
    print("- org_profile_binding_and_invalidation=PASS")
    print("- factory_drift_invalidation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
