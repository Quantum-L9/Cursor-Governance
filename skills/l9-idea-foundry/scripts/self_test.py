#!/usr/bin/env python3
"""Self-test deterministic L9 Idea Foundry scripts without network access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

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


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_fixture(root: Path, *, handoff: str = "EMBEDDED") -> tuple[str, str]:
    inventory_digest = digest(b"idea-source-v1")
    plan_text = '{"schema":"plan","todo":"build core"}\n'
    plan_digest = digest(plan_text.encode("utf-8"))
    plan_ref = "docs/idea-origin/IMPLEMENTATION.plan.json"

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
        "from foundry_fixture.core import normalize\n\ndef test_normalize():\n    assert normalize(' A ') == 'a'\n",
    )
    write(root / "scripts/inventory_check.py", "def main():\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n")
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
        else "  compatibility_fallback: true\n  fallback_reason: current Plan Simple lacks first-class embedded mode\n"
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
    compatibility_line = "    compatibility_fallback: false\n" if handoff == "EMBEDDED" else "    compatibility_fallback: true\n"
    write(
        root / "docs/idea-origin/FOUNDRY_RECEIPT.yaml",
        f"""schema: l9.idea-foundry.receipt/v1
run:
  status: CODE_REALIZED_LOCAL
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
  results: [PASSED]
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


def emit_index(root: Path, inventory_digest: str, plan_digest: str) -> None:
    run(
        PYTHON,
        str(SCRIPT_DIR / "emit_foundry_index.py"),
        str(root),
        "--inventory-digest",
        inventory_digest,
        "--plan-ref",
        "docs/idea-origin/IMPLEMENTATION.plan.json",
        "--plan-digest",
        plan_digest,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="foundry-self-test-") as td:
        base = Path(td)
        root = base / "payload"
        root.mkdir()
        inventory_digest, plan_digest = build_fixture(root)

        # First-class embedded path.
        emit_index(root, inventory_digest, plan_digest)
        run(PYTHON, str(SCRIPT_DIR / "validate_foundry_payload.py"), str(root))

        # Deterministic index emission: same inputs -> identical bytes.
        first_index = (root / "docs/idea-origin/FOUNDRY_INDEX.json").read_bytes()
        emit_index(root, inventory_digest, plan_digest)
        second_index = (root / "docs/idea-origin/FOUNDRY_INDEX.json").read_bytes()
        if first_index != second_index:
            raise AssertionError("FOUNDRY_INDEX emission is not deterministic")

        # Git/freeze exact-state contract.
        run("git", "init", cwd=root)
        run("git", "config", "user.email", "foundry@example.invalid", cwd=root)
        run("git", "config", "user.name", "Foundry Self Test", cwd=root)
        run("git", "add", ".", cwd=root)
        run("git", "commit", "-m", "fixture", cwd=root)
        freeze = base / "freeze.json"
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
        run(
            PYTHON,
            str(SCRIPT_DIR / "validate_foundry_payload.py"),
            str(root),
            "--birth-ready",
            "--freeze-receipt",
            str(freeze),
        )

        # Exact-state validation must fail after mutation.
        with (root / "src/foundry_fixture/core.py").open("a", encoding="utf-8") as fh:
            fh.write("\n# changed after freeze\n")
        run(
            PYTHON,
            str(SCRIPT_DIR / "validate_foundry_payload.py"),
            str(root),
            "--birth-ready",
            "--freeze-receipt",
            str(freeze),
            expect=1,
        )

        # Legacy bounded handoff remains an explicit compatibility path.
        legacy = base / "legacy"
        legacy.mkdir()
        inv2, plan2 = build_fixture(legacy, handoff="EMBEDDED_PRE_BIRTH")
        emit_index(legacy, inv2, plan2)
        run(PYTHON, str(SCRIPT_DIR / "validate_foundry_payload.py"), str(legacy))

        # Invalid handoff is rejected before code can claim readiness.
        bad_receipt = legacy / "docs/idea-origin/FOUNDRY_RECEIPT.yaml"
        bad_receipt.write_text(
            bad_receipt.read_text(encoding="utf-8").replace(
                "plan_handoff: EMBEDDED_PRE_BIRTH", "plan_handoff: CURSOR_BUILD"
            ),
            encoding="utf-8",
        )
        run(
            PYTHON,
            str(SCRIPT_DIR / "emit_foundry_index.py"),
            str(legacy),
            "--inventory-digest",
            inv2,
            "--plan-ref",
            "docs/idea-origin/IMPLEMENTATION.plan.json",
            "--plan-digest",
            plan2,
            expect=1,
        )

        # Source archive traversal is fail-closed.
        unsafe = base / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as zf:
            zf.writestr("../escape.txt", "nope")
        proc = run(
            PYTHON,
            str(SCRIPT_DIR / "inventory_idea_pack.py"),
            str(unsafe),
            expect=1,
        )
        if "unsafe or unreadable source archive" not in proc.stdout:
            raise AssertionError("unsafe archive failure did not preserve its reason")

    print("FOUNDRY_SELF_TEST: PASS")
    print("- embedded_handoff=PASS")
    print("- legacy_handoff_compatibility=PASS")
    print("- deterministic_index=PASS")
    print("- exact_state_freeze=PASS")
    print("- unsafe_archive_rejection=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
