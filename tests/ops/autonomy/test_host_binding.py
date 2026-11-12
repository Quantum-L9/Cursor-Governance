"""Cursor host default binding: the operating plane plus the canonical Cursor domain set."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import host_binding  # noqa: E402

BASE = "l9.projection/cursor-governance-operating-plane@2"
# Quantum-L9/.github l9.domain-consumer-binding/cursor@1, as the owner set the Cursor default.
EXPECTED = {
    "l9.projection/governance@1": "always",
    "l9.projection/architecture@1": "always",
    "l9.projection/contracts-conformance@1": "always",
    "l9.projection/capabilities-dependencies@1": "always",
    "l9.projection/evidence-provenance@1": "hosted_skill_requirement",
    "l9.projection/identity-attribution@1": "hosted_skill_requirement",
    "l9.projection/strategic-value@1": "explicit_task_requirement",
    "l9.projection/signals@1": "explicit_task_requirement",
}
ALWAYS = [ref for ref, activation in EXPECTED.items() if activation == "always"]


def _verify(statuses: dict[str, str] | None = None, default: str = host_binding.ADMITTED):
    statuses = statuses or {}

    def verify(binding: Path, _root: Path | None) -> dict:
        ref = yaml.safe_load(binding.read_text())["input"]["authority"]["projection_profile_ref"]
        status = statuses.get(ref, default)
        return {"status": status, "reason": status}

    return verify


def _base(status: str = host_binding.BASE_CURRENT):
    return lambda _base, _ws, _root: {"status": status, "reason": status}


def _evaluate(**kwargs):
    kwargs.setdefault("verify", _verify())
    kwargs.setdefault("verify_base", _base())
    return host_binding.evaluate("cursor", **kwargs)


def test_contract_mirrors_the_canonical_cursor_binding_on_the_operating_plane() -> None:
    doc = host_binding.load_contract(host_binding.contract_path("cursor"))
    assert doc["canonical_binding_ref"] == "l9.domain-consumer-binding/cursor@1"
    assert doc["base"]["ref"] == BASE
    assert doc["base"]["binding"] == "governance/authority-bindings/operating-plane-v2.yaml"
    assert doc["base"]["required"] is True
    assert {d["ref"]: d["activation"] for d in doc["domains"]} == EXPECTED


@pytest.mark.parametrize("ref", sorted(EXPECTED))
def test_each_domain_binding_names_the_cursor_default_and_pins_its_bundle(ref: str) -> None:
    doc = host_binding.load_contract(host_binding.contract_path("cursor"))
    entry = next(d for d in doc["domains"] if d["ref"] == ref)
    binding = yaml.safe_load((REPO / entry["binding"]).read_text())
    assert "cursor_host_default" in binding["load_condition"]["when"]
    pins = binding["input"]["authority"]
    lock = json.loads((REPO / binding["input"]["bundle"]["path"] / "bundle.lock.json").read_text())
    assert lock["projection_profile"] == {"ref": ref, "digest": pins["projection_profile_digest"]}
    decided = {
        (d["candidate_ref"], d["candidate_digest"]) for d in binding["admission"]["decisions"]
    }
    assert (ref, pins["projection_profile_digest"]) in decided


def test_default_loads_only_the_always_domains() -> None:
    report = _evaluate()
    assert report["status"] == "BOUND"
    assert report["base"]["status"] == host_binding.BASE_CURRENT
    assert [item["ref"] for item in report["load"]] == ALWAYS
    inactive = {d["ref"] for d in report["domains"] if d["status"] == "NOT_ACTIVATED"}
    assert inactive == set(EXPECTED) - set(ALWAYS)
    assert all(Path(item["composed_view"]).is_file() for item in report["load"])


def test_conditional_domains_load_only_when_their_activation_is_named() -> None:
    hosted = _evaluate(activations=frozenset({"hosted_skill_requirement"}))
    assert {i["ref"] for i in hosted["load"]} == set(ALWAYS) | {
        "l9.projection/evidence-provenance@1",
        "l9.projection/identity-attribution@1",
    }
    both = _evaluate(
        activations=frozenset({"hosted_skill_requirement", "explicit_task_requirement"})
    )
    assert [i["ref"] for i in both["load"]] == list(EXPECTED)


def test_conditional_domain_not_activated_is_not_verified() -> None:
    seen: list[str] = []

    def verify(binding: Path, _root: Path | None) -> dict:
        seen.append(binding.name)
        return {"status": host_binding.ADMITTED}

    _evaluate(verify=verify)
    assert sorted(seen) == sorted(f"{ref.split('/')[1].split('@')[0]}.yaml" for ref in ALWAYS)


def test_base_not_current_blocks_and_loads_nothing() -> None:
    report = _evaluate(verify_base=_base("STALE"))
    assert report["status"] == "BLOCKED"
    assert report["load"] == []
    assert report["blockers"][0]["ref"] == BASE


@pytest.mark.parametrize("status", ["BUNDLE_VERIFIED", "BLOCKED", "REJECTED", "STALE"])
def test_activated_domain_not_admitted_blocks(status: str) -> None:
    report = _evaluate(verify=_verify({"l9.projection/governance@1": status}))
    assert report["status"] == "BLOCKED"
    assert report["load"] == []
    assert [b["ref"] for b in report["blockers"]] == ["l9.projection/governance@1"]


def test_unactivated_failure_does_not_block() -> None:
    report = _evaluate(verify=_verify({"l9.projection/signals@1": "STALE"}))
    assert report["status"] == "BOUND"


def test_domains_only_skips_the_base() -> None:
    report = _evaluate(domains_only=True, verify_base=_base("STALE"))
    assert report["base"]["status"] == "NOT_EVALUATED"
    assert report["status"] == "BOUND"


def test_unknown_activation_is_rejected() -> None:
    report = _evaluate(activations=frozenset({"whenever"}))
    assert report["status"] == "REJECTED"


@pytest.mark.parametrize(
    "mutate, reason",
    [
        (lambda d: d["domains"][0].update(activation="sometimes"), "ACTIVATION_UNKNOWN"),
        (lambda d: d["domains"].append(dict(d["domains"][0])), "DOMAIN_DUPLICATE"),
        (lambda d: d["base"].update(required=False), "BASE_MUST_BE_REQUIRED"),
        (lambda d: d["domains"][0].update(binding="nope.yaml"), "BINDING_ABSENT"),
    ],
)
def test_malformed_contract_is_rejected(tmp_path: Path, mutate, reason: str) -> None:
    doc = yaml.safe_load(host_binding.contract_path("cursor").read_text())
    mutate(doc)
    path = tmp_path / "cursor.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    report = _evaluate(path=path)
    assert report["status"] == "REJECTED"
    assert reason in report["reason"]


def test_markdown_cli_is_report_only(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops/autonomy/host_binding.py"),
            "--domains-only",
            "--workspace",
            str(tmp_path),
            "--format",
            "markdown",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    # No authority checkout is reachable: every always domain blocks, and the report still exits 0.
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("### cursor host binding (report-only)")
    assert "- status: BLOCKED" in proc.stdout
