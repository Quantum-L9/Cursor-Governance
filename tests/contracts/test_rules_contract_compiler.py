from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "ops" / "contracts"
ADAPTERS = CONTRACTS / "adapters"
SCRIPTS = ROOT / "ops" / "scripts"
for directory in (CONTRACTS, ADAPTERS, SCRIPTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from build_rules import build_projection_index  # noqa: E402
from cursor_rules import load_rule_binding  # noqa: E402
from render_cursor_rule import (  # noqa: E402
    enforce_context_budget,
    render_cursor_rule,
)
from resolve_rule_contracts import (  # noqa: E402
    canonical_contract_digest,
    load_contract_index,
    resolve_binding,
)
from validate_rule_binding import validate_binding  # noqa: E402


def _write_yaml(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            value,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        ),
        encoding="utf-8",
    )


def _contract(
    contract_id: str = "TEST.RULE.001",
    *,
    version: str = "1.0.0",
    status: str = "active",
    effect: str = "require",
    clause_id: str = "C01",
    subject: str = "governed_actor",
    action: str = "perform_validated_action",
    obj: str = "target",
    paths: list[str] | None = None,
) -> dict:
    document = {
        "metadata": {
            "contract_id": contract_id,
            "version": version,
            "kind": "invariant",
            "status": status,
            "title": "Test contract",
            "summary": "Fixture.",
            "owner": "tests",
            "domain": "testing",
        },
        "authority": {
            "tier": "domain",
            "semantic_owner": "contract",
            "override_policy": "higher_authority_only",
            "lower_tier_redefinition": "forbidden",
        },
        "scope": {
            "actors": ["agent"],
            "operations": ["test"],
            "resources": ["*"],
            "environments": ["*"],
            "paths": paths or [],
        },
        "normative_clauses": [
            {
                "clause_id": clause_id,
                "effect": effect,
                "subject": subject,
                "action": action,
                "object": obj,
                "conditions": [],
                "exceptions": [],
                "parameters": {},
            }
        ],
        "dependencies": {
            "requires_contracts": [],
            "conflicts_with": [],
        },
        "enforcement": {
            "class": "mechanical",
            "severity": "blocker",
            "failure_mode": "fail_closed",
            "validators": ["test"],
        },
        "evidence_obligations": [],
        "projections": {
            "binding_refs": [],
        },
        "provenance": {
            "origin": "authored",
            "source_refs": [],
        },
        "integrity": {
            "canonical_serialization": "deterministic_yaml_normalization_v1",
            "content_digest": None,
        },
        "lifecycle": {
            "introduced_at": "2026-08-14",
            "supersedes": [],
            "deprecated_by": None,
            "change_policy": "semantic_versioning",
        },
    }
    document["integrity"]["content_digest"] = canonical_contract_digest(document)
    return document


def _binding(
    *,
    contract_id: str = "TEST.RULE.001",
    clause_id: str = "C01",
    mode: str = "auto_attached",
    globs: list[str] | None = None,
    migration_state: str = "generated",
    budget: int = 4096,
    output: str = "rules/40-test-contract.mdc",
) -> dict:
    activation = {
        "mode": mode,
        "globs": globs if globs is not None else ["src/**/*.py"],
        "justification_ref": None,
        "description": "Apply test rule.",
    }
    if mode == "always":
        activation["globs"] = []
        activation["justification_ref"] = contract_id
    return {
        "schema_ref": "canonical.schema.rule_activation_binding.v1",
        "binding_identity": {
            "binding_id": "RULE.CURSOR.TEST_CONTRACT.001",
            "version": "1.0.0",
            "status": "active",
        },
        "target": {
            "platform": "cursor",
            "format": "mdc",
            "output_path": output,
        },
        "rule_identity": {
            "rule_id": "l9.rule.test.contract",
            "rule_version": "1.0.0",
            "title": "Test Contract",
            "description": "Apply test contract.",
            "scope": "repository",
            "domain": "testing",
        },
        "activation": activation,
        "contract_bindings": [
            {
                "contract_id": contract_id,
                "version_constraint": "^1.0",
                "clauses": [clause_id],
                "scope_narrowing": None,
            }
        ],
        "guidance": {
            "refs": [],
            "inline": [],
        },
        "render": {
            "renderer": "cursor_mdc_v1",
            "include_rationale": False,
            "include_examples": False,
            "context_budget_bytes": budget,
        },
        "lifecycle": {
            "migration_state": migration_state,
            "replacement_binding_ref": None,
        },
        "integrity": {
            "canonical_serialization": "deterministic_yaml_normalization_v1",
            "binding_digest": None,
        },
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "rules").mkdir()
    (tmp_path / "contracts" / "domains" / "testing").mkdir(parents=True)
    (tmp_path / "contracts" / "projections" / "rules").mkdir(parents=True)
    return tmp_path


def _install_contract(
    repo: Path,
    document: dict,
    name: str = "test-rule.yaml",
) -> Path:
    path = repo / "contracts" / "domains" / "testing" / name
    _write_yaml(path, document)
    return path


def _install_binding(
    repo: Path,
    document: dict,
    name: str = "test-rule.yaml",
) -> Path:
    path = repo / "contracts" / "projections" / "rules" / name
    _write_yaml(path, document)
    return path


def _resolved(repo: Path) -> tuple[object, dict]:
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    return binding, resolve_binding(binding, index)


def test_valid_binding_resolves(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    binding, resolution = _resolved(repo)
    assert resolution["binding_id"] == binding.binding_id
    assert resolution["resolved_contracts"][0]["contract_id"] == "TEST.RULE.001"
    assert resolution["directives"][0]["clause_id"] == "C01"


def test_render_is_deterministic(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    _, resolution = _resolved(repo)
    first = render_cursor_rule(resolution)
    second = render_cursor_rule(copy.deepcopy(resolution))
    assert first == second
    assert "<!-- GENERATED FILE — DO NOT EDIT -->" in first
    assert "`[TEST.RULE.001:C01]`" in first


def test_generated_rule_contains_native_frontmatter(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    _, resolution = _resolved(repo)
    rendered = render_cursor_rule(resolution)
    assert rendered.startswith("---\n")
    assert "alwaysApply: false" in rendered
    assert "id: l9.rule.test.contract" in rendered
    assert "authority: reference_only" in rendered


def test_missing_contract_is_blocking(repo: Path) -> None:
    _install_binding(repo, _binding(contract_id="MISSING.RULE.001"))
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-CONTRACT-MISSING" for finding in findings)


def test_missing_clause_is_blocking(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding(clause_id="C99"))
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-CLAUSE-MISSING" for finding in findings)


def test_retired_contract_is_blocking(repo: Path) -> None:
    _install_contract(repo, _contract(status="retired"))
    _install_binding(repo, _binding())
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-CONTRACT-LIFECYCLE" for finding in findings)


def test_always_requires_justification(repo: Path) -> None:
    _install_contract(repo, _contract())
    binding_document = _binding(mode="always")
    binding_document["activation"]["justification_ref"] = None
    _install_binding(repo, binding_document)
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-ALWAYS-JUSTIFICATION" for finding in findings)


def test_always_rejects_globs(repo: Path) -> None:
    _install_contract(repo, _contract())
    binding_document = _binding(mode="always")
    binding_document["activation"]["globs"] = ["**/*.py"]
    _install_binding(repo, binding_document)
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-ALWAYS-GLOBS" for finding in findings)


def test_auto_attached_requires_globs(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding(globs=[]))
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-AUTO-GLOBS" for finding in findings)


def test_advisory_must_is_rejected(repo: Path) -> None:
    _install_contract(repo, _contract())
    document = _binding()
    document["guidance"]["inline"] = [
        {
            "guidance_id": "G01",
            "classification": "advisory",
            "text": "Agents MUST always do this.",
        }
    ]
    _install_binding(repo, document)
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-GUIDANCE-NORMATIVE" for finding in findings)


def test_context_budget_is_hard(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding(budget=10))
    _, resolution = _resolved(repo)
    rendered = render_cursor_rule(resolution)
    with pytest.raises(ValueError, match="exceeding budget"):
        enforce_context_budget(resolution, rendered)


def test_scoped_contract_accepts_narrower_glob(repo: Path) -> None:
    _install_contract(
        repo,
        _contract(paths=["src/**"]),
    )
    _install_binding(
        repo,
        _binding(globs=["src/core/**/*.py"]),
    )
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert not any(finding.code == "RULE-BIND-SCOPE-WIDEN" for finding in findings)


def test_scoped_contract_rejects_wider_glob(repo: Path) -> None:
    _install_contract(
        repo,
        _contract(paths=["src/internal/**"]),
    )
    _install_binding(
        repo,
        _binding(globs=["src/**/*.py"]),
    )
    index = load_contract_index(repo)
    binding = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    findings = validate_binding(binding, index, repo)
    assert any(finding.code == "RULE-BIND-SCOPE-WIDEN" for finding in findings)


def test_require_prohibit_conflict_fails_resolution(repo: Path) -> None:
    first = _contract(
        contract_id="TEST.ALLOW.001",
        effect="require",
        subject="agent",
        action="write",
        obj="target",
    )
    second = _contract(
        contract_id="TEST.DENY.001",
        effect="prohibit",
        subject="agent",
        action="write",
        obj="target",
    )
    _install_contract(repo, first, "allow.yaml")
    _install_contract(repo, second, "deny.yaml")
    binding = _binding(contract_id="TEST.ALLOW.001")
    binding["contract_bindings"].append(
        {
            "contract_id": "TEST.DENY.001",
            "version_constraint": "^1.0",
            "clauses": ["C01"],
            "scope_narrowing": None,
        }
    )
    _install_binding(repo, binding)
    index = load_contract_index(repo)
    loaded = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    with pytest.raises(ValueError, match="conflicting projected clauses"):
        resolve_binding(loaded, index)


def test_filename_order_does_not_resolve_conflict(repo: Path) -> None:
    first = _contract(
        contract_id="TEST.ZZZ.001",
        effect="require",
        subject="agent",
        action="publish",
        obj="artifact",
    )
    second = _contract(
        contract_id="TEST.AAA.001",
        effect="prohibit",
        subject="agent",
        action="publish",
        obj="artifact",
    )
    _install_contract(repo, first, "99-late.yaml")
    _install_contract(repo, second, "00-early.yaml")
    binding = _binding(contract_id="TEST.ZZZ.001")
    binding["contract_bindings"].append(
        {
            "contract_id": "TEST.AAA.001",
            "version_constraint": "^1.0",
            "clauses": ["C01"],
            "scope_narrowing": None,
        }
    )
    _install_binding(repo, binding)
    index = load_contract_index(repo)
    loaded = load_rule_binding(
        repo,
        repo / "contracts/projections/rules/test-rule.yaml",
    )
    with pytest.raises(ValueError):
        resolve_binding(loaded, index)


def test_binding_digest_detects_manual_change(repo: Path) -> None:
    _install_contract(repo, _contract())
    document = _binding()
    _install_binding(repo, document)
    path = repo / "contracts/projections/rules/test-rule.yaml"
    loaded = load_rule_binding(repo, path)
    document["integrity"]["binding_digest"] = loaded.digest
    document["rule_identity"]["title"] = "Changed after digest"
    _write_yaml(path, document)
    with pytest.raises(ValueError, match="binding digest mismatch"):
        load_rule_binding(repo, path)


def test_projection_index_contains_contract_provenance(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    projection_index, outputs = build_projection_index(repo)
    entry = projection_index["rules/40-test-contract.mdc"]
    assert entry["semantic_authority"]["owner"] == "contracts"
    assert entry["contracts"][0]["contract_id"] == "TEST.RULE.001"
    assert "rules/40-test-contract.mdc" in outputs


def test_contract_bound_does_not_write_generated_output(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(
        repo,
        _binding(migration_state="contract_bound"),
    )
    projection_index, outputs = build_projection_index(repo)
    assert "rules/40-test-contract.mdc" in projection_index
    assert "rules/40-test-contract.mdc" not in outputs


def test_generated_output_digest_matches_content(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    projection_index, outputs = build_projection_index(repo)
    text = outputs["rules/40-test-contract.mdc"]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert (
        projection_index["rules/40-test-contract.mdc"]["projection"]["content_digest"]
        == f"sha256:{digest}"
    )


def test_generated_projection_contains_provenance(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    _, outputs = build_projection_index(repo)
    text = outputs["rules/40-test-contract.mdc"]
    assert "[TEST.RULE.001:C01]" in text
    assert "GENERATED FILE — DO NOT EDIT" in text


def test_manual_rule_semantics_are_not_used_for_resolution(repo: Path) -> None:
    _install_contract(repo, _contract())
    _install_binding(repo, _binding())
    legacy = repo / "rules/40-test-contract.mdc"
    legacy.write_text(
        "---\nalwaysApply: false\n"
        "description: stale\n---\n"
        "# Stale\n\nAgent MUST do the opposite.\n",
        encoding="utf-8",
    )
    _, outputs = build_projection_index(repo)
    assert "do the opposite" not in outputs["rules/40-test-contract.mdc"]
