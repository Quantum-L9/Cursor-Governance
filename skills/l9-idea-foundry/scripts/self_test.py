#!/usr/bin/env python3
"""Self-test deterministic L9 Idea Foundry scripts without network access."""

from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
MIB = 1024 * 1024


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


def expect_reason(proc: subprocess.CompletedProcess[str], needle: str, label: str) -> None:
    if needle not in proc.stdout:
        raise AssertionError(f"{label}: expected failure reason {needle!r} in:\n{proc.stdout}")


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_fixture(
    root: Path,
    *,
    handoff: str = "EMBEDDED",
    status: str = "CODE_REALIZED_LOCAL",
    results: str = "[PASSED]",
    plan_ref: str = "docs/idea-origin/IMPLEMENTATION.plan.json",
) -> tuple[str, str]:
    inventory_digest = digest(b"idea-source-v1")
    plan_text = '{"schema":"plan","todo":"build core"}\n'
    plan_digest = digest(plan_text.encode("utf-8"))

    write(
        root / "pyproject.toml",
        '[project]\nname = "foundry-fixture"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n',
    )
    write(
        root / ".l9/architecture.yaml",
        """schema: l9.architecture-spec/v1
metadata:
  repository: Quantum-L9/foundry-fixture
identity:
  role: product
""",
    )
    write(root / "src/foundry_fixture/__init__.py", "from .core import normalize\n")
    write(
        root / "src/foundry_fixture/core.py",
        "def normalize(value: str) -> str:\n    return value.strip().lower()\n",
    )
    write(
        root / "tests/test_core.py",
        (
            "from foundry_fixture.core import normalize\n\n"
            "def test_normalize():\n    assert normalize(' A ') == 'a'\n"
        ),
    )
    write(
        root / "scripts/inventory_check.py",
        "def main():\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
    )
    write(root / plan_ref, plan_text)

    write(
        root / "docs/idea-origin/AUTHORITY_MAP.yaml",
        """schema: l9.idea-foundry.authority-map/v1
sources:
  - ref: canon.md
    digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    state: CANONICAL
    governs: [product_thesis]
claims:
  - id: product_thesis
    source_refs: [canon.md]
    state: CANONICAL
    statement: normalize a value
conflicts: []
""",
    )

    planning_extra = (
        "  mode_evidence_ref: skills/l9-plan-simple/SKILL.md\n  compatibility_fallback: false\n"
        if handoff == "EMBEDDED"
        else (
            "  compatibility_fallback: true\n"
            "  fallback_reason: current Plan Simple lacks first-class embedded mode\n"
        )
    )
    write(
        root / "docs/idea-origin/IMPLEMENTATION_BLUEPRINT.yaml",
        f"""schema: l9.idea-foundry.implementation-blueprint/v1
identity:
  repository: foundry-fixture
  package: foundry_fixture
objective:
  product_thesis: normalize a value
  first_executable_outcome: normalize whitespace and case
compilation:
  ingress_role: PRE_CODE_SSOT
  source_inventory_digest: {inventory_digest}
  authority_map_ref: docs/idea-origin/AUTHORITY_MAP.yaml
  raw_source_after_acceptance: EVIDENCE_ONLY
  change_policy: EARLIEST_INVALID_LAYER
beneficiary:
  repository: foundry-fixture
  package: foundry_fixture
  template_class: non_constellation_python
  product_responsibilities: [normalization]
  external_authorities: []
reuse_map:
  - responsibility: normalization
    verified_owner: null
    disposition: OWN_LOCALLY
    evidence_refs: [owner-search:none]
    integration_shape: local_owner
constellation_leverage:
  highest_leverage_move: keep normalization local and tiny
  upstream_reuse: []
  duplicate_owners_avoided: []
  compounding_contracts: []
  future_actions_accelerated: [traceable origin context]
  speculative_abstractions_rejected: [generic plugin system]
invariants: [deterministic]
anti_goals: [deployment]
architecture:
  style: modular_monolith
  stack: {{language: python}}
  owners: [normalization]
  boundaries: [public function]
  modules: [core]
  dependency_direction: [tests -> core]
contracts:
  persisted_models: []
  apis: []
  deterministic_engines: [normalize]
  model_mediated_surfaces: []
intelligence_harvest:
  status: NOT_APPLICABLE
  harvest_ref: null
  receipt_ref: null
  accepted_nugget_refs: []
planning:
  owner: l9-plan-simple
  plan_document_ref: {plan_ref}
  plan_digest: {plan_digest}
  validation_status: PASSED
  plan_handoff: {handoff}
{planning_extra}acceptance:
  path: [call normalize]
  evidence_required: [tests/test_core.py::test_normalize]
unknowns: []
deferred: []
validation_obligations: [python syntax, unit test]
architecture_questions:
  direction:
    verdict: SATISFIED
    evidence_refs: [blueprint]
  constellation_alignment:
    verdict: SATISFIED
    evidence_refs: [reuse_map]
  first_order:
    verdict: SATISFIED
    evidence_refs: [constellation_leverage]
""",
    )
    write(
        root / "docs/idea-origin/TRACEABILITY.yaml",
        """schema: l9.idea-foundry.traceability/v1
capabilities:
  - id: CAP-001
    status: IMPLEMENTED
    requirement_refs: [claim:product_thesis]
    architecture_refs: [blueprint:core]
    harvest_refs: []
    plan_todo_refs: [TODO-001]
    implementation_paths: [src/foundry_fixture/core.py]
    evidence_refs: [tests/test_core.py::test_normalize]
    unknown_ids: []
implementation_decisions:
  - id: DEC-001
    statement: use a pure function
    source_truth: false
    rationale: reversible implementation default
    affected_paths: [src/foundry_fixture/core.py]
""",
    )
    write(root / "docs/idea-origin/UNKNOWN_REGISTER.md", "# Unknowns\n\nNONE\n")
    compatibility_line = (
        "    compatibility_fallback: false\n"
        if handoff == "EMBEDDED"
        else "    compatibility_fallback: true\n"
    )
    write(
        root / "docs/idea-origin/FOUNDRY_RECEIPT.yaml",
        f"""schema: l9.idea-foundry.receipt/v1
run:
  status: {status}
source:
  input_ref: fixture
  inventory_digest: {inventory_digest}
  source_revision: null
composition:
  intelligence_harvest:
    status: NOT_APPLICABLE
    harvest_ref: null
    receipt_ref: null
  gar:
    status: NOT_USED
    decision_ref: null
  planning:
    owner: l9-plan-simple
    plan_document_ref: {plan_ref}
    plan_digest: {plan_digest}
    validation_status: PASSED
    plan_handoff: {handoff}
{compatibility_line}payload:
  path: .
  freeze_binding: EXTERNAL_RECEIPT
  resume_index_ref: docs/idea-origin/FOUNDRY_INDEX.json
validation:
  commands: [python syntax, unit test]
  results: {results}
birth:
  template_repo: Quantum-L9/l9-repo-template
  payload_contract: null
  local_birth_state: null
  remote_birth_state: null
  repository_url: null
deployment:
  performed: false
unknowns: []
deferred: []
""",
    )
    return inventory_digest, plan_digest


def emit_index(
    root: Path,
    inventory_digest: str,
    plan_digest: str,
    *,
    plan_ref: str = "docs/idea-origin/IMPLEMENTATION.plan.json",
    expect: int = 0,
) -> subprocess.CompletedProcess[str]:
    return run(
        PYTHON,
        str(SCRIPT_DIR / "emit_foundry_index.py"),
        str(root),
        "--inventory-digest",
        inventory_digest,
        "--plan-ref",
        plan_ref,
        "--plan-digest",
        plan_digest,
        expect=expect,
    )


def git_commit_all(root: Path, *, email: str, name: str, message: str) -> None:
    run("git", "init", cwd=root)
    run("git", "config", "user.email", email, cwd=root)
    run("git", "config", "user.name", name, cwd=root)
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", message, cwd=root)


def emit_freeze(root: Path, inventory_digest: str, plan_digest: str, out: Path) -> None:
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
        str(out),
    )


def validate(root: Path, *extra: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    return run(
        PYTHON, str(SCRIPT_DIR / "validate_foundry_payload.py"), str(root), *extra, expect=expect
    )


def frozen_fixture(base: Path, name: str, **fixture: str) -> tuple[Path, Path]:
    """Build, index, commit and freeze a fixture; return (root, freeze receipt)."""
    root = base / name
    root.mkdir()
    inventory_digest, plan_digest = build_fixture(root, **fixture)
    emit_index(root, inventory_digest, plan_digest)
    git_commit_all(root, email="foundry@example.invalid", name="Foundry Self Test", message="fx")
    freeze = base / f"{name}.freeze.json"
    emit_freeze(root, inventory_digest, plan_digest, freeze)
    return root, freeze


def inventory(source: Path, *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    return run(PYTHON, str(SCRIPT_DIR / "inventory_idea_pack.py"), str(source), expect=expect)


def check_validator_fail_closed(base: Path) -> None:
    """F2: evidence assertions must be bound to bytes and refuse recorded failure."""
    # Recorded non-passing validation results are rejected, not merely listed.
    failed = base / "failed-results"
    failed.mkdir()
    inv, plan = build_fixture(failed, results="[PASSED, FAILED]")
    emit_index(failed, inv, plan)
    expect_reason(validate(failed, expect=1), "non-passing entries", "failed results")

    # Missing plan file: the digest is asserted, the file is gone.
    missing = base / "missing-plan"
    missing.mkdir()
    inv, plan = build_fixture(missing)
    emit_index(missing, inv, plan)
    (missing / "docs/idea-origin/IMPLEMENTATION.plan.json").unlink()
    expect_reason(validate(missing, expect=1), "plan_document_ref is not a file", "missing plan")

    # Plan reference escaping the payload root is rejected even when the file exists.
    escaped = base / "escaped-plan"
    escaped.mkdir()
    inv, plan = build_fixture(escaped, plan_ref="../escaped.plan.json")
    emit_index(escaped, inv, plan, plan_ref="../escaped.plan.json")
    expect_reason(validate(escaped, expect=1), "escapes payload root", "escaped plan")

    # Plan bytes that no longer hash to the recorded digest are rejected.
    mismatched = base / "mismatched-plan"
    mismatched.mkdir()
    inv, plan = build_fixture(mismatched)
    emit_index(mismatched, inv, plan)
    (mismatched / "docs/idea-origin/IMPLEMENTATION.plan.json").write_text(
        '{"schema":"plan","todo":"something else"}\n', encoding="utf-8"
    )
    expect_reason(validate(mismatched, expect=1), "plan_digest does not match", "plan digest")

    # Non-ready run states cannot be freeze-validated however clean the tree is.
    for state in ("INTAKE", "PLANNED", "QUARANTINED", "BLOCKED"):
        root, freeze = frozen_fixture(base, f"state-{state.lower()}", status=state)
        proc = validate(root, "--freeze-validated", "--freeze-receipt", str(freeze), expect=1)
        expect_reason(proc, f"run.status is {state}", f"state {state}")


def check_archive_budget(base: Path) -> None:
    """F1: untrusted archives stay traversal-safe AND resource-bounded."""
    # Traversal is fail-closed.
    unsafe = base / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as zf:
        zf.writestr("../escape.txt", "nope")
    proc = inventory(unsafe, expect=1)
    expect_reason(proc, "unsafe or unreadable source archive", "traversal")

    # A single member above the per-member budget is rejected before extraction.
    oversized = base / "oversized.zip"
    with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.bin", b"\0" * (33 * MIB))
    expect_reason(inventory(oversized, expect=1), "archive member exceeds", "oversized member")

    # Members individually under budget but collectively over it are rejected.
    total = base / "total.zip"
    with zipfile.ZipFile(total, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i in range(5):
            zf.writestr(f"part{i}.bin", b"\0" * (30 * MIB))
    expect_reason(inventory(total, expect=1), "uncompressed bytes", "total expanded size")

    # A member flood is rejected by count.
    flood = base / "flood.zip"
    with zipfile.ZipFile(flood, "w") as zf:
        for i in range(2049):
            zf.writestr(f"m/{i}.txt", "x")
    expect_reason(inventory(flood, expect=1), "exceeds 2048 members", "member flood")

    # The same budget governs tar archives, and compressed tar (r:*) still opens.
    tar_total = base / "total.tar"
    with tarfile.open(tar_total, "w") as tf:
        for i in range(5):
            info = tarfile.TarInfo(f"part{i}.bin")
            info.size = 30 * MIB
            tf.addfile(info, io.BytesIO(b"\0" * (30 * MIB)))
    expect_reason(inventory(tar_total, expect=1), "uncompressed bytes", "tar total size")

    good_tgz = base / "good.tgz"
    with tarfile.open(good_tgz, "w:gz") as tf:
        info = tarfile.TarInfo("pack/README.md")
        body = b"# pack\n"
        info.size = len(body)
        tf.addfile(info, io.BytesIO(body))
    proc = inventory(good_tgz)
    if '"path": "pack/README.md"' not in proc.stdout:
        raise AssertionError(f"compressed tar member was not inventoried:\n{proc.stdout}")

    good_zip = base / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as zf:
        zf.writestr("pack/notes.txt", "hello")
    proc = inventory(good_zip)
    if '"path": "pack/notes.txt"' not in proc.stdout:
        raise AssertionError(f"zip member was not inventoried:\n{proc.stdout}")


def main() -> int:
    run(PYTHON, str(SCRIPT_DIR / "validate_skill_contract.py"))
    with tempfile.TemporaryDirectory(prefix="foundry-self-test-") as td:
        base = Path(td)
        root = base / "payload"
        root.mkdir()
        inventory_digest, plan_digest = build_fixture(root)

        # First-class embedded path.
        emit_index(root, inventory_digest, plan_digest)
        validate(root)

        # Deterministic index emission: same inputs -> identical bytes.
        first_index = (root / "docs/idea-origin/FOUNDRY_INDEX.json").read_bytes()
        emit_index(root, inventory_digest, plan_digest)
        second_index = (root / "docs/idea-origin/FOUNDRY_INDEX.json").read_bytes()
        if first_index != second_index:
            raise AssertionError("FOUNDRY_INDEX emission is not deterministic")

        # Git/freeze exact-state contract.
        git_commit_all(
            root, email="foundry@example.invalid", name="Foundry Self Test", message="fixture"
        )
        freeze = base / "freeze.json"
        emit_freeze(root, inventory_digest, plan_digest, freeze)
        proc = validate(root, "--freeze-validated", "--freeze-receipt", str(freeze))
        # F3: freeze validation is pre-factory and must never read as readiness.
        if "phase: FREEZE_VALIDATED" not in proc.stdout or "BIRTH_READY" in proc.stdout:
            raise AssertionError(f"freeze validation leaked a readiness signal:\n{proc.stdout}")
        # Compatibility alias keeps the same non-readiness semantics.
        proc = validate(root, "--birth-ready", "--freeze-receipt", str(freeze))
        if "BIRTH_READY" in proc.stdout:
            raise AssertionError("--birth-ready alias emitted BIRTH_READY")

        # Exact-state validation must fail after mutation.
        with (root / "src/foundry_fixture/core.py").open("a", encoding="utf-8") as fh:
            fh.write("\n# changed after freeze\n")
        validate(root, "--freeze-validated", "--freeze-receipt", str(freeze), expect=1)

        # Legacy bounded handoff remains an explicit compatibility path.
        legacy = base / "legacy"
        legacy.mkdir()
        inv2, plan2 = build_fixture(legacy, handoff="EMBEDDED_PRE_BIRTH")
        emit_index(legacy, inv2, plan2)
        validate(legacy)

        # Invalid handoff is rejected before code can claim readiness.
        bad_receipt = legacy / "docs/idea-origin/FOUNDRY_RECEIPT.yaml"
        bad_receipt.write_text(
            bad_receipt.read_text(encoding="utf-8").replace(
                "plan_handoff: EMBEDDED_PRE_BIRTH", "plan_handoff: CURSOR_BUILD"
            ),
            encoding="utf-8",
        )
        emit_index(legacy, inv2, plan2, expect=1)

        check_validator_fail_closed(base)
        check_archive_budget(base)

    run(PYTHON, str(SCRIPT_DIR / "test_factory_qualification.py"))

    print("FOUNDRY_SELF_TEST: PASS")
    print("- embedded_handoff=PASS")
    print("- legacy_handoff_compatibility=PASS")
    print("- deterministic_index=PASS")
    print("- exact_state_freeze=PASS")
    print("- freeze_validated_not_birth_ready=PASS")
    print("- birth_ready_validator_fail_closed=PASS")
    print("- unsafe_archive_rejection=PASS")
    print("- bounded_archive_extraction=PASS")
    print("- factory_qualification=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
