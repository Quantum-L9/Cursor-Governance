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


MAIN = "f8e44d1536cb218de41dde4685c606a4d6460915"
CLASSES = ["vocabulary", "capabilities", "invariants"]


def _base(status: str = host_binding.BASE_CURRENT):
    def verify_base(_base, _ws, _root) -> dict:
        result = {"status": status, "reason": status}
        if status == host_binding.BASE_CURRENT:
            result.update(authority_main=MAIN, source_classes=CLASSES)
        return result

    return verify_base


def _evaluate(host: str = "cursor", **kwargs):
    kwargs.setdefault("verify", _verify())
    kwargs.setdefault("verify_base", _base())
    return host_binding.evaluate(host, **kwargs)


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


def test_base_not_current_is_not_bound_and_loads_nothing() -> None:
    # The base is required: admitted domains are not bound without it.
    report = _evaluate(verify_base=_base("STALE"))
    assert report["status"] == "NOT_BOUND"
    assert report["fail_open"] is True
    assert report["load"] == []
    assert report["blockers"][0]["ref"] == BASE
    assert all(d.get("bound") is False for d in report["domains"] if "bound" in d)


@pytest.mark.parametrize("status", ["BUNDLE_VERIFIED", "BLOCKED", "REJECTED", "STALE"])
def test_activated_domain_not_admitted_degrades_and_keeps_what_verified(status: str) -> None:
    report = _evaluate(verify=_verify({"l9.projection/governance@1": status}))
    assert report["status"] == "DEGRADED"
    assert report["default"]["status"] == "BOUND"
    # Fail-open: the base and every domain that verified stay bound; the failed one is not.
    assert [item["ref"] for item in report["load"]] == [
        ref for ref in ALWAYS if ref != "l9.projection/governance@1"
    ]
    assert [b["ref"] for b in report["blockers"]] == ["l9.projection/governance@1"]
    bound = {d["ref"]: d.get("bound") for d in report["domains"]}
    assert bound["l9.projection/governance@1"] is False
    assert bound["l9.projection/architecture@1"] is True


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


@pytest.mark.parametrize("host", ["cursor", "claude-code"])
def test_every_host_autobinds_at_session_start_without_a_skill(host: str) -> None:
    doc = host_binding.load_contract(host_binding.contract_path(host))
    assert doc["session_start"]["autobind"] is True
    assert doc["session_start"]["depends_on_skill"] is False
    assert doc["session_start"]["manual_bindings"] == ["/coding-agent", "/lcto", "/architect"]
    assert doc["base"]["ref"] == BASE
    assert doc["base"]["required"] is True


def test_claude_code_binds_the_operating_plane_alone() -> None:
    doc = host_binding.load_contract(host_binding.contract_path("claude-code"))
    assert doc["domains"] == []
    report = _evaluate("claude-code")
    assert report["status"] == "BOUND"
    assert report["default"]["status"] == "BOUND"
    assert report["load"] == []


@pytest.mark.parametrize("host", ["cursor", "claude-code"])
def test_default_is_bound_only_on_a_current_base(host: str) -> None:
    bound = _evaluate(host)["default"]
    assert bound["status"] == "BOUND"
    assert bound["automatic"] is True
    assert bound["authority_main"] == MAIN
    assert bound["source_classes"] == CLASSES
    read = bound["read"]
    assert read[1].endswith("ops/scripts/operating_plane_v2_projection.py")
    assert read[-2:] == ["--source-class", "<class>"]
    assert "--mode" in read and read[read.index("--mode") + 1] == "admitted"
    for status in ("STALE", "BLOCKED", "UNVERIFIED", "REJECTED", "BOUND"):
        unbound = _evaluate(host, verify_base=_base(status))["default"]
        assert unbound["status"] == "NOT_BOUND"
        assert unbound["reason"].startswith(f"{status}:")
        assert "read" not in unbound


def test_read_command_pins_the_resolved_authority(tmp_path: Path) -> None:
    def verify_base(_base, _ws, _root) -> dict:
        return {"status": host_binding.BASE_CURRENT, "authority_main": MAIN, "source_classes": []}

    base = host_binding.load_contract(host_binding.contract_path("claude-code"))["base"]
    result = verify_base(base, None, None)
    bound = host_binding.default_binding(base, result, tmp_path, tmp_path / "authority")
    assert bound["read"][bound["read"].index("--authority-root") + 1] == str(tmp_path / "authority")
    assert bound["read"][bound["read"].index("--workspace") + 1] == str(tmp_path)


@pytest.mark.parametrize(
    "start",
    [
        None,
        {"autobind": False, "depends_on_skill": False},
        {"autobind": True, "depends_on_skill": True},
        {"autobind": True},
    ],
)
def test_contract_that_could_gate_on_a_skill_is_rejected(tmp_path: Path, start) -> None:
    doc = yaml.safe_load(host_binding.contract_path("claude-code").read_text())
    if start is None:
        doc.pop("session_start")
    else:
        doc["session_start"] = start
    path = tmp_path / "claude-code.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    report = _evaluate("claude-code", path=path)
    assert report["status"] == "REJECTED"
    assert "SESSION_START_AUTOBIND_REQUIRED" in report["reason"]


def test_renderings_state_exactly_what_is_bound() -> None:
    cursor = host_binding.markdown(_evaluate())
    assert cursor.startswith("### default projection binding (cursor)\n- BOUND — every")
    assert f"- operating plane {BASE}: BOUND at authority main {MAIN[:12]}" in cursor
    assert "  - source classes: vocabulary, capabilities, invariants" in cursor
    assert "  - l9.projection/governance@1 [always]: BOUND — read " in cursor
    assert (
        "  - l9.projection/signals@1 [explicit_task_requirement]: not activated, not bound"
        in cursor
    )
    assert cursor.endswith("- manual bindings: /coding-agent, /lcto, /architect")
    claude = host_binding.line(_evaluate("claude-code")).splitlines()
    assert claude[0].startswith("default projection binding (claude-code): BOUND — every")
    assert all(item.startswith("  ") for item in claude[1:])
    assert not any("domains" in item for item in claude)


def test_degraded_rendering_names_the_unbound_domain_and_continues() -> None:
    report = _evaluate(verify=_verify({"l9.projection/architecture@1": "STALE"}))
    text = host_binding.markdown(report)
    assert "- DEGRADED — partly bound" in text
    assert "1 default domain(s) failed verification and are not" in text
    assert "fail-open: the session continues" in text
    assert "  - l9.projection/architecture@1 [always]: NOT BOUND (STALE: STALE)" in text
    assert f"- operating plane {BASE}: BOUND" in text


@pytest.mark.parametrize("host", ["cursor", "claude-code"])
def test_not_bound_rendering_claims_nothing_and_continues(host: str) -> None:
    report = _evaluate(host, verify_base=_base("STALE"))
    text = host_binding.line(report)
    assert text.startswith(f"default projection binding ({host}): NOT BOUND — ")
    assert "fail-open: the session continues; cite no operating-plane semantics" in text
    assert f"operating plane {BASE}: NOT BOUND (STALE: STALE)" in text
    assert ": BOUND" not in text and "BOUND —" not in text.replace("NOT BOUND —", "")
    assert "source classes" not in text


def test_rejected_contract_renders_not_bound_and_continues(tmp_path: Path) -> None:
    path = tmp_path / "cursor.yaml"
    path.write_text("schema: wrong\n")
    text = host_binding.markdown(_evaluate(path=path))
    assert "- NOT BOUND — host binding contract rejected: HOST_BINDING_SCHEMA_MISMATCH" in text
    assert "fail-open: the session continues" in text


def test_module_failure_still_renders_not_bound(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(host_binding, "evaluate", explode)
    for fmt in ("markdown", "line"):
        assert host_binding.main(["--host", "claude-code", "--format", fmt]) == 0
        out = capsys.readouterr().out
        assert "NOT BOUND — the host binding failed: HOST_BINDING_ERROR: RuntimeError: boom" in out
        assert "fail-open: the session continues" in out
    assert host_binding.main(["--host", "cursor", "--format", "json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "NOT_BOUND"


@pytest.mark.parametrize("host, fmt", [("cursor", "markdown"), ("claude-code", "line")])
def test_session_start_cli_reports_not_bound_without_authority(
    tmp_path: Path, host: str, fmt: str
) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops/autonomy/host_binding.py"),
            "--host",
            host,
            "--workspace",
            str(tmp_path),
            "--format",
            fmt,
        ],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    # No authority checkout is reachable: the session is not bound, and the rendering exits 0.
    assert proc.returncode == 0, proc.stderr
    assert "NOT BOUND — the operating plane did not verify" in proc.stdout
    assert "fail-open: the session continues" in proc.stdout
    assert "BOUND at authority main" not in proc.stdout
